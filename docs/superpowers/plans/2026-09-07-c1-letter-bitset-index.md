# C1 — LetterBitsetIndex Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first domain capability — a per-(length, position, letter) bitset index over a
`WordList`, exposing both a matcher-compatible query surface and the bitwise primitives the C3
propagator will consume.

**Architecture:** A new library package `cli/src/domain/`. `wordorder.py` fixes one canonical word
order per length; `letter_bitset.py` builds NumPy `uint64` bitmaps over that order, so a pattern
match becomes a few `AND`s over machine words instead of a trie walk or a regex rescan. Correctness
is established differentially: the index must return the same candidate sets as the shipping
`TriePatternMatcher` on the same word list. Nothing is wired to the CLI, the adapter, a route or the
UI in this pass.

**Tech Stack:** Python 3.9+ · NumPy ≥ 1.24.0 · pytest

**Spec:** `docs/superpowers/specs/2026-09-07-domain-capabilities-design.md` (v0.1.2, §1–§4, §11).
Read §2, §3 and §4 before starting. This plan implements **C1 only** — C1b, C2, C3, C4 and C6 are
out of scope.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **Python 3.9 is the floor.** CI runs 3.9/3.10/3.11/3.12 (`.github/workflows/test.yml`). PEP 604
  annotations (`int | None`) are a runtime error at 3.9, so **every new module starts with
  `from __future__ import annotations`**. That is the established pattern in this tree
  (`cli/src/fill/hybrid_autofill.py`, `cli/src/fill/iterative_repair.py`). With it, the spec's
  `X | Y` signature style may be written literally.
- **Line length is 127** for black, isort, ruff and flake8 (`pyproject.toml`, `setup.cfg`).
  Pre-commit enforces all four; never `--no-verify`.
- **Import root is `cli/`.** Tests and modules import as `from src.domain.letter_bitset import ...`
  and `from src.fill.word_list import WordList`, matching every existing test in `cli/tests/unit/`.
- **Flat and index-based** (spec §2): stored structures carry only ints, tuples and NumPy arrays.
  No compiled regex, no dict keyed by tuples of coordinates, no borrowed payloads. This exists so
  the module can be ported to Rust+WASM later.
- **Alphabet masks are `int` with at most 64 bits** (spec §2). `|alphabet| > 64` raises
  `ValueError` at index build.
- **No counts, timings or pass rates in docstrings or comments** — project anti-pattern
  (`.claude/CLAUDE.md`). Name the command that proves a claim instead. `stats()` is the only place
  a footprint is reported (spec §4).
- **Nothing is wired** to the CLI, `cli_adapter.py`, a Flask route or React (spec decision 3).
- **Additive only.** No existing module is modified by any task in this plan.
- **Tests touching the real word list** (`data/wordlists/comprehensive.txt`) carry
  `@pytest.mark.slow` if they exceed a couple of seconds; `pytest.ini` deselects `slow` by default.
- **Commits:** one conventional commit per task, `feat(domain): ...`. No AI attribution trailers.

---

## File Structure

| File | Responsibility |
|---|---|
| `cli/src/domain/__init__.py` | Package marker. Empty apart from a one-line docstring. |
| `cli/src/domain/wordorder.py` | The single definition of canonical word order per length. Nothing else. |
| `cli/src/domain/letter_bitset.py` | `LetterBitsetIndex`: build, query surface, primitives, persistence. |
| `cli/tests/unit/test_wordorder.py` | Tests for Task 1. |
| `cli/tests/unit/test_letter_bitset.py` | Tests for Tasks 2–4. |

`wordorder.py` is separate from `letter_bitset.py` because C1b (`inverted_index.py`) consumes the
same order, and the two index classes must agree on word ids for their masks to convert (spec §5).
One definition, two consumers.

---

## Task 1: Canonical word order

**Files:**
- Create: `cli/src/domain/__init__.py`
- Create: `cli/src/domain/wordorder.py`
- Test: `cli/tests/unit/test_wordorder.py`

**Interfaces:**
- Consumes: `WordList` and `ScoredWord` from `cli/src/fill/word_list.py`. `ScoredWord` is a
  dataclass with fields `text: str`, `score: int`, `length: int`.
