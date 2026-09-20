# C4 Fillability Implementation Plan

> **Written 2026-09-13, after the implementation and before its commit.** Every other capability in
> this family (C1, C2, C3, decisions 16–17) got a plan doc before its code; C4 did not, and this
> document closes that gap rather than pretending to predate the module. Treat the task order below
> as the build order the work *followed*, reconstructed from the module and its tests — not as a
> forecast. The tasks are therefore stated with their outcomes, and the checkboxes are left
> unchecked to match the sibling plans, which are also unchecked despite having landed.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or
> superpowers:executing-plans if any task below is reopened. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build `cli/src/domain/fillability.py` — `assess(model, index, fixed, min_score)` runs the
merged C3 propagator to its arc-consistency fixed point and returns a `FillabilityReport` describing
that fixed point, plus one field C4 computes itself.

**Architecture:** C4 is the first consumer of the merged C3 propagator, and through it of C2
(`SlotModel`) and C1 (`LetterBitsetIndex`). It adds one module and one test file; no existing module
is modified. `assess` is `propagate` plus a report — it owns no propagation logic of its own. The
single exception is `off_list_fixed`, which C4 computes by walking `model.slots` itself, for the
reason recorded in Task 3. Nothing is wired to the CLI, adapter, route or UI (spec decision 3).

**Tech Stack:** Python 3.9+ with `from __future__ import annotations`, NumPy `>=1.24.0`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-domain-capabilities-design.md` — §8 is the contract; §2
(project-wide constraints), §3 (vocabulary) and §7 (C3 surface) bind it. Decisions **16** (value
semantics), **18** (no `unslotted_cells`) and **19** (`off_list_fixed`, membership alone) govern the
report's shape and were ratified before this work began, in commit `a7404ca`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Module placement:** `cli/src/domain/fillability.py`, tests in `cli/tests/unit/test_fillability.py`.
  Additive only — no existing module is modified (spec §11).
- **Imports** use the `src.`-rooted form the sibling modules use; the module opens with
  `from __future__ import annotations`.
- **Decision 16's family rule applies to `FillabilityReport`.** It holds an `np.ndarray`
  (`cell_letters`), so it is `@dataclass(frozen=True, eq=False)` **plus an `__eq__` defined in the
  class body**. Bare `eq=False` is not sufficient: Python nulls `__hash__` only for a class that
  defines `__eq__` in its own body, so `eq=False` alone leaves `object.__hash__` in place and the
  class is silently hashable by identity.
- **No `unslotted_cells` field** (decision 18). `model.unslotted` already is that list; the label
  belongs at the rendering layer, which holds the model.
- **`refuted` is one-sided and never graduated.** `True` proves no fill exists under `min_score`;
  `False` certifies nothing. No threshold, no penalty ladder, no confidence score — `analyze_constraints`'
  "critical" threshold and `StateEvaluator`'s penalty ladder both go past what any source licenses.
- **Fixtures pass Python `int` only** into `SlotModel.from_blacks`. It never coerces, so a
  NumPy-sourced `blacks` or `size` leaks `numpy.int64` past `to_dict`'s no-NumPy contract — which
  `to_dict` states and does not enforce, returning normally with the NumPy scalars in place. The
  `TypeError` comes later, from `json.dumps`.
- **Every `SlotModel` in a test is built at `min_length=3`** — every oracle in this repo is valid
  only there.
- **No count, timing or pass rate in any docstring, comment or doc.** Name the command instead.
- **One commit, additive** — module, tests and this plan together.

## The shared fixture

`cli/tests/unit/test_fillability.py` transcribes — does not import — `FIXTURE_WORDS` and three
geometries from `test_propagator.py`. There is no `conftest.py` under `cli/tests`, and this repo
duplicates fixtures per test module by convention; the test module's own docstring records that.

| geometry | blacks | shape | used for |
|---|---|---|---|
| **FIX-A** | `3, 8, 15, 21` | 5×5, 10 slots, 18 crossings, unslotted cell `20` | the crossing-heavy default |
| **FIX-C** | `4,5,6,7,8,9,14,15,16,17,18,19,24` | three isolated length-4 across slots | `off_list_fixed` without crossings |
| **FIX-G** | `3..9, 13..19, 23, 24` | three isolated length-3 across slots | `off_list_fixed` vs C3 step 2 |

FIX-C and FIX-G exist because decision 19 is about a property of a *fixed slot alone* — its word is
on-list or off-list independent of any open slot's domain. An uncrossed geometry isolates that;
FIX-A's crossing-heavy one does not. Module-scoped fixtures: `fixture_word_list`, `bitset_index`,
`model`, `fix_c_model`, `fix_g_model`.

## Tasks

### - [ ] Task 1: `FillabilityReport` — the five fields and decision 16's `__eq__`

The dataclass, frozen, `eq=False`, with an in-body `__eq__`. Exactly five fields, no more:

```python
@dataclass(frozen=True, eq=False)  # decision 16's family rule; __eq__ below
class FillabilityReport:
    refuted: bool
    wiped_slots: tuple[int, ...]
    domain_sizes: tuple[int, ...]      # parallel to slots; -1 for a fixed slot
    cell_letters: np.ndarray           # uint64 per cell
    off_list_fixed: tuple[int, ...]    # decision 19

    def __eq__(self, other: object) -> bool: ...
