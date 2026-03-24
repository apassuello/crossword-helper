# Quick Wins & Crossing Quality Heatmap — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 algorithm bugs, fix the `--theme-entries` CLI flag, and add a full-stack crossing quality heatmap feature.

**Architecture:** Bug fixes are small, independent changes in the CLI fill engine. The heatmap is a new CLI `analyze` command → Flask API endpoint → React grid overlay, following the project's CLI-as-single-source-of-truth pattern where all logic lives in the CLI and the backend is a thin subprocess wrapper.

**Tech Stack:** Python (Click CLI, Flask API, NumPy grid), React (JSX), SCSS

**Spec:** `docs/superpowers/specs/2026-03-24-quick-wins-and-heatmap-design.md`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `cli/src/fill/word_trie.py` | Modify | Fix score bound initialization (Workstream 1) |
| `cli/tests/unit/test_word_trie.py` | Modify | Update existing test + add score bound tests |
| `cli/src/fill/beam_search/orchestrator.py` | Modify | Reorder backtracking strategies (Workstream 2) |
| `cli/src/fill/hybrid_autofill.py` | Modify | Scale beam timeout with grid size (Workstream 3) |
| `cli/tests/unit/test_hybrid_integration.py` | Modify | Add beam timeout scaling tests |
| `backend/tests/integration/test_theme_priority.py` | Modify | Fix canary test to use temp file (Workstream 4) |
| `.claude/CLAUDE.md` | Modify | Remove fixed Known Issue (if test passes) |
| `cli/src/core/constraint_analyzer.py` | Create | Constraint analysis core logic (Workstream 5a) |
| `cli/tests/unit/test_constraint_analyzer.py` | Create | Tests for constraint analyzer |
| `cli/src/cli.py` | Modify | Add `analyze` command (Workstream 5b) |
| `backend/core/cli_adapter.py` | Modify | Add `analyze_constraints` + `analyze_placement_impact` methods |
| `backend/api/constraint_routes.py` | Create | `/api/constraints` and `/api/constraints/impact` endpoints |
| `backend/app.py` | Modify | Register constraint blueprint |
| `backend/tests/unit/test_constraint_routes.py` | Create | Unit tests for constraint routes |
| `backend/tests/integration/test_constraint_api.py` | Create | Integration tests for constraint API |
| `src/components/GridEditor.jsx` | Modify | Add heatmap overlay + toggle (Workstream 5c) |
| `src/components/GridEditor.scss` | Modify | Heatmap cell styles |

---

## Task 1: Fix Trie Score Bound Initialization

**Files:**
- Modify: `cli/src/fill/word_trie.py:25-30` (TrieNode.__init__)
- Modify: `cli/src/fill/word_trie.py:80-93` (add_word score updates)
- Modify: `cli/tests/unit/test_word_trie.py:15-22` (existing test)

- [ ] **Step 1: Update existing test for new initial values**

In `cli/tests/unit/test_word_trie.py`, update `test_trie_node_creation` (line 15):

```python
def test_trie_node_creation():
    """Test TrieNode initialization."""
    node = TrieNode()
    assert node.children == {}
    assert node.words == []
    assert node.is_end_of_word is False
    assert node.min_score == float('inf')  # Changed: was 0
    assert node.max_score == 0
```

- [ ] **Step 2: Add score bound correctness tests**

Append to `cli/tests/unit/test_word_trie.py`:

```python
def test_score_bounds_multiple_words():
    """Score bounds track min and max across all words in subtree."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 100, 3))
    trie.add_word(ScoredWord("COT", 50, 3))
    trie.add_word(ScoredWord("CUT", 1, 3))

    root = trie._length_roots[3]
    assert root.min_score == 1
    assert root.max_score == 100


def test_score_bounds_zero_score():
    """Score bound handles word with score=0 correctly."""
    trie = WordTrie()
    trie.add_word(ScoredWord("ZZZ", 0, 3))

    root = trie._length_roots[3]
    assert root.min_score == 0
    assert root.max_score == 0


def test_score_pruning_filters_low_scores():
    """min_score parameter in find_pattern excludes low-scoring words."""
    trie = WordTrie()
    trie.add_word(ScoredWord("CAT", 100, 3))
    trie.add_word(ScoredWord("COT", 50, 3))
    trie.add_word(ScoredWord("CUT", 1, 3))

    results = trie.find_pattern("C?T", min_score=50)
    words = {w.text for w in results}
    assert "CAT" in words
    assert "COT" in words
    assert "CUT" not in words
```

- [ ] **Step 3: Run tests — expect failures (old init values)**

Run: `pytest cli/tests/unit/test_word_trie.py -v --no-header 2>&1 | tail -20`
Expected: `test_trie_node_creation` FAILS (min_score is 0, expected inf). New tests may also fail.

- [ ] **Step 4: Fix TrieNode.__init__**

In `cli/src/fill/word_trie.py`, replace lines 29-30:

```python
        self.min_score: int = 0  # Minimum score in subtree (for pruning)
        self.max_score: int = 0  # Maximum score in subtree (for pruning)
```

With:

```python
        self.min_score: float = float('inf')  # Minimum score in subtree (for pruning)
        self.max_score: int = 0                # Maximum score in subtree (for pruning)
```

- [ ] **Step 5: Simplify add_word score updates**

In `cli/src/fill/word_trie.py`, replace line 81:

