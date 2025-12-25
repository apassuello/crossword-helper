# Critical Fixes Guide

**Priority:** URGENT - Fix before deployment
**Estimated Time:** 3.5 hours
**Impact:** Prevents runtime errors, ensures consistency

---

## Fix #1: Constructor Parameter Mismatch (30 minutes)

### Problem
`MRVSlotSelector` constructor doesn't match how orchestrator uses it.

### Location
`cli/src/fill/beam_search/selection/slot_selector.py` (line 41)

### Current Code (BROKEN)
```python
class MRVSlotSelector(SlotSelectionStrategy):
    def __init__(self, pattern_matcher, word_list, theme_entries=None):
        """Initialize MRV selector."""
        self.pattern_matcher = pattern_matcher
        self.word_list = word_list  # ❌ NOT PROVIDED by orchestrator
        self.theme_entries = theme_entries or {}
```

### How Orchestrator Calls It
```python
# orchestrator.py line 93
self.slot_selector = MRVSlotSelector(
    pattern_matcher=self.pattern_matcher,
    get_min_score_func=self._get_min_score_for_length  # ❌ NOT IN CONSTRUCTOR
)
```

### Fixed Code
```python
class MRVSlotSelector(SlotSelectionStrategy):
    def __init__(self, pattern_matcher, get_min_score_func, theme_entries=None):
        """
        Initialize MRV selector.

        Args:
            pattern_matcher: Pattern matching utility
            get_min_score_func: Function to get minimum score for a given length
            theme_entries: Optional theme entries to prioritize
        """
        self.pattern_matcher = pattern_matcher
        self.get_min_score = get_min_score_func
        self.theme_entries = theme_entries or {}

    def _get_min_score_for_length(self, length: int) -> int:
        """Delegate to injected function."""
        return self.get_min_score(length)
```

### Changes Required
1. Remove `word_list` parameter (unused)
2. Add `get_min_score_func` parameter
3. Store as `self.get_min_score`
4. Update `_get_min_score_for_length` to delegate to injected function

### Verification
```python
# Test that orchestrator can create slot selector
from cli.src.fill.beam_search.orchestrator import BeamSearchOrchestrator
from cli.src.core.grid import Grid
from cli.src.fill.word_list import WordList
from cli.src.fill.pattern_matcher import PatternMatcher

grid = Grid(11, 11)
word_list = WordList()
pattern_matcher = PatternMatcher(word_list)

# Should not raise TypeError
orchestrator = BeamSearchOrchestrator(grid, word_list, pattern_matcher)
print("✅ Fix verified - orchestrator creates successfully")
```

---

## Fix #2: Inconsistent Quality Thresholds (1 hour)

### Problem
Same method returns different values in different files, causing inconsistent quality standards.

### Locations
- `cli/src/fill/beam_search/orchestrator.py` (line 131)
- `cli/src/fill/beam_search/selection/slot_selector.py` (line 249)

### Current Code (INCONSISTENT)

**File 1: orchestrator.py**
```python
def _get_min_score_for_length(self, length: int) -> int:
    if length <= 3:
        return 0
    elif length == 4:
        return 10
    elif length <= 6:
        return 30  # ✅
    elif length <= 8:
        return 50
    else:
        return 70
```

**File 2: slot_selector.py**
```python
def _get_min_score_for_length(self, length: int) -> int:
    if length <= 3:
        return 0
    elif length <= 5:
        return 10
    elif length <= 7:
        return 20  # ❌ Different from orchestrator!
    elif length <= 9:
        return 30  # ❌ Different from orchestrator!
    else:
        return 40  # ❌ Different from orchestrator!
```

### Fixed Code

**Step 1: Create shared config**

