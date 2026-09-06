# Contributing

**Version 1.0.0** · 2026-08-15

---

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified.

---

## 1. Setup

**[SPEC]**
```bash
pip install -r requirements.txt
npm install
pre-commit install          # black, isort, ruff, flake8 run on commit
```

Run the app (two terminals):
```bash
python run.py               # Flask backend  -> :5000
npm run dev                 # Vite dev server -> :3000 (proxies /api to :5000)
```

---

## 2. Architecture rule

**[SPEC]**
- All crossword logic lives in `cli/`. The backend is a thin HTTP wrapper that shells out to it.
- A new capability is added to the CLI **first**, then exposed via `backend/core/cli_adapter.py`,
  then routed in `backend/api/`, then wired in `src/`.
- Do not implement crossword logic in `backend/` or `src/`. Two implementations will diverge.

**[SPEC] A staged-file-scoped guard has never seen your untouched files.**
`scripts/check-guards.sh` inspects staged files, so it passes vacuously on everything nobody has
edited. The API-confinement rule had never fired on `PatternMatcher.jsx` or `useSSEProgress.js`
because neither was ever modified on this branch; merging `main` staged them and a long-standing
violation surfaced at once. It then recurred — removing those two exclusions appeared to pass only
because neither file was staged.

**CI closes that blind spot at the tree level; the hook still does not.**
`./scripts/check-guards.sh --full-tree` enumerates every tracked file under `src/` and reads the
working tree, so an untouched violator fails the `guards` job even though no commit ever staged it.
The no-argument invocation the hook runs is unchanged and remains staged-scoped, so the rule below
still applies locally. Full-tree mode refuses two ways of passing without looking: an unrecognised
flag exits non-zero rather than falling through to staged mode (which, with nothing staged, would
exit 0 forever), and an enumeration that returns no files under `src/` is an error, not a pass. The
script also resolves paths from the repository root, because git pathspecs are relative to the
working directory — run from `backend/`, the scan used to find nothing and report success.

**Prove a guard change against a known violator, never by a clean run.** And note what that takes:
`git add` on an **unmodified** file stages nothing, because `git diff --cached --diff-filter=ACM`
reports no entry for a blob identical to `HEAD`. So deliberately `git add`-ing a known-bad file does
**not** arm the guard and proves nothing — a green result there is the vacuous pass again, one level
down. The file has to be genuinely modified before staging. Verified on issue #14's three files:
staged unmodified, `check-guards.sh` exits 0; append one newline to the same file and it exits 1.

---

## 3. Tests

**[SPEC]**
```bash
pytest                                   # default suite (slow tests deselected)
pytest -m slow                           # slow suite only
pytest --cov=backend --cov=cli           # with coverage
npx vitest run                           # frontend
npm run build                            # must stay clean
```

Markers registered in `pytest.ini`: `slow`, `integration`, `unit`.

**Read the `[BUG]` blocks below before diagnosing a test that fails only in CI.** Each was written
from an incident, and each has since recurred because someone reasoned from first principles
instead of reading them. The coverage block immediately below is the clearest case: it names the
misdiagnosis ("slow CI runners") that it cost three attempts to reach, and that same misdiagnosis
was made again afterwards, for two more.

**[BUG] Tests that spawn CLI subprocesses run far slower under coverage — and the tax is not
uniform across the phases a test budgets separately**
- Symptom: subprocess-spawning tests fail only in the `--cov` CI job, not locally. Only `test
  (3.12)` is given `--cov` (`.github/workflows/test.yml`), so a failure on exactly one matrix
  entry while the other three pass is this until proven otherwise.
- Cause: `pytest-cov` installs a `.pth` that runs `pytest_cov.embed.init()` in *every* Python
  subprocess when `COV_CORE_SOURCE` is set.
- **The tax differs by phase, which is what makes it bite twice.** Measured on the 5x5 fill in
  `cli/tests/integration/test_fill_pause_resume.py`: solver time `0.96s -> 4.35s` (~4.5x), wall
  `1.92s -> 34.16s` (~17x) — startup (wordlist load, trie build, CSP setup) carries most of it.
  A test bounds *wall* through `communicate(timeout=)` while `-t` bounds *solver*, so the two
  budgets fail independently: fixing the one the traceback names surfaces the other on the next
  CI run. Sweep every budget in the invocation at once.