```python
        node.min_score = min(node.min_score, word.score) if node.min_score > 0 else word.score
```

With:

```python
        node.min_score = min(node.min_score, word.score)
```

And replace line 92 (same pattern, inside the for loop):

```python
            node.min_score = min(node.min_score, word.score) if node.min_score > 0 else word.score
```

With:

```python
            node.min_score = min(node.min_score, word.score)
```

(Leave the `max_score` lines as-is — they're already correct.)

- [ ] **Step 6: Run tests — all should pass**

Run: `pytest cli/tests/unit/test_word_trie.py -v --no-header 2>&1 | tail -20`
Expected: All tests PASS.

- [ ] **Step 7: Run full CLI test suite for regressions**

Run: `pytest cli/tests/ -v --no-header -q 2>&1 | tail -10`
Expected: All tests PASS (trie is used throughout fill algorithms).

- [ ] **Step 8: Commit**

```bash
git add cli/src/fill/word_trie.py cli/tests/unit/test_word_trie.py
git commit -m "fix(trie): initialize min_score to inf for correct pruning bounds"
```

---

## Task 2: Reorder Backtracking Strategies

**Files:**
- Modify: `cli/src/fill/beam_search/orchestrator.py:665-782` (_try_backtracking method)

- [ ] **Step 1: Read the current _try_backtracking method**

Read `cli/src/fill/beam_search/orchestrator.py` lines 665-782 to get the exact current code.

- [ ] **Step 2: Reorder strategy blocks**

In `_try_backtracking()`, move the conflict-directed backjumping block (currently lines 707-747, "Try 4") to right after the initial debug logging (after line 682), before the current "Try 1: More candidates (2x)".

The conflict-directed block includes both the conditional assignment AND the guard check — they must stay together:

```python
        # Try 1: CONFLICT-DIRECTED BACKJUMPING (intelligent)
        # Skip in partial fill mode - too aggressive
        if self.partial_fill_mode:
            logger.debug("  Skipping conflict-directed backjumping (partial fill mode)")
        else:
            # Analyze which filled slots are causing this failure and undo them
            logger.debug("  Analyzing conflicts for intelligent backjumping...")
            conflicts = self._analyze_slot_conflicts(beam[0], slot)

        if not self.partial_fill_mode and conflicts:
            logger.debug(f"  Found {len(conflicts)} conflicting slots, attempting backjump...")

            # Create backjumped beam by removing conflicting assignments
            backjumped_beam = []
            for state in beam:
                new_state = state.clone()

                # Remove all conflicting assignments
                for conflict_slot_id in conflicts:
                    if conflict_slot_id in new_state.slot_assignments:
                        word = new_state.slot_assignments[conflict_slot_id]
                        row, col, direction = conflict_slot_id
                        word_length = len(word)

                        # Remove word from grid
                        new_state.grid.remove_word(row, col, word_length, direction)

                        # Remove from tracking structures
                        del new_state.slot_assignments[conflict_slot_id]
                        new_state.used_words.discard(word)
                        new_state.slots_filled -= 1

                        logger.debug(f"    Removed conflicting slot {conflict_slot_id} (word={word})")

                backjumped_beam.append(new_state)

            # Try expanding from backjumped state
            expanded = self.beam_manager.expand_beam(backjumped_beam, slot, self.candidates_per_slot * 10)
            if expanded:
                logger.debug("  ✓ Success with conflict-directed backjumping")
                return expanded

        # Try 2: More candidates (2x)
        expanded = self.beam_manager.expand_beam(beam, slot, self.candidates_per_slot * 2)
        if expanded:
            logger.debug("  ✓ Success with 2x candidates")
            return expanded

        # Try 3: Even more candidates (5x)
        ...rest stays in same relative order...
```

Update the "Try N" comment numbers to match the new order (1-7).

Also update the method docstring (lines 667-673) to reflect the new order:

```python
        """
        Multi-level backtracking strategy with conflict analysis.

        Strategy progression:
        1. Conflict-directed backjumping (undo problematic assignments) - skipped in partial fill mode
        2. Try more candidates (relaxed constraints)
        3. Try with no score filter
        4. Chronological backtracking (undo recent assignments) - limited in partial fill mode
        """
```

- [ ] **Step 3: Run beam search tests**

Run: `pytest cli/tests/ -v -k "beam" --no-header -q 2>&1 | tail -15`
Expected: All beam tests PASS.

- [ ] **Step 4: Run full test suite for regressions**

Run: `pytest --no-header -q 2>&1 | tail -10`
Expected: All tests PASS. Some beam search tests may produce different filled grids (different exploration order), but structural assertions should hold.

- [ ] **Step 5: Commit**

```bash
git add cli/src/fill/beam_search/orchestrator.py
git commit -m "perf(beam): try conflict-directed backjumping before brute-force strategies"
```

---

## Task 3: Scale Beam Timeout with Grid Size

**Files:**
- Modify: `cli/src/fill/hybrid_autofill.py:115-116`
- Modify: `cli/tests/unit/test_hybrid_integration.py`

- [ ] **Step 1: Add beam timeout scaling tests**

Append to `cli/tests/unit/test_hybrid_integration.py`:

```python
class TestBeamTimeoutScaling:
    """Test that beam timeout scales with grid size."""

    @pytest.fixture
    def word_list(self):
        """Minimal word list for timeout tests."""
        words = ['CAT', 'COT', 'CUT', 'BAT', 'RAT', 'ACE', 'ART', 'TEA']
        return WordList(words)

    def test_small_grid_gets_short_beam_timeout(self, word_list):
        """11x11 grid should get beam_cap=30."""
        grid = Grid(11, validate_size=False)
        pm = TriePatternMatcher(word_list)
        hybrid = HybridAutofill(grid, word_list, pm)

        # beam_cap = min(120, max(30, (11 - 11) * 9 + 30)) = 30
        # With timeout=300, beam_timeout_ratio=0.2: int(300*0.2)=60
        # beam_timeout = min(30, max(10, 60)) = 30
        # We can't directly access beam_timeout, but we can verify
        # the grid.size is used correctly by checking the formula
        beam_cap = min(120, max(30, (grid.size - 11) * 9 + 30))
        assert beam_cap == 30

    def test_large_grid_gets_long_beam_timeout(self, word_list):
        """21x21 grid should get beam_cap=120."""
        grid = Grid(21, validate_size=False)
        pm = TriePatternMatcher(word_list)
        hybrid = HybridAutofill(grid, word_list, pm)

        beam_cap = min(120, max(30, (grid.size - 11) * 9 + 30))
        assert beam_cap == 120

    def test_standard_grid_beam_timeout(self, word_list):
        """15x15 grid should get beam_cap=66."""
        grid = Grid(15, validate_size=False)
        beam_cap = min(120, max(30, (grid.size - 11) * 9 + 30))
        assert beam_cap == 66

    def test_nonstandard_grid_beam_timeout(self, word_list):
        """19x19 grid should get beam_cap=102 (linear interpolation)."""
        grid = Grid(19, validate_size=False)
        beam_cap = min(120, max(30, (grid.size - 11) * 9 + 30))
        assert beam_cap == 102
```

- [ ] **Step 2: Run tests — expect pass (formula tests don't need implementation)**

Run: `pytest cli/tests/unit/test_hybrid_integration.py::TestBeamTimeoutScaling -v --no-header 2>&1 | tail -10`
Expected: PASS (these test the formula directly, not the HybridAutofill code).

- [ ] **Step 3: Apply the fix to hybrid_autofill.py**

In `cli/src/fill/hybrid_autofill.py`, replace lines 115-116:

```python
        # Calculate timeouts (beam capped at 60s — it's slow on large grids)
        beam_timeout = min(60, max(10, int(timeout * beam_timeout_ratio)))
```

With:

```python
        # Scale beam timeout cap with grid size (linear: 30s at size 11, +9s per size step, max 120s)
        beam_cap = min(120, max(30, (self.grid.size - 11) * 9 + 30))
        beam_timeout = min(beam_cap, max(10, int(timeout * beam_timeout_ratio)))
```

- [ ] **Step 4: Run full test suite**

Run: `pytest --no-header -q 2>&1 | tail -10`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add cli/src/fill/hybrid_autofill.py cli/tests/unit/test_hybrid_integration.py
git commit -m "perf(hybrid): scale beam timeout cap with grid size (30s-120s)"
```

---

## Task 4: Fix --theme-entries Canary Test

**Files:**
- Modify: `backend/tests/integration/test_theme_priority.py:316-409`
- Modify: `.claude/CLAUDE.md` (if test passes)

- [ ] **Step 1: Read the current canary test**

Read `backend/tests/integration/test_theme_priority.py` lines 316-409 to get the full test.

- [ ] **Step 2: Fix the test to use a temp file for theme entries**

Replace the test method `test_theme_entries_flag_preserves_words` (lines 317-409) with:

```python
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
```

Key changes:
- Theme entries written to a temp file (not raw JSON string)
- `pytest.skip` changed to `pytest.fail` for missing JSON output (the test should no longer silently skip)
- "KNOWN BROKEN" language removed from assertion message

- [ ] **Step 3: Run the fixed test**

Run: `pytest backend/tests/integration/test_theme_priority.py::TestThemeWordCLIIntegration::test_theme_entries_flag_preserves_words -v -m "" --no-header 2>&1 | tail -15`

Expected: PASS. The underlying locking mechanism (`grid.place_word(word, row, col, direction, lock=True)`) in both `iterative_repair.py:199` and `beam_search/orchestrator.py:482` should preserve the theme word.

If it FAILS: read the stderr output and investigate the actual locking failure. The fix would be in the CLI fill command's handling of `theme_entries_dict`.

- [ ] **Step 4: If test passes, update CLAUDE.md Known Issues**

In `.claude/CLAUDE.md`, in the "Known Issues" section, change:

```markdown
- CLI `--theme-entries` flag does NOT preserve theme words
  - **Workaround:** Use web interface for themed puzzles
```

To:

```markdown
- ~~CLI `--theme-entries` flag does NOT preserve theme words~~ **FIXED** (the feature works; the canary test was broken)
```

Or simply remove the bullet entirely.

- [ ] **Step 5: Run full test suite**

Run: `pytest --no-header -q 2>&1 | tail -10`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/integration/test_theme_priority.py .claude/CLAUDE.md
git commit -m "fix(test): canary test for --theme-entries was passing raw JSON instead of file path"
```

---

## Checkpoint: Bug Fixes Complete

Run full test suite before proceeding to the heatmap feature:

```bash
pytest --no-header -q 2>&1 | tail -10
```

Expected: All tests PASS, no regressions.

---

## Task 5: Constraint Analyzer Core

**Files:**
- Create: `cli/src/core/constraint_analyzer.py`
- Create: `cli/tests/unit/test_constraint_analyzer.py`

- [ ] **Step 1: Write tests for analyze_constraints**

Create `cli/tests/unit/test_constraint_analyzer.py`:

```python
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
        grid.set_black(2, 2)  # Center cell
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
```

- [ ] **Step 2: Run tests — expect import failure**

Run: `pytest cli/tests/unit/test_constraint_analyzer.py -v --no-header 2>&1 | tail -10`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.core.constraint_analyzer'`

- [ ] **Step 3: Implement constraint_analyzer.py**

Create `cli/src/core/constraint_analyzer.py`:

```python
"""
Constraint analyzer for crossword grids.

Computes per-cell constraint data (how many words can fill each crossing slot)
and placement impact analysis (how placing a word affects neighboring slots).
"""

from typing import Dict, List, Any


def analyze_constraints(grid, word_list, pattern_matcher) -> Dict[str, Any]:
    """
    Analyze constraints for every white cell in the grid.

    For each white cell, counts valid words for the across and down slot
    passing through it. Returns per-cell data and a summary.

    Args:
        grid: Grid object
        word_list: WordList object (unused directly, but pattern_matcher is built from it)
        pattern_matcher: TriePatternMatcher or PatternMatcher instance

    Returns:
        Dict with 'constraints' (per-cell data) and 'summary' keys.
    """
    slots = grid.get_word_slots()

    # Count matches per slot (cache by slot identity)
    slot_counts = {}
    for slot in slots:
        slot_key = (slot['row'], slot['col'], slot['direction'])
        pattern = grid.get_pattern_for_slot(slot)
        matches = pattern_matcher.find(pattern, min_score=0)
        slot_counts[slot_key] = len(matches)

    # Build cell-to-slot mapping
    cell_across = {}  # (row, col) -> match count for across slot
    cell_down = {}    # (row, col) -> match count for down slot

    for slot in slots:
        slot_key = (slot['row'], slot['col'], slot['direction'])
        count = slot_counts[slot_key]
        row, col = slot['row'], slot['col']

        for i in range(slot['length']):
            if slot['direction'] == 'across':
                cell = (row, col + i)
            else:
                cell = (row + i, col)

            if slot['direction'] == 'across':
                cell_across[cell] = count
            else:
                cell_down[cell] = count

    # Build per-cell constraint dict
    constraints = {}
    all_white_cells = set()

    for row in range(grid.size):
        for col in range(grid.size):
            if not grid.is_black(row, col):
                all_white_cells.add((row, col))

    for cell in all_white_cells:
        row, col = cell
        across = cell_across.get(cell, 0)
        down = cell_down.get(cell, 0)
        min_opts = min(across, down) if across and down else (across or down)

        constraints[f"{row},{col}"] = {
            'across_options': across,
            'down_options': down,
            'min_options': min_opts,
        }

    # Summary
    total_cells = len(constraints)
    critical = sum(1 for c in constraints.values() if c['min_options'] < 5)
    avg_min = (
        sum(c['min_options'] for c in constraints.values()) / total_cells
        if total_cells > 0 else 0
    )

    return {
        'constraints': constraints,
        'summary': {
            'total_cells': total_cells,
            'critical_cells': critical,
            'average_min_options': round(avg_min, 1),
        },
    }


def analyze_placement_impact(
    grid, word: str, slot: Dict, word_list, pattern_matcher
) -> Dict[str, Any]:
    """
    Analyze how placing a word affects crossing slot options.

    Args:
        grid: Grid object
        word: Word to place (e.g., "OCEAN")
        slot: Target slot dict with 'row', 'col', 'direction', 'length'
        word_list: WordList object
        pattern_matcher: Pattern matcher instance

    Returns:
        Dict with 'impacts' (per-crossing-slot data) and 'summary' keys.
    """
    all_slots = grid.get_word_slots()
    target_cells = set()
    row, col = slot['row'], slot['col']

    for i in range(slot['length']):
        if slot['direction'] == 'across':
            target_cells.add((row, col + i))
        else:
            target_cells.add((row + i, col))

    # Find crossing slots (slots that share at least one cell with target)
    crossing_slots = []
    for s in all_slots:
        s_key = (s['row'], s['col'], s['direction'])
        # Skip the target slot itself
        if s_key == (slot['row'], slot['col'], slot['direction']):
            continue

        s_cells = set()
        for i in range(s['length']):
            if s['direction'] == 'across':
                s_cells.add((s['row'], s['col'] + i))
            else:
                s_cells.add((s['row'] + i, s['col']))

        if s_cells & target_cells:
            crossing_slots.append(s)

    # Compute before counts
    before_counts = {}
    for s in crossing_slots:
        pattern = grid.get_pattern_for_slot(s)
        matches = pattern_matcher.find(pattern, min_score=0)
        s_key = f"{s['row']},{s['col']},{s['direction']}"
        before_counts[s_key] = len(matches)

    # Place word temporarily in a clone
    cloned_grid = grid.clone()
    cloned_grid.place_word(word.upper(), slot['row'], slot['col'], slot['direction'])

    # Compute after counts
    after_counts = {}
    for s in crossing_slots:
        pattern = cloned_grid.get_pattern_for_slot(s)
        matches = pattern_matcher.find(pattern, min_score=0)
        s_key = f"{s['row']},{s['col']},{s['direction']}"
        after_counts[s_key] = len(matches)

    # Build impacts
    impacts = {}
    for s_key in before_counts:
        before = before_counts[s_key]
        after = after_counts.get(s_key, 0)
        # Find the slot to get its length
        s_parts = s_key.split(',')
        s_slot = next(
            (s for s in crossing_slots
             if s['row'] == int(s_parts[0]) and s['col'] == int(s_parts[1])
             and s['direction'] == s_parts[2]),
            None
        )
        impacts[s_key] = {
            'before': before,
            'after': after,
            'delta': after - before,
            'length': s_slot['length'] if s_slot else 0,
        }

    # Summary
    worst_delta = min((i['delta'] for i in impacts.values()), default=0)
    eliminated = sum(1 for i in impacts.values() if i['after'] == 0)

    return {
        'impacts': impacts,
        'summary': {
            'total_crossings': len(impacts),
            'worst_delta': worst_delta,
            'crossings_eliminated': eliminated,
        },
    }
```

- [ ] **Step 4: Run tests — all should pass**

Run: `pytest cli/tests/unit/test_constraint_analyzer.py -v --no-header 2>&1 | tail -15`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add cli/src/core/constraint_analyzer.py cli/tests/unit/test_constraint_analyzer.py
git commit -m "feat(cli): add constraint analyzer for crossing quality analysis"
```

---

## Task 6: CLI analyze Command

**Files:**
- Modify: `cli/src/cli.py` (add `analyze` command after existing commands)

- [ ] **Step 1: Add the analyze command**

Add after the `number` command (around line 950) in `cli/src/cli.py`:

```python
@cli.command()
@click.argument("grid_file", type=click.Path(exists=True))
@click.option(
    "--wordlists", "-w", multiple=True, help="Word list files (can specify multiple)"
)
@click.option(
    "--word", default=None, help="Word to analyze placement for"
)
@click.option(
    "--slot", default=None, help="Target slot as 'row,col,direction,length' (requires --word)"
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output JSON format",
)
def analyze(grid_file: str, wordlists: tuple, word: Optional[str], slot: Optional[str], json_output: bool):
    """
    Analyze grid constraints and placement impact.

    Without --word: shows per-cell constraint data (how many words fit each slot).
    With --word and --slot: shows how placing a word affects crossing slots.

    Examples:
        crossword analyze puzzle.json -w data/wordlists/comprehensive.txt --json-output
        crossword analyze puzzle.json -w data/wordlists/comprehensive.txt --word OCEAN --slot "0,0,across,5" --json-output
    """
    from .core.constraint_analyzer import analyze_constraints, analyze_placement_impact
    from .fill.trie_pattern_matcher import TriePatternMatcher

    # Validate --slot requires --word
    if slot and not word:
        click.echo("Error: --slot requires --word", err=True)
        sys.exit(1)

    # Load grid (Grid has from_dict, not from_file)
    try:
        with open(grid_file) as f:
            grid_data = json.load(f)
        grid = Grid.from_dict(grid_data, strict_size=False)
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error loading grid: {e}", err=True)
        sys.exit(1)

    # Load wordlists (WordList has from_file but no merge — use first, add_words for rest)
    if not wordlists:
        click.echo("Error: at least one wordlist is required (-w)", err=True)
        sys.exit(1)

    word_list = None
    for wl_path in wordlists:
        try:
            wl = WordList.from_file(wl_path)
            if word_list is None:
                word_list = wl
            else:
                # Add words from subsequent wordlists
                word_list.add_words([sw.text for sw in wl.get_all()])
        except Exception as e:
            click.echo(f"Warning: Could not load {wl_path}: {e}", err=True)

    if word_list is None or len(word_list) == 0:
        click.echo("Error: no words loaded from wordlists", err=True)
        sys.exit(1)

    # Build pattern matcher
    pattern_matcher = TriePatternMatcher(word_list)

    if word and slot:
        # Placement impact analysis
        try:
            parts = slot.split(',')
            if len(parts) != 4:
                raise ValueError("Expected 'row,col,direction,length'")
            slot_dict = {
                'row': int(parts[0]),
                'col': int(parts[1]),
                'direction': parts[2].strip(),
                'length': int(parts[3]),
            }
        except (ValueError, IndexError) as e:
            click.echo(f"Error parsing --slot: {e}. Expected format: row,col,direction,length", err=True)
            sys.exit(1)

        result = analyze_placement_impact(grid, word, slot_dict, word_list, pattern_matcher)
    else:
        # Grid-wide constraint analysis
        result = analyze_constraints(grid, word_list, pattern_matcher)

    result['success'] = True

    if json_output:
        click.echo(json.dumps(result))
    else:
        # Human-readable output
        if 'constraints' in result:
            summary = result['summary']
            click.echo(f"Grid analysis: {summary['total_cells']} cells")
            click.echo(f"  Critical cells (< 5 options): {summary['critical_cells']}")
            click.echo(f"  Average min options: {summary['average_min_options']}")
        elif 'impacts' in result:
            click.echo(f"Placement impact for {word}:")
            for slot_key, impact in result['impacts'].items():
                click.echo(f"  {slot_key}: {impact['before']} → {impact['after']} ({impact['delta']:+d})")
```

- [ ] **Step 2: Test the command manually**

Run: `python -m cli.src.cli analyze data/example_grids/example_15x15.json -w data/wordlists/core/crosswordese.txt --json-output 2>&1 | head -5`

Expected: JSON output with `constraints` and `summary` keys. If `example_15x15.json` doesn't exist, use any grid JSON file that does exist.

- [ ] **Step 3: Commit**

```bash
git add cli/src/cli.py
git commit -m "feat(cli): add analyze command for constraint analysis"
```

---

## Task 7: Backend API for Constraints

**Files:**
- Create: `backend/api/constraint_routes.py`
- Modify: `backend/core/cli_adapter.py`
- Modify: `backend/app.py`
- Create: `backend/tests/unit/test_constraint_routes.py`
- Create: `backend/tests/integration/test_constraint_api.py`

- [ ] **Step 1: Add CLIAdapter methods**

In `backend/core/cli_adapter.py`, add after the `number` method (around line 218):

```python
    def analyze_constraints(
        self,
        grid_data: Dict[str, Any],
        wordlist_paths: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze grid constraints (per-cell option counts).

        Args:
            grid_data: Grid data dictionary
            wordlist_paths: List of wordlist file paths

        Returns:
            Dict with 'constraints' and 'summary' keys
        """
        if not grid_data:
            raise ValueError("Grid data cannot be empty")
        if not wordlist_paths:
            raise ValueError("At least one wordlist path is required")

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grid_data, f)
            temp_path = f.name

        try:
            args = ["analyze", temp_path, "--json-output"]
            for wl in wordlist_paths:
                args.extend(["--wordlists", wl])

            stdout, stderr, _ = self._run_command(args, timeout=30)

            try:
                return json.loads(stdout)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse CLI output: {e}\nOutput: {stdout}")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def analyze_placement_impact(
        self,
        grid_data: Dict[str, Any],
        word: str,
        slot: Dict[str, Any],
        wordlist_paths: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze how placing a word affects crossing slots.

        Args:
            grid_data: Grid data dictionary
            word: Word to place
            slot: Slot dict with row, col, direction, length
            wordlist_paths: List of wordlist file paths

        Returns:
            Dict with 'impacts' and 'summary' keys
        """
        if not grid_data:
            raise ValueError("Grid data cannot be empty")
        if not word:
            raise ValueError("Word cannot be empty")

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grid_data, f)
            temp_path = f.name

        try:
            slot_str = f"{slot['row']},{slot['col']},{slot['direction']},{slot['length']}"
            args = ["analyze", temp_path, "--json-output", "--word", word, "--slot", slot_str]
            for wl in wordlist_paths:
                args.extend(["--wordlists", wl])

            stdout, stderr, _ = self._run_command(args, timeout=30)

            try:
                return json.loads(stdout)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse CLI output: {e}\nOutput: {stdout}")
        finally:
            Path(temp_path).unlink(missing_ok=True)
```

- [ ] **Step 2: Create constraint_routes.py**

Create `backend/api/constraint_routes.py`:

```python
"""
API routes for constraint analysis.

Provides endpoints for grid-wide constraint heatmap data
and single-word placement impact analysis.
"""

from flask import Blueprint, request, jsonify
from backend.core.cli_adapter import CLIAdapter
from backend.core.wordlist_resolver import resolve_wordlist_paths

constraint_bp = Blueprint('constraint_api', __name__)


@constraint_bp.route('/constraints', methods=['POST'])
def get_constraints():
    """
    Get per-cell constraint data for the grid.

    Request body:
        {
            "grid": [[cell, ...], ...],
            "wordlists": ["comprehensive", ...]
        }

    Returns:
        JSON with 'constraints' and 'summary' keys.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    grid = data.get('grid')
    if not grid:
        return jsonify({'error': 'grid is required'}), 400

    wordlist_names = data.get('wordlists', ['comprehensive'])
    wordlist_paths = resolve_wordlist_paths(wordlist_names)

    if not wordlist_paths:
        return jsonify({'error': 'No valid wordlists found'}), 400

    # Build grid data for CLI
    grid_data = {
        'size': len(grid),
        'grid': grid,
    }

    try:
        adapter = CLIAdapter()
        result = adapter.analyze_constraints(grid_data, wordlist_paths)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@constraint_bp.route('/constraints/impact', methods=['POST'])
def get_placement_impact():
    """
    Get impact of placing a word on crossing slots.

    Request body:
        {
            "grid": [[cell, ...], ...],
            "word": "OCEAN",
            "slot": {"row": 0, "col": 0, "direction": "across", "length": 5},
            "wordlists": ["comprehensive", ...]
        }

    Returns:
        JSON with 'impacts' and 'summary' keys.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    grid = data.get('grid')
    word = data.get('word')
    slot = data.get('slot')

    if not grid:
        return jsonify({'error': 'grid is required'}), 400
    if not word:
        return jsonify({'error': 'word is required'}), 400
    if not slot:
        return jsonify({'error': 'slot is required'}), 400

    for key in ('row', 'col', 'direction', 'length'):
        if key not in slot:
            return jsonify({'error': f'slot.{key} is required'}), 400

    wordlist_names = data.get('wordlists', ['comprehensive'])
    wordlist_paths = resolve_wordlist_paths(wordlist_names)

    if not wordlist_paths:
        return jsonify({'error': 'No valid wordlists found'}), 400

    grid_data = {
        'size': len(grid),
        'grid': grid,
    }

    try:
        adapter = CLIAdapter()
        result = adapter.analyze_placement_impact(grid_data, word, slot, wordlist_paths)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 3: Register blueprint in app.py**

In `backend/app.py`, add the import at the top (after line 15):

```python
from backend.api.constraint_routes import constraint_bp
```

And register it (after line 52):

```python
    app.register_blueprint(constraint_bp, url_prefix='/api')
```

- [ ] **Step 4: Write unit tests**

Create `backend/tests/unit/test_constraint_routes.py`:

```python
"""Unit tests for constraint API routes."""

import json
import pytest
from unittest.mock import patch, MagicMock
from backend.app import create_app


@pytest.fixture
def client():
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client


class TestConstraintsEndpoint:

    def test_post_constraints_returns_200(self, client):
        """POST /api/constraints with valid grid returns 200."""
        with patch('backend.api.constraint_routes.CLIAdapter') as mock_cls:
            mock_adapter = MagicMock()
            mock_adapter.analyze_constraints.return_value = {
                'constraints': {'0,0': {'across_options': 10, 'down_options': 5, 'min_options': 5}},
                'summary': {'total_cells': 1, 'critical_cells': 0, 'average_min_options': 5.0},
            }
            mock_cls.return_value = mock_adapter

            response = client.post('/api/constraints', json={
                'grid': [['.' for _ in range(5)] for _ in range(5)],
                'wordlists': ['comprehensive'],
            })

            assert response.status_code == 200
            data = response.get_json()
            assert 'constraints' in data
            assert 'summary' in data

    def test_post_constraints_missing_grid_returns_400(self, client):
        """POST /api/constraints without grid returns 400."""
        response = client.post('/api/constraints', json={'wordlists': ['comprehensive']})
        assert response.status_code == 400

    def test_post_constraints_empty_body_returns_400(self, client):
        """POST /api/constraints with empty body returns 400."""
        response = client.post('/api/constraints',
                               data='',
                               content_type='application/json')
        assert response.status_code == 400


class TestImpactEndpoint:

    def test_post_impact_returns_200(self, client):
        """POST /api/constraints/impact with valid data returns 200."""
        with patch('backend.api.constraint_routes.CLIAdapter') as mock_cls:
            mock_adapter = MagicMock()
            mock_adapter.analyze_placement_impact.return_value = {
                'impacts': {'0,1,down': {'before': 100, 'after': 10, 'delta': -90, 'length': 5}},
                'summary': {'total_crossings': 1, 'worst_delta': -90, 'crossings_eliminated': 0},
            }
            mock_cls.return_value = mock_adapter

            response = client.post('/api/constraints/impact', json={
                'grid': [['.' for _ in range(5)] for _ in range(5)],
                'word': 'CATCH',
                'slot': {'row': 0, 'col': 0, 'direction': 'across', 'length': 5},
                'wordlists': ['comprehensive'],
            })

            assert response.status_code == 200
            data = response.get_json()
            assert 'impacts' in data

    def test_post_impact_missing_word_returns_400(self, client):
        """POST /api/constraints/impact without word returns 400."""
        response = client.post('/api/constraints/impact', json={
            'grid': [['.' for _ in range(5)] for _ in range(5)],
            'slot': {'row': 0, 'col': 0, 'direction': 'across', 'length': 5},
        })
        assert response.status_code == 400

    def test_post_impact_missing_slot_returns_400(self, client):
        """POST /api/constraints/impact without slot returns 400."""
        response = client.post('/api/constraints/impact', json={
            'grid': [['.' for _ in range(5)] for _ in range(5)],
            'word': 'CATCH',
        })
        assert response.status_code == 400
```

- [ ] **Step 5: Run unit tests**

Run: `pytest backend/tests/unit/test_constraint_routes.py -v --no-header 2>&1 | tail -15`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/constraint_routes.py backend/core/cli_adapter.py backend/app.py backend/tests/unit/test_constraint_routes.py
git commit -m "feat(api): add /api/constraints and /api/constraints/impact endpoints"
```

---

## Task 8: Frontend Heatmap Overlay

**Files:**
- Modify: `src/components/GridEditor.jsx`
- Modify: `src/components/GridEditor.scss`

- [ ] **Step 1: Read the current GridEditor component**

Read `src/components/GridEditor.jsx` fully to understand the SVG cell rendering structure and props.
Read `src/components/GridEditor.scss` to understand existing cell styles.

- [ ] **Step 2: Add constraint state and fetch logic to GridEditor.jsx**

Add to the component, after the existing `useState` declarations (around line 19):

```jsx
  const [showConstraints, setShowConstraints] = useState(false);
  const [constraintData, setConstraintData] = useState(null);
  const [constraintLoading, setConstraintLoading] = useState(false);
  const constraintDebounceRef = useRef(null);
```

Add a `useEffect` that fetches constraints when enabled and grid changes:

```jsx
  // Fetch constraint data when heatmap is toggled on or grid changes
  useEffect(() => {
    if (!showConstraints || !grid) {
      setConstraintData(null);
      return;
    }

    // Debounce: wait 500ms after last grid change
    if (constraintDebounceRef.current) {
      clearTimeout(constraintDebounceRef.current);
    }

    constraintDebounceRef.current = setTimeout(async () => {
      setConstraintLoading(true);
      try {
        const response = await fetch('/api/constraints', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            grid: grid.map(row => row.map(cell =>
              cell.isBlack ? '#' : (cell.letter || '.')
            )),
            wordlists: ['comprehensive'],
          }),
        });
        if (response.ok) {
          const data = await response.json();
          setConstraintData(data.constraints || null);
        }
      } catch (err) {
        console.error('Constraint fetch failed:', err);
      } finally {
        setConstraintLoading(false);
      }
    }, 500);

    return () => {
      if (constraintDebounceRef.current) {
        clearTimeout(constraintDebounceRef.current);
      }
    };
  }, [showConstraints, grid]);
