# C2 — SlotModel and Grid Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the second domain capability — a flat, index-based slot/cell model of a grid with
crossings materialised as data, plus the bridge that reads letters out of a `Grid` and renders a
slot's pattern.

**Architecture:** A new module `cli/src/domain/slot_model.py`. `SlotModel` holds a slot array, a
crossing array and two per-cell owner arrays; a slot's identity is its index, and crossings are
stored rather than recomputed. Geometry is separated from content: `SlotModel` depends only on the
black-square layout, while the letters currently in the grid travel separately as a `fixed` tuple.
That split is what lets C3 hold one model constant and propagate over changing letters. Correctness
is established against the shipping implementations — `Grid.get_word_slots`,
`SlotIntersectionHelper`, `Autofill._initialize_csp` and `Grid.get_pattern_for_slot` — none of
which this plan modifies or replaces.

**Tech Stack:** Python 3.9+ · pytest

**Spec:** `docs/superpowers/specs/2026-09-07-domain-capabilities-design.md` (v0.1.6, §1–§3, §6, §11).
Read §2, §3 and §6 before starting. This plan implements **C2 only** — C1b, C3, C4 and C6 are out of
scope. Note the build order changed at v0.1.3: C2 follows C1 directly, and C1b is deferred to after
C4.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.9 is the floor.** CI runs 3.9/3.10/3.11/3.12 (`.github/workflows/test.yml`). PEP 604
  annotations (`int | None`) are a runtime error at 3.9, so **the new module starts with
  `from __future__ import annotations`**, as `cli/src/domain/letter_bitset.py` already does. With
  it, the spec's `X | Y` signature style may be written literally.
- **Line length is 127** for black, isort and ruff (`pyproject.toml`), and for flake8 via
  `--max-line-length=127` in `.pre-commit-config.yaml`. There is no `setup.cfg` in this repo.
  Pre-commit enforces all four; never `--no-verify`.
- **Import root is `cli/`.** Tests and modules import as `from src.domain.slot_model import ...`,
  `from src.core.grid import Grid`, matching every existing test in `cli/tests/unit/`.
- **Flat and index-based** (spec §2): stored structures carry only ints, strings, tuples and NumPy
  arrays. **Cell index is `row * size + col`** — no `(row, col)` tuple keys in any stored structure.
  On a 5×5 grid, `(1, 2)` is cell `7`. This exists so the module can be ported to Rust+WASM later.
- **Square grids only.** `size` is a single dimension, inherited from `Grid` (spec §6).
- **No counts, timings or pass rates in docstrings or comments** — project anti-pattern
  (`.claude/CLAUDE.md`). Name the command that proves a claim instead.
- **Nothing is wired** to the CLI, `cli_adapter.py`, a Flask route or React (spec decision 3).
- **Additive only.** No existing module is modified by any task in this plan. In particular
  `cli/src/core/grid.py`, `cli/src/core/numbering.py`, `cli/src/fill/autofill.py` and
  `cli/src/fill/beam_search/utils/slot_utils.py` are read as oracles and left untouched (spec §6,
  §12).
- **Tests are never `slow`** (spec §11). Every oracle in this plan runs on a small fixture grid and
  a fixture `WordList`; none touches `data/wordlists/comprehensive.txt`.
- **Branch:** `feat/c2-slot-model`, cut from `main`. One commit per task, plus whatever review-fix
  commits the gates produce, then merge — the C1 precedent (`feat/c1-letter-bitset`, which took six
  commits for four tasks). Never commit this plan's work to `main` directly.
- **Commits:** one conventional commit per task, `feat(domain): ...`. No AI attribution trailers.

### Error behaviour

**Pinned by spec §6 and decision 12**, not by this plan. An earlier draft resolved it here; that
was the plan authoring spec, which the writing-plans skill forbids, so it moved. Restated for the
implementer:

- **`ValueError` for input the module rejects** — an out-of-range black index; a `fixed` tuple of
  the wrong length. The codebase convention (`Grid.__init__`, `grid.py:41`).
- **Native `IndexError` / `KeyError` for a bad lookup**, unguarded. A **negative `slot_id` therefore
  indexes from the end and does not raise** — `model.slots[-1]` is slot 9.
- **No exact messages are pinned**; nothing consumes them while the family is unwired (decision 3).

### Fixture traps — both will silently produce the wrong grid

