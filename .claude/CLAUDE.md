# Crossword Construction Helper

Crossword puzzle construction toolkit: React frontend, Flask backend, Python CLI.

> **No status claims in this file.** Test counts, pass rates, phase-completion and version-status
> statements go stale silently, then get asserted as fact into every session. For current state run
> `pytest` and read `git log`. CI enforces this — do not re-add them.

**Stack**: Python 3.9+ · Flask 3.0 · Click · NumPy · React 18 · Vite 5 · SCSS
**Build**: pip + npm · **Test**: pytest + vitest

---

## Commands

```bash
python run.py                  # Flask backend -> :5000
npm run dev                    # Vite dev server -> :3000 (proxies /api to :5000)
npm run build                  # must stay clean
pytest                         # default suite; slow tests deselected
pytest -m slow                 # slow suite
npx vitest run                 # frontend tests
python -m cli.src.cli --help   # 14 CLI commands; --help per command is authoritative
```

---

## Architecture

**The CLI is the single source of truth.** All crossword logic lives in `cli/`. The backend is a
thin HTTP wrapper that shells out to it via `backend/core/cli_adapter.py` — that adapter is the
integration seam and the place bugs hide.

```
src/ (React) --HTTP+SSE--> backend/ (Flask) --subprocess--> cli/ (logic)
```

Add capability CLI-first, then adapter, then route, then UI.

---

## Code Patterns

- **New capability**: CLI command → `cli_adapter.py` method → Flask route → React. Never skip a layer.
- **Autofill**: CSP (`fill/autofill.py`), beam search (`fill/beam_search/`), iterative repair
  (`fill/iterative_repair.py`, the `--algorithm` default), and a `hybrid` of beam+repair.
- **Pattern matching**: `fill/pattern_matcher.py` (regex) and `fill/trie_pattern_matcher.py` (trie).
- **Pause/resume**: file-based IPC. CLI serializes solver state to gzipped JSON; resume applies user
  edits as locked cells and continues from that position.
- **Seam tests**: the backend↔CLI boundary needs a contract test on argv acceptance plus one real
  subprocess e2e. Mocks on both sides hide breakage — that is how pause/resume shipped broken.

---

## Anti-Patterns

❌ Crossword logic in `backend/` or `src/` → ✅ implement in `cli/`, expose via the adapter
Why: two implementations diverge; the CLI is the contract.

❌ Mocking both sides of the backend↔CLI seam → ✅ one real-subprocess e2e
Why: a green suite once coexisted with pause/resume broken end to end.

❌ Quoting counts, timings or "FIXED" in docs or docstrings → ✅ name the command that proves it
Why: source docstrings claimed a "454k word" list; the file has ~44k. See `docs/dev/FABRICATION-LOG.md`.

❌ Treating a docstring as prose, not a testable claim about the code beside it → ✅ read them
together; a contradiction is a bug
Why: `beam_search_autofill.py`'s docstring said task_id "is intentionally NOT forwarded" (`950fa79`,
true when written); `2ef7d47` added the `task_id` param and forwarded it in the `super().__init__()`
call below without touching the docstring. Fixed in `fc3f2aa`, which names both commits. No test
covered the difference, so nothing failed. Different failure than the entry above — that one is a
fabricated number, this is a docstring contradicting the code next to it.

❌ Gating a liveness check on an iteration counter → ✅ gate it on elapsed time
Why: `iterations % N == 0` bounds latency only if an iteration is cheap. Pause was polled that way
on both solver paths; a beam iteration on a blank 15x15 outlasts the whole run, so `iterations`
reached 1 in 20s and the pause flag was never read (#26). `autofill.py` already learned this for
timeouts — "checking only every 100 iterations let slow-running grids overrun the timeout budget,
since iteration count alone does not track wall-clock time".

❌ Trusting pre-commit lint to catch a defect in a file the commit didn't touch → ✅ lint the full
tree periodically, not only the diff
Why: `.pre-commit-config.yaml`'s ruff hook runs only on changed files (no `always_run`, unlike
`check-guards`). `backend/tests/unit/test_routes.py` defined `TestFillWithProgress` twice — line 415
(7 methods) and line 655 (2) — Python binds the later class, so the first 7 methods never ran, and
the suite stayed green because no commit touched the file to trigger the lint. F811 fired the moment
one finally did (`0c6ac10`); collection in that file went 51 → 58.

❌ Reaching for `WordList.get_by_length` when you need canonical order → ✅ use
`cli/src/domain/wordorder.py`'s `canonical_words`
Why: `get_by_length` sorts by score alone — the `_length_index` sort at the end of `add_words` is
`key=w.score, reverse=True`, and Python's sort is stable, so equal-scored words keep *insertion*
order. Canonical order is `(-score, text)`. On the six-word fixture the two differ at one tie:
`get_by_length` yields `CAB, ACT` where canonical is `ACT, CAB`. A word's id is its position in
canonical order, so delegating silently renumbers every id — and `LetterBitsetIndex` and the
planned `InvertedIndex` can only convert masks between them because both assign ids from the same
function. The docstring saying "sorted by score descending" is accurate and still not what you want.

