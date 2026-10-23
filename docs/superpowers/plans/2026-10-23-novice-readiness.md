# Novice Fresh-Install Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A novice with nothing installed can install the app on macOS or Linux and use every feature; autofill never changes a letter the user typed and never strands the workflow.

**Architecture:** CLI-first, as the repo requires: lock semantics, pre-flight and the result keys live in `cli/` (`fill`); the Flask route carries a lock list to the CLI and maps exit 3 to a `complete` event; the React autofill machine snapshots, merges by provenance (`isAutofilled`) and restores. Grid, save and install work is independent of the solver and lands in its own phases.

**Tech Stack:** Python 3.9+ · Click · NumPy · Flask 3.0 · React 18 · Vite 5 · pytest · vitest

**Spec:** `docs/superpowers/specs/2026-10-23-novice-readiness-design.md`, version 0.2.4 @ `c281396` (0.2.3 approved by the owner 2026-10-23, every §7 default ruled; 0.2.4 adds §8, the planning defaults this plan cites as "(spec §8)", whose defaults apply if unruled by 2026-10-30). The spec governs: where this plan and the spec disagree, the plan is wrong. Executors read both.

## Global Constraints

- Platforms: macOS and Linux; Windows is out of scope (§1).
- Python floor 3.9: a module-level type alias uses `typing.Union`, never `|`; a class with `eq=False` also defines `__eq__` in its own body (`.claude/CLAUDE.md`).
- New capability goes CLI → `cli_adapter.py`/route → React; never crossword logic in `backend/` or `src/` (`.claude/CLAUDE.md`). `verify_words` and `clean_grid` in `backend/api/routes.py` are a recorded deviation and stay where they are (§3.5 NOTE).
- The backend↔CLI seam gets an argv contract test plus one real-subprocess end-to-end test; never mock both sides (`.claude/CLAUDE.md`).
- Docstrings and comments that implement a spec rule cite it as `novice-readiness spec 0.2.4 §<section> (<finding id>)`, e.g. `novice-readiness spec 0.2.4 §2.1 (C12)`.
- No status values written by hand into docs or docstrings (counts, timings, "FIXED"); name the command that proves them (`.claude/CLAUDE.md`).
- User-visible strings are copied verbatim from the spec, including punctuation: `×` (U+00D7), `—` (U+2014), `’` (U+2019), `·` (U+00B7).
- Every commit runs pre-commit (black, isort, ruff, flake8); never `--no-verify`. Conventional commits, `type(scope): description`; no AI attribution trailers.
- Never chain a test run and a commit in one shell command; read the result, then commit. Run a suite whose result you cite alone, not beside another suite (`test_hybrid_integration.py::test_fill_simple_grid` asserts wall clock).
- Work happens in the worktree `../crossword-helper-novice` on `feat/novice-readiness`. Never push.

## Commands

```bash
pytest                          # default suite (slow deselected)
pytest -m slow                  # slow suite
npx vitest run                  # frontend
npm run build                   # must stay clean
bash scripts/docs-check.sh      # doc guard
bash scripts/check-guards.sh    # repo guards
```

## Sequencing: priority versus dependency

§1 lists the must-haves **in priority order**. This plan keeps that priority where it can and resequences for dependency in three places; this is sequencing, not a spec change:

1. **`isAutofilled` and its writers (§3.7) land before §2.3**, because §2.3's lock list is defined by the flag.
2. **The document id (§3.4, M1) is introduced before §2.3**, because the machine's stale-merge guard compares it. Phase 4 replaces `gridId` with the document id and mints it at app start and on import; New grid (Phase 6) and Open saved/restore-on-load (Phase 6) mint or adopt it.
3. **The D1 writer gate (§2.3) lands before New grid and Open saved (§3.2, §3.4)**, which are built already gated.

Phases: 0 plan-time checks (done, below) · 1 install (§5) · 2 CLI `fill` (§2.1) · 3 route, adapter and server tracker (§2.2, §2.4 server) · 4 UI foundation (cell fields, document id, §3.7 writers, D1 gate) · 5 UI autofill (§2.3, §2.4 client, §2.5) · 6 grid UI (§3.1–§3.6, §3.8) · 7 word lists and CLI (§4) · 8 acceptance (§6).

## Phase 0: plan-time checks (results)

Run 2026-10-23 on `feat/novice-readiness` @ `2e36f17` (code identical to `main` @ `a72be24`).

**0.1 Every writer of `Grid.cells` in `cli/src` (§2.1 D3).** Commands, run from the worktree root:

```bash
ast-grep run -p '$G.cells[$$$] = $V' -l python cli/src
ast-grep run -p '$G.cells[$A][$B] = $V' -l python cli/src      # no hits
ast-grep run -p '$G.cells = $V' -l python cli/src
git grep -nE 'cells\.(fill|put|itemset)|np\.copyto|np\.putmask' -- cli/src   # no hits
git grep -nE '^\s*[A-Za-z_]+\s*=\s*[A-Za-z_.]+\.cells\s*$' -- cli/src       # no aliases
git grep -nE '\.(set_letter|set_black_square|place_word|remove_word|clear_unlocked)\(' -- cli/src ':!cli/src/core/grid.py'
```

Positive control: `grid.py`'s `set_letter` body (`self.cells[row, col] = ord(upper) - ord("A") + 1`) and `iterative_repair.py`'s `self.grid.cells[:] = best_grid` both appear in the first command's output.

Direct writes outside `cli/src/core/grid.py`, all in `cli/src/fill/iterative_repair.py`:
lines 243, 247, 281, 500 (`cells[:] = best_grid` / `original_grid`, bulk restores), 334 and 1661 (`cells[pos] = 0`), 686, 1192, 1206, 1390, 1401, 1503 (`cells[pos] = val`), 1360 and 1435 (`cells[pos] = ord(ch) - ord("A") + 1`).

Setter call sites outside `grid.py` (these go through `place_word`/`remove_word`/`set_letter`/`set_black_square`, which this plan makes lock-checking): `constraint_analyzer.py` (1, on a clone), `nyt_parser.py` (1, `set_letter`), `adaptive_autofill.py` (2, `set_black_square`), `autofill.py` (6), `beam_search/beam/manager.py` (1), `beam_search/orchestrator.py` (4), `beam_search/selection/value_ordering.py` (2), `iterative_repair.py` (6).

Inside `grid.py`, direct writes are in `set_black_square`, `set_letter`, `from_dict` and `clear_unlocked` (which by name skips locked cells). Task 2.4 classifies each `iterative_repair.py` line above as "skips locked cells" or "restores a copy taken while locked cells held their input letters", per §2.1.

**0.2 Beam and `problematic_slots` (§2.1 `[?]`), partially resolved by reading:**
- `beam_search/beam/manager.py` expansion skips a slot whose pattern has no `?` (`# Skip if already filled`) without consulting the word list, so a fully typed off-list word is not searched during expansion.
- Beam's `_create_result` (`beam_search/orchestrator.py`) builds `problematic_slots` only when `success` is false, as **raw slot dicts** (`row`, `col`, `direction`, `length`) for every slot not in `best_state.slot_assignments`, with **no `"reason"` key**. A typed word is never in `slot_assignments`, so it is listed whenever the run is not a success. `Autofill` (classic) lists `self.grid.get_empty_slots()`, also without `"reason"`. Only `IterativeRepair` (and therefore hybrid) emits `{"slot", "pattern", "reason"}` with reasons `unfilled`, `invalid_word`, `partial`.
- Consequence for §2.1 case 3 (b): it reads only entries with `"reason": "invalid_word"`, so it contributes nothing under `beam`, `regex` and `trie`; case 3 (a) still applies to them.
- **Not resolved by reading:** whether beam's viability check rejects states because of a fully typed off-list crossing (the beam analogue of #74). Task 2.11 pins it with a characterization test and a STOP gate (below).

**0.3 P5: do `verify_words` and `clean_grid` fold?** No. Both in `backend/api/routes.py` read each list with their own `open(...)` loop and `line.split(";")[0].strip().upper()`, not `WordList.from_file`. P5's ruled default is "every word-list load", so Phase 7 moves both onto the shared parser (`WordList.parse_line`) so they fold exactly as the solver does. Note: `WordList.from_file(..., use_cache=True)` has a cache; Phase 7 checks that a folded list is not served from a pre-fold cache entry.

## File Structure

Existing files named loosely in the spec, exactly: the cell codec is `src/api/gridCodec.js` (`makeCell`); `contentSigOf` and `initializeGrid` are in `src/App.jsx`; `gridId` is `src/App.jsx`'s `useState(1)`; the Save button is `src/components/bench/TopBar.jsx` (`onSave`); autosave is `src/hooks/useSaveMachine.js` (`AUTOSAVE_MS`); storage is `src/lib/storage.js` (`SAVE_KEY = 'crossword_saved_grid'`); the route is `backend/api/routes.py` (`fill_with_progress`, `run_cli_with_progress`, `_pump_stderr`); validation is `backend/api/validators.py` (`validate_fill_request`); the tracker is `backend/api/progress_routes.py` (`generate`, `cleanup_progress_tracker`); `CLI_STARTUP_BUDGET_SECONDS` is in `backend/core/cli_adapter.py`; pre-flight's inputs are `cli/src/domain/slot_model.py` (`SlotModel.from_grid`, module function `fixed_from_grid`), `cli/src/domain/letter_bitset.py` (`LetterBitsetIndex.from_word_list`, `count_matches`), `cli/src/domain/fillability.py` (`assess`).

New files (paths fixed; writers pin their signatures in the tasks):

| Path | Responsibility | Phase |
|---|---|---|
| `cli/src/fill/locked_letters.py` | lock-set resolution after load, pre-flight (dead slots, cases 1, 2, B2), `stuck_cells`, the end-of-run postcondition | 2 |
| `src/lib/docId.js` | `mintDocId()`: `crypto.randomUUID()` with a fallback | 4 |
| `src/lib/gridEdits.js` | pure grid-write rules: the §3.7 `write*` helpers (Task 4.3) and Phase 6's guard rules (`canToggleBlack`, `gridHasContent`, `applyVerifyErrors`, `planClean`, `clearAllErrors`) | 4, 6 |
| `src/components/bench/GridPanel.jsx` | the new Grid panel for tool `edit`: New grid, Black square toggle, Open saved | 6 |
| `src/components/bench/InlineConfirm.jsx` | the in-panel confirm (no browser dialog), shared by New grid, Open saved and Clean | 6 |
| `src/components/bench/SavedGridsList.jsx` | the Open saved list (name, size, saved time; Open, Delete) | 6 |
| `src/components/bench/SaveNamePrompt.jsx` | the name prompt under the Save button | 6 |
| `src/components/bench/RestoreBanner.jsx` | `Restored "<name>" (saved <time>)` with "Start blank" and × | 6 |
| `src/components/bench/GridHintLine.jsx` | the always-visible key hint under the grid | 6 |
| `docs/dev/qa/YYYY-MM-DD-novice-readiness-run.md` | the Phase 8 run log, dated on the day it runs, beside `docs/dev/qa/2026-10-22-fresh-install-run.md` | 8 |

Styling for new bench components follows their siblings (`AutofillPanel.jsx`, `TopBar.jsx`): the writer reads where those take their classes from and does the same; no new styling system.

Test locations: CLI `cli/tests/unit/` and `cli/tests/integration/`; backend `backend/tests/unit/` and `backend/tests/integration/`; hooks `src/hooks/__tests__/`; bench components `src/components/bench/__tests__/`; other components `src/__tests__/components/`; `App` behaviour `src/__tests__/`; storage `src/lib/__tests__/`; codec `src/api/__tests__/`.

## Cross-phase pins (verbatim from the spec; binding on every phase)

**Lock channel (§2.1, §2.2).**
- CLI option `--lock-filled/--no-lock-filled`, default `--lock-filled` (P1). Grid file key `"locked": [[r, c], ...]`; `"locked": []` locks nothing; key absent with `--lock-filled` locks every letter; `--no-lock-filled` locks no input letter.
- A listed cell that is out of bounds or holds no letter fails the run through `_fail_fill` (exit 1).
- `Grid.to_dict` gains `include_locks: bool = False`; with `True` it adds `"locked"` (sorted row-major, `[]` when none). Only `Autofill.fill_with_restarts` and `AdaptiveAutofill`'s round trip pass `True`.
- Request body field `"locked_cells": [[r, c], ...]`; the UI **always** sends it, `[]` included. The route tests `locked_cells is not None`, writes it as `"locked"` beside `"size"` and `"grid"`, and always passes `--lock-filled` explicitly. Field absent → no `"locked"` key written.

**Blocked result and exit code (§2.1).** Exit code **3**. JSON:
`{"success": false, "blocked": true, "reason": "no_word_fits", "blocked_cells": [[r, c], ...], "blocked_slots": [{"row": r, "col": c, "direction": "across"|"down", "length": n, "pattern": "C?T"}], "off_list_cells": [...], "stuck_cells": [], "grid": <input grid, unchanged>}`; for B2 `"reason": "no_word_of_length"` and `"blocked_cells": []`.
Text output: `Blocked: no word fits <pattern> at <row>,<col> <direction>` (one line per slot); `Blocked: the selected word lists have no words of length <n>` (one line per length).

**Result keys (C11).** The four `--json-output` fill results (main, already-filled early return, paused payload, blocked) carry `"blocked"` (bool), `"blocked_cells"`, `"off_list_cells"`, `"stuck_cells"` (lists, `[]` when empty). `_fail_fill` errors (`{success, error, hint}`) do not. Cell lists are unique, sorted row-major, `[row, col]` zero-based.

**Case 2 (§2.1).** `"warnings"` gains `"Typed words not in the selected word lists: <WORD>, ..."`; pre-flight emits one stderr progress event, status `running`, whose `data` carries `"off_list_cells"` and that warning.

**Postcondition message (§2.1).** `Autofill changed a locked letter; nothing was written.`

**SSE (§2.2, §2.4).** Statuses are `running`, `complete`, `paused`, `error`; there is no `failed` and no `blocked` status. Exit 3 with parseable stdout JSON carrying `"blocked": true` → terminal event status `complete`. Timeout text: `Operation timed out`. The 202 response gains `"ceiling_seconds"` = `timeout` + `CLI_STARTUP_BUDGET_SECONDS` (P7).

**Route error text and Cancel (planning defaults PD-3-KILL, PD-3-EARLY; C4 key).** A non-zero exit whose stdout parses as JSON with a string `"error"` → the `error` event's message is that string; a negative return code keeps `CLI Error (code <rc>)`; the client counts an `error` as the cancel's kill when a cancel is pending and the message starts with `CLI Error (code -`. An early Cancel (recorded before the process registers) returns 200. The C4 pre-flight event's `data` is `{"off_list_cells": [...], "warning": "<text>"}`.

**Tracker (§2.4).** Terminal event (`complete`, `error`, `paused`) recorded with its enqueue time; removed 60 s after it (P3); `generate()` sends the recorded terminal event on connect and on every queue timeout if its own subscriber has not sent one; no timer thread.

**Cell fields (§2.3, §3.7).** `isAutofilled` (boolean, default `false`): saved, part of `contentSigOf`, absent → `false`; import ignores it. `isBlocked` (boolean, the red cells, separate from `isError`): **not** saved, **not** part of `contentSigOf`. Both are added to `makeCell` and to `App.jsx`'s `initializeGrid`.

**Lock list (§2.3).** Every **white** `isThemeLocked` cell with a letter, plus every white cell with a letter that is not `isAutofilled`.

**Live states (§2.3, D1).** `autofill.state` `submitting` or `running`. While live, the machine's `onGridUpdate` is the only writer of letters and black squares; every other writer is disabled and returns early at write time. Grid message: `Editing is paused while autofill runs.`

**Document id (§3.4, M1).** A unique string, `crypto.randomUUID()` with a fallback. Minted by New grid, import, and app start when restore-on-load finds no save; adopted by Open saved and restore-on-load. Passed to the machine's `start` and with every merge and "Keep partial fill".

**UI names pinned by this plan (Phases 4–6 share them).**
- `src/App.jsx`: `const [docId, setDocId] = useState(...)` replaces `gridId`/`setGridId` everywhere `gridId` is used today.
- `src/lib/docId.js`: `export function mintDocId(): string`.
- `src/hooks/useAutofillMachine.js`: `export const LIVE_STATES = new Set(['submitting', 'running'])`; the hook's return object gains `startSnapshot` (the full grid copy taken at Start, or `null` when no run has started since the last New grid / Open saved).
- `src/App.jsx`: `const editingPaused = LIVE_STATES.has(autofill.state)`, the one predicate every gated writer and control reads.

**Storage (§3.4).** `src/lib/storage.js`: `list()` (all entries, newest first), `remove(id)`, upsert-by-id `save(doc)`, `load()` returns the newest entry; `save` rejects on a write failure, `load` never rejects. Key `crossword_saved_grids` (array, newest first); each entry is the save document plus `name`, keyed by `doc.id`, with `savedAt`. Legacy key `crossword_saved_grid` migrated once into the array as `Saved grid`, then removed. Default name `<size>×<size> <YYYY-MM-DD HH:MM>`.

**UI strings (verbatim).**
- Outcome table (§2.3): `Successfully filled X/Y slots!` · `Filled X/Y slots — N entries may be invalid (use Verify Words to check)` with offer "Keep fill" · `Autofill could not fill around the highlighted letters.` / `Partial: X/Y slots (P%)` with offer "Keep partial fill (X/Y slots)" · `No word fits the highlighted letters.` · `The selected word lists have no words of length N.` · `No solution found` · `Cancelled by user` · `Autofill was paused outside the app.` · `Lost contact with the autofill run.`
- Hints: `Select at least one word list` · `Clear some cells to run autofill again`.
- New grid confirm: `Replace the current grid? Unsaved changes are lost.` with "Replace" and "Cancel".
- Clean: `Clean will remove N letters` (`1 letter` when N is 1) with "Clean" and "Cancel"; `Grid is clean — all words are valid!`; `Nothing removed: theme-locked letters are kept.`
- Saves: `Restored "<name>" (saved <time>)` with "Start blank"; `Could not save: browser storage is full. Delete a saved grid or export this one.`; autosave failure unchanged: `Couldn’t save — will retry.` and status `offline — will retry`.
- Theme: `Suggestions updated for the changed grid.` · `skipped due to conflicts` only for real conflicts · `Could not reach the server`.
- Key hint: `Type letters · Arrows move · Space or . black square · Enter switch direction · Tab next word · Backspace clear`.
- Install: `Missing: <tool> <minimum version> — install from <url>` · `Install python3-venv (for example: sudo apt install python3-venv), then run ./setup.sh again` · `Port <n> is in use. Start with PORT=<other> python3 run.py`.

## STOP gates (task-time; the executor stops and reports to Arthur)

An executor reaching one of these steps stops, records the measurement in the plan's task with the command that produced it, and reports before continuing:

- **Pre-flight latency (§2.1):** measured on `comprehensive` and the largest `raw/` list at 15×15 and 21×21. Over 2 s on `comprehensive` at 21×21 → report before the task lands.
- **Pre-placed unlocked letters per `--algorithm` (§2.3 `[?]`):** one characterization test per value records what happens to a pre-placed unlocked letter. A solver that changes one is a finding to report, not something to fix in the task.
- **Beam and a fully typed off-list word (§2.1 `[?]`, Phase 0.2):** a characterization test under `--algorithm beam`. If beam rejects every placement crossing it, report: the spec's case 2 under beam needs an amendment.
- **`npm ci` on a fresh clone (§5):** with the Node LTS the README names. If it fails, the lock is regenerated once with that Node and committed; report either way.
- **`lsof -i :5000` on a stock Mac (§5 `[?]`):** record whether AirPlay Receiver holds the port.

---

## Phase 1: install (spec §5)

Independent of the solver. Order inside the phase: 1.1 → 1.6; 1.6 (README) is last so it documents behaviour that exists. Every task cites `novice-readiness spec 0.2.4 §5 (<id>)` in the comment or docstring that implements a rule.

**Phase-wide verification rules (apply to every task below).**
- Shell and README changes are verified by (a) a pytest script test that runs `setup.sh`/`run.py` against a fixture `PATH` or a patched `app.run`, never the network, never a real `pip`/`npm`; or (b) a manual step with the exact command. No expected value that a command could print is typed by hand into a doc.
- Script tests live in `tests/` (listed in `pytest.ini` `testpaths`, so CI runs them without a list edit). They copy `setup.sh` into a `tmp_path` project dir, because the script derives `venv/` from its own location.
- Tool shims (a fake `python3`, `node`, `npm`) are test fixtures the implementer designs; the contract below pins only what each shim must report and what the script must then do.

### Task 1.1: `npm ci`, `engines`, and the lock-file gate (§5, #49)

**Files:**
- Modify: `package.json` (add `engines`)
- Modify: `setup.sh` (the `npm install --silent 2>&1 | tail -1` line only)
- Modify (only if the STOP gate below fails): `package-lock.json`
- Test: `tests/test_setup_script.py` (create; this task adds only the `engines` assertion)

**Interfaces:**
- Produces: `package.json` key `"engines": {"node": ">=18"}` (verbatim, §5); `setup.sh` runs `npm ci` where it ran `npm install`.

