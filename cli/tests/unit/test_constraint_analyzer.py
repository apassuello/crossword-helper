"""Unit tests for constraint analyzer."""

import pytest
from core.grid import Grid
from core.constraint_analyzer import analyze_constraints, analyze_placement_impact
from fill.word_list import WordList
from fill.trie_pattern_matcher import TriePatternMatcher


@pytest.fixture
def small_wordlist():
    """5-letter and 3-letter words for a 5x5 grid."""
    words = [
        'CAT', 'COT', 'CUT', 'BAT', 'RAT', 'MAT', 'SAT', 'HAT', 'PAT',
        'ACE', 'ARC', 'ARE', 'ATE', 'AWE', 'AXE',
        'TEA', 'TEN', 'TAN', 'TAR',
        'CATCH', 'MATCH', 'BATCH', 'WATCH', 'PATCH',
        'TRACE', 'SPACE', 'PLACE', 'GRACE',
    ]
    return WordList(words)


@pytest.fixture
def pattern_matcher(small_wordlist):
    return TriePatternMatcher(small_wordlist)


class TestAnalyzeConstraints:

    def test_empty_grid_returns_constraints_for_all_white_cells(self, small_wordlist, pattern_matcher):
        """Every white cell in an empty grid should have constraint data."""
        grid = Grid(5, validate_size=False)
        result = analyze_constraints(grid, small_wordlist, pattern_matcher)

        assert 'constraints' in result
        assert 'summary' in result
        # 5x5 grid with no black squares = 25 white cells
        assert result['summary']['total_cells'] == 25

    def test_cell_has_across_and_down_options(self, small_wordlist, pattern_matcher):
        """A cell at a crossing should have both across and down options."""
        grid = Grid(5, validate_size=False)
        result = analyze_constraints(grid, small_wordlist, pattern_matcher)

        # Cell (0,0) is part of across slot (0,0) and down slot (0,0)
        cell_key = "0,0"
        assert cell_key in result['constraints']
        cell = result['constraints'][cell_key]
        assert 'across_options' in cell
        assert 'down_options' in cell
        assert 'min_options' in cell
        assert cell['min_options'] == min(cell['across_options'], cell['down_options'])

    def test_partially_filled_grid_has_fewer_options(self, small_wordlist, pattern_matcher):
        """Filling letters should reduce options for crossing slots."""
        empty_grid = Grid(5, validate_size=False)
        empty_result = analyze_constraints(empty_grid, small_wordlist, pattern_matcher)

        filled_grid = Grid(5, validate_size=False)
        filled_grid.place_word("CAT", 0, 0, "across")
        filled_result = analyze_constraints(filled_grid, small_wordlist, pattern_matcher)

        # Cell (1,0) is in the down slot starting at (0,0).
        # With 'C' placed at (0,0), the down slot pattern changes from "?????" to "C????"
        # which should have fewer matches.
        empty_down = empty_result['constraints'].get('1,0', {}).get('down_options', 0)
        filled_down = filled_result['constraints'].get('1,0', {}).get('down_options', 0)
        assert filled_down <= empty_down

    def test_summary_critical_cells(self, small_wordlist, pattern_matcher):
        """Critical cells count matches cells with min_options < 5."""
        grid = Grid(5, validate_size=False)
        result = analyze_constraints(grid, small_wordlist, pattern_matcher)

        critical_count = sum(
            1 for cell in result['constraints'].values()
            if cell['min_options'] < 5
        )
        assert result['summary']['critical_cells'] == critical_count

    def test_black_square_cells_excluded(self, small_wordlist, pattern_matcher):
        """Black square cells should not appear in constraints."""
        grid = Grid(5, validate_size=False)
        grid.set_black_square(2, 2)  # Center cell
        result = analyze_constraints(grid, small_wordlist, pattern_matcher)

        assert '2,2' not in result['constraints']


class TestAnalyzePlacementImpact:

    def test_placement_returns_crossing_impacts(self, small_wordlist, pattern_matcher):
        """Placing a word should return impact data for crossing slots."""
        grid = Grid(5, validate_size=False)
        slot = {'row': 0, 'col': 0, 'direction': 'across', 'length': 5}
        result = analyze_placement_impact(grid, "CATCH", slot, small_wordlist, pattern_matcher)

        assert 'impacts' in result
        assert 'summary' in result
        assert result['summary']['total_crossings'] > 0

    def test_placement_reduces_or_maintains_options(self, small_wordlist, pattern_matcher):
        """Placing a word should not increase options for crossing slots."""
        grid = Grid(5, validate_size=False)
        slot = {'row': 0, 'col': 0, 'direction': 'across', 'length': 5}
        result = analyze_placement_impact(grid, "CATCH", slot, small_wordlist, pattern_matcher)

        for key, impact in result['impacts'].items():
            assert impact['after'] <= impact['before'], (
                f"Crossing slot {key}: after ({impact['after']}) > before ({impact['before']})"
            )

    def test_impact_keys_use_coordinates(self, small_wordlist, pattern_matcher):
        """Impact keys should be 'row,col,direction' format."""
        grid = Grid(5, validate_size=False)
        slot = {'row': 0, 'col': 0, 'direction': 'across', 'length': 5}
        result = analyze_placement_impact(grid, "CATCH", slot, small_wordlist, pattern_matcher)

        for key in result['impacts']:
            parts = key.split(',')
            assert len(parts) == 3, f"Key '{key}' should be 'row,col,direction'"
            assert parts[2] in ('across', 'down')