```

`__eq__` mirrors `Result.__eq__`: `NotImplemented` for a non-report, `==` on the bool and the three
tuples, `np.array_equal` on `cell_letters`. The generated `__eq__` would raise `ValueError` the
moment it reached `cell_letters`, which always holds more than one element.

**Requirements:** fields are exactly the five above; `frozen` is True and `eq` is False; `__eq__`
appears in `FillabilityReport.__dict__`, not merely on the class; `__hash__ is None`; a report is
unhashable. Each of the five fields differing makes two reports unequal — one test per field, so a
field dropped from the comparison chain is caught.

### - [ ] Task 2: `assess` — the four fields read off `Result`

```python
def assess(model: SlotModel, index: LetterBitsetIndex, fixed: tuple[str, ...],
           min_score: MinScore = 0) -> FillabilityReport: ...
```

One call to `propagate`, then read the report off it. `refuted = bool(result.wiped)`;
`wiped_slots = result.wiped`; `cell_letters = result.state.cell_letters` carried through unchanged
(Qxw's assist mode is exactly this array, decoded); `domain_sizes` mirrors `word_masks` positionally
— `-1` where the mask is `None` (a fixed slot), `index.count(mask)` otherwise, read **at the fixed
point**, so a slot the score floor or arc consistency empties reads `0` like any other wiped slot.

`assess` carries **no `not_equals` parameter**; `propagate` runs at its own default (`True`).

**Requirements:** not refuted on the empty grid; `refuted` and `wiped_slots` agree with `propagate`
on a cascading wipeout; `domain_sizes` is parallel to *all* slots and is `-1` for a fixed one;
`cell_letters` matches `result.state.cell_letters` on both an empty grid and a wipeout.

### - [ ] Task 3: `_off_list_fixed` — decision 19, and why it is not delegated

```python
def _off_list_fixed(model: SlotModel, index: LetterBitsetIndex,
                    fixed: tuple[str, ...]) -> tuple[int, ...]: ...
