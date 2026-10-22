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
python -m cli.src.cli --help   # lists the CLI commands; --help per command is authoritative
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
- **Spec decisions in code**: when code implements a spec decision, the docstring cites it by
  number — the `Decision 16 (spec 0.1.8, section 7)` form in `cli/src/domain/`, enumerable with
  `git grep -E 'Decision [0-9]+' -- cli`. The 2026-09-19 audit found the decision family cited this
  way survived intact and the one with zero code citations rotted; citation density predicts
  durability better than document quality.

---

## Anti-Patterns

❌ Crossword logic in `backend/` or `src/` → ✅ implement in `cli/`, expose via the adapter
Why: two implementations diverge; the CLI is the contract.

❌ Mocking both sides of the backend↔CLI seam → ✅ one real-subprocess e2e
Why: a green suite once coexisted with pause/resume broken end to end.

❌ Writing any value a command could produce — counts, timings, "FIXED", diff totals — by hand in
docs or docstrings → ✅ name the command that proves it
Why: source docstrings claimed a "454k word" list; the file has ~44k. See `docs/dev/FABRICATION-LOG.md`.
Second instance: commit `cd75876`'s own message states dead cited paths fell "35 -> 19" and, four
lines later, that "19 of the 35 dead path citations were in these eight files" — which would leave
16. One commit message, two incompatible numbers, both written by hand where a command could have
produced one.

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
`min_length=3`. And `Autofill._ac3` is unsound in **both** directions, so
neither branch of its return value may be gated on: run it for its pruning side effect and
inspect `self.domains` directly. **Primary record: `cli/src/fill/autofill.py:437`** (the
`_unwind_dead_ends` call site, stating why `True` must not be early-exited on) and **`:901`**
(what the return value is not, cited to #17). Both state the mechanism in place, beside the code
it governs — do not restate them here.

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
Why: `from_blacks` never coerces, so `numpy.int64` reaches the model. `to_dict`'s docstring
promises "ints and strings only -- no ... NumPy scalars" and **enforces nothing**: it returns
normally with `size` and every element of `blacks` still `numpy.int64` (`slots[*].row/col/length`
survive as plain `int`, being products of Python arithmetic). The contract breaks *silently*; the
`TypeError` — `Object of type int64 is not JSON serializable` — surfaces a layer later, in
`json.dumps`, at whatever call site serialises the model. A silent breach is the worse failure, so
do not expect `to_dict` to raise and tell you. Unreachable through `from_grid`, which is why it has
not fired yet. Measured on `from_blacks(np.int64(5), np.array([3,8,15,21]))`.

❌ Sweeping for references with `git grep` or recursive `grep` and reading a null as "unreferenced"
→ ✅ search `data/research/` and `.handoff/` by explicit path as well; `scripts/check-guards.sh`
Guard 3 blocks the one case it can decide
Why: both trees are gitignored (`.gitignore:106`, `:123`), so `git grep` (tracked only) and the
ugrep-wrapped recursive `grep` return the *same* clean null — while `applied.html`, inside one of
them, quotes live code by symbol. **Primary record: `scripts/check-guards.sh:121`.** That comment
block carries the genesis (`7b0060c` deleted `get_slot_by_id`; `b4253fd` restored it), why it was
load-bearing, the name-extinction scope, the two cases that stay a non-blocking NOTE, and the
measured true/false-positive counts. Amend the script, not this entry; a silent Guard 3 is not
proof the page is intact.

❌ Asserting provenance from a doc that paraphrases the issue → ✅ open the issue
Why: `4cd4fe3` claimed a gating form "is the bug #17 fixed", taken from `ALGORITHM_DEEP_DIVE.md`.
#17 says the opposite branch. Corrected in `1178679` — and the *source* sentence was still false
three sections away at `ALGORITHM_DEEP_DIVE.md:287-288`, where `8220500` had edited the same
paragraph the same day without touching it. Fixing the paraphrase does not fix what it paraphrased,
so the claim comes back. Sibling of the docstring-as-testable-claim entry: same failure, different
artifact.

❌ Adopting a guard pattern because it reads right → ✅ run it over the tree and count true vs
false before it lands
Why: three instances. A bare decimal-`%` rule fired on black-square density, fill thresholds,
timeout ratios and a URL-encoded badge link — four false to one true. Guard 3's bare-identifier
form fires on three of `7b0060c`'s seventeen removed names where only one is real, because six
classes define `order_values` in one file and a citation of a *surviving* same-named symbol reads
exactly like a true hit; adding "no definition survives" gives 1 true, 0 false. And the `docs-check`
extension inversion was measured over its 117 newly reachable files before landing: one hit, the
true positive, zero false. A guard noisy enough to distrust only teaches everyone to reach for the
escape hatch. Measure it against the defect that motivated it as well as the tree: the 2026-09-19
doc-reference guard scored 0 true / 1 false where Guard 3 scored 1 / 0 on the same commit, and its
motivating defect — a paragraph in `ALGORITHM_DEEP_DIVE.md` describing a since-deleted function's
behaviour without ever naming it, before `3a40b28` — was undetectable by any symbol predicate. Closed at the gate; T1 of the archived governance-recurrence plan holds the
measurement.

❌ Treating a guard's own source as out of its own scope → ✅ the guard must pass the guard
Why: the guard that enforces a rule is the one file most likely to quote what it bans. <!-- docs-check: allow (the primary names the banned figure) -->
**Primary record: `scripts/docs-check.sh`** — its header and `live_code()` comment blocks carry the
genesis (the banned figure quoted at `:26`, the include list `1abbf61` claimed to abolish, the
extension-layer inversion in `ff8e561`) and the measured true/false counts. Amend the script, not
this entry. The one thing not recorded there: prove such a fix **red then green on the tracked
file** — `live_code()` enumerates via `git ls-files`, so running a `/tmp` copy of the script scans
the real tree and tests nothing.

❌ Composing `dest / user_supplied_path` without checking for an absolute path → ✅ `isabs` plus an <!-- docs-check: allow (Python stdlib function, not a repo-defined symbol) -->
`_is_inside(resolved, root)` check before anything is copied or written
Why: `Path("/a/b") / "/abs/c"` evaluates to `/abs/c` — the left operand is discarded silently. Found
in a tool whose entire purpose was to stop writing the real tree, after 67 of its own tests were
green. Relevant here because pause/resume is file-based IPC over caller-supplied paths.

❌ Running anything alongside a suite whose result you intend to cite → ✅ run it alone
Why: `cli/tests/unit/test_hybrid_integration.py::test_fill_simple_grid` asserts
`result.time_elapsed < 30.0` on wall clock. A second pytest run concurrently with a full suite took
628s against 302s idle; the test failed at 307s and the failure was read as a regression in new
code, then as a different regression. Both wrong — the suite is green run alone.

❌ Comparing a pytest-reported path against a path your own tool built → ✅ `realpath` both sides
Why: macOS resolves `/tmp` → `/private/tmp` and pytest reports the realpath, so
`reported.startswith(run_root)` is `False` while
`realpath(reported).startswith(realpath(run_root))` is `True`. Every run misfires, on a comparison
that looks obviously correct.

❌ Deleting an unreferenced override whose base declares it `@abstractmethod` → ✅ delete the
abstract declaration with it, or not at all
Why: leaving the abstract half makes the subclass uninstantiable at import. `7b0060c` had to remove
`DiversityStrategy.apply_diversity_bonus` together with `DiversityManager`'s implementation, or two
live `diverse_beam_prune` call sites in `orchestrator.py` would have broken. Zero callers on the
override says nothing about the base.

❌ Reading zero call sites on a decorator-registered route as "dead" → ✅ check
`docs/api/openapi.yaml`, the documented single source of truth for endpoints, before deleting
Why: a Flask route handler has no Python caller by construction, so a reference sweep returns the
same null for a live endpoint as for a dead one. The 2026-09-20 dead-code pass proposed deleting
three `wordlist_routes.py` handlers on that null; all three were in `openapi.yaml` and two are
documented in `API_REFERENCE.md` as an intentional pair, so the ruling shrank to one (`7af0ebf`,
whose body says why). The check that would replace this entry is an openapi↔route parity
predicate in `docs-check.sh` — not built; measure true/false over the tree first, per the guard
entry above.

❌ Reading a closed issue as evidence the work is done → ✅ check the items against the code
Why: #21 auto-closed on a rebase-merge via unreworded `Closes #21 item N` trailers while items 2b
and 3 were never implemented; `.handoff/post-m1-decisions.md`'s D12 had warned about exactly that
and the reword did not happen. Reopened 2026-09-13. Conversely #9-#17 and #22-#25 were all verified
genuinely resolved — the state field carries no information either way.

❌ Recording a decision only in auto-memory → ✅ the tracked repo holds the primary; memory is a
pointer to it, never the record itself
Why: `~/.claude/projects/*/memory/` is outside version control and invisible to `git grep`, the
gitignore-honouring recursive `grep`, `check-guards.sh` and `docs-check.sh` alike. Spec decision 6's
evidentiary clause was unintelligible without `project_applied_research_capability.md`, which lives
only there — **four independent readers each concluded the clause was false**, and every one of them
had checked correctly against an incomplete source set. Fixed by inlining the mechanism into the
spec row (`a6d8d85`), not by citing the memory file. Memory is a *delivery* tier, auto-loaded per
session; it is not a *durability* tier, and a decision whose only record is there is one disk loss
from gone. Q11 of the same audit asked whether those six memory decisions needed a register of
their own; resolved 2026-09-20 — they map onto spec decisions 1, 2, 3, 6, 7 and 8, so no separate
decisions directory was built. The spec's §1 table is the register.

❌ Citing `file:line` for a target that has a name → ✅ cite the identifier; reserve `file:line` for
targets with no enclosing symbol
Why: issue #21 cited `state_manager.py:403` for a function that is in fact `cleanup_old_states`;
`:403` is `list_states`' docstring. A line number is invalidated by any edit above it; an identifier
is invalidated only by a rename, which `grep` finds. This is a qualified rule, not "never cite a line
number" — that unqualified form is false and this file disproves it: most of its own line-number
citations point at targets with no enclosing symbol to name instead (a comment block, `.gitignore`
entries, a figure inside a comment, markdown prose), and one pair
(`backend/tests/unit/test_routes.py`'s two `TestFillWithProgress` classes) is load-bearing precisely
*because* the line number, not an identifier, is what distinguishes them.

❌ Leaving a fact with two homes, or designating a primary without re-deriving its values → ✅ one
primary per fact; treat designating one as a verification event
Why: `scripts/check-guards.sh` was designated Guard 3's primary while asserting that `7b0060c`
removed 18 names; it removed 17. A primary carrying a false value is worse than two copies, because
every other site now points at it. This file already uses the phrase "Primary record:" in three
entries above without ever stating the convention — this entry names it. The two homes can be one
file: the doc-truth plan carried "18" in its summary while its own Gate Findings said 17. Grep a
changed quantity across the whole file, not just the section you edited.

❌ Leaving a document that describes finished work on the live surface → ✅ move it under
`docs/archive/`
Why: `cd75876` archived eight completed plans and the dead-path citations fell without a word of
prose being edited. A stale plan is the document class that most reliably contradicts its own
outcome.

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
- An owner-decision row carries a default-if-unruled outcome and a review date. "Awaiting owner"
  with no expiry is a no-op: nine post-M1 rows sat that way from 2026-08-19 until the register's
  defaults were ratified on 2026-09-20 (review date 2026-10-20). That register is gitignored, so
  this line is the rule's tracked home.
