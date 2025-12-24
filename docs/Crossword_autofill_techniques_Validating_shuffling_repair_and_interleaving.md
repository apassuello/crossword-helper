# Crossword autofill techniques: Validating shuffling, repair, and interleaving

**Your three implemented techniques—word candidate shuffling, iterative repair, and direction interleaving—are all strongly validated by academic literature and production solver practice.** The combination represents a coherent architecture that aligns with state-of-the-art approaches. Shuffling addresses beam convergence bias documented in Diverse Beam Search research; iterative repair follows the min-conflicts tradition proven effective since 1992; and direction interleaving implements the fail-first principle that Ginsberg established as essential for crossword CSPs. This report provides theoretical grounding, refinement opportunities, and integration patterns to push your system toward 90%+ completion rates.

---

## Word candidate shuffling prevents beam collapse

Standard beam search with alphabetically ordered candidates suffers from a well-documented convergence problem. The Diverse Beam Search paper (Vijayakumar et al., 2016) describes the core issue: "BS explores the search space in a greedy left-right fashion retaining only the top-B candidates—resulting in sequences that differ only slightly from each other." When dictionary words are alphabetically sorted, early letters (A, B, C) systematically win tie-breaking, causing all beam candidates to converge toward similar solutions sharing common prefixes.

### Academic evidence confirms input ordering bias

Multiple sources validate that shuffling addresses a real problem. The Built In beam search analysis notes: "The branches will often converge to k states that are all very similar to each other. If this happens, we pay the expense of maintaining k branches but effectively only gain the benefits of one." Wikipedia's beam search entry recommends choosing next states randomly, "favoring higher-scoring states, of course—to encourage exploration."

A crucial finding from Diverse Beam Search research: **diversity doesn't hurt quality—it helps it**. The DBS paper reports that their diversity-promoting method "finds better top-1 solutions by controlling for the exploration and exploitation of the search space." This directly counters concerns that shuffling might miss optimal candidates.

### Production solvers explicitly randomize

Exet (viresh-ratnakar/exet) documents: "Autofill randomizes its choices to an extent. You can run it repeatedly to get different results every time, until you are satisfied with the fills." The solver explicitly encourages re-running autofill because "of the slight randomness in the choices that it makes."

Qxw offers three explicit modes: **deterministic**, **slightly randomised**, and **highly randomised**. The documentation states: "The filler implements randomisation by not always choosing the most constrained variable or highest-scoring word." Crosshare similarly randomizes—pressing Enter produces a different autofill result each time.

### Shuffling strategy recommendations

**Stratified shuffling** preserves quality while breaking alphabetical bias. Rather than fully randomizing, partition candidates into quality tiers (top 10%, next 20%, etc.) and shuffle only within tiers:

```python
import random
from typing import List, Tuple

def stratified_shuffle(
    candidates: List[Tuple[str, float]],  # (word, quality_score)
    tier_percentiles: List[float] = [0.1, 0.3, 0.6, 1.0],
    seed: int = None
) -> List[str]:
    """
    Shuffle candidates within quality tiers to break alphabetical bias
    while preserving quality gradient.
    """
    if seed is not None:
        random.seed(seed)
    
    # Sort by quality descending
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

**Per-expansion shuffling** provides more diversity than one-time startup shuffling. Re-shuffle when:
- Starting a new beam expansion step
- Backtracking to retry a slot
- Entering repair mode

For reproducible debugging, use seeded shuffling with a deterministic PRNG. For production diversity, use timestamps or increment seeds per expansion.

### Diverse Beam Search complements shuffling

DBS and shuffling address different convergence sources and are **complementary, not redundant**. Shuffling addresses the **presentation** phase (tie-breaking and initial ordering), while DBS addresses the **selection** phase (which candidates make the beam) by penalizing similar hypotheses. Consider implementing DBS as a future enhancement:

```python
def diverse_beam_select(
    candidates: List[Tuple[str, float]],  # (word, log_prob)
    existing_selections: List[str],
    diversity_weight: float = 0.5
) -> Tuple[str, float]:
    """
    Select candidate with diversity penalty against existing selections.
    """
    best_word, best_score = None, float('-inf')
    
    for word, log_prob in candidates:
        # Hamming diversity: count differing positions
        dissimilarity = sum(
            sum(1 for a, b in zip(word, sel) if a != b)
            for sel in existing_selections
        ) / max(1, len(existing_selections))
        
        augmented_score = log_prob + diversity_weight * dissimilarity
        if augmented_score > best_score:
            best_score = augmented_score
            best_word = word
    
    return best_word, best_score