- Produces: `canonical_words(word_list) -> dict[int, tuple[ScoredWord, ...]]`, used by Task 2 and
  later by C1b.

**Contract — signature the implementation must expose:**

```python
from src.fill.word_list import ScoredWord, WordList

def canonical_words(word_list: WordList) -> dict[int, tuple[ScoredWord, ...]]: ...
```

**Behavioral criteria** (spec §3, "Canonical word order"):
- Returns one entry per word length present in `word_list`, keyed by length.
- Within a length, words are ordered by `(-score, text)` — score descending, then text ascending.
  A word's id is its position in that tuple.
- Values are `tuple`, not `list` — the order is a fixed contract, not a mutable buffer.
- A length with no words has no key. An empty `WordList` returns `{}`.
- The function reads `word_list.words` and sorts it. It must **not** delegate to
  `WordList.get_by_length`, which sorts by score alone and leaves equal-scored words in insertion
  order (`cli/src/fill/word_list.py`, the `_length_index` sort in `add_words`). The fixture below
  inserts `CAB` before `ACT` at equal score precisely so that a delegating implementation returns
  the wrong order and fails the second normative row.

**Normative cases** — build a `WordList` from the scored pairs
`[("CAT", 90), ("COT", 90), ("CUT", 70), ("BAT", 50), ("CAB", 30), ("ACT", 30)]`.
The implementer's tests must cover every row; exact values:

| call | result |
|---|---|
| `canonical_words(wl).keys()` | `{3}` |
| `[w.text for w in canonical_words(wl)[3]]` | `["CAT", "COT", "CUT", "BAT", "ACT", "CAB"]` |
| `canonical_words(WordList([]))` | `{}` |
| `type(canonical_words(wl)[3])` | `tuple` |

Add a second length to the fixture (any valid 4-letter words) and assert both keys are present and
each is independently ordered.

- [ ] **Step 1: Write the failing test**

Design the tests yourself from the contract above. Cover every normative row, plus the multi-length
case the criteria imply. See `superpowers:test-driven-development` and its `writing-good-tests.md`.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd cli && python -m pytest tests/unit/test_wordorder.py -v
```
Expected: FAIL — `src.domain.wordorder` does not exist. Confirm the failure is the absence of the
module, not a broken test.

- [ ] **Step 3: Implement to pass the test**

Create `cli/src/domain/__init__.py` and `cli/src/domain/wordorder.py`. Write the body to satisfy the
contract and the tests from Step 1.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd cli && python -m pytest tests/unit/test_wordorder.py -v
```
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/__init__.py cli/src/domain/wordorder.py cli/tests/unit/test_wordorder.py
git commit -m "feat(domain): add canonical word order"
```

---

## Task 2: Index build and the matcher-compatible surface

This is the task the whole capability is chosen for: it is the only piece of the family with an
oracle that already ships (spec decision 1). The differential test is written first and goes RED
against a stub.

**Files:**
- Create: `cli/src/domain/letter_bitset.py`
- Test: `cli/tests/unit/test_letter_bitset.py`

**Interfaces:**
- Consumes: `canonical_words` from Task 1; `WordList` from `src.fill.word_list`;
  `TriePatternMatcher` from `src.fill.trie_pattern_matcher` (test-only, as the oracle) whose
  signature is `find(pattern: str, min_score: int = 30, max_results: Optional[int] = None, progress_callback=None) -> List[Tuple[str, int]]`.
- Produces: `LetterBitsetIndex` with the attributes and query methods below. Task 3 adds primitives
  to the same class; Task 4 adds persistence.

**Contract — signatures the implementation must expose:**

```python
class LetterBitsetIndex:
    alphabet: tuple[str, ...]          # derived from the word list, sorted
    letter_index: dict[str, int]       # letter -> its position in alphabet

    @classmethod
    def from_word_list(cls, word_list: WordList) -> "LetterBitsetIndex": ...

    def find(self, pattern: str, min_score: int = 30, max_results: int | None = None) -> list[tuple[str, int]]: ...
    def count_matches(self, pattern: str, min_score: int = 30) -> int: ...
    def has_matches(self, pattern: str, min_score: int = 30) -> bool: ...