- Fix: already applied globally — the session fixture in the root `conftest.py` clears
  `COV_CORE_*` before anything spawns, so new tests need nothing. It is done through the
  environment rather than `env=` per call site because product code spawns the CLI too
  (`backend/core/cli_adapter.py`, `backend/api/routes.py`). Cost, accepted deliberately: lines
  executed only inside a spawned CLI stop counting (integration step 38.43% -> 34.40%, a strict
  upper bound on the loss to the combined total), and the step runs 746s -> 74s.
- Do not diagnose this as "slow CI runners". That misdiagnosis cost three CI attempts, then two
  more after this block was written to prevent it.

**[BUG] `communicate(timeout=)` and a dedicated reader thread on the same pipe race**
- Symptom: stderr progress events go missing silently — no exception, no timeout, just fewer
  `send_progress` calls than the child actually emitted.
- Cause: `subprocess.communicate(timeout=)` drains stdout **and** stderr internally. Pairing it with
  a reader thread on the SAME pipe means the two readers compete for each line; whichever loses gets
  nothing, because a line landing in `communicate()`'s own buffer is never parsed or forwarded.
- Measured (`b5751e7`): a synthetic 20-line child lost 1 of 20 lines, in two of three runs, under
  the naive (thread-plus-`communicate()`) version.
- Fix: capture the stream into a local, then set `process.stderr = None` **before** starting the
  reader thread, so `communicate()` sees no stream to manage — exactly one reader on the pipe
  throughout. Live at `_pump_stderr` / `run_cli_with_progress` in `backend/api/routes.py`.
- Distinct from the pytest-cov block above, which also mentions `communicate(timeout=)`: that one
  bounds *wall* time while `-t` bounds *solver* time — a different budget, not this race.

**[SPEC] A `slow`-marked test runs automatically only if a job names its file.** `pytest.ini`
sets `addopts = -m "not slow"`, so every ordinary invocation deselects slow tests. One job
overrides this: `pause-resume-seam` in `.github/workflows/test.yml` runs `pytest -m slow` against
four explicitly listed seam files. **A slow test in any other file still runs nowhere** — it can
assert something false indefinitely and nothing will notice. One did:
`test_theme_priority.py::TestThemeEntriesCLICanary` claimed `--theme-entries` was broken, when
the flag worked and the test's own fixture was wrong. If you slow-mark a test, either add its file
to that job or you own running it.

**[SPEC] Path arguments override `testpaths`, silently.** CI does not invoke bare `pytest`; it
passes explicit directories (`pytest backend/tests/unit cli/tests/unit …`). Those arguments replace
`testpaths` from `pytest.ini` entirely, so a test file that sits outside the enumerated directories
is **never collected by CI** while a bare local `pytest` runs it happily. The real-subprocess pause
gate sat directly in `cli/tests/`, in neither `unit/` nor `integration/`, and was invisible to every
CI run until `15d0db5` — which is the arrangement the architecture rule in §2 warns produced a green
suite alongside broken pause/resume. A local pass is not evidence about CI. Prove collection:

```bash
pytest <the paths CI uses> --collect-only -q | grep -c <your_test_file>
```

Moving a test between directories also moves it relative to `Path(__file__).parents[N]`. Two
subprocess tests here resolve `REPO_ROOT` that way and pass it as `cwd`; the index has to move
with the file.

**[SPEC] `xfail(strict=True)` as a self-removing scaffold.** When a test must wait on an
incomplete contract, mark it `xfail(strict=True)` rather than skipping or deleting it. Once the
contract is fixed the test XPASSes, which *fails* the suite under `strict`, forcing someone to
remove the marker. A plain `xfail` lapses silently and the test never comes back.
For a known failure inside a **multi-assertion** test, prefer a conditional imperative
`pytest.xfail()` at the failing assertion over the decorator: it guards that one assertion, leaves
the rest of the test live, and self-clears when the contract is fixed. The decorator surrenders the
whole test.

**[SPEC] A green suite can hide a test that never executes.** `test_pause_edit_resume_workflow`
was stale four independent ways — request body shape, response key, status code (**no branch ever
returned 202**) and an async subscribe against a synchronous route — and had never actually run on
any branch, because every assertion sat nested under `if response.status_code == 200:`. It was then
patched assertion-by-assertion across four serial runs before anyone read the block against the
whole contract. Two rules follow: on a contract-mismatch failure read the **entire** block against
the **entire** contract before changing a line; and treat assertions nested under a status check as
unguarded until you have seen them fail.

