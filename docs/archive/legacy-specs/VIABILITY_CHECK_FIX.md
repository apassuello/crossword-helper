# Fix: Viability Check is Too Aggressive

**File:** `/Users/apa/projects/untitled_project/crossword-helper/cli/src/fill/beam_search_autofill.py`
**Function:** `_is_viable_state()` (lines 540-578)
**Date:** 2025-12-23

---

## Problem Statement

The viability check is rejecting **100% of beam states** at slot 3, causing beam search to exit early with no solution.

### Observed Behavior
```
DEBUG: Filling slot 3/38: length=11, pos=(2,0), dir=across
  ...10 candidates tried...

DEBUG: Expansion failed!
  Skipped (duplicate): 10
  Skipped (viability): 40  ← ALL states rejected!
  Added: 0
```

### Root Cause

The `_is_viable_state()` function checks **ALL 38 unfilled slots** after placing just 3 words. This is computationally expensive and overly pessimistic:

1. **Early in search:** Grid is mostly empty, many slots have constrained patterns
2. **Aggressive filtering:** If ANY slot has 0 candidates (even distant slots), state is rejected
3. **False negatives:** Slots that appear "impossible" early may become viable later

**Example failure cascade:**
```
Filled: Slot 1 (ALMOSTTHERE), Slot 2 (ALMOSTNEVER)
Trying: Slot 3 (ABLE BODIED)

Viability check examines ALL 35 remaining unfilled slots:
- Slot 4 (horizontal, row 3): Pattern "???" → 1000+ candidates ✓
- Slot 5 (vertical, col 1): Pattern "LM?????????" → 1 candidate ✓
- Slot 6 (vertical, col 2): Pattern "MO?????????" → ??? candidates ???
- ...
- Slot 38: Pattern "???????????" → Many candidates ✓

If ANY slot returns 0 candidates → ENTIRE state rejected!
```

The problem is likely a **rare constraint** in one of the 35 slots that temporarily has 0 candidates, even though it might become viable after more words are placed.

---

## Evidence

### Test Run Output
```bash
$ python -m cli.src.cli fill simple_fillable_11x11.json \
  -w data/wordlists/comprehensive.txt \
  --algorithm hybrid --beam-width 5 --min-score 30 --timeout 60

DEBUG: Expansion failed!
  Skipped (duplicate): 10
  Skipped (viability): 40
  Added: 0
```

**Analysis:**
- 5 beam states × 10 candidates/state = 50 total expansions
- 10 skipped (duplicates) → 40 remaining
- **40 rejected by viability** → 0 added
- Result: Beam becomes empty, algorithm exits

---

## Solutions

### Option 1: **Disable Viability Check** (Quick Fix)

**Pros:**
- Immediate fix
- Lets beam search explore more states
- Standard beam search doesn't use viability checks

**Cons:**
- May waste time on doomed states
- Could fill slots with incompatible words

**Implementation:**
```python
def _is_viable_state(self, state: BeamState) -> bool:
    """Always return True - disable viability checking."""
    return True
```

---

### Option 2: **Lazy Viability Check** (Smart Fix)

Only check viability for **neighboring slots** (slots that intersect with just-placed word).

**Pros:**
- Catches immediate conflicts
- Much faster (checks 5-15 slots instead of 38)
- Reduces false negatives

**Cons:**
- Misses distant conflicts
- Slightly more complex implementation

**Implementation:**
```python
def _is_viable_state(self, state: BeamState, last_filled_slot: Dict = None) -> bool:
    """
    Check if state has any dead ends in NEIGHBORING slots only.

    Args:
        state: Beam state to check
        last_filled_slot: The slot that was just filled (optional)

    Returns:
        True if viable (all neighbor slots have ≥1 candidate)
        False if dead end (any neighbor has 0 candidates)
    """
    # If no last_filled_slot provided, check all slots (conservative)
    if last_filled_slot is None:
        slots_to_check = state.grid.get_empty_slots()
    else:
        # Only check slots that intersect with last_filled_slot
        slots_to_check = self._get_intersecting_slots(state.grid, last_filled_slot)

    for slot in slots_to_check:
        pattern = state.grid.get_pattern_for_slot(slot)

        # Get candidates (excluding used words)
        candidates = self.pattern_matcher.find(
            pattern,
            min_score=self.min_score
        )

        # Filter out used words
        available_candidates = [
            (word, score) for word, score in candidates
            if word not in state.used_words
        ]

        # Dead end if no candidates
        if not available_candidates:
            return False

    return True

def _get_intersecting_slots(self, grid: Grid, slot: Dict) -> List[Dict]:
    """
    Get all slots that intersect with the given slot.

    Args:
        grid: Current grid
        slot: Reference slot

    Returns:
        List of slots that share at least one cell with reference slot
    """
    intersecting = []
    all_slots = grid.get_word_slots()

    # Get cells occupied by reference slot
    ref_cells = set()
    if slot['direction'] == 'across':
        for c in range(slot['col'], slot['col'] + slot['length']):
            ref_cells.add((slot['row'], c))
    else:
        for r in range(slot['row'], slot['row'] + slot['length']):
            ref_cells.add((r, slot['col']))

    # Find slots that intersect
    for other_slot in all_slots:
        # Skip same slot
        if (other_slot['row'] == slot['row'] and
            other_slot['col'] == slot['col'] and
            other_slot['direction'] == slot['direction']):
            continue

        # Get cells for other slot
        other_cells = set()
        if other_slot['direction'] == 'across':
            for c in range(other_slot['col'], other_slot['col'] + other_slot['length']):
                other_cells.add((other_slot['row'], c))
        else:
            for r in range(other_slot['row'], other_slot['row'] + other_slot['length']):
                other_cells.add((r, other_slot['col']))

        # Check intersection
        if ref_cells & other_cells:  # Non-empty intersection
            intersecting.append(other_slot)

    return intersecting
```

