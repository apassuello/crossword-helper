# Clue Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clues can be written in a Clues panel. They are stored in the document by entry start cell and
direction, and tracked as ok, stale or orphaned. They are saved, undone and carried through the grid JSON file
and every CLI write path.

**Architecture:** CLI-first (spec Decision 6). `cli/src/core/clues.py` owns validation and the authoritative
status. `crossword clues check` exposes them. `CLIAdapter.clues_check` and `POST /api/clues/check` wrap the
command. React holds `clues` in the live document beside `grid`. It computes a display status by the same rule
and reconciles that status from the route.

**Tech Stack:** Python 3.9+ · Click · Flask 3.0 · React 18 · Vite 5 · pytest · vitest

**Spec:** `docs/superpowers/specs/2026-10-31-clue-authoring-design.md`, version 0.1.4. The spec governs, and
every task reads the sections it names. Where this plan and the spec disagree, one of them is wrong: stop and
report it.

## Global Constraints

- Code that implements a §1 decision cites it as `Decision N (clue-authoring spec 0.1.4, section 1)`.
- Layering (spec §2): crossword logic only in `cli/`. The order is CLI → `cli_adapter.py` → Flask route →
  React, and no layer is skipped. The browser status is for display only (R4).
- Python 3.9 floor. Module-level type aliases use `typing.Union`, not `|` (`.claude/CLAUDE.md`).
- Every code task runs RED → GREEN → REVIEW with three different agents (Execution protocol below). All run on
  **Sonnet**. RED evidence before any `src` edit is mandatory in every task report: the
  failing output, with a per-row failed/passed-before table. A row that passes before the fix needs a
  discriminating fixture and a mutation proof that fails at the target assertion's own line (CONTRIBUTING §3).
- Every mutation row in spec §6.3 is assigned to exactly one task below. That task's report shows the
  mutation, the failure at the assertion's own line, and the revert.
- Implementers own sub-visible mechanics: helper names inside one task, request timeouts, how the CLI passes
  `clues` to the engines, CSS details within the existing `.xw-clue*` classes. Any user-visible choice the spec
  does not settle is escalated. It is not decided in the task.
- Tests: run the touched modules' tests per task (`pytest <paths>`, `npx vitest run <paths>`). Do not run the
  full or slow suite locally, and run nothing alongside a suite whose result you cite. `npm run build` must stay
  clean for every frontend task.
- Commits: `type(scope): imperative description`. Pre-commit runs, and `--no-verify` is never used. No AI
  attribution trailers. Never chain a test run and a commit in one shell command.
- Spec §7's document amendments are applied in Task 11, not before.

## Verified facts this plan relies on (checked 2026-10-31 at `17f058f`)

- `_load_grid_or_exit(grid_file, allow_nonstandard, json_output)` returns `(data, grid)`. `data` is the raw
  JSON dict, so `clues` is read from `data`. `Grid.to_dict()` knows nothing of `clues`, so every write that
  should keep them adds the key to the dict it dumps (`cli/src/cli.py`).
- `fill` writes its result with `json.dump(result.grid.to_dict(), …)` to `output if json_output else (output or
  grid_file)`. Its pause write uses the same rule (`paused_output_file`).
- `fill --resume` does **not** call `_execute_resume`. It resolves the state in `fill`'s `resume_state_file`
  branch and reads the state's metadata there (`resume_metadata`). Spec 0.1.3 §3.5.
- `validate_grid_request` returns the same dict it was given, so `clues` passes through to the adapter
  (`backend/api/validators.py`).
- `CLIAdapter.number` raises `ValueError` on non-JSON output, and `/api/number` maps `ValueError` to 400
  `INVALID_GRID`. **Do not copy that path.** Spec §3.6 maps non-JSON output to 500 `INTERNAL_ERROR`, and
  `json.JSONDecodeError` is a `ValueError` subclass.
- `clean()` in `src/api/client.js` drops only `undefined`, so `clues: {}` and `clues: null` are sent.
- Neither language's built-in trim matches spec §3.1's whitespace set. JS `String.prototype.trim` strips
  U+FEFF (not in the set) and keeps U+0085 (in the set). Python `str.strip()` strips U+001C–U+001F (not in the
  set). Both sides use the explicit set from §3.1.
- `cli/src/cli.py` has no nested click group yet. `clues` is the first (`@cli.group()` + `@clues.command("check")`).

## Execution protocol: RED → GREEN → REVIEW, three agents per task

Owner ruling, 2026-10-31: every code task runs as three phases, each done by a **different** fresh agent. The
controller writes a task's three briefs **together, before RED starts**, and **from the spec and the task's
contract**. GREEN is never briefed from RED's tests, so the tests are its acceptance check, not its
specification. Briefs are written one task at a time and never for a later task. The files are
`task-N-red.md`, `task-N-green.md` and `task-N-review.md` in the SDD workspace. Each brief points at
`task-N-contract.md` (the task's text from this plan), at `global-constraints.md` (this plan's Global
Constraints, Verified facts and this protocol), and at the spec sections the task implements. Run-specific
facts (the RED and GREEN commits, the review package path) go in the dispatch message, not in a brief.

