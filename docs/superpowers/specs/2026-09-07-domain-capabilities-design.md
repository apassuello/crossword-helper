# Domain Capability Family — Design
**Version 0.1.6** · Claude with Arthur Passuello · 2026-09-07 · status: design, approved by owner 2026-09-07
(amended 2026-09-08; this line is not checked by anything — verify it against §13 before citing it)

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified — treat with lower confidence.

Source ids (`A-S3`, `B-T01`, `R-S7`, …) are rows in `docs/resources/SOURCES.md`. They are always
run-prefixed: `A-S7` and `R-S7` are different sources. Research options come only from the six
DELTA sections of `data/research/deep-research-2026-09/presentation/applied.html` (gitignored);
plain-text extracts of those sections were used to write this document.

---

## 1. Scope and ratified decisions

**[SPEC]**
- One mechanism: propagated per-slot candidate sets over a slot/cell model with declared crossings,
  backed by per-(length, position, letter) letter bitsets.
- Built as capabilities, one at a time, each a library module under `cli/src/domain/` with its own
  tests. Nothing is wired to the CLI, the adapter, a route or the UI in this pass.
- Build order: C1 → C2 → C3 → C4 → C1b → C6. There is no C5.

| # | Decision (Arthur, 2026-09-07) | What it beat |
|---|---|---|
| 1 | `lookup` is the first capability | grid-model spec first — no existing oracle |
| 2 | per-(length, position, letter) bitset now [B-T01, B-T10] | CrossHatch inverted index [R-S5] — not rejected, queued as C1b |
| 3 | library module + tests only | a CLI subcommand at the first layer |
| 4 | placement: new package `cli/src/domain/` | `cli/src/fill/letter_bitset.py` beside the retiring matchers |
| 5 | bitsets as NumPy `uint64` rows | Python bigints — no direct Rust analogue |
| 6 | `crossing_counts` is a propagator primitive; **no ranking rule ships** — `applied.html` attests no ranking option | P05 top-k + product [B-P05]; CrossHatch's formula [C-44] |
| 7 | singleton not-equals propagation is implemented, cited `[?]` to A-S3 | leaving it out — a false "not refuted" on two same-length singletons |
| 8 | the live `analyze` command keeps its current scoring; the cost is recorded in §12, no follow-up item | an unfired issue draft; wiring `analyze` to C4 now |
| 9 | *(2026-09-08)* C1b moves to after C4 — spine first, so C2 → C3 gives C1 its first consumer | C1b at position 2: a second lookup index for the same function, unconsumed, making a fourth pattern matcher in the tree §12 already flags |
| 10 | *(2026-09-08)* `direction` serialises as its string | 0/1 ints — honours §6's "ints and lists only" literally, but the dump then matches no existing slot dict |
| 12 | *(2026-09-08)* C2's error contract, pinned here rather than in the plan | leaving it to the plan — the same class of choice as 10 and 11, which were ratified here, so the plan would have been authoring spec |
| 11 | *(2026-09-08)* `crossings` and `unslotted` sorted by cell index | `crossings` by `(across_id, across_pos)` — equally total, reads naturally slot-by-slot in C3, but puts two ordering rules in one dataclass |

**[NOTE]**
Decision 3 is a deliberate, owner-approved exception to the project rule "new capability: CLI
command → adapter → route → React, never skip a layer". The exception is for this pass only.
Decision 6 followed a five-agent red-team of the first draft (2026-09-07): the draft had written a
ranking rule as if one were attested; none is.

---

## 2. Constraints that bind every capability

**[SPEC]**
- Flat and index-based, per run-A §A5: a slot's index is its identity (orca-solver, `A-S41`);
  crossings are stored as data, not recomputed; solver state is arrays parallel to the slot array;
  graph structs carry only ints, tuples and NumPy arrays — no compiled regex, no borrowed payloads.
- Cell index is `row * size + col`. No `(row, col)` tuple keys in any stored structure.
- Alphabet masks are `int` with at most 64 bits — a `u64` in the Rust port. `|alphabet| > 64` raises
  `ValueError` at index build. The cap is an implementation decision, not a research finding.
- Nothing extends `BeamState` (`cli/src/fill/beam_search/state.py`); it lives in the retiring beam
  search.
- Only options attested in `applied.html` are built. An option that is not attested is out of scope
  by construction, however sensible.
- `min_score` is a per-length policy everywhere: `MinScore = int | Callable[[int], int]`. An `int`
  is a constant policy. The callers this family eventually replaces use `get_min_score(length)`.

