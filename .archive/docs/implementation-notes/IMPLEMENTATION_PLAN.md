# Crossword Autofill - Implementation Plan
**Date:** 2025-12-23  
**Objective:** Fix critical bugs and implement state-of-the-art CSP algorithms  
**Target:** 95%+ success rate on empty 11×11 grids in < 5 seconds

---

## 📋 Implementation Phases

### Phase 1: Critical Bug Fixes (Priority: URGENT)
**Time Estimate:** 1-2 hours  
**Risk Level:** Low (simple parameter changes)  
**Expected Impact:** Algorithm will start working on empty grids

#### Task 1.1: Fix Domain Initialization (CRITICAL)
**File:** `cli/src/fill/autofill.py`  
**Line:** 206  

**Current Code:**
```python
candidates = self.pattern_matcher.find(
    pattern,
    min_score=self.min_score,
    max_results=1000,  # ← BUG: Truncates domains
)
self.domains[idx] = {word for word, score in candidates}
```

**Fix:**
```python
candidates = self.pattern_matcher.find(
    pattern,
    min_score=self.min_score,
    max_results=None,  # ← FIX: Get ALL matching words
)
self.domains[idx] = {word for word, score in candidates}
```

**Justification:**
- Top 1000 3-letter words only cover letters A-E
- Causes AC-3 to fail when constraints need letters F-Z
- Root cause of "0 iterations" failure on 11×11 grids

**Testing:**
```bash
python3 -m cli.src.cli fill simple_fillable_11x11.json \
  --wordlists data/wordlists/comprehensive.txt \
  --timeout 30 --algorithm trie
```

**Success Criteria:**
- AC-3 no longer returns False immediately
- At least 1+ iterations attempted
- Some slots filled (even if not all)

---

#### Task 1.2: Lower Default Min Score
**File:** `cli/src/fill/autofill.py`  
**Line:** 48

**Current Code:**
```python
def __init__(
    self,
    grid: Grid,
    word_list: WordList,
    pattern_matcher: PatternMatcher = None,
    timeout: int = 300,
    min_score: int = 30,  # ← BUG: Too aggressive
    ...
):
```

**Fix:**
```python
def __init__(
    self,
    grid: Grid,
    word_list: WordList,
    pattern_matcher: PatternMatcher = None,
    timeout: int = 300,
    min_score: int = 0,  # ← FIX: Allow all words initially
    ...
):
```

**Justification:**
- min_score=30 excludes 60.6% of 3-letter words
- Eliminates words starting with J, Q, X, Z
- Quality filtering should happen AFTER finding a solution

**Alternative (conservative):**
```python
min_score: int = 10,  # Compromise: allow most words, filter worst
```

---

#### Task 1.3: Increase Backtracking Candidate Limit
**File:** `cli/src/fill/autofill.py`  
**Line:** 468

**Current Code:**
```python
def _get_candidates(self, slot: Dict) -> List[Tuple[str, int]]:
    pattern = self.grid.get_pattern_for_slot(slot)
    candidates = self.pattern_matcher.find(
        pattern, min_score=self.min_score, max_results=100  # ← BUG: Too few
    )
    return candidates
```

**Fix:**
```python
def _get_candidates(self, slot: Dict) -> List[Tuple[str, int]]:
    pattern = self.grid.get_pattern_for_slot(slot)
    candidates = self.pattern_matcher.find(
        pattern, min_score=self.min_score, max_results=1000  # ← FIX: More options
    )
    return candidates
```

**Justification:**
- During backtracking, top 100 candidates might all fail
- Need more options to explore before giving up
- Still capped for performance (not unlimited)

---

#### Task 1.4: Validate Phase 1 Fixes
**Test Grids:**
1. `simple_fillable_11x11.json` (38 slots)
2. Create new 7×7 grid (20 slots)
3. Create new 9×9 grid (30 slots)

