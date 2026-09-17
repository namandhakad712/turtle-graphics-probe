"""Add the shared <head> metadata to every docs page, idempotently.

Favicon, canonical URL and Open Graph / Twitter card tags. Run after adding a
page; running it twice changes nothing.

    python analysis/add_head_meta.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")

SITE = "https://namandhakad712.github.io/drape/"
PAGES = ["index.html", "paper.html", "findings.html", "method.html", "reproduce.html"]

BLOCK = """<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="canonical" href="{url}">
<meta name="author" content="Naman Dhakad">
<meta name="theme-color" content="#1f5fa8">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Drape">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{site}assets/figures/fig1-degeneracy.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
"""


def attr(text, name):
    m = re.search(rf'<meta name="{name}" content="([^"]*)"', text)
    return m.group(1) if m else ""


def main():
    changed = 0
    for page in PAGES:
        path = os.path.join(DOCS, page)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        if 'rel="canonical"' in text:
            print(f"  {page:<18} already has the block")
            continue

        title = attr(text, "description") and ""
        m = re.search(r"<title>(.*?)</title>", text, re.S)
        title = m.group(1) if m else "Drape"
        desc = attr(text, "description")
        if not desc:
            print(f"  {page:<18} SKIP -- no meta description")
            continue

        url = SITE + ("" if page == "index.html" else page)
        block = BLOCK.format(url=url, title=title, desc=desc, site=SITE)

        anchor = re.search(r'<meta name="description"[^>]*>\n', text)
        if not anchor:
            print(f"  {page:<18} SKIP -- no description tag to anchor on")
            continue

        text = text[:anchor.end()] + block + text[anchor.end():]

        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"  {page:<18} added {block.count(chr(10))} lines")
        changed += 1

    print(f"\n  {changed} page(s) updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