```

---

## Min-conflicts repair handles the last mile efficiently

Iterative repair using min-conflicts is theoretically grounded in foundational CSP research. Minton et al. (1992) demonstrated that repair-based methods excel when starting from near-solutions—exactly the situation after beam search produces an almost-complete grid with a few conflicts.

### The min-conflicts algorithm explained

The algorithm starts with a complete but potentially inconsistent assignment and iteratively repairs conflicts:

1. **Select a conflicting variable** (random or most-conflicted)
2. **Choose a value that minimizes conflicts** with other variables
3. **Repeat until solution found or max iterations exceeded**

The key insight from Minton's analysis: a complete assignment provides more guidance than a partial one. When repairing a variable, the algorithm can see conflicts with ALL other variables, enabling informed decisions.

```python
from dataclasses import dataclass
from typing import Dict, Set, List, Optional
import random

@dataclass
class CrosswordGrid:
    slots: Dict[str, str]  # slot_id -> current_word
    crossings: Dict[str, List[tuple]]  # slot_id -> [(crossing_slot, my_pos, their_pos), ...]
    candidates: Dict[str, List[str]]  # slot_id -> valid_words

def count_conflicts(grid: CrosswordGrid, slot_id: str, word: str) -> int:
    """Count letter mismatches at crossing positions."""
    conflicts = 0
    for crossing_slot, my_pos, their_pos in grid.crossings[slot_id]:
        other_word = grid.slots.get(crossing_slot)
        if other_word and word[my_pos] != other_word[their_pos]:
            conflicts += 1
    return conflicts

def get_conflicting_slots(grid: CrosswordGrid) -> Set[str]:
    """Find all slots with at least one crossing conflict."""
    conflicting = set()
    for slot_id, word in grid.slots.items():
        if count_conflicts(grid, slot_id, word) > 0:
            conflicting.add(slot_id)
    return conflicting

def min_conflicts_repair(
    grid: CrosswordGrid,
    max_iterations: int = 1000,
    tabu_tenure: int = 7,
    random_move_prob: float = 0.1
) -> Optional[CrosswordGrid]:
    """
    Repair a near-complete crossword grid using min-conflicts with tabu.
    
    Args:
        grid: Grid with all slots filled (possibly with conflicts)
        max_iterations: Maximum repair attempts
        tabu_tenure: How long to forbid reversed moves
        random_move_prob: Probability of random move for plateau escape
    
    Returns:
        Repaired grid or None if repair failed
    """
    tabu_list: Dict[tuple, int] = {}  # (slot_id, old_word) -> expiry_iteration
    best_conflict_count = float('inf')
    no_progress_count = 0
    
    for iteration in range(max_iterations):
        conflicting = get_conflicting_slots(grid)
        
        if not conflicting:
            return grid  # Solution found
        
        conflict_count = len(conflicting)
        if conflict_count < best_conflict_count:
            best_conflict_count = conflict_count
            no_progress_count = 0
        else:
            no_progress_count += 1
        
        # Early termination if stuck
        if no_progress_count > 50:
            return None  # Repair failed, need different approach
        
        # Variable selection: mix of random and most-conflicted
        if random.random() < 0.5:
            slot_id = random.choice(list(conflicting))
        else:
            # Select most-conflicted slot
            slot_id = max(conflicting, 
                         key=lambda s: count_conflicts(grid, s, grid.slots[s]))
        
        old_word = grid.slots[slot_id]
        
        # Value selection: min-conflicts or random for plateau escape
        if random.random() < random_move_prob:
            # Random move for exploration
            valid_candidates = [w for w in grid.candidates[slot_id]
                              if (slot_id, w) not in tabu_list or 
                                 tabu_list[(slot_id, w)] <= iteration]
            if valid_candidates:
                new_word = random.choice(valid_candidates)
            else:
                continue
        else:
            # Min-conflicts selection
            best_word, min_conflicts = old_word, count_conflicts(grid, slot_id, old_word)
            for candidate in grid.candidates[slot_id]:
                # Check tabu status (with aspiration)
                is_tabu = (slot_id, candidate) in tabu_list and \
                          tabu_list[(slot_id, candidate)] > iteration
                conflicts = count_conflicts(grid, slot_id, candidate)
                
                # Accept if better than current OR if best-ever (aspiration)
                if conflicts < min_conflicts and (not is_tabu or conflicts == 0):
                    min_conflicts = conflicts
                    best_word = candidate
            
            new_word = best_word
        
        if new_word != old_word:
            # Make the repair
            grid.slots[slot_id] = new_word
            # Add old assignment to tabu list
            tabu_list[(slot_id, old_word)] = iteration + tabu_tenure
    
    return None  # Max iterations reached