1. **RED** (Sonnet, a test writer). It writes tests and test fixtures only, designed from the task's contract
   (signatures, criteria, normative cases), and reads `superpowers:test-driven-development` and its
   `writing-good-tests.md` first. It edits no production file. It runs the tests and records the failure of
   each one. Expected failures:
   - A symbol or module that does not exist yet fails on import or attribute lookup.
   - Behaviour on existing code fails on an assertion.
   - A broken test (syntax, a wrong fixture path) is not a RED.

   The report carries a table: normative case → test → failing line and message. A test that **passes** at
   RED is listed as such with the reason and a **proposed mutation** (the production line and the defect
   that would make it fail), and REVIEW runs that mutation. RED commits
   `test(<scope>): failing tests for Task N`. Failing tests committed on this branch are intended, and nothing
   is pushed between phases.
2. **GREEN** (Sonnet, an implementer, not the RED agent). It works from the spec and the contract, with RED's
   tests as the acceptance check. It writes the production code (and the task's docstring, comment and doc
   edits) until RED's tests pass. It **must not change any file RED committed**;
   `git diff <RED>..HEAD -- <RED's files>` must be empty. If a RED test is defective (a path, an import, or a
   test that contradicts the contract), it stops at once with BLOCKED. It quotes the test and the contract
   text and proposes the one-line fix. The controller then routes it to a RED
   fix or to Spec Drift; GREEN never edits the test. It runs the task's tests, plus `npm run build` for a
   frontend task, and commits with the task's commit subject.
3. **REVIEW** (Sonnet, a reviewer, not RED or GREEN). It reads the review package (RED's base to GREEN's head)
   and gives two verdicts.
   - **Spec compliance:** every criterion and normative case is covered by a test and met by the code.
   - **Quality:** test honesty and code quality.

   It also checks that RED's failures were real failures for the right reason (from the RED report and the
   RED commit), and that GREEN changed no RED file. It runs this task's spec §6.3 mutations and the mutation
   proofs for RED-passing tests. For each: edit the production file, run, show the failure at the target
   assertion's own line, `git restore <file>`, then `git status --short` clean. Its report records each
   mutation's exact diff, so the controller can confirm it hit the named defect and not a neighbouring guard
   (CONTRIBUTING §3). It never runs `git checkout` or `git stash`.

   It also runs **at least three free mutants**: defects of its own choosing on lines the task's diff changed,
   which the named mutations do not cover, each run against the task's whole test set. A killed mutant names
   the test and line that failed. A survivor is either a missing test (a quality finding) or an equivalent
   mutant, with the reason it makes no observable difference. Owner proposal, adopted 2026-10-31. The
   controller's comparison, not weighed by the owner: it replaces an optional extra mutant, which Task 2's
   REVIEW did not run. A `mutmut` run per task was not tried.
