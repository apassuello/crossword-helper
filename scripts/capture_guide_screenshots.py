#!/usr/bin/env python3
"""Capture the screenshots used by the user guide (docs/user-guide/images/).

Drives the running web app through the tutorial and each tool with Playwright, in
a fresh browser profile (empty local storage), light theme, at a fixed viewport.
Re-run it after a UI change and commit the images that changed.

Prerequisites, not installed by setup.sh:
  pip install playwright        # uses the installed Google Chrome, no browser download
  npm run build                 # Flask serves frontend/dist; a stale build gives a stale UI
  PORT=5077 python3 run.py      # in another terminal

Usage:
  python scripts/capture_guide_screenshots.py [--url http://localhost:5077] [--only NAME ...]

Autofill output differs from run to run, so the shots taken after a fill (Verify,
Clean, Save, Export) use a fixed grid, scripts/guide_fixtures/tutorial-filled.json.
If that file is missing, this script writes it from the live fill it just made.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import BrowserContext, Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "user-guide" / "images"
FIXTURES = ROOT / "scripts" / "guide_fixtures"
FILLED = FIXTURES / "tutorial-filled.json"

VIEWPORT = {"width": 1440, "height": 900}
SCALE = 2

# Tutorial step 4: (row, column), counted from 1.
TUTORIAL_BLACKS = [(1, 5), (2, 5), (3, 5), (4, 1), (4, 6), (4, 7), (4, 8), (5, 1), (5, 8), (6, 4)]

IMPORT_EXAMPLE = {
    "size": 5,
    "grid": [
        ["C", "A", "T", "#", "."],
        [".", ".", ".", ".", "."],
        [".", ".", "#", ".", "."],
        [".", ".", ".", ".", "."],
        [".", "#", ".", ".", "."],
    ],
}


class Shooter:
    def __init__(self, page: Page, only: set[str] | None):
        self.page = page
        self.only = only
        self.taken: list[str] = []

    def _wanted(self, name: str) -> bool:
        return not self.only or name in self.only

    def full(self, name: str) -> None:
        if self._wanted(name):
            self.page.screenshot(path=str(OUT / f"{name}.png"))
            self.taken.append(name)

    def region(self, name: str, *locators: Locator, pad: int = 12) -> None:
        """Screenshot the union of the locators' boxes, padded, clipped to the viewport."""
        if not self._wanted(name):
            return
        boxes = [box for box in (loc.bounding_box() for loc in locators) if box]
        if not boxes:
            raise RuntimeError(f"{name}: no visible element to capture")
        left = max(0, min(box["x"] for box in boxes) - pad)
        top = max(0, min(box["y"] for box in boxes) - pad)
        right = min(VIEWPORT["width"], max(box["x"] + box["width"] for box in boxes) + pad)
        bottom = min(VIEWPORT["height"], max(box["y"] + box["height"] for box in boxes) + pad)
        self.page.screenshot(
            path=str(OUT / f"{name}.png"),
            clip={"x": left, "y": top, "width": right - left, "height": bottom - top},
        )
        self.taken.append(name)

    def whole_panel(self, name: str) -> None:
        """The right-hand panel from its top, unscrolled: grow the window to fit the panel's
        content, capture the panel, then restore the window."""
        if not self._wanted(name):
            return
        panel = self.page.locator(".xw-inspector")
        content_height = panel.evaluate("el => { el.scrollTop = 0; return el.scrollHeight; }")
        top = panel.bounding_box()["y"]
        self.page.set_viewport_size({"width": VIEWPORT["width"], "height": int(top + content_height + 24)})
        self.page.wait_for_timeout(300)
        panel.screenshot(path=str(OUT / f"{name}.png"))
        self.page.set_viewport_size(VIEWPORT)
        self.page.wait_for_timeout(200)
        self.taken.append(name)


def button(page: Page, name: str, exact: bool = True) -> Locator:
    return page.get_by_role("button", name=name, exact=exact)