**Test Script:**
```python
#!/usr/bin/env python3
"""Test autofill after Phase 1 fixes."""

import json
from cli.src.core.grid import Grid
from cli.src.fill.word_list import WordList
from cli.src.fill.autofill import Autofill

# Load wordlist
wl = WordList.from_file('data/wordlists/comprehensive.txt', use_cache=True)

# Test grids
grids = [
    'simple_fillable_11x11.json',
    'test_7x7.json',
    'test_9x9.json',
]

for grid_file in grids:
    print(f"\nTesting {grid_file}...")
    with open(grid_file) as f:
        grid = Grid.from_dict(json.load(f))
    
    autofill = Autofill(grid, wl, timeout=30, algorithm='trie')
    result = autofill.fill()
    
    print(f"  Success: {result.success}")
    print(f"  Filled: {result.slots_filled}/{result.total_slots}")
    print(f"  Time: {result.time_elapsed:.2f}s")
    print(f"  Iterations: {result.iterations}")
```

**Success Criteria:**
- ✅ 7×7 grid: 100% filled
- ✅ 9×9 grid: 80%+ filled
- ✅ 11×11 grid: 50%+ filled (partial success acceptable)
- ✅ No "0 iterations" failures

---

### Phase 2: Advanced Optimizations (Priority: HIGH)
**Time Estimate:** 3-5 hours  
**Risk Level:** Medium (new algorithm logic)  
**Expected Impact:** 80%+ success rate on 11×11, faster solving

#### Task 2.1: Stratified Domain Sampling
**Objective:** If domain > 10,000 words, sample strategically to ensure letter diversity

**New Method in `autofill.py`:**
```python
def _stratified_sample(
    self, 
    candidates: List[Tuple[str, int]], 
    target_size: int = 5000
) -> Set[str]:
    """
    Sample domain ensuring letter diversity across score ranges.
    
    Strategy:
    1. Divide candidates into score deciles
    2. Sample proportionally from each decile
    3. Ensure all 26 letters represented at each position
    
    Args:
        candidates: List of (word, score) tuples
        target_size: Target domain size
        
    Returns:
        Set of sampled words with good letter coverage
    """
    import random
    from collections import defaultdict
    
    # Group by score deciles
    sorted_cands = sorted(candidates, key=lambda x: x[1], reverse=True)
    decile_size = len(sorted_cands) // 10
    
    sampled = set()
    per_decile = target_size // 10
    
    # Sample from each decile
    for i in range(10):
        start = i * decile_size
        end = start + decile_size if i < 9 else len(sorted_cands)
        decile = sorted_cands[start:end]
        
        if decile:
            sample_size = min(per_decile, len(decile))
            sample = random.sample(decile, sample_size)
            sampled.update(word for word, score in sample)
    
    # Verify letter coverage
    pattern_length = len(candidates[0][0]) if candidates else 0
    for pos in range(pattern_length):
        letters_at_pos = {word[pos] for word in sampled if pos < len(word)}
        missing = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ') - letters_at_pos
        
        # If missing critical letters, add them
        if missing:
            for letter in missing:
                matching = [w for w, s in candidates if w[pos] == letter]
                if matching:
                    sampled.add(matching[0])  # Add highest-scored word with this letter
    
    return sampled
```

**Integration in `_initialize_csp`:**
```python
def _initialize_csp(self, slots: List[Dict]) -> None:
    # ... existing code ...
    
    for idx, slot in enumerate(slots):
        pattern = self.grid.get_pattern_for_slot(slot)
        candidates = self.pattern_matcher.find(
            pattern,
            min_score=self.min_score,
            max_results=None,  # Get all
        )
        
        # Apply stratified sampling if domain too large
        if len(candidates) > 10000:
            self.domains[idx] = self._stratified_sample(candidates, target_size=5000)
        else:
            self.domains[idx] = {word for word, score in candidates}
```

**Testing:**
```python
# Test letter coverage
def test_stratified_sampling():
    candidates = matcher.find('???', min_score=0, max_results=None)
    sampled = autofill._stratified_sample(candidates, 1000)
    
    # Check all letters represented
    first_letters = {w[0] for w in sampled}
    assert len(first_letters) >= 24, f"Only {len(first_letters)} letters covered"
```

---

#### Task 2.2: Implement MAC (Maintaining Arc Consistency)
**Objective:** Run AC-3 after each variable assignment to prune domains earlier