- **`Grid(size, validate_size=True)` rejects any size but 11, 15 and 21** (`grid.py:41`). Every
  test grid in this plan is 5×5, so it **must** be built as `Grid(5, validate_size=False)`.
- **`set_black_square(row, col, enforce_symmetry=True)` defaults to `True`** (`grid.py:51`) and
  places the 180°-rotational partner as well. The fixture below is asymmetric, so every call
  **must** pass `enforce_symmetry=False`. A test that omits it is testing a different grid than the
  one this plan pins.

---

## File Structure

| File | Responsibility |
|---|---|
| `cli/src/domain/slot_model.py` | `Slot`, `Crossing`, `SlotModel`, `fixed_from_grid`, `pattern`. The whole capability. |
| `cli/tests/unit/test_slot_model.py` | Tests for all four tasks. |

`cli/src/domain/__init__.py` already exists (C1) and needs no change.

One module, not three: the three dataclasses and two free functions are a single responsibility —
the geometry of one grid — and they change together. This mirrors `letter_bitset.py`, which holds
its index class and primitives together.

---

## The normative fixture

**Every task tests against this grid.** It is 5×5, asymmetric, and chosen so that `unslotted` is
non-empty and both `cell_across` and `cell_down` carry `-1` entries on white cells.

Blacks at `(0,3)`, `(1,3)`, `(3,0)`, `(4,1)` — cell indices **`(3, 8, 15, 21)`**:

```
col      0 1 2 3 4
row 0    . . . # .
row 1    . . . # .
row 2    . . . . .
row 3    # . . . .
row 4    . # . . .
```

Build it with `Grid(5, validate_size=False)` and place each black with
`set_black_square(row, col, enforce_symmetry=False)` — both flags are mandatory here, see **Fixture
traps** above.

The values below were produced by running the oracles named in each task against this grid; they
are transcribed, not derived by hand. At `min_length=3` it yields 10 slots and 18 crossings.

---

## Task 1: Geometry — dataclasses, construction, cell ownership

**Files:**
- Create: `cli/src/domain/slot_model.py`
- Test: `cli/tests/unit/test_slot_model.py`

**Interfaces:**
- Consumes: `Grid` (`cli/src/core/grid.py`) — `size`, `get_black_squares()`, `is_black(row, col)`.
- Produces: `Slot`, `Crossing`, `SlotModel`, `SlotModel.from_blacks`, `SlotModel.from_grid`,
  `SlotModel.slot_key`. Tasks 2–4 all build their models through `from_grid` / `from_blacks` and
  address slots by `Slot.id`.

**Contract — signatures the implementation must expose:**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class Slot:
    id: int
    direction: str            # "across" | "down"
    row: int
    col: int
    length: int
    cells: tuple[int, ...]    # cell indices, in reading order

@dataclass(frozen=True)
class Crossing:               # orientation pinned: across first
    cell: int
    across_id: int
    across_pos: int
    down_id: int
    down_pos: int

@dataclass(frozen=True)
class SlotModel:
    size: int
    blacks: tuple[int, ...]           # sorted cell indices
    slots: tuple[Slot, ...]           # index == Slot.id
    crossings: tuple[Crossing, ...]   # sorted by .cell
    cell_across: tuple[int, ...]      # len size*size; slot id or -1
    cell_down: tuple[int, ...]        # len size*size; slot id or -1
    unslotted: tuple[int, ...]        # sorted cell indices

    @classmethod
    def from_grid(cls, grid: Grid, min_length: int = 3) -> "SlotModel": ...
    @classmethod
    def from_blacks(cls, size: int, blacks: Iterable[int], min_length: int = 3) -> "SlotModel": ...
    def slot_key(self, slot_id: int) -> tuple[int, int, str]: ...   # (row, col, direction)