**Behavioral criteria:**
- `package.json` gains `"engines": {"node": ">=18"}`, matching the README floor (§5). No `.nvmrc` is added (§5 `[?]`, P14: "this spec does not require one").
- `setup.sh` installs with `npm ci`, keeping the existing `--silent` and failure propagation under `set -euo pipefail`. `npm ci` never writes `package-lock.json`, so a fresh clone is still clean after setup (#49).
- A comment at the changed line cites `novice-readiness spec 0.2.4 §5 (#49)`.

**Normative cases:**

| check | result |
|---|---|
| `package.json` parsed as JSON, key `engines.node` | `">=18"` |
| `setup.sh` text | contains `npm ci`; no `npm install` |

- [ ] **Step 1: STOP gate, baseline `npm ci` on a fresh clone (before editing).** Install the current Node LTS line listed at nodejs.org/en/about/previous-releases into a `mktemp -d` (download the tarball and `SHASUMS256.txt` from nodejs.org/dist, verify with `shasum -a 256 -c --ignore-missing`), put it first on `PATH`, then:

```bash
SB=$(mktemp -d); node --version
git clone --local /Users/apa/projects/crossword-helper-novice "$SB/clone"
cd "$SB/clone"
npm ci > "$SB/npm-ci.log" 2>&1
```
Read `$?` on its own line. Then `git status --short` and `git diff --stat -- package-lock.json` in the clone. **STOP and report to Arthur:** the Node version, the `npm ci` exit code, and whether the status/diff are empty. Do not continue to Step 2 before reporting.

**Result (2026-10-23):** `node --version` gave v24.22.1 (Active LTS) and `npm --version` gave 11.19.1. On a fresh `git clone --local` at `509f464`, `npm ci > "$SB/npm-ci.log" 2>&1` returned rc=0; `git status --short` and `git diff --stat -- package-lock.json` were both empty. `npm run build` on that clone returned rc=0. Step 2 was skipped (rc was 0) and `package-lock.json` is unchanged.

- [ ] **Step 2: Lock-regenerate branch (only if Step 1's exit code was non-zero, §5).** With the same Node: `rm package-lock.json && npm install --package-lock-only`, copy the result to the worktree's `package-lock.json`, repeat Step 1 on a new fresh clone and read its exit code. Commit once: `git add package-lock.json`, `git diff --cached --stat`, `git commit -m "chore(deps): regenerate package-lock.json so npm ci succeeds"`. **STOP and report** either way (regenerated or not). The lock is regenerated at most once.
- [ ] **Step 3: Write the failing test** for the two normative rows; design it yourself.
- [ ] **Step 4: Run it, confirm it fails because `engines` is absent:** `pytest tests/test_setup_script.py -v`.
- [ ] **Step 5: Edit `package.json` and `setup.sh`.**
- [ ] **Step 6: Run it, confirm it passes:** `pytest tests/test_setup_script.py -v`.
- [ ] **Step 7: Manual check on a fresh clone with the Step 1 Node** (needs network): copy the edited `package.json`/`setup.sh` into a new `git clone --local` of the worktree, run `./setup.sh`, then `git status --short`. Expected: empty output (tracked tree clean; `venv/`, `node_modules/`, `frontend/dist/` are gitignored). Paste the command output into the commit body only if it is non-empty.
- [ ] **Step 8: Commit** (read the test result first; do not chain):

```bash
git add package.json setup.sh tests/test_setup_script.py
git diff --cached --stat
git commit -m "feat(install): setup uses npm ci and package.json declares node >=18"
```

### Task 1.2: `setup.sh` prerequisite checks print `Missing:` (§5)

**Files:**
- Modify: `setup.sh:7-34` (the Python and Node checks) and add an `npm` check after the Node check
- Test: `tests/test_setup_script.py` (extend; create the fixture-`PATH` harness here)

**Interfaces:**
- Consumes: Task 1.1's test module.
- Produces: the fixture-`PATH` harness (shim directory builder) that Task 1.3 reuses.

**Contract — the message form (spec §5, verbatim):** `Missing: <tool> <minimum version> — install from <url>`; the dash is U+2014. Each failing check prints exactly one such line and exits 1 before anything is created (no `venv/`, no `node_modules/`). The existing `Error:` wording for these checks is removed.

**Behavioral criteria:**
- `python3` absent, or present but older than 3.9 → the python3 line. `node` absent, or older than 18 → the node line. `npm` absent while python3 and node pass → the npm line. (§5: "The existing Python ≥3.9 and Node ≥18 checks print `Missing:` …" and "An `npm` check is added in the same form"; the too-old case is read as covered by "checks", not as a separate message.)
- Order of checks: python3, node, npm. A later check never runs once an earlier one has failed.
- Passing checks still print `[ok] Python <ver>` and `[ok] Node.js <ver>` as today.
- Tokens, pinned from the README floors in §5 (`Python 3.9 or later`, `Node.js 18 or later`) and the urls as the spec writes them (`python.org/downloads`, `nodejs.org`). **Planning defaults `PD-L1` (npm line) and `PD-L2` (url scheme) (spec §8): the npm row below is a planning default, not a spec value.**
- Comments cite `novice-readiness spec 0.2.4 §5 (SETUP-MISSING)`.

**Normative cases** (fixture `PATH`; the script is run with `bash setup.sh`; output is stdout+stderr combined, stream not pinned):

| fixture `PATH` | exit | output contains | `venv/` created |
|---|---|---|---|
| no `python3` | 1 | `Missing: python3 3.9 or later — install from https://python.org/downloads` | no |
| `python3` shim reporting 3.8 | 1 | same line | no |
| no `node` (python3 ok) | 1 | `Missing: node 18 or later — install from https://nodejs.org` | no |
| `node` shim reporting v16 | 1 | same line | no |
| no `npm` (python3, node ok) | 1 | `Missing: npm (installed with Node.js 18 or later) — install from https://nodejs.org` (planning default `PD-L1`, spec §8) | no |
| python3 3.9, node v18, npm present | proceeds past the checks | `[ok] Node.js v18…` | n/a (test stops at the shims) |

- [ ] **Step 1: Write the failing tests** from the table.
- [ ] **Step 2: Run, confirm they fail on the old `Error:` text:** `pytest tests/test_setup_script.py -v`.
- [ ] **Step 3: Implement** the three checks.
- [ ] **Step 4: Run, confirm pass:** `pytest tests/test_setup_script.py -v`.
- [ ] **Step 5: Manual check (SETUP-MISSING, §6)** on the real machine: `env -i HOME="$HOME" PATH=/usr/bin:/bin bash setup.sh` with a `PATH` lacking `node` prints the node line and exits 1 (read `$?` on its own line). Repeat for python3 and npm by building a `PATH` directory of symlinks that omits that tool. The Phase 8 task 8.3 repeats this under E1.
- [ ] **Step 6: Commit:**

```bash
git add setup.sh tests/test_setup_script.py
git diff --cached --stat
git commit -m "feat(install): setup.sh names the missing tool, its minimum version and where to get it"
```

### Task 1.3: `setup.sh` checks `venv/bin/pip` on both branches (§5)

**Files:**
- Modify: `setup.sh:36-47` (the venv creation / "already exists" block)
- Test: `tests/test_setup_script.py` (extend)

**Interfaces:**
- Consumes: Task 1.2's shim harness.

**Contract — message (spec §5, verbatim):** `Install python3-venv (for example: sudo apt install python3-venv), then run ./setup.sh again`

**Behavioral criteria:**
- After `python3 -m venv "$VENV_DIR"` the script checks that `venv/bin/pip` exists. If not it removes the `venv/` it just created, prints the message, exits 1.
- The "already exists" branch runs the same check: a partial `venv/` left by an earlier run is removed and the same message printed, exit 1 ("repaired rather than trusted").
- `python3 -m venv` itself exiting non-zero while leaving a partial `venv/` (Debian/Ubuntu without `python3-venv` leave a partial `venv/`, §5) must reach the same check and message; under `set -e` a bare failing `python3 -m venv` would otherwise abort the script before the check. The Phase 8 LINUX row is the real-system confirmation of this reading.
- When `venv/bin/pip` exists on either branch the script continues to "Installing Python dependencies".
- Comments cite `novice-readiness spec 0.2.4 §5 (venv)`.

**Normative cases:**

| starting state, shim behaviour | exit | output contains | `venv/` afterwards |
|---|---|---|---|
| no `venv/`; `-m venv` creates `venv/` without `bin/pip`, exits 0 | 1 | the message | absent |
| no `venv/`; `-m venv` creates `venv/` without `bin/pip`, exits non-zero | 1 | the message | absent |
| `venv/` exists without `bin/pip` | 1 | the message | absent |
| `venv/` exists with an executable `bin/pip` | script continues | `Installing Python dependencies` | present |
| no `venv/`; `-m venv` creates `venv/bin/pip` | script continues | `Virtual environment created` | present |

- [ ] **Step 1: Write the failing tests** from the table.
- [ ] **Step 2: Run, confirm failure** (`pytest tests/test_setup_script.py -v`): the absence of the check, not a broken shim.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run, confirm pass.**
- [ ] **Step 5: Commit:**

```bash
git add setup.sh tests/test_setup_script.py
git diff --cached --stat
git commit -m "feat(install): setup.sh repairs a venv without pip and says which package to install"
```

### Task 1.4: `run.py` and `backend/app.py` debug off by default, `PORT`, port-in-use message (§5, SERVE-1, I6)

**Files:**
- Modify: `run.py` (all; docstring included)
- Modify: `backend/app.py` (the `if __name__ == "__main__":` launcher only; planning default `PD-L5`, spec §8)
- Test: `backend/tests/unit/test_run_launcher.py` (create; covers both launchers)

**Interfaces:**
- Produces: `run.py` keeps its call `app.run(host=..., port=..., debug=...)` with those three keyword arguments (tests patch `backend.app.app.run` and execute `run.py` as `__main__` via `runpy`). `backend/app.py`'s `__main__` launcher keeps its `app.run(host="localhost", port=..., debug=...)` call; its test runs the file as `__main__` via `runpy` with `flask.Flask.run` patched.

**Behavioral criteria:**
- `debug` is `True` only when the environment variable `FLASK_DEBUG` equals `1`; otherwise `False` (§5: "`debug=False` by default; `FLASK_DEBUG=1` turns debug on"). The docstring says so and drops "with debug mode enabled".
- `port` is the integer value of the environment variable `PORT`, default 5000. `host` stays `"localhost"`.
- If binding fails because the address is in use (`OSError` with `errno.EADDRINUSE`), `run.py` prints `Port <n> is in use. Start with PORT=<other> python3 run.py` (`<n>` replaced by the port; `<other>` left as the literal placeholder: planning default `PD-L3`, spec §8), prints no traceback, and exits 1 (planning default `PD-L4`, spec §8; so is: a non-integer or out-of-range `PORT` is not handled, the `int` conversion error propagates; only `FLASK_DEBUG=1` turns debug on). Any other `OSError` propagates unchanged.
- **`backend/app.py` (planning default `PD-L5`, spec §8):** its `if __name__ == "__main__":` launcher gets the same rule as `run.py`: `debug` is `True` only when `FLASK_DEBUG` equals `1`, otherwise `False`; `port` is the integer value of `PORT`, default 5000; `host` stays `"localhost"`. (The in-use message is `run.py`'s; `app.py` does not duplicate it.)
- Comments cite `novice-readiness spec 0.2.4 §5 (I6, SERVE-1)`.

**Normative cases** (patched `app.run`; the in-use rows run the real script in a subprocess with a socket held on `127.0.0.1:<port>`):

| environment | `app.run` keyword arguments / observable |
|---|---|
| neither variable set | `host="localhost"`, `port=5000`, `debug=False` |
| `FLASK_DEBUG=1` | `debug=True` |
| `FLASK_DEBUG=0` | `debug=False` |
| `PORT=5057` | `port=5057` (an `int`) |
| `PORT=<held port>` | output contains `Port <held port> is in use. Start with PORT=<other> python3 run.py`; no `Traceback`; exit code 1 |
| `backend/app.py` as `__main__`, neither variable set (`PD-L5`) | `host="localhost"`, `port=5000`, `debug=False` |
| `backend/app.py` as `__main__`, `FLASK_DEBUG=1` (`PD-L5`) | `debug=True` |
| `backend/app.py` as `__main__`, `FLASK_DEBUG=0` (`PD-L5`) | `debug=False` |
| `backend/app.py` as `__main__`, `PORT=5057` (`PD-L5`) | `port=5057` (an `int`) |

- [ ] **Step 1: STOP gate, AirPlay on :5000 (§5 `[?]`, P13).** On a stock Mac run `lsof -nP -iTCP:5000 -sTCP:LISTEN` and, separately, `lsof -i :5000`. **STOP and report to Arthur:** the command output verbatim, the macOS version (`sw_vers -productVersion`), and whether AirPlay Receiver (ControlCenter) holds the port. The 2026-10-22 run could not test this (its SERVE-0 case: "the setting is off"). If the executing machine is not a stock Mac, report that instead; do not guess.
  Result (2026-10-23): macOS 26.5.2 (`sw_vers -productVersion`). `lsof -nP -iTCP:5000 -sTCP:LISTEN` and `lsof -i :5000` printed nothing (rc=1 both); `lsof -nP -iTCP -sTCP:LISTEN | grep -iE 'ControlCe|AirPlay|:7000|:5000'` printed nothing; `defaults -currentHost read com.apple.controlcenter AirplayRecieverEnabled` -> "does not exist". AirPlay Receiver does not hold :5000 here; whether this Mac is stock is unconfirmed.
- [ ] **Step 2: Write the failing tests** from the table.
- [ ] **Step 3: Run, confirm failure:** `pytest backend/tests/unit/test_run_launcher.py -v`.
- [ ] **Step 4: Implement `run.py`.**
- [ ] **Step 5: Run, confirm pass.**
- [ ] **Step 6: Manual check, debug mode (the reloader):** with `FLASK_DEBUG=1` and a port held (`python3 -c 'import socket,time; s=socket.socket(); s.bind(("127.0.0.1",5057)); s.listen(); time.sleep(60)' &`), run `FLASK_DEBUG=1 PORT=5057 python3 run.py`. Expected: the in-use message is the only user-facing error text (no traceback). If the reloader prints a traceback, report it to Arthur rather than widening the task.
- [ ] **Step 7: Commit:**

```bash
git add run.py backend/app.py backend/tests/unit/test_run_launcher.py
git diff --cached --stat
git commit -m "feat(install): run.py and backend/app.py default to debug off, read PORT; run.py explains a port in use"
```

### Task 1.5: Vite proxy follows `PORT` (§5, I6)

**Files:**
- Modify: `vite.config.js:10-15` (`server.proxy['/api'].target`)
- Test: `src/__tests__/viteConfig.test.js` (create)

**Contract:** the proxy target is `http://localhost:<port>` where `<port>` is `process.env.PORT`, default `5000` (§5: "`vite.config.js` reads `process.env.PORT` (default 5000) for the proxy target"). `server.port` (3000), `server.host` (`127.0.0.1`), `build` and `test` entries are unchanged.

**Normative cases** (the test re-imports the config with `PORT` set/unset):

| `PORT` | `config.server.proxy['/api'].target` |
|---|---|
| unset | `http://localhost:5000` |
| `5057` | `http://localhost:5057` |

- [ ] **Step 1: Write the failing test.** **Step 2: Run:** `npx vitest run src/__tests__/viteConfig.test.js` — confirm it fails on the second row. **Step 3: Implement.** **Step 4: Run, confirm pass.**
- [ ] **Step 5: Build still clean:** `npm run build`.
- [ ] **Step 6: Commit:**

```bash
git add vite.config.js src/__tests__/viteConfig.test.js
git diff --cached --stat
git commit -m "feat(install): the Vite dev proxy follows PORT"
```

### Task 1.6: README "Before you start", "Using the app", dev-mode section (§5)

**Files:**
- Modify: `README.md` (insert after the screenshot table, before "Quick Start"; edit "Development Mode")

**Behavioral criteria** (each from §5; a missing item is a defect):
- **"Before you start"** is the first section after the screenshots and contains: (1) Python 3.9 or later — macOS: from python.org (the system `python3` stub opens an Xcode command-line-tools install dialog on first use; either path works); Linux: the distribution's `python3` and `python3-venv` packages. (2) Node.js 18 or later (LTS): from nodejs.org, or the distribution package if it is 18 or later. (3) Getting the code: "Download ZIP" from GitHub, or `git clone`; after a ZIP extract the existing `chmod +x setup.sh` line is part of the steps. (4) One line: Windows is not supported yet.
- **"Using the app"**: a short tour, one or two lines per visible tool — Grid, Lists, Search, Theme, Autofill, Import/Export — naming controls exactly as they appear on screen (e.g. the tool-rail labels in `src/components/bench/ToolRail.jsx`). It names only controls that exist in the code at this commit; later UI phases add `New grid`, `Black square`, `Open saved`, and Task 8.1 re-sweeps the names. It does not describe the hidden controls (§3.1: Clues, Heatmap, Suggest Black Square, PDF, `.puz`).
- **Development Mode** says: debug is off by default and `FLASK_DEBUG=1` turns it on; to use a port other than 5000 set the same `PORT` for both terminals (`PORT=<other> python3 run.py` and `PORT=<other> npm run dev`); the Vite server on :3000 proxies to that `PORT`.
- No test counts, timings or status claims are written (`.claude/CLAUDE.md`).

**Verification (no typed values):**
- [ ] **Step 1: Edit `README.md`.**
- [ ] **Step 2: Presence of each pinned phrase:** `git grep -n -F -e 'Before you start' -e 'Using the app' -e 'FLASK_DEBUG=1' -e 'PORT=' -e 'Windows' -e 'python3-venv' -e 'chmod +x setup.sh' -- README.md` — every `-e` must hit (run each separately if the combined output is ambiguous).
- [ ] **Step 3: Doc guard:** `bash scripts/docs-check.sh`, read the result on its own line.
- [ ] **Step 4: Every control name the tour backticks exists in `src/`:** for each name, `git grep -n -F -- '<name>' -- src ':!src/__tests__'`; a miss is a defect in the tour.
- [ ] **Step 5: Commit:**

```bash
git add README.md
git diff --cached --stat
git commit -m "docs(readme): prerequisites, a tour of the tools, and the debug/PORT switches"
```


---

## Phase 2: CLI `fill` — locked letters, pre-flight, result keys (§2.1)

Every task runs from the worktree root `../crossword-helper-novice`. Line numbers below are as of `a72be24`; cite methods by name in code and commits (they shift as tasks land).

**Shared definitions (all Phase 2 and 3 tasks).**
- **Input lock set**: `grid.locked_cells` on a fresh run, read immediately after Task 2.2's resolution and before any solver object touches the grid. On `--resume` it is empty (§2.1 last bullet).
- **Input lock letters**: the mapping `{(row, col): letter}` over the input lock set, captured at the same moment.
- **Cell list**: a list of `[row, col]` pairs, zero-based, unique, sorted row-major (§2.1 C11). Every cell list in a result goes through `cell_list` (Task 2.2).
- **Fixture grids** are passed to `fill` with `--allow-nonstandard`. Fixture word lists are temp files of `WORD;SCORE` lines, the format `WordList.parse_line` accepts. Named lists:

| Name | Lines |
|---|---|
| `L1` | `CAT;50` `COT;50` `CUT;50` `QUA;50` `XIS;50` |
| `L2` | `CRANE;50` `SLATE;50` |
| `L3` | `CARE;50` |
| `L4` | `COT;50` `CAT;50` `ART;50` `AHA;50` `BOA;50` `BIT;50` |
| `L5` | `COD;50` `ALE;50` `BEE;50` `OLE;50` `DEE;50` |
| `L6` | `CAT;50` `ORE;50` `WED;50` `COW;50` `ARE;50` `TED;50` (a 3×3 word square: rows `CAT`/`ORE`/`WED`, columns `COW`/`ARE`/`TED`) |

- **Grid `G33`**: 3×3, all white. **Grid `G44`**: 4×4, black at `(0,0)` and `(3,3)`, all other cells white. Slot-model order (`SlotModel.from_blacks`: across row-major, then down column-major) is, for `G33`: `(0,0,across)`, `(1,0,across)`, `(2,0,across)`, `(0,0,down)`, `(0,1,down)`, `(0,2,down)`; for `G44`: `(0,1,across,3)`, `(1,0,across,4)`, `(2,0,across,4)`, `(3,0,across,3)`, `(1,0,down,3)`, `(0,1,down,4)`, `(0,2,down,4)`, `(0,3,down,3)`.

---

### Task 2.1: Grid lock primitives (§2.1 C12, C10, D3, D2) and the two lock-preserving round trips

**Files:**
- Modify: `cli/src/core/grid.py` (`set_letter`, `set_black_square`, `to_dict`, `from_dict`)
- Modify: `cli/src/fill/autofill.py` (`Autofill.fill_with_restarts`: `original_grid_state = self.grid.to_dict()`)
- Modify: `cli/src/fill/adaptive_autofill.py` (`AdaptiveAutofill.fill`: `original_grid_dict = copy.deepcopy(self.grid.to_dict())`; `_skeleton_grid`: the `or self.grid.to_dict()` fallback)
- Test: `cli/tests/unit/test_grid_locking.py` (extend); `cli/tests/unit/test_autofill.py` (extend, `fill_with_restarts` row)

**Interfaces:**
- Consumes: nothing new.
- Produces: `Grid.to_dict(self, include_locks: bool = False) -> Dict`; `Grid.from_dict` applying `"locked"`; the raising `set_letter` / `set_black_square` that Tasks 2.4, 2.5, 2.7 rely on.

**Contract:**

```python
def to_dict(self, include_locks: bool = False) -> Dict: ...
@classmethod
def from_dict(cls, data: Dict, strict_size: bool = True) -> "Grid": ...   # signature unchanged
def set_letter(self, row: int, col: int, letter: str, lock: bool = False): ...   # unchanged
def set_black_square(self, row: int, col: int, enforce_symmetry: bool = True): ...   # unchanged
```

**Behavioral criteria:**
- `from_dict` applies a `"locked"` key in its own pass **after** every cell is populated; with the key absent `locked_cells` is `set()` (§2.1 C12). Each entry must be a 2-element list of `int` naming an in-bounds cell (`0 <= r, c < size`; a negative index is out of bounds, not Python negative indexing) that holds a letter; anything else raises `ValueError` and the list is never trimmed (§2.1 "the list is never trimmed silently"). Duplicate entries collapse into the set.
- `to_dict()` output is byte-for-byte unchanged (keys `size`, `grid`, `black_squares`, `is_symmetric`; no `"locked"`) (§2.1 C10). `to_dict(include_locks=True)` adds `"locked"`: the cell list of `locked_cells`, `[]` when none.
- `set_letter` raises `ValueError` when `(row, col)` is locked and the uppercased letter differs from the cell's letter; the cell is unchanged. The same letter (any case) on a locked cell succeeds (§2.1 D3, C12 "raises only on a different one").
- `set_black_square` raises `ValueError` when the cell is locked, or when `enforce_symmetry` is true and the 180° partner `(size-1-row, size-1-col)` is locked. It raises before writing either cell. With `enforce_symmetry=False` only the cell itself is checked (§2.1 D2).
- `place_word` and `remove_word` are unchanged (they already honour locks, §2.1 D3).
- Only the two solver round trips pass `include_locks=True` (§2.1 C10): `Autofill.fill_with_restarts` (`original_grid_state`) and `AdaptiveAutofill` (`original_grid_dict` in `fill` and the `_skeleton_grid` fallback). `git grep -n "include_locks=True" -- cli/src` lists those files only. Every other `to_dict` call keeps the default, so `-o` files, pause state (`state_manager.py`, the degenerate save in `fill`), progress snapshots and `nyt_parser.py` carry no locks.
- Docstrings of `to_dict`, `from_dict`, `set_letter`, `set_black_square` cite `novice-readiness spec 0.2.4 §2.1 (C10)` / `(C12)` / `(D3)` / `(D2)`.

**Normative cases** (grid `G33` unless stated; `strict_size=False`):

| # | input | result |
|---|---|---|
| fd1 | `from_dict({"size":3,"grid":[["C","A","T"],[".",".","."],[".",".","."]],"locked":[[0,0],[0,2]]})` | `locked_cells == {(0,0),(0,2)}` |
| fd2 | same grid, `"locked": []` | `locked_cells == set()` |
| fd3 | same grid, no `"locked"` key | `locked_cells == set()` |
| fd4 | `"locked": [[3,0]]` | `ValueError` |
| fd5 | `"locked": [[-1,0]]` | `ValueError` |
| fd6 | `"locked": [[1,1]]` (cell `"."`) | `ValueError` |
| fd7 | grid with `"#"` at `(1,1)`, `"locked": [[1,1]]` | `ValueError` |
| fd8 | `"locked"` is `[[0]]`, `[[0,0,1]]`, `[["0",0]]`, or `"0,0"` | `ValueError` each |
| fd9 | `"locked": [[0,0],[0,0]]` | `locked_cells == {(0,0)}` |
| td1 | `to_dict()` on fd1's grid | keys exactly `size`, `grid`, `black_squares`, `is_symmetric` |
| td2 | `to_dict(include_locks=True)` on fd1's grid | `"locked": [[0,0],[0,2]]` |
| td3 | `to_dict(include_locks=True)` on fd2's grid | `"locked": []` |
| td4 (load-bearing, §2.1) | fd1's grid through `clone()`, and through `from_dict(to_dict(include_locks=True), strict_size=False)` | `locked_cells == {(0,0),(0,2)}` both ways, letters equal |
| sl1 | fd1's grid, `set_letter(0,0,"C")` / `set_letter(0,0,"c")` | succeeds, cell `"C"` |
| sl2 | fd1's grid, `set_letter(0,0,"D")` | `ValueError`; cell still `"C"` |
| sl3 | fd1's grid, `set_letter(1,1,"D")` (unlocked) | succeeds |
| bs1 | fd1's grid, `set_black_square(0,0)` | `ValueError`; `(0,0)` `"C"`, `(2,2)` unchanged |
| bs2 | fd1's grid, `set_black_square(2,0)` (partner `(0,2)` locked) | `ValueError`; `(2,0)` and `(0,2)` unchanged |
| bs3 | fd1's grid, `set_black_square(2,0, enforce_symmetry=False)` | succeeds |
| rt1 | `Autofill.fill_with_restarts(attempts=2, …)` on an 11×11 grid (it rebuilds with `strict_size=True`) with `locked_cells == {(0,0)}` | after the call `autofill.grid.locked_cells == {(0,0)}` |
| rt2 | `AdaptiveAutofill` built over a grid with `locked_cells == {(0,0)}`, after `fill` has set `_original_grid_dict` | `_skeleton_grid().locked_cells == {(0,0)}` |

- [ ] **Step 1: Write the failing tests.** Design them from the contract; cover every row. Extend `test_grid_locking.py`'s `TestCellLocking`; keep its existing `test_from_dict_initializes_empty_locked_cells` (it is row fd3).
- [ ] **Step 2: Run, verify they fail on the missing behaviour.** `pytest cli/tests/unit/test_grid_locking.py cli/tests/unit/test_autofill.py -v`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the CLI suite alone.** `pytest cli/tests -v`. A pre-existing test that sets a different letter on a locked cell, or blacks out a locked cell, encodes the behaviour D3/D2 forbid: change the test to the new rule and say so in the commit body.
- [ ] **Step 5: Commit.**

```bash
git add cli/src/core/grid.py cli/src/fill/autofill.py cli/src/fill/adaptive_autofill.py cli/tests/unit/test_grid_locking.py cli/tests/unit/test_autofill.py
git diff --cached --stat
git commit -m "feat(grid): locked cells survive to_dict/from_dict round trips and refuse overwrites"
```

---

### Task 2.2: `fill --lock-filled/--no-lock-filled` and the lock-set resolution (§2.1, P1)

**Files:**
- Create: `cli/src/fill/locked_letters.py`
- Modify: `cli/src/cli.py` (`fill`: new option; the fresh-load branch `grid = Grid.from_dict(data, strict_size=not allow_nonstandard)`)
- Modify: `docs/specs/CLI_SPEC.md` (`fill` options table; **Grid File Format**: the optional `"locked"` key)
- Test: `cli/tests/unit/test_locked_letters.py` (create); `cli/tests/unit/test_fill_command.py` (extend)

**Interfaces:**
- Consumes: Task 2.1's `from_dict` (`"locked"`).
- Produces (in `cli/src/fill/locked_letters.py`):

```python
from typing import Dict, Iterable, List, Mapping, Tuple

def cell_list(cells: Iterable[Tuple[int, int]]) -> List[List[int]]: ...
def apply_lock_mode(grid: Grid, grid_data: Mapping, lock_filled: bool) -> None: ...
def input_lock_letters(grid: Grid) -> Dict[Tuple[int, int], str]: ...
```

`fill` gains the parameter `lock_filled: bool` from `@click.option("--lock-filled/--no-lock-filled", default=True)`.

**Behavioral criteria:**
- `cell_list` returns unique `[row, col]` pairs sorted row-major (§2.1 C11).
- `apply_lock_mode` (§2.1 C12): `lock_filled` and `"locked" in grid_data` → leaves `from_dict`'s set as is; `lock_filled` and no key → `locked_cells` = every cell holding a letter; not `lock_filled` → `locked_cells = set()`, with or without the key.
- `input_lock_letters` returns `{(r, c): letter}` for every cell in `grid.locked_cells`.
- In `fill`, `apply_lock_mode` runs on the fresh branch only, immediately after `Grid.from_dict`; the input lock letters are captured right after it. On `--resume`, neither runs and the input lock letters are `{}` (§2.1 last bullet: neither `--lock-filled` nor a `"locked"` key applies).
- A `ValueError` from the fresh-branch `Grid.from_dict` goes through `_fail_fill(str(e), json_output)` (exit 1) (§2.1 "fails the run through `_fail_fill`"). That call also raises for the grid shape errors it raised before. They now reach the same `_fail_fill` shape instead of a traceback, with the same exit 1. The `"locked"` key is validated by `from_dict` before `--no-lock-filled` empties the set, so an invalid list exits 1 under `--no-lock-filled` too (C12 ordering).
- `--theme-entries` handling is unchanged (§2.1: theme entries are locked by beam, repair and hybrid as today).
- `docs/specs/CLI_SPEC.md` documents the option, its default and the `"locked"` key in the words of §2.1's first bullet.

**Normative cases.** `apply_lock_mode` on `G33` with `C` at `(0,0)` and `A` at `(1,1)`:

| `grid_data` `"locked"` | `lock_filled` | `locked_cells` |
|---|---|---|
| `[[0,0]]` | `True` | `{(0,0)}` |
| `[]` | `True` | `set()` |
| absent | `True` | `{(0,0),(1,1)}` |
| absent | `False` | `set()` |
| `[[0,0]]` | `False` | `set()` |

`cell_list([(2,1),(0,2),(2,1),(0,0)])` → `[[0,0],[0,2],[2,1]]`.

`fill` subprocess rows (`python -m cli.src.cli fill <grid> -w <L1> --allow-nonstandard --json-output`):

| grid file | flags | exit | stdout JSON |
|---|---|---|---|
| `G33`, `C` at `(0,0)`, `"locked": [[5,5]]` | — | 1 | `success: false`, has `error`, no `blocked` key |
| same, `"locked": [[2,2]]` (empty cell) | — | 1 | as above |
| same, `"locked": [[5,5]]` | `--no-lock-filled` | 1 | as above |

- [ ] **Step 1: Write the failing tests** for every row above, plus one in-process test that `fill --resume` never calls `apply_lock_mode`. Use a monkeypatch that raises, and the existing pause/resume fixtures in `cli/tests/unit/test_pause_resume_regressions.py` for a state file.
- [ ] **Step 2: Run, verify failure.** `pytest cli/tests/unit/test_locked_letters.py cli/tests/unit/test_fill_command.py -v`
- [ ] **Step 3: Implement.** Module docstring cites `novice-readiness spec 0.2.4 §2.1 (C12)`.
- [ ] **Step 4: Run.** `pytest cli/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add cli/src/fill/locked_letters.py cli/src/cli.py docs/specs/CLI_SPEC.md cli/tests/unit/test_locked_letters.py cli/tests/unit/test_fill_command.py
git diff --cached --stat
git commit -m "feat(fill): --lock-filled/--no-lock-filled and the grid file's locked key"
```

---

### Task 2.3: Pause markers cleared on every early exit (§2.1 C6)

**Files:**
- Modify: `cli/src/cli.py` (`fill`: the `try`/`finally` around `_run_fill`; the `empty_slots` early return)
- Test: `cli/tests/unit/test_pause_resume_regressions.py` (extend)

**Interfaces:** Consumes nothing new. Produces the `try` block that Task 2.9's blocked return and Task 2.8's postcondition sit inside.

**Behavioral criteria:**
- The `try` whose `finally:` runs `pause_controller.clear_running()` and the conditional `clear_pause()` starts immediately after `pause_controller.mark_running()` and ends where the current one ends, after `_run_fill` and its `except ValueError` (§2.1 C6). The `finally` body and its `result is None or not result.paused` condition are unchanged. The DD6 paused block still runs after the `finally`, as its comment requires.
- The `empty_slots` early return's own `clear_running()`/`clear_pause()` calls are removed, because the `finally` now covers that return (C6 "one cleanup covers all of them and the `empty_slots` early return").
- After each exit listed below, no `crossword_running_<id>.pid`, `crossword_searching_<id>.flag` or `crossword_pause_<id>.flag` remains in `--pause-flag-dir` (the `PauseController` file names).

**Normative cases.** Every row runs `fill` with `--task-id t1 --pause-flag-dir <tmp> --state-dir <tmp2> --json-output --allow-nonstandard`, on an empty `G33` with list `L1` unless the row says otherwise:

| early exit (§2.1 C6) | how to reach it | exit |
|---|---|---|
| theme-entries JSON error `return` | `--theme-entries` file containing `{not json` | 0 (unchanged) |
| word-list open error `_fail_fill` | `-w` names a directory | 1 |
| invalid theme entries `_fail_fill` | theme entry `{"(0,0,across)": "TOOLONG"}` on `G33` | 1 |
| solver `ValueError` → `_fail_fill` | `--algorithm repair --timeout 5` | 1 |
| `empty_slots` early return | a fully lettered `G33` | 0 |

The blocked return's row is added in Task 2.9.

- [ ] **Step 1: Write the failing tests.** Every row above, asserting that no marker file remains.
- [ ] **Step 2: Run, verify the leaking rows fail.** `pytest cli/tests/unit/test_pause_resume_regressions.py -v`
- [ ] **Step 3: Implement.** Comment at the `try` cites `novice-readiness spec 0.2.4 §2.1 (C6)`.
- [ ] **Step 4: Run.** `pytest cli/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add cli/src/cli.py cli/tests/unit/test_pause_resume_regressions.py
git diff --cached --stat
git commit -m "fix(fill): pause markers are cleared on every exit after mark_running"
```

---

### Task 2.4: Every direct `Grid.cells` writer in `IterativeRepair` skips or restores locked cells (§2.1 D3)

**Files:**
- Modify: `cli/src/fill/iterative_repair.py` (`_backtrack_region`, `_would_create_gibberish`, and a classification comment at each writer)
- Test: `cli/tests/unit/test_iterative_repair.py` (extend)

**Interfaces:** Consumes Task 2.1. Produces nothing new.

**Classification (§2.1 D3; Phase 0.1's list).** Each writer either skips locked cells, or restores a copy taken while the locked cells held their input letters. The second class holds by induction once every writer of the first class skips locked cells and `place_word`/`set_letter` refuse a different letter (Task 2.1):

| line @ `a72be24` | method | write | class | change |
|---|---|---|---|---|
| 243 | `fill` | `cells[:] = best_grid` | restores (copy at the `best_grid = self.grid.cells.copy()` after an attempt) | comment only |
| 247 | `fill` | `cells[:] = original_grid` | restores (copy taken after theme placement, before any solver write) | comment only |
| 281 | `fill` | `cells[:] = best_grid` | restores | comment only |
| 334 | `_region_fill_attempt` | `cells[pos] = 0` | skips (`if pos not in self.grid.locked_cells`) | comment only |
| 500 | `_repair_invalid_words` | `cells[:] = best_grid` | restores (copies at method entry and on each improvement) | comment only |
| 686 | `_csp_backtrack` | `cells[pos] = val` | restores `saved_cells` taken before `place_word` | comment only |
| 1192, 1206 | `_try_repair_slot` | `cells[pos] = val` | restores `saved_cells` | comment only |
| 1360 | `_backtrack_region` | `cells[pos] = ord(ch) - ord("A") + 1` | **neither today** | skip locked cells |
| 1390, 1401 | `_backtrack_region` | `cells[pos] = val` | restores `saved_cells` | comment only |
| 1435 | `_would_create_gibberish` | `cells[pos] = ord(ch) - ord("A") + 1` | **neither today** | skip locked cells |
| 1503 | `_would_create_gibberish` | `cells[pos] = val` | restores `original_cells` | comment only |
| 1661 | `cleanup_grid` | `cells[pos] = 0` | skips (`if pos in self.grid.locked_cells: continue`) | comment only |

`_backtrack_region` has no caller in `cli/src` other than its own recursion (`git grep -n "_backtrack_region" -- cli/src`). It still gets the skip, because D3 covers every writer.

**Behavioral criteria:**
- `_backtrack_region` and `_would_create_gibberish` never write a locked cell; a trial word disagreeing with a locked letter leaves that cell's letter in place (§2.1 D3).
- Each row's line carries a one-line comment naming its class and citing `novice-readiness spec 0.2.4 §2.1 (D3)`.
- Positive control: `ast-grep run -p '$G.cells[$$$] = $V' -l python cli/src` still lists `grid.py`'s `set_letter` write, and every hit outside `cli/src/core/grid.py` is a row of the table (by method). A new hit is a new writer and must be classified before the task lands.

**Normative cases** (`G33`, `(0,0)` locked `C`):

| call | observation | expected |
|---|---|---|
| `_would_create_gibberish("DOG", slot (0,0,across), …)` | `(0,0)` during every `pattern_matcher.find` call (a recording matcher), and after return | `"C"` throughout |
| `_backtrack_region([slot (0,0,across)], 0, set(), …)` with a matcher returning `[("DOG", 50)]` | `(0,0)` throughout and after return | `"C"` throughout |
| `IterativeRepair(...).fill(timeout=10)` on `G33` with `(0,0)` locked `C`, list `L6` | `(0,0)` at every `find` call of a recording matcher wrapping the real `TriePatternMatcher` | `"C"` at every call |

- [ ] **Step 1: Write the failing tests** (the first two rows fail on `main`).
- [ ] **Step 2: Run, verify failure.** `pytest cli/tests/unit/test_iterative_repair.py -v`
- [ ] **Step 3: Implement the two skips and the comments.**
- [ ] **Step 4: Run the positive control and the suite.** `ast-grep run -p '$G.cells[$$$] = $V' -l python cli/src`, then `pytest cli/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add cli/src/fill/iterative_repair.py cli/tests/unit/test_iterative_repair.py
git diff --cached --stat
git commit -m "fix(repair): trial writes skip locked cells; classify every direct cells writer"
```

---

### Task 2.5: A placement that conflicts with a lock fails that placement at the three bare sites (§2.1 C13)

**Files:**
- Modify: `cli/src/fill/autofill.py` (`Autofill._backtrack`, `Autofill._backtrack_with_mac`: their `self.grid.place_word(word, …)`)
- Modify: `cli/src/fill/iterative_repair.py` (`IterativeRepair._repair_invalid_words`: `self.grid.place_word(best_word, …)`)
- Test: `cli/tests/unit/test_autofill_regressions.py` (extend); `cli/tests/unit/test_iterative_repair.py` (extend)

**Interfaces:** Consumes Task 2.1. Produces nothing new.

**Behavioral criteria (§2.1 C13):**
- In `_backtrack` and `_backtrack_with_mac`, a `ValueError` from `place_word` for a candidate is treated as a failed placement. The grid is unchanged, the word is not added to `used_words`, `remove_word` is not called, the domains are not saved or restored, and the loop moves to the next candidate. No `ValueError` leaves the method for this reason.
- In `_repair_invalid_words`, a `ValueError` from `place_word(best_word, …)` is handled as if `_try_repair_slot` had returned `(False, None)`. The swap is not applied, no tabu entry is added for it, `conflicts` is not recomputed, and the loop continues.
- A lock-conflict failed placement does not fire `on_backtrack` (planning default `PD-2-C13` (spec §8): "No, as for a `used_words` skip"); no `slot_key` is reported for it.
- Beam search and repair's CSP path already catch the error; they are untouched.

**Normative cases** (`G33`, `(0,0)` locked `C`):

| site | setup | expected |
|---|---|---|
| `Autofill._backtrack` | driven through `Autofill.fill(use_mac=False)` (which runs `_initialize_csp`); `_get_candidates` patched so slot `(0,0,across)` yields `[("DOG",50),("CAT",50)]`; list allows a fill with `CAT` | no exception; `(0,0)` `"C"`; `CAT` placed |
| `Autofill._backtrack_with_mac` | same, through `Autofill.fill(use_mac=True)` | same |
| `on_backtrack` (`PD-2-C13`) | the two `Autofill` rows above, with `on_backtrack` set to a recording callable | the recorded calls are empty: the rejected `DOG` fires nothing and `CAT` succeeds without any other backtrack |
| `IterativeRepair._repair_invalid_words` | called directly on a grid with at least one conflict (an off-list unlocked word in row 1), `_intersection_cache` built for `all_slots` exactly as `fill` builds it; `_try_repair_slot` stubbed to return `(True, "DOG")` once for slot `(0,0,across)` | no exception; `(0,0)` `"C"`; `"DOG"` never in the grid |

- [ ] **Step 1: Write the failing tests** (each raises on `main`).
- [ ] **Step 2: Run, verify failure.** `pytest cli/tests/unit/test_autofill_regressions.py cli/tests/unit/test_iterative_repair.py -v`
- [ ] **Step 3: Implement.** Each handler cites `novice-readiness spec 0.2.4 §2.1 (C13)`.
- [ ] **Step 4: Run.** `pytest cli/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add cli/src/fill/autofill.py cli/src/fill/iterative_repair.py cli/tests/unit/test_autofill_regressions.py cli/tests/unit/test_iterative_repair.py
git diff --cached --stat
git commit -m "fix(fill): a locked-letter conflict fails the placement, not the run"
```

---

### Task 2.6: A fully locked slot is valid in `IterativeRepair` (§2.1 B1, G13, #74)

**Files:**
- Modify: `cli/src/fill/iterative_repair.py` (`_find_conflicts` STEP 2; `_forward_check`)
- Test: `cli/tests/unit/test_iterative_repair.py` (extend; the #74 regression is named `test_issue_74_*`)

**Interfaces:** Consumes `_slot_fully_locked` (existing). Produces nothing new.

**Behavioral criteria (§2.1 B1):**
- Every row builds `IterativeRepair` with `all_valid_words` = the list's words, as `fill` does (`_validation_words`). Rows that call `_forward_check` (lk3–lk6) first build `_intersection_cache` for `all_slots` exactly as `fill` does. `__init__` never sets it, and an empty cache skips every crossing, so the row would pass vacuously on `main`.
- `_find_conflicts` adds no invalid-word pseudo-conflict for a slot whose every cell is locked, in the grid passed to it, whatever its list membership or score.
- `_forward_check` does not call `find` for a fully filled crossing slot that is fully locked; that crossing never makes it return `False`.
- A fully filled crossing slot that is **not** fully locked is judged as today (`find` at `self.min_score`).
- This covers a typed off-list word, a typed listed word below `--min-score`, and a theme entry placed by `IterativeRepair.fill` with `lock=True` (#74). `autofill.py`'s `_forward_check` already skips filled crossings (`if "?" not in pattern: continue`) and is not changed.

**Normative cases** (`G33`; "CAB locked" means row 0 holds `C`,`A`,`B` with all three cells locked; `min_score=30`):

| # | setup | call | expected |
|---|---|---|---|
| lk1 | CAB locked, rows 1–2 `OLE`/`DEE`, list `L5` (no `CAB`) | `_find_conflicts(grid, all_slots)` | no conflict with `slot1_id == slot2_id == (0,0,"across")` |
| lk2 | CAB locked, list `L5` plus `CAB;10` | `_find_conflicts` | as lk1 |
| lk3 | CAB locked, `COD` just placed down at `(0,0)`, list `L5` | `_forward_check(slot (0,0,down), all_slots, used)` | `True` |
| lk4 (#74) | `theme_entries={(0,0,"across"): "CAB"}` placed by `fill`'s theme loop, `COD` placed down at `(0,0)`, list `L5` | `_forward_check` | `True` (`False` on `main`) |
| lk5 (#74) | as lk4, list `L5` plus `CAB;10` | `_forward_check` | `True` (`False` on `main`) |
| lk6 | row 0 holds `CAB` with **no** cell locked, `COD` placed down at `(0,0)`, list `L5` | `_forward_check` | `False` (unchanged) |
| lk7 | `IterativeRepair(G33, L5, TriePatternMatcher, min_score=30, theme_entries={(0,0,"across"): "CAB"}).fill(timeout=10)` | result | `success is True`; grid rows `CAB`, `OLE`, `DEE` |
| lk8 | `G33` with CAB locked (typed, no theme entry), list `L5`, `fill(timeout=10)` | result | `success is True`; `problematic_slots == []` (on `main` `(0,0,across)` is `invalid_word`) |

- [ ] **Step 1: Write the failing tests.** lk4 and lk5 are #74's regression. Each must fail at its own assertion on `main` (CONTRIBUTING §3 mutation rule).
- [ ] **Step 2: Run, verify failure.** `pytest cli/tests/unit/test_iterative_repair.py -v`
- [ ] **Step 3: Implement.** Comments cite `novice-readiness spec 0.2.4 §2.1 (B1)` and `#74`.
- [ ] **Step 4: Run.** `pytest cli/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add cli/src/fill/iterative_repair.py cli/tests/unit/test_iterative_repair.py
git diff --cached --stat
git commit -m "fix(repair): a fully locked slot is valid regardless of list or score (#74)"
```

---

### Task 2.7: Adaptive mode never blacks out a locked letter (§2.1 D2)

**Files:**
- Modify: `cli/src/fill/adaptive_autofill.py` (`_try_adapt`, between `suggest_placements` and `_apply_black_square`)
- Test: `backend/tests/integration/test_adaptive_on_backtrack.py` (extend). It already imports `AdaptiveAutofill` with the backend suggester on the path.

**Interfaces:** Consumes Task 2.1's raising `set_black_square` (defence in depth) and the lock-carrying `_skeleton_grid`. Produces nothing new.

**Behavioral criteria (§2.1 D2):**
- `_try_adapt` drops every suggestion whose cell or 180° partner (`suggestion["symmetric_position"]`) is in the grid's `locked_cells` or holds a letter in `_skeleton_grid()` (see planning default `PD-2-D2` (spec §8)). The best remaining suggestion is applied; with none remaining, `_try_adapt` returns `False` exactly as the existing "No valid black square suggestions" branch does.
- `_apply_black_square` is never reached with a locked cell or partner.

**Normative cases** (11×11 grid, `(0,0)` locked `C`, so its partner is `(10,10)`; the suggester is stubbed to return the listed suggestions in order):

| suggestions returned | applied | `_try_adapt` |
|---|---|---|
| `[(0,0)]` | none | `False` |
| `[(10,10)]` (partner `(0,0)` locked) | none | `False` |
| `[(0,0), (10,10), (5,3)]` | `(5,3)` and partner `(5,7)` | `True` |
| `[(2,2)]` where `(2,2)` holds an unlocked letter in the skeleton grid | none | `False` |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run, verify failure.** `pytest backend/tests/integration/test_adaptive_on_backtrack.py -v`
- [ ] **Step 3: Implement.** Cite `novice-readiness spec 0.2.4 §2.1 (D2)`.
- [ ] **Step 4: Run.** `pytest backend/tests/integration/test_adaptive_on_backtrack.py cli/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add cli/src/fill/adaptive_autofill.py backend/tests/integration/test_adaptive_on_backtrack.py
git diff --cached --stat
git commit -m "fix(adaptive): drop black-square suggestions on locked or lettered cells"
```

---

### Task 2.8: End-to-end postcondition in `fill` (§2.1 "End-to-end postcondition")

**Files:**
- Modify: `cli/src/fill/locked_letters.py`; `cli/src/cli.py` (`fill`)
- Test: `cli/tests/unit/test_locked_letters.py` (extend); `cli/tests/unit/test_fill_command.py` (extend)

**Interfaces:**
- Consumes: `input_lock_letters` (Task 2.2), `cell_list`.
- Produces:

```python
POSTCONDITION_MESSAGE = "Autofill changed a locked letter; nothing was written."
def changed_locked_cells(grid: Grid, expected: Mapping[Tuple[int, int], str]) -> List[List[int]]: ...
```

**Behavioral criteria:**
- `changed_locked_cells` returns the cell list of every `(r, c)` in `expected` whose cell in `grid` does not hold `expected[(r, c)]`, whether the cell is empty, black or a different letter.
- `fill` checks the final grid against the input lock letters at two points (§2.1: "before a grid leaves `fill` (the stdout result, the paused payload, the `-o` file)"): (a) after the `try`/`finally` and before the DD6 paused block (`result.grid`, or `grid` when `result is None`); (b) after the `--cleanup` pass and before the first completion `progress.update`, the `-o` write and the stdout JSON.
- On a mismatch: `_fail_fill(POSTCONDITION_MESSAGE, json_output)` (exit 1). No `-o` file is written. In human mode the input grid file is not overwritten. No paused state file, paused event or paused payload is emitted.
- On a mismatch the pause markers are cleared before `_fail_fill`, including when the result is paused (planning default `PD-2-C6P` (spec §8): "Also clears the pause markers (one `finally`)"). Today's `finally` calls `clear_pause()` only when `result is None or not result.paused`, so the paused-result path must be covered by the same single cleanup. The markers are those of `cli/src/fill/pause_controller.py`: `crossword_pause_<task_id>.flag`, `crossword_running_<task_id>.pid` and `crossword_searching_<task_id>.flag`.
- With `--json-output` the stdout object is `_fail_fill`'s `{"success": false, "error": "Autofill changed a locked letter; nothing was written."}`. `run_cli_with_progress` (Task 3.3, planning default `PD-3-KILL` (spec §8)) turns it into an `error` event whose message is that `error` string verbatim.

**Normative cases:**

| # | case | expected |
|---|---|---|
| pc1 | `changed_locked_cells(grid with (0,0)="C", {(0,0):"C"})` | `[]` |
| pc2 | `(0,0)="D"` | `[[0,0]]` |
| pc3 | `(0,0)` empty | `[[0,0]]` |
| pc4 | `(0,0)` black | `[[0,0]]` |
| pc5 | `expected == {}` | `[]` |
| pc6 (§2.1 test 1) | in-process `fill` (Click `CliRunner`) on `G33` with `C` at `(0,0)`, key absent, `-o <tmp>/out.json --json-output`; the repair solver is stubbed to return a `FillResult` whose grid has `D` at `(0,0)` | exit 1; stdout `error` = the message; `out.json` does not exist |
| pc7 | pc6 in human mode with no `-o` | exit 1; the input file's bytes are unchanged |
| pc8 (`PD-2-C6P`) | pc6 with `--task-id t1 --state-dir <tmp> --pause-flag-dir <tmp2>` and a stub result with `paused=True` (the stub touches `crossword_pause_t1.flag` in `<tmp2>` before returning) | exit 1; no state file in `<tmp>`; no `paused` payload on stdout; no `crossword_pause_t1.flag` and no `crossword_running_t1.pid` remains in `<tmp2>` |
| pc9 (§2.1 test 2) | subprocess `fill` on `G33` with `C` at `(0,0)`, list `L6`, `--json-output --timeout 10`, once per `--algorithm` in `regex`, `trie`, `beam`, `repair`, `hybrid` (`hybrid` with `--timeout 30`), and once with `--adaptive` (default algorithm) | exit ≠ 1; final `grid[0][0] == "C"` |

- [ ] **Step 1: Write the failing tests** (pc6–pc8 fail on `main`). If pc9's six runs make the file slow, mark that test `@pytest.mark.slow` and confirm the slow job collects it (`pytest -m slow --collect-only -q cli/tests/unit/test_fill_command.py`).
- [ ] **Step 2: Run, verify failure.** `pytest cli/tests/unit/test_locked_letters.py cli/tests/unit/test_fill_command.py -v`
- [ ] **Step 3: Implement.** Cite `novice-readiness spec 0.2.4 §2.1 (D3)` at the check.
- [ ] **Step 4: Run the CLI suites alone.** `pytest cli/tests -v`, then `pytest -m slow cli/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add cli/src/fill/locked_letters.py cli/src/cli.py cli/tests/unit/test_locked_letters.py cli/tests/unit/test_fill_command.py
git diff --cached --stat
git commit -m "feat(fill): fail closed when a locked letter changed; write nothing"
```

---

### Task 2.9: Pre-flight: dead slots, case 1, B2, case 2 and the blocked result, exit 3 (§2.1 Pre-flight, C1, C4, C9, M2, B2)

**Files:**
- Modify: `cli/src/domain/fillability.py`, `cli/src/domain/letter_bitset.py`, `cli/src/domain/propagator.py`, `cli/src/domain/slot_model.py`, `cli/src/domain/wordorder.py`: absolute `from src.…` imports become relative (C9; see the decision below)
- Modify: `cli/src/fill/locked_letters.py`; `cli/src/cli.py` (`fill`, after the `empty_slots` early return and before `_run_fill`)
- Modify: `cli/tests/unit/test_fill_command.py`: its module docstring's exit-code contract gains `exit 3 - blocked by pre-flight; stdout JSON carries "blocked": true` (the docstring is a testable claim); `docs/specs/CLI_SPEC.md` (`fill` **Exit codes** table and the blocked output)
- Test: `cli/tests/unit/test_locked_letters.py`, `cli/tests/unit/test_fill_command.py`, `cli/tests/unit/test_pause_resume_regressions.py` (extend)

**Plan decision (C9's two options):** relative imports in `cli/src/domain/` (`from .letter_bitset import …`, `from ..core.grid import Grid`, `from ..fill.word_list import …`), not the `sys.path` bootstrap. Why: the bootstrap would load `src.core.grid` beside `cli.src.core.grid`, two distinct `Grid`/`WordList` classes in one process. Relative imports resolve under `python -m cli.src.cli`, under `cli/crossword` (`from src.cli import cli`), and under the existing tests' `from src.domain…` imports. Check: `git grep -n "from src\." -- cli/src/domain` returns nothing, and the control `git grep -n "from \." -- cli/src/domain` returns the new imports.

**Interfaces:**
- Consumes: `cell_list`, the input lock set, `SlotModel.from_grid`, `fixed_from_grid`, `pattern`, `LetterBitsetIndex.from_word_list`, `count_matches`, `assess`.
- Produces (in `locked_letters.py`):

```python
from typing import Dict, List, NamedTuple, Optional, Sequence

OFF_LIST_WARNING_PREFIX = "Typed words not in the selected word lists: "

class PreflightResult(NamedTuple):
    reason: Optional[str]                 # None, "no_word_fits" or "no_word_of_length"
    blocked_cells: List[List[int]]
    blocked_slots: List[Dict[str, object]]  # {"row", "col", "direction", "length", "pattern"}
    off_list_cells: List[List[int]]
    off_list_words: List[str]             # slot-model order
    index: LetterBitsetIndex

def preflight(grid: Grid, word_list: WordList) -> PreflightResult: ...
def off_list_warning(words: Sequence[str]) -> str: ...      # prefix + ", ".join(words)
def blocked_text_lines(result: PreflightResult) -> List[str]: ...
```

- Produces (stderr event, consumed by Task 3.3 and Phase 5): status `running`, `data == {"off_list_cells": [[r, c], …], "warning": "<off_list_warning text>"}` (key `"warning"`, a string: the C4 key, Cross-phase pins).

**Behavioral criteria:**
- `preflight` follows §2.1's procedure verbatim. `model = SlotModel.from_grid(grid)`, `index = LetterBitsetIndex.from_word_list(word_list)`, `g = grid.clone(); g.clear_unlocked()`, `fixed = fixed_from_grid(g)`, `report = assess(model, index, fixed, min_score=0)`. It never mutates `grid`.
- A **dead slot** is a slot whose `pattern(model, s.id, fixed)` contains `?` and `index.count_matches(that_pattern, min_score=0) == 0`; `min_score=0` is passed explicitly (`count_matches` defaults to 30). `report.wiped_slots` is never used for red cells (C1).
- **Length block (planning default `PD-2-PREC` (spec §8), option (b)):** a dead slot of length `n` is a *length block* when `index.count_matches("?" * n, min_score=0) == 0` (no word of its length in the lists). A length block goes to B2 with no red cell **whether or not it holds a locked letter**; only the remaining dead slots go to case 1.
- **Case 1:** some dead slot that is not a length block contains a locked cell. Then `reason="no_word_fits"`, `blocked_slots` = every dead slot in slot-model order as `{"row", "col", "direction", "length", "pattern"}`, and `blocked_cells` = the cell list of locked cells inside the dead slots that are not length blocks.
- **B2:** dead slots exist and no dead slot that is not a length block contains a locked cell. Then `reason="no_word_of_length"`, the same `blocked_slots`, and `blocked_cells == []`. This runs whatever the lock set, including an empty one (M2, P8).
- No dead slot (including `report.refuted` with no dead slot, P10): `reason=None` and the run proceeds.
- **Case 2:** `off_list_cells` = the cell list of every cell of every slot in `report.off_list_fixed`, and `off_list_words` = those slots' words in that order. With an empty lock set both are `[]` (the fixed letters are none).
- `fill` runs `preflight` on fresh runs only (never `--resume`), after the `empty_slots` early return and before `_run_fill`, inside Task 2.3's `try`.
- **Blocked** (`reason` not `None`), `--json-output`: stdout is exactly one JSON object with exactly these keys: `{"success": false, "blocked": true, "reason": …, "blocked_cells": …, "blocked_slots": …, "off_list_cells": …, "stuck_cells": [], "grid": grid.to_dict()["grid"]}`. Exit code **3**. No solver runs. Pause markers are cleared by Task 2.3's `finally`.
- **Blocked**, text mode: `blocked_text_lines` lines, one per output line. For `no_word_fits`, one line per `blocked_slots` entry: `Blocked: no word fits <pattern> at <row>,<col> <direction>`. For `no_word_of_length`, one line per distinct length: `Blocked: the selected word lists have no words of length <n>`. Exit 3. (Planning default `PD-2-OUT` (spec §8): stdout; length lines in ascending length; no `-o` file and no input-file write on a block.)
- **Case 2 and not blocked:** `warnings` gains `off_list_warning(off_list_words)`. With `--json-output`, one stderr progress event is emitted before `_run_fill`: status `running`, message = the warning text, `data` as above (C4). In text mode the warning is echoed as `Warning: <text>`, like the other warnings.
- C9: `python -m cli.src.cli fill …` from the repo root imports and runs pre-flight with no `ModuleNotFoundError`.

**Normative cases** (`--json-output --allow-nonstandard`, default `--lock-filled`, no `"locked"` key unless stated):

| # | grid | list | expected |
|---|---|---|---|
| PF1 (case 1, C1) | `G33`, `Q` `(0,0)`, `X` `(0,1)` | `L1` | exit 3; `reason "no_word_fits"`; `blocked_slots [{"row":0,"col":0,"direction":"across","length":3,"pattern":"QX?"}]`; `blocked_cells [[0,0],[0,1]]`; `off_list_cells []`; `stuck_cells []`; `grid [["Q","X","."],[".",".","."],[".",".","."]]` |
| PF2 | PF1 in text mode | `L1` | exit 3; stdout holds the line `Blocked: no word fits QX? at 0,0 across` |
| PF3 (unlocked letters take no part) | PF1's grid with `"locked": []` | `L1` | not blocked (exit ≠ 3) |
| PF4 | PF1's grid with `"locked": [[0,0]]` | `L1` | not blocked (`Q??` matches `QUA`) |
| PF5 (B2) | `G33` empty | `L2` | exit 3; `reason "no_word_of_length"`; `blocked_cells []`; `blocked_slots` = the six `G33` slots in slot-model order, each `"pattern":"???"`, `"length":3` |
| PF6 | PF5 in text mode | `L2` | exactly one line `Blocked: the selected word lists have no words of length 3` |
| PF7 (B2 with a typed letter, M2) | `G44` with `A` at `(1,1)` | `L3` | exit 3; `reason "no_word_of_length"`; `blocked_cells []`; `blocked_slots` = `(0,1,across,3)`, `(3,0,across,3)`, `(1,0,down,3)`, `(0,3,down,3)`, each `"???"` |
| PF8 (M2) | `G44` empty | `L3` | identical JSON to PF7 except `grid` |
| PF9 (B2, empty lock set) | PF5's grid plus `C` at `(0,0)`, `--no-lock-filled` | `L2` | as PF5 except `grid` |
| PF10 (case 2) | `G33`, row 0 `C A B` | `L5` | exit ≠ 3; result `warnings` contains `Typed words not in the selected word lists: CAB`; stderr has one `running` event with `data == {"off_list_cells": [[0,0],[0,1],[0,2]], "warning": "Typed words not in the selected word lists: CAB"}` |
| PF11 | `G33`, row 0 `C A B`, row 2 `T A T` | `L4` | warning text `Typed words not in the selected word lists: CAB, TAT` |
| PF12 | PF10 with `--no-lock-filled` | `L5` | no such warning; no such event |
| PF13 (P10) | `G33` empty (no letters, no locks); the test asserts both preconditions, `assess(model, index, fixed, min_score=0).refuted is True` and `index.count_matches(pattern, min_score=0) == 1` for each of the six slots (no slot dead) | list of exactly one word, `ABA` (score 50). Measured read-only: `refuted == True`, `wiped_slots == (0, 1, 2, 3, 4, 5)`, six counts of 1. Only the arc-consistency cascade finds the refutation: every row must be `ABA`, so every column is `AAA`/`BBB`/`AAA` | not blocked (the run proceeds) |
| PF14 (C6) | PF1 with `--task-id t1 --pause-flag-dir <tmp>` | `L1` | exit 3; no marker files remain |
| PF15 (C9) | `data/grids/example_15x15.json` copied to a temp dir with `Q` and `X` in the first two cells of row 0's first slot; README argv: `python -m cli.src.cli fill <copy> -w data/wordlists/comprehensive.txt -t 180 --min-score 30 -o <tmp>/filled.json`, cwd = repo root | `comprehensive` | exit 3; stdout has a `Blocked: no word fits QX` line; stderr has no `ModuleNotFoundError` (comprehensive has no word starting `QX`: `grep -ciE '^qx' data/wordlists/comprehensive.txt` prints `0`) |
| PF16 | `preflight` on a `--resume` run | — | never called |
| PF17 (B2, length block holding a locked letter, `PD-2-PREC`) | `G33`, `Q` at `(0,0)`, default `--lock-filled` | `L2` | exit 3; `"reason": "no_word_of_length"`; `"blocked_cells": []`; `blocked_slots` = the six `G33` slots, each `"length":3`, the two through `(0,0)` with `"pattern":"Q??"` |
| PF18 (`PD-2-OUT`) | PF1 with `-o <tmp>/out.json`, once in `--json-output` and once in text mode | `L1` | exit 3; `<tmp>/out.json` does not exist; the input grid file's bytes are unchanged |

- [ ] **Step 1: Write the failing tests** for every row. PF15 is the test §2.1 C9 names. It blocks before the solver, so it stays in the default suite.
- [ ] **Step 2: Run, verify failure.** `pytest cli/tests/unit/test_locked_letters.py cli/tests/unit/test_fill_command.py cli/tests/unit/test_pause_resume_regressions.py -v`
- [ ] **Step 3: Implement, imports first.** Run `pytest cli/tests/unit/test_fillability.py cli/tests/unit/test_letter_bitset.py cli/tests/unit/test_propagator.py cli/tests/unit/test_slot_model.py cli/tests/unit/test_wordorder.py -v` green after the import change, before writing `preflight`.
- [ ] **Step 4: Run.** `pytest cli/tests -v`
- [ ] **Step 5: STOP gate: pre-flight latency (§2.1).** Run alone, nothing else executing:

```bash
for size in 15 21; do for wl in data/wordlists/comprehensive.txt data/wordlists/raw/comprehensive_scored.txt; do
python - "$size" "$wl" <<'EOF'
import json, sys, time
from cli.src.core.grid import Grid
from cli.src.fill.locked_letters import preflight
from cli.src.fill.word_list import WordList
size, wl = sys.argv[1], sys.argv[2]
g = Grid.from_dict(json.load(open(f"data/grids/example_{size}x{size}.json")))
r, c = next((r, c) for r in range(g.size) for c in range(g.size) if not g.is_black(r, c))
g.set_letter(r, c, "A", lock=True)
words = [p for p in (WordList.parse_line(l.strip()) for l in open(wl) if l.strip() and not l.startswith("#")) if p and p[0]]
wlist = WordList(words)
t = time.perf_counter(); preflight(g, wlist); print(f"{size}x{size} {wl} {time.perf_counter() - t:.2f}s")
EOF
done; done
```

`data/wordlists/raw/comprehensive_scored.txt` is the largest `raw/` list by bytes (`ls -S data/wordlists/raw`). Record the four timings and the command in this task. If `comprehensive` at 21×21 takes more than 2 s, **STOP and report to Arthur** before the commit.
- [ ] **Step 6: Commit.**

```bash
git add cli/src/domain cli/src/fill/locked_letters.py cli/src/cli.py docs/specs/CLI_SPEC.md cli/tests/unit/test_locked_letters.py cli/tests/unit/test_fill_command.py cli/tests/unit/test_pause_resume_regressions.py
git diff --cached --stat
git commit -m "feat(fill): pre-flight blocks a dead slot with exit 3 and reports off-list typed words"
```

---

### Task 2.10: Result keys on every fill result and `stuck_cells` (§2.1 C11, case 3 C2)

**Files:**
- Modify: `cli/src/fill/locked_letters.py`; `cli/src/cli.py` (`fill`: main `output_data`, the already-filled early return, `paused_payload`)
- Modify: `docs/specs/CLI_SPEC.md` (the `fill` JSON result keys)
- Test: `cli/tests/unit/test_locked_letters.py`, `cli/tests/unit/test_fill_command.py` (extend)

**Interfaces:**
- Consumes: `PreflightResult.index` and `.off_list_cells` (Task 2.9), the input lock set, `cell_list`.
- Produces:

```python
def stuck_cells(
    final_grid: Grid,
    locked: Iterable[Tuple[int, int]],
    problematic_slots: Sequence[Mapping],
    index: Optional[LetterBitsetIndex],   # None on --resume (no pre-flight ran)
    min_score: int,
) -> List[List[int]]: ...
```

**Behavioral criteria:**
- `stuck_cells` returns the cell list of locked cells (from `locked`; see planning default `PD-2-STUCK` (spec §8)) lying in (a) a slot of `final_grid` with at least one empty cell whose pattern has `index.count_matches(pattern, min_score=min_score) == 0`, or (b) a slot named by a `problematic_slots` entry with `"reason": "invalid_word"`, in `IterativeRepair._build_result`'s shape `{"slot": (row, col, direction), "pattern": str, "reason": …}`. The slot's length is `len(pattern)`. Entries without a `"reason"` key (beam, classic) or with another reason contribute nothing to (b) (Phase 0.2).
- The main result carries `"blocked": false`, `"blocked_cells": []`, `"off_list_cells"` = pre-flight's, and `"stuck_cells"` = `stuck_cells(result.grid, input lock set, result.problematic_slots, preflight.index, min_score)`. That is `[]` on `--resume` (empty lock set) and `[]` when the fill is complete (§2.1 C2).
- The already-filled early return carries `"blocked": false` and three `[]` lists, because pre-flight runs after it.
- The paused payload carries `"blocked": false`, `"blocked_cells": []`, `"off_list_cells"` = pre-flight's (`[]` on `--resume`) and `"stuck_cells": []` (planning default `PD-2-PAUSE` (spec §8)).
- With an empty input lock set (always the case on `--resume`, where pre-flight does not run and so there is no `index`), `stuck_cells` is `[]` without building an index.
- The blocked result keeps Task 2.9's shape. A `_fail_fill` error (`{success, error, hint}`) carries none of the four keys (C11).

**Normative cases.** `stuck_cells` on `G33`, `locked = {(0,0),(0,1)}` holding `C`, `A`:

| # | `final_grid` rows | list | `min_score` | `problematic_slots` | expected |
|---|---|---|---|---|---|
| SC1 (a) | `CA.` / `...` / `...` | `CAT;10` `COT;50` `ART;50` | 30 | `[]` | `[[0,0],[0,1]]` |
| SC2 | SC1 | same | 0 | `[]` | `[]` |
| SC3 (b) | `CAX` / three letters / three letters (no empty cell) | `COT;50` | 30 | `[{"slot":(0,0,"across"),"pattern":"CAX","reason":"invalid_word"}]` | `[[0,0],[0,1]]` |
| SC4 | SC3 | same | 30 | `[{"slot":(0,0,"across"),"pattern":"CAX","reason":"unfilled"}]` | `[]` |
| SC5 | SC3 | same | 30 | `[{"row":0,"col":0,"direction":"across","length":3}]` (beam shape) | `[]` |
| SC6 | SC3 | same | 30 | `[{"slot":(1,0,"across"),"pattern":"OLE","reason":"invalid_word"}]` (no locked cell) | `[]` |
| SC7 | as SC1 | as SC1 | 30 | SC3's entry | `[[0,0],[0,1]]` (unique) |
| SC8 (`--resume`) | SC1 | `CAT;10` `COT;50` `ART;50` | 30 | SC3's entry; `locked = set()`; `index=None` | `[]`; no index is built (`index` is never touched) |

`fill` key rows (`--json-output`):

| result | how | expected |
|---|---|---|
| main | `G33`, `C` `(0,0)`, `L6`, `--algorithm repair --timeout 10` | keys present; `blocked false`; lists are lists |
| early return | fully lettered `G33` | keys present; `blocked false`; three `[]` |
| paused | a pause flag raised during the run (the existing pause tests' mechanism in `cli/tests/integration/test_fill_pause_resume.py`) | keys present; `stuck_cells []` |
| blocked | PF1 | keys present (Task 2.9 shape) |
| `_fail_fill` | `-w` naming a directory | none of the four keys |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run, verify failure.** `pytest cli/tests/unit/test_locked_letters.py cli/tests/unit/test_fill_command.py -v`
- [ ] **Step 3: Implement.** Cite `novice-readiness spec 0.2.4 §2.1 (C11)` / `(C2)`.
- [ ] **Step 4: Run.** `pytest cli/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add cli/src/fill/locked_letters.py cli/src/cli.py docs/specs/CLI_SPEC.md cli/tests/unit/test_locked_letters.py cli/tests/unit/test_fill_command.py
git diff --cached --stat
git commit -m "feat(fill): blocked/off-list/stuck cell lists on every fill result"
```

---

### Task 2.11: Characterization STOP gates: pre-placed unlocked letters per `--algorithm`, beam and a typed off-list word (§2.3 `[?]`, §2.1 `[?]`, Phase 0.2)

**Files:**
- Test: `cli/tests/unit/test_fill_characterization.py` (create)
- Modify: this plan (record the observations in this task)

**Interfaces:** Consumes the `"locked"` key (Task 2.2), result keys (Task 2.10). Produces recorded findings that Phase 5 and P6 rely on.

**Behavioral criteria:** characterization only; no product code changes in this task. Each test pins the behaviour observed today, and its docstring states it as observed with the command that shows it.

**Cases:**

| # | run | records |
|---|---|---|
| CH1 | `G33` with `C` at `(0,0)` and `"locked": []` (the UI channel), list `L6` (the letter agrees with both of its fills, the square and its transpose), `--json-output --timeout 10` (`30` for hybrid), once per `--algorithm` in `regex`, `trie`, `beam`, `repair`, `hybrid` | final `grid[0][0]`: `"C"` kept, another letter, or `"."` |
| CH2 | as CH1 with `Q` at `(0,0)` (no `L6` word contains `Q`, so no complete fill keeps it) | the same three outcomes |
| CH3 | `--algorithm beam`, `G33`, row 0 `C A B` locked (key absent), list `L5`, `--timeout 10` | whether rows 1–2 and the three downs fill (`OLE`/`DEE`, `COD`/`ALE`/`BEE`), or beam rejects every placement crossing `CAB` |

- [ ] **Step 1: Write the characterization tests;** run each three times to check it is deterministic: `pytest cli/tests/unit/test_fill_characterization.py -v --count 3` if `pytest-repeat` is installed, else three plain runs.
- [ ] **Step 2: STOP gate (§2.3 `[?]`).** If any CH1/CH2 row shows a solver changing a pre-placed unlocked letter (other letter or `"."`), or the outcome varies between runs, **STOP and report to Arthur** with the table. Do not fix it in this task.
- [ ] **Step 3: STOP gate (§2.1 `[?]`).** If CH3 shows beam rejecting every placement crossing the locked off-list word, **STOP and report to Arthur**: the spec's case 2 under beam needs an amendment.
- [ ] **Step 4: Record** the observed table in this task, with the command `pytest cli/tests/unit/test_fill_characterization.py -v`.
- [ ] **Step 5: Commit.**

```bash
git add cli/tests/unit/test_fill_characterization.py docs/superpowers/plans/2026-10-23-novice-readiness.md
git diff --cached --stat
git commit -m "test(fill): characterize unlocked pre-placed letters per algorithm and beam on a locked off-list word"
```

---

## Phase 3: route, adapter and server tracker (§2.2, §2.4 server)

### Task 3.1: The lock channel through `validate_fill_request` and `fill_with_progress` (§2.2 Lock channel)

**Files:**
- Modify: `backend/api/validators.py` (`validate_fill_request`)
- Modify: `backend/api/routes.py` (`fill_with_progress`: `grid_data`, `cmd_args`)
- Modify: `docs/api/openapi.yaml`, `docs/api/API_REFERENCE.md` (`/fill/with-progress` request body)
- Test: `backend/tests/unit/test_validators.py` (extend); `backend/tests/unit/test_fill_lock_channel_route.py` (create, in the style of `backend/tests/unit/test_fill_resume_route.py`: Flask client, `threading.Thread` patched, argv read from `thread.call_args.kwargs["args"][1]`, grid file read from `argv[1]`)

**Interfaces:** Consumes the CLI's `"locked"` key and `--lock-filled` (Tasks 2.1, 2.2). Produces the request field `"locked_cells"` (pinned) for Phase 5.

**Behavioral criteria (§2.2):**
- `validate_fill_request`: an absent `locked_cells` is valid. A present one must be a list; every entry must be a list of exactly two `int` values with `0 <= r < size` and `0 <= c < size`; `[]` is valid. Violations raise `ValueError`, which the route already turns into a 400 `INVALID_REQUEST`. The message names `locked_cells`; its exact text is not pinned by the spec, so tests assert the status and field name only.
- `"locked_cells": null` (key present, value `None`) is refused: the validator raises `ValueError` naming `locked_cells` ("the validator requires a list"), the route answers 400 `INVALID_REQUEST`; only an absent field means an older client (planning default `PD-3-NULL` (spec §8)). The validator tests presence of the key, not truthiness or `is not None` on `data.get`.
- `fill_with_progress` reads `locked_cells = data.get("locked_cells")`. When `locked_cells is not None` (never truthiness), the temp grid file is `{"size": …, "grid": …, "locked": locked_cells}`, with `[]` written as `"locked": []`. With the field absent, the file has no `"locked"` key.
- `--lock-filled` is in the argv on every request, the field-absent case included.

**Normative cases.** Route rows, `size 5`, `grid` `[["."]*5]*5` with `"A"` at `(0,0)`:

| body `locked_cells` | 202? | temp file `"locked"` | argv |
|---|---|---|---|
| `[[0,0]]` | yes | `[[0,0]]` | contains `--lock-filled` |
| `[]` | yes | `[]` (key present) | contains `--lock-filled` |
| absent | yes | key absent | contains `--lock-filled` |
| `null` (key present) | no: 400 `INVALID_REQUEST`, message names `locked_cells` | no grid file written | no thread started (`PD-3-NULL`) |

Validator rows (`size 5`):

| `locked_cells` | outcome |
|---|---|
| `[]` | valid |
| `[[0,0],[4,4]]` | valid |
| `[[5,0]]`, `[[0,5]]`, `[[-1,0]]` | `ValueError` (out of range) |
| `[[0.5,1]]`, `[["0",1]]` | `ValueError` (non-integer) |
| `[[1]]`, `[[1,2,3]]`, `["0,0"]`, `"0,0"` | `ValueError` (not a pair / not a list) |
| `None` (key present) | `ValueError` (not a list; names `locked_cells`; `PD-3-NULL`) |

- [ ] **Step 1: Write the failing tests** (argv contract in three cases, §2.2 Tests).
- [ ] **Step 2: Run, verify failure.** `pytest backend/tests/unit/test_validators.py backend/tests/unit/test_fill_lock_channel_route.py -v`
- [ ] **Step 3: Implement.** Cite `novice-readiness spec 0.2.4 §2.2`.
- [ ] **Step 4: Run.** `pytest backend/tests -v`, then `bash scripts/docs-check.sh`
- [ ] **Step 5: Commit.**

```bash
git add backend/api/validators.py backend/api/routes.py docs/api/openapi.yaml docs/api/API_REFERENCE.md backend/tests/unit/test_validators.py backend/tests/unit/test_fill_lock_channel_route.py
git diff --cached --stat
git commit -m "feat(api): locked_cells reaches the CLI as the grid file's locked key"
```

---

### Task 3.2: The route's ceiling and `"ceiling_seconds"` (§2.2 B4, P7)

**Files:**
- Modify: `backend/api/routes.py` (`fill_with_progress`: the `data.get("timeout", 300) + 10` thread arg; the 202 body; import `CLI_STARTUP_BUDGET_SECONDS` from `backend.core.cli_adapter`)
- Modify: `backend/core/cli_adapter.py` (the header comment naming the call sites of the addend now includes `routes.py`'s `fill_with_progress`)
- Modify: `docs/api/openapi.yaml`, `docs/api/API_REFERENCE.md` (202 body)
- Test: `backend/tests/unit/test_fill_lock_channel_route.py` (extend)

**Interfaces:** Produces the 202 key `"ceiling_seconds"` (pinned) for Phase 5's watchdog.

**Behavioral criteria:**
- The timeout passed to `run_cli_with_progress` is `timeout + CLI_STARTUP_BUDGET_SECONDS`, where `timeout = data.get("timeout", 300)` (§2.2 B4, P7).
- The 202 JSON is `{"task_id", "progress_url", "ceiling_seconds"}`, where `ceiling_seconds` is that same integer.
- `run_cli_with_progress`'s `TimeoutExpired` branch is unchanged (`Operation timed out`, status `error`).

**Normative cases** (assert against the imported constant, not a literal):

| body `timeout` | thread arg [2] | 202 `ceiling_seconds` |
|---|---|---|
| `60` | `60 + CLI_STARTUP_BUDGET_SECONDS` | same |
| absent | `300 + CLI_STARTUP_BUDGET_SECONDS` | same |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run, verify failure.** `pytest backend/tests/unit/test_fill_lock_channel_route.py -v`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** `pytest backend/tests -v`, then `bash scripts/docs-check.sh`
- [ ] **Step 5: Commit.**

```bash
git add backend/api/routes.py backend/core/cli_adapter.py docs/api/openapi.yaml docs/api/API_REFERENCE.md backend/tests/unit/test_fill_lock_channel_route.py
git diff --cached --stat
git commit -m "feat(api): the fill route's ceiling uses the startup budget and is returned as ceiling_seconds"
```

---

### Task 3.3: Exit 3 reaches the SSE stream as `complete`; the C4 event crosses `_pump_stderr`; a CLI `error` string reaches the stream (§2.2 Exit 3, B3; §2.1 C4; `PD-3-KILL`)

**Files:**
- Modify: `backend/api/routes.py` (`run_cli_with_progress`: the `process.returncode == 0` / `else` branches)
- Test: `backend/tests/unit/test_fill_resume_route.py`-style unit rows in `backend/tests/unit/test_fill_lock_channel_route.py` (extend; `Popen` patched); `backend/tests/integration/test_fill_blocked_e2e.py` (create, **unmarked**, real subprocess, like `test_sse_fill_timeout.py`)

**Interfaces:** Consumes the CLI's exit 3 and blocked JSON (Task 2.9) and the C4 event (Task 2.9). Produces the terminal `complete` event with `data.blocked === true` (pinned) for Phase 5, and the `error` event text of `PD-3-KILL` (Cross-phase pins) that Task 5.4's kill test reads.

**Behavioral criteria:**
- When the exit code is 3 and `json.loads(stdout.strip())` succeeds with `"blocked": true`, `send_progress(task_id, 100, "Complete", "complete", result_data)` (the existing complete branch's call) (§2.2 Exit 3).
- Any other non-zero exit, including 3 with unparseable stdout or without `"blocked": true`, takes the `error` path; its message is per the next bullet.
- **Route error text (planning default `PD-3-KILL`, spec §8):** on a non-zero exit (other than the blocked exit 3 above) whose `json.loads(stdout.strip())` succeeds with an object whose `"error"` is a string, the `error` event's message is that string verbatim (so Task 2.8's postcondition arrives as `Autofill changed a locked letter; nothing was written.`). A negative return code (the child was killed by a signal) keeps today's `CLI Error (code <rc>): …` text whatever stdout holds; every other non-zero exit (stdout not JSON, no string `"error"`) keeps it too. Phase 5's kill test (Task 5.4) depends on this split.
- `_pump_stderr`'s rewrite list, `generate()`'s terminal set and the statuses are unchanged. There is no `blocked` status (B3).

**Normative cases:**

| # | child | terminal event |
|---|---|---|
| E1 | exit 3, stdout PF1's JSON | status `complete`, `data` == the JSON |
| E2 | exit 3, stdout `not json` | status `error`, message starts `CLI Error (code 3)` |
| E3 | exit 3, stdout `{"success": false}` | status `error` |
| E6 (`PD-3-KILL`) | exit 1, stdout `{"success": false, "error": "Autofill changed a locked letter; nothing was written."}` | status `error`, message exactly `Autofill changed a locked letter; nothing was written.` |
| E7 (`PD-3-KILL`) | return code -9, same stdout as E6 | status `error`, message starts `CLI Error (code -9)` |
| E8 (`PD-3-KILL`) | exit 1, stdout `{"success": false, "error": 5}` | status `error`, message starts `CLI Error (code 1)` |
| E9 (`PD-3-KILL`) | exit 1, stdout `not json` | status `error`, message starts `CLI Error (code 1)` |
| E4 (real CLI, §2.2 Tests) | `POST /api/fill/with-progress` with `size 5`, all-white grid, `Q` `(0,0)`, `X` `(0,1)`, `locked_cells [[0,0],[0,1]]`, `wordlists ["comprehensive"]`; read the task's events until a terminal one | status `complete`; `data.blocked true`; `data.reason "no_word_fits"`; `data.blocked_cells [[0,0],[0,1]]`; `data.blocked_slots [{"row":0,"col":0,"direction":"across","length":5,"pattern":"QX???"}]` |
| E5 (C4 contract, real CLI) | `POST` with `size 3`, row 0 `C`,`A`,`B`, `locked_cells [[0,0],[0,1],[0,2]]`, a word list resolving to a temp copy of `L5` (patch the resolver to return its path), `algorithm "repair"`, `timeout 10` | a `running` event whose `data == {"off_list_cells": [[0,0],[0,1],[0,2]], "warning": "Typed words not in the selected word lists: CAB"}` precedes the terminal event |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run, verify failure.** `pytest backend/tests/unit/test_fill_lock_channel_route.py backend/tests/integration/test_fill_blocked_e2e.py -v`
- [ ] **Step 3: Implement.** Cite `novice-readiness spec 0.2.4 §2.2 (B3)`.
- [ ] **Step 4: Run alone.** `pytest backend/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add backend/api/routes.py backend/tests/unit/test_fill_lock_channel_route.py backend/tests/integration/test_fill_blocked_e2e.py
git diff --cached --stat
git commit -m "feat(api): a blocked fill (exit 3) is a complete event; pin the off-list event across the seam"
```

---

### Task 3.4: `CLIAdapter.fill` reports exit 3 with the CLI's message (§2.2 last bullet)

**Files:**
- Modify: `backend/core/cli_adapter.py` (`CLIAdapter.fill`)
- Test: `backend/tests/unit/test_cli_adapter.py` (extend; the exit-3 row runs the real CLI)

**Interfaces:** Consumes the blocked JSON. Produces nothing a UI phase consumes (`/api/fill` is not on the UI path).

**Behavioral criteria (§2.2):**
- `CLIAdapter.fill` passes `--json-output`. It sends no lock list, so the CLI locks every letter.
- Exit 3 with a parseable last stdout JSON carrying `"blocked": true` returns `{"success": False, "error": <message>, **blocked_json}`. By default `<message>` is §2.1's text-output lines for the blocked result, rendered from `reason` and `blocked_slots` and joined by `\n` (planning default `PD-3-MSG` (spec §8)).
- Otherwise, when the `-o` file is missing or empty, the failure carries the CLI's message instead of `CLI produced no output` (planning default `PD-3-ERR` (spec §8): the message is the stdout JSON `error`; when stdout carries none, stderr's non-JSON lines).
- The success path still reads the `-o` file.

**Normative cases:**

| child | returned |
|---|---|
| real CLI on `G33`, `Q` `(0,0)`, `X` `(0,1)`, list `L1` (via `wordlist_paths`) | `success False`; `blocked True`; `error == "Blocked: no word fits QX? at 0,0 across"` |
| real CLI with `wordlist_paths` naming a directory | `success False`; `error` contains `Could not read wordlist` |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run, verify failure.** `pytest backend/tests/unit/test_cli_adapter.py -v`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** `pytest backend/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add backend/core/cli_adapter.py backend/tests/unit/test_cli_adapter.py
git diff --cached --stat
git commit -m "fix(adapter): fill reports a blocked run with the CLI's message"
```

---

### Task 3.5: The tracker keeps its terminal event for 60 s; `generate()` re-sends it (§2.4 server, #41, P3)

**Files:**
- Modify: `backend/api/progress_routes.py` (`send_progress`, `cleanup_progress_tracker`, `stream_progress`, `generate`)
- Test: `backend/tests/unit/test_progress_terminal_record.py` (create); update `backend/tests/integration/test_progress_integration.py` assertions that encode "the tracker is removed when a stream ends" (sweep for the recorded reason, not only callers)

**Interfaces:** Produces (module level in `progress_routes.py`):

```python
TERMINAL_STATUSES = ("complete", "error", "paused")
TRACKER_RETENTION_SECONDS = 60
QUEUE_TIMEOUT_SECONDS = 30
terminal_events: Dict[str, Tuple[Dict[str, Any], float]]   # task_id -> (event, enqueue time)
def get_terminal_event(task_id: str) -> Optional[Dict[str, Any]]: ...
def sweep_expired_trackers(now: Optional[float] = None) -> List[str]: ...   # returns removed ids
```

**Behavioral criteria (§2.4):**
- `send_progress` with a status in `TERMINAL_STATUSES` records `(event, event["timestamp"])` in `terminal_events[task_id]` when it enqueues the event. The `TimeoutExpired` path's `Operation timed out` `error` is recorded like any other.
- `generate()`'s `finally:` no longer calls `cleanup_progress_tracker`.
- On connect, before the first `get`, and on every `queue.Empty` (`task_queue.get(timeout=QUEUE_TIMEOUT_SECONDS)`), `generate()` sends the recorded terminal event if this subscriber has not yet sent a terminal event, then stops. A terminal event taken from the queue is sent and ends the stream as today. A subscriber never sends two terminal events.
- `cleanup_progress_tracker` also removes `terminal_events[task_id]`.
- `sweep_expired_trackers(now)` removes every tracker whose terminal event is older than `TRACKER_RETENTION_SECONDS`, i.e. `now - enqueue_time > 60`; `now` defaults to `time.time()`. It runs at the start of every `stream_progress` request, before the 404 check, and in `generate()` on each `queue.Empty`. A tracker with no terminal event is never swept. There is no timer thread (P3; planning default `PD-3-SWEEP` (spec §8)).

**Normative cases:**

| # | sequence | expected |
|---|---|---|
| tr1 | subscriber A consumes `complete`; subscriber B connects 5 s later | B's first frame is that `complete` event; B ends |
| tr2 | A and B connected; A takes the queued `complete` (`QUEUE_TIMEOUT_SECONDS` patched to 0.1) | B sends the recorded `complete` within one queue timeout and ends |
| tr3 | A disconnects mid-run | `task_id in progress_queues` still true; a new `GET /api/progress/<id>` is 200 |
| tr4 | terminal recorded at `t0`; `sweep_expired_trackers(now=t0+60)` | tracker kept |
| tr5 | `sweep_expired_trackers(now=t0+60.001)` | tracker, its max-progress entry and its terminal record removed; `GET` is 404 |
| tr6 | tracker with no terminal event, `sweep_expired_trackers(now=float("inf"))` | kept |
| tr7 | `error` from the `TimeoutExpired` branch | `get_terminal_event` returns it |
| tr8 | `paused` | recorded and re-sent like `complete` |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run, verify failure.** `pytest backend/tests/unit/test_progress_terminal_record.py -v`
- [ ] **Step 3: Implement.** Cite `novice-readiness spec 0.2.4 §2.4 (#41)`.
- [ ] **Step 4: Run alone.** `pytest backend/tests -v`
- [ ] **Step 5: Commit.**

```bash
git add backend/api/progress_routes.py backend/tests/unit/test_progress_terminal_record.py backend/tests/integration/test_progress_integration.py
git diff --cached --stat
git commit -m "fix(progress): keep the terminal event 60 s and re-send it to every subscriber (#41)"
```

---

### Task 3.6: Early Cancel is recorded and applied at registration (§2.4 C7 "Early Cancel")

**Files:**
- Modify: `backend/api/progress_routes.py` (`register_process`; new `request_cancel`)
- Modify: `backend/api/pause_resume_routes.py` (`cancel_autofill`)
- Modify: `docs/api/openapi.yaml`, `docs/api/API_REFERENCE.md` (cancel responses)
- Test: `backend/tests/unit/test_pause_resume_routes.py` (extend); `backend/tests/integration/test_sse_fill_timeout.py`-style real child in `backend/tests/integration/test_fill_blocked_e2e.py` (extend)

**Interfaces:** Consumes Task 3.5's `get_terminal_event`. Produces:

```python
pending_cancels: Set[str]   # guarded by running_processes_lock
def request_cancel(task_id: str) -> str: ...   # "killed" | "recorded" | "not_running"
```

**Behavioral criteria (§2.4):**
- `request_cancel`, under `running_processes_lock`:
  - A live registered process gives `"killed"` (as `cleanup_process`).
  - A tracker that exists with no terminal event and no registered process records `task_id` in `pending_cancels` and gives `"recorded"`.
  - Anything else (no tracker, a recorded terminal event, a dead process) gives `"not_running"`.
- `register_process(task_id, process)`, under the same lock: when `task_id` is in `pending_cancels`, it removes it and terminates the process with `cleanup_process`'s terminate-then-kill sequence before returning (§2.4 "kills the process as soon as it registers"). No interleaving of `request_cancel` and `register_process` leaves a process running after `"recorded"` was returned.
- `cancel_autofill` maps `"killed"` → 200 (today's body), `"recorded"` → 200 with the same body (planning default `PD-3-EARLY` (spec §8): 200), `"not_running"` → 404 `TASK_NOT_FOUND` (today's). It clears the pause markers in both 200 cases.

**Normative cases:**

| # | sequence | expected |
|---|---|---|
| cx1 | tracker created, no process; `POST /api/fill/cancel/<id>` | 200; `id in pending_cancels` |
| cx2 | cx1, then `register_process(id, <python -c "import time; time.sleep(3600)">)` | the child's `poll()` is not `None` within 10 s; `id not in pending_cancels` |
| cx3 | cx1, then `run_cli_with_progress(id, …)` with a sleeping child | terminal event status `error` |
| cx4 | live process | 200; process terminated (today's behaviour) |
| cx5 | terminal event recorded, no process | 404 |
| cx6 | unknown id | 404 |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run, verify failure.** `pytest backend/tests/unit/test_pause_resume_routes.py backend/tests/integration/test_fill_blocked_e2e.py -v`
- [ ] **Step 3: Implement.** Cite `novice-readiness spec 0.2.4 §2.4 (C7)`.
- [ ] **Step 4: Run alone.** `pytest backend/tests -v`, then `bash scripts/docs-check.sh`
- [ ] **Step 5: Commit.**

```bash
git add backend/api/progress_routes.py backend/api/pause_resume_routes.py docs/api/openapi.yaml docs/api/API_REFERENCE.md backend/tests/unit/test_pause_resume_routes.py backend/tests/integration/test_fill_blocked_e2e.py
git diff --cached --stat
git commit -m "feat(api): a cancel before the process registers kills it at registration"
```
---

## Phase 4: UI foundation (cell fields, document id, §3.7 writers, D1 gate)

Spec sections: §2.3 (Provenance, `isBlocked` scope, D1), §3.4 (document id only: M1), §3.7. Read against
`src/App.jsx`, `src/api/gridCodec.js`, `src/components/bench/CrosswordGrid.jsx` on `feat/novice-readiness` @ `2e36f17`.

Out of scope here and owned by Phase 6: New grid and Open saved (§3.2, §3.4), which are built **already gated**
on this phase's `editingPaused`; S1 (Verify/Clean functional updates), Clean's G5 guard and confirm, #62 and
G6 (`handlePatternSelect` skip rule), G7 (`toggleBlackSquare` refusing a theme-locked partner), named saves,
restore-on-load, S2–S4. This phase's writer helpers keep today's set of written cells; Phase 6 narrows them.

Run from the worktree root `../crossword-helper-novice`. Every task: run the named test file(s) alone, then
`npx vitest run` alone, then `npm run build`; read each result before committing (never chain a test run and
a commit).

### Task 4.1: Canonical cell fields and the save codec

**Files:**
- Modify: `src/api/gridCodec.js` (`makeCell`; module header comment listing the canonical cell; add `normalizeCell`, `toSavedGrid`)
- Test: `src/api/__tests__/gridCodec.test.js` (the `makeCell returns the canonical empty cell` equality changes)

**Interfaces:**
- Consumes: nothing new.
- Produces (Phase 4.2, 4.3, Phase 5, Phase 6 restore-on-load / Open saved):

```js
export function makeCell(): { letter: '', isBlack: false, isThemeLocked: false, number: null,
                              isError: false, isAutofilled: false, isBlocked: false }
export function normalizeCell(cell: object): object   // canonical cell from a saved/foreign cell
export function toSavedGrid(grid: object[][] | null): object[][] | null   // cells as the save document carries them
```

**Behavioral criteria:**
- `makeCell()` gains `isAutofilled: false` and `isBlocked: false` (§2.3 Provenance; §2.3 Red cells). `makeGrid` and `fromCliStrings` inherit them through `makeCell`.
- `normalizeCell(cell)` returns a new object: `makeCell()`'s fields, overlaid by `cell`'s fields, then `isAutofilled: cell.isAutofilled === true` and `isBlocked: false`. "A grid loaded without the field gets `false`" (§2.3, §3.4); `isBlocked` is never saved, so a loaded cell is never red (§2.3).
- `toSavedGrid(grid)` returns a new grid whose every cell is a copy of the input cell **without the `isBlocked` key** and with `isAutofilled: cell.isAutofilled === true`; `null` → `null`. "`isBlocked` is **not** saved" (§2.3); "the flag is part of the saved document" (§2.3, §3.4). Input not mutated.
- The header comment's "Frontend canonical" line lists the two new fields.

**Normative cases:**

| call | result |
|---|---|
| `makeCell()` | `{letter:'', isBlack:false, isThemeLocked:false, number:null, isError:false, isAutofilled:false, isBlocked:false}` |
| `normalizeCell({})` | deep-equals `makeCell()` |
| `normalizeCell({letter:'A', isThemeLocked:true})` | `letter 'A'`, `isThemeLocked true`, `isAutofilled false`, `isBlocked false` |
| `normalizeCell({letter:'A', isAutofilled:true, isBlocked:true})` | `isAutofilled true`, `isBlocked false` |
| `normalizeCell({letter:'A', isAutofilled:'yes'})` | `isAutofilled false` |
| `toSavedGrid([[{letter:'A', isAutofilled:true, isBlocked:true, isBlack:false}]])[0][0]` | has no `isBlocked` key; `isAutofilled true`; `letter 'A'` |
| `toSavedGrid([[{letter:'B'}]])[0][0].isAutofilled` | `false` |
| `toSavedGrid(null)` | `null` |

- [ ] **Step 1: Write the failing tests** — design them from the contract; cover every row.
- [ ] **Step 2: Run** `npx vitest run src/api/__tests__/gridCodec.test.js` — expect failure from the missing fields/functions, not a broken test.
- [ ] **Step 3: Implement** to the contract.
- [ ] **Step 4: Run** the same command, then `npx vitest run`, then `npm run build`; all green and clean.
- [ ] **Step 5: Commit**

```bash
git add src/api/gridCodec.js src/api/__tests__/gridCodec.test.js
git commit -m "feat(grid): canonical cells carry isAutofilled and isBlocked; save codec strips isBlocked"
```

### Task 4.2: Document id and the save document

**Files:**
- Create: `src/lib/docId.js`
- Modify: `src/App.jsx` (`contentSigOf`; `initializeGrid`; the `gridId` state and its comment; the `doc` memo; `handleGridImport`'s id bump)
- Test: `src/lib/__tests__/docId.test.js` (new); `src/__tests__/App.docId.test.jsx` (new)

**Interfaces:**
- Consumes: `toSavedGrid` (Task 4.1).
- Produces (pinned by the skeleton; Phase 5 and Phase 6 consume):

```js
// src/lib/docId.js
export function mintDocId(): string
// src/App.jsx
export function contentSigOf(size: number, grid: object[][] | null): string   // now exported, for tests
const [docId, setDocId] = useState(mintDocId);   // replaces gridId / setGridId everywhere
```

**Behavioral criteria:**
- `mintDocId()` returns `globalThis.crypto.randomUUID()` when that is a function; otherwise a non-empty string unique per call built without `crypto` (the "fallback where it is unavailable", §3.4 M1). Format of the fallback is the implementer's; uniqueness and non-emptiness are the contract.
- `gridId`/`setGridId` no longer exist in `src/App.jsx`; `docId` is its replacement everywhere (§3.4 M1: "a counter that restarts at 1 on every load ... cannot key a save").
- App start mints one (`useState(mintDocId)`); `initializeGrid` calls `setDocId(mintDocId())` where it called `setGridId((n) => n + 1)`; `handleGridImport` calls `setDocId(mintDocId())` where it called `setGridId(...)` (§3.4: "New grid (§3.2) and import (§3.7) mint one, and so does app start"). This keeps `useSaveMachine`'s F10 behaviour: `doc.id` changes on init and import, never on an edit.
- `initializeGrid` builds each cell with `isAutofilled: false` and `isBlocked: false` in addition to today's fields (§2.3 Provenance: "`App.jsx`'s `initializeGrid`, which builds cells by hand").
- `contentSigOf` is exported; each cell's tuple becomes `[c.letter, c.isBlack, c.isThemeLocked, c.isAutofilled === true]` (§2.3: `isAutofilled` is part of `contentSigOf`, absent → `false`; `isBlocked` is not).
- The `doc` memo is `{ id: docId, size: gridSize, grid: toSavedGrid(grid), numbering, symmetryEnabled }` (§2.3: the flag is saved, `isBlocked` is not).

**Normative cases:**

| input | result |
|---|---|
| `mintDocId()` twice, `crypto.randomUUID` present | two different strings, each equal to what `randomUUID` returned |
| `mintDocId()` twice, `crypto.randomUUID` absent (stubbed `undefined`) | two different non-empty strings |
| `contentSigOf(1, [[A]])` vs `contentSigOf(1, [[A']])`, `A'` = `A` with `isAutofilled` flipped | different |
| same, `A'` = `A` with `isBlocked` flipped | identical |
| same, `A` lacks `isAutofilled`, `A'` has `isAutofilled: false` | identical |
| App: Save clicked, then a grid imported, then Save clicked (`storage.save` spied) | both `doc.id` are non-empty strings and differ |
| App: Save clicked after typing a letter | saved `doc.grid` cells carry `isAutofilled` and no `isBlocked` key |

- [ ] **Step 1: Write the failing tests** (`App.docId.test.jsx` renders `App` inside `ToastProvider` as `src/__tests__/components/App.test.jsx` does, with `react-hot-toast` mocked the same way).
- [ ] **Step 2: Run** `npx vitest run src/lib/__tests__/docId.test.js src/__tests__/App.docId.test.jsx` — expect failure from the missing module/export.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the same, then `npx vitest run` (`useSaveMachine.test.jsx` and `App.test.jsx` stay green unchanged), then `npm run build`.
- [ ] **Step 5: Commit**

```bash
git add src/lib/docId.js src/lib/__tests__/docId.test.js src/App.jsx src/__tests__/App.docId.test.jsx
git commit -m "feat(app): a minted document id replaces the gridId counter"
```

### Task 4.3: §3.7 grid writers clear `isAutofilled`; an edit clears red on the edited cell; red renders

**Files:**
- Create: `src/lib/gridEdits.js` (the seven pure `write*` helpers below)
- Modify: `src/App.jsx` (`setLetter`, `toggleBlackSquare`, `toggleThemeLock`, `handlePatternSelect`, `handleThemeWordApplied`, `handleGridImport`, `handleCleanGrid` import the helpers and delegate their grid computation to them)
- Modify: `src/components/bench/CrosswordGrid.jsx` (cell rendering)
- Test: `src/lib/__tests__/gridEdits.test.js` (create, pure helpers); `src/components/bench/__tests__/CrosswordGrid.test.jsx` (red rendering)

**Interfaces:**
- Consumes: `normalizeCell` (Task 4.1).
- Produces (named exports of `src/lib/gridEdits.js`, created here; `App.jsx` imports them; Phase 6 adds its own exports to the same file and amends `writePatternWord` for #62/G6 and `writeCleanedGrid` for S1/G5):

```js
// src/lib/gridEdits.js
export function writeLetter(grid, row, col, letter): object[][]
export function writeToggleBlack(grid, row, col, symmetryEnabled): object[][]
export function writeToggleThemeLock(grid, row, col): object[][]
export function writePatternWord(grid, selectedCell /* {row, col, direction} */, word): object[][]
export function writeAppliedTheme(prevGrid, updatedGrid): object[][]
export function writeImportedGrid(importedGrid): object[][]
export function writeCleanedGrid(prevGrid, cleanedGrid): object[][]
```

**Behavioral criteria:**
- Common rule (§3.7 S5; §2.3 Red cells): every cell a helper writes is a **new object** with `isAutofilled: false` and `isBlocked: false`, **a cell given the same letter included**. Cells it does not write are the input's cell objects, untouched (an edit clears red "on the edited cell only"). No helper mutates its input grid or its cells. A helper that writes nothing returns its input grid (same reference).
- `writeLetter`: a black cell → no write. Otherwise writes `letter.toUpperCase()` into `(row, col)` (today's `setLetter`).
- `writeToggleBlack`: writes `(row, col)` with `isBlack` flipped and `letter: ''` when it becomes black; with `symmetryEnabled`, also writes the partner `(size-1-row, size-1-col)` with the same `isBlack` and `letter: ''` when black (today's `toggleBlackSquare`; §3.7 "both the cell and its symmetric partner"). G7 is Phase 6 (its guard rule `canToggleBlack` is a separate export; Task 6.2).
- `writeToggleThemeLock`: a black cell → no write. Otherwise writes `(row, col)` with `isThemeLocked` flipped (§3.7 lists `toggleThemeLock`). Every other cell keeps its object (today's version copies every cell; that is not a write).
- `writePatternWord`: writes `word[i]` into each in-bounds cell from `selectedCell` along `direction`, exactly the cells today's `handlePatternSelect` writes (Phase 6 narrows the set per #62). This also stops today's mutation of shared cell objects.
- `writeAppliedTheme`: a cell is written when `updatedGrid`'s cell differs from `prevGrid`'s in `letter`, `isBlack` or `isThemeLocked`; a written cell is `normalizeCell(updated cell)` with `isAutofilled: false`, `isBlocked: false`; an unwritten cell is `prevGrid`'s object. (The apply route sets `isThemeLocked: true` on every word cell and rewrites blacked cells as `{"letter": "", "isBlack": true}`, `backend/api/theme_routes.py` `apply_placement`, so every cell it changes differs in one of the three.)
- `writeImportedGrid`: every cell is `normalizeCell(cell)` with `isAutofilled: false` (§3.7: "import ignores it, so every imported letter counts as typed"). `ImportPanel`'s `convertGridFormat` builds cells by hand without `isThemeLocked`; normalising every cell is what fills the canonical fields.
- `writeCleanedGrid`: today's mapping (letter/`isBlack` from the response, `isError: false` on every cell); a cell whose `letter` or `isBlack` changes is written per the common rule; others keep `isAutofilled`/`isBlocked`. planning default `PD-4A` (spec §8) governs which cells count as written; Phase 6 amends this helper for S1/G5 (Task 6.11 adds a third parameter, `blanks`, and replaces this mapping and its row below).
- The seven `App.jsx` callbacks call their helper and `setGrid` its result; `handleGridImport` and `handleCleanGrid` keep every other statement they have today (size skip, symmetry, toasts, the `removed_count === 0` early return). `handleThemeWordApplied` has no `grid` in its closure today (`[pushToast]` deps), so its form is `setGrid((prev) => writeAppliedTheme(prev, updatedGrid))`; `grid` is not added to its deps. `handleGridImport` sets the grid to `writeImportedGrid(importedGrid)` and computes `setSavedSig(contentSigOf(size, <that normalised grid>))`, so the sig and the grid cannot drift.
- `CrosswordGrid` renders red for a cell with `isBlocked && !isBlack`: a background `<rect>` carrying `data-blocked="true"`, filled `var(--danger)` at reduced opacity, drawn under the letter, distinct from `isError`'s letter colour and underline (§2.3: "shows them in red"; `isBlocked` is separate from `isError`). A black cell never renders it.

**Normative cases** (cells written `{letter, isAutofilled, isBlocked}`; `F` = `false`, `T` = `true`):

| helper call | before | after |
|---|---|---|
| `writeLetter(g, 0, 0, 'a')` | `(0,0)` `{'', F, F}` | `(0,0)` `{'A', F, F}` |
| `writeLetter(g, 0, 0, 'B')` (same letter) | `(0,0)` `{'B', T, F}` | `(0,0)` `{'B', F, F}` |
| `writeLetter(g, 0, 0, 'C')` | `(0,0)` `{'B', T, T}`; `(0,1)` `isBlocked T` | `(0,0)` `{'C', F, F}`; `(0,1)` same object, `isBlocked T` |
| `writeLetter(g, 0, 0, '')` | `(0,0)` `{'B', T, F}` | `(0,0)` `{'', F, F}` |
| `writeLetter(g, 0, 0, 'A')`, `(0,0)` black | — | returns `g` |
| `writeToggleBlack(g5, 0, 1, true)` | `(0,1)` `{'A', T, T}`; `(4,3)` `{'B', T, F}` | both `isBlack T`, `letter ''`, `isAutofilled F`, `isBlocked F` |
| `writeToggleBlack(g5, 0, 1, false)` | `(4,3)` `{'B', T, F}` | `(4,3)` same object |
| `writeToggleThemeLock(g, 0, 0)` | `{'A', T, T}`, `isThemeLocked F` | `isThemeLocked T`, `{'A', F, F}`; every other cell same object |
| `writePatternWord(g4, {row:0,col:0,direction:'across'}, 'CAT')` | `(0,0..2)` `'' / 'A'(T) / 'X'(T)` | `C / A / T`, all `isAutofilled F`, `isBlocked F`; `g4`'s cells unmutated |
| `writePatternWord(g4, {row:0,col:2,direction:'across'}, 'CAT')` | 4 columns | writes `(0,2)`, `(0,3)` only |
| `writeAppliedTheme(prev, upd)` | `prev(0,0)` `{'A', T}` not theme-locked; `upd(0,0)` `{'A', isThemeLocked T, isAutofilled T}` | `(0,0)` `isThemeLocked T`, `isAutofilled F`, `isBlocked F` |
| `writeAppliedTheme(prev, upd)` | `upd(1,1)` `{letter:'', isBlack:true}` only | `(1,1)` canonical (`isThemeLocked F`, `number null`), `isBlack T`, `isAutofilled F` |
| `writeAppliedTheme(prev, upd)` | cell equal in letter/isBlack/isThemeLocked, `prev` `isAutofilled T` | `prev`'s object, `isAutofilled T` |
| `writeImportedGrid([[{letter:'A', isAutofilled:true}]])` | — | `isAutofilled F`, `isThemeLocked F`, `isBlocked F` |
| `writeCleanedGrid(prev, cleaned)` | `prev(0,0)` `{'Q', T}` → cleaned `''`; `prev(0,1)` `{'A', T}` → cleaned `'A'` | `(0,0)` `{'', F, F}`; `(0,1)` `isAutofilled T` (planning default `PD-4A` (spec §8)) |
| `CrosswordGrid` with two `isBlocked` cells, one of them black | — | exactly one `[data-blocked="true"]` element |

- [ ] **Step 1: Write the failing tests** — one per writer, including the same-letter `writeLetter` row (§3.7 Tests), and the edited-cell-only row (§2.3 Tests, `isBlocked` scope).
- [ ] **Step 2: Run** `npx vitest run src/lib/__tests__/gridEdits.test.js src/components/bench/__tests__/CrosswordGrid.test.jsx` — expect failure from the missing exports.
- [ ] **Step 3: Implement**, citing `novice-readiness spec 0.2.4 §3.7 (S5)` in the helpers' doc comment.
- [ ] **Step 4: Run** the same, then `npx vitest run` (both `App.test.jsx` import regressions stay green), then `npm run build`.
- [ ] **Step 5: Commit**

```bash
git add src/lib/gridEdits.js src/lib/__tests__/gridEdits.test.js src/App.jsx src/components/bench/CrosswordGrid.jsx src/components/bench/__tests__/CrosswordGrid.test.jsx
git commit -m "feat(grid): user writers clear isAutofilled and red on the cells they write"
```

### Task 4.4: The D1 writer gate

**Files:**
- Modify: `src/hooks/useAutofillMachine.js` (add the `LIVE_STATES` export only)
- Modify: `src/App.jsx` (`editingPaused`, `editingPausedRef`, early returns, `useNumbering`'s `enabled`, props below)
- Modify: `src/components/bench/CrosswordGrid.jsx` (`dispatchGridKey`, click handlers, message)
- Modify: `src/components/bench/TopBar.jsx`, `src/components/PatternMatcher.jsx`, `src/components/ThemeWordsPanel.jsx`, `src/components/ImportPanel.jsx` (an `editingPaused` prop each)
- Test: `src/components/bench/__tests__/CrosswordGrid.test.jsx`, `src/components/bench/__tests__/TopBar.test.jsx`, `src/__tests__/App.gate.test.jsx` (new)

**Interfaces:**
- Consumes: Task 4.3's helpers.
- Produces (skeleton-pinned names first; Phase 5 and Phase 6 consume all):

```js
// src/hooks/useAutofillMachine.js
export const LIVE_STATES = new Set(['submitting', 'running']);
// src/App.jsx, in App's body after useAutofillMachine
const editingPaused = LIVE_STATES.has(autofill.state);
const editingPausedRef = useRef(false);   // refreshed every render: editingPausedRef.current = editingPaused
// components
<CrosswordGrid editingPaused={bool} .../>     // default false
<TopBar editingPaused={bool} .../>            // default false
<PatternMatcher editingPaused={bool} .../>    // default false
<ThemeWordsPanel editingPaused={bool} .../>   // default false
<ImportPanel editingPaused={bool} .../>       // default false
// dispatchGridKey's state argument gains `editingPaused` (default false)
```

**Behavioral criteria** (§2.3 D1):
- `editingPaused` is the render-time predicate; `editingPausedRef.current` is the same value read at write time. `useNumbering`'s `enabled` becomes `!editingPaused` (same states as today).
- Write-time early return: `setLetter`, `toggleBlackSquare`, `toggleThemeLock`, `handlePatternSelect`, `handleThemeWordApplied`, `handleGridImport` return before any state change when `editingPausedRef.current` is true. `handleVerifyWords` and `handleCleanGrid` return before the request when it is true, and check it again after `await`, returning before `setGrid` and before their result toast: "an async handler (Verify, Clean) whose response lands after Start writes nothing". (Phase 6's S1 rewrite keeps the post-`await` check.)
- Disabled controls while `editingPaused`: in `CrosswordGrid`, `dispatchGridKey` returns `{ preventDefault: true, actions: [] }` for letters, `Backspace`, `Delete`, `Space`, `.` and Ctrl/Cmd+L; arrows, `Tab`/Shift+`Tab` and `Enter` behave as today; Shift/Alt+click does not call `onToggleBlack`; right-click calls `preventDefault` and not `onToggleLock`; a plain click still focuses. `TopBar`'s Verify and Clean buttons are `disabled` (`offline || editingPaused`); Save is unaffected (S2 is Phase 6). `PatternMatcher`'s `.result-item` rows carry `aria-disabled="true"` and their click is a no-op. `ThemeWordsPanel`'s `.apply-btn` buttons and Apply All button are `disabled`. `ImportPanel`'s `Import Grid` button is `disabled`.
- While `editingPaused`, `CrosswordGrid` renders, inside `.xw-grid-wrap`, an element with `role="status"` whose text is exactly `Editing is paused while autofill runs.`; absent otherwise.
- The D1 list's "grid size" has no control today: `setGridSize` is called only from `handleGridImport`, which is gated above. New grid (§3.2) and Open saved (§3.4) do not exist yet; Phase 6 builds them disabled on `editingPaused` and returning early on `editingPausedRef.current`.
- The machine's `onGridUpdate` (`(updater) => setGrid(updater)`) is not gated: it is the only writer while live.

**Normative cases:**

| situation | result |
|---|---|
| `dispatchGridKey({key:'A'}, {…, editingPaused:true})` | `{preventDefault:true, actions:[]}` |
| same for `Backspace`, `Delete`, `' '`, `'.'`, `{key:'l', ctrlKey:true}` | `{preventDefault:true, actions:[]}` |
| `dispatchGridKey({key:'ArrowRight'}, {…, editingPaused:true})` | the same actions as with `editingPaused:false` |
| mounted `CrosswordGrid editingPaused` | status text `Editing is paused while autofill runs.`; Shift+click and right-click call no handler |
| mounted `CrosswordGrid` (prop absent) | no status element |
| `TopBar status online, editingPaused` | Verify and Clean disabled, Save enabled |
| App: Start pressed in the Autofill panel with `api.startFill` never resolving (state `submitting`), then a letter typed on a focused cell | no letter appears; status text shown |
| App: as above, then Ctrl+L, Space, Shift+click on a white cell | grid unchanged |
| App: `api.verifyWords` pending, Start pressed, then `verifyWords` resolves with an invalid word | no cell gains `isError` (no red underline rendered); no result toast |
| App: same with `api.cleanGrid` resolving `removed_count: 1` | no letter removed |
| App: run reaches a terminal state (`startFill` rejects) | status text gone; typing writes again |
| `PatternMatcher editingPaused` with results showing; click a result row | row has `aria-disabled="true"`; `onSelectWord` not called |
| `ThemeWordsPanel editingPaused` with suggestions showing | every `.apply-btn` and the Apply All button `disabled` |
| App: `submitting` (as above), Import tool, a valid grid pasted and validated (the `App.test.jsx` paste flow) | `Import Grid` button `disabled`; grid unchanged |

- [ ] **Step 1: Write the failing tests.** `App.gate.test.jsx`: mock `api.getWordlists` (resolve `{wordlists: []}`) so the Autofill panel mounts, and `api.health` online so Verify/Clean are not disabled for being offline; a never-resolving `api.startFill` holds `submitting`, which is live. `PatternMatcher` and `ThemeWordsPanel` rows extend `src/__tests__/components/PatternMatcher.test.jsx` and `src/__tests__/components/ThemeWordsPanel.test.jsx`; `ImportPanel` has no test file, so its row lives in `App.gate.test.jsx`.
- [ ] **Step 2: Run** `npx vitest run src/components/bench/__tests__/CrosswordGrid.test.jsx src/components/bench/__tests__/TopBar.test.jsx src/__tests__/components/PatternMatcher.test.jsx src/__tests__/components/ThemeWordsPanel.test.jsx src/__tests__/App.gate.test.jsx`.
- [ ] **Step 3: Implement**, citing `novice-readiness spec 0.2.4 §2.3 (D1)` at `editingPaused`.
- [ ] **Step 4: Run** the same, then `npx vitest run`, then `npm run build`.
- [ ] **Step 5: Commit**

```bash
git add src/hooks/useAutofillMachine.js src/App.jsx src/components/bench/CrosswordGrid.jsx src/components/bench/TopBar.jsx src/components/PatternMatcher.jsx src/components/ThemeWordsPanel.jsx src/components/ImportPanel.jsx src/components/bench/__tests__/CrosswordGrid.test.jsx src/components/bench/__tests__/TopBar.test.jsx src/__tests__/components/PatternMatcher.test.jsx src/__tests__/components/ThemeWordsPanel.test.jsx src/__tests__/App.gate.test.jsx
git commit -m "feat(autofill): no grid writer but the run's own while autofill is live"
```

---

## Phase 5: UI autofill (§2.3 machine, §2.4 client, §2.5)

Spec sections: §2.3, §2.4 (client half), §2.5. Wire contract consumed from Phase 3 (skeleton "Cross-phase pins"):
request field `locked_cells`; SSE statuses `running|complete|paused|error`; blocked = `complete` with
`data.blocked === true`, `data.reason` `no_word_fits|no_word_of_length`, `blocked_cells`, `blocked_slots`,
`off_list_cells`, `stuck_cells`; the 202 carries `ceiling_seconds`. Event payloads arrive as
`{status, progress, message, data}`; "`data`" below means the event's `data` object (today's `data.data`).

Existing tests in `src/hooks/__tests__/useAutofillMachine.test.jsx` this phase edits, because the spec changes
the behaviour they pin: 1 (request gains `locked_cells`), 3, 4 (no suggestion suffix; spec §8 NOTE: the plan follows §2.3 over today's code),
4b/4c (fixtures need full result grids; same §8 NOTE), 5, 6, 7 (C7), 10 (stray events after the new
cancel flow). Its header's "No fake timers" note becomes false in Task 5.4 (`vi.useFakeTimers`). The shared
`gridFromRows` fixture may be extended with the two new fields.

### Task 5.1: Pure grid functions of the autofill merge

**Files:**
- Modify: `src/hooks/useAutofillMachine.js` (rewrite `mergeGridPreserveThemeLocked`; add the exports below)
- Test: `src/hooks/__tests__/useAutofillMachine.grid.test.js` (new)

**Interfaces:**
- Consumes: canonical cell fields (Task 4.1).
- Produces (Tasks 5.2–5.4; Phase 6 may use `clearBlocked`):

```js
export function mergeGridPreserveThemeLocked(currentGrid, cliGrid): object[][]
export function lockedCellsOf(grid): Array<[number, number]>
export function markBlocked(grid, cells /* [[r, c], ...] */): object[][]
export function clearBlocked(grid): object[][]          // every cell a new object, isBlocked false
export function resultGridIsFull(cliGrid): boolean      // no '.' and no '' cell
export function fillsAnyCell(snapshotGrid, cliGrid): boolean
```

**Behavioral criteria:**
- Merge (§2.3 Merge; §3.7): defined against the **current** grid. A cell is writable iff it is not `isThemeLocked` and is either an empty white cell (`!isBlack && letter === ''`) or `isAutofilled`. A writable cell given a letter becomes `{...cell, letter, isAutofilled: true}` (letter passed through as today); given `'.'` or `''` becomes `{...cell, letter: '', isAutofilled: false}`; given `'#'` becomes `{...cell, isBlack: true, letter: '', isAutofilled: false}`. A non-writable cell is returned as the same object. `isBlocked` and `isError` are never changed. Never changes a user's letter.
- `lockedCellsOf` (§2.3 Lock list): every cell with `!isBlack && letter !== ''` and (`isThemeLocked` or `!isAutofilled`), as `[row, col]`, row-major order. `[]` when none.
- `markBlocked`: listed cells become new objects with `isBlocked: true`; others keep their object (§2.3 Red cells).
- `fillsAnyCell` (§2.3 table, cancelled row: "if any progress grid filled at least one cell"): true iff some `(r, c)` holds a letter (not `'#'`, `'.'`, `''`) in `cliGrid` while the snapshot's cell is white, empty and not theme-locked.

**Normative cases** — merge (current cell → CLI cell → result):

| current | CLI | result |
|---|---|---|
| white `''`, not autofilled | `'A'` | `letter 'A'`, `isAutofilled T` |
| `'B'`, `isAutofilled T` | `'C'` | `letter 'C'`, `isAutofilled T` |
| `'B'`, `isAutofilled T` | `'.'` | `letter ''`, `isAutofilled F` |
| `'D'`, `isAutofilled F` (user) | `'E'` / `'.'` / `'#'` | same object |
| `'F'`, `isThemeLocked T` | `'G'` | same object |
| white `''`, `isThemeLocked T` | `'G'` | same object |
| white `''` | `'#'` | `isBlack T`, `letter ''`, `isAutofilled F` (§2.3 Tests: black-square branch leaves `letter: ''`) |
| `'B'`, `isAutofilled T` | `'#'` | `isBlack T`, `letter ''`, `isAutofilled F` |
| black | `'A'` / `'.'` | same object |
| `'D'` user, `isBlocked T` | `'D'` | same object, `isBlocked T` |

`lockedCellsOf` on a 3×3 grid (§2.3 Tests: "white theme-locked cells with letters and non-autofilled letters only"):

| cell | included |
|---|---|
| `(0,0)` `'A'`, user | yes |
| `(0,1)` `'B'`, `isAutofilled T` | no |
| `(0,2)` `''`, `isThemeLocked T` | no |
| `(1,0)` `'C'`, `isAutofilled T`, `isThemeLocked T` | yes |
| `(1,1)` black, `letter 'Z'` | no |
| `(2,0)` `'D'`, user, `isBlocked T` | yes |
| → result | `[[0,0],[1,0],[2,0]]` |
| every letter autofilled, none theme-locked | `[]` |

`fillsAnyCell`: snapshot `(0,1)` empty white, CLI `(0,1)` `'A'` → `true`; CLI letters only on cells the snapshot already holds → `false`; CLI `'#'` on an empty cell only → `false`.

- [ ] **Step 1: Write the failing tests**, every row.
- [ ] **Step 2: Run** `npx vitest run src/hooks/__tests__/useAutofillMachine.grid.test.js`.
- [ ] **Step 3: Implement**, citing `novice-readiness spec 0.2.4 §2.3 (G12)` on the merge.
- [ ] **Step 4: Run** the same, then `npx vitest run` (test 12, theme-locked cells never overwritten, stays green), then `npm run build`.
- [ ] **Step 5: Commit**

```bash
git add src/hooks/useAutofillMachine.js src/hooks/__tests__/useAutofillMachine.grid.test.js
git commit -m "feat(autofill): merge writes only empty or autofilled cells and marks provenance"
```

### Task 5.2: Start, snapshot, lock list, document id, running branch

**Files:**
- Modify: `src/hooks/useAutofillMachine.js` (hook params, `start`, the `running` branch, return object, module doc comment's contract line)
- Modify: `src/hooks/useNumbering.js` (return `invalidate`)
- Modify: `src/App.jsx` (pass `docId`, `onStart`, `onToast` to the hook; `docId` to `AutofillPanel`)
- Modify: `src/components/bench/AutofillPanel.jsx` (`docId` prop; `handleStart` passes it)
- Test: `src/hooks/__tests__/useAutofillMachine.test.jsx`, `src/hooks/__tests__/useNumbering.test.jsx`, `src/components/bench/__tests__/AutofillPanel.test.jsx`

**Interfaces:**
- Consumes: Task 5.1 functions; `docId` (Task 4.2); `LIVE_STATES` (Task 4.4).
- Produces (Phase 6 consumes `startSnapshot` for S2 and `start`'s arity):

```js
useAutofillMachine({ grid, gridSize, docId, onGridUpdate, onStart, onToast })
  -> { state, taskId, progress, message, errorCard, offer, startSnapshot,
       start, cancel, reset, keepFill, discardRun }        // offer/keepFill/discardRun: Task 5.3
start(options = {}, docId: string): void
// start(options, docId): docId is the document id at Start; it is stored with the snapshot (the start document id).
// The hook's own `docId` parameter is App's CURRENT id, compared against the stored one at every merge, Restore and "Keep partial fill".
// onStart: () => void, called once per accepted start(); onToast: ({kind, message}) => void
useNumbering(...) -> { numbering, violations, unverified, invalidate }   // invalidate(): ++tokenRef.current
AutofillPanel({ machine, grid, docId })
```

App wiring: `const invalidateNumberingRef = useRef(() => {})`; after `useNumbering`, `invalidateNumberingRef.current = invalidate`; the hook gets `onStart: () => invalidateNumberingRef.current()`, `onToast: pushToast`, `docId`.

**Behavioral criteria:**
- `start(options, docId)` is accepted only from `idle` (unchanged guard). On acceptance, in this order: `snapshot = clearBlocked(gridRef.current)` (a full copy, every cell a new object, no red: "Start clears all red cells **on the copy it snapshots**"); the start document id `= docId`; `startSnapshot` (returned) `= snapshot`; `onGridUpdate(prev => clearBlocked(prev))` ("Start clears all red"); `onStart()` (bumps `useNumbering`'s token so an in-flight reconcile cannot land mid-run); then `api.startFill` with `grid: toCliStrings(snapshot)` and `locked_cells: lockedCellsOf(snapshot)`, **always** present, `[]` included (§2.3 Lock list, M3), other fields as today. Any retained last grid and offer from a previous run are cleared.
- `startSnapshot` is `null` until the first accepted `start`; Task 5.3's `discardRun` nulls it again.
- Doc-id rule (§2.3 M1): every merge and every red-marking write the machine makes while live is skipped when the hook's current `docId` differs from the start document id.
- `running` event (§2.3): progress/message as today. If `data.grid` is present: remember it as the last grid, then merge it (`onGridUpdate(prev => mergeGridPreserveThemeLocked(prev, data.grid))`). Case 2 (§2.3 Red cells, C4): if `data.off_list_cells` is a non-empty list, `onGridUpdate(prev => markBlocked(prev, data.off_list_cells))` and, when `data.warning` (a string; the C4 key, Cross-phase pins) is present, `onToast({ kind: 'info', message: data.warning })`, while the run continues.
- `useNumbering`'s `invalidate()` increments `tokenRef.current` and nothing else, so every already-issued numbering/validation resolution fails its token guard.
- `AutofillPanel`'s `handleStart` calls `machine.start({ ...options, themeEntries: getThemeEntries(grid) }, docId)`.

**Normative cases:**

| situation | result |
|---|---|
| grid: `(0,0)` `'A'` user `isBlocked T`; `(0,1)` `'B'` autofilled; rest empty; `start({}, 'doc-1')` | `startFill` called with `locked_cells: [[0,0]]`; `startSnapshot[0][0].isBlocked === false`; `onGridUpdate` called with an updater that clears `isBlocked`; `onStart` called once |
| every letter autofilled; `start({}, 'd')` | `locked_cells: []` (key present) |
| `start` while `submitting` | no second `startFill`, no second `onStart` |
| hook `docId 'doc-1'`, `start({}, 'doc-1')`, running event with `data.grid` | `onGridUpdate` called with the merge |
| same, then rerender with `docId 'doc-2'`, running event with `data.grid` | `onGridUpdate` not called (the doc-id drop, §2.3 Tests) |
| running event `data: { off_list_cells: [[2,0],[2,1]], warning: 'Typed words not in the selected word lists: QZX' }` | cells `(2,0)`, `(2,1)` marked `isBlocked`; `onToast` with that text; state still `running` |
| `useNumbering`: structural edit, debounce fires, `invalidate()`, then `numberGrid` resolves | no reconciling `setGrid`, `unverified` stays `true` |
| `AutofillPanel` with `docId 'doc-9'`, Start clicked | `machine.start` called with `(options, 'doc-9')` |

- [ ] **Step 1: Write the failing tests**; update test 1's expected request with `locked_cells`.
- [ ] **Step 2: Run** `npx vitest run src/hooks/__tests__/useAutofillMachine.test.jsx src/hooks/__tests__/useNumbering.test.jsx src/components/bench/__tests__/AutofillPanel.test.jsx`.
- [ ] **Step 3: Implement**, citing `novice-readiness spec 0.2.4 §2.3 (M1)` at the doc-id check and `(M3)` at `locked_cells`.
- [ ] **Step 4: Run** the same, then `npx vitest run`, then `npm run build`.
- [ ] **Step 5: Commit**

```bash
git add src/hooks/useAutofillMachine.js src/hooks/useNumbering.js src/App.jsx src/components/bench/AutofillPanel.jsx src/hooks/__tests__/useAutofillMachine.test.jsx src/hooks/__tests__/useNumbering.test.jsx src/components/bench/__tests__/AutofillPanel.test.jsx
git commit -m "feat(autofill): Start snapshots the grid, sends the lock list and guards merges by document id"
```

### Task 5.3: Terminal outcomes, restore, red cells and the Keep offers

**Files:**
- Modify: `src/hooks/useAutofillMachine.js` (`complete`, `paused`, `error` branches; `offer`, `keepFill`, `discardRun`, `reset`)
- Test: `src/hooks/__tests__/useAutofillMachine.test.jsx`

**Interfaces:**
- Consumes: Tasks 5.1, 5.2.
- Produces (Task 5.5 renders it; Phase 6's New grid / Open saved call `discardRun`):

```js
offer: null | { kind: 'keepFill' | 'keepPartialFill', slotsFilled: number | null, totalSlots: number | null }
keepFill(docId: string): void
discardRun(): void
```

**Behavioral criteria:**
- **Restore** (§2.3): `onGridUpdate(() => markBlocked(snapshot, red))`, one updater, so restore lands first and red lands on the restored grid ("Order on a terminal outcome"). `red` = the union of `data.blocked_cells`, `data.stuck_cells` and `data.off_list_cells`, each treated as `[]` when absent. Doc-id: planning default `PD-5D` (spec §8) (restore is skipped when the current `docId` differs from the start document id).
- `complete`: checks `data.blocked === true` **first** (§2.3, B3). Then the table below, row by row. On `success: true` the grid is the merged result, `onGridUpdate(prev => markBlocked(mergeGridPreserveThemeLocked(prev, data.grid), red))`, subject to the doc-id rule; red marked by the running branch persists because the merge never writes a user's letter.
- The "every slot filled" predicate is `resultGridIsFull(data.grid)` (§2.3 table: "the result grid has no empty white cell"), replacing today's count-based `allSlotsFilled` (spec §8 NOTE: the plan follows §2.3 over today's code).
- When `state` is `failed`, the outcome's text is in `errorCard.message`; otherwise in `message` (today's split, which `AutofillPanel` renders).
- Offers: `offer` is `null` whenever the hook's current `docId` differs from the start document id ("offered only while the document id `App` passes still matches Start's"). `keepFill(docId)`: no-op unless an offer is showing and `docId` equals the start document id; otherwise `onGridUpdate(prev => mergeGridPreserveThemeLocked(prev, lastGrid))` against the grid as it is when clicked, then `offer = null`; state unchanged. The last grid is the last `data.grid` received on any event (`running`, `complete`, `paused`).
- `reset()`: as today, and clears `offer`; keeps `startSnapshot`. `discardRun()`: from any state not in `LIVE_STATES`, moves to `idle` with `taskId`, `progress`, `message`, `errorCard`, `offer`, the last grid and `startSnapshot` all cleared; from a live state, no-op (§3.2: New grid clears "any retained snapshot or 'Keep partial fill' offer").

**Normative cases** — one test per row (§2.3 Tests). Fixture: 4×4 white grid, user letter `'U'` at `(0,0)`, `start({}, 'doc-1')`, hook `docId 'doc-1'`; `S` = the Start snapshot; `Gfull` = a CLI grid with no `'.'`; `Gpart` = a CLI grid with `'.'` cells.

| # | event `data` | state | grid afterwards | `offer` | text |
|---|---|---|---|---|---|
| 1 | `complete`, `{success:true, grid:Gfull, slots_filled:8, total_slots:8}` | `done` | merge of `Gfull` onto current; `(0,0)` still `'U'`, not autofilled | `null` | `Successfully filled 8/8 slots!` |
| 2 | `complete`, `{success:false, grid:Gfull, slots_filled:8, total_slots:8, problematic_slots_count:2}` | `done` | `S` | `{kind:'keepFill'}` | `Filled 8/8 slots — 2 entries may be invalid (use Verify Words to check)` |
| 2b | as 2, `problematic_slots_count` absent | `done` | `S` | `{kind:'keepFill'}` | `Filled 8/8 slots — some entries may need review (use Verify Words to check)` (planning default `PD-5G` (spec §8)) |
| 2c | `complete`, `{success:false, grid:Gpart, slots_filled:8, total_slots:8, fill_percentage:100}` | `done` | `S` | `keepPartialFill` 8/8 | `Partial: 8/8 slots (100%)` (the grid decides, not the counts) |
| 3 | `complete`, `{success:false, grid:Gpart, slots_filled:5, total_slots:8, fill_percentage:62, stuck_cells:[], suggestions:[{message:'x'}]}` | `done` | `S` | `{kind:'keepPartialFill', slotsFilled:5, totalSlots:8}` | `Partial: 5/8 slots (62%)` |
| 4 | as 3 with `stuck_cells:[[0,0]]` | `done` | `S`, `(0,0)` `isBlocked T` | as 3 | `Autofill could not fill around the highlighted letters.` |
| 5 | `complete`, `{success:false, blocked:true, reason:'no_word_fits', blocked_cells:[[0,0]], blocked_slots:[…], off_list_cells:[], stuck_cells:[], grid:<input>}` | planning default `PD-5C` (spec §8): `failed` | `S`, `(0,0)` `isBlocked T` | `null` | `No word fits the highlighted letters.` |
| 6 | `complete`, `{…, blocked:true, reason:'no_word_of_length', blocked_cells:[], blocked_slots:[{row:0,col:0,direction:'across',length:4,pattern:'U???'}], …}` | as 5 | `S`, no red | `null` | `The selected word lists have no words of length 4.` (several lengths: planning default `PD-5F` (spec §8)) |
| 7 | `complete`, no `data.grid` | `failed` | `S` | `null` | `No solution found` |
| 8 | progress `Gpart` filled `(0,1)`, then cancelled (Task 5.4's 200 path) | `cancelled` | `S` | `{kind:'keepPartialFill', slotsFilled:null, totalSlots:null}` | `Cancelled by user` |
| 8b | cancelled with no progress grid | `cancelled` | `S` | `null` | `Cancelled by user` |
| 9 | `paused`, `data.grid` filling `(0,1)` | `paused`, `taskId` kept | `S` | as 8 | `Autofill was paused outside the app.` |
| 10 | `error`, `message:'CLI Error (code 1): boom'`, after a progress grid filling `(0,1)` | `failed` | `S` | as 8 | `CLI Error (code 1): boom` |
| 11 | lost contact (Task 5.4) | `failed` | `S` | as 8 | `Lost contact with the autofill run.` |
| 12 | row 1 with `off_list_cells:[[0,0]]` | `done` | merged; `(0,0)` `isBlocked T` | `null` | as row 1 |

Further rows:

| situation | result |
|---|---|
| row 3, then `keepFill('doc-1')` | `onGridUpdate` merges `Gpart` onto the current grid; `offer` `null` |
| row 3, a letter typed into an empty cell after the run, then `keepFill('doc-1')` | that letter stays (the merge skips a user cell) |
| row 3, rerender `docId 'doc-2'` | `offer` `null`; `keepFill('doc-2')` is a no-op |
| row 3, `reset()` | `idle`, `offer` `null`, `startSnapshot` unchanged |
| row 3, `discardRun()` | `idle`, `offer` `null`, `startSnapshot` `null` |
| `discardRun()` while `running` | no change |

Rows 8/8b are written against today's `cancel()` (immediate transition to `cancelled`); Task 5.4 re-pins *when* that transition happens (on the 200), and its tests drive rows 8/8b through the new path.

- [ ] **Step 1: Write the failing tests** (update 3, 4, 4b, 4c, 5, 6 to the rows above).
- [ ] **Step 2: Run** `npx vitest run src/hooks/__tests__/useAutofillMachine.test.jsx`.
- [ ] **Step 3: Implement**, citing `novice-readiness spec 0.2.4 §2.3` at the outcome table and `(B3)` at the blocked check.
- [ ] **Step 4: Run** the same, then `npx vitest run`, then `npm run build`.
- [ ] **Step 5: Commit**

```bash
git add src/hooks/useAutofillMachine.js src/hooks/__tests__/useAutofillMachine.test.jsx
git commit -m "feat(autofill): every unfinished run restores the Start grid, marks red and offers the fill"
```

### Task 5.4: The panel never strands (§2.4 client: submit timeout, watchdog, C8, C7)

**Files:**
- Modify: `src/hooks/useAutofillMachine.js` (`start`'s submit timeout, watchdog, `handleStreamError`, `cancel`, the `error`/`complete` branches while a cancel is pending, unmount cleanup)
- Test: `src/hooks/__tests__/useAutofillMachine.test.jsx` (fake timers for the timer cases)

**Interfaces:**
- Consumes: Tasks 5.2, 5.3 (restore, offers); `api.cancelFill`, `ApiError.status`.
- Produces:

```js
export const SUBMIT_TIMEOUT_MS = 30000;     // planning default `PD-5H` (spec §8): 30 s
export const WATCHDOG_GRACE_MS = 30000;     // P4
export function isKillError(message: string): boolean   // message.startsWith('CLI Error (code -')  (PD-3-KILL)
```

**Behavioral criteria:**
- **Submit timeout** (§2.4 Submit exit): armed on entering `submitting`; fires after `SUBMIT_TIMEOUT_MS` (30 s) if still `submitting`: `failed` with `Lost contact with the autofill run.`, restore (Task 5.3). A 202 arriving later is ignored (no stream, no watchdog, state stays `failed`) and its task cancelled best effort: `api.cancelFill(task_id)`, rejection swallowed (planning default `PD-5H` (spec §8): "30 s; `Lost contact with the autofill run.`; a 202 arriving later is ignored and its task cancelled best effort").
- **Watchdog** (§2.4 B4, P4): Start time recorded on entering `submitting`. When the 202 arrives with `ceiling_seconds`, the watchdog is keyed to `task_id` and set to fire at Start + `ceiling_seconds × 1000` + `WATCHDOG_GRACE_MS`. On firing, if the state is live and the task id matches: `api.cancelFill(taskId)` (best effort, rejection swallowed), close the stream, `failed` with `Lost contact with the autofill run.`, restore. Cleared on every transition to a non-live state and on unmount.
- **C8** (§2.4): any stream error while `running` closes the stream, calls `api.cancelFill(taskId)` best effort, moves to `failed` with `Lost contact with the autofill run.` (replacing `Connection error`), restores. A stream error in any other state is a no-op.
- **C7** (§2.4): `cancel()` in `running` calls `api.cancelFill(taskId)` first and keeps the stream open; state stays `running` with a cancel pending.
  - 200: if still `running`: close the stream, `cancelled`, `Cancelled by user`, restore, offer per Task 5.3 row 8.
  - Rejection with `status === 404`: the cancel is no longer pending; the machine keeps waiting on the open stream; the next terminal event or the watchdog decides.
  - Rejection with any other status: planning default `PD-5J` (spec §8) (as 404).
  - An `error` event while the cancel is pending: `isKillError(message)` (the message starts with `CLI Error (code -`: the route's text for a child killed by a signal, planning default `PD-3-KILL`) → as the 200 path (`cancelled`); otherwise → `failed` with that event's message ("shown as that error, not as `Cancelled by user`").
  - A `complete` or `paused` event while pending: handled as Task 5.3 shows it ("shown as what it is"); a later 200 is a no-op.
- **Cancel in `submitting`** (§2.4: "Cancel is available in `submitting` too"; early Cancel): planning default `PD-5I` (spec §8) (the cancel is recorded; when the 202 arrives the machine enters `running`, opens the stream and immediately proceeds as `cancel()` in `running`, posting `api.cancelFill(task_id)`).

**Normative cases** (fake timers; Start at t = 0):

| situation | result |
|---|---|
| 202 `{task_id:'t', ceiling_seconds:70}` at t = 0, no terminal event; advance to t = 99 999 ms | still `running`, `cancelFill` not called |
| same, advance to t = 100 000 ms | `failed`, `Lost contact with the autofill run.`, `cancelFill('t')` once, grid restored |
| 202 at t = 5 000 with `ceiling_seconds:70` | fires at t = 100 000, not 105 000 (keyed to Start) |
| row-1 `complete` at t = 10 000; advance past 100 000 | state `done`, `cancelFill` not called |
| unmount while `running`; advance past the deadline | `cancelFill` not called |
| `startFill` never resolves; advance to `SUBMIT_TIMEOUT_MS` | `failed`, `Lost contact with the autofill run.`, grid restored |
| `startFill` resolves `{task_id:'t3', ceiling_seconds:70}` after `SUBMIT_TIMEOUT_MS` has fired | state stays `failed`; no stream opened; `cancelFill('t3')` called once; no watchdog armed |
| stream error while `running` | `failed`, `Lost contact with the autofill run.`, `cancelFill(taskId)` once, grid restored (§2.4 Tests: C8) |
| stream error after `done` | no change |
| `cancel()` while `running` | `cancelFill('t')` called; state `running`; stream not closed (a later progress event still updates `progress`) |
| …then `cancelFill` resolves 200 | `cancelled`, `Cancelled by user`, restored |
| …`cancelFill` rejects `{status:404}`, then a `complete` row-3 event | state `done`, `Partial: 5/8 slots (62%)` (§2.4 Tests: C7 404 keeps waiting for the kept terminal event) |
| …`cancelFill` rejects `{status:404}`, no event; advance to the deadline | `failed`, `Lost contact with the autofill run.` |
| `cancel()`, then `error` event `CLI Error (code -9): …` (the kill's text, `PD-3-KILL`) before the 200 | `cancelled`, `Cancelled by user` |
| `cancel()`, then `error` event `CLI Error (code 1): boom` or `Autofill changed a locked letter; nothing was written.` (neither starts `CLI Error (code -`) | `failed`, that text (§2.4 Tests: pending-cancel error) |
| `cancel()` while `submitting`, then 202 `{task_id:'t2', ceiling_seconds:70}` | `cancelFill('t2')` called; stream opened; a 200 then gives `cancelled` (§2.4 Tests: early Cancel, client side) |

- [ ] **Step 1: Write the failing tests** (update tests 7 and 10 to the new cancel flow).
- [ ] **Step 2: Run** `npx vitest run src/hooks/__tests__/useAutofillMachine.test.jsx`.
- [ ] **Step 3: Implement**, citing `novice-readiness spec 0.2.4 §2.4 (B4)`, `(C7)`, `(C8)`.
- [ ] **Step 4: Run** the same, then `npx vitest run`, then `npm run build`.
- [ ] **Step 5: Commit**

```bash
git add src/hooks/useAutofillMachine.js src/hooks/__tests__/useAutofillMachine.test.jsx
git commit -m "fix(autofill): a lost stream, a dead run or a late Cancel never strands the panel (#41)"
```

### Task 5.5: Autofill panel — theme entries, min score 30, Start hints, Cancel, Keep buttons

**Files:**
- Modify: `src/components/bench/AutofillPanel.jsx` (`getThemeEntries`, `DEFAULT_OPTIONS` and the comments above it and in the header, Start gating and hints, Cancel, the terminal and paused panels)
- Test: `src/components/bench/__tests__/AutofillPanel.test.jsx`

**Interfaces:**
- Consumes: the machine's `state`, `message`, `errorCard`, `offer`, `start`, `cancel`, `reset`, `keepFill` (Tasks 5.2–5.4); `allSlots` from `src/hooks/useGridGeometry.js`.
- Produces:

```js
export function getThemeEntries(grid): Record<string, string>   // keys `(${row},${col},${direction})`
```

**Behavioral criteria:**
- `getThemeEntries` (§2.3 Theme entries): an entry only for a slot of `allSlots(grid)` (length ≥ 2) whose **every** cell is white, `isThemeLocked` and has a letter; key format unchanged; the word is the slot's letters. A partial theme-locked run yields no entry (it goes only in the lock list).
- `DEFAULT_OPTIONS.minScore` is `30` (§2.5). The comment above `DEFAULT_OPTIONS` and the header paragraph that says "this panel's user-visible default (50, matching the old panel)" are rewritten to say the default is 30, the value the README's `fill` example uses, citing `novice-readiness spec 0.2.4 §2.5 (#40)`.
- Start (§2.3 I5, P18): disabled when `options.wordlists.length === 0`, with the hint text `Select at least one word list`; disabled when the empty-slot count is 0, with the hint text `Clear some cells to run autofill again`. Each hint renders exactly when its condition holds (both may show).
- Cancel renders in `submitting` and in `running` and calls `machine.cancel` (§2.4).
- Terminal panel: when `machine.offer` is non-null, a button whose label is `Keep fill` for `kind 'keepFill'`, `Keep partial fill (X/Y slots)` for `kind 'keepPartialFill'` with counts, `Keep partial fill` without counts; it calls `machine.keepFill(docId)` (§2.3 table). The `paused` panel shows `machine.message` (`Autofill was paused outside the app.`) in place of today's `paused — resume support lands with F11`, plus the offer button and Reset.

**Normative cases:**

| situation | result |
|---|---|
| 1×5 row, cells 0–2 theme-locked `C A T`, cell 3 black, cell 4 white | `{'(0,0,across)': 'CAT'}` |
| 1×5 row, cells 0–2 theme-locked `C A T`, cells 3–4 empty white | `{}` |
| 1×3 row fully theme-locked, `(0,1)` letter `''` | `{}` |
| 3×1 column fully theme-locked `D O G` | `{'(0,0,down)': 'DOG'}` |
| Start clicked with defaults | `machine.start` receives `minScore: 30` |
| all word lists unticked | Start disabled; `Select at least one word list` shown |
| grid with no empty slot | Start disabled; `Clear some cells to run autofill again` shown |
| state `submitting` | Cancel shown; click calls `machine.cancel` |
| `offer {kind:'keepPartialFill', slotsFilled:5, totalSlots:8}`, `docId 'd'`, click | label `Keep partial fill (5/8 slots)`; `machine.keepFill('d')` |
| `offer {kind:'keepPartialFill', slotsFilled:null, totalSlots:null}` | label `Keep partial fill` |
| `offer {kind:'keepFill', …}` | label `Keep fill` |
| state `paused`, `message 'Autofill was paused outside the app.'` | that text shown |

- [ ] **Step 1: Write the failing tests**; update "submitting state has no Cancel button", "paused state renders the exact stub text" and the minScore-50 expectation.
- [ ] **Step 2: Run** `npx vitest run src/components/bench/__tests__/AutofillPanel.test.jsx`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the same, then `npx vitest run`, then `npm run build`.
- [ ] **Step 5: Commit**

```bash
git add src/components/bench/AutofillPanel.jsx src/components/bench/__tests__/AutofillPanel.test.jsx
git commit -m "feat(autofill): panel defaults to min score 30, explains a disabled Start and offers the fill"
```
---

## Phase 6: grid UI (§3.1 hiding · §3.3 black squares · §3.2 New grid · §3.4 saves · §3.5 edit guards · §3.6 Theme panel and top bar · §3.8 theme suggestions)

Spec sections: §3.1, §3.3, §3.2, §3.4, §3.5, §3.6, §3.8 (§1's priority order; Task 6.3 lands the Grid panel with the Black square toggle first because §3.2's panel is the host of §3.3's button). Everything is frontend: no `cli/` or `backend/` change, no new endpoint. Commands run from the worktree root. Cite code by identifier; Phases 4 and 5 edit the same files, so line numbers below are today's and will have moved.

### Phase 6 conventions

- Run vitest per file during a task: `npx vitest run <path>`. The task's last gate before its commit is `npx vitest run` (whole frontend suite) and `npm run build`. Read each result, then commit in a separate command.
- Bench components take their classes from `src/styles/bench/base.css` (`xw-primary-btn`, `xw-ghost-btn`, `xw-danger-btn`, `xw-icon-btn`); new classes are appended there with an `xw-` prefix. No new styling system.
- Component and App tests mock `src/lib/storage` functions with `vi.spyOn(storage, ...)` as `src/hooks/__tests__/useSaveMachine.test.jsx` does, or back the `localStorage` mock bag with a `Map` as `src/lib/__tests__/storage.test.js` does (the global mock's `getItem` returns `undefined` by default; storage treats `== null` as absent).
- Every writer this phase adds or rewrites sets `isAutofilled: false` on every cell it writes, same letter included (§3.7, S5), and keeps Phase 4's write-time D1 gate (`editingPaused`) as its first statement.
- Docstrings cite `novice-readiness spec 0.2.4 §<section> (<finding id>)`.

### Names this phase consumes (pinned by the skeleton) and names it adds

Consumed, not planned here: `docId`/`setDocId`, `mintDocId()` (`src/lib/docId.js`), `isAutofilled`, `isBlocked`, `LIVE_STATES`, `editingPaused`, `autofill.startSnapshot`, `autofill.discardRun()` (Phase 5; drops `startSnapshot` and any "Keep" offer), `contentSigOf` extended by Phase 4, `skipNextInitRef`, `initializeGrid`, `pushToast`, `localNumber` (`src/hooks/useNumbering.js`), `mirrorOf(r, c, size)` (`src/hooks/useGridGeometry.js`, returns `[row, col]`), `api.cleanGrid`, `api.verifyWords`.

Also consumed, as pinned by earlier phases:
- the document id is minted by `initializeGrid` (Task 4.2), so New grid built through `initializeGrid` needs no second mint; Task 6.4 item (e) asserts the id differs;
- `toSavedGrid` (Task 4.1) strips `isBlocked` from saves;
- the write-time gate is `editingPausedRef` (Task 4.4).

Added by this phase (names are binding on later tasks in this phase):

| Name | Path | Task |
|---|---|---|
| `src/lib/gridEdits.js`: new exports `canToggleBlack`, `gridHasContent`, `applyVerifyErrors`, `planClean`, `clearAllErrors`; amends Phase 4's `writePatternWord` (Task 6.10) and `writeCleanedGrid` (Task 6.11) | **Modify** (the file and the seven `write*` helpers are created in Task 4.3; it is in the skeleton's File Structure table) | 6.2, 6.4, 6.10, 6.11 |
| `GRID_HINT` (string constant) | `src/components/bench/GridHintLine.jsx` | 6.2 |
| `normalizeSavedGrid(grid)` | `src/api/gridCodec.js` | 6.5 |
| `list`, `remove`, `save(doc, opts)`, `load`, `defaultName`, `formatStamp`, `SAVE_KEY`, `LEGACY_SAVE_KEY` | `src/lib/storage.js` | 6.5 |
| `saveNamed`, `adoptSavedAt`, `onForked` | `src/hooks/useSaveMachine.js` | 6.6 |
| CSS custom property `--xw-topbar-h` | `src/styles/bench/tokens.css` | 6.12 |
| `SUGGESTION_REFETCH_DEBOUNCE_MS` (export) | `src/components/ThemeWordsPanel.jsx` | 6.13 |

### Task 6.1: Hide the unfinished controls (§3.1, G10)

**Files:**
- Modify: `src/components/bench/ToolRail.jsx` (`TOOLS`, the Heatmap `<button>`, `ICONS.clues`)
- Modify: `src/components/bench/AutofillPanel.jsx` (`SuggestBlackSquareButton` and its two render sites: the `state === 'running'` actions row and the `state === 'idle'` footer `emptySlots > 0 &&` line)
- Modify: `src/components/ExportPanel.jsx` (the `pdf` and `puz` `<option>`s, the `include-clues` checkbox block and the `includeClues` state, the `PDF` and `.puz` `<dt>`/`<dd>` pairs)
- Modify: `src/App.jsx` (the `currentTool === 'clues'` inspector block; the `heatmapOn` state and `viewToggles.heatmap`)
- Test: `src/components/bench/__tests__/ToolRail.test.jsx`, `src/components/bench/__tests__/AutofillPanel.test.jsx`, `src/__tests__/components/ExportPanel.test.jsx`, `src/__tests__/components/App.test.jsx`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `ToolRail` renders exactly the tools `Grid, Search, Autofill, Theme, Lists, Import, Export` and the VIEW toggle `Symmetry`. `ToolRail`'s `viewToggles` prop is `{ symmetry }` (a `heatmap` key is ignored if passed) and `onToggleView` is only ever called with `'symmetry'`. `CrosswordGrid`'s `heatmap` prop stays (issue #50 stays open).

**Behavioral criteria:**
- The Clues tool button is not rendered (§3.1, #53). The Heatmap toggle is not rendered (§3.1, #50). No `Suggest Black Square` button renders in the idle footer or the running actions row (§3.1, #54); the running row keeps Cancel.
- `ExportPanel` renders no `PDF (coming soon)` option, no `.puz (coming soon)` option, no `Include clues (if available)` checkbox, and its Format Information list has no `PDF` or `.puz` term (§3.1, G10). The JSON, HTML and Text options and terms are unchanged.
- The App's unreachable `clues` inspector block and the dead `heatmapOn` state are removed with the controls that fed them.
- The GitHub issues stay open; nothing is closed by trailer (`.claude/CLAUDE.md`, #21 lesson): the commit message must not contain `Closes`/`Fixes`.

**Normative cases** (the implementer's tests must cover every row; exact strings):

| Surface | Must not render (query returns nothing) | Must still render |
|---|---|---|
| `ToolRail` | text `Clues`; text `Heatmap` | `Grid`, `Search`, `Autofill`, `Theme`, `Lists`, `Import`, `Export`, `Symmetry`; clicking each tool calls `onSelectTool` with `edit`, `search`, `autofill`, `theme`, `lists`, `import`, `export` |
| `AutofillPanel` (idle, `emptySlots > 0`) | button named `/suggest black square/i` | `Start Autofill` |
| `AutofillPanel` (`state: 'running'`) | button named `/suggest black square/i` | `Cancel` |
| `ExportPanel` | `PDF (coming soon)`; `.puz (coming soon)`; `Include clues (if available)`; a `dt` with text `PDF`; a `dt` with text `.puz` | options matching `JSON`, `HTML`, `Text`; `dt`s `JSON`, `HTML`, `Text` |

**Existing tests that change (spec §3.1 names them):**
- `ToolRail.test.jsx`: `TOOL_IDS`/`TOOL_LABELS` lose `clues`/`Clues`; the title of the "renders all … tools" test must stop stating a number; the `clicking Heatmap…` and the two `viewToggles.heatmap` tests are deleted or rewritten into the absence assertions; the Symmetry-with-`heatmap:false` test keeps working without the key. (Spec §3.1 reads: "its `TOOL_LABELS` assertion for Clues and the separate Heatmap tests": `TOOL_LABELS` holds only `Clues`; the Heatmap tests are the separate ones named here.)
- `AutofillPanel.test.jsx`: the two tests `"Suggest Black Square" is present but disabled…` (running and idle) become absence assertions.
- `App.test.jsx`: add one assertion that the rail has no `Clues` and no `Heatmap` text in a mounted `App`.

- [ ] **Step 1: Write the failing tests.** Edit the four test files per the table and the list above; design the exact assertions yourself.
- [ ] **Step 2: Run** `npx vitest run src/components/bench/__tests__/ToolRail.test.jsx src/components/bench/__tests__/AutofillPanel.test.jsx src/__tests__/components/ExportPanel.test.jsx src/__tests__/components/App.test.jsx`. Expected: the new absence assertions fail because the controls still render (not because a test is broken).
- [ ] **Step 3: Implement** the removals.
- [ ] **Step 4: Run** the four files again, then `npx vitest run` and `npm run build`. Expected: all green, build clean.
- [ ] **Step 5: Commit** (after reading the results):

```bash
git add src/components/bench/ToolRail.jsx src/components/bench/AutofillPanel.jsx src/components/ExportPanel.jsx src/App.jsx src/components/bench/__tests__/ToolRail.test.jsx src/components/bench/__tests__/AutofillPanel.test.jsx src/__tests__/components/ExportPanel.test.jsx src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "feat(ui): hide Clues, Heatmap, Suggest Black Square and the dead export options"
```

### Task 6.2: Black-square guard rule and the key hint line (§3.3, G7)

**Files:**
- Modify: `src/lib/gridEdits.js` (created in Task 4.3; adds `canToggleBlack`)
- Create: `src/components/bench/GridHintLine.jsx`
- Modify: `src/App.jsx` (`toggleBlackSquare`; render `GridHintLine` under `CrosswordGrid`)
- Modify: `src/styles/bench/base.css` (`.xw-grid-hint`)
- Test: `src/lib/__tests__/gridEdits.test.js` (created in Task 4.3), `src/components/bench/__tests__/GridHintLine.test.jsx` (create), `src/__tests__/components/App.test.jsx`

**Interfaces:**
- Consumes: `mirrorOf` from `src/hooks/useGridGeometry.js`; `dispatchGridKey` from `src/components/bench/CrosswordGrid.jsx`; Phase 4's gated `toggleBlackSquare(row, col)` and its `isAutofilled` clearing.
- Produces:

```js
// src/lib/gridEdits.js
/** G7: false when the cell, or with symmetry its mirror partner, is theme-locked. Out-of-range -> false. */
export function canToggleBlack(grid: Cell[][], row: number, col: number, symmetryEnabled: boolean): boolean;
```

```jsx
// src/components/bench/GridHintLine.jsx
export const GRID_HINT: string;   // exactly the §3.3 line
export default function GridHintLine(): JSX.Element;   // renders GRID_HINT in a <p className="xw-grid-hint">
```

**Behavioral criteria:**
- `canToggleBlack` is `false` when `grid[row][col].isThemeLocked`; with `symmetryEnabled` also `false` when the `mirrorOf(row, col, grid.length)` cell is `isThemeLocked`; otherwise `true` (§3.3, G7). With symmetry off the partner is never consulted. The centre cell's partner is itself.
- `toggleBlackSquare` returns without changing the grid when `canToggleBlack` is `false`: no partial write (neither the cell nor the partner changes). The key path (`dispatchGridKey` → `onToggleBlack`) and Task 6.3's button both reach this one function (§3.3).
- `toggleBlackSquare` writes new cell objects for the cell and its partner and does not mutate the previous grid's cells (the G6 rule applied to the function this task rewrites; if Phase 4 already did so, nothing changes).
- `GridHintLine` is rendered under the grid whenever the grid renders, in every tool, and its text is exactly `GRID_HINT`.
- `GRID_HINT` equals, character for character (`·` is U+00B7): `Type letters · Arrows move · Space or . black square · Enter switch direction · Tab next word · Backspace clear` (§3.3).

**Normative cases — `canToggleBlack`** (5×5 grid, `TL` = `isThemeLocked`; mirror of (r,c) is (4-r,4-c)):

| selected | TL cells | symmetryEnabled | result |
|---|---|---|---|
| (1,1) | none | true | `true` |
| (1,1) | (1,1) | true | `false` |
| (1,1) | (1,1) | false | `false` |
| (1,1) | (3,3) | true | `false` |
| (1,1) | (3,3) | false | `true` |
| (2,2) | (2,2) | true | `false` |
| (1,1) | (0,0) | true | `true` |

**Normative cases — hint test** (G7 sibling; spec: "every key the line names is handled by `dispatchGridKey`; it does not require the reverse"). The test splits `GRID_HINT` on ` · ` and fails if any segment has no row here, so a later key added to the line forces a handler. Focus is a white, empty, unlocked cell with neighbours on every side, `selectedDir: 'across'`, slots from `allSlots`:

| hint segment | key descriptor(s) fed to `dispatchGridKey` | required in result |
|---|---|---|
| `Type letters` | `{ key: 'a' }` | `preventDefault: true`; an action of type `setLetter` with `ch: 'A'` |
| `Arrows move` | `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight` | each `preventDefault: true` and a `moveFocus` action |
| `Space or . black square` | `{ key: ' ' }` and `{ key: '.' }` | each yields a `toggleBlack` action |
| `Enter switch direction` | `{ key: 'Enter' }` | a `rotateDir` action |
| `Tab next word` | `{ key: 'Tab' }` | a `moveFocus` action |
| `Backspace clear` | `{ key: 'Backspace' }` on a cell that holds a letter | a `setLetter` action with `ch: ''` |

**Normative cases — App (G7, through the UI):** with symmetry on, Ctrl+L on cell A locks it; selecting A and pressing Space leaves A white; selecting A's mirror partner and pressing Space leaves both white (the partner of a locked cell is refused too). The App test uses the existing `cells(container)` / key-event style of `App.test.jsx`.

- [ ] **Step 1: Write the failing tests** (`gridEdits.test.js`, `GridHintLine.test.jsx`, the App cases) from the tables.
- [ ] **Step 2: Run** `npx vitest run src/lib/__tests__/gridEdits.test.js src/components/bench/__tests__/GridHintLine.test.jsx src/__tests__/components/App.test.jsx`. Expected: fail because `gridEdits.js`/`GridHintLine.jsx` do not exist and the partner of a locked cell still toggles.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the three files, then `npx vitest run` and `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/lib/gridEdits.js src/lib/__tests__/gridEdits.test.js src/components/bench/GridHintLine.jsx src/components/bench/__tests__/GridHintLine.test.jsx src/App.jsx src/styles/bench/base.css src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "feat(grid): refuse black squares on theme-locked cells and partners; add the key hint line"
```

### Task 6.3: The Grid panel with the Black square toggle (§3.3, §3.2 panel)

**Files:**
- Create: `src/components/bench/GridPanel.jsx`
- Modify: `src/App.jsx` (replace the `currentTool === 'edit'` block that renders `xw-inspector-empty` / `Grid editor`)
- Modify: `src/styles/bench/base.css`
- Test: `src/components/bench/__tests__/GridPanel.test.jsx` (create), `src/__tests__/components/App.test.jsx`

**Interfaces:**
- Consumes: `canToggleBlack` (6.2); `editingPaused` (Phase 4); App's `toggleBlackSquare`, `selectedCell` (`{row, col, direction}` or `null`), `symmetryEnabled`, `gridSize`, `grid`.
- Produces (Tasks 6.4 and 6.9 extend the props; the first three are final now):

```jsx
export default function GridPanel(props: {
  grid: Cell[][] | null;
  gridSize: number;
  selectedCell: { row: number; col: number; direction: 'across' | 'down' } | null;
  symmetryEnabled: boolean;
  editingPaused: boolean;
  onToggleBlack: (row: number, col: number) => void;   // App.toggleBlackSquare
}): JSX.Element;
```

**Behavioral criteria:**
- For tool `edit`, `App` renders `GridPanel` in `.xw-inspector` in place of the static `Grid editor` placeholder (§3.2).
- The panel has a button named exactly `Black square`. Clicking it calls `onToggleBlack(selectedCell.row, selectedCell.col)`, i.e. acts on the selected cell exactly as Space and `.` do, symmetry included (§3.3).
- The button is disabled when `selectedCell` is `null`, when `canToggleBlack(grid, row, col, symmetryEnabled)` is `false` (G7), or when `editingPaused` (D1, §2.3). It carries `aria-pressed` = whether the selected cell is currently black.
- The panel hides no other control yet; Tasks 6.4 and 6.9 add New grid and Open saved.

**Normative cases:**

| state | `Black square` button |
|---|---|
| no selected cell | disabled |
| selected (1,1), nothing locked | enabled; click → `onToggleBlack(1, 1)` |
| selected (1,1) is theme-locked | disabled |
| selected (1,1), symmetry on, mirror (3,3) theme-locked (5×5) | disabled |
| same, symmetry off | enabled |
| `editingPaused` true, otherwise enabled | disabled |
| mounted `App`, select a cell, click `Black square` | the cell and its mirror become black; with symmetry off only the cell |

- [ ] **Step 1: Write the failing tests** (`GridPanel.test.jsx` per the table; one App-level case for the last row).
- [ ] **Step 2: Run** `npx vitest run src/components/bench/__tests__/GridPanel.test.jsx src/__tests__/components/App.test.jsx`. Expected: fail because `GridPanel` does not exist.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the two files, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/components/bench/GridPanel.jsx src/components/bench/__tests__/GridPanel.test.jsx src/App.jsx src/styles/bench/base.css src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "feat(ui): Grid panel with a Black square toggle replaces the editor placeholder"
```

### Task 6.4: In-panel confirm and New grid (§3.2, #55)

**Files:**
- Create: `src/components/bench/InlineConfirm.jsx`
- Modify: `src/components/bench/GridPanel.jsx`
- Modify: `src/App.jsx` (add `createNewGrid`; wire `onNewGrid`; reset `selectedCell`)
- Modify: `src/lib/gridEdits.js` (`gridHasContent`)
- Modify: `src/styles/bench/base.css`
- Test: `src/components/bench/__tests__/InlineConfirm.test.jsx` (create), `src/components/bench/__tests__/GridPanel.test.jsx`, `src/lib/__tests__/gridEdits.test.js`, `src/__tests__/components/App.test.jsx`

**Interfaces:**
- Consumes: Phase 4 `docId`/`setDocId`/`mintDocId`, `editingPaused`, `initializeGrid`; Phase 5 `autofill.discardRun()`; `localNumber` from `src/hooks/useNumbering.js`.
- Produces:

```jsx
// shared by New grid (this task), Open saved (6.9), the save-name collision (6.7) and Clean (6.11)
export default function InlineConfirm(props: {
  message: string;
  confirmLabel: string;                // e.g. 'Replace', 'Clean'
  cancelLabel?: string;                // default 'Cancel'
  onConfirm: () => void;
  onCancel: () => void;
}): JSX.Element;   // role="group", two buttons; never window.confirm
```

```js
// src/lib/gridEdits.js
/** §3.2: true if any cell has a letter or is black. null grid -> false. */
export function gridHasContent(grid: Cell[][] | null): boolean;
```

```jsx
// GridPanel gains:
onNewGrid: (size: 11 | 15 | 21) => void;
```

**Behavioral criteria:**
- The panel shows a "New grid" section with three buttons labelled exactly `11×11`, `15×15`, `21×21` (`×` is U+00D7) (§3.2).
- Choosing a size when `gridHasContent(grid)` shows an `InlineConfirm` with message `Replace the current grid? Unsaved changes are lost.`, `confirmLabel` `Replace`, cancel `Cancel`; `Replace` calls `onNewGrid(size)`, `Cancel` closes the confirm and changes nothing. Choosing a size on a grid with no letter and no black square calls `onNewGrid(size)` with no confirm (§3.2).
- All three size buttons are disabled while `editingPaused` (§3.2, D1). An open confirm is dropped when the panel unmounts (tool switch).
- `createNewGrid(size)` in `App`: returns immediately when `editingPaused` (write-time gate). Otherwise it (a) when `size !== gridSize`, sets `skipNextInitRef.current = true` and then `setGridSize(size)`, so the `[gridSize]` effect does not initialise a second time; when sizes are equal it leaves the flag alone; (b) builds the blank grid through `initializeGrid(size)`; (c) the new grid's cells are empty, white, `isThemeLocked: false`, `isAutofilled: false`, `isBlocked: false`, `isError: false` (§3.2 Ordering: resets `isBlocked`, `isError`); (d) carries numbering equal to `localNumber(blank).grid` **even when the structural signature is unchanged from the previous grid**: `useNumbering` fires only on a `structuralSigOf` change, so a same-size New grid from a grid with the same black layout would otherwise show no numbers, contradicting "numbered" (§3.2); (e) the document id is minted by `initializeGrid(size)` (Task 4.2), so there is no second mint; the new id differs from the previous one (M1, §3.4; asserted below); (f) calls `autofill.discardRun()` so no retained `startSnapshot` and no "Keep" offer survives (§3.2 Ordering); (g) sets `selectedCell` to `null` (see planning default `PD-6-G4` (spec §8)); (h) sets `symmetryEnabled` to `true` (§3.2: "The new grid is empty, numbered, with symmetry on."; this overrides a persisted off, which is `usePersistentState('crossword_symmetry_enabled', true)`'s current value); (i) the grid is born clean (`savedSig` = its signature), as `initializeGrid` already does.

**Normative cases:**

| input | result |
|---|---|
| `gridHasContent(null)` | `false` |
| all cells `letter: ''`, `isBlack: false` (even if some `isThemeLocked`) | `false` |
| one cell `letter: 'A'` | `true` |
| one cell `isBlack: true`, no letters | `true` |
| 15×15 with letters, choose `21×21`, press `Replace` | grid is 21×21 and blank; `docId` ≠ previous; `isError`/`isBlocked`/`isAutofilled` all false on every cell |
| 15×15 with letters, choose `15×15`, press `Cancel` | grid unchanged, `docId` unchanged |
| blank 15×15, choose `11×11` | no confirm; grid is 11×11 |
| 15×15 with letters only (no black), choose `15×15`, `Replace` | blank grid whose cells carry the numbers `localNumber` gives a blank 15×15 (cell (0,0) `number` is 1) |
| `editingPaused` true | the three size buttons are disabled; `createNewGrid(11)` leaves the grid and `docId` unchanged |
| a snapshot/offer is retained (mock `autofill`) | `autofill.discardRun` was called once by New grid |
| symmetry off (persisted) before New grid | `symmetryEnabled` is `true` after New grid (§3.2: "with symmetry on") |

- [ ] **Step 1: Write the failing tests** from the table (`InlineConfirm` render/callback tests; `GridPanel` confirm flow; `gridHasContent` rows; the App rows including the `skipNextInitRef`-no-double-init case, the same-size numbering case and the docId case, mocking `src/lib/docId` to return distinguishable ids).
- [ ] **Step 2: Run** `npx vitest run src/components/bench/__tests__/InlineConfirm.test.jsx src/components/bench/__tests__/GridPanel.test.jsx src/lib/__tests__/gridEdits.test.js src/__tests__/components/App.test.jsx`. Expected: fail (no `InlineConfirm`, no size buttons).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the four files, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/components/bench/InlineConfirm.jsx src/components/bench/__tests__/InlineConfirm.test.jsx src/components/bench/GridPanel.jsx src/components/bench/__tests__/GridPanel.test.jsx src/lib/gridEdits.js src/lib/__tests__/gridEdits.test.js src/App.jsx src/styles/bench/base.css src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "feat(grid): New grid (11/15/21) with an in-panel confirm that resets red cells and the run snapshot"
```

### Task 6.5: Storage as a list of saved grids (§3.4)

**Files:**
- Modify: `src/lib/storage.js`
- Modify: `src/api/gridCodec.js` (`normalizeSavedGrid`)
- Test: `src/lib/__tests__/storage.test.js`, `src/api/__tests__/gridCodec.test.js` (the existing codec test file; add cases)

**Interfaces:**
- Consumes: `makeCell` (Phase 4 added `isAutofilled`, `isBlocked`); `mintDocId` (`src/lib/docId.js`).
- Produces:

```js
export const SAVE_KEY = 'crossword_saved_grids';          // array, newest first
export const LEGACY_SAVE_KEY = 'crossword_saved_grid';    // pre-6.5 single blob

/** An entry is the save document plus name and savedAt. */
// { id: string, name: string, savedAt: string /* ISO */, size: number, grid, numbering, symmetryEnabled }

export function list(): Promise<Entry[]>;                   // newest first; never rejects
export function load(): Promise<Entry | null>;              // list()[0] ?? null; never rejects
export function save(
  doc: { id: string; size: number; grid: unknown; numbering?: unknown; symmetryEnabled?: boolean; name?: string },
  opts?: { name?: string; expectedSavedAt?: string | null; replaceEntryId?: string }
): Promise<{ savedAt: string; id: string; name: string; forked: boolean }>;   // rejects on a write failure
export function remove(id: string): Promise<void>;          // unknown id: resolves, nothing changes
export function formatStamp(date: Date): string;            // 'YYYY-MM-DD HH:MM', local time
export function defaultName(size: number, date: Date): string;   // `${size}×${size} ${formatStamp(date)}`
export default { list, load, save, remove, defaultName, formatStamp, SAVE_KEY, LEGACY_SAVE_KEY };

// src/api/gridCodec.js
/** Returns a new grid whose every cell is { ...makeCell(), ...cell, isBlocked: false }; an absent isAutofilled reads false (§3.4, §3.7). */
export function normalizeSavedGrid(grid: unknown[][]): Cell[][];
```

**Behavioral criteria:**
- `SAVE_KEY` is `crossword_saved_grids` and holds a JSON array, newest first; each entry is keyed by `doc.id` (§3.4, M1). `save` upserts by id: an existing entry is replaced and moved to the front with a fresh `savedAt`; a new id is inserted at the front.
- Name resolution on `save`: `opts.name` if given; else the stored entry's name; else `defaultName(doc.size, now)` (§3.4: autosave "creating it under the default name below if absent"). `doc.name` is ignored in favour of the stored one unless `opts.name` is passed.
- `save` rejects if any `setItem` throws (existing contract, §3.4 "`save` rejects on a write failure"); `load` and `list` never reject: a missing or corrupt array blob resolves `[]`/`null`.
- `remove(id)` rewrites the array without that entry.
- `opts.replaceEntryId`: the entry with that id is removed in the same write that stores the saved entry (a name-collision replace, §3.4).
- **Fork (S4, P16):** when `opts.expectedSavedAt` is a string and an entry with `doc.id` exists whose `savedAt` differs from it, `save` writes a **new** entry with `id = mintDocId()` and name `<stored entry's name> (copy)`, leaves the stored entry untouched, and resolves with `forked: true` and the new `id` and `name`. If no entry with `doc.id` exists (deleted in another tab) it saves normally. `expectedSavedAt` `null`/absent skips the check.
- **Legacy migration (§3.4):** on the first `list`/`load`/`save`, if `LEGACY_SAVE_KEY` holds a parseable blob it is merged into the array as one entry named `Saved grid` with its own `savedAt` kept, then `LEGACY_SAVE_KEY` is removed (after the array write succeeded; if that write throws, the legacy key is left in place). The migrated entry's id is `legacy-<savedAt>` (planning default `PD-6-G1` (spec §8)), so re-running after an interrupted removal upserts the same entry instead of duplicating. A corrupt legacy blob is not migrated, not removed, and does not throw.
- The newest entry is the one with the most recent `savedAt` (array order maintains it).
- `normalizeSavedGrid` fills missing cell fields from `makeCell()` and forces `isBlocked: false` (`isBlocked` is never saved or restored, §2.3); an `isAutofilled` that is present is kept as saved.
- **Existing tests that change:** `storage.test.js` pins `SAVE_KEY` to the legacy key and `save()` writing "the legacy blob under the exact key"; both reasons are now false and the tests are rewritten against the array key. The `load()` legacy-blob-without-`savedAt` test is rewritten as a migration case.

**Normative cases** (`localStorage` mock backed by a `Map`; `now` mocked):

| setup | action | expected |
|---|---|---|
| empty | `list()` | `[]`; `load()` → `null` |
| empty | `save({id:'a', size:15, grid:g})` | result `{id:'a', name:'15×15 <stamp of now>', forked:false}`; `list()` has one entry `a` |
| `a` stored named `Mine` | `save({id:'a',…})` | still one entry, name `Mine`, `savedAt` newer, first in `list()` |
| `a` stored | `save({id:'a',…}, {name:'Puzzle 1'})` | one entry, name `Puzzle 1` |
| `a`, `b` stored (`b` newer) | `list()` | `[b, a]`; `load()` → `b` |
| `a` stored | `remove('a')`; `remove('zzz')` | list empty; second call resolves, no change |
| `a` (savedAt `T1`), `b` stored | `save({id:'a',…}, {name:'Other', replaceEntryId:'b'})` | `b` gone, `a` named `Other`, one write |
| `a` stored at `T1` | `save({id:'a',…}, {expectedSavedAt:'T0'})` | `forked:true`; list now has `a` unchanged and a new id named `<a's name> (copy)` |
| `a` stored at `T1` | `save({id:'a',…}, {expectedSavedAt:'T1'})` | `forked:false` |
| nothing stored for `a` | `save({id:'a',…}, {expectedSavedAt:'T1'})` | `forked:false`, entry created |
| `setItem` throws | `save(...)` | rejects |
| legacy key = `{"id":2,"size":5,"grid":[[…]],"savedAt":"2026-10-01T10:00:00.000Z"}`, array key absent | `list()` | one entry named `Saved grid`, `savedAt` `2026-10-01T10:00:00.000Z`, string id; `removeItem` called with `crossword_saved_grid`; second `list()` does not duplicate |
| legacy key corrupt | `list()` | `[]`, no throw, legacy key not removed |
| array key corrupt | `list()` / `load()` | `[]` / `null` |
| `defaultName(15, new Date(2026, 9, 23, 14, 5))` | | `15×15 2026-10-23 14:05` |
| `normalizeSavedGrid([[{letter:'A'}]])` | | the cell has `letter:'A'`, `isAutofilled:false`, `isBlocked:false`, `isBlack:false`, `isThemeLocked:false` |
| `normalizeSavedGrid([[{letter:'A', isAutofilled:true, isBlocked:true}]])` | | `isAutofilled:true`, `isBlocked:false` |

- [ ] **Step 1: Write the failing tests** (storage and codec).
- [ ] **Step 2: Run** `npx vitest run src/lib/__tests__/storage.test.js src/api/__tests__/gridCodec.test.js`. Expected: fail because `list`, `remove` and the array key do not exist.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** both files, then `npx vitest run` (the save-machine and App suites exercise `storage` through mocks) and `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/lib/storage.js src/lib/__tests__/storage.test.js src/api/gridCodec.js src/api/__tests__/gridCodec.test.js
git diff --cached --stat
git commit -m "feat(storage): saved grids as a newest-first list with upsert, remove, fork and legacy migration"
```

### Task 6.6: Save machine: explicit named save, fork on conflict, adopted `savedAt` (§3.4 G3, G4, S4)

**Files:**
- Modify: `src/hooks/useSaveMachine.js`
- Test: `src/hooks/__tests__/useSaveMachine.test.jsx`

**Interfaces:**
- Consumes: `storage.save(doc, opts)` (6.5); `useToasts().pushToast`.
- Produces:

```js
export function useSaveMachine(params: {
  doc: { id: string; [k: string]: unknown };
  isDirty: boolean;
  onForked?: (info: { id: string; name: string }) => void;   // called when storage.save returned forked: true
}): {
  status: 'pristine' | 'dirty' | 'saving' | 'saved' | 'error';
  savedLabel: string;
  save: () => Promise<void>;                                   // autosave path, unchanged
  saveNamed: (name: string, opts?: { replaceEntryId?: string }) => Promise<boolean>;   // true saved, false failed; never rejects
  adoptSavedAt: (savedAt: string | null) => void;              // the savedAt this tab loaded or last wrote
};
```

**Behavioral criteria:**
- Autosave (the 30 s timer, `AUTOSAVE_MS`) calls `storage.save(doc, { expectedSavedAt })` with no `name`, so it updates the one entry for `doc.id` and never prompts (§3.4). `expectedSavedAt` is the machine's `knownSavedAt` (starts `null`; set by `adoptSavedAt`; set to the returned `savedAt` after every successful save).
- **Existing behaviour that must not change (pinned by existing tests, §3.4 G4):** a failed autosave shows the toast `Couldn’t save — will retry.` (U+2019), sets status `error` (label `offline — will retry`), and re-arms the 30 s timer without bound; one timer per dirty period; `doc.id` change clears the pending timer (F10).
- `saveNamed(name, opts)` runs the same save path with `opts.name = name` and `opts.replaceEntryId`, clears the pending autosave timer, and resolves `true` on success. On a rejected write it pushes an `error` toast with exactly `Could not save: browser storage is full. Delete a saved grid or export this one.`, does **not** push `Couldn’t save — will retry.`, sets status `error` and re-arms autosave (planning default `PD-6-G6` (spec §8)), and resolves `false`. A failed explicit save is never swallowed (§3.4 G4).
- If `storage.save` resolves `forked: true`, the machine calls `onForked({id, name})` and records the returned `savedAt` as `knownSavedAt` (S4).
- `adoptSavedAt(savedAt)` only sets `knownSavedAt`; it does not change status.
- **Existing tests that change:** `toHaveBeenLastCalledWith(expect.objectContaining({ v: 3 }))` in `useSaveMachine.test.jsx` becomes a two-argument match, because `storage.save` now receives `(doc, opts)`.

**Normative cases** (`storage.save` spied):

| situation | expected |
|---|---|
| dirty, 30 s elapse | `storage.save` called once with `(doc, { expectedSavedAt: null })` and no `name` |
| after `adoptSavedAt('T1')`, dirty, 30 s elapse | `storage.save` called with `expectedSavedAt: 'T1'` |
| autosave rejects | toast `Couldn’t save — will retry.`; label `offline — will retry`; second attempt at +30 s |
| `saveNamed('Puzzle')` succeeds | `storage.save` called with `opts.name === 'Puzzle'`; resolves `true`; status `saved` |
| `saveNamed('Puzzle', {replaceEntryId:'b'})` | `opts.replaceEntryId === 'b'` forwarded |
| `saveNamed` rejects | quota toast text exactly as above; no `Couldn’t save — will retry.`; resolves `false`; status `error` |
| `storage.save` resolves `{forked:true, id:'n', name:'X (copy)', savedAt:'T9'}` | `onForked({id:'n', name:'X (copy)'})` called once; next save uses `expectedSavedAt: 'T9'` |

- [ ] **Step 1: Write the failing tests** (extend `useSaveMachine.test.jsx`; update the one changed assertion).
- [ ] **Step 2: Run** `npx vitest run src/hooks/__tests__/useSaveMachine.test.jsx`. Expected: fail because `saveNamed`/`adoptSavedAt` do not exist.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the file, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/hooks/useSaveMachine.js src/hooks/__tests__/useSaveMachine.test.jsx
git diff --cached --stat
git commit -m "feat(save): explicit named save, quota message and fork-on-conflict in the save machine"
```

### Task 6.7: Save wiring in `App`: name prompt and saves during a run (§3.4 G3, G4, S2)

**Files:**
- Create: `src/components/bench/SaveNamePrompt.jsx`
- Modify: `src/components/bench/TopBar.jsx` (new optional `savePrompt` slot under the Save button)
- Modify: `src/App.jsx` (`doc`, `contentSig`, `savedSig`, `onSave`, `onForked`)
- Modify: `src/styles/bench/base.css`
- Test: `src/components/bench/__tests__/SaveNamePrompt.test.jsx` (create), `src/components/bench/__tests__/TopBar.test.jsx`, `src/__tests__/components/App.test.jsx`

**Interfaces:**
- Consumes: `useSaveMachine` (6.6); `storage.list/defaultName` (6.5); `InlineConfirm` (6.4); Phase 5 `autofill.startSnapshot`; Phase 4 `LIVE_STATES`/`editingPaused`.
- Produces:

```jsx
export default function SaveNamePrompt(props: {
  initialName: string;
  entries: Array<{ id: string; name: string }>;   // every saved entry
  currentId: string;                              // the document's own id
  onConfirm: (name: string, opts?: { replaceEntryId?: string }) => void;
  onCancel: () => void;
}): JSX.Element;
// TopBar gains: savePrompt?: React.ReactNode   (rendered in a position:relative wrapper directly under the Save button)
```

**Behavioral criteria:**
- The Save button (`onSave` prop of `TopBar`) no longer saves directly: it opens `SaveNamePrompt` under the button, prefilled with the current entry's name (the stored entry for `docId`, else `defaultName(gridSize, now)`) (§3.4 G3). Autosave never opens it.
- Confirming a trimmed, non-empty name renames the document's own entry via `saveNamed(name)`; the confirm button is disabled for an empty or whitespace-only name (planning default `PD-6-G7` (spec §8)). Cancel closes the prompt and saves nothing.
- A name equal (after trimming, case-sensitive) to a **different** entry's name does not save yet: the prompt shows an `InlineConfirm` with message `Replace the saved grid named "<name>"?` (planning default `PD-6-G8` (spec §8)), `Replace` and `Cancel`; `Replace` calls `saveNamed(name, { replaceEntryId: <other id> })`. A name equal to the document's own entry's name is not a collision.
- On `saveNamed` resolving `true` the prompt closes; on `false` the prompt stays open (the quota toast is the machine's).
- `onForked` → `setDocId(info.id)`.
- **S2:** while `editingPaused` (LIVE_STATES), the document handed to `useSaveMachine` carries `grid: autofill.startSnapshot` (falling back to the live `grid` only if it is `null`, which Phase 5 must not allow while live) instead of the live grid, for the Save button and autosave alike. `contentSig` is computed from that same grid, so merges during the run do not flip `isDirty`; a separate `liveSig = contentSigOf(gridSize, grid)` stays available for Tasks 6.8 and 6.11. When `saveStatus` becomes `'saved'`, `savedSig` is set to the signature of the grid that was **written** (the snapshot's during a run), not the live grid's, otherwise a fill that ends exactly at the mid-run state would read clean while storage holds the Start grid.
- The saved document never carries `isBlocked: true` cells (`toSavedGrid`, Task 4.1, strips `isBlocked`).

**Normative cases:**

| situation | expected |
|---|---|
| click `Save grid` on a new document | prompt visible, input value = `15×15 <YYYY-MM-DD HH:MM>` |
| click `Save grid` with a stored entry `Mine` for `docId` | input value `Mine` |
| confirm `Puzzle 1`, no other entry has it | `saveNamed('Puzzle 1')`; prompt closes |
| confirm `Other` where entry `x` ≠ own is named `Other` | `Replace the saved grid named "Other"?` shown; `Replace` → `saveNamed('Other', {replaceEntryId:'x'})` |
| confirm own current name | no collision confirm |
| empty / `"   "` | confirm button disabled |
| autosave fires | no prompt appears |
| run live (`submitting`/`running`), `startSnapshot` = S, live grid = L ≠ S, autosave fires | `storage.save` called with a doc whose `grid` is S |
| same, click Save and confirm a name | doc grid is S |
| run live, `saveStatus` → `saved` | `savedSig` equals `contentSigOf(size, S)` |
| `storage.save` forks | `docId` becomes the returned id |

- [ ] **Step 1: Write the failing tests** (`SaveNamePrompt`, `TopBar` slot, App rows with `storage` and `autofill` mocked as needed).
- [ ] **Step 2: Run** `npx vitest run src/components/bench/__tests__/SaveNamePrompt.test.jsx src/components/bench/__tests__/TopBar.test.jsx src/__tests__/components/App.test.jsx`. Expected: fail (no prompt; Save still saves directly).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the three files, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/components/bench/SaveNamePrompt.jsx src/components/bench/__tests__/SaveNamePrompt.test.jsx src/components/bench/TopBar.jsx src/components/bench/__tests__/TopBar.test.jsx src/App.jsx src/styles/bench/base.css src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "feat(save): name prompt under Save, collision replace, and Start-snapshot saves during a run"
```

### Task 6.8: Restore on load, the banner, and restore across sizes (§3.4, S3)

**Files:**
- Create: `src/components/bench/RestoreBanner.jsx`
- Modify: `src/App.jsx` (mount effect; `restoredBanner` state; render above the grid)
- Modify: `src/styles/bench/base.css`
- Test: `src/components/bench/__tests__/RestoreBanner.test.jsx` (create), `src/__tests__/components/App.test.jsx`

**Interfaces:**
- Consumes: `storage.load()`, `formatStamp` (6.5); `normalizeSavedGrid` (6.5); `adoptSavedAt` (6.6); Phase 4 `setDocId`, `skipNextInitRef`.
- Produces:

```jsx
export default function RestoreBanner(props: {
  name: string;
  savedAt: string;            // ISO
  onStartBlank: () => void;
  onDismiss: () => void;
}): JSX.Element;
// text: Restored "<name>" (saved <formatStamp(new Date(savedAt))>)  — buttons: "Start blank" and a dismiss button with aria-label "Dismiss" and text "×" (U+00D7)
```

**Behavioral criteria:**
- On mount, `App` calls `storage.load()` once. If it resolves an entry: the grid becomes `normalizeSavedGrid(entry.grid)`, `docId` becomes `entry.id` (adopted, not minted; §3.4 M1), `symmetryEnabled` follows the entry when present, `savedSig` is set to its signature (born clean), `adoptSavedAt(entry.savedAt)` is called, and the banner state is set with `{name, savedAt}`. If it resolves `null`, nothing changes: the blank grid and the `docId` Phase 4 minted at app start stay (§3.4: "app start when restore-on-load finds no save").
- **S3:** when `entry.size !== gridSize` at that moment, `skipNextInitRef.current = true` is set **before** `setGridSize(entry.size)`; when the sizes are equal the flag is **not** set (a stray `true` would swallow the next legitimate size change). The restored cells survive the `[gridSize]` effect (§3.4 S3).
- Restored cells keep their saved `isAutofilled` (restore is an exception to §3.7: provenance loads as saved); an entry without it reads `false`.
- The banner is rendered above the grid in `.xw-canvas`, in flow (not over the top bar). It closes on its `×`, or on any grid edit: when `liveSig` (6.7) differs from the signature recorded at restore. It also closes when `Start blank` is pressed, which selects the Grid tool (`setCurrentTool('edit')`) where New grid (6.4) lives; the confirm of §3.2 then applies as the grid has content (planning default `PD-6-G9` (spec §8)).
- A restore that resolves after the user already changed the grid is not special-cased (the load is a localStorage read and resolves before first input).
- Restore sets `selectedCell` to `null` (planning default `PD-6-G4` (spec §8)).

**Normative cases** (`storage.load` mocked):

| setup | expected |
|---|---|
| `load` → `null` | grid blank 15×15; no banner |
| `load` → 15×15 entry `Mine`, `savedAt` `2026-10-22T09:30:00` local | letters present; banner text `Restored "Mine" (saved 2026-10-22 09:30)` (local time); `docId` = entry id |
| `load` → 21×21 entry while `gridSize` is 15 | grid is 21×21 **with the entry's letters** (not blank); `Restored` banner visible |
| `load` → 15×15 entry while `gridSize` is 15, then the user later changes size via New grid to 11 | the 11×11 grid is blank and fresh (the skip flag was not left set) |
| entry cells lack `isAutofilled` | all cells read `isAutofilled:false` |
| entry has `isAutofilled:true` on a cell | stays `true` |
| click `×` | banner gone |
| type a letter | banner gone |
| click `Start blank` | banner gone; Grid panel shown with the New grid buttons |
| restore with no edits | banner stays; `isDirty` is false (no autosave armed) |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run** `npx vitest run src/components/bench/__tests__/RestoreBanner.test.jsx src/__tests__/components/App.test.jsx`. Expected: fail (no restore, no banner).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** both files, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/components/bench/RestoreBanner.jsx src/components/bench/__tests__/RestoreBanner.test.jsx src/App.jsx src/styles/bench/base.css src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "feat(save): restore the newest saved grid on load with a dismissible banner, across grid sizes"
```

### Task 6.9: Open saved (§3.4)

**Files:**
- Create: `src/components/bench/SavedGridsList.jsx`
- Modify: `src/components/bench/GridPanel.jsx`
- Modify: `src/App.jsx` (`openSavedEntry`)
- Modify: `src/styles/bench/base.css`
- Test: `src/components/bench/__tests__/SavedGridsList.test.jsx` (create), `src/components/bench/__tests__/GridPanel.test.jsx`, `src/__tests__/components/App.test.jsx`

**Interfaces:**
- Consumes: `storage.list/remove/formatStamp` (6.5); `InlineConfirm`, `gridHasContent` (6.4); `normalizeSavedGrid`; `adoptSavedAt`; `autofill.discardRun()`.
- Produces:

```jsx
export default function SavedGridsList(props: {
  entries: Array<{ id: string; name: string; size: number; savedAt: string }>;
  disabled: boolean;                 // editingPaused
  onOpen: (entry) => void;
  onDelete: (id: string) => void;
}): JSX.Element;   // one row per entry: name, `${size}×${size}`, formatStamp(savedAt); buttons "Open" and "Delete"
// GridPanel gains: onOpenSaved: (entry: Entry) => void
```

**Behavioral criteria:**
- The Grid panel has an `Open saved` button that loads `storage.list()` and shows `SavedGridsList` (name, size, saved time; `Open` and `Delete` per row), newest first (§3.4). An empty list shows no rows.
- `Delete` asks an `InlineConfirm` (in the Grid panel, above the list) with message `Delete "<name>"?`, `confirmLabel` `Delete`, cancel `Cancel`, before removing (planning default `PD-6-G20` (spec §8)); `Delete` in the confirm calls `storage.remove(id)` and refreshes the list; `Cancel` removes nothing.
- `Open` on an entry: if `gridHasContent(grid)`, the §3.2 `InlineConfirm` (`Replace the current grid? Unsaved changes are lost.`, `Replace`/`Cancel`) is shown first; otherwise it opens immediately (§3.4). `Open saved`, `Open` and `Delete` are disabled while `editingPaused` (§3.4, D1); `openSavedEntry` also returns early when `editingPaused` at write time.
- `openSavedEntry(entry)`: when `entry.size !== gridSize`, sets `skipNextInitRef.current = true` **before** `setGridSize(entry.size)` (S3), and does not set it when equal; sets the grid from `normalizeSavedGrid(entry.grid)`, `setDocId(entry.id)` (adopted, not minted), symmetry from the entry, `savedSig` to the entry's signature, `adoptSavedAt(entry.savedAt)`, `autofill.discardRun()` (no retained snapshot/offer), `selectedCell` `null`; loads `isAutofilled` as saved (§3.7 exception); clears `isBlocked` (not saved); dismisses the restore banner.

**Normative cases:**

| situation | expected |
|---|---|
| 2 stored entries | two rows, newest first, each with `Open` and `Delete`, time via `formatStamp` |
| `Delete` on one | confirm `Delete "<name>"?` with `Delete`/`Cancel`; `storage.remove` not yet called |
| …press `Delete` in the confirm (`PD-6-G20`) | `storage.remove` called with that id; row disappears |
| …press `Cancel` in the confirm (`PD-6-G20`) | `storage.remove` not called; row stays |
| current grid blank, `Open` | opens at once, no confirm |
| current grid has a letter, `Open` | confirm `Replace the current grid? Unsaved changes are lost.`; `Cancel` leaves grid and `docId`; `Replace` opens |
| entry 21×21 while `gridSize` 15 | grid is 21×21 with the entry's letters, not blank (S3) |
| entry 15×15 while `gridSize` 15, then New grid → 11 | the 11×11 is blank (flag not left set) |
| open entry `e` | `docId === e.id`; `adoptSavedAt(e.savedAt)` called; a following autosave updates entry `e` instead of creating another |
| `editingPaused` | `Open saved`, `Open`, `Delete` disabled |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run** `npx vitest run src/components/bench/__tests__/SavedGridsList.test.jsx src/components/bench/__tests__/GridPanel.test.jsx src/__tests__/components/App.test.jsx`. Expected: fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the three files, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/components/bench/SavedGridsList.jsx src/components/bench/__tests__/SavedGridsList.test.jsx src/components/bench/GridPanel.jsx src/components/bench/__tests__/GridPanel.test.jsx src/App.jsx src/styles/bench/base.css src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "feat(save): Open saved lists, opens and deletes saved grids behind the replace confirm"
```

### Task 6.10: Search placement keeps protected cells and does not mutate (§3.5 #62, G6)

**Files:**
- Modify: `src/lib/gridEdits.js` (amends Task 4.3's `writePatternWord`)
- Modify: `src/App.jsx` (`handlePatternSelect` becomes a thin caller)
- Test: `src/lib/__tests__/gridEdits.test.js`, `src/__tests__/components/App.test.jsx`

**Interfaces:**
- Consumes: Phase 4's D1 gate at the top of `handlePatternSelect`; Task 4.3's `writePatternWord(grid, selectedCell, word)`, whose signature is unchanged here.
- Produces:

```js
/**
 * Amends Task 4.3's writePatternWord (same signature) for #62 + G6. Returns a NEW grid; the input
 * grid and its cells are never mutated. Walks word[i] along `selectedCell.direction` from
 * (selectedCell.row, selectedCell.col): stops at the first black cell or the grid edge (the size is
 * grid.length); skips (keeps) a theme-locked cell; otherwise writes
 * { ...cell, letter: word[i], isAutofilled: false, isBlocked: false } (Task 4.3's common rule).
 */
export function writePatternWord(
  grid: Cell[][],
  selectedCell: { row: number; col: number; direction: 'across' | 'down' },
  word: string
): Cell[][];
```

**Behavioral criteria:**
- A letter is written only into a white, not theme-locked cell — exactly the rule the key handler applies to typed letters; the walk stops at the first black square in the slot's direction; cells it skips keep their content (§3.5 #62). A theme-locked cell is skipped but the walk continues past it; only a black square or the edge ends it.
- Each changed cell is a **new** object `{ ...cell, letter, isAutofilled: false }` (G6, §3.7 S5: a same-letter write also clears the flag). Unchanged cells may be shared. `writePatternWord` does not throw when called on a deeply frozen grid.
- Letters are written as given by the word (the caller passes the word as the Search result supplies it; today uppercase).
- `handlePatternSelect` returns without effect when there is no `selectedCell` or no grid (existing) and when `editingPaused` (D1).

**Normative cases** (`writePatternWord`, 5×5, row 0 shown; `.` empty, `#` black, `X*` theme-locked holding `X`; `Z` a user letter; `selectedCell` is `{row, col, direction}`). These rows replace Task 4.3's `writePatternWord` rows where they differ:

| `selectedCell` (start, dir) | word | row 0 before | row 0 after |
|---|---|---|---|
| (0,0) across | `CAT` | `.....` | `CAT..` |
| (0,0) across | `CAT` | `..#..` | `CA#..` |
| (0,0) across | `CAT` | `#....` | `#....` |
| (0,0) across | `CAT` | `.X*..` | `CX*T..` (C at col 0, col 1 kept, T at col 2) |
| (0,3) across | `CAT` | `.....` | `...CA` |
| (0,0) across | `CAT` | `Z....` | `CAT..` |
| (0,0) across | `CAT` | `C....` where that `C` has `isAutofilled: true` | `CAT..`, cell (0,0) `isAutofilled: false` |
| (0,0) down | `CAT` | column 0 = `.`,`.`,`#`,`.`,`.` | column 0 = `C`,`A`,`#`,`.`,`.` |

Also: after `writePatternWord`, a snapshot taken of the input grid before the call deep-equals the input after the call (G6), including `isAutofilled` on every cell.

- [ ] **Step 1: Write the failing tests** (unit table; one App case placing a Search result across a black square and a theme-locked cell through the UI, per §6 SR-PLACE).
- [ ] **Step 2: Run** `npx vitest run src/lib/__tests__/gridEdits.test.js src/__tests__/components/App.test.jsx`. Expected: fail (Task 4.3's `writePatternWord` still overwrites theme-locked cells and walks through black squares; the table rows below fail).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** both files, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/lib/gridEdits.js src/lib/__tests__/gridEdits.test.js src/App.jsx src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "fix(grid): a placed Search result skips theme-locked cells, stops at black squares and never mutates the old grid"
```

### Task 6.11: Verify and Clean apply to the current grid; #63; Clean never destroys theme-locked letters (§3.5, §2.3 S1, G5)

**Files:**
- Modify: `src/lib/gridEdits.js` (`applyVerifyErrors`, `planClean`, `clearAllErrors`; amends Task 4.3's `writeCleanedGrid`)
- Modify: `src/App.jsx` (`handleVerifyWords`, `handleCleanGrid`, a `pendingClean` state, the confirm render at the top of `.xw-canvas`, dismissal effect)
- Modify: `src/styles/bench/base.css`
- Test: `src/lib/__tests__/gridEdits.test.js`, `src/__tests__/components/App.test.jsx`

**Interfaces:**
- Consumes: `InlineConfirm` (6.4); `liveSig` (6.7); `editingPaused` and its write-time check (`editingPausedRef`, Task 4.4) as Phase 4 installed it in these two handlers (keep it; do not rename); Task 4.3's `writeCleanedGrid`; `api.verifyWords`, `api.cleanGrid`.
- Produces:

```js
/** S1: new grid; only isError changes; key is "row,col". */
export function applyVerifyErrors(prev: Cell[][], errorKeys: Set<string>): Cell[][];

/**
 * G5 + S1. sentLetters / cleanedLetters are string[][] ('' for blank or black).
 * blanks = cells where sent letter is non-empty AND cleaned letter is '' AND prev cell is white,
 * NOT theme-locked, and prev letter === sent letter.
 */
export function planClean(prev: Cell[][], sentLetters: string[][], cleanedLetters: string[][]): { blanks: Array<[number, number]> };

/**
 * Amends Task 4.3's writeCleanedGrid(prevGrid, cleanedGrid) with ONE added parameter, `blanks` (the
 * cells planClean returned). Replaces Task 4.3's mapping and its table row: only the listed cells are
 * written, each as a new object { ...prev cell, letter: cleanedGrid[r][c].letter (always '' for a
 * blank), isError: false, isAutofilled: false, isBlocked: false }. Every other cell is prevGrid's
 * object (its isError is left as it was); isBlack never changes and cleanedGrid's isBlack is not applied.
 */
export function writeCleanedGrid(prevGrid: Cell[][], cleanedGrid: Cell[][], blanks: Array<[number, number]>): Cell[][];

/** #63 / G5 step 3: new grid with isError false on every cell. */
export function clearAllErrors(prev: Cell[][]): Cell[][];
```

**Behavioral criteria:**
- **S1, Verify:** the response is applied with `setGrid(prev => applyVerifyErrors(prev, errorKeys))`; it changes only `isError`. A letter typed while the request was in flight survives; the toasts are unchanged.
- **S1, Clean:** `handleCleanGrid` sends `{letter, isBlack}` per cell as today; after the response, `planClean(currentGrid, sentLetters, cleanedLetters)` is computed against the **current** grid (the one in state when the response lands), and the write is a functional update. The server's cleaned grid's `isBlack` is not applied.
- **G5 step 1:** a theme-locked cell keeps its letter and lock (it is never in `blanks`).
- **G5 step 2:** `N = blanks.length`. If `N > 0`, no `setGrid` yet: `pendingClean = { blanks, cleaned, message }` (`cleaned` = the server's cleaned grid) and an `InlineConfirm` with message `Clean will remove N letters` (`Clean will remove 1 letter` when `N` is 1), `confirmLabel` `Clean`, cancel `Cancel`, rendered at the top of `.xw-canvas` above the grid regardless of the open tool (planning default `PD-6-G10` (spec §8)). **Cancel** clears `pendingClean` and changes nothing: grid, `isError` flags and toasts exactly as before (no toast). **Clean** applies `setGrid(prev => writeCleanedGrid(prev, cleaned, blanks))` and pushes the server's `message` as an `info` toast.
- **G5 step 3 / #63:** if `N === 0` no confirm is shown; `setGrid(prev => clearAllErrors(prev))`; toast `Grid is clean — all words are valid!` (info) only when `removed_count === 0`, else `Nothing removed: theme-locked letters are kept.` (info) (§3.5, P15).
- **Dismissal (S1):** an open confirm is dismissed (`pendingClean` cleared, nothing applied) when `liveSig` changes (any letter, black-square, theme-lock or provenance change; an `isError`-only change does not count, planning default `PD-6-G11` (spec §8)) or when `editingPaused` becomes true (Start).
- Both handlers keep Phase 4's write-time gate: a response landing while `editingPaused` writes nothing. A Verify or Clean response that lands after `docId` changed since its request is dropped: it writes nothing (no grid write, no `pendingClean`, no confirm, no toast) — planning default `PD-6-G12` (spec §8).
- Failure toasts (`Failed to verify words: …`, `Failed to clean grid: …`) are unchanged.

**Normative cases — `planClean`** (3×3, `TL` = theme-locked; sent row 0 `CAT`, cleaned row 0 `C..`, other rows empty):

| prev | blanks | N |
|---|---|---|
| row 0 `CAT`, no locks | `[[0,1],[0,2]]` | 2 |
| row 0 `CAT`, (0,1) TL | `[[0,2]]` | 1 |
| row 0 `CAT`, (0,1) and (0,2) TL | `[]` | 0 |
| prev (0,1) is `Q` (typed after the request), (0,2) `T` | `[[0,2]]` | 1 |
| cleaned keeps `A` (cleaned row 0 `CA.`) | `[[0,2]]` | 1 |
| sent (0,1) was `''` | not in `blanks` | — |

**Normative cases — `applyVerifyErrors`:** prev has (0,0) `isError:true`, (0,1) `isError:false`, (1,1) letter `Q`; keys `{"0,1"}` → (0,0) `false`, (0,1) `true`, (1,1) still `Q`; the input grid unchanged.

**Normative cases — `writeCleanedGrid` (third parameter `blanks`) / `clearAllErrors`:** `writeCleanedGrid(prev, cleaned, [[0,2]])` blanks (0,2) with `isError:false`, `isAutofilled:false`, leaves every other cell's `isError` as it was; `clearAllErrors` sets every cell `isError:false` and touches no letter.

**Normative cases — App (S1, #63, G5, `PD-6-G12`, §6 CL-CLEAR and CL-CLEAN-GUARD):**

| situation | expected |
|---|---|
| Verify in flight, user types `Q` in an unrelated cell, response arrives | `Q` is still there; flagged cells show `isError` |
| Clean in flight, user types, response arrives | confirm (if `N > 0`) is shown only for cells still holding the sent letter; the typed cell is untouched |
| Clean, `N > 0` | confirm text `Clean will remove N letters`; `Cancel` → grid, flags, toasts unchanged |
| Clean, `N > 0`, accept | those letters blank; theme-locked letters unchanged; toast = server `message` |
| Clean, `N === 0`, `removed_count === 0`, cells flagged red beforehand | no confirm; toast `Grid is clean — all words are valid!`; no cell has `isError` |
| Clean, `N === 0`, `removed_count > 0` (only theme-locked letters wanted) | no confirm; toast `Nothing removed: theme-locked letters are kept.`; no cell has `isError` |
| Verify in flight, `docId` changes (New grid or Open saved), response arrives (`PD-6-G12`) | nothing is written: no `isError` change on the new grid, no toast |
| Clean in flight, `docId` changes, response arrives (`PD-6-G12`) | nothing is written: no confirm, no `pendingClean`, no grid write, no toast |
| confirm open, user types a letter | confirm gone, nothing applied |
| confirm open, `autofill.state` becomes `submitting` | confirm gone, nothing applied |

- [ ] **Step 1: Write the failing tests.**
- [ ] **Step 2: Run** `npx vitest run src/lib/__tests__/gridEdits.test.js src/__tests__/components/App.test.jsx`. Expected: fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** both files, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/lib/gridEdits.js src/lib/__tests__/gridEdits.test.js src/App.jsx src/styles/bench/base.css src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "fix(grid): Verify and Clean apply to the current grid; Clean keeps theme-locked letters and asks first"
```

### Task 6.12: The Theme panel sits below the top bar (§3.6, TH5, G11)

**Files:**
- Modify: `src/styles/bench/tokens.css` (define `--xw-topbar-h: 54px` in `:root`, the single home of the number)
- Modify: `src/styles/bench/base.css` (`.xw-app`'s `grid-template-rows` reads `var(--xw-topbar-h) 1fr`)
- Modify: `src/components/ThemeWordsPanel.scss` (`.theme-words-panel`: `top: var(--xw-topbar-h)`, `height: calc(100vh - var(--xw-topbar-h))`)
- Possibly modify: `src/styles/bench/base.css` top-bar rules, only if the browser check (below) shows the top bar itself overflowing 1024 px
- Test: `src/__tests__/components/App.test.jsx`, `src/__tests__/themePanelLayout.test.js` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks (Task 6.7's prompt is exercised in the functional case).
- Produces: `--xw-topbar-h` (CSS custom property, `:root`).

**Behavioral criteria:**
- With the Theme panel open, the top bar, including the Save button and the theme toggle, is fully visible and clickable; the panel starts at the top bar's bottom edge and does not overlap it (§3.6). The offset is the layout's own value (`--xw-topbar-h`, the same variable `.xw-app` uses for its first row), not a second copied `54px`.
- The narrowest width tested is 1024 px (the QA run's smallest desktop width: `docs/dev/qa/2026-10-22-fresh-install-run.md` L4/ENV-3 measure 1440×900 and 1024×768, so the spec's `[?]` resolves to 1024); phone width is out of scope. The `@media (max-width: 768px)` rule in the panel stylesheet is left as is.
- The panel's existing `×` (`.close-btn`) keeps working.
- At 1024 px the whole top bar must fit: if, with the panel closed, the Save button's right edge exceeds the viewport (brand text plus Verify, Clean, Save, the saved label and the toggle in one flex row), the top bar sheds width in a way that keeps Save and the toggle on screen (for example hiding `.xw-brand-sub` and `.xw-pill` under the existing `@media (max-width: 1200px)` block); this is within TH5's "fully visible" and is decided by the measurement below, not by guess.

**How this is tested (vitest cannot measure layout; jsdom has no box model):**
1. Functional (vitest): in a mounted `App`, open Theme via the rail; `Save grid` is still in the document, enabled, and clicking it opens the Task 6.7 name prompt; the panel's `×` closes the panel.
2. Source guard (vitest, `src/__tests__/themePanelLayout.test.js`, in the style of `src/__tests__/blackSquareSuggestionsDeletion.test.js`): reads the three stylesheets and asserts `--xw-topbar-h` is defined exactly once in `tokens.css`, that `base.css`'s `.xw-app` rule and `ThemeWordsPanel.scss`'s `.theme-words-panel` rule both reference `var(--xw-topbar-h)`, and that `.theme-words-panel` no longer has `top: 0`. This guards the regression; it is **not** evidence that the layout is right.
3. **Browser check (the gate; required before the commit lands — owner rule "build-green + vitest ≠ works"):** run `python3 run.py` and `npm run dev`; per ENV-3 the window cannot be resized reliably, so load the app in a same-origin iframe sized exactly 1024×768 and again 1440×900 on `127.0.0.1` (not `localhost`). For each size: open the Theme tool; read `getBoundingClientRect()` of `.xw-topbar`, of the `Save grid` button and of `.theme-words-panel`; require panel `top` ≥ top bar `bottom`, Save's rect inside the viewport, and `document.elementFromPoint(centre of Save)` to be the Save button (or its child); then click Save and see the name prompt; click the theme toggle; click `×`. Record the measured rects in the task's commit body or the run notes. If any check fails the task is not done.

**Normative cases:**

| check | expected |
|---|---|
| `getComputedStyle(documentElement).getPropertyValue('--xw-topbar-h')` | `54px` (value as defined; the guard test reads the source) |
| browser, 1024×768 and 1440×900, panel open | panel `top` ≥ top bar `bottom`; Save centre hit-tests to Save; Save click opens the prompt |

- [ ] **Step 1: Write the failing tests** (functional App case; source guard).
- [ ] **Step 2: Run** `npx vitest run src/__tests__/themePanelLayout.test.js src/__tests__/components/App.test.jsx`. Expected: the guard fails (panel still `top: 0`, no variable).
- [ ] **Step 3: Implement** the CSS change.
- [ ] **Step 4: Run** the two files, `npx vitest run`, `npm run build`; then do the browser check above.
- [ ] **Step 5: Commit:**

```bash
git add src/styles/bench/tokens.css src/styles/bench/base.css src/components/ThemeWordsPanel.scss src/__tests__/themePanelLayout.test.js src/__tests__/components/App.test.jsx
git diff --cached --stat
git commit -m "fix(ui): the Theme panel starts below the top bar so Save stays reachable"
```

### Task 6.13: Theme suggestions refresh when the grid changes (§3.8 #19 panel half, TH2b)

**Files:**
- Modify: `src/components/ThemeWordsPanel.jsx` (`analyzePlacements`, `handleApplyPlacement`, a grid-change effect)
- Test: `src/__tests__/components/ThemeWordsPanel.test.jsx`

**Interfaces:**
- Consumes: `grid` and `gridSize` props (unchanged); `api.themeSuggestPlacements`; `react-hot-toast` (the panel's existing channel).
- Produces: `export const SUGGESTION_REFETCH_DEBOUNCE_MS: number` (planning default `PD-6-G13` (spec §8): the spec says "debounced" and gives no value; plan default `400`); no prop change.

**Behavioral criteria:**
- While suggestions are showing (`suggestions` non-null), any change to the grid's letters or black squares runs `analyzePlacements` again for the same `themeWords`, debounced by `SUGGESTION_REFETCH_DEBOUNCE_MS`, and replaces the list (§3.8). "Change" = a difference in the per-cell `[letter, isBlack]` signature (and `gridSize`); changes to `isError`, `number`, `isHighlighted`, `isThemeLocked` or `isAutofilled` alone do not refetch.
- Several changes inside one debounce window produce one refetch. The upload's own auto-analyze records the grid signature it used, so no extra fetch follows it.
- A response that is not for the latest grid signature (a newer change happened while it was in flight) is dropped.
- **Superseded entries:** a list is superseded from the moment the grid signature differs from the one it was fetched with until the replacing list lands. `Apply This Placement` on an entry of a superseded list does nothing — no `api.themeApplyPlacement` call, no `onApplyPlacement` call — and shows the toast `Suggestions updated for the changed grid.` (§3.8; channel per planning default `PD-6-G14` (spec §8)). `Apply All Best Placements` on a superseded list is likewise a no-op with the same toast (the spec's rule that a placement offered before the change is never applied after it).
- Apply All's own sequential applications change the grid prop while it runs; the refetch is suspended while `applyingAll` and, if the grid changed during the loop, runs once after it ends (planning default `PD-6-G15` (spec §8)). A single `Apply This Placement` that succeeds changes the grid and therefore triggers one refetch like any other change.
- The refetch is silent: it does not push the `Found placement suggestions for N words!` toast (planning default `PD-6-G16` (spec §8)); a failed refetch pushes the same error toast as `analyzePlacements` does today and leaves the old list marked superseded.
- With no suggestions showing (before an upload, or after a failed analyze) a grid change fetches nothing.

**Normative cases:**

| situation | expected |
|---|---|
| upload words, suggestions show; `themeSuggestPlacements` called once so far | no further call |
| then rerender with the grid's letter at (0,0) changed; advance `SUGGESTION_REFETCH_DEBOUNCE_MS` | exactly one more call, `themeWords` identical, `existingGrid` reflects the change; the list is replaced |
| two letter changes inside one window | one more call |
| a black square added | one more call |
| only `isError` / `number` / `isThemeLocked` changed | no call |
| grid changed twice, first response resolves after the second request started | the first response is ignored |
| suggestions not yet loaded; grid changes | no call |
| grid changed, debounce pending, click `Apply This Placement` | no `themeApplyPlacement` request, `onApplyPlacement` not called, toast `Suggestions updated for the changed grid.` |
| grid unchanged, click `Apply This Placement` | applies as today |
| Apply All with 3 words, each apply changes the grid prop | no refetch until the loop ends; then one |

- [ ] **Step 1: Write the failing tests** (fake timers for the debounce; rerender the panel with a new `grid` prop; assert request counts through the existing `mockApiEndpoint` helper).
- [ ] **Step 2: Run** `npx vitest run src/__tests__/components/ThemeWordsPanel.test.jsx`. Expected: fail (no refetch exists).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the file, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/components/ThemeWordsPanel.jsx src/__tests__/components/ThemeWordsPanel.test.jsx
git diff --cached --stat
git commit -m "feat(theme): refetch placement suggestions when the grid changes; stale Apply is a no-op"
```

### Task 6.14: Apply All reports each word's real failure (§3.8 #20, TH3)

**Files:**
- Modify: `src/components/ThemeWordsPanel.jsx` (`handleApplyAllPlacements`; a module-private `describeApplyFailure`)
- Test: `src/__tests__/components/ThemeWordsPanel.test.jsx`

**Interfaces:**
- Consumes: `ApiError` shape from `src/api/client.js` (`status`, `code`, `message`, `details`; a network failure is `status: 0`, `code: 'NETWORK'`).
- Produces: none exported.

**Behavioral criteria:**
- `handleApplyAllPlacements` keeps each skipped word's reason instead of counting it in a bare catch (§3.8).
- The count `N` in the summary is the number of words **this action** applied (a placement applied earlier by `Apply This Placement`, or by an earlier Apply All, is not counted).
- Reasons, per skipped word:
  - a failure whose `details` is a non-empty array (the 400 `conflicts` shape `handleApplyPlacement` already reads): `skipped due to conflicts: ` + the first detail, plus ` (+K more)` when there are `K` further details — the same first-plus-count rule as `handleApplyPlacement` (§3.8: "as `handleApplyPlacement` already shows it");
  - `status === 0` (no response): `Could not reach the server` (planning default `PD-6-G17` (spec §8) on the reading);
  - any other failure: the error's `message`, or `Failed to apply placement` when the message is empty (the existing `handleApplyPlacement` fallback; RED-1 forbids showing the synthesised `HTTP_500` code);
  - a word skipped without a request: no suggestions → `no valid placement`; best suggestion whose `reasoning` contains `WARNING` → `skipped due to conflicts: ` + that reasoning (planning default `PD-6-G18` (spec §8)).
  `skipped due to conflicts` appears only in the two conflict reasons above (§1 Theme suggestions, §3.8).
- Summary text, pushed with `toast.success`/`toast.error` and `{ id: 'apply-all' }` as today (planning default `PD-6-G19` (spec §8) on the format): `Applied N theme words successfully!` when `N > 0`, else `Could not apply any theme words`; when anything was skipped, append ` Skipped: WORD (reason); WORD (reason)` in suggestion order. The old `(K skipped due to conflicts)` suffix is gone.
- A superseded list makes Apply All a no-op (Task 6.13); the loop's own grid changes do not count as supersession.

**Normative cases** (suggestions for `ALPHA`, `BETA`, `GAMMA`, `DELTA`; best suggestions apply in that order):

| `ALPHA` | `BETA` | `GAMMA` | `DELTA` |
|---|---|---|---|
| 400, body `{error:'Placement conflicts detected', conflicts:['ALPHA at (0,0) overlaps R']}` | 500, body `{error:'boom'}` | network failure (`fetch` rejects) | 200 with a grid |

Expected summary: `Applied 1 theme words successfully! Skipped: ALPHA (skipped due to conflicts: ALPHA at (0,0) overlaps R); BETA (boom); GAMMA (Could not reach the server)`. Three different reasons; `N` is 1.

| other situation | expected |
|---|---|
| a word skipped with `details` of two entries `['a','b']` | reason `skipped due to conflicts: a (+1 more)` |
| 500 with empty body | reason `Failed to apply placement` (never `HTTP_500`) |
| all four fail | `Could not apply any theme words Skipped: …` with all four reasons |
| one placement applied earlier by `Apply This Placement`, then Apply All applies one more | `Applied 1 theme words successfully!` (counts only its own) |
| a word with an empty suggestion list | reason `no valid placement` |

- [ ] **Step 1: Write the failing tests** (`mockApiEndpoint` for the 400 and 500; make the third request reject at the fetch layer for the network case).
- [ ] **Step 2: Run** `npx vitest run src/__tests__/components/ThemeWordsPanel.test.jsx`. Expected: fail (the summary still reads `skipped due to conflicts` for every failure).
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the file, `npx vitest run`, `npm run build`.
- [ ] **Step 5: Commit:**

```bash
git add src/components/ThemeWordsPanel.jsx src/__tests__/components/ThemeWordsPanel.test.jsx
git diff --cached --stat
git commit -m "fix(theme): Apply All names each skipped word's real reason and counts only its own applies"
```

### Task 6.15: Phase 6 browser drive (no code; the owner's GUI gate)

**Files:** none. Record each result (pass, or the measurement) in the phase notes; Phase 8 repeats the cases formally on a fresh clone.

Run `python3 run.py` and `npm run dev`; drive the real browser on `127.0.0.1` (not `localhost`, ENV-3):

- [ ] **Step 1: Hiding (G8/G9/CL1/A-SBS/EXPORT-HIDE).** Rail has no Clues and no Heatmap; Autofill panel has no Suggest Black Square; Export panel has no PDF/.puz option, no Include clues checkbox, no PDF/.puz line under Format Information.
- [ ] **Step 2: Black squares (G1, G7).** Grid panel shows New grid, Black square, Open saved; hint line visible under the grid; Black square on a selected cell blackens it and its mirror; Ctrl+L a cell, then Space on it and on its mirror: both refused and the button disabled.
- [ ] **Step 3: New grid (G1, #55).** From a grid with letters choose `11×11`: confirm appears; Cancel changes nothing; Replace gives a numbered blank 11×11. Repeat with `15×15` on a 15×15 that has letters and no black squares: numbers are present.
- [ ] **Step 4: Saves (G3, SAVE-NAMED, SAVE-SIZE, SAVE-TABS, AF-SAVE-RUN where autofill exists).** Type, wait 30 s, reload: banner `Restored "<name>" (saved <time>)`, `×` and `Start blank` work. Save under a name; Open saved, Delete (answer the `Delete "<name>"?` confirm with Cancel, then with Delete). Save a 21×21, switch to 11×11, reload and Open saved: letters restored at 21×21. Two tabs on one saved grid, edit and save in both: second save forks `<name> (copy)`. Fill storage until a write fails: explicit Save shows the quota text.
- [ ] **Step 5: Guards (SR-PLACE, CL-CLEAR, CL-CLEAN-GUARD).** Place a Search result across a black square and a theme-locked cell; Verify, retype flagged cells, Clean; theme-lock a word, type an invalid word elsewhere, Clean: Cancel changes nothing, accept removes only non-locked letters; type while Verify is in flight.
- [ ] **Step 6: Theme (TH5, TH2b, TH3).** Task 6.12's measurements, and: with suggestions showing, place a black square: the list refreshes; apply one placement then Apply All with one conflicting word: summary names the word and its reason.
- [ ] **Step 7: Commit nothing.** If any step fails, fix it in the owning task and re-run this task.

### Phase 6 traceability: every "Tests:" item in §3.1–§3.8

| Spec test item | Task |
|---|---|
| §3.1 `ToolRail.test.jsx` edits (Clues, Heatmap) | 6.1 |
| §3.1 `AutofillPanel.test.jsx` "Suggest Black Square" | 6.1 |
| §3.1 assertion that none of the hidden labels renders, incl. ExportPanel (G10) | 6.1 |
| §3.3 G7: toggle and key refuse a theme-locked cell or partner | 6.2 (rule, key path, App), 6.3 (button) |
| §3.3 hint test: every named key handled by `dispatchGridKey` | 6.2 |
| §3.4 legacy-key migration | 6.5 |
| §3.4 name collision asks to replace | 6.7 (prompt), 6.5 (`replaceEntryId`) |
| §3.4 banner and its dismissal | 6.8 |
| §3.4 document-id minting: New grid, import | 6.4 (New grid); import: assert in 6.7 that after `handleGridImport` an autosave writes an entry under the new id and leaves the earlier entry untouched (Phase 4 owns the mint) |
| §3.4 document-id adoption: Open saved, restore | 6.8, 6.9 |
| §3.4 S2 reload mid-run restores the Start grid | 6.7 |
| §3.4 S3 restore and Open saved across sizes | 6.8, 6.9 |
| §3.4 S4 changed `savedAt` forks `(copy)` | 6.5 (storage), 6.6 (machine), 6.7 (`onForked` → `setDocId`) |
| §3.5 step 3, both toasts | 6.11 |
| §3.5 G6 no mutation | 6.10 |
| §3.5 S1 typing survives Verify/Clean; Start or a grid change dismisses the confirm | 6.11 |
| §3.6 top bar and Save visible and clickable at 1024 px | 6.12 (browser check), 6.15 |
| §3.8 refetch on grid change | 6.13 |
| §3.8 superseded Apply is a no-op | 6.13 |
| §3.8 Apply All: 400 conflict, 500, network failure → three reasons | 6.14 |
---

## Phase 7: word lists and CLI (spec §4; P5, Phase 0.3)

Independent of the solver seams. Every docstring/comment implementing a rule cites `novice-readiness spec 0.2.4 §4 (L11 | SR4 | CLI-normalize)`.

**Names pinned by this phase (all in `cli/src/fill/word_list.py` unless stated):**

```python
def fold_letters(text: str) -> str: ...          # module level; case preserved
class WordList:
    @staticmethod
    def parse_line(line: str) -> Optional[Tuple[str, Optional[int]]]: ...  # signature unchanged; the word part is folded
    @staticmethod
    def canonical_word(text: str) -> str: ...     # fold, strip, then uppercase only if the folded text is ASCII
    def _is_valid_word(self, word: str) -> bool: ...                        # signature unchanged; now ASCII A-Z only
```

### Task 7.1: L11 fold in the shared load path (§4 item 1, P5)

**Files:**
- Modify: `cli/src/fill/word_list.py` (`add_words` lines 56-115, `_is_valid_word` 148-170, `parse_line` 228-258; add `fold_letters`, `WordList.canonical_word`)
- Modify: `cli/src/cli.py` (`parse_wordlist` command, its docstring and the `word.upper()` / `_is_valid_word` sequence, ≈ lines 2270-2320)
- Modify: `docs/specs/CLI_SPEC.md` (the `parse-wordlist` section: "Words are uppercased" now also says accented letters are folded)
- Test: `cli/tests/unit/test_word_list.py`, `cli/tests/unit/test_parse_wordlist_command.py`, `backend/tests/integration/test_parse_wordlist_e2e.py`, `cli/tests/unit/test_letter_bitset.py`

**Interfaces:**
- Consumes: nothing from earlier phases.
- Produces: `fold_letters`, `WordList.canonical_word` (Task 7.3 uses `WordList.from_file`, which calls these); `parse-wordlist` JSON where `words[].word` is the folded word and `skipped[].text` is the original stripped line.

**Behavioral criteria:**
- `fold_letters(text)`: Unicode NFKD decomposition, then drop combining marks (§4: "folds letters to A–Z with Unicode NFKD decomposition, dropping combining marks"). Case is preserved; the function is idempotent; text that has nothing to fold is returned equal.
- The fold applies at every point a line becomes a word: `parse_line` folds the word part (score parsing unchanged), `add_words` folds each entry before validation, so `WordList(["CAFÉ"])`, `WordList.from_file`, `fill`'s loader (`cli.py` ≈ line 788), `_load_wordlist_words` (resume) and `pattern` (`from_file`) all fold identically, and so does `parse-wordlist` (§4: "so the solver and the upload preview fold identically").
- `WordList.canonical_word(text)` returns the folded, stripped text, uppercased **only when the folded text is ASCII**. Reason (code-vs-spec finding): `"ß".upper()` is `"SS"`, so uppercasing before validating would accept `ß`, which §4 says is skipped; a character that is still non-ASCII after the fold must reach `_is_valid_word` unchanged. `add_words` and `parse-wordlist` both use `canonical_word`.
- `_is_valid_word` requires 3–21 characters, all ASCII `A`–`Z` (§4: "tightened from `isalpha()` plus `isupper()`, which accept non-ASCII letters, to require ASCII A–Z"). A word still containing a non-A–Z letter after the fold is skipped; in `parse-wordlist` its reason is `not letters only` (§4). Length is still classified before letters (existing rule; see planning default `PD-L6` (spec §8) on bare `ß`).
- Duplicates are detected after the fold (`CAFE` then `CAFÉ` keep the first, existing "keep first occurrence" rule).
- The upload preview (`POST /api/wordlists/import` with `dry_run: true`) needs no backend change: it returns the CLI's parse result, so the folded word is what it shows. The stored lines (`WORD;N`) are folded for the same reason.
- `ß`, `Æ`, `Ø` have no NFKD decomposition and stay skipped with `not letters only` (§4).
- `cli/tests/unit/test_parse_wordlist_command.py::test_accented_word_accepted` currently pins `CAFÉ` → `CAFÉ`; it is rewritten to the fold. `cli/tests/unit/test_letter_bitset.py::_word_list_spanning_n_letters` and its docstring ("`WordList._is_valid_word` accepts any `str.isalpha()` and `str.isupper()` text") become false: a `WordList` can no longer hold more than 26 distinct letters. The helper must build its >26-letter alphabets without going through `WordList` validation (for example by constructing `ScoredWord`s and the indices directly) so the 64-letter boundary tests (`test_from_word_list_rejects_alphabet_over_64_letters`, `…accepts_alphabet_of_exactly_64_letters`, `test_top_alphabet_bit_is_live_through_letters_at_and_restrict`) keep covering the same boundary. Sweep the reason, not only the call sites (`.claude/CLAUDE.md`).

**Normative cases** — one input line to `parse-wordlist` / `WordList.from_file` (L11):

| input line | result |
|---|---|
| `CAFÉ` | word `CAFE`, score `null` |
| `NAÏVE` | word `NAIVE` |
| `ÜBER` | word `UBER` |
| `café` | word `CAFE` |
| `CAFÉ;50` | word `CAFE`, score `50` |
| `CAFE` + U+0301 (decomposed) | word `CAFE` |
| `ＣＡＴ` (fullwidth, U+FF23 U+FF21 U+FF34) | word `CAT` (NFKD, not NFD) |
| `CAFE` then `CAFÉ` on two lines | one word `CAFE`, nothing skipped |
| `STRAßE` | skipped, reason `not letters only`, `text` `STRAßE` |
| `ÆON` | skipped, reason `not letters only` |
| `BJØRN` | skipped, reason `not letters only` |
| `ONE TWO` | skipped, reason `not letters only` (unchanged) |
| `AB` | skipped, reason `length outside 3-21` (unchanged) |
| `ΑΒΓ` (Greek capitals) | skipped, reason `not letters only` |
| `WordList.canonical_word("ß")` | `"ß"` (not `"SS"`) |
| `WordList._is_valid_word("CAFÉ")` / `("CAFE")` | `False` / `True` |

- [ ] **Step 1: Write the failing tests.** Cover every row at the level that owns it: `fold_letters`/`canonical_word`/`_is_valid_word`/`add_words` in `test_word_list.py`; the `parse-wordlist` rows in `test_parse_wordlist_command.py` (subprocess, as that file does); one folded row and one `not letters only` row added to the fixture of the real-CLI seam test `test_parse_wordlist_through_real_cli` in `backend/tests/integration/test_parse_wordlist_e2e.py` (spec §4 item 1: the fold rows are *added* to that file, which "has no accented input today"). Rewrite the expectation of `cli/tests/unit/test_parse_wordlist_command.py`'s `test_accented_word_accepted` (`CAFÉ` was kept as `CAFÉ`; it becomes `CAFE`), and pin the `ß` → `SS` trap (spec §4: "Folding uppercases only ASCII letters: `"ß".upper()` is `"SS"`") with the `STRAßE` row above. Rebuild the `_word_list_spanning_n_letters` helper.
- [ ] **Step 2: Run, confirm failure is the missing fold:**

```bash
pytest cli/tests/unit/test_word_list.py cli/tests/unit/test_parse_wordlist_command.py cli/tests/unit/test_letter_bitset.py backend/tests/integration/test_parse_wordlist_e2e.py -v
```
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the same command, confirm pass.** Then run the whole CLI suite alone: `pytest cli/tests -m "not slow"`; read the result on its own line.
- [ ] **Step 5: Commit:**

```bash
git add cli/src/fill/word_list.py cli/src/cli.py docs/specs/CLI_SPEC.md cli/tests/unit/test_word_list.py cli/tests/unit/test_parse_wordlist_command.py cli/tests/unit/test_letter_bitset.py backend/tests/integration/test_parse_wordlist_e2e.py
git diff --cached --stat
git commit -m "feat(wordlist): fold accented letters to A-Z on every load and tighten word validity to ASCII"
```

### Task 7.2: a pre-fold cache cannot be served (§4 item 1, P5)

**Files:**
- Modify: `cli/src/fill/word_list.py` (`to_cache`, `from_cache`, and the cache branch of `from_file`)
- Test: `cli/tests/unit/test_word_list.py` (extend `TestFromFileCacheFallback`)

**Interfaces:**
- Consumes: Task 7.1's fold.
- Produces: `from_file(path, use_cache=True)` never returns a word that a fresh text load of the same file would not return.

**Behavioral criteria:**
- Context: `from_file` serves a sibling `.pkl` whenever its mtime is newer than the text list's; the cache stores `ScoredWord`s and indices as built by the code that wrote it (`to_cache` writes `"version": "1.0"`; `from_cache` does not check it). A cache written before Task 7.1 can hold `CAFÉ`. After this task such a cache is not used: `from_file` falls back to the text list through its existing warning-and-reload path.
- A cache written after this task (including by `build-cache`, which loads with `use_cache=False`) is used when newer, exactly as today.
- Spec basis: spec §4 item 1: "The fold lives in the shared load path, `WordList.from_file → parse_line → add_words` in `cli/src/fill/word_list.py`, so the solver and the upload preview fold identically". `from_file` serves a newer `.pkl` without parsing, so a cache entry built before the fold would make the solver load unfolded words and the sentence would be false; this task is a derivation of that sentence. The mechanism is the implementer's. Reference hint, not the step: bumping the `"version"` value written by `to_cache` and having `from_cache` raise `ValueError` on a missing or older value routes a stale cache into the existing `except Exception` fallback.
- Caches are gitignored (`data/wordlists/**/*.pkl`); nothing tracked changes.

**Normative cases:**

| setup | `WordList.from_file(path, use_cache=True)` |
|---|---|
| text file `CAFÉ\nDOGS`; sibling `.pkl` written in the pre-change layout holding the `ScoredWord` text `CAFÉ`, mtime newer than the text file | words are `CAFE`, `DOGS` (no non-ASCII word) |
| same text file; `.pkl` written by `to_cache` after this task, newer | the cache is used (words equal the cached words) |
| same text file; `.pkl` older than the text file | the text file is read |

- [ ] **Step 1: Write the failing test** for row 1 (build the pre-change cache by constructing the `ScoredWord` directly and writing the pre-change dict layout; do not call the new `to_cache`).
- [ ] **Step 2: Run, confirm the stale cache is served:** `pytest cli/tests/unit/test_word_list.py -k Cache -v`.
- [ ] **Step 3: Implement. Step 4: Run, confirm pass.**
- [ ] **Step 5: Commit:**

```bash
git add cli/src/fill/word_list.py cli/tests/unit/test_word_list.py
git diff --cached --stat
git commit -m "fix(wordlist): a cache written before the accent fold is never served"
```

### Task 7.3: `verify_words` and `clean_grid` load lists through the shared parser (§4 item 1, P5 `[?]`, Phase 0.3)

**Files:**
- Modify: `backend/api/routes.py` (`verify_words` ≈ lines 745-752 and `clean_grid` ≈ lines 936-945: the `open(...)`/`line.split(";")[0].strip().upper()` loops)
- Test: `backend/tests/unit/test_routes.py` (the `/api/grid/verify-words` and `/api/grid/clean` sections, ≈ lines 510-640)

**Interfaces:**
- Consumes: `WordList.from_file`, `fold_letters`, `canonical_word` from Tasks 7.1-7.2.
- Produces: both routes accept exactly the words `WordList.from_file(path)` accepts.

**Behavioral criteria:**
- Both routes obtain the list's words from the shared loader (`WordList.from_file`, or `parse_line` plus `canonical_word` plus `_is_valid_word`; the implementer's choice) instead of their own parser. The routes stay in `backend/api/routes.py` (recorded deviation, plan Global Constraints; no move to `cli/`).
- Consequence of P5 ("every word-list load"): the accepted set equals the solver's. Differences from today, all intended: accented words fold (`NAÏVE;50` loads `NAIVE`); `word,score` lines now load (the old loop split on `;` only and dropped them); lines the solver rejects (non-ASCII after the fold) are rejected.
- Slot classification, response shape and the existing swallow-and-skip of an unreadable list are unchanged.
- The routes are checked with a stale pre-fold `.pkl` beside the test list, so they cannot be served one whether or not they use the cache.
- Comments cite `novice-readiness spec 0.2.4 §4 (L11, P5)`.

**Normative cases** (custom list file named in `wordlists`; grid rows typed in A–Z):

| list line | grid slot | `verify-words` | `clean` |
|---|---|---|---|
| `NAÏVE;50` | `NAIVE` | not in `invalid_words` | slot not cleared |
| `café,40` | `CAFE` | not in `invalid_words` | not cleared |
| `STRAßE` | `STRASSE` | in `invalid_words` | cleared |
| `ONE` and slot `ONE` | | not invalid | not cleared (control: unchanged behaviour) |

Parity: for a fixture list holding every row of Task 7.1's table, the word set the routes accept equals `{w.text for w in WordList.from_file(path, use_cache=False).words}`.

- [ ] **Step 1: Write the failing tests** (rows + parity). **Step 2: Run:** `pytest backend/tests/unit/test_routes.py -k "verify or clean" -v` — confirm the fold rows fail on the old parser. **Step 3: Implement. Step 4: Run, confirm pass.**
- [ ] **Step 5: Backend suite alone:** `pytest backend/tests -m "not slow"`; read the result on its own line.
- [ ] **Step 6: Commit:**

```bash
git add backend/api/routes.py backend/tests/unit/test_routes.py
git diff --cached --stat
git commit -m "fix(grid): verify and clean read word lists through the parser the solver uses"
```

### Task 7.4: Search is disabled with no word list (§4 item 2, SR4)

**Files:**
- Modify: `src/components/PatternMatcher.jsx` (the Search button ≈ line 150, `searchPattern` ≈ line 38, `handleKeyPress` ≈ line 117)
- Test: `src/__tests__/components/PatternMatcher.test.jsx` (extend)

**Behavioral criteria:**
- With `selectedWordlists` empty the Search button is disabled and the hint `Select at least one word list` is visible (§4 item 2, verbatim). With at least one list ticked the button is enabled (unless a search is loading, as today) and the hint is absent.
- "The CLI's built-in fallback list is not reachable from the UI": pressing Enter in the pattern input with no list ticked sends no request either (`searchPattern` returns early).
- The hint and the disabled state clear the moment a list is ticked. No server or CLI change.
- Comments cite `novice-readiness spec 0.2.4 §4 (SR4)`.

**Normative cases:**

| state | Search button | hint `Select at least one word list` | request on click / Enter |
|---|---|---|---|
| default (`comprehensive` ticked) | enabled | absent | sent |
| last list unticked | disabled | present | none |
| unticked, then a list ticked | enabled | absent | sent |
| zero ticked, Enter in the pattern input | disabled | present | none |

- [ ] **Step 1: Write the failing tests. Step 2: Run:** `npx vitest run src/__tests__/components/PatternMatcher.test.jsx` — confirm failure is the missing disabled state. **Step 3: Implement. Step 4: Run, confirm pass.** **Step 5:** `npm run build`.
- [ ] **Step 6: Commit:**

```bash
git add src/components/PatternMatcher.jsx src/__tests__/components/PatternMatcher.test.jsx
git diff --cached --stat
git commit -m "fix(ui): Search is disabled until a word list is selected"
```

### Task 7.5: default `normalize` keeps letters only (§4 item 3, CLI-normalize)

**Files:**
- Modify: `cli/src/core/conventions.py` (`ConventionHelper.normalize`, the default branch ≈ lines 97-108)
- Modify: `cli/src/cli.py` (`normalize` command docstring ≈ line 1729, only if its examples contradict the new default)
- Modify: `docs/specs/CLI_SPEC.md` (the `normalize` section, if it states the default)
- Test: `cli/tests/unit/test_conventions.py` (create); `backend/tests/test_api.py` (`TestNormalizeEndpoint` keeps passing unchanged)

**Behavioral criteria:**
- The default rule (no named rule matched) keeps letters only and uppercases: `normalize "Hello, World!"` → `HELLOWORLD` (§4 item 3).
- The named rules in `RULES` (`two_word_names`, `title_with_article`, `hyphenated`, `apostrophe`) are unchanged in pattern, transform and examples; they are checked first, in the same order (§4: "keep their behaviour; only the default rule changes").
- The default rule's `rule_info["type"]` stays `"default"`. Its `description`/`explanation` text must stop saying "remove spaces, uppercase" because that no longer describes it (docstring-as-testable-claim); proposed default wording `Default: keep letters only, uppercase`. **Planning default `PD-L7` (spec §8): wording, non-ASCII letters, empty result.** The behaviour for non-ASCII letters is not asserted by any normative row.
- Comments cite `novice-readiness spec 0.2.4 §4 (CLI-normalize)`.

**Normative cases** (`python -m cli.src.cli normalize "<text>" --json-output`, field `normalized`):

| input | `normalized` | `rule.type` |
|---|---|---|
| `Hello, World!` | `HELLOWORLD` | `default` |
| `Tina Fey` | `TINAFEY` | `two_word_names` |
| `The Office` | `THEOFFICE` | `title_with_article` |
| `self-aware` | `SELFAWARE` | `hyphenated` |
| `can't` | `CANT` | `apostrophe` |

- [ ] **Step 1: Write the failing test** (CLI through `CliRunner` or subprocess, as neighbouring CLI tests do). **Step 2: Run:** `pytest cli/tests/unit/test_conventions.py -v` — confirm only the first row fails. **Step 3: Implement. Step 4: Run, confirm pass; then `pytest backend/tests/test_api.py -k Normalize -v`.**
- [ ] **Step 5: Commit:**

```bash
git add cli/src/core/conventions.py cli/src/cli.py docs/specs/CLI_SPEC.md cli/tests/unit/test_conventions.py
git diff --cached --stat
git commit -m "fix(cli): the default normalize rule keeps letters only"
```

(Stage only the files this task changed; drop `cli/src/cli.py` / `docs/specs/CLI_SPEC.md` from `git add` if untouched, and read `git diff --cached --stat` before committing.)
---

## Phase 8: acceptance (spec §6)

**Method (binding, from `docs/dev/qa/2026-10-22-fresh-install-run.md`).**
- Fresh clones of the committed `feat/novice-readiness` tip: E1 = CPython 3.13.7 (uv download only) + current Node LTS; E2 = the Xcode CLT `/usr/bin/python3` first on `PATH` + the same Node. Wrapper scripts run one command string under `env -i` (ENV-1, ENV-2).
- Functional cases run top-level on `http://127.0.0.1:5000` (ENV-3: the browser tool cannot set the window size; `localhost` carries a stored page zoom). Layout cases (TH5 at the desktop viewport and at 1024 px; the Lists rows if re-run) are measured inside a same-origin iframe sized exactly 1440×900 and 1024×768, reading the iframe's own `innerWidth/innerHeight`, as L3 and L4 did.
- Evidence goes to `/Users/apa/projects/crossword-helper/.handoff/artifacts/<YYYY-MM-DD>-novice-readiness/` (gitignored; exists only in the main checkout). Reuse `…/2026-10-22-fresh-install/driver/api_probe.py` and `api_probe2.py` as the model for API-level observations (they hard-code `/private/tmp/crossword-fresh/crossword-helper/data/grids/` and `http://127.0.0.1:5000/api`; copy and adapt the paths, do not edit the originals).
- The run log is `docs/dev/qa/YYYY-MM-DD-novice-readiness-run.md`, dated the day it runs, using the old log's case-block format verbatim (`### <ID> — <title>` / Phase · Env · Viewport / Steps / Expected / Observed / Evidence / Verdict: PASS|FAIL|BLOCKED|NOT-IMPLEMENTED|UNSPECIFIED|NOT-TESTABLE · Severity · Known). Observed values are pasted command output, never typed.
- **A FAIL is recorded, not fixed here.** On any FAIL: STOP and report to Arthur; the fix returns to the owning phase and the row is re-run cold.

### Task 8.1: README control-name sweep against the finished UI

**Files:** Modify: `README.md` ("Using the app").

**Criteria:** after Phases 4-6 landed, every control name the tour backticks appears in `src/` as a rendered label, and no hidden control (Clues, Heatmap, Suggest Black Square, PDF, `.puz`) is named as available. The tour is extended with `New grid`, `Black square`, `Open saved` under Grid and the save-name prompt under Save only as those labels exist in the code (§3.2-§3.4).

- [ ] **Step 1:** for each backticked name in the tour, `git grep -n -F -- '<name>' -- src ':!src/__tests__'`; list the misses.
- [ ] **Step 2:** edit the tour to fix misses and add the Phase 6 controls.
- [ ] **Step 3:** `bash scripts/docs-check.sh`, read the result on its own line.
- [ ] **Step 4: Commit:** `git add README.md`; `git diff --cached --stat`; `git commit -m "docs(readme): tour names match the shipped controls"`.

### Task 8.2: harness, fresh clones, run-log header

**Files:** Create: `docs/dev/qa/YYYY-MM-DD-novice-readiness-run.md` (header only); scratch `SB=$(mktemp -d)` for tools, clones and fixtures.

**Wrappers, verbatim shape (from the 2026-10-22 run; `$SB` is this run's sandbox):**

```bash
# $SB/e1.sh — one command string under the E1 environment
exec /usr/bin/env -i HOME="$SB/home" PATH="$SB/tools/node/bin:$SB/tools/python/<cpython-3.13.7-dir>/bin:/usr/bin:/bin:/usr/sbin:/sbin" TERM=xterm LANG=en_US.UTF-8 /bin/bash -c "$1"
# $SB/e2.sh — the same without the E1 python segment
exec /usr/bin/env -i HOME="$SB/home" PATH="$SB/tools/node/bin:/usr/bin:/bin:/usr/sbin:/sbin" TERM=xterm LANG=en_US.UTF-8 /bin/bash -c "$1"
```

- [ ] **Step 1: Pin the artefact.** In the worktree: `git status --short` must be empty; `git rev-parse --short HEAD` is the sha under test. Everything below clones exactly that sha.
- [ ] **Step 2: Tools.** `UV_PYTHON_INSTALL_DIR="$SB/tools/python" uv python install 3.13.7`; Node LTS tarball into `$SB/tools/node` with its SHA-256 verified against `SHASUMS256.txt`; write `e1.sh`, `e2.sh`; run the ENV-1/ENV-2 probe (`python3 --version`, `which -a python3 node npm`, `env`) through each and keep the output.
- [ ] **Step 3: Clones.** `git clone --local /Users/apa/projects/crossword-helper-novice "$SB/e1/crossword-helper"` and `…/e2/crossword-helper`; `git -C <clone> checkout <sha>`; `git -C <clone> status --short` empty in both (CLONE-1).
- [ ] **Step 4: Fixtures.** Recreate F7 (non-ASCII: the words of L11, `CAFÉ`, `NAÏVE`, `ÜBER`, plus one `ß`, one `Æ` and one `Ø` word) from the 2026-10-22 definition (`FIX-1` in the old log; fixtures are under `/private/tmp/crossword-fresh/fixtures/` only while that directory survives). Fixtures for AF-BLOCK-LEN and AF-LOCKED-CROSS are built in Task 8.6 when needed. Keep all under `$SB/fixtures`.
- [ ] **Step 5: Write the header** of the run log: clone sha, E1/E2 interpreter and Node versions (pasted), the ENV-3 viewport method sentence, and a coverage table with one row per §6 "Area" cell (copied from the spec, one line each) whose Verdict column is filled by Tasks 8.3-8.7.
- [ ] **Step 6: Commit the header:** `git add docs/dev/qa/<run-log>`; `git diff --cached --stat`; `git commit -m "docs(qa): novice-readiness acceptance run, header and environment"`.

### Task 8.3: install-side rows (E1, E2, host)

§6 rows, copied verbatim (the checklist is these rows; do not paraphrase):

| Area | Cases | Pass criterion |
|---|---|---|
| Install | SETUP-1, SETUP-2, SETUP-3, E2-SETUP-1, SERVE-1 | Setup completes, the tree stays clean, debug off |
| New: ZIP | SETUP-1 and the README `pattern`, `analyze` and `fill` examples on a GitHub "Download ZIP" extract (not a clone), following the README's `chmod +x setup.sh` | Setup completes; the examples run; Search for `C?T` returns CAT, COT and CUT; `chmod +x` alone is enough |
| New: PORT | Start with `PORT=<other>` while :5000 is held, and with the port in use; the Vite proxy with the same `PORT` | The app serves on `<other>`; the in-use case prints `Port <n> is in use. Start with PORT=<other> python3 run.py`, no traceback |
| New: SETUP-MISSING | `setup.sh` with each tool (python3, node, npm) absent in turn; `FLASK_DEBUG=1 python3 run.py` | Each prints its `Missing: <tool> <minimum version> — install from <url>` and exits 1; debug is off unless `FLASK_DEBUG=1` |

**Case procedures (the 2026-10-22 definitions, re-run):** SETUP-1 = `$SB/e1.sh "cd <clone> && chmod +x setup.sh && ./setup.sh"` timed, exit code read on its own line; SETUP-2 = `venv/bin/python --version`, `venv/bin/pip list`, `npm ls --depth=0`, `ls -l frontend/dist/index.html`; SETUP-3 = `git status --short` and `git diff --stat` in the clone after setup (pass: empty, "the tree stays clean"); E2-SETUP-1 = the same setup in the E2 clone; SERVE-1 = `source venv/bin/activate`, `python3 run.py` in the background, `curl` of `/` (200, contains `<div id="root">`) and `/api/health`, and the server banner must read debug off (no "Debugger is active", no PIN). ZIP: `git archive --format=zip -o "$SB/zip/crossword-helper.zip" <sha>`, extract with `unzip` into a new empty directory, `chmod -x setup.sh` first if the extract kept the mode (GitHub's ZIP does not reliably), then follow the README only: `chmod +x setup.sh && ./setup.sh`, the README `pattern`, `analyze` and `fill` examples verbatim, then `python3 run.py` and, in the browser, Search `C?T`. PORT and SETUP-MISSING: the exact commands of Task 1.2 Step 5 and Task 1.4 Step 6, run under E1, with `PORT` also exported to `npm run dev` and `curl http://127.0.0.1:3000/api/health` through the proxy.

- [ ] **Step 1:** run each case, one `### <ID>` block per case in the run log (SETUP-1, SETUP-2, SETUP-3, E2-SETUP-1, SERVE-1, ZIP, PORT, SETUP-MISSING), evidence files under the evidence dir.
- [ ] **Step 2:** fill the coverage-table rows for these four areas. Any FAIL: STOP and report.
- [ ] **Step 3: Commit:** `git add docs/dev/qa/<run-log>`; `git diff --cached --stat`; `git commit -m "docs(qa): novice-readiness run, install rows"`.

### Task 8.4: Linux row (containers)

§6 row, verbatim:

| Area | Cases | Pass criterion |
|---|---|---|
| New: LINUX | `./setup.sh` on Debian or Ubuntu (a Docker `debian:12` and `ubuntu:24.04` container is acceptable) with and without `python3-venv`; `npm ci` on Node 18 | With: completes. Without: exits 1 with the `Install python3-venv` message and no partial `venv/` left; a re-run after installing it succeeds. Node 18: `npm ci` completes and leaves `package-lock.json` unchanged |

**Procedure (per image `debian:12` and `ubuntu:24.04`):** mount the E1 clone read-only at `/src`, copy it to `/work` inside the container, `apt-get update`, install `python3`, `nodejs`, `npm` (not `python3-venv`), run `./setup.sh`, read its exit code on its own line, `ls -d venv` (must be absent), keep the output. Then `apt-get install -y python3-venv`, run `./setup.sh` again. Record `node --version` and `python3 --version` from the container (the distribution Node must be 18 or later for the README's "distribution package" path; if it is not, record that as the finding). Node 18 `npm ci`: with a Node 18 in the container, `npm ci` then `git diff --exit-code -- package-lock.json` (exit 0 = unchanged). If Docker is unavailable: record BLOCKED and STOP; do not substitute.

- [ ] **Step 1:** run both images; one case block per image-and-state. **Step 2:** fill the coverage row. **Step 3: Commit:** `git add docs/dev/qa/<run-log>`; `git diff --cached --stat`; `git commit -m "docs(qa): novice-readiness run, linux rows"`.

### Task 8.5: grid, save, guard, theme and hidden-control rows (browser, E1)

§6 rows, verbatim:

| Area | Cases | Pass criterion |
|---|---|---|
| Grid | G1, G3, G8, G9 | New grid, discoverable black squares, no Heatmap toggle, save restored |
| New: SAVE-NAMED | Autosave a grid, then Save under a name, Open saved, Delete (the `Delete "<name>"?` confirm: Cancel keeps it, Delete removes it); fill storage until a write fails | Autosave keeps one entry per grid; the name prompt appears only on Save; Open asks the confirm; the quota text shows on an explicit Save |
| Grid guards | New: SR-PLACE (place a Search result across a black square and a theme-locked cell); new: CL-CLEAR (Verify flags cells, retype them, Clean) | Protected cells unchanged; no red cells after "Grid is clean" |
| New: CL-CLEAN-GUARD | Theme-lock a word, type an invalid word elsewhere, press Clean; once with Cancel, once with the confirm accepted | The confirm shows `Clean will remove N letters` with `N` equal to the non-theme-locked letters in the slots Clean flags (Clean blanks every cell of a flagged slot, so a crossing letter counts too); Cancel changes nothing, including `isError`; accepting removes those letters and every theme-locked letter is unchanged |
| Hidden | CL1, A-SBS, new: EXPORT-HIDE | Control absent; the Export panel shows no PDF or `.puz` option, no "Include clues" checkbox, and no PDF or `.puz` line under Format Information |
| New: TH2b | With suggestions showing, place a black square through an offered placement | The list refreshes; that placement is no longer offered; nothing stale can be applied |
| New: TH3 | Apply one placement, then Apply All Best Placements, with one word that conflicts | The summary counts only Apply All's own applies and names the skipped word with the server's reason |
| New: TH5 | Open the Theme panel at the desktop viewport and at 1024 px, the QA run's smallest desktop width (phone width is out of scope) | The top bar and Save are visible and clickable; Save succeeds with the panel open |
| New: SAVE-SIZE | Save a 21x21 grid, switch to 11x11, reload or Open saved | The saved grid restores at its own size, with its letters (S3) |
| New: SAVE-TABS | Open one saved grid in two tabs, edit and save in both | The second save forks `<name> (copy)`; neither tab's work is lost (S4) |

**Case definitions carried from the 2026-10-22 run:** G1 (new 15×15 from the Grid tool), G3 (place a black square), G8 (Heatmap toggle), G9 (Save, reload, grid persists), CL1 (Clues tool), A-SBS (Suggest Black Square in the Autofill panel), TH2b/TH3/TH5 as defined in that log; the new ids are defined by the rows above. TH5 and any layout measurement use the iframe method at 1440×900 and 1024×768. The quota step of SAVE-NAMED fills `localStorage` from the page until a write throws, then presses Save.

- [ ] **Step 1:** run each case in the browser at `http://127.0.0.1:5000` (E1 server running); one block per case id; screenshots/JSON in the evidence dir. **Step 2:** fill the coverage rows. Any FAIL: STOP and report. **Step 3: Commit:** `git add docs/dev/qa/<run-log>`; `git diff --cached --stat`; `git commit -m "docs(qa): novice-readiness run, grid and theme rows"`.

### Task 8.6: autofill rows (browser, E1)

§6 rows, verbatim:

| Area | Cases | Pass criterion |
|---|---|---|
| Autofill | A2, A3, A4 | Panel returns to idle by itself; every letter typed before Start is unchanged |
| New: AF-LOCK | Type letters, run Repair on the 11x11, cancel and let one run end | Typed letters intact in every progress sample and at the end |
| New: AF-BLOCK | Type a partial pattern no word fits (e.g. `QX` in the first two cells of a 3-letter slot, pattern `QX?`; a fully typed off-list word is case 2, not a block) | Run does not start; those cells red; message as §2.3. A valid word typed elsewhere in the grid stays black, not red (C1: only directly dead slots count) |
| New: AF-BLOCK-LEN | Tick a single list that has no word of some slot length in the grid (`awk '{print length($1)}' <list> \| sort -n \| uniq -c` shows which lengths it has); type a valid word elsewhere; Start | Run does not start; `The selected word lists have no words of length N.`; no cell red, including the typed word. Repeat on an empty grid: the same block (M2) |
| New: AF-DEFAULTS | Press Start with all panel defaults on the shipped 11x11 and 15x15 example grids, after typing a few letters | `Successfully filled`, **or** a partial result with every typed letter intact and the panel back at idle; the log records which |
| New: AF-SUB2 | Open a second progress stream on a running task and close it | The panel still reaches its terminal state |
| New: AF-REFILL | Run Repair, choose "Keep partial fill", type a letter, press Start again | The typed letter is intact; the run is not refused because of the autofilled letters; the lock list sent excludes them |
| New: AF-LOCKED-CROSS | Under Repair, type an off-list word and a listed word below the score floor, each crossed by open slots; Start | The run fills the crossing slots or reports them in `"stuck_cells"`; it never rejects every placement |
| New: AF-GATE | Start a run, then use every writer in §2.3's D1 list: typing, Backspace, black-square and theme-lock toggles, Search placement, theme apply, import, Verify, Clean, grid size, New grid, Open saved | None of them changes the grid; `Editing is paused while autofill runs.` shows |
| New: AF-OFFLIST | Type a word not in the lists (case 2), Start | The run proceeds; those cells show red; the toast `Typed words not in the selected word lists: <WORD>` shows |
| New: AF-NOLISTS | Untick every word list | Start is disabled with `Select at least one word list` (I5) |
| New: AF-VERIFY-STALE | Press Verify (and, separately, Clean), type a letter while the request is in flight | The typed letter survives the response; an open Clean confirm is dismissed by the typing (S1) |
| New: AF-SAVE-RUN | Start a run, wait for autosave, reload mid-run | The restored grid is the Start grid (S2) |
| New: PROV-SAME | Autofill a letter, retype the same letter, Start again | The letter is in the lock list (S5) |
| New: FULL-GRID | Fill every cell, open the Autofill panel | Start is disabled; the hint says to clear cells (P18) |

**Case definitions carried from the 2026-10-22 run:** A2 (panel defaults on the 11x11), A3 (Cancel on the 15x15), A4 (option "Repair (Recommended)"). Observing "typed letters intact in every progress sample" (AF-LOCK) and "the lock list sent" (AF-REFILL) uses the browser's network log for `POST /api/fill/with-progress` (`locked_cells` in the request body) and the progress stream; AF-SUB2 opens the second stream with `curl -N http://127.0.0.1:5000/api/progress/<task_id>` and closes it. "Every letter typed before Start is unchanged" is compared as the grid's cell letters read from the DOM before Start and at the terminal state, pasted into the log.

- [ ] **Step 1:** run each case; one block per case id; evidence in the evidence dir. **Step 2:** fill the coverage rows. Any FAIL: STOP and report. **Step 3: Commit:** `git add docs/dev/qa/<run-log>`; `git diff --cached --stat`; `git commit -m "docs(qa): novice-readiness run, autofill rows"`.

### Task 8.7: lists and CLI rows, run close

§6 row, verbatim:

| Area | Cases | Pass criterion |
|---|---|---|
| Lists, CLI | L11, SR4, CLI-normalize | Per §4 |

**Case definitions:** L11 = upload fixture F7 (non-ASCII) through Lists → "Upload Wordlist", read the dry-run preview and the stored list (`GET /api/wordlists/custom/<name>`): per §4 the accented words appear folded (`CAFÉ`→`CAFE`, `NAÏVE`→`NAIVE`, `ÜBER`→`UBER`) and `ß`/`Æ`/`Ø` words are skipped with `not letters only`; SR4 = untick every list, Search tab: the Search button is disabled with `Select at least one word list`; CLI-normalize = `$SB/e1.sh "cd <clone> && python -m cli.src.cli normalize 'Hello, World!' --json-output"` → `normalized` `HELLOWORLD`.

- [ ] **Step 1:** run the three cases; blocks in the run log. **Step 2: Coverage check, no typed values.** Extract the spec's Area column and confirm each appears in the run log's coverage table:

```bash
SPEC=docs/superpowers/specs/2026-10-23-novice-readiness-design.md
RUN=docs/dev/qa/<YYYY-MM-DD>-novice-readiness-run.md
sed -n '/^## 6\. Acceptance/,/^## 7\./p' "$SPEC" | awk -F'|' '/^\| /{gsub(/^ +| +$/,"",$2); print $2}' | grep -v -e '^Area$' -e '^-' > "$SB/areas.txt"
wc -l < "$SB/areas.txt"
while IFS= read -r a; do grep -qF -- "$a" "$RUN" || echo "MISSING: $a"; done < "$SB/areas.txt"
```
Positive control: `areas.txt` is non-empty and the loop prints nothing only if every area is present; run it once against a copy of the log with one row deleted and confirm it prints `MISSING`.
- [ ] **Step 3: Close the log.** Add the summary the old log's `summary.txt` served (verdict per area, pasted from the coverage table), and record every FAIL/BLOCKED with its owning phase.
- [ ] **Step 4: Doc guard:** `bash scripts/docs-check.sh`, read the result on its own line.
- [ ] **Step 5: Commit:** `git add docs/dev/qa/<run-log>`; `git diff --cached --stat`; `git commit -m "docs(qa): novice-readiness acceptance run, lists, CLI and close"`.