def tool(page: Page, name: str) -> None:
    page.locator(".xw-toolrail .xw-tool-btn", has_text=name).first.click()
    page.wait_for_timeout(300)


def click_cell(page: Page, row: int, col: int) -> None:
    """Click the square at (row, col), counted from 1, by geometry of the grid SVG."""
    svg = page.locator(".xw-grid-svg")
    size = int(svg.get_attribute("aria-label").split(" by ")[0])
    box = svg.bounding_box()
    inset = 12  # the SVG draws the grid 12px inside its box
    cell = (box["width"] - 2 * inset) / size
    page.mouse.click(box["x"] + inset + cell * (col - 0.5), box["y"] + inset + cell * (row - 0.5))


def dismiss_toasts(page: Page) -> None:
    for btn in page.locator(".xw-toast-dismiss").all():
        try:
            btn.click(timeout=500)
        except PlaywrightTimeout:
            pass  # the toast closed on its own between listing and clicking
    page.wait_for_timeout(200)


def wait_hot_toasts_gone(page: Page) -> None:
    """The Theme and Lists panels report through react-hot-toast, which has no close
    button; wait for its toasts to time out instead."""
    page.wait_for_function("() => !document.querySelector('[role=status][aria-live]')", timeout=15000)


def wait_toast(page: Page, text: str, timeout: int = 15000) -> Locator:
    toast = page.locator(".xw-toast", has_text=text).first
    toast.wait_for(timeout=timeout)
    return toast


def new_grid(page: Page, size: str) -> None:
    tool(page, "Grid")
    button(page, size).click()
    replace = button(page, "Replace")
    if replace.count():
        replace.click()
    page.wait_for_timeout(300)


def annotate_overview(page: Page) -> None:
    """Overlay numbered callouts on the main regions; the guide's text explains each number."""
    page.evaluate(
        """() => {
      const marks = [
        ['.xw-topbar-right', 1, 'top bar'],
        ['.xw-toolrail-top', 2, 'tool rail'],
        ['.xw-toolrail-bottom', 3, 'view, grid stats, violations'],
        ['.xw-grid-wrap', 4, 'grid'],
        ['.xw-inspector', 5, 'tool panel'],
      ];
      for (const [sel, n] of marks) {
        const el = document.querySelector(sel);
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        const box = document.createElement('div');
        box.className = 'guide-annot';
        Object.assign(box.style, {position:'fixed', left:rect.x+2+'px', top:rect.y+2+'px',
          width:rect.width-4+'px', height:rect.height-4+'px', border:'2px dashed #1d5fa8',
          borderRadius:'6px', zIndex:9999, pointerEvents:'none'});
        // A small numbered badge on the box's corner; the guide's text names each number.
        const badge = document.createElement('div');
        badge.textContent = n;
        Object.assign(badge.style, {position:'absolute', right:'-11px', bottom:'-11px', width:'22px',
          height:'22px', lineHeight:'22px', textAlign:'center', background:'#1d5fa8', color:'#fff',
          font:'700 13px system-ui, sans-serif', borderRadius:'50%', boxShadow:'0 0 0 2px #fff'});
        box.appendChild(badge);
        document.body.appendChild(box);
      }
    }"""
    )


def clear_annotations(page: Page) -> None:
    page.evaluate("() => document.querySelectorAll('.guide-annot').forEach(e => e.remove())")


def export_json(page: Page, dest: Path) -> None:
    tool(page, "Export")
    page.locator(".xw-inspector select").first.select_option(label="JSON (for reimport)")
    with page.expect_download() as dl:
        page.locator(".xw-inspector .export-btn").click()
    dl.value.save_as(str(dest))


def import_json(page: Page, data: dict) -> None:
    tool(page, "Import")
    button(page, "Paste JSON").click()
    page.locator(".xw-inspector textarea").fill(json.dumps(data))
    button(page, "Validate JSON").click()
    page.wait_for_timeout(500)