4. **Findings.** A test gap goes to a fresh RED fix agent: new tests fail first, or carry a mutation proof. A
   code defect goes to a fresh GREEN fix agent. Then a fresh REVIEW agent re-reviews. A behaviour change goes
   through Spec Drift (amend the spec and plan, and get the owner's ruling), never inside a fix.
   Exception (owner ruling, 2026-11-01): a tests-only fix, with `git diff <last reviewed head>..HEAD -- <the
   task's production paths>` empty, after at least two full REVIEWs with free mutants, closes on a controller
   check that reproduces each of its kills at the target line. It beat a third full REVIEW (Task 3 fix 3,
   `5bf3346`); the whole-branch review before merge remains the second gate.

Task 11 (documentation) has no tests. It runs as WRITE then REVIEW (two agents), with
`scripts/docs-check.sh` as its gate. Task 12 is the browser acceptance gate.

## File map

| File | Task | Role |
|---|---|---|
| `cli/src/core/clues.py` (new) | 1 | validator, key order, status, carry helper |
| `tests/fixtures/clue_status_cases.json` (new) | 1 | §3.2 rows, read by pytest and vitest |
| `cli/src/core/grid.py` | 1 | `get_word_slots` docstring fix (spec §8) |
| `cli/src/cli.py` | 2, 3 | `clues check` command; `clues` carry in `fill`, `fill --resume`, `_execute_resume` |
| `cli/src/fill/autofill.py`, `cli/src/fill/beam_search/orchestrator.py` | 3 | `metadata["clues"]` at the pause save sites |
| `backend/core/cli_adapter.py` | 4 | `clues_check` |
| `backend/api/clue_routes.py` (new), `backend/app.py` | 4 | `POST /api/clues/check` |
| `docs/api/openapi.yaml`, `docs/api/API_REFERENCE.md` | 4 | the route |
| `src/lib/clues.js` (new) | 5 | keys, browser status, commit/keep/delete |
| `src/lib/contentSig.js`, `src/lib/history.js`, `src/lib/gridEdits.js`, `src/App.jsx` (`isAdoptableEntry`) | 6 | signatures, snapshots, replacement predicate |
| `src/components/CluesPanel.jsx` (new) | 7 | the panel |
| `src/App.jsx`, `src/hooks/useUndoHistory.js`, `src/hooks/useSaveMachine.js`, `src/components/bench/ToolRail.jsx`, `src/components/bench/GridPanel.jsx` | 8 | state, undo, save, lifecycle, confirm, gating, rail |
| `src/components/ImportPanel.jsx`, `src/components/ExportPanel.jsx`, `src/api/client.js` | 9 | grid-file clues |
| `src/hooks/useClueReconcile.js` (new) | 10 | reconciliation |

---

### Task 1: CLI clue module and shared fixture

**Files:** Create `cli/src/core/clues.py`, `tests/fixtures/clue_status_cases.json`. Modify the
`get_word_slots` docstring in `cli/src/core/grid.py`. Test `cli/tests/unit/test_clues.py`.

**Interfaces — Produces:**

```python
class CluesError(ValueError): ...            # str(e) is the exact §3.4 message
def validate_clues(clues: object, size: int) -> None: ...   # raises CluesError
def clue_key_sort(key: str) -> Tuple[int, int, int]: ...      # (row, col, 0 for across / 1 for down)
def clue_statuses(grid: Grid, clues: Dict[str, Dict[str, str]]) -> Dict[str, str]: ...  # validated input
def carry_clues(source: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]: ...
```

`carry_clues` sets `target["clues"] = source["clues"]` when `source` has the key (any value, `{}` included),
leaves `target` without the key otherwise, and returns `target`. Task 3 uses it at every write site, with the
input data dict or the state metadata as `source`.

**Fixture schema** (spec §3.2; pytest and vitest both read it):

```json
{"cases": [{"grid": [["R","O","S","E"], [".",".",".","."], [".",".",".","."], [".",".",".","."]],
            "key": "0,0,across", "answer": "ROSE", "status": "ok"}]}
```

It holds the seven §3.2 rows for `across` and the same seven transposed with key `"0,0,down"`: 14 cases,
written out literally. `#` is black and `.` is empty. Rows are lists of one-character strings, the grid
file's own row shape (`Grid.to_dict` builds each row cell by cell, and `Grid.from_dict` rejects a non-list row,
`cli/src/core/grid.py:372-373`). Neither consumer converts: pytest loads a case with
`Grid.from_dict({"size": 4, "grid": rows}, strict_size=False)` (4×4 is non-standard), and vitest passes the rows
straight to `fromCliStrings` (`src/api/gridCodec.js`, which maps `#`, `.` and letters per cell).

**Behavioural criteria:** spec §3.4 rules 1–6 in their stated order. Rule 2 is checked over all keys in
code-point string order before any value is checked. Rules 3–6 run key by key in key order (§3.1). Messages
are exact (§3.4). Rule 4 uses §3.1's whitespace set and rule 5 counts code points. Status follows §3.2, with
entries from `grid.get_word_slots(min_length=2)` and each `.` of `pattern` read as `?`. Orphan keys are valid.
The `get_word_slots` docstring example is corrected to show `.` for an empty square, and a direct test pins
that form: `get_word_slots(min_length=2)` on a grid with an empty square returns `.` at that position of
`pattern` (spec §8; the `RO.E` fixture row covers it only indirectly).

**Normative cases:** spec §3.4's messages; spec §6.1 "Validation" (every listed case: `null`, an array,
`"00,0,across"`, code-point order of key errors, key order of value errors, leading U+00A0, 200 vs 201 code
points with an emoji counted as one, an orphan key valid); plus a leading U+0085 rejected and a leading U+001C
accepted (the trim trap above). Status: all 14 fixture rows.

**Mutation (§6.3):** "The CLI status uses `get_word_slots()` at its default" → the 2-letter `RO` row is `ok`.

