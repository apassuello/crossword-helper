# C3 Propagator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `cli/src/domain/propagator.py` — AC-3 to a fixed point over `SlotModel` crossings and `LetterBitsetIndex` bitsets, maintaining word masks per slot and letter sets per cell.

**Architecture:** C3 is the first consumer of both C1 (`LetterBitsetIndex`) and C2 (`SlotModel`), which are on `main` and unwired. It adds one module and one test file; no existing module is modified except the C2 test file in Task 0. The propagator holds two views (word masks per slot, letter bitmask per cell) linked by the crossings C2 materialises, revises them to a fixed point, and reports what it removed. Nothing is wired to the CLI, adapter, route or UI (spec decision 3).

**Tech Stack:** Python 3.9+ with `from __future__ import annotations`, NumPy `>=1.24.0` (`uint64` masks), pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-domain-capabilities-design.md` — §7 is the contract; §2 (project-wide constraints), §3 (vocabulary), §4 (C1 surface) and §6 (C2 surface) bind it.

> **Amendment 0.1.7 — all three decisions ratified 2026-09-09. Every task is unblocked.**
> Two were ratified against the proposal. **14** on its answer: `crossing_counts` validates the word
> length, and the proposal's premise was wrong — decision 12 declined to guard *lookups*, while §4
> and §6 already pin three shape guards of the same kind. **15** on its reasoning: the value is
> unchanged (`0`), but it holds because an unslotted white cell is a **grid defect** where no letter
> may legally sit — not because of a precedence rule chosen for tidiness.

## Global Constraints

Every task's requirements implicitly include this section.

- **Module placement:** `cli/src/domain/propagator.py`, tests in `cli/tests/unit/test_propagator.py`. Additive only — no existing module is modified (spec §11).
- **Imports** use the `src.`-rooted form the sibling modules use (`from src.domain.slot_model import ...`), and each module opens with `from __future__ import annotations`.
- **Cell index is `row * size + col`.** No `(row, col)` tuple keys in any stored structure (spec §2).
- **Alphabet masks are Python `int`, at most 64 bits.** Word masks are NumPy `uint64` arrays (spec §2).
- **Canonical pattern** is uppercase with `?` for a blank (spec §3). The C1 primitives (`mask`, `letters_at`, `restrict`, `words`, `count`) do **not** normalise; `pattern(model, slot_id, fixed)` already emits the canonical form.
- **Open slot** = its pattern contains at least one `?`. **Fixed slot** = it contains none (spec §3).
- **`MinScore = int | Callable[[int], int]`.** An `int` is a constant policy; a callable is applied as `min_score(length)`. Every entry point takes it and defaults to `0`. **Write the alias in the `typing.Union` form** — `MinScore = Union[int, Callable[[int], int]]`. The spec writes it with `|`, but a module-level alias is a *runtime* expression that `from __future__ import annotations` does not defer, and `int | Callable[...]` raises `TypeError` on Python 3.9, which README's badge and CLAUDE.md both still claim as the floor. Annotations may keep the `|` form; the alias may not.
- **The oracle matcher is `TriePatternMatcher(word_list)`, never `PatternMatcher`.** `PatternMatcher.find` defaults `max_results=100` (`cli/src/fill/pattern_matcher.py:41`) while `TriePatternMatcher.find` defaults `None` (`cli/src/fill/trie_pattern_matcher.py:67`), and both `analyze_constraints` and `analyze_placement_impact` call `pattern_matcher.find(pattern, min_score=0)` with no `max_results`. A `PatternMatcher` silently caps every count at 100.
- **Every oracle is valid at `min_length=3` only.** `Grid.get_empty_slots`, `analyze_constraints` and `analyze_placement_impact` all call `grid.get_word_slots()` with no argument. Build every `SlotModel` in a test with `min_length=3`.
- **Fixtures pass Python `int` only** into `SlotModel.from_blacks` / `from_grid`. `from_blacks` never coerces, so a NumPy-sourced `blacks` or `size` leaks `numpy.int64` and breaks `to_dict`'s no-NumPy contract.
- **No count, timing or pass rate appears in any docstring, comment or doc** (project anti-pattern list). Name the command that proves it instead.
- **Every task is one conventional commit**, additive, with `pytest cli/tests/unit/test_propagator.py -v` green before it.

## The shared fixture

Every task below uses one hand-built word list and one grid geometry. Both are pinned here; the values in every normative table were transcribed from running the named oracles against them, not hand-derived.

**`FIXTURE_WORDS`** — passed to `WordList` as `(text, score)` tuples so the scores are explicit and canonical order is fully determined:

```
("ARISE", 90) ("EVERY", 80) ("TRIES", 70) ("EARN", 60) ("NEAR", 50)
("EAR", 40)   ("PEA", 40)   ("SEA", 35)   ("SPA", 30)  ("PAR", 30)
("PET", 25)   ("SET", 25)   ("SAP", 20)   ("SPY", 20)
```

Derived and pinned: **alphabet is `AEINPRSTVY`** (10 letters — `X` and `Z` are outside it, and used deliberately below). Canonical order (`(-score, text)`, so a word's id is its position here):

| length | canonical order |
|---|---|
| 3 | `EAR, PEA, SEA, PAR, SPA, PET, SET, SAP, SPY` |
| 4 | `EARN, NEAR` |
| 5 | `ARISE, EVERY, TRIES` |

**Geometry `FIX-A`** — the same 5×5 C2's tests pin. `Grid(5, validate_size=False)` with `set_black_square(r, c, enforce_symmetry=False)` at `(0,3), (1,3), (3,0), (4,1)`; equivalently `SlotModel.from_blacks(5, [3, 8, 15, 21], min_length=3)`. It has 10 slots, 18 crossings and one unslotted cell, `20`.

| slot | direction | length | cells |
|---|---|---|---|
| 0 | across | 3 | 0, 1, 2 |
| 1 | across | 3 | 5, 6, 7 |
| 2 | across | 5 | 10, 11, 12, 13, 14 |
| 3 | across | 4 | 16, 17, 18, 19 |
| 4 | across | 3 | 22, 23, 24 |
| 5 | down | 3 | 0, 5, 10 |
| 6 | down | 4 | 1, 6, 11, 16 |
| 7 | down | 5 | 2, 7, 12, 17, 22 |
| 8 | down | 3 | 13, 18, 23 |
| 9 | down | 5 | 4, 9, 14, 19, 24 |

The other geometries are built with `SlotModel.from_blacks` and a hand-written `fixed` tuple; each task names the ones it needs.

---

### Task 0: Guard `pattern()`'s Grid-independence

Twice-deferred from the C1 and C2 passes; C3's whole design rests on `pattern` being a pure function of `(model, slot_id, fixed)` so one model stays constant while `fixed` changes underneath it. `slot_model.py`'s module docstring already asserts this ("`pattern` never touches a Grid") and nothing tests it.

**Files:**
- Modify: `cli/tests/unit/test_slot_model.py`
- Test: same file

**Interfaces:**
- Consumes: `cli/src/domain/slot_model.pattern` (already on `main`).
- Produces: nothing importable. This task exists to make the invariant fail loudly if a later change adds a `Grid` parameter.

**Behavioral criteria:**
- The guard pins the **signature**, not behaviour under a stub: `tuple(inspect.signature(pattern).parameters)` is exactly `("model", "slot_id", "fixed")`.
- Pinning the signature rather than passing a stubbed `Grid` is the point: an added *optional* `grid=None` parameter slips past a stub guard, because a stub is simply never consulted.

**Normative cases:**

| expression | value |
|---|---|
| `tuple(inspect.signature(pattern).parameters)` | `("model", "slot_id", "fixed")` |

- [ ] **Step 1: Write the test**

Add it to the existing `test_slot_model.py`. Design the test yourself from the criterion above.

- [ ] **Step 2: Run it**

Run: `pytest cli/tests/unit/test_slot_model.py -v`
Expected: PASS. `pattern` already has this signature — this test is GREEN the moment it is written, so Step 3 is not optional.

- [ ] **Step 3: Mutate to prove the test can fail**

A test that passed the first time it ran is not yet evidence. Temporarily add a fourth parameter `grid=None` to `pattern` in `cli/src/domain/slot_model.py`, re-run the command from Step 2, and confirm the new test **fails**. Then revert the mutation and re-run to confirm it is green again. Do not commit the mutation.

- [ ] **Step 4: Commit**

```bash
git add cli/tests/unit/test_slot_model.py
git commit -m "test(domain): guard pattern's Grid-independence by signature"
```

---

### Task 1: Dataclasses and `initial_state`

Spec §7 step 1 and step 2's first half — the state shape and the unpropagated masks. Not-equals is Task 3; arc consistency is Task 2.

**Files:**
- Create: `cli/src/domain/propagator.py`
- Test: `cli/tests/unit/test_propagator.py`

**Interfaces:**
- Consumes: `SlotModel`, `Slot`, `Crossing`, `pattern`, `fixed_from_grid` from `src.domain.slot_model`; `LetterBitsetIndex` and its primitives `mask`, `letters_at`, `restrict`, `words`, `count` from `src.domain.letter_bitset`.
- Produces: `MinScore`, `DomainState`, `Revision`, `Result`, `initial_state` — Tasks 2, 3 and 4 all import these names.

**Contract — signatures the implementation must expose:**

```python
MinScore = int | Callable[[int], int]

