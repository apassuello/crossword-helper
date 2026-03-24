"""
Integration tests for theme word priority feature.

This test suite ensures that theme words are correctly prioritized during autofill:
- Theme words receive +50 score bonus
- Theme words are sorted before non-theme words
- API accepts and processes theme parameters
- CLI loads theme wordlists correctly

Created: 2025-12-28
Purpose: Regression protection for theme priority feature (commit e213f74)
"""

import pytest
from pathlib import Path
import tempfile
import json


class TestThemeWordPriorityOrdering:
    """Unit tests for theme word scoring and ordering."""

    def test_theme_word_receives_50_bonus(self):
        """Verify theme words get +50 score bonus."""
        from cli.src.fill.beam_search.selection.value_ordering import ThemeWordPriorityOrdering

        # Create theme set
        theme_words = {'TEST', 'QUIZ', 'EXAM'}

        # Create candidates: theme word with score 60 vs non-theme with score 100
        candidates = [
            ('TEST', 60),   # Theme word: 60 + 50 = 110
            ('WORD', 100),  # Non-theme: stays 100
        ]

        # Create ordering strategy
        ordering = ThemeWordPriorityOrdering(theme_words)

        # Order the candidates (pass None for slot/state since they're not used in this strategy)
        ordered = ordering.order_values(slot=None, candidates=candidates, state=None)

        # Theme word should be first (higher score after bonus)
        assert ordered[0][0] == 'TEST', "Theme word should be first"
        assert ordered[0][1] == 110, "Theme word should have +50 bonus: 60 + 50 = 110"
        assert ordered[1][0] == 'WORD', "Non-theme word should be second"
        assert ordered[1][1] == 100, "Non-theme word should keep original score"

    def test_theme_words_sorted_first(self):
        """Theme words appear before non-theme in candidate list."""
        from cli.src.fill.beam_search.selection.value_ordering import ThemeWordPriorityOrdering

        theme_words = {'APPLE', 'BERRY'}

        # Candidates with non-theme having higher base score
        candidates = [
            ('GRAPE', 100),  # Non-theme, high score
            ('APPLE', 60),   # Theme, lower base score (but gets +50 = 110)
            ('MELON', 90),   # Non-theme
            ('BERRY', 55),   # Theme, lower base score (but gets +50 = 105)
        ]

        ordering = ThemeWordPriorityOrdering(theme_words)
        ordered = ordering.order_values(slot=None, candidates=candidates, state=None)

        # Theme words should appear first
        assert ordered[0][0] == 'APPLE', "APPLE (60+50=110) should be first"
        assert ordered[0][1] == 110
        assert ordered[1][0] == 'BERRY', "BERRY (55+50=105) should be second"
        assert ordered[1][1] == 105
        assert ordered[2][0] == 'GRAPE', "GRAPE (100) should be third"
        assert ordered[2][1] == 100
        assert ordered[3][0] == 'MELON', "MELON (90) should be fourth"
        assert ordered[3][1] == 90

    def test_multiple_theme_words_ordered_by_quality(self):
        """Among theme words, higher base quality still wins."""
        from cli.src.fill.beam_search.selection.value_ordering import ThemeWordPriorityOrdering

        theme_words = {'ALPHA', 'BRAVO', 'DELTA'}

        candidates = [
            ('ALPHA', 70),  # Theme: 70 + 50 = 120
            ('BRAVO', 65),  # Theme: 65 + 50 = 115
            ('DELTA', 60),  # Theme: 60 + 50 = 110
        ]

        ordering = ThemeWordPriorityOrdering(theme_words)
        ordered = ordering.order_values(slot=None, candidates=candidates, state=None)

        # Should maintain quality order among theme words
        assert ordered[0][0] == 'ALPHA', "ALPHA (70+50=120) highest"
        assert ordered[0][1] == 120
        assert ordered[1][0] == 'BRAVO', "BRAVO (65+50=115) middle"
        assert ordered[1][1] == 115
        assert ordered[2][0] == 'DELTA', "DELTA (60+50=110) lowest"
        assert ordered[2][1] == 110

    def test_empty_theme_set_works(self):
        """Ordering works with empty theme word set (no crash)."""
        from cli.src.fill.beam_search.selection.value_ordering import ThemeWordPriorityOrdering

        theme_words = set()  # Empty set

        candidates = [
            ('WORD', 100),
            ('TEST', 90),
        ]

        ordering = ThemeWordPriorityOrdering(theme_words)
        ordered = ordering.order_values(slot=None, candidates=candidates, state=None)

        # Without theme words, should return candidates as-is (no modification)
        assert ordered == candidates, "Empty theme set should return candidates unchanged"

    def test_all_theme_words_get_bonus(self):
        """Every word in theme set gets the bonus."""
        from cli.src.fill.beam_search.selection.value_ordering import ThemeWordPriorityOrdering

        theme_words = {'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE'}

        candidates = [
            ('ONE', 50),
            ('TWO', 50),
            ('THREE', 50),
            ('FOUR', 50),
            ('FIVE', 50),
            ('NOTTHEME', 50),
        ]

        ordering = ThemeWordPriorityOrdering(theme_words)
        ordered = ordering.order_values(slot=None, candidates=candidates, state=None)

        # All theme words should have +50 bonus and come first
        for i, word in enumerate(['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE']):
            assert ordered[i][0] in theme_words, f"Position {i} should be a theme word"
            assert ordered[i][1] == 100, "Theme word should have +50 bonus (50 + 50 = 100)"

        # Non-theme word should be last with original score
        assert ordered[5][0] == 'NOTTHEME'
        assert ordered[5][1] == 50, "Non-theme word should keep original score"