```

**Behavioral criteria:**
- `from_grid` delegates to `from_blacks`: the grid contributes its `size` and its black cells, and
  nothing else. Letters in the grid do not affect any field of `SlotModel`.
- Slot order — and therefore slot id — is: **all across runs first in row-major order, then all
  down runs in column-major order**, keeping only runs of `length >= min_length`. This is
  `Grid.enumerate_white_runs`'s order (`grid.py:185`, across loop then down loop) filtered as
  `Grid.get_word_slots` filters it (`grid.py:234`).
- `Slot.cells` lists cell indices in reading order: left-to-right for `"across"`, top-to-bottom for
  `"down"`. `Slot.row`/`Slot.col` are the run's first cell.
- `blacks` is sorted ascending, and holds every black cell whether or not it was passed sorted.
- `cell_across[i]` is the id of the across slot covering cell `i`, or `-1` — for a black cell, for a
  white cell whose across run is shorter than `min_length`, and for a white cell in no across run.
  `cell_down` likewise. Both tuples have length `size * size`.
- `unslotted` is **geometric**: sorted indices of white cells where `cell_across` and `cell_down`
  are *both* `-1`. It is not a provenance or ownership judgement (that is C6, spec §9). A white cell
  in a two-cell across run and a five-cell down run is owned by the down slot and is **not**
  unslotted.
- `crossings` is `()` in this task. Task 2 fills it. **Any test you write asserting
  `model.crossings == ()` is scoped to Task 1 and is superseded there** — Task 2's first step
  rewrites it into the 18-row assertion. Retiring it then is expected, not a licence to weaken
  any other assertion.
- `slot_key(slot_id)` returns `(row, col, direction)` — the key shape
  `Autofill.slot_id_map` uses (`autofill.py:107`, `:619`), so a slot can be looked up across the two
  models.
- `from_blacks` accepts any `Iterable[int]`; a black index outside `range(size * size)` raises
  `ValueError`. Duplicates in the input are collapsed.

**Normative cases** — the implementer's tests must cover every row; exact values.

Model built as `SlotModel.from_grid(g, min_length=3)` on the fixture grid.

`len(model.slots) == 10`, and `model.blacks == (3, 8, 15, 21)`.

| slot id | direction | row | col | length | cells |
|---|---|---|---|---|---|
| 0 | `"across"` | 0 | 0 | 3 | `(0, 1, 2)` |
| 1 | `"across"` | 1 | 0 | 3 | `(5, 6, 7)` |
| 2 | `"across"` | 2 | 0 | 5 | `(10, 11, 12, 13, 14)` |
| 3 | `"across"` | 3 | 1 | 4 | `(16, 17, 18, 19)` |
| 4 | `"across"` | 4 | 2 | 3 | `(22, 23, 24)` |
| 5 | `"down"` | 0 | 0 | 3 | `(0, 5, 10)` |
| 6 | `"down"` | 0 | 1 | 4 | `(1, 6, 11, 16)` |
| 7 | `"down"` | 0 | 2 | 5 | `(2, 7, 12, 17, 22)` |
| 8 | `"down"` | 2 | 3 | 3 | `(13, 18, 23)` |
| 9 | `"down"` | 0 | 4 | 5 | `(4, 9, 14, 19, 24)` |

| field | exact value |
|---|---|
| `cell_across` | `(0, 0, 0, -1, -1, 1, 1, 1, -1, -1, 2, 2, 2, 2, 2, -1, 3, 3, 3, 3, -1, -1, 4, 4, 4)` |
| `cell_down` | `(5, 6, 7, -1, 9, 5, 6, 7, -1, 9, 5, 6, 7, 8, 9, -1, 6, 7, 8, 9, -1, -1, 7, 8, 9)` |
| `unslotted` | `(20,)` |
| `crossings` | `()` |

Cell `20` is `(4, 0)`: its across run is the single cell `[20]` and its down run is the single cell
`[20]`, both shorter than 3. Cells `4` and `9` show the other case — `cell_across` is `-1` (their
across runs are one cell long) while `cell_down` is `9`, so they are owned and not unslotted.

| call | result |
|---|---|
| `model.slot_key(0)` | `(0, 0, "across")` |
| `model.slot_key(9)` | `(0, 4, "down")` |
| `SlotModel.from_blacks(5, [21, 3, 15, 8])` | equal to `SlotModel.from_grid(g)` — input order does not matter |
| `SlotModel.from_blacks(5, [3, 3, 8, 15, 21])` | equal to `SlotModel.from_grid(g)` — duplicates collapse |
| `SlotModel.from_blacks(5, [25])` | raises `ValueError` |
| `SlotModel.from_blacks(5, [-1])` | raises `ValueError` |

**Oracle** — the test must assert this, not just the table:

`[(s.row, s.col, s.direction, s.length) for s in model.slots]` equals
`[(d["row"], d["col"], d["direction"], d["length"]) for d in g.get_word_slots(3)]` — as an **ordered
list**, not a set. Order is what carries the "slot id = position" guarantee; set equality would pass
on a permutation and silently renumber every id. Assert this at `min_length` 1, 2, 3, 4 and 5, since
`Grid.get_word_slots` takes the parameter.

- [ ] **Step 1: Write the failing test**

Design the tests yourself from the contract above. Cover every normative row, the ordered-list
oracle at each `min_length`, and the two `ValueError` cases. Do NOT expect pre-written test code
here — see `superpowers:test-driven-development` and its `writing-good-tests.md`.

Build the fixture with `validate_size=False` and `enforce_symmetry=False` — see **Fixture traps**.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cli && python -m pytest tests/unit/test_slot_model.py -v`
Expected: FAIL — `src.domain.slot_model` does not exist yet. Confirm the failure is the *absence of
the implementation*, not a broken test.