```

### When repair succeeds versus fails

Minton's theoretical analysis identifies two regimes:

**Repair works well (Gaussian limit)** when constraints are dense:
- Local information is highly informative
- Probability of moving toward solution: approximately d/n (where d = distance to solution)
- Expected steps: O(n log d₀)
- Examples: N-Queens, dense graph coloring

**Repair often fails (Poisson limit)** when constraints are sparse:
- Local information is misleading
- "Islands" of inconsistency can form where boundaries oscillate without progress
- Probability of finding solution declines exponentially with iterations

For crosswords, repair works best when **>80-90% of words are already correct**. Below this threshold, consider partial restart (clearing a region) rather than continued repair. The empirical rule: if initial conflict rate exceeds 20-30%, repair is unlikely to succeed efficiently.

### Plateau escape mechanisms

**Tabu search** prevents cycling by forbidding recently reversed moves:
- **Tabu tenure**: 5-15 iterations for typical crossword size (√n to 2√n as a general rule)
- **Aspiration criteria**: Override tabu status if move produces best-ever solution
- **Random walk**: With probability 0.1-0.2, make random moves instead of best moves

**Termination conditions**:
- **Solution found**: Zero conflicts
- **Max iterations**: Set to 300 × num_words
- **No progress**: 50 iterations without improvement
- **Oscillation detected**: Same conflict pattern repeating

### Crossword-specific repair considerations

**Cascade effects** are the primary challenge. Changing one word affects 3-15 crossing words. Mitigation strategies:

1. **Minimize letter changes**: Choose replacement words sharing maximum letters with original
2. **Cluster-based repair**: Identify connected conflict clusters and repair them together
3. **Region-based fallback**: If conflicts span more than 20% of grid, clear and re-solve a rectangular region

```python
def find_conflict_clusters(grid: CrosswordGrid) -> List[Set[str]]:
    """Group conflicting slots into connected clusters."""
    conflicting = get_conflicting_slots(grid)
    clusters = []
    visited = set()
    
    for slot in conflicting:
        if slot in visited:
            continue
        
        # BFS to find connected conflict cluster
        cluster = set()
        queue = [slot]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            if current in conflicting:
                cluster.add(current)
                # Add crossing slots that are also conflicting
                for crossing_slot, _, _ in grid.crossings[current]:
                    if crossing_slot in conflicting and crossing_slot not in visited:
                        queue.append(crossing_slot)
        
        if cluster:
            clusters.append(cluster)
    
    return clusters
```

---

## Direction interleaving implements fail-first principle

Filling all horizontal words before vertical (or vice versa) creates impossible constraints. Ginsberg et al. (1990) established that dynamic variable ordering is essential for crossword CSPs. The fail-first principle (Haralick & Elliott, 1980) states: "To succeed, try first where you are most likely to fail."

### Why sequential filling fails catastrophically

When horizontal words are filled independently, the resulting letter patterns at crossing points may have **zero valid vertical completions**. If 5 horizontal words each constrain one letter of a 5-letter vertical word, the probability of a valid vertical word plummets exponentially.

Sequential filling causes:
- **Late constraint discovery**: Conflicts only detected when attempting vertical slots
- **No early pruning**: Arc consistency cannot propagate between directions
- **Accumulated impossible states**: Many cells have letters making valid crossings impossible

### MRV naturally interleaves directions

**Minimum Remaining Values (MRV)** heuristic automatically interleaves because constraint propagation alternates which direction becomes most constrained:

1. After filling a horizontal word, arc consistency updates vertical word domains
2. If vertical words become more constrained, MRV selects them next
3. The algorithm discovers when to switch directions based on actual constraint state

**Key insight: explicit direction alternation is unnecessary if using proper MRV.** Production solvers (Crossfire, Qxw, Dr.Fill) all use most-constrained-first rather than strict H/V alternation.

```python
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass 
class Slot:
    id: str
    direction: str  # 'H' or 'V'
    length: int
    cells: List[Tuple[int, int]]  # (row, col) positions
    domain: List[str]  # valid candidate words
    crossings: List[Tuple[str, int, int]]  # (crossing_slot_id, my_pos, their_pos)