---

## 3. Shared vocabulary

**[SPEC]**
- Canonical pattern: uppercase, `?` for a blank, every other character a letter of the index's
  alphabet. `Grid.get_pattern_for_slot` already emits this form (`cli/src/core/grid.py`,
  `WILDCARD` in `cli/src/core/cell_types.py`).
- Canonical word order for a length `L`: `sorted(words_of_length_L, key=(-score, text))`. A word's
  id is its position in that order. Both lookup structures use the same order so masks convert.
- Open slot: its pattern contains at least one `?`. Fixed slot: its pattern contains none.
- `fixed`: the letters currently in the grid, every filled white cell, locked or not. Locked-ness is
  provenance and belongs to C6.

```python
# cli/src/domain/wordorder.py
def canonical_words(word_list: WordList) -> dict[int, tuple[ScoredWord, ...]]: ...
```

---

## 4. C1 — lookup: `LetterBitsetIndex`

**[SPEC]**
Option: per-(length, position, letter) bitset — Crosshare [B-T01] and Orca [B-T10] reached it
independently. Module `cli/src/domain/letter_bitset.py`.

Layout, per length `L` with `N_L` words and alphabet size `A`:

```
words[L]  : tuple[ScoredWord, ...]        canonical order
scores[L] : np.ndarray[int32]             parallel to words[L], non-increasing
bits[L]   : np.ndarray[uint64]            shape (L, A, ceil(N_L / 64))
            bit b of bits[L][pos][a][w] is set  ⟺  words[L][64*w + b].text[pos] == alphabet[a]
```

```python
class LetterBitsetIndex:
    alphabet: tuple[str, ...]                     # derived from the word list, sorted
    letter_index: dict[str, int]

    @classmethod
    def from_word_list(cls, word_list: WordList) -> "LetterBitsetIndex": ...

    # the matcher-compatible surface
    def find(self, pattern: str, min_score: int = 30,
             max_results: int | None = None) -> list[tuple[str, int]]: ...
    def count_matches(self, pattern: str, min_score: int = 30) -> int: ...
    def has_matches(self, pattern: str, min_score: int = 30) -> bool: ...

    # the primitives the propagator needs
    def mask(self, pattern: str, min_score: int = 0) -> np.ndarray: ...       # uint64, shape (ceil(N_L/64),)
    def letters_at(self, length: int, pos: int, mask: np.ndarray) -> int: ...  # alphabet bitmask
    def restrict(self, length: int, pos: int, letters: int, mask: np.ndarray) -> np.ndarray: ...
    def words(self, length: int, mask: np.ndarray) -> list[tuple[str, int]]: ...
    def count(self, mask: np.ndarray) -> int: ...                             # popcount

    def stats(self) -> dict: ...                                              # word count, alphabet, bytes
    def save(self, path: Path) -> None: ...                                   # .npz, flat arrays only
    @classmethod
    def load(cls, path: Path) -> "LetterBitsetIndex": ...
```

Behaviour pinned to exact values:
- `from_word_list` takes a `WordList`, never a file path. Length bounds (3–21) and de-duplication
  are inherited from `WordList`'s own validation (`cli/src/fill/word_list.py`).
- The §2 alphabet cap raises exactly
  `ValueError(f"alphabet has {n} letters; the index supports at most 64")`, `n = len(alphabet)`.
- `find` normalises first: `pattern.upper().replace(".", "?")` — the same step
  `TriePatternMatcher.find` performs (`cli/src/fill/trie_pattern_matcher.py`). The primitives do
  **not** normalise; they require a canonical pattern.
- A pattern whose length has no words, an empty pattern, or a pattern containing a letter outside
  the alphabet returns an empty result — `[]` from `find`, an all-zero mask from `mask`. Never an
  exception. (`WordTrie._search_trie` degrades the same way: an unknown letter simply fails
  `if char in node.children`.)
- `find` returns tuples sorted by `(-score, text)`. `max_results=N` returns the first `N` of that
  order — true top-N.
- `min_score` is a prefix bound: `n = searchsorted(-scores[L], -min_score, side="right")`; word
  ids `>= n` are masked off. Words sharing the boundary score are all kept (they precede `n`).
- `restrict(L, pos, letters, mask)` = `mask & OR(bits[L][pos][a] for a in letters)`.
- `letters_at(L, pos, mask)` has bit `a` set iff `any(bits[L][pos][a] & mask)`.
- `save` writes, per length, `bits_L`, `scores_L`, `texts_L` (a NumPy `U` array), plus `alphabet`.
  `load` rebuilds `words[L]` from `texts_L`/`scores_L`. Round trip is exact.