- [ ] **Step 3: Implement to pass the test**

Write `cli/src/domain/slot_model.py` to satisfy the contract and the tests you wrote in Step 1.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cli && python -m pytest tests/unit/test_slot_model.py -v`
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/slot_model.py cli/tests/unit/test_slot_model.py
git commit -m "feat(domain): add SlotModel geometry and cell ownership"
```

---

## Task 2: Crossings

**Files:**
- Modify: `cli/src/domain/slot_model.py`
- Test: `cli/tests/unit/test_slot_model.py`

**Interfaces:**
- Consumes: Task 1's `Slot`, `Crossing`, `SlotModel`, `slot_key`.
- Produces: a populated `SlotModel.crossings`. Task 4 serialises it; C3 walks it.

**Contract:** no new signature. `SlotModel.crossings` stops being `()` and the `from_*`
constructors gain the agreement assertion below.

**Behavioral criteria:**
- One `Crossing` per cell where an across slot and a down slot both cover the cell — i.e. every cell
  `i` with `cell_across[i] != -1` and `cell_down[i] != -1`.
- `crossings` is sorted ascending by `.cell`. `Crossing.cell` is unique across the tuple: a cell has
  at most one across and one down slot, so no tie-break is needed (spec §6).
- `across_pos` is the cell's index within the across slot's `cells`; `down_pos` likewise. Orientation
  is pinned across-first: `across_id` always names an `"across"` slot and `down_id` a `"down"` one,
  whatever order the oracles return them in.
- `from_blacks` and `from_grid` **assert** that the materialised `crossings` agree with
  `cell_across` / `cell_down` plus `Slot.cells` — the spec's word is "asserts" (§6) and this is an
  internal invariant that should never fire, so a bare `assert` is correct here rather than a raised
  domain exception.
- **The assert must compare two independently derived things, or it is a no-op.** If you build
  `crossings` by scanning cells where `cell_across[c] != -1 and cell_down[c] != -1` and then assert
  agreement with those same two arrays, you are checking a value against its own inputs and the
  assert can never fail. Materialise `crossings` from the *slots* — walk each across slot's `cells`
  against the down slot covering each cell — and let `cell_across`/`cell_down` be the independent
  side of the check. Both routes pass all 18 normative rows; only this one has teeth.
- A grid with no crossings at all yields `crossings == ()`, not an error.

**Normative cases** — all 18 crossings of the fixture, in the exact order the field must hold them:

| # | cell | across_id | across_pos | down_id | down_pos |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 5 | 0 |
| 1 | 1 | 0 | 1 | 6 | 0 |
| 2 | 2 | 0 | 2 | 7 | 0 |
| 3 | 5 | 1 | 0 | 5 | 1 |
| 4 | 6 | 1 | 1 | 6 | 1 |
| 5 | 7 | 1 | 2 | 7 | 1 |
| 6 | 10 | 2 | 0 | 5 | 2 |
| 7 | 11 | 2 | 1 | 6 | 2 |
| 8 | 12 | 2 | 2 | 7 | 2 |
| 9 | 13 | 2 | 3 | 8 | 0 |
| 10 | 14 | 2 | 4 | 9 | 2 |
| 11 | 16 | 3 | 0 | 6 | 3 |
| 12 | 17 | 3 | 1 | 7 | 3 |
| 13 | 18 | 3 | 2 | 8 | 1 |
| 14 | 19 | 3 | 3 | 9 | 3 |
| 15 | 22 | 4 | 0 | 7 | 4 |
| 16 | 23 | 4 | 1 | 8 | 2 |
| 17 | 24 | 4 | 2 | 9 | 4 |