```

Storage layout, per length `L` with `N_L` words and alphabet size `A` (spec §4):

```
words[L]  : tuple[ScoredWord, ...]   canonical order from Task 1
scores[L] : np.ndarray[int32]        parallel to words[L], non-increasing
bits[L]   : np.ndarray[uint64]       shape (L, A, ceil(N_L / 64))

bit b of bits[L][pos][a][w] is set  <=>  words[L][64*w + b].text[pos] == alphabet[a]
```

**Behavioral criteria** (spec §4):
- `from_word_list` takes a `WordList`, never a file path. Length bounds (3–21) and de-duplication
  are inherited from `WordList`'s own validation and are not re-implemented.
- `alphabet` is derived from the words present, sorted ascending — not hardcoded to 26 letters.
- `len(alphabet) > 64` raises exactly
  `ValueError(f"alphabet has {n} letters; the index supports at most 64")`, `n = len(alphabet)`.
- `find` normalises first: `pattern.upper().replace(".", "?")` — the same step `TriePatternMatcher`
  performs. Matching is then: `?` matches any letter, every other character must equal the letter at
  that position.
- `min_score` is a **prefix bound**, exploiting that `scores[L]` is non-increasing:
  `n = searchsorted(-scores[L], -min_score, side="right")`, and word ids `>= n` are masked off.
  `side="right"` keeps words whose score equals `min_score` exactly.
- `find` returns `(text, score)` tuples sorted by `(-score, text)`. `max_results=N` returns the
  first `N` of that order — **true top-N**, unlike the trie (see the `[BUG]` note below).
- Degradation is silent, never an exception: a pattern whose length has no words, an empty pattern,
  or a pattern containing a character outside the alphabet returns `[]`.
- `count_matches(p, m) == len(find(p, m, max_results=None))` and
  `has_matches(p, m) == (count_matches(p, m) > 0)`.

**The differential contract** (spec §4, "Equivalence contract") — the acceptance criterion of this
task:
- For every pattern `p` in the sample below and every `m` in `{0, 30, 50}`:
  `find(p, m)` and `TriePatternMatcher(word_list).find(p, m, max_results=None)` contain the same
  `(text, score)` pairs. Compare as sorted sequences under `(-score, text)`, never as returned
  order: this index breaks score ties by text, the trie returns a tie group in traversal order.
- **`max_results=None` on the trie side, always.** `TriePatternMatcher.find` with a cap is not
  top-N: `WordTrie._search_trie` exits early in dict-insertion traversal order
  (`cli/src/fill/word_trie.py:223`, `:239`, `:261`) and `find_pattern` sorts and slices only
  afterwards (`:181`). Do **not** make the bitset match the trie's capped behaviour — the trie is
  retiring and the bug must not be carried forward (spec §4 `[BUG]`).
- The pattern sample must include, at minimum: all-wildcard; one fixed letter at the first,
  a middle, and the last position; two fixed letters; an all-fixed pattern that is on the list; an
  all-fixed pattern that is not; a pattern containing a letter outside the alphabet; a pattern whose
  length has no words; and the empty string. Each of these answers to a criterion above.

**Normative cases** — same fixture as Task 1:
`[("CAT", 90), ("COT", 90), ("CUT", 70), ("BAT", 50), ("CAB", 30), ("ACT", 30)]`.
Values below were taken from the shipping `TriePatternMatcher` on this fixture, so they are the
oracle's own answers:

| call | result |
|---|---|
| `idx.alphabet` | `("A", "B", "C", "O", "T", "U")` |
| `idx.find("C?T", 0)` | `[("CAT", 90), ("COT", 90), ("CUT", 70)]` |
| `idx.find("C?T", 70)` | `[("CAT", 90), ("COT", 90), ("CUT", 70)]` — 70 is kept, the `side="right"` boundary |
| `idx.find("C?T", 80)` | `[("CAT", 90), ("COT", 90)]` |
| `idx.find("C?T", 0, max_results=2)` | `[("CAT", 90), ("COT", 90)]` — true top-N |
| `idx.find("???", 0)` | `[("CAT", 90), ("COT", 90), ("CUT", 70), ("BAT", 50), ("ACT", 30), ("CAB", 30)]` |
| `idx.find("c.t", 0)` | `[("CAT", 90), ("COT", 90), ("CUT", 70)]` — normalisation |
| `idx.find("Z??", 0)` | `[]` — `Z` is outside this list's alphabet |
| `idx.find("CATS", 0)` | `[]` — no words of length 4 |
| `idx.find("", 0)` | `[]` |
| `idx.count_matches("C?T", 0)` | `3` |
| `idx.has_matches("Z??", 0)` | `False` |
| `LetterBitsetIndex.from_word_list(wl_65)` | raises `ValueError("alphabet has 65 letters; the index supports at most 64")` |

For the last row, build a `WordList` whose words span 65 distinct uppercase alphabetic characters.
`WordList._is_valid_word` accepts any `str.isalpha()` and `str.isupper()` text, so uppercase Greek
or Cyrillic letters qualify alongside A–Z.

**The real-list case.** Add one test running the same differential comparison over the sample
against `data/wordlists/comprehensive.txt`. Two things are pinned so it behaves identically however
pytest is invoked:
- Resolve the path from the test file, never relatively — `REPO_ROOT = Path(__file__).resolve().parents[3]`,
  then `REPO_ROOT / "data" / "wordlists" / "comprehensive.txt"`. That is the existing idiom in
  `cli/tests/integration/test_fill_pause_resume.py:29`, and `parents[3]` is correct from
  `cli/tests/unit/` too. A bare relative path resolves against the repo root under `pytest` and
  against `cli/` under `cd cli && pytest`, so it cannot pass both.
- Load with `WordList.from_file(path, use_cache=False)`. The default is `True`, which reads a 19 MB
  sibling `.pkl` whenever its mtime is not older than the source. Both paths load today and yield
  the same list, so this is for determinism, not correctness: the test should not depend on a build
  artifact's timestamp.

Mark it `@pytest.mark.slow` if it exceeds a couple of seconds.

- [ ] **Step 1: Write the failing differential test**

Design the tests yourself. Write the differential test against a stub `LetterBitsetIndex` whose
`from_word_list` returns a bare instance and whose *query* methods raise, so the RED run fails in
the assertions rather than erroring during fixture setup. A stub that raises at construction makes
every test error identically and proves nothing. Cover every normative row and every pattern class
in the sample list.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd cli && python -m pytest tests/unit/test_letter_bitset.py -v
```
Expected: FAIL. Confirm the failure is the missing implementation, not a broken fixture — a test
that fails because the fixture cannot be built proves nothing.