- `stats()` returns exactly the keys `{"words": int, "lengths": tuple[int, ...], "alphabet": str,
  "bytes": int}` — `alphabet` the letters joined in order, `bytes` the summed `nbytes` of every
  stored array. It is the only place the footprint is reported; do not quote its numbers in prose.

Equivalence contract (the test that is written first, RED against a stub):
- For every pattern `p` in a fixed sample and `m in {0, 30, 50}`:
  `sorted(find(p, m)) == sorted(TriePatternMatcher(word_list).find(p, m, max_results=None))`,
  both under key `(-score, text)`. Compared as sorted sequences, never as returned order: this
  index breaks score ties by text, the trie returns a tie group in traversal order.
- `max_results=None` only. See the `[BUG]` below.
- Primitive oracles, all derived from `find`:
  `words(L, mask(p, m)) == find(p, m)`;
  `count(mask(p, m)) == len(find(p, m))`;
  `letters_at(L, pos, mask(p)) == bitmask({w[pos] for w, _ in find(p, 0)})`;
  `restrict(L, pos, letters, mask(p)) == OR(mask(p with pos := a) for a in letters)`.
- Round trip: `load(save(idx))` reproduces every `find` and every primitive result.
- Invariants: no repeated text within a length; lengths present are exactly those `WordList` holds.

**[BUG] The trie's capped `find` is not top-N**
- Symptom: `TriePatternMatcher.find(p, m, max_results=N)` can omit the highest-scoring match.
- Cause: `WordTrie._search_trie` returns early once `len(results) >= max_results`, in traversal
  order (`cli/src/fill/word_trie.py`, the three `max_results` early exits), and `find_pattern`
  sorts and slices only afterwards. Traversal order follows dict insertion — the order
  `build_trie_from_wordlist` adds `word_list.words` — not score.
- Fix: none in this family — the trie is retiring. The equivalence test excludes `max_results`;
  `LetterBitsetIndex.find` documents its own `max_results` as true top-N. Do not "fix" the bitset
  by matching the trie here.

**[NOTE]**
Both shipped word lists are pure A–Z after comment stripping (`data/wordlists/comprehensive.txt`,
`comprehensive_intl.txt`; the only non-letters are `#` header lines). Deriving the alphabet from the
list, rather than hardcoding 26, costs nothing today and keeps the index honest if a list ever
carries accented letters. The test that touches the real list is marked `slow` if it exceeds a
couple of seconds; `pytest.ini` deselects `slow` by default.

**[NOTE] The archive carries no `version` key, and C1b is not the reason to add one**
`save` writes `alphabet`, `bits_{L}`, `scores_{L}` and `texts_{L}` and nothing else. Adding a
`version` scalar later is additive on both sides — `load` derives the lengths it reads from the
`bits_*` keys and ignores keys it does not know, so an older archive reads as the unversioned one.
C1b does not force it: its `InvertedIndex` (§5) is a separate class holding its own `one`/`two`
dicts and never touches these arrays, so the only thing that can invalidate an archive is this
class's own layout changing. Add the key in the commit that first wires a real caller, not before.

---

## 5. C1b — lookup: CrossHatch inverted index

**[SPEC]**
Option: precomputed one- and two-position inverted index, CrossHatch [R-S5]. Module
`cli/src/domain/inverted_index.py`. Built after C4, not second (decision 9) — it is a validation
artefact, not a dependency, and nothing in C2–C4 needs it. The equivalence harness of §4 is
parametrised over both index classes at that point; the deferred C1 Minor "dedup the duplicated
invariant classes" is done in the same pass. This section keeps its number; only the build
position moved (§1, §11).

```python
class InvertedIndex:
    one: dict[int, dict[tuple[int, str], np.ndarray]]              # (pos, letter) -> sorted word ids, per length
    two: dict[int, dict[tuple[int, str, int, str], np.ndarray]]    # (p1, l1, p2, l2) -> sorted word ids
    @classmethod
    def from_word_list(cls, word_list: WordList) -> "InvertedIndex": ...
    def find(self, pattern: str, min_score: int = 30, max_results: int | None = None) -> list[tuple[str, int]]: ...
    def mask(self, pattern: str, min_score: int = 0) -> np.ndarray: ...   # adapter: ids -> uint64 mask over canonical order
```

- Word ids are C1's canonical order (§3), so `mask` is an exact conversion.
- A pattern with three or more fixed positions is answered by intersecting sorted id arrays
  (`np.intersect1d`); the research attests only the one- and two-position tables.