Note row 9: cell `13` is `(2, 3)`, where across slot 2 is at position 3 and down slot 8 is at
position 0. A transposed implementation would write `across_pos=0, down_pos=3` and still satisfy a
crossing-set test that ignored positions — which is why the position oracles below are mandatory.

**Oracles — mechanics an implementer will not infer:**

Both oracles read plain dicts with keys `row`, `col`, `direction`, `length`, so build those from
each `Slot`. Neither reads `cells` or `id`.

*Oracle A — `SlotIntersectionHelper` (`cli/src/fill/beam_search/utils/slot_utils.py`):*
- `get_slot_crossings(slot, grid)` gives the crossing **set** for one slot but carries no positions.
- `get_crossing_position(slot1, slot2)` returns `(pos_in_slot1, pos_in_slot2)` — **in argument
  order**, not across-first (`slot_utils.py:96`). Call it as
  `get_crossing_position(across_dict, down_dict)` to get `(across_pos, down_pos)` directly; calling
  it the other way round and forgetting to swap puts the very transposition the spec warns about
  inside the test.
- **`get_slot_crossings` is valid only at `min_length=3`.** It calls `grid.get_word_slots()` with no
  argument (`slot_utils.py:156`), so it always sees the default filter regardless of the model's
  `min_length`. Do not test crossings at other `min_length` values against this oracle.

*Oracle B — `Autofill` (`cli/src/fill/autofill.py`):*
- Build `Autofill(grid, word_list)` then call `_initialize_csp(grid.get_word_slots(3))`. It creates
  its own matcher — `TriePatternMatcher` at the default `algorithm="trie"` (`autofill.py:86`),
  which is a separate class from `PatternMatcher`, not a subclass — and defaults
  `pause_controller=None`, so no further setup is needed (spec §6).
- Read `solver.constraints[i] == [(j, my_pos, other_pos), ...]` (`autofill.py:105`). It builds the
  graph through its own `_get_intersection` (`autofill.py:851`), independent of
  `SlotIntersectionHelper` — that independence is the point of having a second oracle.
- Its slot ids index the list it was *given*, not `SlotModel`'s. Map through
  `solver.slot_id_map[model.slot_key(s)]` (`autofill.py:107`).
- `_initialize_csp` also builds domains, so pass a small fixture `WordList` — for example
  `WordList([("CAT", 50), ("DOG", 50), ("BIRDS", 50), ("HORSE", 50), ("FISH", 50)])`. The test stays
  well under the `slow` threshold; it must not load `comprehensive.txt`.

- [ ] **Step 1: Write the failing test**