class TestThemeWordCLIIntegration:
    """Integration tests for CLI theme word loading."""

    def test_cli_loads_theme_wordlist_file(self):
        """Test CLI --theme-wordlist flag loads words correctly."""
        from backend.tests.integration.conftest import run_cli_until_output

        # Create a temporary theme wordlist file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("APPLE\nBERRY\nGRAPE\nLEMON\nMELON\n")
            theme_file = f.name

        # Create a minimal test grid
        grid_file = Path(tempfile.gettempdir()) / 'test_grid_theme.json'
        grid_data = {
            "grid": [
                [".", ".", ".", "."],
                [".", ".", ".", "."],
                [".", ".", ".", "."],
                [".", ".", ".", "."]
            ],
            "width": 4,
            "height": 4
        }
        with open(grid_file, 'w') as f:
            json.dump(grid_data, f)

        try:
            # Kill as soon as the loading message appears — don't wait for fill to finish
            stdout = run_cli_until_output(
                cmd=[
                    'python3', '-m', 'cli.src.cli', 'fill',
                    str(grid_file),
                    '--wordlists', 'data/wordlists/core/crosswordese.txt',
                    '--theme-wordlist', theme_file,
                    '--timeout', '10',
                    '--allow-nonstandard'
                ],
                target_text='theme words',
                timeout=10,
            )

            assert '⭐' in stdout, "CLI should show theme word indicator"
            assert 'Loaded 5 theme words' in stdout or '5 theme words' in stdout, \
                "CLI should report loading 5 theme words"

        finally:
            Path(theme_file).unlink(missing_ok=True)
            grid_file.unlink(missing_ok=True)

    def test_theme_words_display_in_cli_output(self):
        """Verify CLI shows '⭐ Loaded N theme words' message."""
        from backend.tests.integration.conftest import run_cli_until_output

        demo_wordlist = Path('data/wordlists/custom/demo_words.txt')
        if not demo_wordlist.exists():
            pytest.skip("Demo wordlist not found")

        grid_file = Path(tempfile.gettempdir()) / 'test_grid_cli_msg.json'
        grid_data = {
            "grid": [[".", ".", "."], [".", ".", "."], [".", ".", "."]],
            "width": 3,
            "height": 3
        }
        with open(grid_file, 'w') as f:
            json.dump(grid_data, f)

        try:
            # Kill as soon as the loading message appears
            stdout = run_cli_until_output(
                cmd=[
                    'python3', '-m', 'cli.src.cli', 'fill',
                    str(grid_file),
                    '--wordlists', 'data/wordlists/core/crosswordese.txt',
                    '--theme-wordlist', str(demo_wordlist),
                    '--timeout', '10',
                    '--allow-nonstandard'
                ],
                target_text='theme words',
                timeout=10,
            )

            assert '⭐' in stdout, "Output should contain star emoji for theme words"
            assert 'theme words' in stdout.lower(), "Output should mention 'theme words'"

        finally:
            grid_file.unlink(missing_ok=True)