- [ ] **Step 3: Implement to pass the test**

Build the layout above in `from_word_list`, then the three query methods.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd cli && python -m pytest tests/unit/test_letter_bitset.py -v -o addopts=""
```
Expected: PASS, output pristine, the real-list case included. `-o addopts=""` clears `pytest.ini`'s
default `-m "not slow"` so slow tests run too; do not use a bare `-m slow`, which exits rc=5 when
nothing carries the marker.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/letter_bitset.py cli/tests/unit/test_letter_bitset.py
git commit -m "feat(domain): add LetterBitsetIndex with trie-equivalent lookup"
```

---

## Task 3: Propagator primitives

The primitives are the reason the index exists — C3 calls them in its inner loop, not `find`.

**Files:**
- Modify: `cli/src/domain/letter_bitset.py` (add methods to `LetterBitsetIndex`)
- Test: `cli/tests/unit/test_letter_bitset.py` (add cases)

**Interfaces:**
- Consumes: the storage layout built in Task 2.
- Produces: the five primitives below. C3 (`propagator.py`, a later plan) is the consumer:
  `mask` seeds a slot's domain, `letters_at` and `restrict` are the two halves of one arc revision,
  `count` is the domain size, `words` materialises a domain for display.

**Contract — signatures the implementation must expose:**

