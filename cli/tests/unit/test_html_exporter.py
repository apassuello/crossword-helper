"""
Unit tests for HTML exporter.

Regression tests for the template-interpolation bug where the page header
was never .format()-ed, leaving literal '{title}' and invalid '{{...}}' CSS
in the exported HTML.
"""

import pytest
from src.core.grid import Grid
from src.export.html_exporter import HTMLExporter


@pytest.fixture
def grid():
    """A simple 11x11 grid with some letters and black squares."""
    g = Grid(11)
    g.set_black_square(0, 3)  # symmetric partner (10, 7) added automatically
    g.set_letter(0, 0, "C")
    g.set_letter(0, 1, "A")
    g.set_letter(0, 2, "T")
    return g


class TestHTMLExporterTemplate:
    """Test that the HTML template is fully interpolated."""

    def test_title_is_interpolated(self, grid):
        """The --title value must appear in <title> and <h1>."""
        html = HTMLExporter.export(grid, title="My Puzzle")

        assert "<title>My Puzzle</title>" in html
        assert "<h1>My Puzzle</h1>" in html

    def test_no_literal_placeholders_remain(self, grid):
        """Regression: output must not contain un-formatted placeholders."""
        html = HTMLExporter.export(grid, title="My Puzzle")

        assert "{title}" not in html
        assert "{grid.size}" not in html
        assert "{{" not in html
        assert "}}" not in html

    def test_css_uses_grid_size(self, grid):
        """The CSS grid template must use the actual grid size."""
        html = HTMLExporter.export(grid, title="My Puzzle")

        assert "repeat(11, 40px)" in html
        assert "repeat(11, 30px)" in html  # print stylesheet

    def test_default_title(self, grid):
        """Default title is used when none is given."""
        html = HTMLExporter.export(grid)

        assert "<title>Crossword Puzzle</title>" in html

    def test_title_is_html_escaped(self, grid):
        """HTML-special characters in the title must be escaped."""
        html = HTMLExporter.export(grid, title="Cats & <Dogs>")

        assert "Cats &amp; &lt;Dogs&gt;" in html
        assert "<Dogs>" not in html


class TestHTMLExporterContent:
    """Test that grid content still renders correctly."""

    def test_black_cells_rendered(self, grid):
        """Black squares appear as .cell.black divs."""
        html = HTMLExporter.export(grid)

        assert html.count('<div class="cell black"></div>') == 2  # (0,3) + (10,7)

    def test_letters_rendered(self, grid):
        """Filled letters appear as cell-letter spans."""
        html = HTMLExporter.export(grid)

        assert '<span class="cell-letter">C</span>' in html
        assert '<span class="cell-letter">A</span>' in html
        assert '<span class="cell-letter">T</span>' in html

    def test_export_to_file(self, grid, tmp_path):
        """export_to_file writes the same interpolated HTML."""
        out = tmp_path / "puzzle.html"
        HTMLExporter.export_to_file(grid, str(out), title="File Test")

        content = out.read_text(encoding="utf-8")
        assert "<title>File Test</title>" in content
        assert "{title}" not in content
        assert "{{" not in content