- `find` obeys the whole contract of §4, including normalisation and empty results.
- Detailed layout is decided when C1b is reached. Nothing in C2–C4 depends on C1b.

---

## 6. C2 — slot model and Grid bridge

**[SPEC]**
Research: the three CP model families of Beacham et al. [A-S3] (m1 cell-as-variable,
m2 slot-as-variable, m3 merged) and Botea's two-viewpoint architecture with channelling constraints
[A-S6]. Module `cli/src/domain/slot_model.py`.

What is built: a slot array, a crossing array, and per-cell owner arrays — plain arc consistency
over precomputed crossings, the formulation both papers build on. Botea's two views (cells, slots)
linked by declared crossing data is the *shape*; this is not a claim to implement either paper's
full architecture. m3 was not chosen: nothing downstream needs letter variables and word variables
in one constraint graph, and two typed arrays serialise more simply.

```python
@dataclass(frozen=True)
class Slot:
    id: int
    direction: str            # "across" | "down" — the strings every existing key uses
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
    unslotted: tuple[int, ...]        # sorted cell indices; white cells with no slot either way

    @classmethod
    def from_grid(cls, grid: Grid, min_length: int = 3) -> "SlotModel": ...
    @classmethod
    def from_blacks(cls, size: int, blacks: Iterable[int], min_length: int = 3) -> "SlotModel": ...
    def slot_key(self, slot_id: int) -> tuple[int, int, str]: ...   # (row, col, direction)
    def to_dict(self) -> dict: ...                                   # JSON: ints, strings and lists only
    @classmethod
    def from_dict(cls, d: dict) -> "SlotModel": ...

def fixed_from_grid(grid: Grid) -> tuple[str, ...]: ...              # len size*size; letter or ""
def pattern(model: SlotModel, slot_id: int, fixed: tuple[str, ...]) -> str: ...
```

Behaviour pinned to exact values:
- Slot id = position in `slots`: across runs first in `Grid.enumerate_white_runs` order (row-major),
  then down runs (column-major), keeping runs of `length >= min_length`. Verified against
  `cli/src/core/grid.py`. Ids are stable for a fixed black layout; a change to `blacks` rebuilds.
- `unslotted` is **geometric**: a white cell whose across run and down run are both shorter than
  `min_length`. It is not run-A §A4's zero-owner cell, which is a provenance question (C6).
  A white cell in a two-cell across run and a five-cell down run is owned by the down slot only.
- `crossings` and `unslotted` are both **sorted by cell index**, as `blacks` already is. A cell is
  crossed by at most one across and one down slot, so `Crossing.cell` is unique and the sort is
  total with no tie-break. Round-trip equality and every normative table depend on this order.
- `direction` travels as its string (`"across"`/`"down"`) through `to_dict`/`from_dict`, matching
  every existing slot dict in the codebase. It is the one non-int scalar on the wire.