**New Method:**
```python
def _ac3_incremental(self, assigned_slot_id: int) -> bool:
    """
    Run AC-3 starting from a newly assigned slot.
    
    More efficient than full AC-3: only propagates constraints
    from the assigned slot outward.
    
    Args:
        assigned_slot_id: Slot that was just filled
        
    Returns:
        True if consistent, False if any domain becomes empty
    """
    from collections import deque
    
    # Initialize queue with arcs FROM assigned slot
    queue = deque()
    for other_id, pos1, pos2 in self.constraints.get(assigned_slot_id, []):
        queue.append((other_id, assigned_slot_id, pos2, pos1))
    
    # Standard AC-3 loop
    while queue:
        slot_id, other_id, pos1, pos2 = queue.popleft()
        
        if self._revise(slot_id, other_id, pos1, pos2):
            if len(self.domains[slot_id]) == 0:
                return False  # Domain wipeout
            
            # Add affected arcs
            for neighbor_id, my_pos, neighbor_pos in self.constraints[slot_id]:
                if neighbor_id != other_id:
                    queue.append((neighbor_id, slot_id, neighbor_pos, my_pos))
    
    return True
```

**Update Backtracking:**
```python
def _backtrack_with_mac(self, slots: List[Dict], current_index: int) -> bool:
    """Backtracking with MAC (Maintaining Arc Consistency)."""
    
    self.iterations += 1
    
    # Check timeout
    if time.time() - self.start_time > self.timeout:
        raise TimeoutError("Autofill timeout")
    
    # Base case
    if current_index >= len(slots):
        return True
    
    slot = slots[current_index]
    
    # Skip if already filled
    pattern = self.grid.get_pattern_for_slot(slot)
    if "?" not in pattern:
        return self._backtrack_with_mac(slots, current_index + 1)
    
    # Get candidates
    candidates = self._get_candidates(slot)
    if not candidates:
        return False
    
    # Try each candidate
    for word, score in candidates:
        if word in self.used_words:
            continue
        
        # Place word
        self.grid.place_word(word, slot["row"], slot["col"], slot["direction"])
        self.used_words.add(word)
        
        # Save domains (for backtracking)
        saved_domains = {k: v.copy() for k, v in self.domains.items()}
        
        # Run incremental AC-3 from this slot
        slot_id = self.slot_id_map[(slot["row"], slot["col"], slot["direction"])]
        
        if self._ac3_incremental(slot_id):
            # AC-3 succeeded, recurse
            if self._backtrack_with_mac(slots, current_index + 1):
                return True
        
        # Backtrack: restore domains and remove word
        self.domains = saved_domains
        self.grid.remove_word(slot["row"], slot["col"], slot["length"], slot["direction"])
        self.used_words.remove(word)
    
    return False
```

**Enable MAC:**
```python
def fill(self, interactive: bool = False, use_mac: bool = True) -> FillResult:
    """Fill grid using CSP with optional MAC."""
    # ... initialization ...
    
    # Choose algorithm
    if use_mac:
        success = self._backtrack_with_mac(slots, 0)
    else:
        success = self._backtrack(slots, 0)  # Original
    
    # ... return result ...
```

---

#### Task 2.3: Domain Save/Restore Optimization
**Objective:** Efficient domain snapshots for backtracking

**Current Issue:** Copying all domains on every backtrack is O(n*m) where n=slots, m=domain size

**Optimization:**
```python
class DomainStack:
    """Efficient domain state management for backtracking."""
    
    def __init__(self, initial_domains: Dict[int, Set[str]]):
        self.domains = initial_domains
        self.snapshots = []  # Stack of changes
    
    def push_snapshot(self):
        """Save current state."""
        self.snapshots.append({})
    
    def record_change(self, slot_id: int, old_domain: Set[str]):
        """Record a domain change for current snapshot."""
        if self.snapshots:
            if slot_id not in self.snapshots[-1]:
                self.snapshots[-1][slot_id] = old_domain.copy()
    
    def pop_snapshot(self):
        """Restore to previous state."""
        if self.snapshots:
            changes = self.snapshots.pop()
            for slot_id, old_domain in changes.items():
                self.domains[slot_id] = old_domain
    
    def get_domain(self, slot_id: int) -> Set[str]:
        """Get current domain for slot."""
        return self.domains.get(slot_id, set())
    
    def set_domain(self, slot_id: int, domain: Set[str]):
        """Update domain (records change automatically)."""
        old = self.domains.get(slot_id, set())
        self.record_change(slot_id, old)
        self.domains[slot_id] = domain
```