@dataclass
class DomainState:
    model: SlotModel
    word_masks: list[np.ndarray | None]   # parallel to slots; None for a fixed slot
    cell_letters: np.ndarray               # uint64, len size*size; alphabet bitmask per cell
    fixed: tuple[str, ...]

@dataclass(frozen=True)
class Revision:
    source_crossing: int      # crossing index, or -1 for the not-equals rule
    source_slot: int          # the slot whose domain caused the removal
    slot: int                 # the slot revised
    removed: np.ndarray       # uint64 mask of the word ids removed

@dataclass(frozen=True)
class Result:
    state: DomainState
    wiped: tuple[int, ...]            # open slots with an empty mask at the fixed point, by id
    revisions: tuple[Revision, ...]

def initial_state(model, index, fixed, min_score: MinScore = 0) -> DomainState: ...
```

**Behavioral criteria:**
- A slot is **open** iff `pattern(model, s, fixed)` contains `?`, **fixed** otherwise (spec §3).
- For every open slot `s`: `word_masks[s] = index.mask(pattern(model, s, fixed), policy(L_s))`, where `policy` is `min_score` itself when it is an `int` and `min_score(L_s)` when it is callable (spec §2, §7 step 2).
- For every fixed slot `s`: `word_masks[s] is None` (spec §7 step 1).
- `word_masks` is parallel to `model.slots` — `len(word_masks) == len(model.slots)` and index `s` is slot id `s`.
- `initial_state` performs **no** not-equals removal. Step 2's not-equals half belongs to `propagate` (Task 3): `initial_state`'s signature has no `not_equals`, and spec §7 step 8 places step 2 inside `propagate`.
- `cell_letters` is computed by the spec §7 step 7 rule. Step 7 is a pure function of `(model, fixed, word_masks)`, and `cell_letters` is a field of `DomainState` rather than of `Result`, so it is well-defined on any state and is filled in here too — not left zero. Per-cell, in this precedence order (**decision 15**):
  1. cell in `model.blacks` or in `model.unslotted` → `0`, whatever `fixed` holds there.
  2. otherwise `fixed[cell]` non-empty → the single bit of that letter, or `0` if the letter is outside the index alphabet.
  3. otherwise (a slotted, unfilled cell) → all alphabet bits set.
  Then for every **open** slot `s` and position `p`: `cell_letters[s.cells[p]] &= index.letters_at(L_s, p, word_masks[s])`.
- A pattern containing a letter outside the alphabet yields an all-zero mask, never an exception (C1 contract, spec §4).

**Normative cases** — the implementer's tests must cover every row; exact values.

*Initial mask counts on `FIX-A` with an all-empty `fixed`, by slot id 0…9 — these are the values `analyze_constraints` writes as `across_options`/`down_options` for the same slots:*

| `min_score` | `tuple(index.count(m) for m in word_masks)` |
|---|---|
| `0` | `(9, 9, 3, 2, 9, 9, 2, 3, 9, 3)` |
| `30` | `(5, 5, 3, 2, 5, 5, 2, 3, 5, 3)` |
| `lambda L: 40 if L == 3 else 0` | `(2, 2, 3, 2, 2, 2, 2, 3, 2, 3)` |

*Open/fixed classification and mask contents — `FIX-A`, `min_score=0`:*

| `fixed` | slot | pattern | `word_masks[slot]` |
|---|---|---|---|
| all empty | 0 | `???` | the 9 length-3 words |
| `fixed[0..2] = "E","A","R"` | 0 | `EAR` | `None` (fixed slot) |
| `fixed[0..2] = "E","A","R"` | 5 | `E??` | exactly `{EAR}` |
| `fixed[0..2] = "E","A","R"` | 6 | `A???` | empty mask (count `0`) |
| `fixed[0..2] = "X","Y","Z"` | 0 | `XYZ` | `None` — fixed, even though `XYZ` is off-list |
| `fixed[0] = "X"` | 0 | `X??` | empty mask — open, because `?` is present |

*`cell_letters` on `FIX-A`, all-empty `fixed`, `min_score=0`, as letter sets (`—` means `0`). Note these are **not** the full alphabet: the step-7 AND loop runs on the initial masks too, and `letters_at` on a full length-3 mask is already only `EPS` at position 0. Black cells `3, 8, 15, 21` and unslotted cell `20` are `0`.*

| | col 0 | col 1 | col 2 | col 3 | col 4 |
|---|---|---|---|---|---|
| **row 0** | `EPS` | `E` | `AT` | `—` | `AET` |
| **row 1** | `EP` | `AE` | `R` | `—` | `RV` |
| **row 2** | `AT` | `R` | `EI` | `ES` | `E` |
| **row 3** | `—` | `N` | `E` | `A` | `R` |
| **row 4** | `—` | `—` | `ES` | `AP` | `Y` |

*The per-position letter sets those intersect, for reference — `index.letters_at(L, p, index.mask("?" * L, 0))`: length 3 is `EPS, AEP, APRTY`; length 4 is `EN, AE, AR, NR`; length 5 is `AET, RV, EI, ERS, ESY`.*

*Decision 15's precedence, which no other row exercises — `FIX-A` with `fixed[20] = "A"` and nothing else. Cell `20` is white and in `model.unslotted`, in no slot either way, so:*

| assertion | value |
|---|---|
| `cell_letters[20]` | `0` — unslotted wins over the fixed letter |
| every `word_masks[s]` | identical to the all-empty-`fixed` case above |

*Without decision 15 the same cell would carry the single bit of `A`, so this row is the one that distinguishes the two readings. The ratified reading is that cell `20` is a **grid defect** — white but in no entry — so `0` is not a sentinel but the true count of letters that may legally sit there. The typed letter stays readable from `fixed[20]`, and `model.unslotted` is the defect list. Labelling it as a defect in a user-facing report is a C4 question, recorded as a `[NOTE]` under spec §8; C3 adds nothing for it.*

**Traceability note.** `initial_state`'s `min_score` normalisation, the open/fixed split and the `None` for fixed slots are spec §7 steps 1–2. `cell_letters` on an unpropagated state is derived, as argued above. Decision 15's precedence is amendment 0.1.7.

- [ ] **Step 1: Write the failing test**

Design the tests yourself from the contract. Cover every normative row plus the edge cases the criteria imply that the table does not name (a callable `min_score` that varies across the three lengths present; `len(word_masks) == len(model.slots)`).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest cli/tests/unit/test_propagator.py -v`
Expected: FAIL — the module does not exist yet. Confirm the failure is the *absence of the implementation*, not a broken test.