def select_next_slot_mrv(
    unfilled_slots: Dict[str, Slot],
    grid_state: Dict[Tuple[int, int], str]  # cell -> current letter (or None)
) -> Optional[str]:
    """
    Select slot with minimum remaining values (fewest valid candidates).
    Ties broken by degree (most constraints on unfilled slots).
    """
    if not unfilled_slots:
        return None
    
    candidates = []
    for slot_id, slot in unfilled_slots.items():
        # Count remaining valid words given current grid state
        domain_size = len(get_valid_candidates(slot, grid_state))
        
        # Count unfilled crossing slots (degree)
        degree = sum(1 for crossing_id, _, _ in slot.crossings 
                    if crossing_id in unfilled_slots)
        
        candidates.append((slot_id, domain_size, degree))
    
    # Sort by domain_size ascending, then degree descending
    candidates.sort(key=lambda x: (x[1], -x[2]))
    
    # Return slot with smallest domain (ties broken by highest degree)
    return candidates[0][0] if candidates else None

def get_valid_candidates(slot: Slot, grid_state: Dict) -> List[str]:
    """Filter slot's domain to words matching current grid letters."""
    valid = []
    for word in slot.domain:
        matches = True
        for i, (row, col) in enumerate(slot.cells):
            current_letter = grid_state.get((row, col))
            if current_letter and current_letter != word[i]:
                matches = False
                break
        if matches:
            valid.append(word)
    return valid
```

### Interleaving strategy comparison

| Strategy | Advantages | Disadvantages | Recommendation |
|----------|------------|---------------|----------------|
| **Strict alternation (H,V,H,V)** | Simple, guarantees some propagation | Arbitrary, ignores actual constraints | ⚠️ Acceptable fallback |
| **MRV-based** | Adapts to grid, finds bottlenecks | Requires domain tracking | ✅ Recommended |
| **Region-based** | Exploits local structure | May fail at boundaries | ⚠️ Niche use |
| **Most-constrained-first** | Equivalent to MRV | Same as MRV | ✅ Recommended |

Crossfire's "Best Location" feature explicitly identifies bottlenecks—"tight, constrained areas with fewest options." This is MRV in practice.

### Beam search integration

**All beams should use the same dynamic MRV ordering**—diversity comes from value (word) selection, not variable ordering. Different orderings per beam add complexity without proportional benefit. After each beam expansion:

1. Propagate constraints across all beams
2. Prune beams with empty domains (impossible states)
3. Re-evaluate MRV for next slot selection
4. Apply stratified shuffling to candidate lists

---

## Integration architecture: combining all three techniques

The three techniques address different phases of the solve process and combine naturally:

```
┌─────────────────────────────────────────────────────────────────┐
│                     BEAM SEARCH PHASE                           │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │ MRV Slot    │───▶│ Stratified   │───▶│ Expand Beam     │    │
│  │ Selection   │    │ Shuffle      │    │ (k candidates)  │    │
│  │ (Interleave)│    │ Candidates   │    │                 │    │
│  └─────────────┘    └──────────────┘    └─────────────────┘    │
│         │                                        │              │
│         │                                        ▼              │
│         │                              ┌─────────────────┐      │
│         │                              │ Constraint Prop │      │
│         │                              │ + Prune Beams   │      │
│         │                              └─────────────────┘      │
│         │                                        │              │
│         └────────────────────────────────────────┘              │
│                            │                                    │
│                    Grid complete?                               │
│                    ───────┬───────                              │
│                   No      │     Yes                             │
│                   ▲       │      │                              │
│                   │       │      ▼                              │
│                   │       │  ┌─────────────────┐                │
│                   │       │  │ Check conflicts │                │
│                   │       │  └────────┬────────┘                │
│                   │       │           │                         │
│                   │       │    No conflicts? ──▶ RETURN SUCCESS │
│                   │       │           │                         │
└───────────────────┼───────┼───────────┼─────────────────────────┘
                    │       │           │
                    │       │           ▼