- [ ] RED: tests and fixtures only; run `pytest cli/tests/unit/test_clues.py -v`; commit `test(cli): failing tests for Task 1`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(cli): clue map validation and status`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 2: `crossword clues check`

**Files:** Modify `cli/src/cli.py` (new `clues` group and `check` command). Test
`cli/tests/unit/test_clues_command.py`.

**Interfaces — Consumes:** Task 1's `validate_clues`, `clue_statuses`, `CluesError`. **Produces:** the
two-token command `clues check <grid.json> [--allow-nonstandard] --json-output` (spec §3.6), which Task 4's adapter
invokes.

**Behavioural criteria** (spec §3.6): load through `_load_grid_or_exit` (an unloadable grid gives that
helper's existing JSON error and exit 1, with no `code`). A file with no `clues` key gives
`{"success": true, "statuses": {}}`. A present `clues` key (including `null`) is validated against
`grid.size`. With `--json-output`:

| Input | Exit | stdout |
|---|---|---|
| valid clues | 0 | `{"success": true, "statuses": {"<key>": "ok"\|"stale"\|"orphaned", …}}`, one per clue |
| §3.4 failure | 1 | `{"success": false, "code": "INVALID_CLUES", "error": "<§3.4 message>"}` |
| unloadable grid | 1 | `{"success": false, "error": …}` (no `code`) |
| no `clues` key | 0 | `{"success": true, "statuses": {}}` |

Human mode (no `--json-output`) keeps the same exit codes. Spec §3.6 gives `--json-output` unbracketed and
does not define human-mode text. **Owner ruling (2026-10-31, spec §10):** the same JSON object is printed with
or without the flag, so there is one format and nothing new for CLI_SPEC. Under this ruling, `_load_grid_or_exit` is called with `json_output=True` in both modes, so the
unloadable-grid error is JSON too (with `False` it prints human text, `cli/src/cli.py`, the helper's `else`
branch). Task 11 documents whichever applies.

- [ ] RED: tests and fixtures only; run `pytest cli/tests/unit/test_clues_command.py -v`; tests go through `click.testing.CliRunner` on files in `tmp_path` and cover every row and a 4×4 grid with `--allow-nonstandard`; commit `test(cli): failing tests for Task 2`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(cli): clues check command`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 3: Carry `clues` through every CLI grid write

**Files:** Modify `cli/src/cli.py` (`fill`'s pause write and result write, its `resume_state_file` branch,
the state for other algorithms, `_execute_resume`'s output write, and the comment ending "metadata is therefore
intentionally unused on load", which spec §7 rewrites), `cli/src/fill/autofill.py` (the CSP pause
`metadata = {…}`), and `cli/src/fill/beam_search/orchestrator.py` (the beam pause `metadata = {…}`). Test
`cli/tests/unit/test_clues_carry.py` and `cli/tests/integration/test_clues_pause_resume.py`.

**Interfaces — Consumes:** `carry_clues` (Task 1).

**Behavioural criteria** (spec 0.1.4 §3.5):
- `fill` carries the input file's `clues` unchanged into its pause write and its result write. In human mode
  with no `-o` it writes back to the input, so the clues stay in place. With `--json-output` it writes a file
  only when `-o` is given.
- Every pause state saved on the `fill` path stores the carried value as `metadata["clues"]`. That covers the
  CSP engine, the beam orchestrator, and the CLI's state for other algorithms. The solver never reads it.
- `resume` (`_execute_resume`) and `fill --resume` read `metadata["clues"]` and write it into their output and
  into any pause state they save. With `--resume`, a grid file's `clues` are not read.