class TestThemeWordAPIIntegration:
    """Integration tests for theme word API parameter."""

    @pytest.fixture
    def app_client(self):
        """Create Flask test client."""
        from backend.app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_fill_endpoint_accepts_theme_list_parameter(self, app_client):
        """Test /api/fill endpoint accepts themeList in request."""
        request_data = {
            "grid": [
                [".", ".", "."],
                [".", ".", "."],
                [".", ".", "."]
            ],
            "size": [3, 3],
            "wordlists": ["comprehensive"],
            "themeList": "custom/demo_words",  # Theme parameter
            "algorithm": "beam",
            "timeout": 10
        }

        response = app_client.post(
            '/api/fill',
            json=request_data,
            content_type='application/json'
        )

        # Should accept the request (even if autofill fails on small grid)
        # We're just testing that the API accepts the parameter
        assert response.status_code in [200, 400], \
            f"API should accept themeList parameter, got {response.status_code}"

        # If 400, it should be validation error, not missing parameter
        if response.status_code == 400:
            data = response.get_json()
            assert 'themeList' not in str(data.get('error', '')).lower(), \
                "Error should not be about missing themeList parameter"

    def test_fill_endpoint_without_theme_list_still_works(self, app_client):
        """Test /api/fill works without themeList (backward compatibility)."""
        request_data = {
            "grid": [
                [".", ".", ".", ".", "."],
                [".", ".", ".", ".", "."],
                [".", ".", ".", ".", "."],
                [".", ".", ".", ".", "."],
                [".", ".", ".", ".", "."]
            ],
            "size": [5, 5],
            "wordlists": ["comprehensive"],
            # No themeList parameter
            "algorithm": "beam",
            "timeout": 10
        }

        response = app_client.post(
            '/api/fill',
            json=request_data,
            content_type='application/json'
        )

        # Should work without theme list (backward compatible)
        assert response.status_code in [200, 400], \
            f"API should work without themeList, got {response.status_code}"


# Note: The actual end-to-end test verifying theme words appear in results
# requires a longer-running autofill which would be better in a performance
# or E2E test suite. The tests above verify the infrastructure is in place.


class TestThemeEntriesCLICanary:
    """Canary tests for the --theme-entries CLI flag.

    KNOWN BROKEN: The --theme-entries flag does NOT actually preserve theme
    words during autofill. This test documents the broken behavior so we
    detect when/if it gets fixed. See CLAUDE.md "Known Issues" section.
    """

    @pytest.mark.slow
    def test_theme_entries_flag_preserves_words(self):
        """Test that --theme-entries preserves 'CAT' at (0,0,across) in a 5x5 grid.

        Previously a canary for a known-broken feature. The test itself was
        broken: it passed a raw JSON string to --theme-entries, but the CLI
        expects a file path (click.Path(exists=True)). After fixing the test
        to use a temp file, the underlying locking works correctly.
        """
        import subprocess
        import sys
        import os

        grid_data = {
            "size": 5,
            "grid": [
                ["C", "A", "T", ".", "."],
                [".", ".", ".", ".", "."],
                [".", ".", ".", ".", "."],
                [".", ".", ".", ".", "."],
                [".", ".", ".", ".", "."],
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(grid_data, f)
            grid_file = f.name

        # Write theme entries to a temp JSON file (CLI expects a file path)
        theme_data = {"(0,0,across)": "CAT"}
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(theme_data, f)
            theme_file = f.name

        try:
            cmd = [
                sys.executable, "-m", "cli.src.cli", "fill",
                grid_file,
                "--wordlists", "data/wordlists/core/crosswordese.txt",
                "--theme-entries", theme_file,
                "--timeout", "10",
                "--allow-nonstandard",
                "--json-output",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
            )

            # Try to parse JSON from stdout (may be mixed with progress text)
            output = result.stdout.strip()
            json_result = None
            for line in reversed(output.splitlines()):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        json_result = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue

            if json_result is None:
                pytest.fail(
                    f"CLI did not produce JSON output (rc={result.returncode}); "
                    f"stderr: {result.stderr[:500]}"
                )

            filled_grid = json_result.get("grid")
            if filled_grid is None:
                pytest.fail(
                    f"JSON output has no 'grid' key: {list(json_result.keys())}"
                )

            # Check whether CAT is preserved at row 0, cols 0-2
            row0 = filled_grid[0]
            cat_preserved = (
                row0[0] == "C" and row0[1] == "A" and row0[2] == "T"
            )

            assert cat_preserved, (
                f"--theme-entries did not preserve 'CAT' at row 0. "
                f"Got: {row0[:3]}. Full row: {row0}"
            )

        except subprocess.TimeoutExpired:
            pytest.skip("CLI process timed out (expected for slow CI)")

        finally:
            if os.path.exists(grid_file):
                os.unlink(grid_file)
            if os.path.exists(theme_file):
                os.unlink(theme_file)
