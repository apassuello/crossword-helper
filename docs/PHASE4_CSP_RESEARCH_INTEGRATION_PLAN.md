# Phase 4: CSP Research Integration Plan

**Date:** 2025-12-24
**Status:** Research Complete, Ready for Implementation
**Target:** 90%+ completion, 90%+ quality, 30-300s time budget for 15×15/21×21 grids

---

## Executive Summary

Analysis of two comprehensive CSP research reports reveals that our Phase 1 + Phase 2 implementation is **fundamentally sound** but has **three critical gaps** and **one refuted technique**:

**✅ Validated (Keep/Enhance):**
- Direction interleaving principle (currently static, needs upgrade to dynamic MRV)
- Length-dependent quality thresholds (3-letter: 15, 6+: 45-50)
- Min-conflicts repair (enhance with tabu list + clustering)
- Crosswordese filtering (already implemented correctly)
- Conflict-directed backjumping (already implemented in repair)

**❌ Refuted (Remove/Replace):**
- **Adaptive beam width 8→5→3→1 is NOT validated** - research shows beam quality is non-monotonic; narrowing can worsen solutions. Replace with **constant beam width + diversity mechanisms**.

**🔧 Critical Gaps (High Priority):**
1. **Constraint propagation:** Upgrade from forward checking to **MAC (Maintaining Arc Consistency)** → 10-100x fewer backtracks
2. **Variable ordering:** Replace static length-first with **dynamic MRV + degree** → 50-80% faster search
3. **Diverse Beam Search:** Add group-based diversity penalty to prevent beam collapse → Better solution quality

**🎯 Medium Priority Enhancements:**
4. **LCV value ordering:** Prefer words leaving more options for crossings
5. **Stratified shuffling:** Per-expansion, preserve quality tiers
6. **Tabu search in repair:** Prevent cycling, tenure 5-15 iterations
7. **Conflict clustering:** Repair connected conflict groups together

---

## Current Implementation Analysis

### What We Have (Phase 1 + Phase 2)

#### ✅ Well-Implemented:
1. **Crosswordese filtering** (`cli/src/fill/crosswordese.py`)
   - Length-based penalty system: 3-4 letters OK, 7+ filtered
   - Aligned with constructor community standards
   - **Research says:** ✅ Keep as-is

2. **Theme entry support** (`beam_search_autofill.py:_prioritize_theme_entries`)
   - Pre-fills NON-NEGOTIABLE words before search
   - Marks theme words as used to prevent duplicates
   - **Research says:** ✅ Keep as-is

3. **Conflict-directed backjumping** (`iterative_repair.py:_identify_culprit_slot`)
   - Identifies root cause slot using heuristic (alternatives × conflicts)
   - **Research says:** ✅ Good foundation, enhance with conflict sets

4. **Min-conflicts repair** (`iterative_repair.py:fill`)
   - Complete assignment + iterative repair
   - **Research says:** ✅ Theoretically sound (Minton et al. 1992), enhance with tabu

#### ⚠️ Needs Refinement:
1. **Direction interleaving** (`beam_search_autofill.py:_sort_slots_by_constraint`)
   - **Current:** Static length-first with ACROSS/DOWN interleaving within length groups
   - **Research says:** ⚠️ Principle correct, but implementation is static not dynamic
   - **Fix:** Replace with dynamic MRV that recomputes after each assignment