```

Walk `model.slots`; skip any slot whose `pattern(model, slot.id, fixed)` still contains `?` (open,
not fixed); report the rest whose `index.count(index.mask(text, 0)) == 0`.

**Two traps, both load-bearing:**

1. **The score floor is always `0`, never the caller's `min_score`.** Membership is a fact about the
   word list, not something a score floor should gate — a fixed on-list word scoring below the floor
   is still on-list. `min_score` is therefore never passed to this function, and its signature has
   no such parameter so it cannot be passed by accident.
2. **It must not reuse `propagator._fixed_word_removals` or its loop.** That function runs only when
   `not_equals=True` (step 2 of `propagate`, between `initial_state` and `refine`). Delegating would
   silently omit every off-list fixed slot whenever a caller's `propagate` ran with
   `not_equals=False` — and `assess`'s contract carries no parameter guaranteeing which way that
   goes. This module mirrors the per-slot predicate independently, over `fixed` alone rather than
   over `propagate`'s narrowed `word_masks`.

A fixed slot whose text uses a letter outside `index.alphabet` is **off-list, not an error**:
`index.mask` degrades to an all-zero array and never raises, so its count is `0` and it lands in
`off_list_fixed` like any other off-list word. No guard is added, and none should be.

**Requirements:** an open slot is never reported; an out-of-alphabet fixed word is reported; an
on-list fixed word is not; an on-list fixed word under `min_score=99` (above every score in
`FIXTURE_WORDS`) is still not reported — trap 1; a FIX-C off-list fixed slot is reported and never
appears in `wiped_slots`.

### - [ ] Task 4: the partial/complete flip, and agreement with C3 step 2

Two tests that pin the boundary rather than the two sides of it. On FIX-A, a partial entry (`X` in
one cell) leaves the slot **open** — so it can be wiped, and is never in `off_list_fixed`; completing
it to `XYZ` makes the slot **fixed** — so it is not wiped, and is in `off_list_fixed`. The same slot,
one letter apart, swaps every relevant field.

Then, on FIX-G: an on-list fixed word is on-list *and* C3 step 2 removes it from the crossing
domains; an off-list fixed word is off-list *and* C3 step 2 removes nothing. This pins that C4's
independent predicate and C3's own agree where both are defined, without C4 depending on C3 for the
answer.

## Evidence

- `pytest` full suite green at `a7404ca` with the four uncommitted files present, run with nothing
  else executing (a concurrent second suite makes
  `test_hybrid_integration.py::test_fill_simple_grid`'s 30-second wall-clock assertion misfire).
- **Trap 1's test was demonstrated load-bearing by mutation**, at the time it was written. The
  target is `cli/tests/unit/test_fillability.py:284`, `assert 1 not in report.off_list_fixed` — the
  last assertion of `test_fixed_on_list_word_scoring_below_a_nonzero_floor_stays_on_list`.
  Reproducible without any tooling: copy `fillability.py` aside by bytes (it may be untracked, so
  `git checkout` is not a revert), change `_off_list_fixed`'s score floor from the literal `0` in
  `index.mask(text, 0)` to the caller's `min_score`, then

  ```
  pytest 'cli/tests/unit/test_fillability.py::TestOffListFixed::test_fixed_on_list_word_scoring_below_a_nonzero_floor_stays_on_list' -x --tb=line -o addopts=
  ```

  The evidence is an `AssertionError` reported at line 284 — its own assertion, not an upstream
  exception and not a neighbouring test. Restore the file from the copy.
- Contract shape verified directly, not inferred: five fields and no `unslotted_cells`,
  `__hash__ is None` with `__eq__` in the class body, membership via `index.mask(text, 0)`,
  `min_score` never reaching `_off_list_fixed`.

## Before the branch merges

- [ ] Commit C4 (module, tests, this plan) as one additive commit.
- [ ] Re-pin the research bundle's `applied_gate.py` `PIN` **once, after the last commit**, and prove
      it two ways: five gates green at the new PIN, and `grep -rl <old-sha> README.md specs/
      presentation/` returning nothing outside `_build/applied/fixtures/`.
- [ ] Spec §13: add the `0.1.9` changelog entry covering decisions 18 and 19, and correct the
      header — it still reads `0.1.8 · amended 2026-09-10` while §1 and §8 carry 2026-09-11 content.

## Not built (spec §8)

- **`unslotted_cells`** — decision 18. `model.unslotted` is already that list.
- **Any graduated signal on top of `refuted`** — no threshold, no penalty ladder, no confidence.
- **C6 provenance** — decision 19 chose membership precisely because it is separable from knowing
  *who asserted each letter*, which would have blocked C4 on C6.