That rule's own example outlived it. The block was corrected, but the `if response.status_code
== 200:` wrapper around it was left in place, so the test could still pass while asserting nothing —
it was only closed in `b679212`. Before changing it, the vacuity was demonstrated: pointing the
state fetch at a bogus task id left the test **passing**; after the fix the same manipulation fails
with `assert 404 == 200`. Fixing the body of a vacuous test does not make it non-vacuous.

**[SPEC] Comparing two unseeded stochastic solvers with `>=` is a coin flip, not a contract.**
`test_hybrid_vs_beam_alone` compared two independent unseeded runs — the repair and value-ordering
paths draw randomness at `iterative_repair.py:398/647/906` and `value_ordering.py:233/448` — and
failed intermittently under repetition. Seed both runs from one value so the shared phase
reproduces, then assert the property the code actually guarantees: hybrid returns the best of its
own beam and repair passes (`hybrid_autofill.py:200-215`). Fixed in `06f8036`.

**[BUG] A percentage margin on a deterministic delay flakes under load — bound with a fixed ceiling**
- Symptom: a timing assertion written as a multiple of the test's own sleep interval (e.g.
  `elapsed < 1.5 * sleep_interval`) fails intermittently in CI, despite the buggy and fixed
  behaviors differing by orders of magnitude.
- Cause: a percentage margin is only as stable as the wall-clock value it's a percentage of;
  scheduling jitter on a loaded runner can push a near-instant path past a sub-second relative bound.
- Fix: use a fixed ceiling (e.g. `assert elapsed < 3.0`) sized well below the buggy behavior's
  magnitude — never a multiple of the deterministic delay.
- This is already a code comment at `cli/tests/unit/test_beam_search.py:344-345` ("fixed ceiling,
  not % — % margins are fragile on loaded CI runners") — and it recurred anyway, in the same file: a
  draft test using `1.5 * sleep_interval` flaked under concurrent load despite a roughly 300x
  RED/GREEN gap (`2e5e1e0`, ~16s vs ~0.05s). That recurrence is why the lesson is repeated here.

**[SPEC] `Grid.set_black_square` enforces 180° symmetry by default.** A fixture blacking `(10,10)`
silently blacks `(0,0)` as well, so the slot layout under test is not the one you wrote. Pass
`enforce_symmetry=False` when constructing a specific layout. This cost two wrong test
constructions before it was spotted.

**[BUG] CI wall-time is not a property of your code**
- Symptom: a test's duration jumps enormously between CI jobs and the change looks like the cause.
- Cause: fixed startup work (interpreter, wordlist load, trie build, state inflate) varies by
  runner and interpreter. The same commit, same runner class, same subprocess measured **8.1s on
  Python 3.11 and ~92s on Python 3.12** (run `32003100530`).
- **Check `--cov` before blaming the interpreter.** 3.12 is the only job given coverage, so a
  3.11-vs-3.12 gap of this shape is more likely the block above than an interpreter difference —
  an ~17x wall tax on a spawned child reproduces this ratio on one machine with one interpreter,
  varying only `--cov`. Reasoned, not measured: run `32003100530` was not re-examined.
- Fix: read the whole matrix before concluding a change made something slow.
- This is the mirror of the coverage bug above: that one says do not blame the runners, this one
  says do not blame the code.

**[SPEC] Assert the effect, not the existence.** A test that confirms a mechanism is *present*
without measuring what it *does* is worse than no test: it reports green while the mechanism is
dead, and its passing status argues against anyone looking. `should_pause()` had a documented
rate limit guarded only by `isinstance(result, bool)`; the limit gated nothing and the cache
fields were unused until `876a54c`. The replacement in `cli/tests/unit/test_state_manager.py`
counts the filesystem calls the rate limit exists to remove — run it to see the figures. Where a
mechanism claims to reduce, cache, batch or throttle something, the test must count that thing.

**[SPEC] Ask what makes a test red *today*, before writing it.** Three acceptance tests on this
branch could never have failed. "No module imports `BlackSquareSuggestions`" — nothing importing it
was precisely why it was dead code. An equivalence gate asking whether `enumerate_white_runs()` and
`get_word_slots(min_length=1)` agree — `get_word_slots()` calls `enumerate_white_runs()` internally,
so they were structurally guaranteed to agree. And a non-aliasing assertion against an object with
no public handle. Check the call graph before designing an equivalence gate, and rewrite the
assertion rather than discovering the problem when the implementer flounders.

**[SPEC] A test that reaches its assertion only because of the bug must be re-synchronised, and
its diff read specifically for weakening.** When a fix changes behaviour a test's *setup* depended
on, the test can start failing for reasons that have nothing to do with what it asserts — and the
tempting repair is the one that quietly stops gating.
`test_repair_pause_before_restart_exits_cleanly` pre-touched the pause flag before `Popen`, which
only worked while `clear_pause()` targeted the wrong directory; once that was fixed the setup was
racing the process it meant to precede. Re-synchronise against the new behaviour (wait for the
marker the process actually writes), then read the resulting diff asking what it no longer proves.

**[SPEC] Prove a RED against pre-fix source, and record the *received* value.** A pasted failure
does not distinguish "the assertion fired and got the wrong value" from "the setup never reached the
assertion" — and the second is worthless. Check the source files out at BASE while keeping the new
tests, and re-run:

```bash
git checkout <base-sha> -- <the source files under test>   # keep the new tests
pytest <the new tests>                                     # expect RED
git checkout HEAD -- <the source files under test>         # restore, then re-run green
```

Evidence must carry the received value (`expected 'HTTP_500' to be ''`, `Number of calls: 1`), not
just "it failed".

**[SPEC] Sweep the channel a change *widens*, not only the one it narrows.** A fix that empties
`ApiError.message` was swept thoroughly for `.message` consumers — but it also broadened `.details`,
where a pre-existing consumer could silently start receiving a value it used to get `undefined` for.
That direction was unchecked until review asked. Two grep rules follow: a pattern that names its
variables (`\b(err|error|e)\.message\b`) misses `result.message` and is defeated entirely by
`err?.message`, so confirm with a bare `\.message\b` sweep plus an explicit optional-chaining
sweep; and sweep both channels, not just the obvious one.

**[SPEC] Every static gate passes on unreachable code.** `BlackSquareSuggestions` cleared the
scrub sweep, the API-URL guard, vitest and the build while being tree-shaken out of the bundle
entirely (#16). A stylesheet orphaned by the same deletion is still passing every gate today (#23).
Static gates prove a file is *conformant*; they never prove it is *reached*.

**[SPEC] `$?` after a pipe is the pipe's exit status.** Verifying a gate through a pager —
`./scripts/check-guards.sh --full-tree | tail -6; echo "exit=$?"` — reports `tail`'s status, which
is always 0. A gate script "verified" that way has not been consulted at all. Capture the status on
the bare command (`cmd > out 2>&1; rc=$?`), and confirm the guard can still fail: append a violating
line to a tracked file in scope, see it exit 1, restore.

**[SPEC] jsdom does not evaluate stylesheet rules.** `toHaveStyle` reads the inline value on the
JSX element, so a design-token assertion passes even after the underlying CSS rule is reverted —
the test is green and the colour is wrong. Token correctness of *CSS rules* can only be checked in
a real browser; from a unit test, the closest honest check is `getComputedStyle` against an
injected probe element. Treat any stylesheet-level claim as unguarded until a browser gate runs.

**[SPEC] `setupTests.js` stubs `localStorage` with no-op mocks.** `src/__tests__/setupTests.js`
assigns `global.localStorage` a set of bare `vi.fn()`s, so `getItem` returns `undefined` forever.
A test that writes a value and reads it back passes trivially against a dead stub without ever
exercising persistence. Back the stub with a `Map` in any test where storage behaviour is the
thing under test.

---

## 4. Documentation rules

**[SPEC]**
- **No derivable state in prose.** If a command produces the number, print the command, not the
  number. Banned in living docs: test counts, pass rates, coverage %, wordlist sizes, `Status:
  Complete`, `✅ FIXED`. CI enforces this. <!-- docs-check: allow -->
- Living docs in `docs/` follow HADS (`[SPEC]` / `[NOTE]` / `[BUG]` / `[?]` blocks + AI manifest).
- `.claude/CLAUDE.md` follows the claude-meta template instead, and stays under 80 lines.
- Unverified claims go in a `[?]` block. Never assert them as fact.
- Timing or size figures in **code comments** need the command that reproduces them, or state
  complexity instead. See `docs/dev/FABRICATION-LOG.md` for why this rule exists.
- Dated historical records are archival. Do not "correct" them — archive them.
- **A commit sha cited in a doc is a pointer, and history rewrites break it.** Stripping trailers
  from this branch rewrote every sha on it, orphaning citations in three plan docs and in this file.
  Distinguish this from the rule above: a *dated claim* is archival and must not be corrected, but a
  *dangling pointer* names nothing and should be repointed. Repoint only unambiguous rewrite twins —
  same subject, same diff modulo the trailer, and the target verified with `git merge-base
  --is-ancestor <sha> HEAD`. Leave alone: shas whose only on-branch container is a squash superset
  rather than a 1:1 twin, shas cited *because* they are orphaned (see §5's merge-commit rule), and
  everything under `docs/archive/`, which `docs-check.sh` excludes as historical record. Report the
  ambiguous ones rather than guessing.
- **Archiving a doc needs `git add -f`.** `.gitignore` carries a bare `archive/` pattern, so
  `docs/archive/` content is tracked only by grandfathering. A new file moved there is ignored,
  and the move lands as a plain deletion — the archive silently becomes a delete.
- **`.gitignore` unanchored directory patterns match at every depth.** `.gitignore:13` is a bare
  `lib/`, meant for Python build output, and it also swallows `src/lib/`. Nothing under such a
  path can be committed until a negation (`!src/lib/`) is added. There is no `src/lib/` on this
  branch, so the trap is latent — it fires the moment frontend work introduces one.

---

## 5. Commits and branches

**[SPEC]**
- Branch: `type/short-description`.
- Commit: `type(scope): imperative description` — e.g. `fix(ci): widen CLI subprocess timeout`.
- Types in use: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- Before pushing: `pytest`, `npm run build`, and let pre-commit run (do not `--no-verify`).
- **Merge with a merge commit when anything outside the repo cites individual commits.** A squash
  replaces every commit on the branch with one new hash, so references to the originals stop
  resolving against `main`. PR #5 merged as `f727f1a` (two parents) and its commits are still
  reachable; PR #7 squashed to `c756a99` (one parent), so `4994e3d`, `8bbff08`, `901fa60` and
  `876a54c` are not in `main` and resolve only through `refs/pull/7/head`, which GitHub retains.
  Check with `git merge-base --is-ancestor <sha> main`. Squashing is fine for branches nothing
  external points at.

**[SPEC] Resolving a large merge — four rules earned on the bench↔main sync.**

- **Conflict markers show where git could not decide, not where the contract broke.** The two worst
  defects of that merge were in files that auto-merged with **no conflict**: `validator.py` (each
  branch's call site needed a different `grid.py`, and neither side satisfied both) and
  `state_manager.py` (one branch's `slots_sorted: List[Dict]` annotation sitting over the other's
  serializer writing `List[int]`, which broke exact-position resume silently). After any large
  merge, diff every **auto-merged** file in the affected subsystem against **both** parent versions
  and look for one side's contract paired with the other's implementation.
- **A deleted delegation drops everything the delegate did — enumerate it, do not infer it.** The
  resolution plan named three obligations for removing `_execute_resume`; it actually dropped six.
  The three unlisted ones each surfaced later as a separate test failure, one at a time.
- **A green suite is not evidence a merged feature works.** The solver suite passed in full over a
  resume path that was broken, because no test round-trips `capture_csp_state` → `_resume_fill`.
  Prove a merged contract by executing both call sites directly; reserve the suite for regressions.
- **A branch's regression tests are the merge's acceptance criteria.** Where each fix carries a
  named guard test, take the conflicted file wholesale from one side and let the resulting failures
  dictate the re-apply worklist. That turns conflict resolution from judgement into a checklist.

---

## 6. Changelog

- 1.2.0 (2026-08-17) — §2 records that CI now runs the guard over the whole tree, and what
  full-tree mode refuses to treat as a pass.
- 1.1.0 (2026-08-17) — distilled the bench↔main merge session. §2 gains the staged-file guard rule,
  §3 four test rules plus an extension to the `xfail` block, §5 the large-merge resolution block.
- 1.0.0 (2026-08-15) — written during the docs overhaul. Replaces an 18-line stub that had been
  archived unwritten ("Content will be populated shortly").
