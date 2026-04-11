# Algorithm Deep Dive: Crossword Construction Science & Tech Stack

This document provides a comprehensive technical review of all crossword-specific concepts, algorithms, and techniques used in this codebase.

**Last Updated:** March 2026

---

## Table of Contents

1. [Grid Representation & Data Model](#1-grid-representation--data-model)
2. [Crossword Construction Rules](#2-crossword-construction-rules)
3. [Auto-Numbering](#3-auto-numbering)
4. [Word Quality Scoring](#4-word-quality-scoring)
5. [Pattern Matching (3 Implementations)](#5-pattern-matching-3-implementations)
6. [Autofill Algorithms](#6-autofill-algorithms)
7. [Pause/Resume System](#7-pauseresume-system)
8. [Theme Word Support](#8-theme-word-support)
9. [Entry Conventions](#9-entry-conventions)
10. [Export](#10-export)
11. [CSP Backtracking — Implementation Details](#11-csp-backtracking--implementation-details)
12. [Beam Search — Implementation Details](#12-beam-search--implementation-details)
13. [Hybrid & Iterative Repair — Details](#13-hybrid--iterative-repair--details)
14. [Technology Stack Summary](#14-technology-stack-summary)

---

## 1. Grid Representation & Data Model

**File:** `cli/src/core/grid.py`

- **NumPy int8 array** — Grid is `np.zeros((size, size), dtype=np.int8)`
- **Cell encoding:** BLACK_SQUARE = -1, EMPTY = 0, A-Z = 1–26
- **Standard sizes:** 11×11, 13×13, 15×15, 17×17, 21×21
- **180° rotational symmetry** enforced automatically: setting `(r,c)` black also sets `(size-1-r, size-1-c)`
- **Locked cells** track theme words that survive autofill clearing
- **Word slot extraction** scans L→R, T→B to find all across/down entries ≥3 letters, returning `{direction, row, col, length, pattern}`

---

## 2. Crossword Construction Rules

**File:** `cli/src/core/validator.py`

Enforces NYT-style construction standards:

| Rule | Method | Standard |
|------|--------|----------|
| **180° rotational symmetry** | `check_symmetry()` | Every black square has a symmetric partner |
| **Full connectivity** | `_check_connectivity()` | Flood-fill DFS from first white cell; all whites reachable |
| **Minimum word length** | `_check_minimum_word_length()` | All entries must be ≥3 letters |
| **Black square density** | `_get_black_square_percentage()` | Maximum 17% of grid |

---

## 3. Auto-Numbering

**File:** `cli/src/core/numbering.py`

Standard crossword numbering convention:
- Scan left→right, top→bottom
- A cell gets a number if it **starts an Across word** (left is edge/black AND right is white) OR **starts a Down word** (above is edge/black AND below is white)
- Numbers are sequential (1, 2, 3...)
- Returns mapping: `clue_number → {position, has_across, has_down, across_length, down_length}`

---

## 4. Word Quality Scoring

**Files:** `cli/src/core/scoring.py`, `cli/src/fill/word_list.py`

### Letter Categories (crossword fill quality)
| Category | Letters | Points |
|----------|---------|--------|
| **Common** (high-frequency, easy crossings) | E, A, R, I, O, T, N, S | +10 each |
| **Regular** | D, H, C, L, U, M, P, F, G, Y, B, W, K, V | +5 each |
| **Uncommon** (constrain crossings) | J, Q, X, Z | −15 each |

### Scoring Formula
```
base = (common × 10) + (regular × 5) − (uncommon × 15)
length_bonus = word_length × 2
repetition_penalty = repeated_letters × 10
adjacent_repeat_penalty = adjacent_doubled_letters × 20
score = clamp(base + length_bonus − penalties, 1, 150)
```

**Rationale:** Words with common letters (ETAOINSR) create more crossing options. Words like QUIZ (−30 from Q,Z) score low because they're hard to cross. Adjacent doubles (TT, SS) are penalized heavily because they constrain both the across and down slots at those positions.

---

## 5. Pattern Matching (3 Implementations)

Crossword patterns use `?` as wildcard: `"C?T"` matches CAT, COT, CUT, etc.

### A. Regex (`cli/src/fill/pattern_matcher.py`)
- Converts `"C?T"` → regex `^C.T$`
- Filters by length first, then regex match
- ~200–500ms per query on 454k words
- LRU cache for repeated patterns

### B. Trie (`cli/src/fill/trie_pattern_matcher.py` + `word_trie.py`)
- **Length-indexed tries** — separate trie per word length (3–21)
- Each node stores min/max score bounds → **early subtree pruning** when min_score threshold eliminates branch
- Wildcard `?` branches to all children simultaneously
- **10–50× faster than regex** (~10–50ms per query)
- Build time: ~2–3s for 454k words
- Default for autofill algorithms

---

## 6. Autofill Algorithms

### A. CSP with Backtracking + MAC (`cli/src/fill/autofill.py`)

**Constraint Satisfaction Problem** formulation:
- **Variables:** Each word slot in the grid
- **Domains:** Valid words matching slot's current pattern + min_score
- **Constraints:** At every crossing, both words must share the same letter

**Key techniques:**

| Technique | Purpose |
|-----------|---------|
| **AC-3 (Arc Consistency 3)** | Pre-prunes domains: removes words that have no compatible partner at any crossing. Queue-based propagation until stable. |
| **MAC (Maintaining Arc Consistency)** | After each word placement, runs incremental AC-3 from that slot outward. Restores domains on backtrack. |
| **MCV (Most Constrained Variable)** | Pick next slot with smallest domain first — fail early on hardest slots. Tie-break: more filled letters > longer length. |
| **LCV (Least Constraining Value)** | Try words that leave the most options for crossing slots. Fast mode uses pre-computed letter frequency table; accurate mode counts exact remaining options. |
| **Forward Checking** | After placement, verify no crossing slot has 0 remaining candidates. |
| **Letter Frequency Table** | Pre-computed `{length → {position → {letter → count}}}` for O(1) LCV estimates |

**Performance:** <30s for 11×11. Guaranteed to find solution if one exists.

### B. Beam Search (`cli/src/fill/beam_search/`)

**Orchestrator pattern** with specialized components:

| Component | File | Role |
|-----------|------|------|
| `BeamSearchOrchestrator` | `orchestrator.py` | Main coordinator |
| `MRVSlotSelector` | `selection/slot_selector.py` | Minimum Remaining Values slot selection |
| `MACConstraintEngine` | `constraints/engine.py` | Constraint propagation after placement |
| `CompositeValueOrdering` | `selection/value_ordering.py` | Chained value ordering strategies |
| `DiversityManager` | `beam/diversity.py` | Prevents beam collapse |
| `BeamManager` | `beam/beam_manager.py` | Beam expansion and pruning |
| `StateEvaluator` | `evaluation/state_evaluator.py` | Viability + risk scoring |

**Value ordering pipeline:**
1. **ThemeWordPriority** — Theme words placed first
2. **LCV** — Least constraining value (counts remaining crossing options)
3. **ThresholdDiverse** — Quality threshold + temperature-based randomization (T=0.8)
4. **Stratified** — Groups into quality tiers, shuffles within tiers to avoid alphabetical bias

**Predictive risk assessment:** Penalizes states where crossing slots have few candidates:
- 0 candidates → dead end
- 1–2 → 0.70× score multiplier
- 3–4 → 0.85×
- 5–9 → 0.95×
- 10+ → no penalty

**Diverse Beam Search** (Vijayakumar et al. 2016): Partitions beam into diversity groups, selects top-K from each group to prevent all beams converging on similar solutions.

**Performance:** 1–5min for 15×15. Better word quality than CSP.

### C. Hybrid (`cli/src/fill/hybrid_autofill.py`)

Two-phase strategy:
1. **Phase 1 — Beam Search** (20% of timeout, max 60s): Global exploration for high-quality partial fill
2. **Phase 2 — Iterative Repair** (80% of remaining): Fixes crossing mismatches via targeted word swaps

**Iterative Repair** (`cli/src/fill/iterative_repair.py`):
- Detects crossing conflicts (letter mismatches at intersections)
- Finds slot with most conflicts
- Tries alternative words that reduce conflict count
- Repeats until converged or timeout

**Performance:** Best all-around. 1–5min for 15×15, 5–30min for 21×21.

---

## 7. Pause/Resume System

### File-Based IPC (`cli/src/fill/pause_controller.py`)
- Backend writes `pause_{task_id}.flag` file
- CLI polls for flag every ~100ms
- On detection: serialize state → exit gracefully

### State Serialization (`cli/src/fill/state_manager.py`)
- **Gzipped JSON** for complete algorithm state (~100–200KB)
- CSP state captures: grid, domains, constraints, used words, backtrack position, locked slots, letter frequency table
- Beam state captures: full beam (all parallel solutions), slot assignments, domain reductions, iteration history

### Edit Merging (`backend/core/edit_merger.py`)
- Detects changes between saved and user-edited grids
- Locks newly-filled slots, updates domains for modifications
- Runs AC-3 constraint propagation on merged state
- Validates no domains became empty (unsolvable)

---

## 8. Theme Word Support

### Theme Placement (`backend/core/theme_placer.py`)
- Places longest theme words first (centered, symmetric)
- Multi-factor scoring: symmetry (+20), intersections (+10 each), position preference (center bias), spacing (+10 if >4 apart), length consideration
- Generates 3 ranked suggestions per word
- Locked theme words survive autofill clearing

### Black Square Suggestion ("Cheater Squares") (`backend/core/black_square_suggester.py`)
- Suggests strategic black square additions for stuck autofills
- Only for slots ≥6 letters
- Scoring factors: length balance, ideal range (3–7 sweet spot), symmetry preservation (+200), word count targets, constraint reduction
- Returns top 3 suggestions maintaining 180° symmetry

---

## 9. Entry Conventions

**File:** `cli/src/core/conventions.py`

Standard crossword entry normalization:

| Convention | Example | Result |
|------------|---------|--------|
| Multi-word names | "Tina Fey" | TINAFEY |
| Articles | "The Office" | THEOFFICE |
| Hyphenated | "self-aware" | SELFAWARE |
| Apostrophes | "can't" | CANT |

---

## 10. Export

**File:** `cli/src/export/html_exporter.py`

- CSS Grid layout with auto-numbering integration
- Responsive: 40px cells (screen), 30px (print)
- Separate Across/Down clue sections with letter counts
- Supports HTML and PDF output formats

---

## 11. CSP Backtracking — Implementation Details

**File:** `cli/src/fill/autofill.py`

### Recursion Structure (`_backtrack_with_mac()`, lines 853–999)
1. **Base case** (line 904): All slots filled → return True
2. **Skip filled** (line 908–913): If slot already has a word, recurse to next
3. **Two-tier LCV scoring** (lines 916–955):
   - If >100 candidates: fast heuristic LCV first (letter frequency table), then accurate LCV on top 100
   - If ≤100: direct accurate LCV (temporarily places each word, counts remaining crossing options)
4. **Backtracking loop** (lines 963–997):
   - Place candidate word
   - **Snapshot all domains** (line 972): `saved_domains = {k: v.copy() for k, v in self.domains.items()}`
   - Run `_ac3_incremental()` from assigned slot
   - Recurse; on failure, **restore all domains** (line 993)

### Domain Snapshot/Restore
- Full copy of ALL domain dictionaries on each placement — O(n × m) memory
- No incremental restore (restores everything, even unaffected domains)
- **Weakness:** Memory-intensive for large grids with 10k+ words per domain

### AC-3 Arc Consistency (lines 661–760)
- Queue-based: maintains arcs `(slot_i, slot_j)` to check
- `_revise()` removes words from domain_i that have no compatible partner in domain_j at their crossing position
- **Wipeout:** If any domain becomes empty → return False → triggers backtrack
- **No conflict learning:** Doesn't record WHY a domain emptied (no nogood recording)

### Letter Frequency Table (lines 465–497)
- Structure: `{word_length: {position: {letter: frequency_count}}}`
- Built once from entire word list at initialization
- Used by `_lcv_score_fast()` to estimate constraining impact in O(1)
- **Gap:** Only individual letter frequencies — ignores bigrams (QU, TH, CH always co-occur)

### Stratified Sampling (lines 408–463)
- Triggered when domain >10,000 words
- Divides into 10 score deciles, samples proportionally
- Ensures letter diversity at each position (all 26 letters represented)

---

## 12. Beam Search — Implementation Details

**File:** `cli/src/fill/beam_search/orchestrator.py`

### Main Loop (lines 208–462)
```
while filled_slots < total_slots:
  1. Check pause/timeout
  2. Select next slot via MRV (smallest domain)
  3. Expand beam: try top-K candidates per state
  4. If expansion fails → backtracking (4 strategies)
  5. Apply diversity pruning
  6. Check for complete solution
```

### Stratified Candidate Selection (lines 140–204)
- Each beam gets overlapping slice of shuffled candidates
- Offset per beam = 2 (hardcoded)
- Beam 0: candidates[0:10], Beam 1: candidates[2:12], etc.

### Dead End Recovery (lines 349–435)
Four escalating strategies:
1. Double candidates (2× normal)
2. Quintuple candidates (5× normal)
3. Remove score filter entirely
4. Conflict-directed backjumping

**Partial fill fallback:**
- ≥80% filled → accept as success
- 50–80% → gentle backtrack (depth=1)
- <50% → aggressive backtrack (undo recent assignments)

### Stale Beam Detection (lines 187–206)
- Hashes first beam state's slot assignments as signature
- Tracks `(signature, slot_id) → attempt_count`, max 3 attempts
- **Bug:** Only uses first state — different 2nd–5th states treated as duplicate

### Diversity Management (`beam_search/beam/diversity.py`)
- Partitions expanded beam into groups (default 4)
- Each group selects top states using diversity-augmented scores
- Diversity metric: Hamming distance at crossing positions between candidate states
- Based on Vijayakumar et al. 2016 (Diverse Beam Search)

### State Evaluation (`beam_search/evaluation/state_evaluator.py`)
- Risk penalties based on crossing slot candidate counts (0.70×–1.0×)
- Word quality heuristics: vowel ratio (20–65%), max repeated letters ≤3, consonant clusters ≤5, Q-without-U detection, impossible bigrams
- **Limitation:** Only 1–2 level lookahead; doesn't detect cascading failures deeper in the tree

---

## 13. Hybrid & Iterative Repair — Details

### Hybrid (`cli/src/fill/hybrid_autofill.py`, lines 75–191)
- Phase 1: Beam Search — `min(60s, 20% of timeout)`
- Phase 2: Iterative Repair — remaining time
- Handoff: passes beam's grid to repair (no algorithm state preserved)
- Returns better of beam vs. repair result

### Iterative Repair (`cli/src/fill/iterative_repair.py`)
- **Region-based fill** (lines 256–336): Finds dead-end slots → identifies blocking words → strips region → CSP backtrack fills the conflict zone → greedy fills remainder
- **Multi-pass greedy** (lines 338–393): Pass 0 strict gibberish check, passes 1–2 relaxed, randomized for restart diversity
- **Tabu search** (lines 395–465): Tracks recent swaps, tenure = √(num_slots), swaps words to reduce conflicts, restores best-seen solution

---

## 14. Technology Stack Summary

| Layer | Technology | Why |
|-------|-----------|-----|
| Grid storage | NumPy int8 arrays | Fast bulk operations, memory-efficient cell encoding |
| Pattern matching | Trie (default) / Regex | 10–50× speedup over naive regex for 454k word dictionary |
| Autofill core | CSP + AC-3 + MAC | Proven constraint satisfaction with arc consistency pruning |
| Autofill quality | Beam Search + Diverse Beam | Global optimization, prevents local optima, better word quality |
| Heuristics | MCV/MRV + LCV + Forward Checking | Standard AI search heuristics adapted for crossword domain |
| Value ordering | Letter frequency tables | O(1) LCV estimation without pattern matching |
| Risk assessment | Predictive state evaluation | Steers search away from high-risk partial fills |
| Pause/resume | Gzipped JSON state + file-based IPC | Complete algorithm state preservation across sessions |
| Web integration | Subprocess (CLI-as-truth) | Single implementation, no logic duplication |
