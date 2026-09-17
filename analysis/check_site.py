"""Validate the docs/ site before publishing it.

Checks, with no dependencies:

  1. every local href/src resolves to a file that exists
  2. every in-page anchor (#id) resolves to an element with that id
  3. every page carries the full navigation, and marks exactly one page current
  4. tags are balanced, ignoring void elements
  5. every <img> has a non-empty alt attribute

    python analysis/check_site.py

Exits non-zero if anything fails, so it can gate a deploy.
"""
import html.parser
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")

PAGES = ["index.html", "paper.html", "findings.html", "method.html", "reproduce.html"]
NAV = ["index.html", "paper.html", "findings.html", "method.html", "reproduce.html"]

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


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


def main():
    problems = []

    for name in PAGES:
        path = os.path.join(DOCS, name)
        if not os.path.exists(path):
            problems.append(f"{name}: MISSING")
            continue

        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        p = Page()
        p.feed(text)

        for err in p.errors:
            problems.append(f"{name}: {err}")

        if p.stack:
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
                f"{name}: expected exactly one aria-current=\"page\", found {p.current_marks}")

        # images need alt text
        for i, alt in enumerate(p.imgs):
            if alt is None:
                problems.append(f"{name}: <img> #{i + 1} has no alt attribute")
            elif not alt.strip():
                problems.append(f"{name}: <img> #{i + 1} has empty alt text")

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
            resolved = os.path.normpath(os.path.join(DOCS, target))
            if not os.path.exists(resolved):
                problems.append(f"{name}: {attr}=\"{value}\" -> file not found")
                continue
            if frag and resolved.endswith(".html"):
                with open(resolved, encoding="utf-8") as fh:
                    other = fh.read()
                if f'id="{frag}"' not in other:
                    problems.append(f"{name}: {value} -> anchor not found")

    # required support files
    for rel in (".nojekyll", "assets/style.css"):
        if not os.path.exists(os.path.join(DOCS, rel)):
            problems.append(f"docs/{rel}: MISSING")

    figs = os.path.join(DOCS, "assets", "figures")
    if not os.path.isdir(figs):
        problems.append("docs/assets/figures: MISSING")
    else:
        n = len([f for f in os.listdir(figs) if f.endswith(".svg")])
        print(f"  figures found: {n}")

    print(f"  pages checked: {len(PAGES)}")

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
    sys.exit(main())