- No `clues` in the input (or in the state's metadata) means none in the output. `new` and `import-nyt` write
  none.

**Pause trigger for the e2e tests:** use the mechanism the existing suites use.
`cli.src.fill.pause_controller.PauseController(task_id).request_pause()` is used from a thread in
`backend/tests/integration/test_e2e_pause_resume.py` (`test_full_pause_resume_workflow`), and the `pause` CLI
command in `cli/tests/unit/test_pause_resume_regressions.py`. **Grid choice is load-bearing.** A beam
iteration on a blank 15×15 can outlast the whole run (`.claude/CLAUDE.md`, the liveness anti-pattern). Use a
small grid that pauses within seconds, and mark a test `@pytest.mark.slow` if it takes longer than about 10 s.

**First step, before writing the beam row (spec 0.1.4 §6.1):** for any algorithm other than `regex` and `trie`,
`fill` makes its own degenerate CSP-type save after the run. That save and `save_beam_search_state` both name
`{task_id}.json.gz` (`cli/src/fill/state_manager.py`). Run a real `fill --algorithm beam` pause and report
which state type survives and in which directory. If no beam-type state survives the CLI path, the beam row
builds one with `save_beam_search_state` (carrying `metadata["clues"]`), on the pattern of the `stored_state`
fixture in `cli/tests/unit/test_pause_resume_regressions.py`. In that case the orchestrator's save site is
tested at unit level. Every e2e asserts on the state file's `metadata["clues"]` as well as on the resumed grid
file.

**Normative cases** (spec §6.1 "Round trip" and the third "Seam" bullet):

| Case | Expect |
|---|---|
| `fill grid.json` (human, no `-o`) with `clues` | the file still has the same `clues` |
| `fill grid.json -o out.json` | `out.json` has the input's `clues` |
| input without `clues` | output without a `clues` key |
| `new`, `import-nyt` | no `clues` key |
| real fill → pause → `resume`, for CSP, other-algorithm and beam-type states | resumed file has the input's `clues` |
| the same through `fill --resume`, for CSP and other-algorithm states only (it loads with `load_csp_state`, which refuses a beam state) | the same |
| `fill --resume` given a grid file whose `clues` differ from the state's | output has the state's `clues` |

**Mutation (§6.3):** "`fill`'s result write drops `clues`" → `fill grid.json` keeps `clues` in place.

- [ ] RED: tests and fixtures only; run `pytest cli/tests/unit/test_clues_carry.py cli/tests/integration/test_clues_pause_resume.py -v`; the beam-state first step above belongs to RED; commit `test(cli): failing tests for Task 3`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(cli): carry clues through fill, pause and resume`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 4: Adapter, route and API docs

**Files:** Modify `backend/core/cli_adapter.py`. Create `backend/api/clue_routes.py`. Modify `backend/app.py`
(register `clue_api` with `url_prefix="/api"`), `docs/api/openapi.yaml`, `docs/api/API_REFERENCE.md`. Test
`backend/tests/unit/test_clue_routes.py`, `backend/tests/unit/test_cli_adapter.py` (argv contract) and
`backend/tests/integration/test_clues_check_e2e.py`.

**Interfaces — Consumes:** the Task 2 command. **Produces:**

```python
def clues_check(self, grid_data: Dict[str, Any], allow_nonstandard: bool = False) -> Dict[str, Any]: ...
clue_api = Blueprint("clue", __name__)   # route: POST /clues/check
```

**Behavioural criteria** (spec §3.6):
- Adapter: writes `grid_data` to a temporary file as `number` does, runs
  `["clues", "check", <path>, "--json-output"]` plus `--allow-nonstandard` when asked, with
  `check_success=False`, and returns the parsed JSON for exit 0 and exit 1 alike. Non-JSON stdout raises an
  exception that is **not** a `ValueError`, so the route's `ValueError → 400` branch cannot catch it.
  `subprocess.TimeoutExpired` propagates. The temp file is always removed.
- Route: the same content-type, JSON and empty-body checks as `/api/number`, then `validate_grid_request`.
  `clues` is not inspected. `allow_nonstandard = size not in [11, 15, 21]`.

| Condition | Reply (`handle_error` shape for errors) |
|---|---|
| CLI `success: true` | 200, the CLI's JSON |
| CLI `code: "INVALID_CLUES"` | 400, `INVALID_CLUES`, the CLI's `error` |
| any other CLI `success: false` | 400, `INVALID_GRID`, the CLI's `error` |
| `validate_grid_request` raises | 400, `INVALID_GRID` |
| non-JSON CLI output | 500, `INTERNAL_ERROR`, fixed message `Clue check returned unreadable output` (no CLI stdout in the reply; `backend/tests/unit/test_error_hygiene.py` polices leaks) |
| timeout | 504, `TIMEOUT`, `Clue check timed out` |

Tests (spec §6.1 "Seam" and "Route shapes"): an argv contract test that the real CLI parser accepts the
adapter's arguments (`--help` acceptance is not enough; parse the actual argv). One real-subprocess e2e from
the Flask test client through the adapter to the CLI, covering 200, 400 `INVALID_CLUES` and 400
`INVALID_GRID`. Non-JSON and timeout with the adapter mocked. `backend/tests/test_openapi_contract.py` must
pass with the new path.

- [ ] RED: tests and fixtures only; run `pytest backend/tests/unit/test_clue_routes.py backend/tests/unit/test_cli_adapter.py backend/tests/integration/test_clues_check_e2e.py -v`; commit `test(api): failing tests for Task 4`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(api): POST /api/clues/check`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 5: Browser clue library

**Files:** Create `src/lib/clues.js`. Test `src/lib/__tests__/clues.test.js`.

**Interfaces — Produces:**

```js
export const CLUE_MAX_LENGTH = 200;
export const CLUE_TOO_LONG = 'At most 200 characters.';
export function clueKey(row, col, dir) {}            // "<row>,<col>,<dir>"
export function parseClueKey(key) {}                 // {row, col, dir}
export function compareClueKeys(a, b) {}             // key order, spec §3.1
export function trimClueText(s) {}                   // §3.1 whitespace set, not String.prototype.trim
export function clueStatus(grid, key, clue) {}       // 'ok' | 'stale' | 'orphaned'
export function clueStatuses(grid, clues) {}         // {[key]: status}
export function applyCommit(clues, key, draft, currentPattern) {} // {clues, changed, error}
export function applyKeep(clues, key, currentPattern) {}          // new map
export function applyDelete(clues, key) {}                        // new map
```

**Behavioural criteria:** status per spec §3.2, with entries from `allSlots(grid)` (a key's entry is the slot
in its `dir` whose `cells[0]` is `[row, col]`) and the pattern from that slot. Commit follows spec §3.3 in its
stated order. Unchanged text or an empty draft with no clue gives `changed: false` and the same map object.
Over 200 code points gives `error: CLUE_TOO_LONG` and the map unchanged. Otherwise `{text: trimmed, answer:
currentPattern}`. All three functions are immutable: they return a new map when something changes and never
mutate the input.

**Normative cases:** the 14 fixture rows, read from `tests/fixtures/clue_status_cases.json` with `fs` (as
`src/lib/__tests__/contentSig.test.js` reads files), with rows passed straight to `fromCliStrings` (Task 1's
schema). Also spec §6.2 "Commit"; key order
`"2,0,down"` < `"10,0,across"`; trim of a leading U+0085 and of U+FEFF (the first is stripped, the second
kept).

- [ ] RED: tests and fixtures only; run `npx vitest run src/lib/__tests__/clues.test.js`; commit `test(web): failing tests for Task 5`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(web): clue library`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 6: Signatures, snapshots, predicate, adoptable entry

**Files:** Modify `src/lib/contentSig.js`, `src/lib/history.js`, `src/lib/gridEdits.js`, and
`isAdoptableEntry` in `src/App.jsx`. Test the matching files in `src/lib/__tests__/`, plus a new
`src/__tests__/isAdoptableEntry.test.js` (no test file covers it today). Also `src/hooks/useUndoHistory.js`,
one interim line only (controller ruling, 2026-11-01; see the last criterion).

**Interfaces — Consumes:** `compareClueKeys` (Task 5). **Produces:**

```js
export function docSigOf(size, grid, clues) {}      // contentSig.js — the document signature
export function statusSigOf(size, grid, clues) {}   // contentSig.js — grid sig + keys + answers, not text
export function snapshotContent(grid, gridSize, clues) {}  // history.js — adds `clues`; sig = docSigOf
export function documentHasContent(grid, clues) {}  // gridEdits.js — gridHasContent(grid) || any clue
```

`contentSigOf(size, grid)` is unchanged. `restoreContent(grid, snapshot)` is unchanged, and callers read
`snapshot.clues`.

**Behavioural criteria:** spec §4.1. The document signature's exact form is
`JSON.stringify({size, cells, clues})`, with `cells` exactly what `contentSigOf` serializes and `clues` as
`[key, text, answer]` triples in key order. `snapshotContent` stores a copy of the clue map. The
`gridHasContent` docstring's purpose ("replacing the grid would lose work") moves to `documentHasContent`
(spec §7). `isAdoptableEntry` follows spec §3.5, "Saved document".

Interim until Task 8 (controller ruling, 2026-11-01): the hook calls `snapshotContent` with two arguments and
compares `snapshot.sig` with its rendered signature (`useUndoHistory.js`'s step-decision effect). So a call with
no clue map gives the same signature and stores the same copy as `{}`, and the effect's rendered signature
becomes `docSigOf(gridSize, grid, {})`. No other hook line changes. Task 8 replaces `{}` with `clues`. The hook
tests (`src/hooks/__tests__/`, `src/__tests__/undo*.test.jsx`) stay green, among them `useUndoHistory.test.jsx`'s
"a batch that changed nothing records no step".

**Normative cases:** spec §6.2 "Pure functions". The §4.1 example string is byte-exact for a 2×2 with clue
`"0,0,across" → {text: "Flower", answer: "RO"}`.

**Mutation (§6.3):** "The document signature does not sort entries" → identical for another insertion order.

- [ ] RED: tests and fixtures only; run `npx vitest run src/lib/__tests__/ src/__tests__/isAdoptableEntry.test.js`; commit `test(web): failing tests for Task 6`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(web): document signature and clue snapshots`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 7: Clues panel component

**Files:** Create `src/components/CluesPanel.jsx`. Test `src/__tests__/components/CluesPanel.test.jsx`.

**Interfaces — Consumes:** Task 5. **Produces** a presentational component with its own draft state:

```jsx
<CluesPanel
  grid={grid}                       // cells carry `number`
  clues={clues}
  displayStatuses={statuses}        // {[key]: 'ok'|'stale'|'orphaned'}
  selectedCell={selectedCell}       // {row, col, direction} | null, App's shape
  editingPaused={bool}
  onCommit={(key, draft) => ({ error })}   // synchronous; error is null or CLUE_TOO_LONG
  onKeep={(key) => {}}
  onDelete={(key) => {}}
  onSelect={(row, col, dir) => {}}
/>
```

**Behavioural criteria:** spec §5.2 (layout and texts, verbatim), §5.3 (selection; the highlighted row is the
entry containing `selectedCell` in its direction, scrolled into view with `block: 'nearest'`), §5.4 (drafts
commit on blur, Enter and unmount; Enter moves to the next row and from Across to Down; Escape restores; a
draft is replaced when the committed text changes beneath it), and §5.5 (inputs, Keep and Delete disabled
while `editingPaused`; number buttons still select). Keep shows where the displayed status is `stale` and
Delete where it is `orphaned` (§3.3). Styles use the existing `.xw-clue*` / `.xw-clues*` classes in
`src/styles/bench/base.css`.

**Normative cases:** spec §6.2 "Panel", except "a tool switch commits a draft" (Task 8 tests that through
App; here, unmounting with a draft calls `onCommit` once).

- [ ] RED: tests and fixtures only; run `npx vitest run src/__tests__/components/CluesPanel.test.jsx`; commit `test(web): failing tests for Task 7`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(web): clues panel`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 8: App wiring

**Files:** Modify `src/App.jsx`, `src/hooks/useUndoHistory.js`, `src/hooks/useSaveMachine.js` (comments
only, spec §7), `src/components/bench/ToolRail.jsx` (the `clues` tool between `autofill` and `theme`, with the
three-stroke icon, and the header comment, spec §5.1, §7), and `src/components/bench/GridPanel.jsx` (the
predicate). Tests: `src/__tests__/components/App.test.jsx` and
`src/components/bench/__tests__/ToolRail.test.jsx` (split the "no Clues tool" assertions, spec §6.2 "Rail"),
`src/hooks/__tests__/useUndoHistory.test.jsx`, plus new `src/__tests__/App.clues*.test.jsx` files as needed.

**Interfaces — Consumes:** Tasks 5–7. **Produces:**

```js
useUndoHistory({ grid, gridSize, clues, setGrid, setClues, editingPausedRef })  // snapshots hold clues
record(beforeGrid, beforeClues)   // returned as `record`, App's `recordStep`; snapshotContent(beforeGrid, size, beforeClues)
// App handlers passed to CluesPanel:
commitClue(key, draft) -> { error }   // returns { error: null } and writes nothing when editingPausedRef.current
keepClue(key)
deleteClue(key)
```

**Behavioural criteria:**
- `clues` state lives in App beside `grid`, in the saved `doc` (spec §3.5), and is read through App's
  `cluesRef`, which advances the way `editGrid`'s grid ref does (spec §4.3). Every `recordStep` call site
  (`App.jsx`, today at the `editGrid` body and the two clean paths) passes `cluesRef.current` as `beforeClues`.
  A clue commit, Keep or Delete records `(gridRef.current, cluesRef.current)` and then advances `cluesRef`.
- Hook internals: the step-decision effect's rendered signature becomes `docSigOf(gridSize, grid, clues)`, not
  `contentSigOf`. `beginBatch`'s "before" takes its clues from the hook's own rendered-clues ref, as it takes
  the grid. Restore calls `setClues(snapshot.clues)`.
- `GridPanel` gains a `clues` prop (default `{}`, so existing GridPanel tests still pass) and calls
  `documentHasContent(grid, clues)` at its two `gridHasContent` sites.
- The consumer table in spec §4.1 is the checklist. Each listed site reads the document signature, except
  `pendingClean`, which keeps the grid signature. Theme staleness and numbering are unchanged.
- Lifecycle per spec §4.2, undo per §4.3, gating per §4.4 (each handler re-checks `editingPausedRef` at write
  time), replacement confirm per §4.5 at its three call sites (`GridPanel.jsx` for New grid and Open, and
  App's prop to `ImportPanel`), and the Open-that-waits terms per §4.6.
- The commit's `currentPattern` and Keep's pattern are `slotAt(<live grid>, row, col, dir).pattern`.
- The Clues panel mounts for `currentTool === 'clues'`. For now its `displayStatuses` is
  `clueStatuses(grid, clues)`; Task 10 replaces this with reconciled statuses.

**Normative cases:** spec §6.2 "Undo", "Save", "Lifecycle", "Confirm" (New grid and Open saved here; Import
in Task 9), "Gating", "Rail", and the Panel row "a tool switch commits a draft".

**Mutations (§6.3):**
- "The snapshot signature reverts to the grid signature" → one changed commit is exactly one step.
- "The replacement predicate ignores clues" → New grid asks on a white grid with a clue.
- "`isDirty` reads the grid signature" → a commit makes the document dirty.

- [ ] RED: tests and fixtures only; run `npx vitest run` on the test files listed under Files; commit `test(web): failing tests for Task 8`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(web): clue state, undo and save`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 9: Grid-file import and export with clues

**Files:** Modify `src/components/ExportPanel.jsx` (receives `clues`, always writes them, `{}` when there are
none), `src/components/ImportPanel.jsx` (`validateImportedData` returns `clues`, and the check runs before
apply), `src/api/client.js`, and App's import handler. Tests: the existing ImportPanel/ExportPanel test files,
plus `src/api/__tests__/`.

**Interfaces — Produces:** `api.checkClues({ size, grid, clues })`, which posts to `/api/clues/check` through
`post()`/`clean()` the way `numberGrid` does. Grid cells are in the shape `numberGrid` sends.

- `validateImportedData(data)` returns `{size, grid, numbering}` plus `clues` **only when the file had the key**,
  with the raw value, `null` included. `'clues' in validated` is the discriminator.
- `performImport` (`ImportPanel.jsx`, after `handleImportClick`'s confirm) awaits `api.checkClues` when the
  key is present, before `onImport`.
- `onImport` / App's `handleGridImport` receive `clues`: the file's map when it was checked, or `{}` when the
  key was absent.

**Behavioural criteria:** spec §3.5, "Grid JSON file, browser export" and "browser import", in order: confirm,
then the check (only when the file has a `clues` key, including `{}` and `null`), then apply. A 400 shows
`error.message` and applies nothing. Any other failure refuses with `Could not check the clues: <error>.`.
Edits made during the check are replaced on the §3.4 Open-that-waits terms. The `Include clues` checkbox stays
hidden and its test is unchanged (spec §7).

**Normative cases:** spec §6.2 "Import", and "Confirm" for Import.

- [ ] RED: tests and fixtures only; run `npx vitest run` on the test files listed under Files; commit `test(web): failing tests for Task 9`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(web): grid-file clues on import and export`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 10: Status reconciliation

**Files:** Create `src/hooks/useClueReconcile.js`. Modify `src/App.jsx` (pass its result as
`displayStatuses`). Test `src/hooks/__tests__/useClueReconcile.test.jsx`.

**Interfaces — Consumes:** `statusSigOf` (Task 6), `clueStatuses` (Task 5), `api.checkClues` (Task 9).
**Produces:**

```js
useClueReconcile({ grid, gridSize, clues, active /* panel open && !editingPaused */ }) -> displayStatuses
```

**Behavioural criteria:** spec §5.6, all bullets. A request goes out on open and 300 ms after the status
signature last changed, carrying the signature it was built from. A reply applies only on an exact signature
match. Keys missing from the reply fall back to the browser's status. On a moved-on signature, a failure or a
live run, every status is the browser's, and a failure shows nothing.

**Normative cases:** spec §6.2 "Reconciliation", with fake timers.

**Mutation (§6.3):** "The reconcile applies a reply without comparing signatures" → a reply for an older status
signature is not applied.

- [ ] RED: tests and fixtures only; run `npx vitest run src/hooks/__tests__/useClueReconcile.test.jsx`; commit `test(web): failing tests for Task 10`.
- [ ] GREEN: production code until RED's tests pass, with RED's files untouched; commit `feat(web): reconcile clue status from the CLI`.
- [ ] REVIEW: spec and quality verdicts, RED/GREEN checks, and this task's mutations.

---

### Task 11: Documentation amendments

**Files:** every target in spec §7, "Novice spec", "CLI and API documentation" (OpenAPI and API_REFERENCE are
already done in Task 4) and "User documentation". The new how-to is `docs/user-guide/how-to/write-clues.md`.
§7's "Code comments" and "Tests" items are applied in Tasks 3, 6 and 8, beside the code they describe. Also,
found by review and not listed in §7:
- `docs/user-guide/README.md`: a how-to index row for `write-clues.md`.
- `docs/diataxis/claims.md`: row E-11 ("Exports have no clues") becomes false for the JSON export, so restate it
  for HTML only, or add a row. Re-verify row E-09 (JSON export is "complete grid data").
- `cli/README.md` has no command list matching the others. Put `clues check` where its commands are
  documented.

**Criteria:**
- Apply §7's edits verbatim. Review found every quoted target present at `17f058f`, some wrapped across lines.
  The novice spec is amended **at its current version on this branch's base**: 0.2.23 here, and 0.2.24 if PR
  #112 has merged first. Bump it and add an amendment record line.
- If `docs/user-guide-html` has landed on main, its regen check covers `docs/user-guide/*.md`, so rebuild the
  site in the same commit.
- `git add`, then `scripts/docs-check.sh`, before the commit.
- **Owner step, not an implementer step:** file the spec §8 tech-debt issue (browser grid-file parsing and
  serialization), labelled `tech-debt`, only with Arthur's go-ahead (CA-4's default: when this feature is built).

- [ ] WRITE: apply the edits; `git add`, `scripts/docs-check.sh`; commit `docs: clue authoring`.
- [ ] REVIEW: every §7 target and the review-found additions, checked against the files at HEAD.

---

### Task 12: Acceptance gate (real browser, not a code task)

Drive CLU-1 to CLU-9 (spec §6.4) in the running app (`python run.py` + `npm run dev`). CLU-8 also needs
`crossword fill` in a terminal. Record pass or fail per row with evidence (a screenshot or quoted DOM text).
Build-green plus vitest is not this gate. A failure goes back to the owning task as a fix and is never waived
here.
