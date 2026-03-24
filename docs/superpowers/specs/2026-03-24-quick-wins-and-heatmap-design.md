# Quick Wins & Crossing Quality Heatmap — Design Spec

**Date:** 2026-03-24
**Scope:** 3 algorithm bug fixes, 1 CLI feature fix, 1 new full-stack feature

---

## Overview

Five workstreams in one plan:

1. **Trie score bound fix** — fix pruning bug in word trie
2. **Backtracking strategy reorder** — try smart strategies before brute-force
3. **Beam timeout scaling** — scale beam phase timeout with grid size
4. **Fix `--theme-entries` CLI flag** — fix canary test + verify locking works
5. **Crossing Quality Heatmap** — full-stack constraint visualization feature

Workstreams 1-4 are independent bug fixes. Workstream 5 is a new feature with three layers (CLI core → backend API → frontend overlay).

---

## Workstream 1: Trie Score Bound Fix

**File:** `cli/src/fill/word_trie.py`

### Problem

Lines 81-82 and 91-92 use a conditional pattern for updating score bounds:

```python
node.min_score = min(node.min_score, word.score) if node.min_score > 0 else word.score
```

This fails when a word with score=0 is added: the `> 0` check causes `min_score` to reset to the next word's score instead of keeping 0. More critically, `min_score` is initialized to 0 in `__init__` (line 29), so the first word always takes the `else` branch — meaning `min_score` can increase if the first word has a high score and a later word has a lower (but > 0) score. This weakens trie pruning.

### Fix

In `TrieNode.__init__` (line 29-30):
```python
self.min_score: float = float('inf')  # Minimum score in subtree (for pruning)
self.max_score: int = 0               # Maximum score in subtree (for pruning)
```

In `add_word()` (lines 81-82 and 91-92), replace both instances with:
```python
node.min_score = min(node.min_score, word.score)
node.max_score = max(node.max_score, word.score)
```

In `_search()` / `find_pattern()`, update any pruning check that compares against `min_score` to handle `float('inf')` as "no words in this subtree" (should already work since `float('inf') >= any_threshold` is always true, meaning empty branches are never pruned — but they also have no children, so no issue).

### Test

Add to `cli/tests/unit/test_word_trie.py`:
- Test that after adding words with scores [100, 50, 1], root `min_score` is 1 and `max_score` is 100
- Test that after adding a single word with score=0, `min_score` is 0
- Test that pruning with `min_score=50` excludes the score=1 word but includes scores 50 and 100

### Verification

```bash
pytest cli/tests/unit/test_word_trie.py -v
```

---

## Workstream 2: Backtracking Strategy Reorder

**File:** `cli/src/fill/beam_search/orchestrator.py`, method `_try_backtracking()` (~line 665)

### Problem

The backtracking strategy order is suboptimal:
1. Try 1: More candidates (2x) — brute force
2. Try 2: Even more candidates (5x) — brute force
3. Try 3: No score filter — brute force
4. Try 4: Conflict-directed backjumping — smart
5. Try 5-7: Chronological backtracking (depth 1/2/3)

The smart strategy (conflict-directed backjumping, Try 4) should be tried first since it targets the actual conflicting slot rather than blindly expanding candidate lists.

### Fix

Reorder the strategy blocks so conflict-directed backjumping (currently Try 4, ~line 707) becomes Try 1. Push 2x/5x/no-filter down to Try 2/3/4. Chronological strategies remain at the end.

**New order:**
1. Conflict-directed backjumping (was Try 4)
2. More candidates 2x (was Try 1)
3. More candidates 5x (was Try 2)
4. No score filter (was Try 3)
5. Chronological depth=1 (was Try 5)
6. Chronological depth=2 (was Try 6)
7. Chronological depth=3 (was Try 7)

This is a pure code block reorder — no logic changes.

### Test

Existing beam search tests must still pass. No new tests needed since this is an ordering optimization, not a behavior change.

### Verification

```bash
pytest cli/tests/ -v -k "beam" --no-header
```

---

## Workstream 3: Beam Timeout Scaling

**File:** `cli/src/fill/hybrid_autofill.py`, line 116

### Problem

