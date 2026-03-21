# Identified Issues & Improvements

A comprehensive audit of algorithm bugs, scoring gaps, validation weaknesses, and component issues across the crossword construction toolkit.

**Last Updated:** March 2026

---

## Table of Contents

1. [Algorithm Weaknesses](#1-algorithm-weaknesses)
2. [Scoring & Word Quality Gaps](#2-scoring--word-quality-gaps)
3. [Validation Gaps](#3-validation-gaps)
4. [Theme Placer & Black Square Suggester Gaps](#4-theme-placer--black-square-suggester-gaps)
5. [Multi-Wordlist Support Gap](#5-multi-wordlist-support-gap)
6. [Implementation Plan](#6-implementation-plan)

---

## 1. Algorithm Weaknesses

### HIGH Severity

| Issue | Location | Impact |
|-------|----------|--------|
| **CSP domain restore copies everything** | `autofill.py:972,993` | Memory bloat on large grids; should use incremental restore or trail-based undo |
| **No conflict learning / nogoods** | `autofill.py:853-999` | CSP re-explores failed assignments; backjump learning would skip proven dead ends |
| **Stale beam signature only uses 1st state** | `orchestrator.py:187-206` | Retries beams that look identical but aren't; wastes iterations |
| **Risk assessment not tree-wide** | `state_evaluator.py:147-165` | Commits to paths that cascade into dead ends 2+ levels deep |
| **Adaptive autofill backtrack tracking dead code** | `adaptive_autofill.py:118-119` | `on_backtrack` callback never implemented in Autofill/BeamSearch; adaptation tracking non-functional |

### MEDIUM Severity

| Issue | Location | Impact |
|-------|----------|--------|
| **Beam timeout capped at 60s** | `hybrid_autofill.py:116` | Too short for 21×21 grids needing 2+ minutes of beam exploration |
| **Hardcoded stratified offset (=2)** | `orchestrator.py:140` | Low diversity when domains are small |
| **Diversity not normalized by crossing count** | `diversity.py:121-123` | Words with 1 crossing get same diversity penalty as words with 10 |
| **Repair CSP ignores beam's domain state** | `iterative_repair.py:538-599` | Duplicates constraint work; should inherit pruned domains |
| **Tabu tenure formula arbitrary** | `iterative_repair.py:407` | `√(num_slots)` — no adaptive tuning based on search progress |
| **Backtracking strategies in wrong order** | `orchestrator.py:684-746` | Tries brute-force (2×, 5×) before conflict analysis; should try smart strategy first |

### LOW Severity

| Issue | Location | Impact |
|-------|----------|--------|
| **LCV ignores bigrams** | `autofill.py:465-497` | Suboptimal value ordering; QU always co-occurs but scored independently |
| **Partial fill gentle backtrack depth=1 hardcoded** | `orchestrator.py:382-401` | Should scale with fill ratio |

---

## 2. Scoring & Word Quality Gaps

### Current Limitations

**Files:** `cli/src/core/scoring.py`, `cli/src/fill/word_list.py`

| Gap | Impact | Difficulty |
|-----|--------|------------|
| **No bigram/trigram analysis** | Words with impossible letter combos (QZXRT) not penalized | Medium |
| **No vowel distribution check** | All-consonant or all-vowel words pass | Low |
| **No consonant clustering penalty** | Runs like STRPHLNG not flagged | Low |
| **No corpus frequency weighting** | Obscure words score same as common ones | High (needs external data) |
| **No clueability metric** | Can't distinguish "easy to clue" from "impossible to clue" | High |
| **Adjacent repeat penalty but no position awareness** | Repeated letters at edges (more constraining for crossings) treated same as middle | Low |
| **Trie score bound logic bug** | `word_trie.py:80-93` — min_score can increase incorrectly, weakening pruning | Low (easy fix) |

### Suggested Improvements

1. **Bigram scoring** — Add `COMMON_BIGRAMS = {'TH': 80, 'HE': 75, 'IN': 70, ...}` bonus
2. **Vowel ratio check** — Penalize <20% or >65% vowels
3. **Consonant cluster limit** — Penalize >3 consecutive consonants
4. **Fix trie score bounds** — Initialize to infinity, use simple min/max
5. **Cache algorithm versioning** — Track scoring version in `.pkl` metadata for auto-invalidation

---

## 3. Validation Gaps

**File:** `cli/src/core/validator.py`

Missing checks that professional constructors need:

| Missing Validation | Why It Matters |
|-------------------|----------------|
| **Word repetition count** | No word should appear >1–2 times in a puzzle |
| **Across/down balance** | Professional puzzles aim for roughly equal across vs down counts |
| **Theme word symmetry** | Theme entries should be symmetrically placed |
| **Crossing quality analysis** | Some intersections force uncommon letter combos (Q-Z crossing) |
| **Unchecked square count** | Cells only in one word are "unchecked" — too many is bad |

---

## 4. Theme Placer & Black Square Suggester Gaps

### Theme Placer (`backend/core/theme_placer.py`)

- **No constraint propagation preview** — Places theme words without checking if grid becomes unfillable
- **Scoring weights arbitrary** — Symmetry (20), position (15), spacing (10) not empirically validated
- **No "will autofill work?" prediction** before returning suggestions

### Black Square Suggester (`backend/core/black_square_suggester.py`)

- **6-letter minimum hardcoded** (line 95) — should be configurable
- **Word count ranges lack sources** — (72,78) for 15×15, but no citation for where these come from
- **No grid-wide impact analysis** — evaluates each suggestion in isolation, doesn't check cascading effects
- **Constraint reduction formula oversimplified** (lines 311–314) — `length² - (left² + right²)` ignores actual crossing patterns

---

## 5. Multi-Wordlist Support Gap

**File:** `cli/src/fill/word_list.py`

- No mechanism to merge multiple wordlists intelligently
- If user loads `comprehensive.txt` + `themed/sports.txt`, duplicates handled by simple set dedup
- No "take higher score" or "average scores" merge strategy
- Cache doesn't track which wordlists contributed to a merged result

---

## 6. Implementation Plan

### Phase 1: Bug Fixes (5 items)

#### 1.1 Fix Trie Score Bound Logic
**File:** `cli/src/fill/word_trie.py` (lines 80–93)
**Change:** Replace conditional initialization with proper infinity-based init:
- In `TrieNode.__init__`: set `min_score = float('inf')`, `max_score = 0`
- In `add_word()`: simplify to `node.min_score = min(node.min_score, word.score)` and `node.max_score = max(node.max_score, word.score)`
- In `_search()` pruning check: update to handle `float('inf')` as unvisited
**Test:** `cli/tests/unit/test_word_trie.py` — add test that score bounds are correct after adding words with score=1 and score=100
**Verify:** `pytest cli/tests/unit/test_word_trie.py -v`

#### 1.2 Fix Stale Beam Signature
**File:** `cli/src/fill/beam_search/orchestrator.py` (lines 187–206)
**Change:** Hash top-3 beam states (or all if beam_width ≤ 3) instead of just first:
```python
assignments = frozenset()
for state in beam[:3]:
    assignments |= frozenset(state.slot_assignments.items())
return hash(assignments)
```
**Test:** `cli/tests/unit/test_beam_search.py` — add test that different beams produce different signatures
**Verify:** `pytest cli/tests/unit/test_beam_search.py -v`

#### 1.3 Reorder Backtracking Strategies
**File:** `cli/src/fill/beam_search/orchestrator.py` (`_try_backtracking()` method, ~line 684)
**Change:** Move conflict-directed backjumping (currently Try 4) to Try 1, push brute-force (2×, 5× candidates) down. The smart strategy should be attempted first since it's more targeted.
**Current order:** 2× → 5× → no-filter → conflict → chronological
**New order:** conflict → 2× → 5× → no-filter → chronological
**Test:** Existing beam search tests should still pass
**Verify:** `pytest cli/tests/unit/test_beam_search.py -v`

#### 1.4 Fix Adaptive Autofill Dead Code
**File:** `cli/src/fill/adaptive_autofill.py` (lines 118–119)
**Change:** The `on_backtrack` callback is checked with `hasattr()` but never exists on Autofill or BeamSearch. Two options:
- **Option A (preferred):** Remove the dead `hasattr` check and `_on_backtrack` method. Use a different detection mechanism — check progress stagnation via iteration count instead.
- **Option B:** Implement `on_backtrack` in `autofill.py` and `beam_search/orchestrator.py`
**Test:** Existing adaptive tests in `backend/tests/integration/test_adaptive_beam_search_api.py`
**Verify:** `pytest backend/tests/integration/test_adaptive_beam_search_api.py -v`

#### 1.5 Scale Beam Timeout with Grid Size
**File:** `cli/src/fill/hybrid_autofill.py` (line 116)
**Change:** Replace `min(60, ...)` with grid-size-aware cap:
```python
size_timeout_caps = {11: 30, 13: 45, 15: 60, 17: 90, 21: 120}
beam_cap = size_timeout_caps.get(grid.size, 60)
```
**Test:** `cli/tests/unit/test_hybrid_integration.py` — add test verifying timeout scales
**Verify:** `pytest cli/tests/unit/test_hybrid_integration.py -v`

---

### Phase 2: Scoring Improvements (4 items)

#### 2.1 Add Bigram Analysis to Scoring
**File:** `cli/src/core/scoring.py`
**Change:** Add `COMMON_BIGRAMS` dict with top 20 English bigrams and frequency weights. Add `bigram_bonus(word)` function that sums bigram scores and normalizes by word length. Integrate into `score_word()` as bonus up to +30 points.
**Constraint:** Old caches remain valid — this only affects newly scored words.
**Test:** `cli/tests/unit/test_word_list.py` — add tests for bigram scoring: "THE" should get TH+HE bonus, "QZX" should get 0
**Verify:** `pytest cli/tests/unit/test_word_list.py -v`

#### 2.2 Add Vowel Distribution Penalty
**File:** `cli/src/core/scoring.py`
**Change:** Add check in `score_word()`: if vowel ratio (AEIOUY) < 0.20 or > 0.65, apply penalty of -20. This catches all-consonant and all-vowel words.
**Test:** Add tests: "STRENGTHS" (1/9 = 11% vowels → penalty), "AEIOU" (100% → penalty), "OCEAN" (60% → no penalty)
**Verify:** `pytest cli/tests/unit/test_word_list.py -v`

#### 2.3 Add Consonant Clustering Penalty
**File:** `cli/src/core/scoring.py`
**Change:** Count max consecutive consonants in word. If >3, apply penalty of -15. Words like "STRPHLNG" get penalized; normal words like "STRING" (STR = 3) don't.
**Test:** Add tests for cluster detection
**Verify:** `pytest cli/tests/unit/test_word_list.py -v`

#### 2.4 Add Scoring Version Metadata to Cache
**File:** `cli/src/fill/word_list.py`
**Change:** Add `'scoring_version': '2.0'` to cache metadata dict. On load, log a warning if cached version differs from current, but DON'T auto-invalidate. This is informational only per user's requirement.
**Test:** Verify old caches still load without error
**Verify:** `pytest cli/tests/unit/test_word_list.py -v`

---

### Verification Plan

After all changes:
1. `pytest` — all 165+ tests pass (existing + new)
2. `pytest --cov=backend --cov=cli` — coverage doesn't decrease
3. Manual test: `python -m cli.src.cli pattern "C?T" --json-output` — verify scoring includes new factors
4. Manual test: `python -m cli.src.cli fill puzzle.json -w data/wordlists/comprehensive.txt --algorithm hybrid` — verify scaled beam timeout

### Files Modified (Summary)

| Phase | Files |
|-------|-------|
| 1.1 | `cli/src/fill/word_trie.py`, `cli/tests/unit/test_word_trie.py` |
| 1.2 | `cli/src/fill/beam_search/orchestrator.py`, `cli/tests/unit/test_beam_search.py` |
| 1.3 | `cli/src/fill/beam_search/orchestrator.py` |
| 1.4 | `cli/src/fill/adaptive_autofill.py` |
| 1.5 | `cli/src/fill/hybrid_autofill.py`, `cli/tests/unit/test_hybrid_integration.py` |
| 2.1–2.3 | `cli/src/core/scoring.py`, `cli/tests/unit/test_word_list.py` |
| 2.4 | `cli/src/fill/word_list.py` |