Design the tests yourself. Cover all 18 normative rows, both oracles, the sort order, the
uniqueness of `.cell`, and a grid whose model has no crossings.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cli && python -m pytest tests/unit/test_slot_model.py -v`
Expected: FAIL — `crossings` is still `()` from Task 1. Confirm the failure is the empty tuple, not
an import or fixture error.

**Before running:** rewrite Task 1's `crossings == ()` assertion into this task's 18-row
assertion. It is the one Task 1 test this task supersedes; leaving it in place makes Step 4
unreachable, since `crossings` cannot be both empty and 18 rows long.

- [ ] **Step 3: Implement to pass the test**

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cli && python -m pytest tests/unit/test_slot_model.py -v`
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/slot_model.py cli/tests/unit/test_slot_model.py
git commit -m "feat(domain): materialise SlotModel crossings with pinned orientation"
```

---

## Task 3: The Grid bridge — `fixed_from_grid` and `pattern`

**Files:**
- Modify: `cli/src/domain/slot_model.py`
- Test: `cli/tests/unit/test_slot_model.py`

**Interfaces:**
- Consumes: Task 1's `SlotModel` and `Slot.cells`.
- Produces: `fixed_from_grid`, `pattern`. C3 calls `pattern` to seed a slot's domain.

**Contract — signatures the implementation must expose:**

```python
def fixed_from_grid(grid: Grid) -> tuple[str, ...]: ...   # len size*size; letter or ""
def pattern(model: SlotModel, slot_id: int, fixed: tuple[str, ...]) -> str: ...
```

**Behavioral criteria:**
- `fixed_from_grid` returns a tuple of length `size * size`. A filled white cell gives its letter —
  **locked or not**; locked-ness is provenance and belongs to C6 (spec §3, §6). A black cell and an
  empty cell both give `""`.
- `pattern` emits, for each cell of the slot in `cells` order, that cell's letter from `fixed` if it
  is non-empty, otherwise `"?"` — the `WILDCARD` constant (`cli/src/core/cell_types.py:64`). The
  result has length `Slot.length`.
- `pattern` reads only `model` and `fixed`; it never touches a `Grid`. This is the separation the
  whole capability rests on — the model is geometry, `fixed` is content.
- A `slot_id` that `model.slots` itself rejects raises `IndexError`. **Negative indices are not
  guarded** — `model.slots[-1]` is slot 9 natively, and this plan adds no check to change that,
  per the error-behaviour convention above. Do not test `pattern(model, -1, fixed)` as an error.
- `len(fixed) != model.size * model.size` raises `ValueError`.

**The invariant** — this is the task's real acceptance test, and it is byte-for-byte (spec §6):

For every slot in the model, `pattern(model, s.id, fixed_from_grid(grid))` equals
`grid.get_pattern_for_slot({"row": s.row, "col": s.col, "length": s.length, "direction": s.direction})`.

Assert it on the empty fixture grid, and again after each of the placements in the table below.

**Normative cases** — on the fixture grid.

Empty grid: `fixed_from_grid(g)` is 25 empty strings, and every slot's pattern is `"?"` repeated to
its length — `("???", "???", "?????", "????", "???", "???", "????", "?????", "???", "?????")` for
slots 0–9 in id order.

After `g.place_word("CAT", 0, 0, "across")`:

| what | exact value |
|---|---|
| `fixed_from_grid(g)[0:3]` | `("C", "A", "T")` |
| `fixed_from_grid(g)[3]` | `""` (black) |
| `fixed_from_grid(g)[5]` | `""` (empty white) |
| patterns, slots 0–9 in id order | `("CAT", "???", "?????", "????", "???", "C??", "A???", "T????", "???", "?????")` |

Slots 5, 6 and 7 are the down slots through cells 0, 1 and 2 — each picks up exactly one letter at
position 0, which is what makes this placement a useful case rather than a trivial one.

Then, on the same grid, `g.place_word("HORSE", 0, 4, "down", lock=True)` — **a locked placement**,
which is the case that discriminates `fixed_from_grid`'s "locked or not" rule (spec §6). Nothing in
the contract may treat these five cells differently from `CAT`'s:

| what | exact value |
|---|---|
| `g.is_locked(0, 4)` | `True` — and `g.is_locked(0, 0)` is `False`, so the two placements differ in lock only |
| `fixed_from_grid(g)[4], [9], [14], [19], [24]` | `"H"`, `"O"`, `"R"`, `"S"`, `"E"` |
| `fixed_from_grid(g)[0:3]` | `("C", "A", "T")` — unchanged |
| patterns, slots 0–9 in id order | `("CAT", "???", "????R", "???S", "??E", "C??", "A???", "T????", "???", "HORSE")` |

The down word crosses three *across* slots — 2, 3 and 4 pick up `R`, `S` and `E` at their last
position — so this row also exercises the invariant in the orientation `CAT` does not.

| call | result |
|---|---|
| `pattern(model, 10, fixed)` | raises `IndexError` |
| `pattern(model, 0, ("",) * 24)` | raises `ValueError` |

- [ ] **Step 1: Write the failing test**

Design the tests yourself. Cover the table, the invariant over every slot both before and after the
placement, and both error cases. Assert the invariant over every slot three times: on the empty
grid, after `CAT`, and after the locked `HORSE` — the last is the down word that exercises the
other orientation, so no further placement of your own is needed.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cli && python -m pytest tests/unit/test_slot_model.py -v`
Expected: FAIL — `fixed_from_grid` and `pattern` do not exist yet.

- [ ] **Step 3: Implement to pass the test**

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cli && python -m pytest tests/unit/test_slot_model.py -v`
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/slot_model.py cli/tests/unit/test_slot_model.py
git commit -m "feat(domain): add the Grid bridge, fixed_from_grid and pattern"
```

---

## Task 4: Serialisation round trip

**Files:**
- Modify: `cli/src/domain/slot_model.py`
- Test: `cli/tests/unit/test_slot_model.py`