```python
    def mask(self, pattern: str, min_score: int = 0) -> np.ndarray: ...            # uint64, shape (ceil(N_L/64),)
    def letters_at(self, length: int, pos: int, mask: np.ndarray) -> int: ...      # alphabet bitmask
    def restrict(self, length: int, pos: int, letters: int, mask: np.ndarray) -> np.ndarray: ...
    def words(self, length: int, mask: np.ndarray) -> list[tuple[str, int]]: ...
    def count(self, mask: np.ndarray) -> int: ...
```

**Behavioral criteria** (spec §4):
- **The primitives do not normalise.** They require a canonical pattern — uppercase, `?` for a
  blank, every other character a letter of the alphabet. Only `find` normalises. No test asserts
  behaviour on non-canonical input to a primitive.
- Note the default divergence, and preserve it: `find` defaults `min_score=30` (mirroring
  `TriePatternMatcher`), the primitives default `min_score=0`.
- `mask(p, m)` returns an all-zero array for the same degenerate inputs `find` returns `[]` for:
  a length with no words, an empty pattern, a letter outside the alphabet. Never an exception.
- `restrict(L, pos, letters, mask)` equals `mask & OR(bits[L][pos][a] for a in letters)`, where
  `letters` is an alphabet bitmask.
- `letters_at(L, pos, mask)` has bit `a` set iff `any(bits[L][pos][a] & mask)`.
- `count(mask)` is a popcount over the whole array.
- `words(L, mask)` returns `(text, score)` tuples in canonical order.

**Normative cases** — same fixture. `bit(letter)` below means `1 << idx.letter_index[letter]`:

| call | result |
|---|---|
| `idx.count(idx.mask("C?T"))` | `3` |
| `idx.count(idx.mask("Z??"))` | `0` |
| `idx.count(idx.mask("CATS"))` | `0` |
| `idx.words(3, idx.mask("C?T"))` | `[("CAT", 90), ("COT", 90), ("CUT", 70)]` |
| `idx.letters_at(3, 1, idx.mask("C?T"))` | `bit("A") \| bit("O") \| bit("U")` |
| `idx.letters_at(3, 0, idx.mask("???"))` | `bit("A") \| bit("B") \| bit("C")` |
| `idx.words(3, idx.restrict(3, 1, bit("A") \| bit("O"), idx.mask("C?T")))` | `[("CAT", 90), ("COT", 90)]` |
| `idx.count(idx.restrict(3, 1, 0, idx.mask("C?T")))` | `0` — empty letter set empties the mask |

**Derived oracles** — assert these as properties over the Task 2 pattern sample and
`m in {0, 30, 50}`, not just on the rows above (spec §4, "Primitive oracles"):
- `words(L, mask(p, m)) == find(p, m, max_results=None)`
- `count(mask(p, m)) == len(find(p, m, max_results=None))`
- `letters_at(L, pos, mask(p)) == OR(bit(w[pos]) for w, _ in find(p, 0, max_results=None))`
- `restrict(L, pos, letters, mask(p)) == OR(mask(p with position pos replaced by a) for a in letters)`

**Invariants** to assert on the real list as well as the fixture: no repeated text within a length;
the lengths present are exactly those `WordList` holds. Load the real list exactly as Task 2 pins it
— `parents[3]`-anchored path, `use_cache=False`.

- [ ] **Step 1: Write the failing test**

Design the tests yourself. Cover every normative row and all four derived oracles as properties over
the sample.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd cli && python -m pytest tests/unit/test_letter_bitset.py -v
```
Expected: FAIL on the new cases — the primitives do not exist. Task 2's cases still pass.

- [ ] **Step 3: Implement to pass the test**

- [ ] **Step 4: Run test to verify it passes**

```bash
cd cli && python -m pytest tests/unit/test_letter_bitset.py -v -o addopts=""
```
Expected: PASS, output pristine.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/letter_bitset.py cli/tests/unit/test_letter_bitset.py
git commit -m "feat(domain): add bitset primitives for constraint propagation"
```

---

## Task 4: Persistence and stats

**Files:**
- Modify: `cli/src/domain/letter_bitset.py`
- Test: `cli/tests/unit/test_letter_bitset.py`