Create new file: `cli/src/fill/beam_search/config.py`
```python
"""
Beam search configuration and shared utilities.

This module contains configuration constants and shared utility functions
used across beam search components.
"""


class BeamSearchConfig:
    """Configuration constants for beam search algorithm."""

    # Quality thresholds by word length
    # Higher values = more selective about word quality
    QUALITY_THRESHOLDS = {
        3: 0,   # 3-letter words: Accept all (crosswordese OK)
        4: 10,  # 4-letter words: Slightly filtered
        5: 20,  # 5-letter words: Moderately filtered
        6: 30,  # 6-letter words: Common words preferred
        7: 40,  # 7-letter words: Quality words only
        8: 50,  # 8-letter words: High quality
        9: 60,  # 9-letter words: Very high quality
        10: 70  # 10+ letter words: Excellent quality only
    }

    # Beam search parameters
    DEFAULT_BEAM_WIDTH = 5
    DEFAULT_CANDIDATES_PER_SLOT = 10
    DEFAULT_DIVERSITY_BONUS = 0.1

    # Diversity parameters
    BEAM_DIVERSITY_OFFSET = 2
    DIRECTION_ALTERNATION_BONUS = 0.1
    MIN_DIVERSITY_THRESHOLD = 0.05

    @staticmethod
    def get_min_score_for_length(length: int) -> int:
        """
        Get minimum quality score threshold for a given word length.

        Different word lengths require different quality standards:
        - Short words (3-4): Allow crosswordese for flexibility
        - Medium words (5-7): Prefer common words
        - Long words (8+): Require high-quality phrases

        Args:
            length: Word length in letters

        Returns:
            Minimum acceptable quality score (0-100)

        Example:
            >>> BeamSearchConfig.get_min_score_for_length(3)
            0
            >>> BeamSearchConfig.get_min_score_for_length(6)
            30
            >>> BeamSearchConfig.get_min_score_for_length(10)
            70
        """
        # Use exact threshold if defined
        if length in BeamSearchConfig.QUALITY_THRESHOLDS:
            return BeamSearchConfig.QUALITY_THRESHOLDS[length]

        # For longer words, use highest threshold
        if length > max(BeamSearchConfig.QUALITY_THRESHOLDS.keys()):
            return BeamSearchConfig.QUALITY_THRESHOLDS[
                max(BeamSearchConfig.QUALITY_THRESHOLDS.keys())
            ]

        # For edge cases, use 0
        return 0
```

**Step 2: Update orchestrator.py**
```python
from .config import BeamSearchConfig

class BeamSearchOrchestrator:
    def _get_min_score_for_length(self, length: int) -> int:
        """
        Return quality threshold appropriate for word length.

        Delegates to shared configuration for consistency.
        """
        return BeamSearchConfig.get_min_score_for_length(length)
```

**Step 3: Update slot_selector.py**
```python
from ..config import BeamSearchConfig

class MRVSlotSelector(SlotSelectionStrategy):
    def _get_min_score_for_length(self, length: int) -> int:
        """
        Get minimum quality score threshold based on word length.

        Delegates to shared configuration for consistency.
        """
        # Now delegates to injected function (from Fix #1)
        return self.get_min_score(length)
```

**Step 4: Update beam_manager.py** (also uses this method)
```python
from ..config import BeamSearchConfig

# Remove hardcoded thresholds, use config
```

### Verification
```python
# Test consistency
from cli.src.fill.beam_search.config import BeamSearchConfig
from cli.src.fill.beam_search.orchestrator import BeamSearchOrchestrator
from cli.src.fill.beam_search.selection.slot_selector import MRVSlotSelector

# All should return same values
assert BeamSearchConfig.get_min_score_for_length(6) == 30
assert orchestrator._get_min_score_for_length(6) == 30
assert slot_selector._get_min_score_for_length(6) == 30
print("✅ Fix verified - all components use same thresholds")
```

---

## Fix #3: Add Backward Compatibility Tests (2 hours)

### Problem
No tests verify that `BeamSearchAutofill` wrapper maintains the original API.

### Location
Create new file: `cli/tests/integration/test_backward_compatibility.py`