**Integration:**
```python
# In __init__:
self.domain_stack = None  # Initialize in fill()

# In fill():
self.domain_stack = DomainStack(self.domains)

# In _backtrack_with_mac:
# Before trying a word:
self.domain_stack.push_snapshot()

# ... try assignment ...

# On failure:
self.domain_stack.pop_snapshot()
```

---

#### Task 2.4: Benchmark Phase 2
**Test Suite:**
```python
import time
import json

def benchmark_algorithms():
    """Compare original vs MAC vs MAC+optimizations."""
    
    grids = [
        ('simple_fillable_11x11.json', 38),
        ('test_9x9.json', 30),
        ('test_7x7.json', 20),
    ]
    
    algorithms = [
        ('Original (fixed)', {'use_mac': False}),
        ('MAC', {'use_mac': True}),
    ]
    
    results = []
    
    for grid_file, slots in grids:
        for alg_name, params in algorithms:
            grid = load_grid(grid_file)
            autofill = Autofill(grid, word_list, **params)
            
            start = time.time()
            result = autofill.fill()
            elapsed = time.time() - start
            
            results.append({
                'grid': grid_file,
                'algorithm': alg_name,
                'success': result.success,
                'filled': result.slots_filled,
                'total': slots,
                'time': elapsed,
                'iterations': result.iterations
            })
    
    # Print comparison table
    print_benchmark_table(results)
```

**Success Criteria:**
- ✅ MAC solves grids with 50-90% fewer iterations
- ✅ Time per iteration is acceptable (< 2x slower)
- ✅ Overall solve time is faster or comparable

---

### Phase 3: State-of-the-Art Enhancements (Priority: MEDIUM)
**Time Estimate:** 4-8 hours  
**Risk Level:** Medium-High (complex algorithms)  
**Expected Impact:** 95%+ success rate, handles 15×15 grids

#### Task 3.1: Implement True LCV (Least Constraining Value)
**Objective:** Choose words that preserve most options for neighbors

**Current Issue:** Candidates sorted by score, not by constraint impact

**New Implementation:**
```python
def _get_candidates_lcv(self, slot: Dict) -> List[Tuple[str, int]]:
    """
    Get candidates sorted by Least Constraining Value.
    
    For each candidate word, count how many options remain
    for crossing slots. Prefer words that leave more options.
    """
    pattern = self.grid.get_pattern_for_slot(slot)
    candidates = self.pattern_matcher.find(
        pattern, min_score=self.min_score, max_results=1000
    )
    
    # Calculate constraint impact for each candidate
    scored_candidates = []
    
    for word, quality_score in candidates:
        if word in self.used_words:
            continue
        
        # Temporarily place word
        self.grid.place_word(word, slot["row"], slot["col"], slot["direction"])
        
        # Count remaining options for crossing slots
        total_options = 0
        crossing_slots = self._get_crossing_slots(slot, self.slot_list)
        
        for crossing in crossing_slots:
            crossing_pattern = self.grid.get_pattern_for_slot(crossing)
            if '?' in crossing_pattern:
                num_options = self.pattern_matcher.count_matches(
                    crossing_pattern, 
                    min_score=self.min_score
                )
                total_options += num_options
        
        # Remove word
        self.grid.remove_word(slot["row"], slot["col"], slot["length"], slot["direction"])
        
        # Higher total_options = less constraining = better
        scored_candidates.append((word, quality_score, total_options))
    
    # Sort by: 1) most options preserved, 2) quality score
    scored_candidates.sort(key=lambda x: (-x[2], -x[1]))
    
    return [(word, score) for word, score, _ in scored_candidates]
```

