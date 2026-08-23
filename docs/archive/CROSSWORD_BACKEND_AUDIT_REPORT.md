# Crossword Backend Algorithm Audit Report
**Date:** 2025-12-23  
**Auditor:** Claude (Sonnet 4.5)  
**Repository:** /home/user/untitled_project/crossword-helper

---

## Executive Summary

A thorough audit of the crossword autofill backend revealed **CRITICAL BUGS** preventing the algorithm from solving empty or large grids. The root cause is **insufficient domain initialization** in the CSP solver, specifically the `max_results=1000` limit combined with score-based sorting, which creates severe letter coverage gaps in initial domains.

### Critical Findings
1. ✅ **Pattern matching works correctly** (trie-based, 10-50x faster than regex)
2. ✅ **Wordlist loading and caching work correctly** (454k words, proper scoring)
3. ❌ **Autofill FAILS on empty/large grids** due to domain truncation bug
4. ❌ **AC-3 arc consistency prematurely eliminates all solutions** 
5. ⚠️  **Scaling issue**: Works on 6-slot grids, fails on 20+ slot grids

---

## Test Results Summary

| Grid Size | Slots | Status | Iterations | Time | Issue |
|-----------|-------|--------|------------|------|-------|
| 5×5 (minimal) | 6 | ✅ SUCCESS | 7 | 0.11s | None |
| 7×7 (medium) | 20 | ❌ FAIL | 1 | 0.05s | No candidates for first slot |
| 11×11 (standard) | 38 | ❌ FAIL | 0 | 0.05s | AC-3 returns False immediately |

---

## Root Cause Analysis

### Bug #1: Domain Truncation with Score-Sorted Results

**Location:** `cli/src/fill/autofill.py:206`

```python
# BUGGY CODE
candidates = self.pattern_matcher.find(
    pattern,
    min_score=self.min_score,
    max_results=1000,  # ← PROBLEM: Truncates to 1000 words
)
self.domains[idx] = {word for word, score in candidates}
```

**Problem:**
- Pattern matcher sorts results by score (descending) before truncating
- Top 1000 3-letter words (score 31-36) only cover **5 letters: A, B, C, D, E**
- Words starting with F-Z are excluded from domains
- When constraints require these letters, AC-3 finds no compatible words
- Domains become empty → AC-3 returns False → autofill fails with 0 iterations

**Evidence:**
```
Top 1000 3-letter words by starting letter:
  A: 249 words ✓
  B: 178 words ✓
  C: 212 words ✓
  D: 207 words ✓
  E: 154 words ✓
  F-Z: 0 words ✗ CRITICAL GAP
```

### Bug #2: Aggressive Min Score Threshold

**Location:** `cli/src/fill/autofill.py:48,79`

```python
def __init__(self, ..., min_score: int = 30, ...):
    self.min_score = min_score  # Default: 30
```

**Problem:**
- With `min_score=30`, **60.6% of 3-letter words are excluded** (2,248 out of 3,710)
- **ZERO 3-letter words starting with J, Q, X, Z** pass the threshold
- Reduces solution space unnecessarily, especially for empty grids

**Evidence:**
```
3-letter words with score >= 30: 1,462 (39.4%)
3-letter words with score < 30:  2,248 (60.6%)

Missing letters (score >= 30): J, Q, X, Z
```

### Bug #3: Limited Candidate Retrieval in Backtracking

**Location:** `cli/src/fill/autofill.py:468`

```python
def _get_candidates(self, slot: Dict) -> List[Tuple[str, int]]:
    pattern = self.grid.get_pattern_for_slot(slot)
    candidates = self.pattern_matcher.find(
        pattern, min_score=self.min_score, max_results=100  # ← Only 100!
    )
    return candidates
```

**Problem:**
- During backtracking, only 100 candidates retrieved per slot
- If top 100 don't lead to solutions, algorithm gives up prematurely
- No fallback to lower-scored words

---

## Algorithm Analysis

### AC-3 Arc Consistency (Lines 256-322)

**Implementation Status:** ✅ CORRECT  
**References:** Matches standard AC-3 algorithm from academic literature

The AC-3 implementation correctly:
- Maintains a queue of arcs (constraint edges)
- Revises domains by removing incompatible values
- Propagates changes to neighboring variables
- Returns False when any domain becomes empty

