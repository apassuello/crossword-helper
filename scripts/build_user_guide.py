#!/usr/bin/env python3
"""Build the HTML user guide from the Markdown user guide.

The Markdown pages under docs/user-guide/ are the source: they are what GitHub
renders and what gets edited. This script turns them into a navigable site under
docs/user-guide/site/, one .html page per .md page, which a reader opens from a
clone or a ZIP without a server (docs/user-guide/site/index.html).

  python scripts/build_user_guide.py           # write the site
  python scripts/build_user_guide.py --check   # exit 1 if the committed site is stale

What the build adds to the Markdown, and nothing more:
  - a page list (NAV below), an "on this page" list, previous/next links;
  - links between guide pages point at the .html pages; links leaving the guide
    point at the file on GitHub, since a relative path would not resolve from the site;
  - an image alone in a paragraph becomes a figure, and an italic line right
    after it becomes its caption;
  - "[?]" (an unverified claim, per the docs convention) becomes a labelled tag;
  - a paragraph starting "**You should see" becomes a checkpoint box.

Hand-edited, not generated: docs/user-guide/site/assets/ (styles, script, fonts)
and scripts/user_guide_site/template.html.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs" / "user-guide"
SITE = GUIDE / "site"
TEMPLATE = ROOT / "scripts" / "user_guide_site" / "template.html"
GITHUB_BLOB = "https://github.com/apassuello/crossword-helper/blob/main/"

# Page order for the page list and previous/next. Every .md page in the guide must
# appear here exactly once; the build fails otherwise, so a new page cannot be orphaned.
NAV: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Start here",
        [
            ("README.md", "Overview"),
            ("how-to/install-on-macos.md", "Install on macOS"),
            ("tutorials/first-crossword.md", "Your first crossword"),
        ],
    ),
    (
        "How-to guides",
        [
            ("how-to/set-up-the-grid.md", "Set up the grid"),
            ("how-to/save-open-and-recover.md", "Save, reopen and recover"),
            ("how-to/find-words-by-pattern.md", "Find words by pattern"),
            ("how-to/use-your-own-word-lists.md", "Use your own word lists"),
            ("how-to/add-theme-words.md", "Add theme words"),
            ("how-to/autofill-a-grid.md", "Autofill a grid"),
            ("how-to/check-and-clean-a-grid.md", "Check and clean a grid"),
            ("how-to/import-and-export-grids.md", "Import and export grids"),
            ("how-to/troubleshoot.md", "Troubleshoot"),
        ],
    ),
    ("Reference", [("reference/web-app.md", "Web app reference"), ("reference/file-formats.md", "File formats")]),
]

KIND = {"tutorials": "Tutorial", "how-to": "How-to guide", "reference": "Reference"}
EXTENSIONS = ["tables", "fenced_code", "toc", "attr_list", "sane_lists"]


@dataclass(frozen=True)
class Page:
    source: str  # path relative to GUIDE, e.g. "how-to/add-theme-words.md"
    label: str

    @property
    def output(self) -> str:
        return "index.html" if self.source == "README.md" else self.source[:-3] + ".html"


def nav_pages() -> list[Page]:
    return [Page(src, label) for _, items in NAV for src, label in items]


def check_nav_complete(pages: list[Page]) -> None:
    on_disk = {p.relative_to(GUIDE).as_posix() for p in GUIDE.rglob("*.md") if SITE not in p.parents}
    listed = [p.source for p in pages]
    missing, extra = on_disk - set(listed), set(listed) - on_disk
    if missing or extra or len(listed) != len(set(listed)):
        raise SystemExit(
            f"build_user_guide: NAV does not match the guide's pages.\n  not in NAV: {sorted(missing)}\n"
            f"  in NAV but no file: {sorted(extra)}"
        )


def rewrite_url(url: str, page: Page) -> str:
    """Map a URL written for the Markdown page to one that works from the built page."""
    if re.match(r"^[a-z][a-z0-9+.-]*:|^#|^//", url, re.I):
        return url
    path_part, _, fragment = url.partition("#")
    fragment = "#" + fragment if fragment else ""
    target = (GUIDE / page.source).parent.joinpath(path_part).resolve()
    out_dir = (SITE / page.output).parent
    if GUIDE in target.parents and SITE not in target.parents:
        rel = target.relative_to(GUIDE).as_posix()
        if rel.endswith(".md"):
            built = SITE / ("index.html" if rel == "README.md" else rel[:-3] + ".html")
            return Path(os.path.relpath(built, out_dir)).as_posix() + fragment
        return Path(os.path.relpath(target, out_dir)).as_posix() + fragment
    return GITHUB_BLOB + target.relative_to(ROOT).as_posix() + fragment


def image_size(path: Path) -> tuple[int, int] | None:
    """Display size of a PNG (stored at 2x, so halved) or an SVG (its width/height attributes)."""
    if not path.exists():
        raise SystemExit(f"build_user_guide: image not found: {path.relative_to(ROOT)}")
    if path.suffix == ".png":
        with path.open("rb") as handle:
            header = handle.read(24)
        width, height = struct.unpack(">II", header[16:24])
        return width // 2, height // 2
    if path.suffix == ".svg":
        found = re.search(r'<svg[^>]*\swidth="(\d+)"[^>]*\sheight="(\d+)"', path.read_text(encoding="utf-8"))
        return (int(found.group(1)), int(found.group(2))) if found else None
    return None


def transform(body: str, page: Page) -> str:
    def relink(match: re.Match) -> str:
        url = rewrite_url(html.unescape(match.group(2)), page)
        return f'{match.group(1)}="{html.escape(url)}"'

    body = re.sub(r'(href|src)="([^"]+)"', relink, body)

    def figure(match: re.Match) -> str:
        attrs, caption_text = match.group(1), match.group(2)
        src = re.search(r'src="([^"]+)"', attrs).group(1)
        classes = ["g-figure"]
        if src.endswith(".svg"):
            classes.append("is-diagram")
        size = image_size(((SITE / page.output).parent / html.unescape(src)).resolve())
        if size:
            width, height = size
            attrs += f' width="{width}" height="{height}"'
            if height > width * 1.1:  # a tall panel screenshot: show it narrower than the text column
                classes.append("is-narrow")
        caption = f"<figcaption>{caption_text}</figcaption>" if caption_text else ""
        img = f'<img{attrs} loading="lazy">'
        return f'<figure class="{" ".join(classes)}"><a href="{src}">{img}</a>{caption}</figure>'

    # An image alone in a paragraph is a figure; an italic paragraph right after it is its caption.
    body = re.sub(r"<p><img([^>]*?)\s*/?></p>(?:\s*<p><em>(.*?)</em></p>)?", figure, body, flags=re.S)
    body = re.sub(r"<table>", '<div class="g-table"><table>', body)
    body = re.sub(r"</table>", "</table></div>", body)
    body = body.replace(
        "[?]", '<span class="g-unverified" title="Not checked against the running app for this page">unverified</span>'
    )
    body = re.sub(r"<p><strong>You should see", '<p class="g-check"><strong>You should see', body)
    return body


def render_toc(tokens: list[dict]) -> str:
    sections = tokens[0]["children"] if len(tokens) == 1 else tokens
    if not sections:
        return ""

    def items(nodes: list[dict]) -> str:
        out = []
        for node in nodes:
            sub = f"<ul>{items(node['children'])}</ul>" if node["children"] and node["level"] < 3 else ""
            out.append(f'<li><a href="#{node["id"]}">{node["name"]}</a>{sub}</li>')
        return "".join(out)

    return f"    <h2>On this page</h2>\n    <ul>{items(sections)}</ul>"


def render_nav(current: Page) -> str:
    out = []
    for heading, items in NAV:
        out.append(f"    <h2>{heading}</h2>\n    <ul>")
        for src, label in items:
            target = Page(src, label)
            href = os.path.relpath(SITE / target.output, (SITE / current.output).parent)
            mark = ' aria-current="page"' if src == current.source else ""
            out.append(f'      <li><a href="{Path(href).as_posix()}"{mark}>{label}</a></li>')
        out.append("    </ul>")
    return "\n".join(out)


def render_pager(pages: list[Page], index: int) -> str:
    def link(target: Page, word: str, cls: str) -> str:
        href = Path(os.path.relpath(SITE / target.output, (SITE / pages[index].output).parent)).as_posix()
        return f'<a class="{cls}" href="{href}"><small>{word}</small>{target.label}</a>'

    prev = link(pages[index - 1], "Previous", "is-prev") if index > 0 else "<span></span>"
    nxt = link(pages[index + 1], "Next", "is-next") if index + 1 < len(pages) else "<span></span>"
    return prev + nxt


def render(pages: list[Page]) -> dict[str, str]:
    template = TEMPLATE.read_text(encoding="utf-8")
    built = {}
    for i, page in enumerate(pages):
        md = markdown.Markdown(extensions=EXTENSIONS)
        body = transform(md.convert((GUIDE / page.source).read_text(encoding="utf-8")), page)
        title = md.toc_tokens[0]["name"] if md.toc_tokens else page.label
        depth = page.output.count("/")
        built[page.output] = template.format(
            title=title,
            root="../" * depth,
            source=f"docs/user-guide/{page.source}",
            source_url=GITHUB_BLOB + f"docs/user-guide/{page.source}",
            nav=render_nav(page),
            kind=KIND.get(page.source.split("/")[0], "User guide"),
            content=body,
            pager=render_pager(pages, i),
            toc=render_toc(md.toc_tokens),
        )
    return built


def generated_on_disk() -> set[str]:
    return {p.relative_to(SITE).as_posix() for p in SITE.rglob("*.html")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the HTML user guide from docs/user-guide/*.md.")
    parser.add_argument("--check", action="store_true", help="fail if the committed site differs from a fresh build")
    args = parser.parse_args()

    pages = nav_pages()
    check_nav_complete(pages)
    built = render(pages)

    if args.check:
        stale = sorted(
            out for out, text in built.items() if not (SITE / out).exists() or (SITE / out).read_text(encoding="utf-8") != text
        )
        orphans = sorted(generated_on_disk() - set(built))
        if stale or orphans:
            print("docs/user-guide/site/ is out of date with the Markdown guide.", file=sys.stderr)
            for out in stale:
                print(f"  stale:   docs/user-guide/site/{out}", file=sys.stderr)
            for out in orphans:
                print(f"  orphan:  docs/user-guide/site/{out}", file=sys.stderr)
            print("Run: python scripts/build_user_guide.py", file=sys.stderr)
            return 1
        print(f"docs/user-guide/site/ is up to date ({len(built)} pages).")
        return 0

    for out in generated_on_disk() - set(built):
        (SITE / out).unlink()
    for out, text in built.items():
        dest = SITE / out
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    print(f"Wrote {len(built)} pages to docs/user-guide/site/ (open docs/user-guide/site/index.html).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