**Performance Optimization (Caching):**
```python
def _get_candidates_lcv_cached(self, slot: Dict) -> List[Tuple[str, int]]:
    """LCV with caching to avoid redundant pattern matches."""
    
    # Cache key: current grid state hash + slot
    cache_key = (self._grid_hash(), slot["row"], slot["col"], slot["direction"])
    
    if cache_key in self._lcv_cache:
        return self._lcv_cache[cache_key]
    
    result = self._get_candidates_lcv(slot)
    self._lcv_cache[cache_key] = result
    return result
```

---

#### Task 3.2: Iterative Deepening with Quality Tiers
**Objective:** Try high-quality words first, relax if needed

**Implementation:**
```python
def fill_iterative_deepening(self) -> FillResult:
    """
    Fill grid with iterative quality relaxation.
    
    Tries to find solution with increasingly lower min_score
    thresholds until success or all options exhausted.
    """
    start_time = time.time()
    
    # Quality tiers to try
    min_score_tiers = [50, 40, 30, 20, 10, 5, 0]
    
    best_result = None
    
    for min_score in min_score_tiers:
        # Check timeout
        if time.time() - start_time > self.timeout:
            break
        
        print(f"Attempting with min_score={min_score}...")
        
        # Reset state
        self.min_score = min_score
        self.used_words = set()
        self.iterations = 0
        
        # Get fresh slots
        slots = self.grid.get_empty_slots()
        if not slots:
            return FillResult(success=True, ...)
        
        # Rebuild domains with new threshold
        self._initialize_csp(slots)
        
        # Try AC-3
        if not self._ac3():
            print(f"  AC-3 failed at min_score={min_score}, trying lower...")
            continue
        
        # Sort slots
        slots = self._sort_slots_by_constraint(slots)
        
        # Try to fill
        try:
            success = self._backtrack_with_mac(slots, 0)
        except TimeoutError:
            success = False
        
        # Calculate result
        remaining = self.grid.get_empty_slots()
        slots_filled = len(slots) - len(remaining)
        
        result = FillResult(
            success=success,
            grid=self.grid,
            time_elapsed=time.time() - start_time,
            slots_filled=slots_filled,
            total_slots=len(slots),
            problematic_slots=remaining if not success else [],
            iterations=self.iterations
        )
        
        # Track best result
        if best_result is None or slots_filled > best_result.slots_filled:
            best_result = result
        
        # If we found complete solution, return it
        if success:
            print(f"  SUCCESS with min_score={min_score}!")
            return result
    
    # Return best partial result
    return best_result if best_result else FillResult(
        success=False,
        grid=self.grid,
        time_elapsed=time.time() - start_time,
        slots_filled=0,
        total_slots=len(self.grid.get_empty_slots()),
        problematic_slots=self.grid.get_empty_slots(),
        iterations=self.iterations
    )
```

**CLI Integration:**
```python
# In cli.py
@click.option('--iterative/--no-iterative', default=False,
              help='Use iterative deepening with quality tiers')

def fill(grid_file, wordlists, timeout, algorithm, iterative, ...):
    # ...
    if iterative:
        result = autofill.fill_iterative_deepening()
    else:
        result = autofill.fill()
```

---

#### Task 3.3: Comprehensive Test Suite
**Create:** `cli/tests/integration/test_empty_grids.py`

