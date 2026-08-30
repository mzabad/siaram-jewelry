#!/usr/bin/env python3
"""
Automated smoke test for the Siaram Jewelry static site.

Checks, for every .html page in the project root:
  - all internal links (href) point to files that actually exist
  - all images (src) point to files that actually exist
  - all images have non-empty alt text
  - required tags exist: <title>, viewport meta, favicon link

Note: WhatsApp/phone contact info is intentionally shown site-wide
(footer contact box), so there's no longer a regression check for it.

Run it any time after editing the site:

    python tests/check-site.py

Exits with code 0 if everything passes, 1 if anything fails.
"""

import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))



class PageChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []       # (tag, attr_value, line)
        self.images = []      # (src, alt, line)
        self.has_title = False
        self.has_viewport = False
        self.has_favicon = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        line = self.getpos()[0]
        if tag == "a" and attrs.get("href"):
            self.links.append((attrs["href"], line))
        elif tag == "img":
            self.images.append((attrs.get("src", ""), attrs.get("alt"), line))
        elif tag == "meta" and attrs.get("name") == "viewport":
            self.has_viewport = True
        elif tag == "link" and attrs.get("rel") == "icon":
            self.has_favicon = True

    def handle_data(self, data):
        pass

    def handle_starttag_title(self):
        pass


def is_external_or_special(href: str) -> bool:
    if href.startswith("#"):
        return True
    scheme = urlsplit(href).scheme
    return scheme in ("http", "https", "mailto", "tel")


def check_page(path: str, all_failures: list):
    rel_path = os.path.relpath(path, ROOT)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # <title> present and non-empty
    title_match = re.search(r"<title>(.*?)</title>", content, re.S)
    if not title_match or not title_match.group(1).strip():
        all_failures.append(f"{rel_path}: missing or empty <title>")

    parser = PageChecker()
    parser.feed(content)

    if not parser.has_viewport:
        all_failures.append(f"{rel_path}: missing viewport meta tag")
    if not parser.has_favicon:
        all_failures.append(f"{rel_path}: missing favicon <link rel=\"icon\">")

    page_dir = os.path.dirname(path)

    for href, line in parser.links:
        if is_external_or_special(href):
            continue
        target_path = href.split("#")[0].split("?")[0]
        if not target_path:
            continue
        resolved = os.path.normpath(os.path.join(page_dir, target_path))
        if not os.path.isfile(resolved):
            all_failures.append(f"{rel_path}:{line}: broken link -> {href}")

    for src, alt, line in parser.images:
        if not src:
            all_failures.append(f"{rel_path}:{line}: <img> with empty src")
            continue
        if is_external_or_special(src):
            continue
        resolved = os.path.normpath(os.path.join(page_dir, src))
        if not os.path.isfile(resolved):
            all_failures.append(f"{rel_path}:{line}: broken image -> {src}")
        if not alt or not alt.strip():
            all_failures.append(f"{rel_path}:{line}: <img src=\"{src}\"> missing alt text")


def main():
    html_files = sorted(
        f for f in os.listdir(ROOT) if f.endswith(".html")
    )
    if not html_files:
        print("No .html files found at project root:", ROOT)
        sys.exit(1)

    failures = []
    for filename in html_files:
        check_page(os.path.join(ROOT, filename), failures)

    print(f"Checked {len(html_files)} page(s): {', '.join(html_files)}\n")

    if failures:
        print(f"FAILED — {len(failures)} issue(s):\n")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("PASSED — no broken links or missing images.")
        sys.exit(0)


if __name__ == "__main__":
    main()