def run(url: str, only: set[str] | None) -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="guide-capture-"))
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE, color_scheme="light", accept_downloads=True)
        page = ctx.new_page()
        s = Shooter(page, only)
        try:
            _flow(page, ctx, s, url, tmp)
        except Exception:
            debug = tmp / "failure.png"
            page.screenshot(path=str(debug))
            print(f"capture failed; page state saved to {debug}", file=sys.stderr)
            raise
        finally:
            browser.close()
    return s.taken


def _flow(page: Page, ctx: BrowserContext, s: Shooter, url: str, tmp: Path) -> None:
    page.goto(url)
    page.locator(".xw-status", has_text="online").wait_for(timeout=15000)
    page.evaluate("() => { localStorage.setItem('xw_theme', 'light'); }")
    page.reload()
    page.locator(".xw-status", has_text="online").wait_for(timeout=15000)

    # --- The app at a glance -------------------------------------------------------------
    annotate_overview(page)
    s.full("app-overview")
    clear_annotations(page)

    # --- Tutorial: 11x11, black squares, JAZZ ---------------------------------------------
    new_grid(page, "11×11")
    for r, c in TUTORIAL_BLACKS:
        click_cell(page, r, c)
        page.keyboard.press("Space")
    click_cell(page, 1, 1)
    page.keyboard.type("JAZZ")
    page.wait_for_timeout(400)
    s.region("tutorial-grid", page.locator(".xw-toolrail-bottom"), page.locator(".xw-grid-wrap"))

    button(page, "Verify words", exact=False).click()
    toast = wait_toast(page, "valid")
    s.region("verify-all-valid", page.locator(".xw-topbar-right"), toast)
    dismiss_toasts(page)

    # --- Search ---------------------------------------------------------------------------
    tool(page, "Search")
    page.get_by_placeholder("Enter pattern (e.g., ?I?A)").fill("C?T")
    page.locator(".xw-inspector").get_by_role("button", name="Search", exact=True).click()
    page.get_by_text("Results (", exact=False).first.wait_for(timeout=15000)
    page.wait_for_timeout(300)
    s.whole_panel("search-results")

    # --- Autofill -------------------------------------------------------------------------
    tool(page, "Autofill")
    page.locator(".xw-af-opts select").nth(1).select_option(label="1 min")
    s.whole_panel("autofill-options")
    button(page, "Start Autofill").click()
    page.wait_for_timeout(4000)
    s.full("autofill-running")
    keep = button(page, "Keep fill")
    reset = button(page, "Reset")
    reset.wait_for(timeout=150000)
    page.wait_for_timeout(500)
    s.whole_panel("autofill-result")
    if keep.count():
        keep.click()
    else:
        reset.click()
    page.wait_for_timeout(500)

    # --- A fixed filled grid for everything after the fill --------------------------------
    if not FILLED.exists():
        export_json(page, FILLED)
        print(f"wrote fixture {FILLED.relative_to(ROOT)} from this run's fill")
    import_json(page, json.loads(FILLED.read_text()))
    s.whole_panel("import-preview")
    button(page, "Import Grid").click()
    if button(page, "Replace").count():
        button(page, "Replace").click()
    page.wait_for_timeout(500)

    button(page, "Verify words", exact=False).click()
    wait_toast(page, "flagged")
    page.wait_for_timeout(300)
    s.full("verify-flagged")
    dismiss_toasts(page)

    button(page, "Clean grid", exact=False).click()
    confirm = page.locator(".xw-inline-confirm")
    confirm.wait_for(timeout=5000)
    s.region("clean-confirm", page.locator(".xw-topbar-right"), confirm)
    confirm.get_by_role("button", name="Cancel").click()

    # --- Save, saved list, export ---------------------------------------------------------
    button(page, "Save grid", exact=False).click()
    prompt = page.locator("form.xw-save-prompt, .xw-save-prompt").first
    prompt.wait_for(timeout=5000)
    s.region("save-prompt", page.locator(".xw-topbar-right"), prompt)
    prompt.get_by_role("button", name="Save", exact=True).click()
    # Autosave may already have stored the grid under the suggested name.
    replace_saved = page.get_by_role("button", name="Replace", exact=True)
    try:
        replace_saved.wait_for(timeout=1500)
        replace_saved.click()
    except PlaywrightTimeout:
        pass
    page.get_by_text("saved locally", exact=False).first.wait_for(timeout=10000)
    page.wait_for_timeout(300)

    tool(page, "Grid")
    button(page, "Open saved").click()
    page.wait_for_timeout(500)
    s.region("saved-grids", page.locator(".xw-inspector .xw-grid-panel"))

    tool(page, "Export")
    page.locator(".xw-inspector select").first.select_option(label="HTML (printable)")
    s.whole_panel("export-panel")
    with page.expect_download() as dl:
        page.locator(".xw-inspector .export-btn").click()
    html_file = tmp / "crossword.html"
    dl.value.save_as(str(html_file))
    if s._wanted("export-html-page"):
        view = ctx.new_page()
        view.set_viewport_size({"width": 900, "height": 760})
        view.goto(html_file.as_uri())
        view.wait_for_timeout(300)
        box = view.evaluate(
            """() => { const r = document.body.getBoundingClientRect();
                       const t = document.querySelector('table').getBoundingClientRect();
                       return {x: r.x, y: 0, width: r.width, height: t.bottom + 32}; }"""
        )
        view.screenshot(path=str(OUT / "export-html-page.png"), clip=box)
        view.close()
        s.taken.append("export-html-page")

    # --- Reload: the restore banner -------------------------------------------------------
    page.reload()
    banner = page.locator(".xw-restore-banner")
    banner.wait_for(timeout=10000)
    page.wait_for_timeout(300)
    s.full("restore-banner")
    banner.get_by_role("button", name="Dismiss").click()

    # --- Theme words on an empty 15x15 ----------------------------------------------------
    new_grid(page, "15×15")
    tool(page, "Theme")
    page.locator(".xw-inspector-shell input[type=file], .theme-words-panel input[type=file]").first.set_input_files(
        str(FIXTURES / "theme-words.txt")
    )
    page.get_by_text("Placement Suggestions", exact=False).first.wait_for(timeout=20000)
    page.get_by_role("button", name="Apply This Placement", exact=False).first.wait_for(timeout=20000)
    page.wait_for_timeout(500)
    dismiss_toasts(page)
    wait_hot_toasts_gone(page)
    s.whole_panel("theme-suggestions")
    button(page, "Apply All Best Placements", exact=False).click()
    page.wait_for_timeout(2500)
    s.full("theme-applied")
    dismiss_toasts(page)
    page.keyboard.press("Escape")

    # --- Word list upload preview (Cancel: nothing is stored) -----------------------------
    tool(page, "Lists")
    button(page, "Upload Wordlist", exact=False).click()
    panel = page.locator(".xw-inspector")
    panel.locator("input[type=text]").first.fill("my words")
    panel.locator("input[type=file]").first.set_input_files(str(FIXTURES / "my-words.txt"))
    panel.get_by_role("button", name="Upload", exact=True).click()
    page.get_by_text("Preview", exact=False).first.wait_for(timeout=10000)
    page.wait_for_timeout(500)
    s.whole_panel("lists-upload-preview")
    panel.get_by_role("button", name="Cancel", exact=True).first.click()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:5077")
    parser.add_argument("--only", nargs="*", help="capture only these image names (the flow still runs)")
    args = parser.parse_args()
    taken = run(args.url, set(args.only) if args.only else None)
    for name in taken:
        print(f"docs/user-guide/images/{name}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