**However**, it's being fed incomplete domains (Bug #1), causing premature failure.

### Backtracking with MRV Heuristic (Lines 324-452)

**Implementation Status:** ✅ MOSTLY CORRECT  
**Issues:** Limited candidates (Bug #3), relies on bad initial domains (Bug #1)

The backtracking implementation correctly:
- Uses MRV (Minimum Remaining Values) to choose most constrained slots first
- Implements forward checking to detect dead ends early
- Tracks used words to avoid duplicates
- Respects timeout limits

### LCV Value Ordering (Lines 454-471)

**Implementation Status:** ⚠️ PARTIALLY IMPLEMENTED  
**Issue:** Returns candidates sorted by score, not by "least constraining"

True LCV should prefer values that preserve the most options for neighboring variables. Current implementation just sorts by quality score, which doesn't optimize constraint satisfaction.

---

## Performance Analysis

### Pattern Matching: ✅ EXCELLENT

| Component | Implementation | Performance | Status |
|-----------|----------------|-------------|--------|
| Regex matcher | Linear scan with regex | 200-500ms | Stable, slow |
| Trie matcher | Prefix tree with pruning | 10-50ms | **10-50x faster** ✅ |

The trie-based pattern matcher is correctly implemented and provides massive speedup.

### Wordlist Management: ✅ EXCELLENT

- 454k words loaded and scored correctly
- Binary cache (`.pkl`) provides ~1.1x speedup (acceptable)
- Length indexing works correctly
- Score distribution: min=1, max=100, avg=84

### CSP Solver: ❌ BLOCKED BY BUGS

The CSP solver architecture is sound but cannot function with truncated/incomplete domains.

---

## Comparison with Reference Implementations

### Sources Consulted:
- [AC-3 Algorithm - Wikipedia](https://en.wikipedia.org/wiki/AC-3_algorithm)
- [CS50 AI Crossword CSP](https://github.com/PLCoster/cs50ai-week3-crossword)
- [How to Solve CSPs with AC-3](https://medium.com/swlh/how-to-solve-constraint-satisfaction-problems-csps-with-ac-3-algorithm-in-python-f7a9be538cfe)
- [CSP Ordering Heuristics](https://forns.lmu.build/classes/fall-2024/cmsi-2130/lecture-11-2.html)
- [Baeldung CS - CSP](https://www.baeldung.com/cs/csp)

### Key Differences:

1. **Domain Initialization:**
   - ✅ Reference: Use ALL words matching pattern constraints
   - ❌ Our implementation: Truncate to 1000, sorted by score

2. **Min Score Filtering:**
   - ✅ Reference: No quality filtering during CSP solving (purely constraint-based)
   - ❌ Our implementation: Aggressive min_score=30 filters out valid solutions

3. **Value Ordering:**
   - ✅ Reference: LCV truly picks least constraining value
   - ⚠️ Our implementation: Sorts by quality score (not constraint-based)

---

## Recommended Fixes

### Fix #1: Remove/Increase max_results Limit (CRITICAL - Priority 1)

**File:** `cli/src/fill/autofill.py`

```python
# CURRENT (Line 201-208):
candidates = self.pattern_matcher.find(
    pattern,
    min_score=self.min_score,
    max_results=1000,  # ← REMOVE THIS
)

# RECOMMENDED FIX:
candidates = self.pattern_matcher.find(
    pattern,
    min_score=self.min_score,
    max_results=None,  # ← Get ALL matching words
)
```

**Impact:** Ensures complete letter coverage in all domains

**Alternative (if memory is a concern):**
```python
max_results=10000,  # Increase significantly
```

### Fix #2: Lower Default min_score (Priority 2)

**File:** `cli/src/fill/autofill.py`

```python
# CURRENT (Line 48):
def __init__(self, ..., min_score: int = 30, ...):

# RECOMMENDED:
def __init__(self, ..., min_score: int = 0, ...):  # Or max 10
```

**Rationale:** Empty grids need maximum solution space. Quality filtering should happen after finding a solution (as a post-processing step), not during solving.

### Fix #3: Increase Backtracking Candidates (Priority 2)

**File:** `cli/src/fill/autofill.py`

```python
# CURRENT (Line 468):
max_results=100

# RECOMMENDED:
max_results=1000  # Or None for unlimited
```

### Fix #4: Implement True LCV (Priority 3 - Enhancement)

**File:** `cli/src/fill/autofill.py`

```python
def _get_candidates(self, slot: Dict) -> List[Tuple[str, int]]:
    pattern = self.grid.get_pattern_for_slot(slot)
    candidates = self.pattern_matcher.find(pattern, ...)
    
    # Sort by how many options each candidate preserves for neighbors
    def count_remaining_options(word):
        # Temporarily place word
        self.grid.place_word(word, ...)
        
        # Count valid options for crossing slots
        options = 0
        for crossing_slot in self._get_crossing_slots(slot):
            crossing_pattern = self.grid.get_pattern_for_slot(crossing_slot)
            options += self.pattern_matcher.count_matches(crossing_pattern, ...)
        
        # Remove word
        self.grid.remove_word(...)
        return options
    
    # Sort by most options preserved (descending)
    candidates.sort(key=lambda w: count_remaining_options(w[0]), reverse=True)
    return candidates
```

**Impact:** Better value ordering → fewer backtracks → faster solving

### Fix #5: Randomize/Diversify Initial Domains (Priority 3 - Alternative)

If keeping `max_results` limit for performance, ensure diversity:

```python
candidates = self.pattern_matcher.find(pattern, ...)

# Instead of taking top N by score, sample evenly across score range
# or shuffle to ensure letter diversity
import random
random.shuffle(candidates)  # Then take first 1000
```

---

## Testing Recommendations

### Test Suite Additions Needed:

1. **Empty Grid Tests:**
   ```python
   def test_fill_empty_11x11_grid():
       grid = create_standard_11x11_pattern()  # With black squares, all empty
       result = autofill.fill(grid)
       assert result.success
       assert result.slots_filled == result.total_slots
   ```

2. **Letter Coverage Tests:**
   ```python
   def test_domain_letter_coverage():
       # Ensure all 26 letters represented in domains for common lengths
       for length in [3, 5, 7, 11]:
           domain = get_initial_domain(pattern='?' * length)
           starting_letters = {word[0] for word in domain}
           assert len(starting_letters) >= 24  # At least 24/26 letters
   ```

3. **Large Grid Stress Tests:**
   ```python
   def test_fill_15x15_empty_grid():
       # Standard NYT-style 15x15
       ...
   ```

---

## Conclusion

The crossword autofill backend has a **sound algorithmic foundation** (AC-3, MRV, backtracking) but is crippled by **overly aggressive domain truncation and filtering**. The fixes are straightforward and low-risk:

1. ✅ Remove `max_results=1000` limit in domain initialization
2. ✅ Lower `min_score` default to 0 or 10
3. ✅ Increase backtracking candidate limit

**Expected Outcome After Fixes:**
- Empty grids: Should fill successfully in < 5 seconds
- Partially filled grids: Should fill faster (better pruning with partial info)
- Solution quality: Can be improved in post-processing if needed

**Confidence Level:** 🔥 **VERY HIGH** - Root cause identified with concrete evidence and clear fix path.

---

## References

### Algorithm References:
- [AC-3 Algorithm - Wikipedia](https://en.wikipedia.org/wiki/AC-3_algorithm)
- [CS50 AI Crossword CSP Implementation](https://github.com/PLCoster/cs50ai-week3-crossword)
- [Solving CSPs with AC-3 in Python](https://medium.com/swlh/how-to-solve-constraint-satisfaction-problems-csps-with-ac-3-algorithm-in-python-f7a9be538cfe)
- [CSP Ordering Heuristics (2024)](https://forns.lmu.build/classes/fall-2024/cmsi-2130/lecture-11-2.html)
- [Constraint Satisfaction Problems - Baeldung](https://www.baeldung.com/cs/csp)
- [Solving Latin Squares with MRV/LCV](https://mienxiu.com/solving-latin-squares-as-csps/)

### Code Locations:
- Autofill CSP Solver: `cli/src/fill/autofill.py` (600 lines)
- Trie Pattern Matcher: `cli/src/fill/trie_pattern_matcher.py` (238 lines)
- Word Trie Data Structure: `cli/src/fill/word_trie.py` (350 lines)
- Grid Management: `cli/src/core/grid.py` (488 lines)
- Word Scoring: `cli/src/core/scoring.py` (81 lines)

---

**End of Report**
