# New Feature Proposals

Feature opportunities for the crossword construction toolkit, with detailed implementation plans for the three prioritized features.

**Last Updated:** March 2026

---

## Table of Contents

1. [Feature Catalog](#1-feature-catalog)
2. [Prioritized Features — Implementation Plans](#2-prioritized-features--implementation-plans)
   - [Crossing Quality Heatmap](#21-crossing-quality-heatmap)
   - [Constraint Visualization](#22-constraint-visualization-real-time-domain-sizes)
   - [Corpus-Based Scoring](#23-corpus-based-scoring)
3. [Verification Plan](#3-verification-plan)
4. [Files Modified Summary](#4-files-modified-summary)

---

## 1. Feature Catalog

### A. Crossing Quality Visualizer (PRIORITIZED)
- Heatmap showing how constrained each cell is (how many words can fill the crossing slot)
- Red = highly constrained (few options), Green = flexible
- Helps constructors identify problem areas before running autofill

### B. Intelligent Word Suggestions
- Given a partial fill, suggest words that maximize options for neighboring slots
- "If you place OCEAN at 1-Across, here's what happens to your crossing options"
- Uses LCV scoring already in codebase, but surfaced to the user

### C. Difficulty Estimator
- Analyze completed puzzle for solver difficulty
- Factors: obscure word count, average word score, crossing patterns, theme complexity
- Output: "Easy / Medium / Hard / Expert" rating

### D. Clue Database Integration
- Import clue databases (public crossword clue/answer databases exist)
- Auto-suggest clues for filled words
- Track "clue freshness" (has this clue been used in NYT recently?)

### E. Corpus-Based Scoring (PRIORITIZED)
- Integrate word frequency data (COCA, Google Ngrams) for familiarity scoring
- Words in top 10k most common English words score higher
- Proper nouns, brand names, slang scored with separate weights

### F. Multi-Wordlist Layering
- Core wordlist + themed overlays + custom user wordlists
- Merge strategies: union, intersection, weighted average
- Per-wordlist score multipliers (themed words get bonus during themed puzzle)

### G. Grid Template Library
- Pre-built grid templates with known-good black square patterns
- Categorized by size, word count, difficulty
- "Start from template" workflow

### H. Undo/Redo for Grid Editing
- Full undo stack for grid operations (place word, add black square, etc.)
- Currently only pause/resume preserves state; no general undo

### I. Constraint Visualization (PRIORITIZED)
- Show which crossing slots are affected by a placement decision
- Visualize domain sizes in real-time during manual construction
- "This placement reduces 3-Down from 847 options to 12"

### J. Improved Adaptive Fill
- Current adaptive_autofill.py has dead code (backtrack tracking not hooked up)
- Should: detect stuck regions → suggest black squares → auto-add → retry fill
- Full pipeline: fill attempt → detect failures → suggest fixes → apply → retry

---

## 2. Prioritized Features — Implementation Plans

### 2.1 Crossing Quality Heatmap

**Goal:** Show constructors how constrained each cell is before running autofill, using a color-coded overlay on the grid.

#### CLI Layer

**New file:** `cli/src/core/constraint_analyzer.py`

```python
def analyze_constraints(grid, word_list, pattern_matcher):
    """
    For each white cell, count valid words for each slot passing through it.

    Returns:
        dict: {(row, col): {
            'across_options': int,   # valid words for the across slot
            'down_options': int,     # valid words for the down slot
            'min_options': int       # min of across/down (bottleneck)
        }}
    """
```

Implementation approach:
- Reuse `grid.get_word_slots()` to find all slots
- For each slot, call `pattern_matcher.find(slot.pattern)` to count valid words
- Map each cell to its across/down slot's candidate count
- Return per-cell constraint data as JSON

#### CLI Command

**File:** `cli/src/cli.py`

Add `analyze` command (or extend `validate`) with `--constraints` flag:
```bash
python -m cli.src.cli analyze puzzle.json --constraints \
  -w data/wordlists/comprehensive.txt --json-output
```

Output format:
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

#### Backend

**New file:** `backend/api/constraint_routes.py`

```python
@constraint_bp.route('/api/constraints', methods=['POST'])
def get_constraints():
    """
    POST /api/constraints
    Body: { "grid": [[...]], "wordlists": ["comprehensive.txt"] }
    Returns: per-cell constraint data
    """
```

Calls CLI `analyze` command via `CLIAdapter`.

#### Frontend

**Files:** `src/components/GridEditor.jsx`, `src/components/GridEditor.scss`

- Add "Show Constraints" toggle button in toolbar
- When active, overlay color-coded backgrounds on cells:
  - **Red** (`#ff4444`): `min_options < 5` — critical constraint
  - **Orange** (`#ff9900`): `min_options 5–10` — tight constraint
  - **Yellow** (`#ffcc00`): `min_options 10–20` — moderate constraint
  - **Green** (`#44bb44`): `min_options > 20` — flexible
- Fetch from `/api/constraints` when grid changes (debounced, 500ms)
- Show tooltip on hover: "234 across options, 12 down options"

#### Testing
- Unit test for `analyze_constraints()` with known 5×5 grid
- Backend integration test calling `/api/constraints`
- Verify: `pytest backend/tests/integration/ -v`

---

### 2.2 Constraint Visualization (Real-time Domain Sizes)

**Goal:** Show how a proposed word placement affects crossing options in real-time.

#### CLI Layer

**File:** `cli/src/core/constraint_analyzer.py` (extends 2.1)

```python
def analyze_placement_impact(grid, word, slot, word_list, pattern_matcher):
    """
    Compute domain sizes for all crossing slots before and after placing word.

    Args:
        grid: Current grid state
        word: Proposed word (e.g., "OCEAN")
        slot: Target slot (row, col, direction, length)
        word_list: Active word list
        pattern_matcher: Pattern matcher instance

    Returns:
        dict: {
            crossing_slot_key: {
                'before': int,    # domain size before placement
                'after': int,     # domain size after placement
                'delta': int,     # change (negative = more constrained)
                'slot_label': str # e.g., "3-Down"
            }
        }
    """
```

Implementation approach:
- Find all slots that cross the target slot
- For each crossing slot: count matches with current pattern (before)
- Temporarily place the word, update crossing patterns, count matches again (after)
- Return before/after/delta for each crossing slot

#### Backend

**File:** `backend/api/constraint_routes.py`

```python
@constraint_bp.route('/api/constraints/impact', methods=['POST'])
def get_placement_impact():
    """
    POST /api/constraints/impact
    Body: {
        "grid": [[...]],
        "word": "OCEAN",
        "slot": {"row": 0, "col": 0, "direction": "across", "length": 5},
        "wordlists": ["comprehensive.txt"]
    }
    Returns: crossing slot impacts
    """
```

#### Frontend

**File:** `src/components/GridEditor.jsx`

- When user selects a word from PatternMatcher suggestions:
  - Call `/api/constraints/impact` with the proposed word
  - Show impact tooltip near the grid:
    ```
    Placing OCEAN at 1-Across:
      3-Down: 847 → 12 (-835)
      5-Down: 234 → 89 (-145)
      7-Down: 456 → 456 (no change)
    ```
  - Color-code deltas: large negative = red, small = yellow, zero = green
- Debounce requests (300ms) to avoid flooding API on rapid navigation

**Depends on:** 2.1 (shared `constraint_analyzer` module)

#### Testing
- Unit test for `analyze_placement_impact` with known grid + word
- Verify crossing slot identification is correct
- Verify: `pytest cli/tests/unit/ -v`

---

### 2.3 Corpus-Based Scoring

**Goal:** Score words based on real-world familiarity, not just letter composition.

#### Data Layer

**New directory:** `data/word_frequency/`

**Approach — Start Simple:**
- Generate initial frequency data from existing wordlists using word rank as proxy
- Format: tab-separated `word\trank`, one per line
- Top words from `comprehensive.txt` get highest ranks
- Future enhancement: integrate COCA (Corpus of Contemporary American English) or Google Ngrams

**File:** `data/word_frequency/english_frequency.tsv`
```
THE	1
OF	2
AND	3
TO	4
...
AREA	847
OCEAN	1234
...
```

#### CLI Layer

**File:** `cli/src/core/scoring.py`

```python
class CorpusScorer:
    """Score words based on corpus frequency data."""

    def __init__(self, frequency_file: str):
        """Load frequency data from TSV file."""
        self._ranks = {}  # word -> rank

    def frequency_bonus(self, word: str) -> int:
        """
        Return bonus points based on word frequency rank.

        Returns:
            int: 0-25 bonus points
                Top 5k:  +25
                Top 10k: +20
                Top 25k: +15
                Top 50k: +10
                Beyond:  +0
        """
        rank = self._ranks.get(word.upper(), float('inf'))
        if rank <= 5000:
            return 25
        elif rank <= 10000:
            return 20
        elif rank <= 25000:
            return 15
        elif rank <= 50000:
            return 10
        return 0
```

Integration into `score_word()`:
```python
def score_word(word: str, corpus_scorer: Optional[CorpusScorer] = None) -> int:
    """Score word quality for crossword fill."""
    score = base_score + length_bonus - penalties

    if corpus_scorer:
        score += corpus_scorer.frequency_bonus(word)

    return max(1, min(175, score))  # Extended range for corpus bonus
```

#### CLI Command

**File:** `cli/src/cli.py`

Add `--corpus-scoring` flag to `fill` and `pattern` commands:
```bash
python -m cli.src.cli fill puzzle.json \
  -w data/wordlists/comprehensive.txt \
  --corpus-scoring \
  --min-score 30

python -m cli.src.cli pattern "C?T" \
  -w data/wordlists/comprehensive.txt \
  --corpus-scoring
```

When flag is set:
- Load `data/word_frequency/english_frequency.tsv`
- Create `CorpusScorer` instance
- Pass to `score_word()` during wordlist loading

#### Backend

**File:** `backend/core/cli_adapter.py`

Pass `--corpus-scoring` flag when calling CLI commands that support it.

#### Testing
- Unit test for `CorpusScorer` with sample frequency data
- Test that known common words (THE, AREA) get bonus
- Test that obscure words get no bonus
- Test backward compatibility: `score_word()` without corpus_scorer still works
- Verify: `pytest cli/tests/unit/ -v`

---

## 3. Verification Plan

After implementing all features:

1. `pytest` — all 165+ tests pass (existing + new)
2. `pytest --cov=backend --cov=cli` — coverage doesn't decrease
3. Manual test: `npm run dev` → open frontend → toggle constraint heatmap → verify color overlay
4. Manual test: hover over word suggestion → verify impact tooltip shows crossing deltas
5. Manual test: `python -m cli.src.cli pattern "C?T" --corpus-scoring --json-output` → verify scores include frequency bonus

---

## 4. Files Modified Summary

| Feature | Files |
|---------|-------|
| 2.1 Heatmap | New `cli/src/core/constraint_analyzer.py`, `cli/src/cli.py`, new `backend/api/constraint_routes.py`, `backend/app.py`, `src/components/GridEditor.jsx`, `src/components/GridEditor.scss` |
| 2.2 Visualization | `cli/src/core/constraint_analyzer.py`, `backend/api/constraint_routes.py`, `src/components/GridEditor.jsx` |
| 2.3 Corpus Scoring | `cli/src/core/scoring.py`, new `data/word_frequency/english_frequency.tsv`, `cli/src/cli.py`, `backend/core/cli_adapter.py` |