```python
"""Integration tests for empty grid filling."""

import pytest
import json
from src.core.grid import Grid
from src.fill.word_list import WordList
from src.fill.autofill import Autofill

@pytest.fixture(scope="module")
def word_list():
    """Load comprehensive wordlist once for all tests."""
    return WordList.from_file(
        'data/wordlists/comprehensive.txt', 
        use_cache=True
    )

class TestEmptyGrids:
    """Test autofill on completely empty grids."""
    
    def test_empty_7x7_simple_pattern(self, word_list):
        """Test 7×7 grid with simple cross pattern."""
        grid = Grid(7)
        grid.set_black_square(3, 3)  # Center black
        
        autofill = Autofill(grid, word_list, timeout=30, algorithm='trie')
        result = autofill.fill()
        
        assert result.success, "Should fill 7×7 empty grid"
        assert result.slots_filled == result.total_slots
        assert result.time_elapsed < 10, "Should complete in < 10s"
    
    def test_empty_11x11_standard(self, word_list):
        """Test standard 11×11 grid with black square pattern."""
        with open('simple_fillable_11x11.json') as f:
            grid = Grid.from_dict(json.load(f))
        
        autofill = Autofill(grid, word_list, timeout=60, algorithm='trie')
        result = autofill.fill()
        
        assert result.success or result.slots_filled > 30, \
            f"Should fill most slots, got {result.slots_filled}/{result.total_slots}"
    
    def test_empty_11x11_with_mac(self, word_list):
        """Test MAC algorithm on 11×11 grid."""
        with open('simple_fillable_11x11.json') as f:
            grid = Grid.from_dict(json.load(f))
        
        autofill = Autofill(grid, word_list, timeout=60, algorithm='trie')
        result = autofill.fill(use_mac=True)
        
        assert result.iterations < 1000, "MAC should reduce search space"
    
    def test_iterative_deepening_quality(self, word_list):
        """Test that iterative deepening finds high-quality solutions."""
        with open('simple_fillable_11x11.json') as f:
            grid = Grid.from_dict(json.load(f))
        
        autofill = Autofill(grid, word_list, timeout=120, algorithm='trie')
        result = autofill.fill_iterative_deepening()
        
        if result.success:
            # Check word quality
            slots = grid.get_word_slots()
            words = [grid.get_pattern_for_slot(s) for s in slots]
            scores = [word_list._score_word(w) for w in words if '?' not in w]
            
            avg_score = sum(scores) / len(scores) if scores else 0
            assert avg_score >= 25, f"Average word score should be >= 25, got {avg_score}"
    
    @pytest.mark.slow
    def test_empty_15x15_grid(self, word_list):
        """Test larger 15×15 grid (slow test)."""
        grid = Grid(15)
        # Add NYT-style black square pattern
        # ... set black squares ...
        
        autofill = Autofill(grid, word_list, timeout=300, algorithm='trie')
        result = autofill.fill(use_mac=True)
        
        # May not fully solve, but should make significant progress
        fill_rate = result.slots_filled / result.total_slots
        assert fill_rate > 0.5, f"Should fill >50% of 15×15 grid, got {fill_rate:.1%}"
```

**Test for Letter Coverage:**
```python
class TestDomainQuality:
    """Test domain initialization quality."""
    
    def test_letter_coverage_3letter(self, word_list):
        """Ensure 3-letter domains cover all letters."""
        matcher = TriePatternMatcher(word_list)
        candidates = matcher.find('???', min_score=0, max_results=None)
        
        # Check starting letters
        first_letters = {word for word, score in candidates}
        first_letters = {w[0] for w in first_letters}
        
        # Should have at least 24 of 26 letters (J, Q might be rare)
        assert len(first_letters) >= 24, \
            f"Only {len(first_letters)} starting letters found: {sorted(first_letters)}"
    
    def test_stratified_sampling_diversity(self, word_list):
        """Test that stratified sampling preserves letter diversity."""
        autofill = Autofill(Grid(11), word_list)
        matcher = TriePatternMatcher(word_list)
        
        candidates = matcher.find('???', min_score=0, max_results=None)
        sampled = autofill._stratified_sample(candidates, target_size=1000)
        
        first_letters = {w[0] for w in sampled}
        assert len(first_letters) >= 20, \
            f"Sampling lost letter diversity: only {len(first_letters)} letters"
```

---

#### Task 3.4: Performance Testing on Large Grids
**Create:** `cli/tests/performance/benchmark_grids.py`