**Interfaces:**
- Consumes: the complete `SlotModel` from Tasks 1–2.
- Produces: `SlotModel.to_dict`, `SlotModel.from_dict`.

**Contract — signatures the implementation must expose:**

```python
    def to_dict(self) -> dict: ...          # JSON: ints, strings and lists only
    @classmethod
    def from_dict(cls, d: dict) -> "SlotModel": ...
```

**Schema.** Keys are the dataclass field names, at every level — `SlotModel`'s seven fields, and
each nested `Slot` and `Crossing` as an object under its own field names. Tuples become lists.
`direction` travels as its string, `"across"` or `"down"`; it is the one non-int scalar on the wire
(spec §6, decision 10).

```
{
  "size": int,
  "blacks": [int, ...],
  "slots": [{"id": int, "direction": str, "row": int, "col": int,
             "length": int, "cells": [int, ...]}, ...],
  "crossings": [{"cell": int, "across_id": int, "across_pos": int,
                 "down_id": int, "down_pos": int}, ...],
  "cell_across": [int, ...],
  "cell_down": [int, ...],
  "unslotted": [int, ...]
}
```

**Behavioral criteria:**
- `from_dict(to_dict(m)) == m` for every model this plan builds. Dataclass equality does the
  comparison, so `from_dict` must restore tuples — a list where a tuple belongs fails equality even
  when every element matches.
- `to_dict()` survives `json.dumps` and `json.loads` unchanged: `from_dict(json.loads(json.dumps(
  m.to_dict()))) == m`. This is what "JSON" in the contract means, and it is a stronger test than
  the in-memory round trip because it collapses tuples to lists on the way through.
- `to_dict` returns plain containers only — no dataclass instances, no NumPy scalars, no sets.
- A dict missing any of the seven keys raises `KeyError`.

**Normative cases** — on the fixture model.

| expression | result |
|---|---|
| `SlotModel.from_dict(m.to_dict()) == m` | `True` |
| `SlotModel.from_dict(json.loads(json.dumps(m.to_dict()))) == m` | `True` |
| `m.to_dict()["size"]` | `5` |
| `m.to_dict()["blacks"]` | `[3, 8, 15, 21]` |
| `m.to_dict()["unslotted"]` | `[20]` |
| `len(m.to_dict()["slots"])` | `10` |
| `len(m.to_dict()["crossings"])` | `18` |
| `m.to_dict()["slots"][0]` | `{"id": 0, "direction": "across", "row": 0, "col": 0, "length": 3, "cells": [0, 1, 2]}` |
| `m.to_dict()["crossings"][9]` | `{"cell": 13, "across_id": 2, "across_pos": 3, "down_id": 8, "down_pos": 0}` |
| `type(SlotModel.from_dict(m.to_dict()).slots)` | `tuple` |
| `SlotModel.from_dict({"size": 5})` | raises `KeyError` |

Round-trip equality is only meaningful because `crossings` and `unslotted` have a pinned order
(spec decision 11); an implementation that rebuilt either in a different order would fail these
rows rather than pass silently.

- [ ] **Step 1: Write the failing test**

Design the tests yourself. Cover both round trips, every table row, and the `KeyError`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd cli && python -m pytest tests/unit/test_slot_model.py -v`
Expected: FAIL — `to_dict` does not exist yet.

- [ ] **Step 3: Implement to pass the test**

- [ ] **Step 4: Run test to verify it passes**

Run: `cd cli && python -m pytest tests/unit/test_slot_model.py -v`
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/slot_model.py cli/tests/unit/test_slot_model.py
git commit -m "feat(domain): add SlotModel to_dict and from_dict"
```

---

## Done criteria for the branch

- `cd cli && python -m pytest tests/unit/test_slot_model.py -v` passes.
- `pytest` from the repo root passes — the default suite, with `slow` deselected.
- `scripts/docs-check.sh` and `scripts/check-guards.sh --full-tree` return 0.
- Pre-commit ran on every commit; no `--no-verify`.
- No file outside `cli/src/domain/slot_model.py` and `cli/tests/unit/test_slot_model.py` changed.

**After merge:** the research bundle's `applied_gate` is red, because every commit moves `main` off
its `PIN`. Re-pin once, per the standing note in `.handoff/log.md` — and remember it needs *both*
proofs, the five gates green at the new `PIN` **and** the old sha absent outside
`_build/applied/fixtures/`.