The beam search phase timeout is hardcoded to `min(60, ...)`. For 21x21 grids, 60 seconds is too short — the audit showed beam search needs 2+ minutes for meaningful exploration on large grids.

### Fix

Replace line 116:
```python
beam_timeout = min(60, max(10, int(timeout * beam_timeout_ratio)))
```

With grid-size-aware cap:
```python
# Scale beam timeout cap with grid size
size = self.grid.size if hasattr(self.grid, 'size') else self.grid.cells.shape[0]
beam_cap = {11: 30, 13: 45, 15: 60, 17: 90, 21: 120}.get(size, 60)
beam_timeout = min(beam_cap, max(10, int(timeout * beam_timeout_ratio)))
```

For a 21x21 grid with `timeout=300`, beam gets `min(120, max(10, 60)) = 60`. With `timeout=600`, beam gets `min(120, max(10, 120)) = 120`. The cap prevents beam from consuming too much of the overall budget while still giving it meaningful time on large grids.

### Test

Add to `cli/tests/unit/test_hybrid_integration.py`:
- Test that a HybridAutofill with an 11x11 grid uses beam_cap=30
- Test that a HybridAutofill with a 21x21 grid uses beam_cap=120
- Test that the beam timeout doesn't exceed the cap regardless of total timeout

### Verification

```bash
pytest cli/tests/unit/test_hybrid_integration.py -v
```

---

## Workstream 4: Fix `--theme-entries` CLI Flag

### Problem

The `--theme-entries` flag is documented as broken (CLAUDE.md Known Issues), with a canary test that skips. Investigation reveals **two issues**:

1. **Canary test bug:** The test passes a raw JSON string as `--theme-entries`, but the CLI declares it as `click.Path(exists=True)` (line 169 of `cli.py`). Click rejects the argument before the fill command runs, the test finds no JSON output, and calls `pytest.skip`. The test never actually exercises the feature.

2. **The underlying locking may already work:** Both `iterative_repair.py` (line 199) and `beam_search/orchestrator.py` (line 482) call `grid.place_word(word, row, col, direction, lock=True)` when `theme_entries` is provided. The grid's `locked_cells` mechanism prevents overwriting. This was added in commit `f10fa3b` ("fix(autofill): preserve theme-locked cells during autofill").

So the "known broken" status may be outdated — the feature may have been fixed but the canary test never detected it because the test itself is wrong.

### Fix

1. **Fix the canary test** in `test_theme_priority.py`:
   - The test currently passes `json.dumps({"(0,0,across)": "CAT"})` as a raw string to `--theme-entries`, but the CLI declares it as `click.Path(exists=True)` — Click rejects it before fill runs
   - Fix: write the theme entries dict to a `tempfile.NamedTemporaryFile(suffix='.json')` and pass that file path to `--theme-entries`
   - Remove the "KNOWN BROKEN" language from assertions if the test passes

2. **Run the fixed test** to verify theme locking works end-to-end:
   - If it passes: update CLAUDE.md Known Issues to remove this item
   - If it fails: investigate the actual locking failure and fix it

3. **Also fix the `--adaptive` canary test** (`test_adaptive_beam_crash_fix.py`) with the same pattern if applicable.

### Expected outcome

Based on code review, the locking infrastructure is solid. The fix is likely just the test. If the test passes after the fix, we remove the "Known Issue" from CLAUDE.md.

### Verification

```bash
pytest backend/tests/integration/test_theme_priority.py::TestThemeWordCLIIntegration::test_theme_entries_flag_preserves_words -v -m ""
pytest backend/tests/integration/test_adaptive_beam_crash_fix.py -v -m ""
```

---

## Workstream 5: Crossing Quality Heatmap

### Goal

Show constructors how constrained each cell is before running autofill, using a color-coded overlay on the grid. A secondary feature shows how a proposed word placement affects crossing options.

### Layer 1: Constraint Analyzer Core

**New file:** `cli/src/core/constraint_analyzer.py`

#### `analyze_constraints(grid, word_list, pattern_matcher) → dict`

For each white cell, count valid words for the across and down slot passing through it.