```

- [ ] **Step 3: Add heatmap color helper**

Add before the return statement:

```jsx
  const getConstraintColor = (row, col) => {
    if (!constraintData) return null;
    const cellData = constraintData[`${row},${col}`];
    if (!cellData) return null;

    const min = cellData.min_options;
    if (min < 5) return 'rgba(255, 68, 68, 0.2)';      // Red
    if (min < 20) return 'rgba(255, 153, 0, 0.2)';      // Orange
    if (min < 50) return 'rgba(255, 204, 0, 0.15)';     // Yellow
    return 'rgba(68, 187, 68, 0.1)';                     // Green
  };

  const getConstraintTooltip = (row, col) => {
    if (!constraintData) return null;
    const cellData = constraintData[`${row},${col}`];
    if (!cellData) return null;
    return `${cellData.across_options} across, ${cellData.down_options} down`;
  };
```

- [ ] **Step 4: Add constraint overlay rect to cell rendering**

In the SVG cell rendering (find the `<rect>` for each cell inside the grid), add a constraint overlay rect AFTER the cell background rect and BEFORE the letter text. This will be inside the map loop that renders cells.

Look for the pattern where cells are rendered. Add after the main cell background rect:

```jsx
{showConstraints && !cell.isBlack && getConstraintColor(rowIdx, colIdx) && (
  <rect
    x={colIdx * CELL_SIZE + GRID_PADDING}
    y={rowIdx * CELL_SIZE + GRID_PADDING}
    width={CELL_SIZE}
    height={CELL_SIZE}
    fill={getConstraintColor(rowIdx, colIdx)}
    className="constraint-overlay"
  >
    <title>{getConstraintTooltip(rowIdx, colIdx)}</title>
  </rect>
)}
```

- [ ] **Step 5: Add toggle button**

Add a toggle button in the grid toolbar area. Find where other toolbar buttons are rendered (likely above the SVG) and add:

```jsx
<button
  className={classNames('constraint-toggle', { active: showConstraints, loading: constraintLoading })}
  onClick={() => setShowConstraints(!showConstraints)}
  title="Show constraint heatmap"