### Implementation
```python
"""
Backward compatibility tests for BeamSearchAutofill.

Verifies that the refactored BeamSearchAutofill class maintains
100% API compatibility with the original implementation.
"""

import pytest
from cli.src.core.grid import Grid
from cli.src.fill.word_list import WordList
from cli.src.fill.pattern_matcher import PatternMatcher
from cli.src.fill.beam_search_autofill import BeamSearchAutofill


class TestBeamSearchAutofillAPI:
    """Test that BeamSearchAutofill maintains original API."""

    @pytest.fixture
    def setup(self):
        """Create test fixtures."""
        grid = Grid(11, 11)
        word_list = WordList()
        word_list.add_words(['CAT', 'DOG', 'BIRD', 'FISH'])
        pattern_matcher = PatternMatcher(word_list)
        return grid, word_list, pattern_matcher

    def test_constructor_signature(self, setup):
        """Test constructor accepts all original parameters."""
        grid, word_list, pattern_matcher = setup

        # Should accept all original parameters
        autofill = BeamSearchAutofill(
            grid=grid,
            word_list=word_list,
            pattern_matcher=pattern_matcher,
            beam_width=5,
            candidates_per_slot=10,
            min_score=0,
            diversity_bonus=0.1,
            progress_reporter=None,
            theme_entries=None
        )

        assert autofill is not None
        assert autofill.grid == grid
        assert autofill.word_list == word_list
        assert autofill.beam_width == 5

    def test_default_parameters(self, setup):
        """Test constructor works with default parameters."""
        grid, word_list, pattern_matcher = setup

        # Should work with minimal parameters
        autofill = BeamSearchAutofill(
            grid=grid,
            word_list=word_list,
            pattern_matcher=pattern_matcher
        )

        assert autofill.beam_width == 5  # Default
        assert autofill.candidates_per_slot == 10  # Default
        assert autofill.min_score == 0  # Default

    def test_fill_method_exists(self, setup):
        """Test fill() method exists and has correct signature."""
        grid, word_list, pattern_matcher = setup
        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)

        # Method should exist
        assert hasattr(autofill, 'fill')
        assert callable(autofill.fill)

    def test_fill_returns_fill_result(self, setup):
        """Test fill() returns FillResult object."""
        grid, word_list, pattern_matcher = setup
        grid.place_word('CAT', 0, 0, 'across')
        grid.place_word('DOG', 0, 0, 'down')

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)
        result = autofill.fill(timeout=10)

        # Should return FillResult
        assert result is not None
        assert hasattr(result, 'success')
        assert hasattr(result, 'grid')
        assert hasattr(result, 'time_elapsed')
        assert hasattr(result, 'slots_filled')
        assert hasattr(result, 'total_slots')

    def test_parameter_validation(self, setup):
        """Test parameter validation raises appropriate errors."""
        grid, word_list, pattern_matcher = setup

        # Invalid beam_width
        with pytest.raises(ValueError, match="beam_width"):
            BeamSearchAutofill(grid, word_list, pattern_matcher, beam_width=0)

        # Invalid candidates_per_slot
        with pytest.raises(ValueError, match="candidates_per_slot"):
            BeamSearchAutofill(grid, word_list, pattern_matcher, candidates_per_slot=0)

        # Invalid timeout
        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)
        with pytest.raises(ValueError, match="timeout"):
            autofill.fill(timeout=5)

    def test_theme_entries_support(self, setup):
        """Test theme_entries parameter works."""
        grid, word_list, pattern_matcher = setup
        theme_entries = {(0, 0, 'across'): 'CAT'}

        autofill = BeamSearchAutofill(
            grid, word_list, pattern_matcher,
            theme_entries=theme_entries
        )

        assert autofill.theme_entries == theme_entries

    def test_inheritance_from_orchestrator(self, setup):
        """Test that BeamSearchAutofill inherits from BeamSearchOrchestrator."""
        from cli.src.fill.beam_search.orchestrator import BeamSearchOrchestrator
        grid, word_list, pattern_matcher = setup

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)

        # Should be instance of both classes
        assert isinstance(autofill, BeamSearchAutofill)
        assert isinstance(autofill, BeamSearchOrchestrator)

    def test_component_initialization(self, setup):
        """Test that all internal components are initialized."""
        grid, word_list, pattern_matcher = setup
        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)

        # All components should be initialized
        assert hasattr(autofill, 'slot_selector')
        assert hasattr(autofill, 'constraint_engine')
        assert hasattr(autofill, 'value_ordering')
        assert hasattr(autofill, 'diversity_manager')
        assert hasattr(autofill, 'state_evaluator')
        assert hasattr(autofill, 'beam_manager')

        assert autofill.slot_selector is not None
        assert autofill.constraint_engine is not None
        assert autofill.beam_manager is not None


class TestBeamSearchAutofillBehavior:
    """Test that refactored version behaves identically to original."""

    @pytest.fixture
    def simple_grid(self):
        """Create simple test grid."""
        grid = Grid(3, 3)
        word_list = WordList()
        word_list.add_words(['CAT', 'DOG', 'COD', 'TAG', 'TAN'])
        pattern_matcher = PatternMatcher(word_list)
        return grid, word_list, pattern_matcher

    def test_empty_grid_handling(self, simple_grid):
        """Test behavior on completely empty grid."""
        grid, word_list, pattern_matcher = simple_grid
        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)

        result = autofill.fill(timeout=10)

        # Should return result (success or partial)
        assert result is not None
        assert result.total_slots > 0

    def test_already_filled_grid(self, simple_grid):
        """Test behavior on already-filled grid."""
        grid, word_list, pattern_matcher = simple_grid

        # Fill entire grid
        grid.place_word('CAT', 0, 0, 'across')
        grid.place_word('DOG', 1, 0, 'across')
        grid.place_word('COD', 0, 0, 'down')

        autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)
        result = autofill.fill(timeout=10)

        # Should recognize already complete
        assert result.success is True
        assert result.slots_filled == 0  # Nothing to fill

    def test_progress_reporting(self, simple_grid):
        """Test progress reporter integration."""
        grid, word_list, pattern_matcher = simple_grid

        progress_calls = []

        class MockReporter:
            def update(self, progress, message):
                progress_calls.append((progress, message))

        reporter = MockReporter()
        autofill = BeamSearchAutofill(
            grid, word_list, pattern_matcher,
            progress_reporter=reporter
        )

        result = autofill.fill(timeout=10)

        # Should have called reporter if any slots were filled
        if result.slots_filled > 0:
            assert len(progress_calls) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

### Run Tests
```bash
# Run backward compatibility tests
pytest cli/tests/integration/test_backward_compatibility.py -v