2. **Length-dependent quality** (`beam_search_autofill.py:_get_min_score_for_length`)
   - **Current:** 3-letter: 0, 4: 10, 5-6: 30, 7-8: 50, 9+: 70
   - **Research says:** ⚠️ Thresholds slightly low
   - **Fix:** 3-letter: 15, 4: 25, 5: 35, 6+: 45-60 (Matt Gaffney's "breakout length")

3. **Predictive viability** (`beam_search_autofill.py:_evaluate_state_viability`)
   - **Current:** Checks domain size and applies risk penalties
   - **Research says:** ⚠️ Concept correct, but should use MAC propagation simulation
   - **Fix:** Simulate 1-level MAC propagation to count surviving candidates

#### ❌ Refuted - Remove:
1. **Adaptive beam width** (`beam_search_autofill.py:_get_adaptive_beam_width`)
   - **Current:** Narrows from 10→5→3→1 as search progresses
   - **Research says:** ❌ **NOT VALIDATED** - Beam quality is non-monotonic (Cohen et al. 2019)
   - **Fix:** Use constant beam width (5-10) + Diverse Beam Search for quality

#### ❌ Missing - Critical Gaps:
1. **MAC propagation** - Only doing forward checking (1-level), not transitive propagation
2. **Dynamic MRV** - Variable ordering is static (pre-computed), not recomputed per assignment
3. **LCV value ordering** - Only using word score, not counting constraints on neighbors
4. **Diverse Beam Search** - No diversity penalty to prevent beam collapse
5. **Tabu list** - Repair can cycle between same states
6. **Stratified shuffling** - Not shuffling candidates to break alphabetical bias

---

## Research-Validated Techniques

### Priority 1: Critical Fixes (1-2 days)

#### 1.1 Replace Adaptive Beam Width with Diverse Beam Search
**Evidence:** Cohen et al. (2019) "Beam Search Curse" - narrowing can worsen quality
**Impact:** Prevent beam collapse, 300% increase in distinct solutions

**Current Code (REMOVE):**
```python
# cli/src/fill/beam_search_autofill.py:_get_adaptive_beam_width
def _get_adaptive_beam_width(self, slot_index: int, total_slots: int) -> int:
    progress = slot_index / max(total_slots, 1)
    if progress < 0.25:
        return self.beam_width * 2     # ❌ REMOVE - not validated
    elif progress < 0.60:
        return self.beam_width
    elif progress < 0.85:
        return max(3, self.beam_width // 2)
    else:
        return 1  # Greedy completion
```

**New Implementation:**
```python
def diverse_beam_search(
    self,
    beam: List[BeamState],
    slot: Dict,
    candidates: List[Tuple[str, int]],
    num_groups: int = 4,
    diversity_lambda: float = 0.5
) -> List[BeamState]:
    """
    Diverse Beam Search (Vijayakumar et al., 2016 AAAI).
    Partition beam into groups with diversity penalty between groups.
    """
    groups = []
    beams_per_group = self.beam_width // num_groups

    for state in beam:
        # For each beam state, expand with diversity
        group_candidates = []

        for word, score in candidates:
            if word in state.used_words:
                continue

            # Calculate diversity penalty (Hamming distance to previous groups)
            diversity_penalty = 0
            if groups:
                for prev_group in groups:
                    for prev_state in prev_group:
                        # Count differing letters at crossing positions
                        diff = self._hamming_distance_at_crossings(
                            word, prev_state, slot
                        )
                        diversity_penalty += diff
                diversity_penalty /= sum(len(g) for g in groups)

            # Augmented score = quality + diversity bonus
            augmented_score = score + diversity_lambda * diversity_penalty
            group_candidates.append((word, augmented_score, state))

        # Select top candidates for this group
        group_candidates.sort(key=lambda x: -x[1])
        group = []
        for word, _, base_state in group_candidates[:beams_per_group]:
            new_state = self._extend_state(base_state, slot, word)
            group.append(new_state)

        if group:
            groups.append(group)

    # Flatten groups into single beam
    return [state for group in groups for state in group][:self.beam_width]

def _hamming_distance_at_crossings(
    self, word: str, state: BeamState, slot: Dict
) -> int:
    """Count differing letters at intersection positions"""
    diff_count = 0
    for crossing_slot in self._get_crossing_slots(slot):
        if crossing_slot not in state.slot_assignments:
            continue
        crossing_word = state.slot_assignments[crossing_slot]
        # Get intersection positions
        my_pos, their_pos = self._get_intersection_positions(slot, crossing_slot)
        if word[my_pos] != crossing_word[their_pos]:
            diff_count += 1
    return diff_count
```

**Effort:** 4 hours | **Priority:** HIGH

---

#### 1.2 Implement Dynamic MRV + Degree Variable Ordering
**Evidence:** Ginsberg (1990) "dynamic ordering is NECESSARY for solving difficult problems"
**Impact:** 50-80% faster search, natural direction interleaving

**Current Code (MODIFY):**
```python
# cli/src/fill/beam_search_autofill.py:_sort_slots_by_constraint
def _sort_slots_by_constraint(self, slots: List[Dict]) -> List[Dict]:
    """Sort slots by length-first ordering with DIRECTION INTERLEAVING."""
    from collections import defaultdict

    length_groups = defaultdict(list)
    for slot in slots:
        length_groups[slot['length']].append(slot)

    # ❌ STATIC ORDERING - computed once, doesn't adapt
```

**New Implementation:**
```python
def _select_next_slot_dynamic_mrv(
    self,
    unfilled_slots: List[Dict],
    current_state: BeamState
) -> Optional[Dict]:
    """
    Dynamic MRV + Degree heuristic (recomputed per assignment).

    MRV: Select slot with fewest valid candidates
    Degree: Tiebreaker - most constraints on unfilled slots
    Length: Secondary tiebreaker - longer first
    """
    if not unfilled_slots:
        return None

    candidates = []
    for slot in unfilled_slots:
        # Get pattern given current assignments
        pattern = current_state.grid.get_pattern_for_slot(slot)
        min_score = self._get_min_score_for_length(slot['length'])

        # Count CURRENT valid candidates (dynamic!)
        valid_candidates = self.pattern_matcher.find(pattern, min_score=min_score)
        available = [w for w, s in valid_candidates if w not in current_state.used_words]
        domain_size = len(available)

        # Count unfilled crossing slots (degree)
        crossing_count = sum(
            1 for crossing in self._get_crossing_slots(slot)
            if crossing not in current_state.slot_assignments
        )

        candidates.append((slot, domain_size, crossing_count, slot['length']))

    # Sort by: domain_size ASC, degree DESC, length DESC
    candidates.sort(key=lambda x: (x[1], -x[2], -x[3]))

    return candidates[0][0] if candidates else None
```

**Integration:** Replace `sorted_slots` iteration with dynamic selection:
```python
# In fill() method:
# OLD: for slot_index, slot in enumerate(sorted_slots):
# NEW:
unfilled_slots = list(all_slots)
slot_index = 0

while unfilled_slots:
    # Dynamically select next slot based on CURRENT beam states
    slot = self._select_next_slot_dynamic_mrv(unfilled_slots, beam[0])

    # ... expand beam for this slot ...

    unfilled_slots.remove(slot)
    slot_index += 1
```

**Effort:** 6 hours | **Priority:** CRITICAL

---

#### 1.3 Upgrade to MAC (Maintaining Arc Consistency) Propagation
**Evidence:** Sabin & Freuder (1994) "MAC is most efficient for hard CSPs"
**Impact:** 10-100x fewer backtracks

**New Implementation:**
```python
def _mac_propagate(
    self,
    slot: Dict,
    word: str,
    state: BeamState
) -> Tuple[bool, Dict[str, Set[str]], Set[str]]:
    """
    Maintaining Arc Consistency after assigning word to slot.

    Returns:
        (is_viable, pruned_domains, conflict_set)
    """
    # Initialize queue with all neighbors of assigned slot
    queue = [(neighbor, slot) for neighbor in self._get_crossing_slots(slot)]
    pruned = {}  # slot -> set of removed words
    conflict_set = set()

    # Make copy of domains (don't modify state.grid yet)
    domains = self._get_current_domains(state)

    while queue:
        (xi, xj) = queue.pop(0)

        # Revise xi's domain based on xj's assignment
        removed = self._revise_domain(xi, xj, domains, state)

        if removed:
            if xi not in pruned:
                pruned[xi] = set()
            pruned[xi].update(removed)

            # Domain wipeout - record conflict
            if len(domains[xi]) == 0:
                conflict_set.add(xj)
                return False, pruned, conflict_set

            # Add all OTHER neighbors of xi to queue (transitive propagation)
            for xk in self._get_crossing_slots(xi):
                if xk != xj and xk not in state.slot_assignments:
                    queue.append((xk, xi))

    return True, pruned, conflict_set

def _revise_domain(
    self,
    xi: Dict,
    xj: Dict,
    domains: Dict,
    state: BeamState
) -> Set[str]:
    """
    Remove values from xi's domain that have no support in xj.
    Returns set of removed words.
    """
    removed = set()

    # Get xj's current assignment or domain
    if xj in state.slot_assignments:
        xj_values = [state.slot_assignments[xj]]
    else:
        xj_values = domains[xj]

    # Get intersection position
    my_pos, their_pos = self._get_intersection_positions(xi, xj)

    for xi_word in list(domains[xi]):
        # Check if xi_word has support (compatible value) in xj
        has_support = any(
            xi_word[my_pos] == xj_word[their_pos]
            for xj_word in xj_values
        )

        if not has_support:
            domains[xi].discard(xi_word)
            removed.add(xi_word)

    return removed
```

**Integration:** Call MAC after each assignment in beam expansion:
```python
# In _expand_beam:
for word, score in candidates:
    # ... create new_state ...

    # MAC PROPAGATION
    is_viable, pruned, conflicts = self._mac_propagate(slot, word, new_state)

    if not is_viable:
        # Dead end detected - skip this candidate
        continue

    # Update state with pruned domains (for future lookups)
    new_state.pruned_domains = pruned

    expanded_beam.append(new_state)
```

**Effort:** 8 hours | **Priority:** CRITICAL

---

### Priority 2: Important Enhancements (2-3 days)

#### 2.1 Add LCV (Least Constraining Value) Ordering
**Evidence:** Russell & Norvig AIMA textbook - standard value ordering heuristic
**Impact:** Faster solution discovery

```python
def _order_values_lcv(
    self,
    slot: Dict,
    candidates: List[Tuple[str, int]],
    state: BeamState
) -> List[Tuple[str, int]]:
    """
    Order candidates by Least Constraining Value heuristic.
    Combine with word quality for final ordering.
    """
    lcv_scores = []

    for word, quality_score in candidates:
        # Count how many options this word eliminates for neighbors
        eliminated = 0

        for crossing_slot in self._get_crossing_slots(slot):
            if crossing_slot in state.slot_assignments:
                continue  # Already assigned

            pattern = state.grid.get_pattern_for_slot(crossing_slot)
            my_pos, their_pos = self._get_intersection_positions(slot, crossing_slot)

            # Count crossing candidates incompatible with word[my_pos]
            crossing_candidates = self.pattern_matcher.find(
                pattern, min_score=self._get_min_score_for_length(crossing_slot['length'])
            )

            for crossing_word, _ in crossing_candidates:
                if crossing_word[their_pos] != word[my_pos]:
                    eliminated += 1

        # Combined score: balance quality (want high) with constraint impact (want low)
        # Tune weight empirically (0.1 to 0.5)
        lcv_weight = 0.3
        combined_score = quality_score - lcv_weight * eliminated

        lcv_scores.append((word, combined_score))

    # Sort by combined score descending
    return sorted(lcv_scores, key=lambda x: -x[1])
```

**Effort:** 3 hours | **Priority:** MEDIUM

---

#### 2.2 Implement Stratified Shuffling (Per-Expansion)
**Evidence:** Diverse Beam Search (Vijayakumar 2016) - prevents alphabetical bias
**Impact:** Better exploration, avoid convergence

```python
def _stratified_shuffle(
    self,
    candidates: List[Tuple[str, int]],
    tier_percentiles: List[float] = [0.1, 0.3, 0.6, 1.0],
    seed: int = None
) -> List[Tuple[str, int]]:
    """
    Shuffle candidates within quality tiers to break alphabetical bias.

    Preserves quality gradient (top 10% stay near top) while breaking
    alphabetical ordering (which causes beam collapse).
    """
    import random

    if seed is not None:
        random.seed(seed)

    # Already sorted by quality descending
    n = len(candidates)

    result = []
    prev_idx = 0
    for percentile in tier_percentiles:
        end_idx = min(int(n * percentile), n)
        tier = candidates[prev_idx:end_idx]

        # Shuffle within tier
        random.shuffle(tier)
        result.extend(tier)

        prev_idx = end_idx

    return result
```

**Integration:** Apply in `_expand_beam` before selecting candidates:
```python
# Get candidates for this slot
all_candidates = self.pattern_matcher.find(pattern, min_score=min_score)

# Crosswordese filter
all_candidates = filter_crosswordese(all_candidates, slot['length'])

# LCV ordering
all_candidates = self._order_values_lcv(slot, all_candidates, state)

# STRATIFIED SHUFFLE (per-expansion, not once at startup)
all_candidates = self._stratified_shuffle(all_candidates)

# Take top K for beam expansion
candidates = all_candidates[:self.candidates_per_slot]
```

**Effort:** 2 hours | **Priority:** MEDIUM

---

#### 2.3 Enhance Repair with Tabu Search
**Evidence:** Minton et al. (1992), plateau escape mechanisms
**Impact:** Avoid cycling, faster convergence

```python
# In cli/src/fill/iterative_repair.py:fill method

# Add tabu list tracking
self.tabu_list = {}  # (slot_id, word) -> expiry_iteration
self.tabu_tenure = 7  # √n heuristic for 11×11
self.random_move_prob = 0.1

# In repair loop, before selecting repair slot:
for iteration in range(self.max_iterations):
    conflicts = self._find_conflicts()

    if not conflicts:
        return self._create_result(success=True)

    # ... existing conflict counting ...

    # Select variable: 50/50 random vs most-conflicted
    if random.random() < 0.5:
        slot_id = random.choice(list(slot_conflict_counts.keys()))
    else:
        culprit_slot_id = self._identify_culprit_slot(
            conflicts, worst_slot_id, all_slots
        )

    old_word = self.grid.get_word_at_slot(slot)

    # Value selection with tabu and random moves
    if random.random() < self.random_move_prob:
        # Random move for plateau escape
        alternatives = self._get_non_tabu_alternatives(slot_id, iteration)
        if alternatives:
            new_word = random.choice(alternatives)
        else:
            continue  # No valid moves
    else:
        # Min-conflicts with tabu aspiration
        new_word = self._min_conflicts_with_tabu(slot_id, iteration, conflicts)

    if new_word != old_word:
        self.grid.place_word(new_word, slot['row'], slot['col'], slot['direction'])
        # Add old assignment to tabu list
        self.tabu_list[(slot_id, old_word)] = iteration + self.tabu_tenure

def _min_conflicts_with_tabu(
    self, slot_id, current_iteration, conflicts
) -> str:
    """Select value minimizing conflicts, respecting tabu list."""
    slot = self._get_slot_by_id(slot_id, all_slots)
    pattern = self.grid.get_pattern_for_slot(slot)
    alternatives = self.pattern_matcher.find(pattern, min_score=self.min_score)

    best_word = None
    min_conflicts_count = float('inf')

    for word, score in alternatives:
        # Check tabu status
        is_tabu = (
            (slot_id, word) in self.tabu_list and
            self.tabu_list[(slot_id, word)] > current_iteration
        )

        # Count conflicts
        conflict_count = self._count_conflicts_for_word(slot, word, conflicts)

        # Aspiration criteria: accept tabu move if it's best-ever (zero conflicts)
        if conflict_count < min_conflicts_count:
            if not is_tabu or conflict_count == 0:
                min_conflicts_count = conflict_count
                best_word = word

    return best_word if best_word else self.grid.get_word_at_slot(slot)
```

**Effort:** 4 hours | **Priority:** MEDIUM

---

#### 2.4 Add Conflict Clustering for Repair
**Evidence:** Cascade effects in crosswords - repair connected groups
**Impact:** More efficient repair

```python
def _find_conflict_clusters(self, conflicts: List[Conflict]) -> List[Set[str]]:
    """Group conflicting slots into connected clusters (BFS)."""
    conflicting_slots = set()
    for conflict in conflicts:
        conflicting_slots.add(conflict.slot1_id)
        conflicting_slots.add(conflict.slot2_id)

    clusters = []
    visited = set()

    for slot_id in conflicting_slots:
        if slot_id in visited:
            continue

        # BFS to find connected conflict cluster
        cluster = set()
        queue = [slot_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue

            visited.add(current)
            if current in conflicting_slots:
                cluster.add(current)

                # Add crossing slots that are also conflicting
                slot = self._get_slot_by_id(current, all_slots)
                for crossing in self._get_crossing_slots(slot):
                    crossing_id = (crossing['row'], crossing['col'], crossing['direction'])
                    if crossing_id in conflicting_slots and crossing_id not in visited:
                        queue.append(crossing_id)

        if cluster:
            clusters.append(cluster)

    return clusters

# In repair loop:
clusters = self._find_conflict_clusters(conflicts)

# Repair largest cluster first (most interconnected conflicts)
clusters.sort(key=len, reverse=True)

for cluster in clusters:
    # Repair all slots in cluster together
    for slot_id in cluster:
        # ... min-conflicts repair ...
```

**Effort:** 3 hours | **Priority:** MEDIUM

---

### Priority 3: Optional Optimizations (1-2 days)

#### 3.1 Conflict Set Tracking for Smarter Backjumping
**Evidence:** Prosser (1993), Chen & van Beek (2001)
**Impact:** Avoid redundant search

```python
class ConflictTracker:
    def __init__(self):
        self.conflict_sets = {}  # slot -> set of slots that constrained it

    def record_pruning(self, slot_id, pruned_by_slot_id):
        """Record that slot's domain was reduced by pruned_by_slot"""
        if slot_id not in self.conflict_sets:
            self.conflict_sets[slot_id] = set()
        self.conflict_sets[slot_id].add(pruned_by_slot_id)

    def get_backjump_target(self, failed_slot_id, assignment_order):
        """Find earliest slot in conflict set to backjump to"""
        conflicts = self.conflict_sets.get(failed_slot_id, set())
        if not conflicts:
            return assignment_order[-1]  # Chronological if no info

        # Find most recent assignment in conflict set
        for slot_id in reversed(assignment_order):
            if slot_id in conflicts:
                return slot_id
        return assignment_order[-1]
```

**Integration:** Update MAC propagation to record conflicts:
```python
# In _mac_propagate:
removed = self._revise_domain(xi, xj, domains, state)

if removed:
    # Record that xj pruned xi's domain
    conflict_tracker.record_pruning(xi, xj)
```

**Effort:** 4 hours | **Priority:** LOW

---

#### 3.2 Adjust Length-Dependent Quality Thresholds
**Evidence:** Matt Gaffney's "breakout length" (6 letters)
**Impact:** Better alignment with constructor standards

```python
# Current (cli/src/fill/beam_search_autofill.py:_get_min_score_for_length)
def _get_min_score_for_length(self, length: int) -> int:
    if length <= 3:
        return 0    # Too low - should be 15
    elif length == 4:
        return 10   # Too low - should be 25
    elif length <= 6:
        return 30   # Too low - should be 35-45
    elif length <= 8:
        return 50   # OK
    else:
        return 70   # OK

# Recommended (from research):
def _get_min_score_for_length(self, length: int) -> int:
    thresholds = {
        3: 15,   # More selective for short words
        4: 25,   # Moderate standards
        5: 35,   # Stricter for 5-letter
        6: 45,   # "Breakout length" - higher expectations
        7: 50,   # Long words should sparkle
        8: 55,
        9: 60,
    }
    return thresholds.get(length, 50 + (length - 7) * 2)
```

**Effort:** 15 minutes | **Priority:** LOW

---

## Implementation Roadmap

### Week 1: Critical Fixes (Must Do)

**Days 1-2: Remove Adaptive Beam + Add Diverse Beam Search**
- Remove `_get_adaptive_beam_width` method
- Implement `diverse_beam_search` with group-based diversity
- Add `_hamming_distance_at_crossings` helper
- Update `_expand_beam` to use constant beam width + diversity
- **Test:** Verify beam doesn't collapse on 15×15 grids

**Days 3-4: Implement Dynamic MRV Variable Ordering**
- Implement `_select_next_slot_dynamic_mrv` method
- Replace static `sorted_slots` iteration with dynamic selection
- Update loop in `fill()` method to recompute MRV per assignment
- **Test:** Verify direction interleaving emerges naturally (check logs)

**Days 5-6: Upgrade to MAC Propagation**
- Implement `_mac_propagate` method
- Implement `_revise_domain` helper
- Implement `_get_current_domains` helper
- Update `_expand_beam` to call MAC after each assignment
- Add domain restoration for backtracking
- **Test:** Measure backtrack reduction vs forward checking

**Day 7: Integration Testing**
- Run all three test grids (Direction Balance, Quality Gradient, Professional)
- Validate: Completion ≥ 90%, Quality ≥ 90%, No duplicates
- Performance: 15×15 in 30-300s

**Success Criteria:**
- ✅ Beam doesn't collapse (diversity visible in solutions)
- ✅ MRV naturally interleaves directions (not strict H,V,H,V)
- ✅ MAC reduces backtracks by 50%+
- ✅ Test Grid 3 (15×15) passes with 0 duplicates

---

### Week 2: Important Enhancements (Should Do)

**Days 1-2: Add LCV Value Ordering + Stratified Shuffling**
- Implement `_order_values_lcv` method
- Implement `_stratified_shuffle` method
- Integrate both into `_expand_beam` candidate selection
- **Test:** Compare solution quality with/without LCV

**Days 3-4: Enhance Repair with Tabu Search**
- Add `tabu_list` tracking in `iterative_repair.py`
- Implement `_min_conflicts_with_tabu` method
- Add 50/50 random vs most-conflicted variable selection
- **Test:** Verify repair doesn't cycle on stuck grids

**Day 5: Add Conflict Clustering**
- Implement `_find_conflict_clusters` method
- Repair largest cluster first in repair loop
- **Test:** Compare repair efficiency on grids with >10% conflicts

**Days 6-7: Full System Testing**
- Run comprehensive test suite
- Benchmark: 11×11 in <30s, 15×15 in 30-180s, 21×21 in 180-300s
- Quality: 90%+ real words, <5% crosswordese in long slots
- Validate on 10+ real grids from Crosshare/NYT

**Success Criteria:**
- ✅ 90%+ completion on 15×15 grids
- ✅ 90%+ quality (real words, not gibberish)
- ✅ Repair success rate >80% when conflict rate <20%
- ✅ No tabu cycling observed

---

### Week 3: Optional Optimizations (Nice to Have)

- Conflict set tracking for backjumping
- Adjust quality thresholds based on empirical tuning
- Region-based filling (corners first)
- OR-Tools CP-SAT fallback for difficult sections

---

## Expected Performance Improvements

### Current (Phase 1 + Phase 2):
- **11×11:** 100% completion, ~92% quality, 0 duplicates, 0.003s ⚡
- **15×15:** 100% completion, ~70% quality, 1 duplicate, 0.01s ⚡

**Issues:**
- Beam collapses at scale (gibberish fills: AAA, IIS, RTNNN)
- Instant completion suspicious (iterations=0)
- Quality degrades when constrained

### After Phase 4 (Predicted):
- **11×11:** 100% completion, 95%+ quality, 0 duplicates, 5-30s
- **15×15:** 95%+ completion, 90%+ quality, 0 duplicates, 30-180s
- **21×21:** 90%+ completion, 85%+ quality, 0 duplicates, 180-300s

**Improvements:**
- ✅ No beam collapse (diverse beam search)
- ✅ Natural direction interleaving (dynamic MRV)
- ✅ Faster convergence (MAC + LCV)
- ✅ No cycling in repair (tabu search)
- ✅ Realistic completion times (proper search depth)

---

## Testing Strategy

### Unit Tests
- Test MAC propagation with simple 3×3 grids
- Test dynamic MRV selection order changes after assignments
- Test diverse beam search produces different solutions
- Test tabu list prevents cycling
- Test LCV prefers less-constraining candidates

### Integration Tests
- Test Grid 1 (Direction Balance): Verify MRV interleaves naturally
- Test Grid 2 (Quality Gradient): Verify MAC enforces quality thresholds
- Test Grid 3 (Professional 15×15): Verify no duplicates, 95%+ completion

### Performance Benchmarks
- Measure backtrack count: MAC vs forward checking
- Measure beam diversity: standard vs diverse beam search
- Measure repair success rate: with/without tabu
- Measure time budget: 11×11 (<30s), 15×15 (<180s), 21×21 (<300s)

---

## Risk Mitigation

### Risk 1: MAC is too slow
**Mitigation:** Optimize with caching, early termination, incremental updates
**Fallback:** Use forward checking + look-ahead depth 2

### Risk 2: Dynamic MRV changes slot order too much
**Mitigation:** Add stability heuristic (prefer recently selected slots)
**Fallback:** Hybrid static/dynamic ordering

### Risk 3: Diverse beam search degrades quality
**Mitigation:** Tune diversity_lambda (start with 0.5, decrease to 0.2 if needed)
**Fallback:** Use stratified shuffling only

### Risk 4: Repair with tabu still cycles
**Mitigation:** Add partial restart (clear region, re-solve)
**Fallback:** Reduce tabu tenure to 3-5 iterations

---

## References

1. **Ginsberg et al. (1990)** - "Search Lessons Learned from Crossword Puzzles" (AAAI)
2. **Minton et al. (1992)** - "Minimizing Conflicts: A Heuristic Repair Method for CSPs"
3. **Vijayakumar et al. (2016)** - "Diverse Beam Search" (AAAI)
4. **Sabin & Freuder (1994)** - "Contradicting Conventional Wisdom in CSPs" (MAC)
5. **Prosser (1993)** - "Hybrid Algorithms for CSP"
6. **Cohen et al. (2019)** - "The Beam Search Curse" (Non-monotonicity)
7. **Matt Gaffney** - Constructor community wisdom (Crosserville, XWord Info)

---

## Appendix: Code Patterns from Research

### A. MAC Propagation (AC-3 Algorithm)
**Source:** CSP Algorithms report, Section "Gap #1"

```python
def mac_propagate(slot, word, domains, constraint_graph):
    queue = [(neighbor, slot) for neighbor in constraint_graph[slot]]
    reduced = {}
    conflict_set = set()

    while queue:
        (xi, xj) = queue.pop(0)
        removed = revise(xi, xj, domains)

        if removed:
            reduced[xi] = reduced.get(xi, []) + removed

            if len(domains[xi]) == 0:
                conflict_set.add(xj)
                return False, reduced, conflict_set

            for xk in constraint_graph[xi]:
                if xk != xj:
                    queue.append((xk, xi))

    return True, reduced, conflict_set
```

### B. Min-Conflicts with Tabu
**Source:** Shuffling/Repair/Interleaving report, Section "Min-conflicts repair"

```python
def min_conflicts_repair(grid, max_iterations=1000, tabu_tenure=7, random_move_prob=0.1):
    tabu_list = {}

    for iteration in range(max_iterations):
        conflicting = get_conflicting_slots(grid)
        if not conflicting:
            return grid  # Solution found

        # Variable selection: 50/50 random vs most-conflicted
        if random.random() < 0.5:
            slot_id = random.choice(list(conflicting))
        else:
            slot_id = max(conflicting, key=lambda s: count_conflicts(grid, s, grid.slots[s]))

        # Value selection with tabu + aspiration
        # ... (see full implementation in report)
```

### C. Stratified Shuffle
**Source:** Shuffling report, Section "Shuffling strategy recommendations"

```python
def stratified_shuffle(candidates, tier_percentiles=[0.1, 0.3, 0.6, 1.0], seed=None):
    if seed is not None:
        random.seed(seed)

    sorted_candidates = sorted(candidates, key=lambda x: -x[1])
    n = len(sorted_candidates)

    result = []
    prev_idx = 0
    for percentile in tier_percentiles:
        end_idx = int(n * percentile)
        tier = [c[0] for c in sorted_candidates[prev_idx:end_idx]]
        random.shuffle(tier)
        result.extend(tier)
        prev_idx = end_idx

    return result
```

### D. Diverse Beam Search
**Source:** CSP report, Section "Fix #3 recommended implementation"

```python
def diverse_beam_search(initial_state, beam_width=10, num_groups=4, diversity_lambda=0.5):
    groups = [[] for _ in range(num_groups)]
    beams_per_group = beam_width // num_groups

    for g in range(num_groups):
        candidates = generate_candidates(initial_state)
        for candidate in candidates:
            diversity_penalty = sum(
                hamming_distance(candidate, prev_candidate)
                for prev_group in groups[:g]
                for prev_candidate in prev_group
            )
            candidate.score += diversity_lambda * diversity_penalty
        groups[g] = sorted(candidates, key=lambda c: -c.score)[:beams_per_group]

    return [c for group in groups for c in group]
```

---

**Date Created:** 2025-12-24
**Last Updated:** 2025-12-24
**Status:** Ready for Phase 4 Implementation
**Next Steps:** Review plan with user, begin Week 1 critical fixes