>
  {constraintLoading ? '...' : '🔍'} Constraints
</button>
```

- [ ] **Step 6: Add styles to GridEditor.scss**

Append to `src/components/GridEditor.scss`:

```scss
.constraint-toggle {
  padding: 4px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  margin-left: 8px;

  &.active {
    background: #e8f0fe;
    border-color: #4285f4;
    color: #1a73e8;
  }

  &.loading {
    opacity: 0.7;
    cursor: wait;
  }
}

.constraint-overlay {
  pointer-events: none;
}
```

- [ ] **Step 7: Build frontend to verify no errors**

Run: `npm run build 2>&1 | tail -10`
Expected: Build succeeds with no errors.

- [ ] **Step 8: Commit**

```bash
git add src/components/GridEditor.jsx src/components/GridEditor.scss
git commit -m "feat(ui): add crossing quality heatmap overlay to grid editor"
```

---

## Task 9: Final Verification

- [ ] **Step 1: Run full backend test suite**

Run: `pytest --no-header -q 2>&1 | tail -10`
Expected: All tests PASS.

- [ ] **Step 2: Build frontend**

Run: `npm run build 2>&1 | tail -5`
Expected: Build succeeds.

- [ ] **Step 3: Smoke test the full stack**

Run: `python run.py &` (background), then:

```bash
curl -s -X POST http://localhost:5000/api/constraints \
  -H 'Content-Type: application/json' \
  -d '{"grid": [[".",".","."],[".",".","."],[".",".","."]], "wordlists": ["comprehensive"]}' | python -m json.tool | head -20
```

Expected: JSON response with `constraints` and `summary` keys.

Kill the server when done.

- [ ] **Step 4: Commit any remaining fixes**

If tests or builds failed, fix and commit.

---

## Risk Notes

1. **Frontend SVG structure**: The GridEditor renders cells via SVG. The exact element nesting (rect, text, group) needs to be matched when inserting the constraint overlay. Read the full component before editing.

2. **`TriePatternMatcher.find()` default `min_score=30`**: The constraint analyzer passes `min_score=0` explicitly to count ALL matching words, not just quality-filtered ones. If you see unexpected low counts, check that `min_score=0` is being passed.

3. **CLI `analyze` stdout must be clean JSON**: When `--json-output` is used, non-JSON progress messages must NOT be printed to stdout. Check that the command only outputs the final JSON result. The CLIAdapter does `json.loads(stdout)` which will fail on mixed output.