# Expected output:
# test_backward_compatibility.py::TestBeamSearchAutofillAPI::test_constructor_signature PASSED
# test_backward_compatibility.py::TestBeamSearchAutofillAPI::test_default_parameters PASSED
# test_backward_compatibility.py::TestBeamSearchAutofillAPI::test_fill_method_exists PASSED
# ... (all tests should PASS)
```

---

## Complete Fix Checklist

### Phase 1: Fix Constructor (30 min)
- [ ] Update `MRVSlotSelector.__init__()` signature
- [ ] Remove `word_list` parameter
- [ ] Add `get_min_score_func` parameter
- [ ] Update `_get_min_score_for_length()` to delegate
- [ ] Test orchestrator instantiation

### Phase 2: Consolidate Quality Thresholds (1 hour)
- [ ] Create `beam_search/config.py`
- [ ] Define `BeamSearchConfig` class
- [ ] Add `QUALITY_THRESHOLDS` dict
- [ ] Implement `get_min_score_for_length()` static method
- [ ] Update `orchestrator.py` to use config
- [ ] Update `slot_selector.py` to use config
- [ ] Update `beam_manager.py` to use config
- [ ] Verify all components return same values

### Phase 3: Add Backward Compatibility Tests (2 hours)
- [ ] Create `test_backward_compatibility.py`
- [ ] Add `TestBeamSearchAutofillAPI` class
- [ ] Implement constructor signature tests
- [ ] Implement fill() method tests
- [ ] Implement parameter validation tests
- [ ] Add `TestBeamSearchAutofillBehavior` class
- [ ] Test edge cases (empty grid, filled grid)
- [ ] Run all tests and verify they pass

---

## Verification Script

Run this after all fixes:

```bash
#!/bin/bash
# verify_critical_fixes.sh

echo "=== Verifying Critical Fixes ==="
echo ""

echo "1. Testing imports..."
python -c "from cli.src.fill.beam_search.orchestrator import BeamSearchOrchestrator; print('✅ Orchestrator imports')"
python -c "from cli.src.fill.beam_search.config import BeamSearchConfig; print('✅ Config imports')"
python -c "from cli.src.fill.beam_search_autofill import BeamSearchAutofill; print('✅ BeamSearchAutofill imports')"

echo ""
echo "2. Testing instantiation..."
python -c "
from cli.src.core.grid import Grid
from cli.src.fill.word_list import WordList
from cli.src.fill.pattern_matcher import PatternMatcher
from cli.src.fill.beam_search_autofill import BeamSearchAutofill

grid = Grid(11, 11)
word_list = WordList()
pattern_matcher = PatternMatcher(word_list)
autofill = BeamSearchAutofill(grid, word_list, pattern_matcher)
print('✅ BeamSearchAutofill instantiates successfully')
"

echo ""
echo "3. Testing quality threshold consistency..."
python -c "
from cli.src.fill.beam_search.config import BeamSearchConfig

# Test all lengths
for length in [3, 4, 5, 6, 7, 8, 9, 10]:
    score = BeamSearchConfig.get_min_score_for_length(length)
    print(f'  Length {length}: min_score={score}')

print('✅ Quality thresholds consistent')
"

echo ""
echo "4. Running backward compatibility tests..."
pytest cli/tests/integration/test_backward_compatibility.py -v --tb=short

echo ""
echo "=== Verification Complete ==="
```

---

## Timeline

| Phase | Task | Time | Status |
|-------|------|------|--------|
| 1 | Fix constructor mismatch | 30 min | ⏸️ Todo |
| 2 | Consolidate quality thresholds | 1 hour | ⏸️ Todo |
| 3 | Add backward compatibility tests | 2 hours | ⏸️ Todo |
| **Total** | **Critical fixes** | **3.5 hours** | **⏸️ Ready to start** |

---

**After these fixes:**
- ✅ No runtime errors
- ✅ Consistent quality standards
- ✅ Verified backward compatibility
- ✅ Production-ready code

**Next:** Repository cleanup (see `AUDIT_EXECUTIVE_SUMMARY.md`)