**Implementation:**
1. Call `grid.get_word_slots()` to find all slots (across and down entries ≥3 letters)
2. For each slot, call `pattern_matcher.find(slot_pattern)` to count valid words — cache count by slot (a cell references its slot's count, not its own)
3. Build per-cell dict mapping `(row, col)` to `{across_options, down_options, min_options}`
4. Compute summary: `total_cells`, `critical_cells` (min_options < 5), `average_min_options`

**Returns:**
```json
{
  "constraints": {
    "0,1": {"across_options": 234, "down_options": 12, "min_options": 12},
    "0,2": {"across_options": 234, "down_options": 847, "min_options": 234}
  },
  "summary": {
    "total_cells": 189,
    "critical_cells": 5,
    "average_min_options": 156.3
  }
}
```

**Performance:** A 15x15 grid has ~78 slots. With trie pattern matching at ~10ms/call, total is ~800ms. Acceptable for interactive use with debouncing.

#### `analyze_placement_impact(grid, word, slot, word_list, pattern_matcher) → dict`

Compute domain sizes for all crossing slots before and after placing a proposed word.

**Implementation:**
1. Find all slots that cross the target slot (share at least one cell)
2. For each crossing slot: count pattern matches with current grid state (before)
3. Temporarily place the word in a grid clone, recompute crossing patterns, count matches (after)
4. Return before/after/delta per crossing slot

**Returns:**
```json
{
  "impacts": {
    "3-Down": {"before": 847, "after": 12, "delta": -835},
    "5-Down": {"before": 234, "after": 89, "delta": -145}
  },
  "summary": {
    "total_crossings": 5,
    "worst_delta": -835,
    "crossings_eliminated": 0
  }
}
```

**Performance:** ~5-10 pattern matcher calls per word (only crossing slots). Under 100ms.

#### Tests

New file: `cli/tests/unit/test_constraint_analyzer.py`

- Test `analyze_constraints` with a known 5x5 grid: verify cell at a crossing has both across and down options
- Test `analyze_constraints` with a partially filled grid: verify filled slots have fewer options
- Test `analyze_constraints` summary: critical_cells count matches cells with min_options < 5
- Test `analyze_placement_impact`: place a word, verify crossing deltas are correct
- Test `analyze_placement_impact`: verify `after` count ≤ `before` count (placing a word can only reduce or maintain options)
- Test with black squares: cells in black-square-only rows/cols are excluded

### Layer 2: Backend API

#### CLI Command

**File:** `cli/src/cli.py`

New `analyze` command:

```bash
# Grid-wide constraint analysis
python -m cli.src.cli analyze puzzle.json \
  -w data/wordlists/comprehensive.txt --json-output

# Single word placement impact
python -m cli.src.cli analyze puzzle.json \
  -w data/wordlists/comprehensive.txt \
  --word OCEAN --slot "0,0,across,5" --json-output
```

**Options:**
- `grid_file` (argument): Path to grid JSON file
- `-w` / `--wordlists` (multiple): Wordlist files to use
- `--word` (optional): Word to analyze placement for
- `--slot` (optional, requires `--word`): Slot spec as "row,col,direction,length"
- `--json-output`: Output as JSON (default for programmatic use)
- `--algorithm` (optional): Pattern matcher algorithm, default "trie"

When `--word` and `--slot` are provided, calls `analyze_placement_impact()`. Otherwise calls `analyze_constraints()`.

#### API Endpoints

**New file:** `backend/api/constraint_routes.py`

**Blueprint:** `constraint_bp` with url_prefix `/api`

**`POST /api/constraints`** — grid-wide heatmap data
- Request body: `{ "grid": [[...]], "wordlists": ["comprehensive"] }`
- Calls CLI `analyze` via CLIAdapter
- Returns: per-cell constraint data JSON
- Expected response time: ~1s for 15x15 (acceptable with 500ms frontend debounce)

**`POST /api/constraints/impact`** — single word placement impact
- Request body: `{ "grid": [[...]], "word": "OCEAN", "slot": {"row": 0, "col": 0, "direction": "across", "length": 5}, "wordlists": ["comprehensive"] }`
- Calls CLI `analyze --word --slot` via CLIAdapter
- Returns: crossing delta JSON
- Expected response time: ~300ms

#### CLIAdapter

**File:** `backend/core/cli_adapter.py`

Add two methods:
- `analyze_constraints(grid_data, wordlist_paths)` → calls `analyze` command, returns parsed JSON
- `analyze_placement_impact(grid_data, word, slot, wordlist_paths)` → calls `analyze --word --slot`, returns parsed JSON

Both follow the existing CLIAdapter pattern: write grid to temp file, run subprocess, parse JSON stdout.

#### Registration

**File:** `backend/app.py`

Register `constraint_bp` blueprint alongside existing blueprints.

#### Tests

New file: `backend/tests/integration/test_constraint_api.py`
- POST to `/api/constraints` with a 5x5 empty grid → 200, response has `constraints` and `summary` keys
- POST to `/api/constraints/impact` with word + slot → 200, response has `impacts` key
- POST to `/api/constraints` with invalid grid → 400
- POST to `/api/constraints/impact` with missing word → 400

New file: `backend/tests/unit/test_constraint_routes.py`
- Mock CLIAdapter, verify route calls adapter with correct args
- Verify error handling for subprocess failures

### Layer 3: Frontend Overlay

**Files:** `src/components/GridEditor.jsx`, `src/components/GridEditor.scss` (or equivalent style file)

#### Heatmap Toggle

- Add "Show Constraints" toggle button in the grid toolbar
- When active, overlay color-coded backgrounds on white cells:

| Color | Condition | Meaning |
|-------|-----------|---------|
| Red (`#ff4444`, 20% opacity) | `min_options < 5` | Critical — very few fill options |
| Orange (`#ff9900`, 20% opacity) | `min_options` 5–20 | Tight — limited options |
| Yellow (`#ffcc00`, 15% opacity) | `min_options` 20–50 | Moderate — workable |
| Green (`#44bb44`, 10% opacity) | `min_options > 50` | Flexible — many options |

- Fetch from `/api/constraints` when grid changes (debounced, 500ms delay after last change)
- Cache results — only re-fetch when grid cells actually change (not on cursor movement)
- Show cell tooltip on hover: "234 across options, 12 down options"

#### Placement Impact (stretch)

- When user selects a word from PatternMatcher suggestions and is hovering/previewing it:
  - Call `/api/constraints/impact` with the proposed word and target slot
  - Show compact tooltip near the grid with crossing deltas:
    ```
    Placing OCEAN at 1-Across:
      3-Down: 847 → 12
      5-Down: 234 → 89
    ```
  - Color-code deltas: large negative = red text, small = yellow, zero = green
- Debounce requests (300ms) — don't flood API on rapid navigation through suggestions

#### State Management

- Constraint data stored in component state (not global store)
- Loading indicator while fetching (subtle spinner or pulse animation on toggle button)
- Clear constraint data when grid size changes
- Disable toggle during autofill (grid is changing rapidly)

---

## Dependency Order

```
Workstream 1 (trie fix)          ─┐
Workstream 2 (backtrack reorder) ─┤── independent, can parallelize
Workstream 3 (beam timeout)      ─┤
Workstream 4 (theme-entries fix) ─┘

Workstream 5a (constraint analyzer core) ──→ 5b (backend API) ──→ 5c (frontend overlay)
```

Workstreams 1-4 should be done before 5 to establish a clean baseline.

## Verification Checkpoints

**After workstreams 1-4:**
```bash
pytest --no-header -q   # all tests pass, no regressions
```

**After workstream 5a:**
```bash
pytest cli/tests/unit/test_constraint_analyzer.py -v
```

**After workstream 5b:**
```bash
pytest backend/tests/ -v --no-header -q
```

**After workstream 5c:**
```bash
npm run build   # frontend builds without errors
```

**Final:**
```bash
pytest --no-header -q   # full suite green
npm run build            # frontend green
```

---

## Out of Scope

- Test efficiency fixes (separate plan exists at `docs/superpowers/plans/2026-03-23-test-efficiency-fixes.md`)
- Corpus-based scoring (separate feature, can build on this work later)
- Constraint visualization for placement impact in the frontend (included as stretch goal, not required)
- CSP domain restore optimization (HIGH severity from IMPROVEMENTS.md but larger refactor)
- Adaptive autofill dead code fix (related but separate concern)