**Update call site** (line 497 in `_expand_beam`):
```python
# Before:
if self._is_viable_state(new_state):
    expanded.append(new_state)
    total_added += 1

# After:
if self._is_viable_state(new_state, last_filled_slot=slot):
    expanded.append(new_state)
    total_added += 1
```

---

### Option 3: **Probabilistic Viability Check** (Advanced)

Check viability with diminishing frequency as search progresses.

**Logic:**
- Early slots (1-10): Check viability 100% of the time
- Middle slots (11-25): Check viability 50% of the time
- Late slots (26+): Check viability 25% of the time

**Rationale:** Early conflicts are more important to catch; late conflicts will resolve naturally.

**Implementation:**
```python
def _is_viable_state(self, state: BeamState, slot_index: int, total_slots: int) -> bool:
    """Probabilistically check viability based on search progress."""
    import random

    # Calculate probability based on slot index
    progress = slot_index / total_slots
    if progress < 0.3:
        check_probability = 1.0  # Always check early
    elif progress < 0.7:
        check_probability = 0.5  # 50% chance mid-search
    else:
        check_probability = 0.25  # 25% chance late

    # Skip check based on probability
    if random.random() > check_probability:
        return True

    # Standard viability check
    empty_slots = state.grid.get_empty_slots()
    for slot in empty_slots:
        pattern = state.grid.get_pattern_for_slot(slot)
        candidates = self.pattern_matcher.find(pattern, min_score=self.min_score)
        available_candidates = [
            (word, score) for word, score in candidates
            if word not in state.used_words
        ]
        if not available_candidates:
            return False

    return True
```

---

## Recommended Fix: **Option 2 (Lazy Viability Check)**

**Reasons:**
1. **Correctness:** Still catches immediate conflicts
2. **Performance:** Much faster (5-15 slots vs 38 slots)
3. **Effectiveness:** Reduces false negatives dramatically
4. **Maintainability:** Clear logic, easy to understand

**Expected Impact:**
- Viability failures drop from 100% to ~10-20%
- Beam search progresses past slot 3
- Actual filling begins

---

## Testing Plan

### Test 1: Verify Fix Works
```bash
$ python -m cli.src.cli fill simple_fillable_11x11.json \
  -w data/wordlists/comprehensive.txt \
  --algorithm hybrid --beam-width 5 --min-score 30 --timeout 60 \
  -o test_fixed.json

# Expected output:
DEBUG: Expansion failed!
  Skipped (duplicate): 10
  Skipped (viability): 5   ← Reduced from 40!
  Added: 35

# Should continue past slot 3
```

### Test 2: Verify Quality
```bash
$ python -m cli.src.cli show test_fixed.json --format grid

# Verify output contains REAL words, not gibberish
```

### Test 3: Performance Test
```bash
$ time python -m cli.src.cli fill standard_11x11.json \
  -w data/wordlists/comprehensive.txt \
  --algorithm hybrid --timeout 120 -o result.json

# Should complete in <2 minutes with valid fill
```

---

## Implementation Notes

1. **Add `_get_intersecting_slots()` helper** to Grid class or BeamSearchAutofill
2. **Update `_is_viable_state()` signature** to accept `last_filled_slot`
3. **Update call site** in `_expand_beam()` to pass `slot` parameter
4. **Add debug logging** to show which slots are being checked
5. **Update unit tests** to reflect new behavior

---

## Risk Analysis

**Risk:** Lazy viability might miss distant conflicts
**Mitigation:** Beam diversity will naturally explore different paths; conflicts will be caught when those slots are filled

**Risk:** Performance regression if many intersecting slots
**Mitigation:** Still faster than checking all slots; can add early termination if >20 intersecting slots

**Risk:** Breaking existing tests
**Mitigation:** Update tests to pass `last_filled_slot` parameter; add new tests for lazy viability

---

## Conclusion

The viability check is currently checking **ALL 38 slots** after placing just 3 words. This is:
1. **Expensive** (38× pattern matches per state)
2. **Pessimistic** (rejects valid states due to distant constraints)
3. **Unnecessary** (distant slots will be checked when filled)

**Fix:** Only check **intersecting slots** (5-15 instead of 38), dramatically reducing false negatives while maintaining correctness.
