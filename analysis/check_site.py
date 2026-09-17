"""Validate the docs/ site before publishing it.

Checks, with no dependencies:

  1. every local href/src resolves to a file that exists
  2. every in-page anchor (#id) resolves to an element with that id
  3. every page carries the full navigation, and marks exactly one page current
  4. tags are balanced, ignoring void elements
  5. every <img> has a non-empty alt attribute
  6. every page has a description, a canonical URL and a favicon link

    python analysis/check_site.py               validate docs/
    python analysis/check_site.py --selftest    prove the checks can fail

Exits non-zero if anything fails, so it can gate a deploy.

The --selftest mode exists for the reason the paper gives: a check that has
never been observed to fail is not evidence. It copies the site to a temporary
directory, injects four faults, and asserts that all four are reported.
"""
import html.parser
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")

PAGES = ["index.html", "paper.html", "findings.html", "method.html", "reproduce.html"]
NAV = ["index.html", "paper.html", "findings.html", "method.html", "reproduce.html"]

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

# (label, fragment to append, the substring the checker should report)
FAULTS = [
    ("dead page link", '<p><a href="nope.html">x</a></p>', "nope.html"),
    ("dead anchor", '<p><a href="#missing-anchor">x</a></p>', "missing-anchor"),
    ("image with no alt", '<p><img src="assets/style.css"></p>', "no alt attribute"),
    ("unclosed tag", "<p>never closed", "never closed"),
]


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.ids = set()
        self.refs = []          # (attr, value)
        self.imgs = []          # alt strings
        self.current_marks = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)

        if "id" in d:
            if d["id"] in self.ids:
                self.errors.append(f"duplicate id: {d['id']}")
            self.ids.add(d["id"])

        for attr in ("href", "src"):
            if attr in d:
                self.refs.append((attr, d[attr]))

        if d.get("aria-current") == "page":
            self.current_marks += 1

        if tag == "img":
            self.imgs.append(d.get("alt", None))

        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        for attr in ("href", "src"):
            if attr in d:
                self.refs.append((attr, d[attr]))
        if tag == "img":
            self.imgs.append(d.get("alt", None))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"stray </{tag}>")
            return
        open_tag, line = self.stack.pop()
        if open_tag != tag:
            self.errors.append(
                f"</{tag}> closes <{open_tag}> opened at line {line}")


def nav_of(text):
    """Pull the site-nav hrefs in document order."""
    m = re.search(r'<nav class="site-nav">(.*?)</nav>', text, re.S)
    if not m:
        return []
    return re.findall(r'href="([^"]+)"', m.group(1))


def check(docs):
    """Return a list of problems found in the site rooted at `docs`."""
    problems = []

    for name in PAGES:
        path = os.path.join(docs, name)
        if not os.path.exists(path):
            problems.append(f"{name}: MISSING")
            continue

        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        p = Page()
        p.feed(text)

        for err in p.errors:
            problems.append(f"{name}: {err}")

        for tag, line in p.stack:
            problems.append(f"{name}: <{tag}> opened at line {line} never closed")

        # navigation
        got = nav_of(text)
        if len(got) < len(NAV):
            problems.append(f"{name}: navigation is incomplete ({len(got)} links)")
        for want in NAV:
            if want not in got:
                problems.append(f"{name}: navigation missing {want}")
        if p.current_marks != 1:
            problems.append(
                f'{name}: expected exactly one aria-current="page", found {p.current_marks}')

        # images need alt text
        for i, alt in enumerate(p.imgs):
            if alt is None:
                problems.append(f"{name}: <img> #{i + 1} has no alt attribute")
            elif not alt.strip():
                problems.append(f"{name}: <img> #{i + 1} has empty alt text")

        # head metadata
        if not re.search(r'<meta name="description" content="[^"]+"', text):
            problems.append(f"{name}: no meta description")
        if 'rel="canonical"' not in text:
            problems.append(f"{name}: no canonical link")
        if 'rel="icon"' not in text:
            problems.append(f"{name}: no favicon link")

        # references
        for attr, value in p.refs:
            if value.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if value.startswith("#"):
                if value[1:] and value[1:] not in p.ids:
                    problems.append(f"{name}: dead anchor {value}")
                continue

            target, _, frag = value.partition("#")
            if not target:
                continue
            resolved = os.path.normpath(os.path.join(docs, target))
            if not os.path.exists(resolved):
                problems.append(f'{name}: {attr}="{value}" -> file not found')
                continue
            if frag and resolved.endswith(".html"):
                with open(resolved, encoding="utf-8") as fh:
                    other = fh.read()
                if f'id="{frag}"' not in other:
                    problems.append(f"{name}: {value} -> anchor not found")

    # required support files
    for rel in (".nojekyll", "assets/style.css", "assets/favicon.svg"):
        if not os.path.exists(os.path.join(docs, rel)):
            problems.append(f"docs/{rel}: MISSING")

    figs = os.path.join(docs, "assets", "figures")
    if not os.path.isdir(figs):
        problems.append("docs/assets/figures: MISSING")

    return problems


def selftest():
    """Inject known faults and assert the checker reports every one.

    Without this, 'the site check passes' is a claim about an untested program.
    """
    print("  SELFTEST -- injecting faults into a temporary copy")
    failures = []

    tmp = tempfile.mkdtemp(prefix="drape-selftest-")
    try:
        copy = os.path.join(tmp, "docs")
        shutil.copytree(DOCS, copy)

        for label, fragment, expect in FAULTS:
            target = os.path.join(copy, "index.html")
            with open(target, encoding="utf-8") as fh:
                original = fh.read()

            with open(target, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(original.replace("</main>", fragment + "\n</main>", 1))

            found = check(copy)
            hit = any(expect in prob for prob in found)

            with open(target, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(original)

            status = "caught" if hit else "MISSED"
            print(f"    {label:<22} {status}")
            if not hit:
                failures.append(label)

        # the restored copy must be clean, or the selftest proves nothing
        residual = check(copy)
        if residual:
            print(f"    restore                 DIRTY ({len(residual)} problems)")
            failures.extend(residual)
        else:
            print("    restore                 clean")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"  {len(failures)} fault(s) not caught -- the checker is not trustworthy.")
        return 1
    print("  all four faults caught, and the restored copy is clean.")
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()

    figs = os.path.join(DOCS, "assets", "figures")
    n_figs = len([f for f in os.listdir(figs) if f.endswith(".svg")]) \
        if os.path.isdir(figs) else 0
    print(f"  figures found: {n_figs}")
    print(f"  pages checked: {len(PAGES)}")

    problems = check(DOCS)
    if problems:
        print()
        for prob in problems:
            print("  FAIL " + prob)
        print(f"\n  {len(problems)} problem(s) -- do not publish.")
        return 1

    print("  all links resolve, all anchors exist, all tags balanced.")
    print("  SITE CHECK PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