```python
"""Performance benchmarks for different grid sizes."""

import time
import json
from src.core.grid import Grid
from src.fill.word_list import WordList
from src.fill.autofill import Autofill

def benchmark_grid_sizes():
    """Benchmark performance on various grid sizes."""
    
    wl = WordList.from_file('data/wordlists/comprehensive.txt', use_cache=True)
    
    test_cases = [
        ('5×5 minimal', 'test_5x5.json', 6),
        ('7×7 simple', 'test_7x7.json', 20),
        ('9×9 medium', 'test_9x9.json', 30),
        ('11×11 standard', 'simple_fillable_11x11.json', 38),
        ('15×15 large', 'test_15x15.json', 80),
    ]
    
    results = []
    
    for name, grid_file, expected_slots in test_cases:
        print(f"\nTesting {name}...")
        
        with open(grid_file) as f:
            grid = Grid.from_dict(json.load(f))
        
        # Test with different algorithms
        configs = [
            ('Basic (fixed)', {'use_mac': False}),
            ('MAC', {'use_mac': True}),
            ('Iterative', {'iterative': True}),
        ]
        
        for config_name, params in configs:
            autofill = Autofill(grid.clone(), wl, timeout=300, algorithm='trie')
            
            start = time.time()
            
            if params.get('iterative'):
                result = autofill.fill_iterative_deepening()
            else:
                result = autofill.fill(use_mac=params.get('use_mac', False))
            
            elapsed = time.time() - start
            
            results.append({
                'grid': name,
                'algorithm': config_name,
                'success': result.success,
                'filled': f"{result.slots_filled}/{result.total_slots}",
                'fill_rate': result.slots_filled / result.total_slots if result.total_slots > 0 else 0,
                'time': f"{elapsed:.2f}s",
                'iterations': result.iterations,
                'iter_per_sec': result.iterations / elapsed if elapsed > 0 else 0,
            })
    
    # Print results table
    print("\n" + "="*80)
    print("PERFORMANCE BENCHMARK RESULTS")
    print("="*80)
    print(f"{'Grid':<15} {'Algorithm':<15} {'Success':<10} {'Filled':<10} {'Time':<10} {'Iters':<10}")
    print("-"*80)
    
    for r in results:
        print(f"{r['grid']:<15} {r['algorithm']:<15} "
              f"{'✓' if r['success'] else '✗':<10} "
              f"{r['filled']:<10} {r['time']:<10} {r['iterations']:<10}")

if __name__ == '__main__':
    benchmark_grid_sizes()
```

---

## 🎯 Success Criteria Summary

### Phase 1 Success (Minimum Viable Fix):
- ✅ AC-3 no longer fails immediately on empty grids
- ✅ At least 50% of 11×11 grid slots filled
- ✅ No "0 iterations" failures

### Phase 2 Success (Good Performance):
- ✅ 80%+ of 11×11 grid slots filled
- ✅ MAC reduces iterations by 50%+
- ✅ Solve time < 30 seconds for 11×11

### Phase 3 Success (Production Ready):
- ✅ 95%+ success rate on 11×11 empty grids
- ✅ 80%+ success rate on 15×15 empty grids
- ✅ Average word quality score >= 30
- ✅ Comprehensive test coverage

---

## 📊 Estimated Timeline

| Phase | Tasks | Time | Cumulative |
|-------|-------|------|------------|
| Phase 1 | 4 tasks | 1-2 hours | 1-2 hours |
| Phase 2 | 4 tasks | 3-5 hours | 4-7 hours |
| Phase 3 | 4 tasks | 4-8 hours | 8-15 hours |

**Total:** 8-15 hours for complete implementation

**Recommended Approach:**
1. Implement Phase 1 → Test → Commit
2. Implement Phase 2 → Benchmark → Commit
3. Implement Phase 3 → Full test suite → Commit

---

## 🔄 Rollback Plan

If any phase causes regressions:

1. **Git branches for each phase:**
   - `phase1-critical-fixes`
   - `phase2-mac-optimization`
   - `phase3-advanced-algorithms`

2. **Feature flags in code:**
   ```python
   class Autofill:
       def __init__(self, ..., use_mac=True, use_lcv=True):
           self.use_mac = use_mac
           self.use_lcv = use_lcv
   ```

3. **Backwards compatibility:**
   - Keep original `_backtrack()` method
   - Add `_backtrack_with_mac()` as alternative
   - CLI flag: `--classic-algorithm` to use old approach

---

**Ready to begin implementation?**