❌ Treating an analyzer as an oracle without reading its defaults and its failure mode → ✅ pass
the arguments explicitly and check what it returns after a wipe
Why: four instances, all silent. `PatternMatcher.find` defaults `max_results=100` while
`TriePatternMatcher.find` defaults `None`, and `analyze_constraints`/`analyze_placement_impact`
both call `find(pattern, min_score=0)` bare — pass the wrong matcher and every count caps at 100
with no error. `get_empty_slots`, `analyze_constraints`, `analyze_placement_impact` and
`get_slot_crossings` all call `get_word_slots()` with no argument, so each is valid **only** at
`min_length=3`. And `Autofill._ac3` returns `False` at the first domain it empties
(`autofill.py`'s early return in `_ac3`), leaving downstream domains stale — it is not a
fixed-point oracle after a wipe, though it is a sound one where it returns `True`.

❌ Trusting a fixture because the suite is green → ✅ confirm the fixture can express the
distinction you are pinning
Why: three shapes of the same failure. `FIXTURE_WORDS` produces one `uint64` chunk, so
`Revision.__eq__` returned `True` on masks where `comprehensive.txt` raises. FIX-A is fully
coupled: every `min_score` floor ≤20 removes nothing and every floor ≥25 empties all ten slots, so
partial narrowing is unobservable on it and a real-list row is required, not optional. And a
fixture that collapses to the same fixed point under both settings of a flag tests neither
setting. Check the fixed point, not the initial state, before pinning a row.

❌ Changing behaviour and sweeping only for callers → ✅ sweep for the recorded *reasons* too
Why: decision 16 gave three dataclasses a working `__eq__`, which falsified three separate
"why this workaround exists" claims — a test helper's docstring giving "plain `==` raises" as its
reason to exist, a test module's docstring justifying a field-by-field predicate because `==`/`in`
raise, and a plan bullet describing a migration that never happened. Each was found only because
someone happened to look at it. A workaround outlives the condition that justified it, and its
stated reason is what goes stale first. Sibling of the docstring-as-testable-claim entry above.

❌ Assuming a parameter is covered because its call sites are → ✅ check the *default* path
Why: `min_score` had eighteen nonzero call sites in one test file and every one passed
`not_equals=False`, so the default `not_equals=True` path had zero coverage through either entry
point — on a parameter whose whole point was that it had been silently ignored. The gap predated
the branch that exposed it. Enumerate call sites by argument value, not by name.

❌ Listing what a CI job should include → ✅ exclude what is already covered
Why: both CI holes were a path list, and anything added outside it ran nowhere. `pytest.ini`'s
`testpaths` and `-m slow` already describe the intent; the jobs overrode them with narrower lists,
so two backend test files and 51 of 71 slow tests never ran in CI. An exclusion cannot orphan a new
file. Same family as the pre-commit entry above: a filter that enumerates goes stale silently.

❌ Writing a module-level type alias with `|`, or `eq=False` without an in-body `__eq__` → ✅
`typing.Union` for aliases; `eq=False` **plus** an explicit `__eq__`
Why: two Python semantics this repo has already paid for. A module-level alias is a runtime
expression that `from __future__ import annotations` does not defer, so `MinScore = int |
Callable[[int], int]` raises on the 3.9 floor — annotations may use `|`, aliases may not. And
Python nulls `__hash__` only for a class that defines `__eq__` **in its own body**: bare
`eq=False` leaves `object.__hash__` in place, making the class silently hashable by identity, on
unfrozen classes as well as frozen ones. The second recurs at C4's `FillabilityReport` under
decision 16's family rule.

❌ Passing a numpy-sourced `blacks` or `size` to `SlotModel.from_blacks` → ✅ coerce to `int` at
the construction site
Why: `from_blacks` never coerces, so `numpy.int64` leaks into the model and breaks `to_dict`'s
no-NumPy contract with a `TypeError`. Unreachable through `from_grid`, which is why it has not
fired yet.

---

## Extensibility

- **Skills** (`.claude/skills/`): `crossword-domain` — NYT grid rules, symmetry, entry conventions.
- **Hooks**: `.pre-commit-config.yaml` runs black, isort, ruff, flake8 on commit. Formatting and
  linting are enforced there — do not add style rules to this file.

---

## Git & Docs

- Branch `type/short-description`; commit `type(scope): imperative description`.
- Check out the work branch before running any default-target tool. `/code-review`, `git diff`, `/simplify` and `/security-review` all resolve their own target: with HEAD parked elsewhere — as the research bundle's `applied_gate` requires — `/code-review` took `origin/main...HEAD` and reviewed a tree the work was not in. Pass the target explicitly if HEAD must stay put.
- Before pushing: `pytest`, `npm run build`, let pre-commit run (never `--no-verify`).
- `docs/README.md` is the navigation index; `CONTRIBUTING.md` holds setup and full conventions.
- Living docs under `docs/` use HADS blocks; unverified claims go in `[?]`, never asserted as fact.