┌───────────────────┼───────┼───────────────────────────────────┐
│                   │       │    REPAIR PHASE                   │
│                   │       │  ┌─────────────────┐              │
│                   │       │  │ Conflict rate   │              │
│                   │       │  │ < 20%?          │              │
│                   │       │  └────────┬────────┘              │
│                   │       │      Yes  │   No                  │
│                   │       │           │    │                  │
│                   │       │           ▼    ▼                  │
│                   │       │  ┌────────────┐  ┌──────────────┐ │
│                   │       │  │Min-Conflicts│  │Partial       │ │
│                   │       │  │+ Tabu       │  │Restart       │ │
│                   │       │  └─────┬──────┘  └──────┬───────┘ │
│                   │       │        │                │         │
│                   │       │        ▼                │         │
│                   │       │  ┌──────────────┐       │         │
│                   │       │  │ Repaired?    │       │         │
│                   │       │  └──────┬───────┘       │         │
│                   │       │    Yes  │   No          │         │
│                   │       │         │    │          │         │
│                   │       │         ▼    └──────────┘         │
│                   │       │    RETURN SUCCESS                 │
│                   └───────┼─────────────────┼─────────────────┤
│                           │                 │                 │
│                           │       RETRY     │                 │
│                           └─────────────────┘                 │
└───────────────────────────────────────────────────────────────┘
```

### Complete integration skeleton

```python
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
import random

@dataclass
class BeamState:
    grid: Dict[str, str]  # slot_id -> word
    filled_slots: Set[str]
    score: float
    
@dataclass
class SolverConfig:
    beam_width: int = 10
    max_iterations: int = 5000
    repair_max_iterations: int = 500
    repair_threshold: float = 0.2  # Max conflict rate for repair
    shuffle_seed: Optional[int] = None
    tabu_tenure: int = 7

def crossword_solve(
    slots: Dict[str, Slot],
    config: SolverConfig
) -> Optional[Dict[str, str]]:
    """
    Main solver combining beam search, shuffling, and repair.
    """
    # Initialize beam with empty grid
    initial_state = BeamState(grid={}, filled_slots=set(), score=0.0)
    beam: List[BeamState] = [initial_state]
    
    iteration = 0
    while iteration < config.max_iterations:
        # Check if any beam has complete solution
        for state in beam:
            if len(state.filled_slots) == len(slots):
                # Grid complete - try repair if needed
                conflicts = count_total_conflicts(state.grid, slots)
                if conflicts == 0:
                    return state.grid
                
                conflict_rate = conflicts / len(slots)
                if conflict_rate < config.repair_threshold:
                    repaired = min_conflicts_repair(
                        state.grid, slots,
                        max_iterations=config.repair_max_iterations,
                        tabu_tenure=config.tabu_tenure
                    )
                    if repaired:
                        return repaired
        
        # === INTERLEAVING: Select next slot using MRV ===
        unfilled = {s: slots[s] for s in slots if s not in beam[0].filled_slots}
        if not unfilled:
            break
            
        next_slot_id = select_next_slot_mrv(unfilled, beam[0].grid)
        next_slot = slots[next_slot_id]
        
        # Expand beam
        new_beam: List[BeamState] = []
        
        for state in beam:
            # Get valid candidates for this state
            candidates = get_valid_candidates(next_slot, state.grid)
            
            # === SHUFFLING: Stratified shuffle to prevent convergence ===
            scored_candidates = [(w, score_word(w, next_slot)) for w in candidates]
            shuffled = stratified_shuffle(
                scored_candidates,
                seed=config.shuffle_seed
            )
            
            # Expand with top candidates
            for word in shuffled[:config.beam_width]:
                new_grid = state.grid.copy()
                new_grid[next_slot_id] = word
                new_score = compute_beam_score(new_grid, slots)
                
                new_state = BeamState(
                    grid=new_grid,
                    filled_slots=state.filled_slots | {next_slot_id},
                    score=new_score
                )
                new_beam.append(new_state)
        
        # Prune to beam width, keeping highest scoring
        new_beam.sort(key=lambda s: -s.score)
        beam = new_beam[:config.beam_width]
        
        # Constraint propagation: remove beams with empty domains
        beam = [s for s in beam if not has_empty_domain(s, slots)]
        
        if not beam:
            # All beams failed - restart with different shuffle
            config.shuffle_seed = random.randint(0, 2**32)
            beam = [initial_state]
        
        iteration += 1
    
    # Final attempt: try repair on best incomplete grid
    if beam:
        best = max(beam, key=lambda s: len(s.filled_slots))
        if len(best.filled_slots) > 0.8 * len(slots):
            return min_conflicts_repair(
                best.grid, slots,
                max_iterations=config.repair_max_iterations * 2
            )
    
    return None  # Solve failed