- `crossings` is derivable from `cell_across`/`cell_down` plus `Slot.cells`; it is materialised
  (orca-solver's shape) and `from_*` asserts the two agree.
- **Errors.** `from_blacks` raises `ValueError` for a black index outside `range(size * size)`;
  duplicates collapse rather than raise. `pattern` raises `ValueError` when
  `len(fixed) != size * size`. Bad lookups are **not** guarded and raise natively —
  `slots[slot_id]` gives `IndexError`, and a negative `slot_id` therefore indexes from the end
  rather than erroring; `from_dict` gives `KeyError` for a missing key. No exact messages are
  pinned: nothing consumes them while the family stays unwired (decision 3).
- `fixed_from_grid` reads every filled white cell — locked or not. Black and empty cells give `""`.
- `pattern` emits the fixed letter or `?` per cell. Invariant test: for every slot,
  `pattern(model, s, fixed_from_grid(grid)) == grid.get_pattern_for_slot(slot_dict)`, byte for byte.
- Square grids only (`size`), inherited from `Grid`. ingrid_core and orca-solver keep width and
  height separately (run-A §A5); the divergence is acknowledged, not fixed here.
- Not built: clue numbering (`cli/src/core/numbering.py` stays), symmetry, any replacement of the
  existing crossing implementations (§12).

Oracles:
- slots: `Grid.get_word_slots(min_length)` — same set of `(row, col, direction, length)`.
- crossings, with positions: for every pair from `SlotIntersectionHelper.get_slot_crossings`, the
  positions from `SlotIntersectionHelper.get_crossing_position`
  (`cli/src/fill/beam_search/utils/slot_utils.py`). `get_slot_crossings` alone carries no
  positions and cannot catch a transposed `across_pos`/`down_pos`.
- a second position oracle — the condition "can be built without side effects" is **met**, checked
  against source: `Autofill(grid, word_list)` creates its own matcher — `TriePatternMatcher` at the
  default `algorithm="trie"` (`autofill.py:86`), a separate class from `PatternMatcher` and not a
  subclass of it — and defaults
  `pause_controller=None`, and `_initialize_csp` builds the constraint graph via its own
  `_get_intersection` (`autofill.py:851`), independent of `SlotIntersectionHelper`. Domains are
  built in the same call, so pass a tiny fixture `WordList` and the oracle stays non-`slow`:
  `Autofill.constraints[i] = [(j, pos1, pos2), ...]` (`cli/src/fill/autofill.py`, built in
  `_initialize_csp`'s crossing loop). Its ids index the slot list it was given, not `SlotModel`'s;
  map through `slot_id_map[model.slot_key(s)]`.
- round trip: `from_dict(to_dict(m)) == m`.

---

## 7. C3 — propagator

**[SPEC]**
Option: AC-3 to a fixed point, ingrid_core [C-46]. Module `cli/src/domain/propagator.py`.
Both views are maintained: word masks per slot (m2) and letter sets per cell (m1).

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
def propagate(model, index, fixed, min_score: MinScore = 0, not_equals: bool = True) -> Result: ...
def refine(state: DomainState, index, min_score: MinScore = 0, not_equals: bool = True) -> Result: ...
def crossing_counts(state: DomainState, index, slot_id: int, word: str) -> tuple[int, ...]: ...
```

Algorithm, pinned:
1. Open and fixed slots per §3. A fixed slot gets `word_masks[s] = None`, is never in `wiped`, and
   constrains its crossers only through `fixed` (its letters are already in their patterns).
2. `initial_state`: `word_masks[s] = index.mask(pattern(model, s, fixed), min_score(L_s))` for every
   open slot. Then, if `not_equals`: every fixed slot whose text is in the index removes that word id
   from every same-length open mask (`Revision(-1, fixed_slot, t, removed)`).
3. Queue: every crossing whose two slots are both open. Arc consistency runs alone — step 5 never
   fires from inside this loop.
4. Pop `(cell, a, i, b, j)`: `allowed = letters_at(L_a, i, mask_a) & letters_at(L_b, j, mask_b)`;
   `new_a = restrict(L_a, i, allowed, mask_a)`, `new_b` likewise. For each side that changed:
   record a `Revision`, store the new mask, and enqueue every other crossing of that slot. An empty
   mask is not a stop: its `letters_at` is `0`, so its crossers empty in turn — the cascade is part
   of the report.
5. Not-equals, singleton level only, run **as a phase and never interleaved**. When the queue
   empties, collect the open slots whose mask is a singleton. That set is a property of the
   arc-consistent state, so it does not depend on queue order. Each singleton `{w}` clears bit `w`
   from every other same-length open mask; each cleared slot records `Revision(-1, s, t, removed)`.
   If the phase removed anything, enqueue every crossing of every slot it changed and return to
   step 4. Two same-length slots holding the same singleton clear each other and both wipe.
6. Fixed point when the queue is empty and a not-equals phase removes nothing. `wiped` = open slots
   with `count == 0`, ascending id.
7. `cell_letters`, computed after the fixed point and independent of queue order: all bits for a
   slotted cell, the single bit of its letter for a fixed cell, `0` for black and unslotted cells;
   then for every open slot `s` and position `p`, `cell_letters[cell] &= letters_at(L_s, p, mask_s)`.
8. `refine(state, ...)` runs steps 3–7 from an existing `DomainState` rather than from `fixed`;
   `propagate` is `refine(initial_state(...))` after step 2. It exists because the idempotence test
   needs an entry point that takes a state, and because re-propagating after one edit is what a
   consumer will want.

`crossing_counts(state, index, slot_id, word)`: for each crossing of `slot_id` in `model.crossings`
order whose other slot is open, `count(mask_other & bits[L_other][pos_other][letter_index[word[pos_self]]])`.
Crossings into fixed slots are omitted. A letter outside the alphabet counts `0`. This is the
least-constraining-value quantity `LCVValueOrdering.order_values` computes by re-placing and
re-matching (`cli/src/fill/beam_search/selection/value_ordering.py`); no ranking rule is built on it
(decision 6).

Properties and tests:
- The fixed point is unique for a given input regardless of queue order, with `not_equals` on or
  off — see the `[NOTE]` on phasing below for why the rule does not break confluence. Tests compare
  masks; the order of `revisions` is never asserted.
- Soundness, brute force on hand-built grids and a hand-built list small enough to enumerate every
  complete fill: every word of every complete solution is in the fixed-point mask of its slot;
  `wiped` non-empty ⟹ zero solutions. Fixtures must include: an unchecked cell, a fixed on-list word,
  a fixed off-list word, a partially typed off-list entry, two same-length slots forced onto one
  word, and a genuine wipeout in one region with another region still open.
- Idempotence: `refine(result.state, ...)` returns an equal state and an empty `revisions`.
- Support: after the fixed point, every word in every open mask has support at every crossing.
- Initial masks vs the live analyzer: `count(initial mask[s])` equals the `across_options` /
  `down_options` `analyze_constraints` writes to that slot's cells
  (`cli/src/core/constraint_analyzer.py`), with `min_score=0` and an uncapped matcher.
- Fixed point vs the existing AC-3: with `not_equals=False` and a constant `min_score` (the CSP
  holds a single `int`), for every open slot `s`,
  `set(w for w, _ in words(mask_s)) == Autofill.domains[slot_id_map[model.slot_key(s)]]` after
  `_ac3()` on the same grid and list, and `bool(wiped) == (not _ac3() or has_empty_domain())`.
  The CSP is initialised from `grid.get_empty_slots()` — slots with at least one empty cell, the
  same set as this module's open slots — so fixed slots are absent on both sides. See the `[NOTE]`
  below for why the comparison is exact.
- `crossing_counts` vs `analyze_placement_impact` `after` counts, on `initial_state` (unpropagated),
  `min_score=0`, no placed words, and no fixed crossing slots — the analyzer counts fixed crossings
  and reports a phantom elimination for an off-list fixed word, so those cases use the hand-built
  fixtures instead.
- `pattern(model, s, fixed) == grid.get_pattern_for_slot(...)` for every slot, or none of the
  analyzer oracles hold.

Not built: `dom/wdeg` (needs wipeout history from search; nothing searches — `dom` is `count`);
general all-different (Régin) beyond the singleton rule; any search.

**[NOTE] Why not-equals is a phase (Claude, after advisor review, 2026-09-07)**
Interleaving the singleton rule into the arc-consistency queue is non-confluent, because the rule
fires on `{w}` and not on the empty set, and a slot on its way to empty may or may not pass through
a singleton depending on queue order. Concretely: `s = {w, x}` with two crossings that each remove
one. One order gives `s = {w}`, the rule strips `w` from a same-length slot `t` in another region,
then the second crossing empties `s`. The other order empties `s` without the rule ever firing, and
`t` keeps `w`. `wiped` and `refuted` agree either way; `t`'s mask, `domain_sizes[t]` and
`cell_letters` do not. Running the rule only on arc-consistent states removes the transient
singleton and restores confluence, at the cost of detecting a not-equals removal one phase later.
Chosen over two alternatives: narrowing the uniqueness claim to `refuted` only, which leaves
`FillabilityReport` irreproducible on any refuted grid; and suppressing the rule once some slot has
wiped, which is order-dependent in its own right.

**[?]**
Beacham et al. [A-S3] describe model m1 as having "word constraints and not-equals constraints".
Run-A's OCR quote stops before saying what the not-equals constraints bind. The singleton rule in
step 5 is cited to A-S3 on that basis until `corpus/A1` (Beacham, p. 4) is read; the rule itself is
kept regardless (decision 7), because without it two same-length singletons on one word report
"not refuted" for a state that has no fill.

**[NOTE]**
The codebase already contains AC-3: `Autofill._ac3` and `_revise` in
`cli/src/fill/autofill.py`, inside the CSP autofill the briefs record as retiring. `_revise` is the
textbook pairwise revise over word sets; this module's step 4 does the same revision in one
`letters_at` and one `restrict` per side. Neither the research section nor the first draft of this
document named the existing implementation; a red-team reviewer did. It is used here as an oracle,
not deleted. It is exact on `comprehensive.txt` because `_initialize_csp` samples a domain only above a
fixed candidate threshold that no length bucket of that list reaches — the test asserts the
threshold is not crossed rather than assuming it.

**[NOTE]**
A partially typed off-list theme entry wipes while it is partial (no dictionary word completes it)
and clears the instant its last letter is typed (it becomes a fixed slot, the user's assertion).
That flip is correct behaviour and is covered by a fixture, not treated as a defect. A per-slot
"user-asserted" flag that would smooth it is provenance — C6.

---

## 8. C4 — fillability

**[SPEC]**
Option: propagate to a fixed point before any guess, Qxw [R-S7] — the only attested option; in
its interactive-assist mode Qxw stops after the first fixed point and never guesses. Module
`cli/src/domain/fillability.py`. Built in the same session as C3.

```python
@dataclass(frozen=True)
class FillabilityReport:
    refuted: bool                      # True: no fill exists under min_score. False: not refuted.
    wiped_slots: tuple[int, ...]
    domain_sizes: tuple[int, ...]      # parallel to slots; -1 for a fixed slot
    cell_letters: np.ndarray           # uint64 per cell — what Qxw's assist mode shows

def assess(model, index, fixed, min_score: MinScore = 0) -> FillabilityReport: ...
```

- `assess` is `propagate` plus a report; `refuted = bool(result.wiped)`.
- The guarantee is one-sided and the field is named for it: `refuted=True` is a proof;
  `refuted=False` certifies nothing. The type carries no threshold, penalty or confidence.
- Not built: any graduated signal. `analyze_constraints`' "critical" threshold and
  `StateEvaluator.evaluate_state_viability`'s penalty ladder
  (`cli/src/fill/beam_search/evaluation/state_evaluator.py`) go past what any source licenses; the
  fillability research section records that a surviving domain "certifies nothing".

**[?] Open, owner's call — an off-list slot completed by its crossings**
By §3 a slot is fixed the moment its pattern has no `?`, whoever filled the cells. Two down entries
can complete a three-letter across as `QZX`: the slot is then fixed, off-list, never in `wiped`, and
`assess` returns `refuted=False` with no field naming it. The §7 `[NOTE]` calls a completed entry
"the user's assertion", which holds when the user typed it and not when the crossings did. Qxw's
assist mode does surface completed non-words. The question: does `FillabilityReport` carry an
`off_list_fixed: tuple[int, ...]`, or is "who asserted this letter" C6 provenance? It decides two of
C3's fixtures. Nothing before C3 depends on the answer.

---

## 9. C6 — ownership (deferred)

**[SPEC]**
Second capability. Three attested options, decided after C3 exists:
- a justification table — every removed value keeps the constraint that removed it, Bessière's
  DnAC-4 [A-S39];
- a per-cell provenance field — CrossHatch's `ContentType` [R-S5], whose own removal path has a
  defect noted in the research;
- entry identity tied to its cells rather than its position — exet [R-S3].

Room left by C2/C3:
- `Revision(source_crossing, source_slot, slot, removed)` is the justification table's row; no
  change to the propagation loop is needed to build A-S39's mechanism.
- `fixed` carries every letter without provenance; a provenance array parallel to it is R-S5's
  layer.
- Slot ids are positional; an exet-style identity map keyed by cell tuples sits over `SlotModel`.

---

## 10. Out of scope

**[SPEC]**
- A ranking rule (decision 6). The two formulae that were read while deciding —
  P05's product over unfilled crossing words after a quality top-k window [B-P05], whose benefit
  the paper reports "only on puzzles of size 9 x 9 and larger" and on the hardest of its four test
  puzzles; CrossHatch's `(crossScore + minCrossScore) * wordScore * (iffy ? 1 : 100)` [C-44] —
  are recorded so the decision is not re-derived.
- "Forced-block provenance" from an earlier handoff: it traces to Leban's theme-first layout
  method [C-2], a placement-feature concern, not a grid-model one.
- Wiring of any kind; replacement of any existing implementation; the Rust port itself.

---

## 11. Build order and test discipline

**[SPEC]**
| Step | Module | Oracle(s) | Marked `slow` when |
|---|---|---|---|
| C1 | `letter_bitset.py` | `TriePatternMatcher.find`; the four primitive derivations; round trip | real-list run exceeds a couple of seconds |
| C2 | `slot_model.py` | `get_word_slots`; `get_slot_crossings` + `get_crossing_position`; `get_pattern_for_slot`; round trip | never |
| C3 | `propagator.py` | brute force; `analyze_constraints`; `Autofill._ac3`; `analyze_placement_impact` | real-list runs |
| C4 | `fillability.py` | C3's, through `assess` | — |
| C1b | `inverted_index.py` | same harness, parametrised | same |
| C6 | `ownership.py` | decided with the option | — |

- Every step: `superpowers:test-driven-development` — the differential test is written first and
  is RED against a stub before any implementation.
- Every step is one conventional commit, additive only (new module, new test). Existing modules
  are not modified in this family's first pass.
- The research bundle's `applied_gate` goes red on the first commit that moves `main` off its
  `PIN`; it is re-pinned once at session end, per the standing note in `.handoff/log.md`.
- No count, timing or pass rate from a run is quoted in this document; `stats()`, the tests and
  `probe_lookup.py` produce those numbers on demand.

---

## 12. Known costs

**[SPEC]**
- The live `analyze` CLI command (`cli/src/cli.py`) calls `analyze_constraints` and
  `analyze_placement_impact`; it keeps its current "critical" threshold and the beam evaluator's
  penalty ladder for as long as nothing consumes C4. Under decision 3 that is the state after this
  family lands, with no consumer, no date and no tracked item (decision 8).
- Crossing logic is implemented independently in seven files under `cli/src/fill/` (all in the
  retiring autofill family, `SlotIntersectionHelper` among them) and once more inline in the live
  `cli/src/core/constraint_analyzer.py`. `SlotModel` is positioned against all of them and replaces
  none in this pass. The project's anti-pattern list names two implementations of one thing as the
  way code diverges; this family adds a third pattern matcher and a second propagator to a tree
  that already has the retiring ones.

---

## 13. Changelog

- **0.1.6** — 2026-09-08 — three corrections from an independent review of the C2 plan. C2's
  error contract moves here from the plan (decision 12): it is the same class of underspecified
  choice as 10 and 11, so resolving it in the plan would have been the plan authoring spec.
  §6 said `Autofill` "creates its own `PatternMatcher`"; at the default `algorithm="trie"` it
  builds a `TriePatternMatcher`, which is not a subclass of `PatternMatcher`. The header version
  line had read 0.1.2 since 0.1.3 landed — nothing checks it, so it drifted silently.
- **0.1.5** — 2026-09-08 — correction, no design change: the class this document called
  `CSPAutofill` in five places is named `Autofill` (`cli/src/fill/autofill.py:42`). `git log -S`
  over `cli/` finds the name `CSPAutofill` in no commit — it never existed, and the error survived
  0.1.0's red-team, both advisor reviews and all of C1, whose oracle was the trie rather than this
  class. Every member the document attributes to it — `_initialize_csp`, `_ac3`, `_revise`,
  `constraints`, `domains`, `slot_id_map` — is correct and is defined on `Autofill`.
- **0.1.4** — 2026-09-08 — planning amendment, C2 only, surfaced writing the C2 plan: pinned the
  sort order of `crossings` and `unslotted` (decision 11) and the wire form of `direction`
  (decision 10) — §6 fixed neither, and two implementers would not have converged on either.
  Resolved §6's conditional second oracle against source: the condition is met, so the oracle is
  in. No behaviour changed that §6 had already fixed.
- **0.1.3** — 2026-09-08 — build order only: C1b deferred to after C4 (decision 9). §1's order line
  and §11's row order updated. No contract, module or oracle changed — §5 already recorded that
  nothing in C2–C4 depends on C1b, so the move is a reordering, not a redesign. The deferred C1
  Minor "dedup the duplicated invariant classes at C1b's parametrisation pass" travels with C1b.
- **0.1.2** — 2026-09-07 — planning amendment, C1 only: pinned the alphabet-cap `ValueError`
  message and the exact key set of `stats()`. Both were interfaces §4 named without fixing, and two
  implementers would not have converged on either. No behaviour changed.
- **0.1.1** — 2026-09-07 — owner approved 0.1.0. Three review findings applied: the singleton
  not-equals rule became a phase between arc-consistency passes, so the fixed point is confluent
  with the rule on (§7); `refine` added, because the idempotence property had no entry point taking
  a state (§7); §4's tie-break sentence corrected — this index does break score ties canonically,
  the trie does not. One open question recorded for the owner in §8. Two claims verified against
  source rather than edited: `get_empty_slots` does mean "at least one empty cell"
  (`cli/src/core/grid.py`) and the trie filters `score >= min_score` (`cli/src/fill/word_trie.py`),
  so §7's oracle and §4's `side="right"` bound both stand.
- **0.1.0** — 2026-09-07 — first design, after a five-agent red-team (C1/C1b, C2, C3/C4, C5, family)
  and two advisor reviews. C5 dissolved into a C3 primitive; not-equals added; `analyze` cost
  recorded; ids run-prefixed; cell index flattened.