**Interfaces:**
- Consumes: the storage layout and primitives from Tasks 2–3.
- Produces: `save` / `load` / `stats`. No later task in this plan consumes them; they exist so an
  index need not be rebuilt per process.

**Contract — signatures the implementation must expose:**

```python
    def stats(self) -> dict: ...
    def save(self, path: Path) -> None: ...
    @classmethod
    def load(cls, path: Path) -> "LetterBitsetIndex": ...
```

**Behavioral criteria** (spec §4):
- `save` writes a NumPy `.npz` containing, per length `L`, the arrays `bits_{L}`, `scores_{L}` and
  `texts_{L}` (a NumPy `U` array), plus a single `alphabet` array. **Flat arrays only** — no
  pickled objects, so the file stays readable from a future Rust port (spec §2).
- `save` writes to exactly the path it is given: the caller supplies the `.npz` suffix, and `save`
  must not let `np.savez` append one. `np.savez` appends `.npz` when the name lacks it, which would
  leave `load(path)` looking at a file that does not exist.
- `load` rebuilds `words[L]` from `texts_{L}` and `scores_{L}`. The round trip is exact: a loaded
  index reproduces every `find` result and every primitive result of the index that saved it.
- `stats()` returns exactly the keys
  `{"words": int, "lengths": tuple[int, ...], "alphabet": str, "bytes": int}` — `alphabet` is the
  letters joined in order, `bytes` the summed `nbytes` of every stored array.
- `stats()` is the only place a footprint is reported. Its numbers are never quoted in a docstring,
  a comment, or a commit message.

**Normative cases** — same fixture:

| call | result |
|---|---|
| `idx.stats()["words"]` | `6` |
| `idx.stats()["lengths"]` | `(3,)` |
| `idx.stats()["alphabet"]` | `"ABCOTU"` |
| `sorted(idx.stats().keys())` | `["alphabet", "bytes", "lengths", "words"]` |
| `idx.stats()["bytes"]` | any positive `int` — the value is not pinned and must not be asserted exactly |
| `LetterBitsetIndex.load(p).find("C?T", 0)` after `idx.save(p)` | `[("CAT", 90), ("COT", 90), ("CUT", 70)]` |

Assert the round trip as a property, not only on one pattern: for every pattern in the Task 2 sample
and every `m in {0, 30, 50}`, the loaded index and the original agree on `find`, `mask`, `count`,
`letters_at` and `words`. Use pytest's `tmp_path` fixture for the file.

- [ ] **Step 1: Write the failing test**

- [ ] **Step 2: Run test to verify it fails**

```bash
cd cli && python -m pytest tests/unit/test_letter_bitset.py -v
```
Expected: FAIL on the new cases only.

- [ ] **Step 3: Implement to pass the test**

- [ ] **Step 4: Run the full suite**

```bash
cd cli && python -m pytest tests/unit/test_letter_bitset.py tests/unit/test_wordorder.py -v -o addopts=""
pytest
npm run build
```
Expected: PASS, output pristine. `pytest` from the repo root runs the default suite across
`backend/tests cli/tests tests`; it must stay green, and `npm run build` must stay clean, before the
final commit.

- [ ] **Step 5: Commit**

```bash
git add cli/src/domain/letter_bitset.py cli/tests/unit/test_letter_bitset.py
git commit -m "feat(domain): add LetterBitsetIndex persistence and stats"
```

---

## After the last task

- The research bundle's `applied_gate` has been red since the first commit that moved `main` off its
  `PIN`. Re-pin **once**, at session end, per the standing note in `.handoff/log.md` — and prove it
  with both checks that note requires: the five gates green at the new `PIN`, **and**
  `grep -rl <old-sha> README.md specs/ presentation/` returning nothing outside
  `_build/applied/fixtures/`.
- C1b (`inverted_index.py`) is the next capability. It reuses `canonical_words` and the Task 2
  differential harness, parametrised over both index classes (spec §5).
- The open question in spec §8 (`off_list_fixed`) still awaits the owner. It binds C3's fixtures,
  not C1 — nothing in this plan depends on the answer.