```

### Technique interaction effects

**Shuffling + Interleaving**: These are largely independent. Shuffling affects which word is selected for a slot; interleaving affects which slot is selected next. Both contribute to diversity but through different mechanisms.

**Repair + Interleaving**: Interleaved fills typically produce more repairable grids than sequential fills. When conflicts occur after interleaved filling, they tend to be localized rather than forming large impossible regions. MRV-based filling distributes constraints evenly, leaving repair a "polishing" task rather than major reconstruction.

**Shuffling + Repair**: Shuffled candidate selection during repair helps escape plateaus. When min-conflicts can't find improvement with current candidates, shuffling the candidate order can reveal overlooked options. The random-move probability (0.1-0.2) in repair serves a similar function.

---

## Validation summary

| Technique | Status | Confidence | Notes |
|-----------|--------|------------|-------|
| **Word candidate shuffling** | ✅ VALIDATED | High | DBS research proves diversity improves quality. Exet, Qxw, Crosshare all implement randomization. |
| **Iterative correction** | ✅ VALIDATED | High | Min-conflicts (1992) is foundational. Dr.Fill explicitly chose postprocessing over branch-and-bound. BCS uses local search repair. |
| **Direction interleaving** | ✅ VALIDATED | High | Ginsberg 1990 established dynamic ordering as essential. All production solvers use MRV/most-constrained-first. |

### Recommended refinements

**Shuffling improvements**:
- Implement stratified shuffling (preserve quality tiers)
- Shuffle per-expansion, not just at startup
- Consider DBS penalty term for additional diversity

**Repair improvements**:
- Add tabu list with tenure 5-15 to prevent cycling
- Use 50/50 mix of random and most-conflicted variable selection
- Set threshold: if >20% conflicts, trigger partial restart instead
- Implement cluster-based repair for connected conflicts

**Interleaving improvements**:
- Replace strict H/V alternation with full MRV
- Track domain sizes after each fill for accurate MRV
- Identify bottleneck slots (domain < 3-5) and prioritize them

### Remaining uncertainties

1. **Optimal repair threshold**: The 20% conflict rate threshold is derived from Minton's analysis but may vary by grid density. Empirical tuning recommended.

2. **Stratified tier boundaries**: The optimal percentile boundaries for stratified shuffling (10/30/60/100) are heuristic. Grid-specific tuning may help.

3. **Beam width vs repair tradeoff**: Wider beams reduce need for repair but slow search. The optimal balance depends on dictionary quality and grid structure.

### Path to 90%+ completion

Your current 70-80% completion rate suggests the architecture is sound but tuning is needed:

1. **Improve repair triggering**: Switch to repair earlier when beam progress stalls, not just when grid is complete
2. **Partial restart capability**: When repair fails, clear 20-30% of grid (the conflicting region) and re-solve rather than full restart
3. **Quality-aware shuffling**: Ensure top 10% of candidates by quality score remain accessible even after shuffling
4. **Constraint propagation**: Aggressive forward checking after each assignment to prune impossible paths early

The combination of validated techniques with these refinements should push completion rates toward 90%+ for typical NYT-style grids within your 30-300 second budget.