- [ ] **Step 3: Implement to pass the test**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest cli/tests/unit/test_propagator.py -v`
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/propagator.py cli/tests/unit/test_propagator.py
git commit -m "feat(domain): add propagator state and initial_state"
```

---

### Task 2: Arc consistency — `refine` and `propagate` with `not_equals=False`

> Decision 13 (the `_refine` seam and `refine`'s non-mutation) is ratified — both are live requirements below, not proposals.

Spec §7 steps 3, 4, 6 and 7. The not-equals phase (step 5) is stubbed off by `not_equals=False` and lands in Task 3.

**Files:**
- Modify: `cli/src/domain/propagator.py`
- Test: `cli/tests/unit/test_propagator.py`

**Interfaces:**
- Consumes: everything Task 1 produced.
- Produces: `propagate`, `refine`, `_refine` — Task 3 extends all three, Task 4's tests build states with `initial_state` only.

**Contract — signatures the implementation must expose:**

```python
def propagate(model, index, fixed, min_score: MinScore = 0, not_equals: bool = True) -> Result: ...
def refine(state: DomainState, index, min_score: MinScore = 0, not_equals: bool = True) -> Result: ...
def _refine(state: DomainState, index, min_score: MinScore, not_equals: bool,
            queue: Sequence[int]) -> Result: ...
```

**Behavioral criteria:**
- `propagate(...)` is `refine(initial_state(model, index, fixed, min_score), ...)`, with step 2's not-equals half applied in between (Task 3; a no-op while `not_equals=False`).
- `refine(state, ...)` calls `_refine` with the **natural queue**: the **indices into `model.crossings`**, in that order, of every crossing whose two slots are both open. `_refine` takes that sequence as an argument so tests can permute it (**decision 13**). Indices rather than `Crossing` objects, so `Revision.source_crossing` is the queue element itself and needs no lookup; the amendment says only "arc sequence", so this is the plan choosing within it.
- **`refine`, `propagate` and `_refine` do not mutate their argument.** The returned `Result.state` is a new `DomainState` with new `word_masks` and a new `cell_letters` array; the caller's `state` and every array it holds are unchanged afterwards (**decision 13**).
- Revision step (spec §7 step 4), per popped crossing `(cell, a, across_pos, b, down_pos)`:
  `allowed = index.letters_at(L_a, i, mask_a) & index.letters_at(L_b, j, mask_b)`; then `index.restrict(L_a, i, allowed, mask_a)` and likewise for `b`. For **each side that changed**, record a `Revision`, store the new mask, and enqueue every *other* crossing of that slot.
- An empty mask is **not** a stop. Its `letters_at` is `0`, so its crossers empty in turn; the cascade is part of the report.
- Fixed slots are never revised, never enqueued, and never appear in `wiped` (spec §7 step 1). They constrain their crossers only through the letters already in `fixed`.
- `wiped` = the open slots whose mask has `count == 0` at the fixed point, **ascending by id**.
- `Revision.source_crossing` is the index of the crossing in `model.crossings` that drove the removal; `source_slot` is the slot on the other side of it.
- `cell_letters` is recomputed at the fixed point by the Task-1 rule (spec §7 step 7), so it is independent of queue order.
- **State equality** (the predicate the idempotence and confluence tests compare with — `DomainState` is a dataclass holding `list[np.ndarray]`, so `==` raises `ValueError: truth value of an array … is ambiguous` and must not be used): two states are equal iff their `model` and `fixed` are equal, their `word_masks` are pairwise both-`None` or `np.array_equal`, and their `cell_letters` are `np.array_equal`.

**Properties to test** (spec §7 "Properties and tests"):
- **Confluence.** Passing permuted initial queues to `_refine` returns an equal state by the predicate above, every time. Cover at least the natural order, its reverse, and a batch of seeded random shuffles. The order of `revisions` is never asserted — only masks.
- **Idempotence.** `refine(result.state, index, min_score, not_equals=False)` returns a state equal to `result.state` and `revisions == ()`. Non-mutation makes this non-vacuous.
- **Support.** At the fixed point, for every crossing whose two slots are open, `index.letters_at(L_a, i, mask_a) == index.letters_at(L_b, j, mask_b)`.
- **Soundness against brute force.** With `FIXTURE_WORDS` on `FIX-A`, enumerate every complete fill by exhaustive search over `index.words(L, index.mask("?" * L, 0))` per slot. Every word of every complete solution must be in the fixed-point mask of its slot, and a non-empty `wiped` must imply zero solutions.
- **A complete fill uses each word at most once.** The enumerator must enforce distinctness. This is not decoration: on `FIX-B` (Task 3) a repeats-allowed search finds the fill `(SPY, SPY)`, while `not_equals=True` reports `wiped == (0, 1)` — so "`wiped` non-empty ⟹ zero solutions" would reject a correct implementation. With distinctness `FIX-B` has no complete fill and the property holds. Traceable to spec decision 7's rationale: two same-length singletons on one word describe "a state that has no fill". `not_equals=False` stays sound under the same enumerator, because propagation without the rule is a relaxation. On `FIX-A` both readings give the same three fills.

**Normative cases** — exact values.

*`FIX-A`, all-empty `fixed`, `min_score=0`, `not_equals=False`. `wiped == ()`, and the fixed-point mask of each slot is exactly:*

| slot | fixed-point words |
|---|---|
| 0 | `PET, SET` |
| 1 | `EAR, PAR` |
| 2 | `ARISE` |
| 3 | `NEAR` |
| 4 | `SPY` |
| 5 | `PEA, SEA, SPA` |
| 6 | `EARN` |
| 7 | `TRIES` |
| 8 | `SAP` |
| 9 | `EVERY` |

*Brute force on the same input yields exactly **3** complete fills, and the set of words appearing at each slot across them is the table above — arc consistency is exactly tight here, so soundness is an equality, not a containment.*

*`cell_letters` at that fixed point, as letter sets (`—` means `0`):*

| | col 0 | col 1 | col 2 | col 3 | col 4 |
|---|---|---|---|---|---|
| **row 0** | `PS` | `E` | `T` | `—` | `E` |
| **row 1** | `EP` | `A` | `R` | `—` | `V` |
| **row 2** | `A` | `R` | `I` | `S` | `E` |
| **row 3** | `—` | `N` | `E` | `A` | `R` |
| **row 4** | `—` | `—` | `S` | `P` | `Y` |

*`FIX-C` — wipeout in one region with another still open. `SlotModel.from_blacks(5, [4,5,6,7,8,9,14,15,16,17,18,19,24], min_length=3)`, three isolated length-4 across slots and no crossings; `fixed[10..13] = "A","R","I","S"` and `fixed[20] = "V"`:*

| slot | pattern | open? | fixed-point mask |
|---|---|---|---|
| 0 | `????` | open | `EARN, NEAR` |
| 1 | `ARIS` | **fixed** | `None` — off-list, but fixed, so never in `wiped` |
| 2 | `V???` | open | empty |

`wiped == (2,)` — not `(1, 2)`.

**The `Autofill._ac3` oracle — scope it.** `Autofill._ac3` returns `False` at `cli/src/fill/autofill.py:949` the first time a domain empties during revision, so it stops short of a fixed point and leaves the domains downstream of a wipe stale. Therefore:

- **Per-slot domain equality holds only when `_ac3()` returns `True`.** On such a grid, for every open slot `s`: `set(w for w, _ in index.words(L_s, mask_s)) == Autofill.domains[slot_id_map[model.slot_key(s)]]`. Verified: on `FIX-A` blank, `_ac3()` is `True` and all ten slots agree.
- **On any grid, wiped-or-not agrees:** `bool(wiped) == (not _ac3() or has_empty_domain())`. Verified on `FIX-A` blank (`_ac3()=True`, `wiped=()`), on `FIX-A` with `EAR` at cells 0–2 (`_ac3()=False`, `wiped` non-empty) and on `FIX-A` with `X` at cell 0 (`_ac3()=False`, `wiped` non-empty). Assert only this on a wiping fixture — the per-slot sets genuinely differ there, and that is `_ac3`'s early return, not a defect on either side.

**Building the oracle** (no `fill()`, which would run the whole solver):
- `Autofill(grid, word_list, min_score=<the same int passed to propagate>)`, then `af._initialize_csp(grid.get_empty_slots())`, then `af._ac3()`. `pause_controller` defaults to `None`, so `_check_pause_during_setup` is inert.
- Pass a constant **`int`** `min_score` to both sides. The CSP holds a single `int` and cannot express a callable policy.
- `Autofill.slot_id_map` keys are `(row, col, direction)` — the same shape `SlotModel.slot_key` returns — but its ids index the slot list it was given, not `SlotModel`'s. Map through `slot_id_map[model.slot_key(s)]`.
- **Assert the sampling threshold is not crossed** rather than assuming it: `_initialize_csp` replaces a domain with `_stratified_sample(...)` when `len(candidates) > 10000` (`autofill.py:646-648`), and that sampler calls `random.sample`, which would make the oracle non-deterministic. The test must assert that the largest per-slot `len(pattern_matcher.find(pattern, min_score, max_results=None))` is `<= 10000` on the fixture it uses. Assert the inequality; do not hardcode the observed maximum.

**The precondition.** Every analyzer oracle in this plan rests on `pattern(model, s, fixed_from_grid(grid)) == grid.get_pattern_for_slot(slot_dict)` holding byte for byte (spec §7's last property). That invariant is already covered by C2's suite — `cli/tests/unit/test_slot_model.py:441-453`, across three grids — so do not duplicate it here. If those tests ever go red, every oracle below is void, not merely failing.

**One real-list run, marked `slow`.** Spec §11 marks C3 `slow` "when real-list runs", and the spec §7 `[NOTE]` scopes `_ac3`'s exactness to `comprehensive.txt` specifically. Add one test, `@pytest.mark.slow`, that builds `WordList.from_file("data/wordlists/comprehensive.txt")` and a `LetterBitsetIndex` over it, runs `propagate` on `FIX-A` with `not_equals=False` and a constant `int` `min_score`, and checks the same two things against the `Autofill` oracle: the threshold assertion above, and — since `_ac3()` returns `True` on a blank `FIX-A` — per-slot domain equality. `pytest.ini` deselects `slow` by default; run it with `pytest -m slow`.

- [ ] **Step 1: Write the failing test**

Design the tests yourself. Cover every normative row and every property above. Write the brute-force enumerator as test-local scaffolding — it is an oracle, not a second implementation to ship.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest cli/tests/unit/test_propagator.py -v`
Expected: FAIL — `refine`/`propagate` do not exist yet.

- [ ] **Step 3: Implement to pass the test**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest cli/tests/unit/test_propagator.py -v`
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/propagator.py cli/tests/unit/test_propagator.py
git commit -m "feat(domain): add arc-consistency propagation to a fixed point"
```

---

### Task 3: The not-equals rule

> Decision 13 is ratified; the confluence harness below permutes `_refine`'s queue.

Spec §7 step 2's second half and step 5. No code oracle exists — brute force and hand fixtures are the oracle.

**Files:**
- Modify: `cli/src/domain/propagator.py`
- Test: `cli/tests/unit/test_propagator.py`

**Interfaces:**
- Consumes: `initial_state`, `refine`, `_refine`, `propagate`, `DomainState`, `Revision`, `Result` from Tasks 1–2.
- Produces: no new names — `not_equals=True` becomes live on `propagate`, `refine` and `_refine`.

**Behavioral criteria:**
- **Step 2 (in `propagate` only).** After `initial_state`, every **fixed** slot whose text is in the index removes that word id from every same-length **open** mask, recording `Revision(-1, fixed_slot, t, removed)`. A fixed slot whose text is *not* in the index removes nothing.
- **Step 5 (the phase, in `_refine`).** Run **only when the arc queue is empty**, never interleaved. Collect the open slots whose mask is a singleton — that set is a property of the arc-consistent state, so it does not depend on queue order. Each singleton `{w}` clears bit `w` from every **other** same-length open mask; each cleared slot records `Revision(-1, s, t, removed)`, where `s` is the singleton's slot — so two singletons clearing the same slot `t` produce two `Revision`s, one per pair. If the phase removed anything, enqueue every crossing of every slot it changed and return to step 4. Two same-length slots holding the same singleton clear each other and **both wipe**.
- **Fixed point** is reached when the queue is empty *and* a not-equals phase removes nothing (spec §7 step 6).
- `source_crossing` is `-1` for every `Revision` the not-equals rule produces, from both step 2 and step 5.
- Interleaving the rule into the arc queue is **non-confluent** and is why it is a phase — see the spec §7 `[NOTE]`. Do not "optimise" it into the loop.

**Properties to test:**
- **Confluence with `not_equals=True`.** Same permutation harness as Task 2, now with the rule on.
- **Idempotence with `not_equals=True`.**
- **Soundness against brute force** on the fixtures below.

**Normative cases** — exact values.

*`FIX-B`, the twins. `SlotModel.from_blacks(5, [3,4,5,6,7,8,9,13,14,15,16,17,18,19,20,21,22,23,24], min_length=3)` — two isolated length-3 across slots (cells 0–2 and 10–12), no crossings. `fixed[1]="P", fixed[2]="Y", fixed[11]="P", fixed[12]="Y"`, so both patterns are `?PY` and both masks are the singleton `{SPY}`:*

| `not_equals` | slot 0 | slot 1 | `wiped` |
|---|---|---|---|
| `False` | `SPY` | `SPY` | `()` |
| `True` | empty | empty | `(0, 1)` |

*`FIX-G`, the gentle case — the rule removes without collapsing. `SlotModel.from_blacks(5, [3,4,5,6,7,8,9,13,14,15,16,17,18,19,23,24], min_length=3)` — three isolated length-3 across slots (cells 0–2, 10–12, 20–22), no crossings. `fixed[1]="P", fixed[2]="Y", fixed[10]="S"`:*

| slot | pattern | `not_equals=False` | `not_equals=True` |
|---|---|---|---|
| 0 | `?PY` | `SPY` | `SPY` |
| 1 | `S??` | `SEA, SPA, SET, SAP, SPY` | `SEA, SPA, SET, SAP` |
| 2 | `???` | all 9 length-3 words | the 9 minus `SPY` |

`wiped == ()` for both settings.

*`FIX-H`, the step-2 discriminator — same geometry as `FIX-G`, but slot 0 is **fully fixed** instead of an open singleton. `SlotModel.from_blacks(5, [3,4,5,6,7,8,9,13,14,15,16,17,18,19,23,24], min_length=3)` with `fixed[0]="S", fixed[1]="P", fixed[2]="Y", fixed[10]="S"`. Slot 0's pattern is `SPY` — no `?`, so it is fixed, `word_masks[0] is None`, and it is not a singleton the step-5 phase can see. `SPY` **is** in the index, so step 2 alone does the work:*

| slot | pattern | `not_equals=False` | `not_equals=True` |
|---|---|---|---|
| 0 | `SPY` | `None` (fixed) | `None` (fixed) |
| 1 | `S??` | `SEA, SPA, SET, SAP, SPY` | `SEA, SPA, SET, SAP` |
| 2 | `???` | all 9 length-3 words | the 9 minus `SPY` |

`wiped == ()` for both settings. `FIX-G` and `FIX-H` produce identical removals by different rules — `FIX-G` through step 5 (slot 0 open and a singleton), `FIX-H` through step 2 (slot 0 fixed and on-list). Testing only one of them cannot tell the two rules apart.

*Under `not_equals=True` on `FIX-H`, a `Revision` with `source_crossing == -1` and `source_slot == 0` is present for each of slots 1 and 2. Assert presence, never position — `revisions` order is not part of the contract.*

*The off-list contrast — the same fixture with `fixed[0..2] = "X","Y","Z"`. Slot 0 is still fixed, but `XYZ` is not in the index, so step 2 removes nothing and both settings leave slots 1 and 2 at their `not_equals=False` values above.*

*Do **not** use `FIX-A` with `EAR` fixed at cells 0–2 as a step-2 case. It is a fixed on-list word, but slots 6 and 7 wipe immediately on `A???` and `R????` and the cascade empties all nine open slots, so `wiped == (1, 2, 3, 4, 5, 6, 7, 8, 9)` and slot 5 is empty under **both** settings — the fixture cannot discriminate. Slot 5's `{EAR}` is its *initial-state* value, pinned in Task 1, not a fixed-point one.*

*The partial-entry flip (spec §7 `[NOTE]`) — `FIX-A`. With `fixed[0] = "X"` only, slot 0's pattern is `X??`: it is **open**, its mask is empty, and `0 ∈ wiped`. Completing it to `fixed[0..2] = "X","Y","Z"` makes the pattern `XYZ`: slot 0 becomes **fixed**, `word_masks[0] is None`, and `0 ∉ wiped`. That flip is correct behaviour, not a defect.*

- [ ] **Step 1: Write the failing test**

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest cli/tests/unit/test_propagator.py -v`
Expected: FAIL — `not_equals=True` does not yet remove anything, so the `FIX-B` and `FIX-G` rows disagree.

- [ ] **Step 3: Implement to pass the test**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest cli/tests/unit/test_propagator.py -v`
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/propagator.py cli/tests/unit/test_propagator.py
git commit -m "feat(domain): add singleton not-equals propagation as a phase"
```

---

### Task 4: `crossing_counts`

> Decision 14 is ratified **against** this plan's original proposal — see the `len(word)` criterion below, which now requires a `ValueError` with a pinned message.

Spec §7's last primitive. Decision 6 is binding: this is a quantity, and **no ranking rule ships**.

**Files:**
- Modify: `cli/src/domain/propagator.py`
- Test: `cli/tests/unit/test_propagator.py`

**Interfaces:**
- Consumes: `DomainState` and `initial_state` from Task 1.
- Produces: `crossing_counts` — the last public name in the module.

**Contract — signature the implementation must expose:**

```python
def crossing_counts(state: DomainState, index, slot_id: int, word: str) -> tuple[int, ...]: ...
```

**Behavioral criteria:**
- Walk the crossings of `slot_id` in **`model.crossings` order** (which §6 pins as sorted by cell). For each whose **other** slot is open, append
  `index.count(mask_other & bits[L_other][pos_other][letter_index[word[pos_self]]])` — equivalently `index.count(index.restrict(L_other, pos_other, 1 << letter_index[word[pos_self]], mask_other))`.
- **Crossings into fixed slots are omitted** — the returned tuple is shorter, not zero-padded.
- A letter outside the index alphabet contributes `0` for that crossing (not an exception).
- **`len(word)` is validated (decision 14).** Before any crossing is walked, `len(word) != model.slots[slot_id].length` raises exactly `ValueError(f"word {word!r} has length {len(word)}; slot {slot_id} has length {length}")`, where `length` is the slot's length. This follows the family's existing convention: it is a shape guard on a per-call argument, the same class as §4's alphabet cap and §6's `from_blacks` range and `pattern` `len(fixed)` checks. Decision 12 declined to guard *lookups* and is unchanged.
- Decision 6: no ranking rule, no sort, no aggregation. The tuple is returned in crossing order.

**Normative cases** — exact values. All on `FIX-A` with an all-empty `fixed` and `min_score=0`, evaluated on `initial_state` (unpropagated), unless a row says otherwise. Slot 2's crossings are at cells `10, 11, 12, 13, 14` (other slots `5, 6, 7, 8, 9`); slot 7's are at cells `2, 7, 12, 17, 22`.

| call | result |
|---|---|
| `crossing_counts(s, index, 2, "ARISE")` | `(3, 1, 2, 5, 1)` |
| `crossing_counts(s, index, 2, "ZRISE")` | `(0, 1, 2, 5, 1)` — `Z` is outside `AEINPRSTVY` |
| `crossing_counts(s, index, 7, "TRIES")` | `(2, 2, 2, 1, 5)` |
| `crossing_counts(s, index, 2, "SPY")` | raises `ValueError("word 'SPY' has length 3; slot 2 has length 5")` |
| `crossing_counts(s, index, 2, "ARISEN")` | raises `ValueError("word 'ARISEN' has length 6; slot 2 has length 5")` |
| `crossing_counts(s, index, 2, "ARISE")` with `fixed[0]="S", fixed[5]="P", fixed[10]="A"` | `(1, 2, 5, 1)` — slot 5 is now fixed (`SPA`), so the cell-10 crossing is omitted |

**The `analyze_placement_impact` oracle.** On `initial_state` with `min_score=0`, no placed words and no fixed crossing slots, each entry equals the `after` count `analyze_placement_impact(grid, word, slot, word_list, TriePatternMatcher(word_list))` reports for the corresponding crossing slot. Verified for `crossing_counts(s, index, 2, "ARISE")`: the analyzer returns `after` of `3` for `0,0,down`, `1` for `0,1,down`, `2` for `0,2,down`, `1` for `0,4,down` and `5` for `2,3,down` — the same five values, reordered into `model.crossings`' by-cell order. Its keys are `"{row},{col},{direction}"`; map them through `model.slot_key`.

Do **not** extend this oracle to the fixed-crossing or off-list-fixed-word cases: the analyzer counts fixed crossings and reports a phantom elimination for an off-list fixed word (spec §7). Those cases use the hand-built rows above.

- [ ] **Step 1: Write the failing test**

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest cli/tests/unit/test_propagator.py -v`
Expected: FAIL — `crossing_counts` does not exist yet.

- [ ] **Step 3: Implement to pass the test**

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest cli/tests/unit/test_propagator.py -v`
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/propagator.py cli/tests/unit/test_propagator.py
git commit -m "feat(domain): add crossing_counts placement quantity"
```

---

## Before the branch merges

- `pytest` — the default suite, `slow` deselected.
- `npm run build` — must stay clean.
- `bash scripts/docs-check.sh` and `bash scripts/check-guards.sh --full-tree`.
- The research bundle's `applied_gate` goes red on the first commit that moves `main` off its `PIN`. Re-pin once at the end, per the standing note in `.handoff/log.md`; **never loosen it**. Proof is both halves: the five gates green at the new `PIN`, **and** `grep -rl <old-sha> README.md specs/ presentation/` empty outside `_build/applied/fixtures/`.

## Not built (spec §7)

`dom/wdeg` (needs wipeout history from a search; nothing searches — `dom` is `count`); general all-different beyond the singleton rule; any search; any ranking rule (decision 6).
