# M1 Phase 3 — Pause → Edit → Resume Restore — Implementation Plan (Tasks 13–19)

> **For agentic workers:** REQUIRED SUB-SKILL — use **superpowers:subagent-driven-development** (recommended) or **superpowers:executing-plans** to implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **STATUS: READY — verified 2026-07-14 against HEAD `9e124b2`.** Every load-bearing citation re-verified against the real code (files drifted since the parent plan: `cli.py` grew from `105-614` → 1640 lines). Authoring → per-section adversarial hardening → cross-section consistency pass → advisor integration all applied. Expands **Phase 3** (Tasks 13–19) of `docs/superpowers/plans/2026-07-12-m1-constructors-bench.md:530-665`.
>
> **Convention (Arthur's):** this plan carries **decisions, contracts, signatures, and TDD assertion checklists — the executing agent writes all full code bodies.** Short snippets appear only where a literal is load-bearing. Concrete test assertions are given. If a step seems underspecified, the binding references are, in order: the task's Interfaces block, the parent plan's **Cross-task literals** (`:81-92`) and **Authoritative endpoint contracts** (`:35-73`), and the real source files cited by `file:line`.

**Branch:** `feature/m1-constructors-bench` · **HEAD:** `9e124b2` · **Repo:** `/Users/apa/projects/crossword-helper`

---

## Goal

Restore a working **pause → edit → resume** autofill loop end-to-end: the CLI `fill` command learns to pause (save solver state) and resume (`--task-id`/`--state-dir`/`--pause-flag-dir`/`--resume`), the Flask backend threads those onto every spawned fill and closes the paused SSE stream cleanly, and the frontend gains a confirmed pausing sub-state, two-step resume, saved-state discovery, live edit preview, and 409-conflict recovery — with **zero new endpoint surface** and honest, algorithm-aware pause semantics.

## Architecture

The CLI stays the single source of truth. **Classic CSP (`trie`/`regex`)** pauses at exact position via the existing `CSPState` machinery (real `domains`); **`repair`/`hybrid`/`beam`** graceful-stop, serializing the current best grid as a *degenerate* `CSPState` (`domains={}`) through the same writer — one UI, honest labels. The backend gives its routes, the CLI it spawns, and the pause route a **single source for both the state dir and the pause-flag dir** (`backend/core/state_paths.py`), killing the split-default severance that keeps pause a no-op today. The frontend extends Task 11's `useAutofillMachine` (state-machine amendments to spec 06 §1) rather than rewriting it.

## Tech Stack

Python 3.9+ / Click CLI (`cli/src/`), Flask 3 (`backend/`), pytest (+ `@pytest.mark.slow` for real-subprocess E2E). React 18 + Vite 5 frontend, vitest + `@testing-library/react` (`renderHook`/`act`/fake timers + the global `MockEventSource` harness).

---

## Phase 3 preamble (binding — from parent `:530-536`)

- **Canonical resume path:** the web path is `fill --resume <state-file> --task-id <id>` matching `CLIAdapter.fill_with_resume` (`cli_adapter.py:403`). The standalone `crossword resume` CLI command is untouched in M1 (CLI-only/legacy); web code never calls it.
- **Uniform pause semantics:** `trie`/`regex` (classic CSP) = **exact-position** resume (existing `CSPState`); `repair`/`hybrid`/`beam` = **graceful-stop** (serialize grid + locks as a degenerate `CSPState` with empty `domains`; resume seeds a fresh fill from the merged grid). One UI, honest labels.
- **Algorithm flag values** (verified `cli.py:118` — there is **no** `csp` value): `regex`/`trie` = classic CSP `Autofill`; `beam`; `repair`; `hybrid` = beam+repair. **Web default: `repair`.**

## Phase-3 Cross-task literals (inlined — the executing agent needs these without cross-referencing)

These are the parent plan's Cross-task literals (`:81-92`), reproduced for the load-bearing subset. **State them ONCE here; tasks reference, never restate.**

- **Pause flag file:** `<pause_flag_dir>/crossword_pause_<task_id>.flag` (`pause_controller.py:40`; dir mkdir'd parents=True).
- **State file:** `<state_dir>/<task_id>.json.gz` (gzipped JSON; `state_manager.py:164-167`).
- **Serialized state envelope** (`state_manager.py:89-102`): top-level `{version, algorithm:"csp"|"beam", task_id, timestamp, metadata, state_data}`. `algorithm` here is the **state FORMAT** — always `"csp"` for anything `save_csp_state` writes, **independent of the `--algorithm` flag** (`load_csp_state` *validates* `algorithm=="csp"`, `:210-211` — so the run's flag must ride in `metadata`, never this field). `state_data = asdict(CSPState)` and contains `domains`. `metadata` is caller-supplied.
- **Degenerate `CSPState` — 11 required fields, no defaults** (`state_manager.py:18-51`): `grid_dict, domains, constraints, used_words, slot_id_map, slot_list, slots_sorted, current_slot_index, iteration_count, locked_slots, timestamp` (ISO string — omitting it is a `TypeError` at construction). Optional: `random_seed`, `letter_frequency_table`. `save_csp_state` (kwarg `csp_state`) does asdict+json+gzip with **no validation** — empty `domains={}` saves fine.
- **Paused stdout protocol** (new, Task 13): `{"paused": true, "task_id": …, "slots_filled": n, "total_slots": m}`, **exit code 0**.
- **Fill success stdout keys** (`cli.py:564-573`): `success, grid, fill_percentage, iterations, slots_filled, total_slots, problematic_slots_count, time_elapsed`. The empty-grid early return emits the same keys plus `message`.
- **Web shared dirs** (new, Task 15): `backend/core/state_paths.py` exports `STATE_DIR` (= `backend/data/autofill_states`) and `PAUSE_FLAG_DIR` (= `/tmp`); backend routes **and** every CLI invocation the backend spawns must pass both explicitly — split defaults are how the current severance happened.

## Global Constraints (Phase-3 subset — from parent `:18-31`)

- **CLI is the single source of truth. The GUI never solves.** No client-side fill/candidate/validity computation (Client-side computation policy, parent `:96-112`).
- **All API URLs/payload shapes live only in `src/api/client.js`** (Task 1 pre-commit guard enforces). Frontend tasks import `{ api }` and call `api.pauseFill(...)` etc. — there are **no** individual named exports.
- **Error surfacing — four surfaces only:** inline-below-field (validator 400s), red toast (request/timeout/network), orange autofill error card (SSE `status:"error"`), red health dot. No `alert()`/modals/console-only.
- **Grid encodings** (client owns all conversions): frontend canonical `{letter, isBlack, …}`; **CLI strings** on every backend call (`"#"/"."/UPPER`); `numbering` keys `"(r,c)"`.
- **Testing:** `pytest backend/tests/ cli/tests/`; real-subprocess E2E gets `@pytest.mark.slow`. `npx vitest run` for frontend. Run the relevant suite before every commit. **Do not push. Do not `--no-verify`.**

---

## ⚠️ Scope decision — flag for Arthur (resolve at plan review)

**The parent plan's Task 13 under-scopes the repair/beam/hybrid pause path.** The parent title + commit name "all web algorithms," but recon found the pause machinery exists *only* in the classic `Autofill` class. `IterativeRepair`, `HybridAutofill`, and `BeamSearchAutofill` **do not accept `pause_controller`/`task_id`** today (their ctors/`fill()` signatures omit them), and `BeamSearchAutofill`'s wrapper drops `pause_controller` from its `super().__init__`, making the orchestrator's existing pause polling **unreachable** via hybrid and the CLI `beam` path. Since the **web default is `repair`**, a fresh `/api/fill/with-progress` fill **cannot be paused at all** at HEAD.

**Resolution taken in this plan (Task 13 DD4/DD5, flagged there):** `csp` + `repair` are the fully-tested core; `beam` + `hybrid` are reached with the **smallest honest edit** — forward `pause_controller` through the two wrappers (`beam_search_autofill.py`, `hybrid_autofill.py`) so the orchestrator's *existing* polling fires, and let the CLI own the single degenerate save. This adds **2 files beyond the parent's Files list**. `--adaptive` and `--attempts>1` pause are made **crash-safe no-ops** and scoped out (web always fills `attempts=1`, non-adaptive).

**If Arthur prefers a tighter M1 cut:** scope pause/resume to `trie`/`regex` (classic CSP) only — that path needs no wrapper edits, the E2E gate (Task 19) already exercises exactly it, and repair/beam graceful-stop lands post-M1. This trims Task 13 DD4/DD5 and the beam/hybrid tests (13 Test C/D). **Decision needed before executing Task 13.**

---

## Cross-section reconciliation notes (from the consistency pass — read before executing the affected tasks)

The 7 sections were drafted and hardened **in isolation**; a dedicated cross-section pass then checked section-to-section agreement. These notes reconcile the seams it found. They are **authoritative over the individual section bodies** where they conflict.

1. **[lock channel · T13↔T14]** T14 DD4's `metadata["theme_entries"]` lock channel is **unsatisfiable by construction** — `edit_merger.merge_edits` carries locks only via `CSPState.locked_slots` (`edit_merger.py:84-86,124`) and neither T13's degenerate save nor the resume route writes `theme_entries` to metadata; a degenerate state's `slot_list=[]` also means no lock can map onto a slot. The **exact-position CSP path already preserves theme+user locks** through `locked_slots`. **Action:** downgrade T14 DD4's "binding dependency on Task 13" to *best-effort / currently degrades*; **accept M1 grid-structure-only degradation** for the degenerate repair/beam re-seed; **do NOT add `theme_entries` to T13's save** (it would change nothing).
2. **[important · T16↔T17↔T18]** The `useAutofillMachine` return surface is **FLAT** (per Task 16's Produces block + the `useSaveMachine`/`useHealth` sibling convention): read `machine.taskId` / `.progress` / `.conflict` and `result.current.taskId` — **not** `machine.context.*`. Tasks 17/18 that reference `context.taskId`/`context.conflict` must use the flat fields. Also carry Task 16's unresolved **`state`-vs-`status` field-name caveat** (PROVISIONAL on Task 11) into T17/T18. *(If Task 11 shipped a context-nested machine, all three sections move together — re-verify at execution.)*
3. **[important · T16↔T18]** `conflict` is the **object** `{ slots, details } | null` (Task 18's shape wins). Task 16 stores `conflict = { slots: [], details: err.details }` (Task 18's `parseConflictSlots` fills `slots`), and **Task 16 Step-1 test 6 must assert `conflict.details === '…'` (not `conflict === '<string>'`)**. Task 18 owns `useAutofillMachine.test.jsx` and updates test 6 when it lands.
4. **[minor · T18]** Expose Task 18's cancel-honesty and discard as **action methods** (`cancel()` extended in place, new `discard()`), consistent with Task 16's method API; the 409 handling stays inside the existing `resume()` method. The "RESUME_CONFLICT/DISCARD/CANCEL events" phrasing is pseudocode, not a reducer contract.
5. **[minor · T14↔T15]** Canonical `PAUSE_FLAG_DIR` is **`/tmp`** (Task 15 / `state_paths.py`). Task 14's `cli_adapter` placeholder `backend/data/autofill_pause_flags` is provisional and superseded when Task 15 deletes the local constant and imports from `state_paths` (the only consumer is test-only and value-agnostic).
6. **[minor · T14 DD2]** On the resume argv, `--task-id` is the **fresh SSE channel id (T2)** from `create_progress_tracker()`, distinct from `resume_<8hex>` (R1), which appears only as the `--resume` state-file basename. T14 DD2's "backend passes `resume_<8hex>`" as `--task-id` is loose wording — the load reads the `--resume` path's basename; `--task-id` governs the resumed run's re-pause.
7. **[minor · T13↔T14]** Task 13 populates `result.paused` via the **`FillResult` constructor** (`paused=was_paused`) and gates on `result.paused`; there is **no `self.was_paused` attribute**. Task 14's dependency is satisfied — its "`self.was_paused`" / "`getattr(autofill,'was_paused')`" wording is stale relative to Task 13 DD2.
8. **[minor · T16↔T17]** `stateInfo` is the `getFillState` body; Task 17's restore may populate the `{slots_filled, total_slots, grid_size, algorithm}` subset **provided the shared paused UI never reads `stateInfo.grid_preview`/`iteration_count`** (F13 drives off `editSummary`, so it currently doesn't). If it ever does, restore must fetch the full body.
9. **[minor · executor trap, out-of-plan-scope]** The `/api/fill/resume` docstring (`pause_resume_routes.py:176`) shows a stale nested `[["R"],["A"]]` example for `edited_grid`; the actual contract is **CLI strings** (`string[][]` of `"#"/"."/UPPER`), as Tasks 16/17/19 correctly use. Don't copy the docstring.

---

## Execution order & dependencies

**Two halves with different readiness:**

| Tasks | Nature | Ready when |
|---|---|---|
| **13, 14, 15, 19** (CLI + backend spine + E2E gate) | Touch **existing** code; every citation verified against HEAD now | **Now** — independent of Phase 2 |
| **16, 17, 18** (frontend) | Extend `useAutofillMachine.js` / `AutofillPanel.jsx` | After **Task 11** (Phase 2) creates those files — internals flagged `(PROVISIONAL)` |

**Sequential dependencies inside the spine:** Task 13 (adds the CLI options + pause) → Task 14 (adds `--resume`, reuses 13's paused-exit; **shifts `cli.py` line numbers** — locate seams by shown code, not absolute line) → Task 15 (backend threads the argv + closes the paused SSE stream) → Task 19 (real-subprocess gate — **legitimately RED until 13–15 land**). Task 15's always-on `--task-id/--state-dir/--pause-flag-dir` mean any real-CLI fill test hard-requires Task 13/14's options; landing 15 before 14 makes those fills `Click exit 2` **by design**.

**Recommendation:** build the spine (**13 → 14 → 15 → 19**) first — it is the **highest-risk part of all of M1** (real subprocess state serialization + IPC + the two-step resume), it is buildable and fully verifiable today, and Task 19 proves it end-to-end with **zero frontend**. Then land the frontend (**16 → 17 → 18**) once Task 11 exists, re-verifying the `(PROVISIONAL)` citations against Task 11's actual output. Frontend order is strict: **16 defines the machine surface**, 17/18 consume it (see reconciliation notes 2–4, 8).

---


## Task 13 — CLI: `fill --task-id/--state-dir/--pause-flag-dir` + pause hooks (csp + repair + beam + hybrid)

> Expands Task 13 of `docs/superpowers/plans/2026-07-12-m1-constructors-bench.md:538-562`. Phase-3 preamble (`:530-536`), **Cross-task literals** (`:81-92`), **Authoritative endpoint contracts** (`:35-73`), **Global Constraints** (`:18-31`), **Client-side computation policy** (`:96-112`), **State-machine amendments** (`:115-123`) are BINDING — referenced, never restated.
> **Convention:** signatures / contracts / short load-bearing snippets only — the implementer writes full bodies. Test steps carry concrete assertions.
> **Branch:** `feature/m1-constructors-bench` · verified vs HEAD `9e124b2`.
> **Scope decision (flagged):** parent's title/commit names all web algorithms (`:538`, `:562`) yet its Files list (`:541`) omits the beam/hybrid wrappers while its interface (`:549`) mandates beam graceful-stop. Resolution: csp + repair are the fully-tested core; beam + hybrid are reached with the smallest honest edit (forward `pause_controller` through the wrappers; the CLI owns one degenerate save so `orchestrator.py`'s native beam writer stays unused — the parent's "native beam save stays unused"). Deviation from the Files list is flagged in Scope & deviations.

### Files
- Modify: `cli/src/cli.py` — fill command: option block (`:104-185`), signature (`:186-203`), instance dispatch (`:350-396`), fill-call dispatch (`:462-506`), and a NEW paused branch inserted after the fill call (before the cleanup pass at `:508` and the completion block at `:533`).
- Modify: `cli/src/fill/autofill.py` — populate the EXISTING `FillResult.paused`/`state_path` fields (`:36-37`) from the two `except PausedException` blocks (`:193-195`, `:247-248`) into the returns (`:203-211`, `:256-263`); persist `self._pause_state_path` in `_handle_pause` (`:1140-1182`, fixes the local-only `state_path` at `:1173`).
- Modify: `cli/src/fill/iterative_repair.py` — `__init__` (`:93-104`) gains optional `pause_controller`; two `should_pause()` hooks at the restart loop (`:215`) and the conflict-repair loop (`:418`); paused flag threaded into the `return best_result` at `:266`.
- Modify: `cli/src/fill/beam_search_autofill.py` — wrapper `__init__` (signature `:31-44`) accepts + forwards `pause_controller` into `super().__init__` (`:68-80`) so the orchestrator's existing pause polling becomes reachable.
- Modify: `cli/src/fill/hybrid_autofill.py` — `__init__` (`:32-44`) accepts + forwards `pause_controller` to BOTH phases (`:122-131`, `:152-162`); `fill` (`:80`) short-circuits to a paused return on a Phase-1 OR Phase-2 pause.
- **No changes** (verified): `pause_controller.py` (`PauseController(task_id, pause_dir=None)` `:24`, flag `:40`, `PausedException` `:121`), `state_manager.py` (`StateManager(storage_dir=None)` `:118-129`, `save_csp_state` `:131`), `orchestrator.py` (already polls `should_pause()` at `:300-301`/`:863-864`, saves via native writer at `:304`, and sets `result.paused=True` + returns at `:306-309`/`:869-872`; its native `_save_state_and_pause` is deliberately left to no-op — see DD5), `autofill.py.__init__` (`pause_controller` `:59`, `state_manager` `:60`) and `Autofill.fill(task_id=…)` (`:122`).
- Test: `cli/tests/test_fill_pause_resume.py` (create).

### Interfaces
Produces — three new Click options + one param on `fill(...)`:
```
--task-id TEXT          # enables pause polling + state saving; None → pause path fully inert (today's behavior)
--state-dir PATH        # StateManager(storage_dir=…); ABSENT → StateManager default /tmp/crossword_states (state_manager.py:126)
--pause-flag-dir PATH   # PauseController(pause_dir=…); ABSENT → PauseController default /tmp (pause_controller.py:34-35)
def fill(..., task_id, state_dir, pause_flag_dir):   # appended to the 16-arg signature at :186-203
```
Consumes (all already present, no signature changes): `PauseController(task_id, pause_dir)` · `StateManager(storage_dir)` · `Autofill(..., pause_controller=, state_manager=)` + `Autofill.fill(task_id=)` · `IterativeRepair.fill(timeout)` → `FillResult` · `BeamSearchOrchestrator` pause polling · `StateManager.save_csp_state(task_id, csp_state=, metadata=, compress=True)` → returns the state `Path` · `CSPState(...)` (11 required fields, Cross-task literal `:88`). **Not consumable with `task_id`:** `AdaptiveAutofill.fill(self, timeout)` (adaptive_autofill.py:143) — signature has NO `task_id`; `--adaptive` therefore excludes the pause path (DD3, Scope 4).

Produces — pause outcome (uniform across engines): a `FillResult` with `.paused == True` and `.grid` = current/best partial grid. The fill command, on `result.paused`, writes the state file (CSP already did; graceful-stop engines saved CLI-side — DD6), emits the **paused stdout protocol** (Cross-task literal `:90`) with **exit 0**, and returns WITHOUT running cleanup/completion. Every backend-spawned fill passes both `--state-dir` and `--pause-flag-dir` explicitly (Task 15 / `state_paths.py`, Cross-task literal `:91`) — the split-default divergence between `StateManager` (`/tmp/crossword_states`) and `PauseController` (`/tmp`) is why the web must never leave them to defaults.

**Imports (load-bearing):** `cli.py` imports none of `PauseController`, `StateManager`, `CSPState`, or `datetime` at module level. Follow the sibling `pause`/`resume`/`list-states` commands, which import locally inside the command body (`PauseController` at `:1202`, `StateManager` at `:1275`/`:1453`). DD1 needs `PauseController`/`StateManager`; DD6 needs `CSPState` (`from .fill.state_manager import CSPState`) and `from datetime import datetime`.

### DD1 — Option surface + one PauseController/StateManager, wired only when `--task-id` present and NOT `--adaptive`
Add the three `@click.option`s and the three params (there is NO `--task-id` today — `fill` at `:104-203`; the sibling `pause`/`resume`/`list-states` commands take `task_id`, `fill` does not). Gate ALL pause wiring on `task_id and not adaptive`, and guard `Path(...)` against the `None` that Click passes when an option is omitted (options carry no `default=`):
```python
pause_controller = state_manager = None
if task_id and not adaptive:               # --adaptive: pause is out of scope → crash-safe no-op (DD3, Scope 4)
    pause_controller = PauseController(task_id, pause_dir=Path(pause_flag_dir) if pause_flag_dir else None)
    state_manager    = StateManager(storage_dir=Path(state_dir) if state_dir else None)
```
The `if x else None` guards preserve the documented "absent → underlying default" semantics AND avoid `Path(None)` → `TypeError` when `--task-id` is given without the dir options. Without `--task-id` (or with `--adaptive`), `pause_controller` stays `None` → every hook below is a no-op and behavior is byte-identical to today (backward-compatible; existing `fill` callers and the 907-test default suite unaffected). Building `PauseController` and `StateManager` from the SAME two dir args in one place is the local guarantee that flag-dir and state-dir agree when both are passed — Global Constraint / Cross-task literal `:91`.

### DD2 — Uniform `result.paused` contract (root-fix the silent-failure hazard; supersede the parent's `autofill.was_paused` instance attr)
The parent (`:547`) proposed `self.was_paused` checked by the command. Reasoned deviation: `FillResult` ALREADY declares `paused: bool = False` (`:36`) and `state_path` (`:37`) — they are simply never populated (the exact silent-failure: `autofill.py:193-195`/`:247-248` set only a local `success=False`, so a paused run is indistinguishable from an unsolvable one — `success=False, paused=False`). Fix it at the source and give the command ONE branch (`if result.paused:`) for csp/repair/beam/hybrid, instead of a per-engine attribute.

CSP (`autofill.py`), both blocks — thread a local flag into the existing return, and persist the state path (the `state_path` computed at `:1173` is local-only and lost when `_handle_pause` returns — the [gotcha] hazard):
```python
# _handle_pause (:1173): after `state_path = self.state_manager.save_csp_state(...)` →
self._pause_state_path = str(state_path)          # persist for the FillResult
# fill()  except PausedException (:193-195):  was_paused = True
# _resume_fill() except PausedException (:247-248): was_paused = True
# both returns (:203-211, :256-263):
FillResult(..., paused=was_paused, state_path=getattr(self, "_pause_state_path", None))
```
The `except` still catches only `TimeoutError`/`PausedException`; `_handle_pause`'s `ValueError("task_id required…")` (`:1152-1153`) is NOT caught — DD3 keeps task_id present whenever `pause_controller` is, so it never fires. Repair sets `.paused` in DD4; beam/hybrid already/forward in DD5. Net: `result.paused` is authoritative for all algorithms.

### DD3 — CSP wiring at the positional construction; single-attempt, non-adaptive call sites only
`cli.py:396` builds classic `Autofill` POSITIONALLY (`Autofill(grid, word_list, None, timeout, min_score, algorithm, progress)`; the 3rd positional `None` is `pattern_matcher`). Append the two injections as KEYWORD args, gated so multi-attempt classic runs never receive a live `pause_controller` (adaptive is already nulled in DD1):
```python
_pc = pause_controller if attempts == 1 else None
_sm = state_manager  if attempts == 1 else None
autofill = Autofill(grid, word_list, None, timeout, min_score, algorithm, progress,
                    pause_controller=_pc, state_manager=_sm)
```
Thread `task_id` into the single-attempt classic call ONLY, and ONLY when `not adaptive` — at `:499` and `:502`:
```python
# :499 / :502 — AdaptiveAutofill.fill(timeout) (adaptive_autofill.py:143) has NO task_id param:
result = autofill.fill(task_id=task_id) if not adaptive else autofill.fill()
```
Rationale — the two crash gates:
- **`attempts>1`**: `fill_with_restarts` (`:488`/`:491`) internally calls `self.fill()` with NO task_id (autofill.py:304). A live `pause_controller` + a pause would reach `_handle_pause` with `task_id=None` → uncaught `ValueError` (DD2). The `attempts == 1` gate keeps `pause_controller` off that path. **Pause during `--attempts>1` is out of scope** (web always fills with `attempts=1`).
- **`--adaptive`**: at `:421` `autofill` is rebound to `AdaptiveAutofill`, whose `fill(timeout)` rejects `task_id` (TypeError) and, if given a live `pause_controller` on the wrapped base, would raise the same `ValueError` on pause. DD1 already withholds the controllers under `--adaptive`; the `not adaptive` guard on the `task_id=` kwarg prevents the TypeError. **Pause under `--adaptive` is out of scope.**

The empty-grid early-return (`:431-451`) precedes any engine and needs no wiring (its hardcoded key block mirrors the success schema — if that schema changes, update both; pause cannot occur there).

### DD4 — Repair: two `should_pause()` hooks, one flag, reuse the existing best-grid restore
`IterativeRepair.__init__` (`:93-104`) gains `pause_controller=None` (stored) + `self._pause_requested = False`. Detection is a file-existence check (`should_pause()`), NEVER an elapsed-time comparison — the timers at `:216-218`/`:420-421` are independent timeout breaks and stay. Hook #2 (`:418`) lives 3 levels below `fill()` (`fill:248 → _region_fill_attempt:343 → _repair_invalid_words:401`), and `_repair_invalid_words` returns `None`, so a bare `break` there only exits the `while` — the restart loop would start the next restart (the [silent-failure] hazard). Propagate via the flag, checked at hook #1 so the EXISTING best-grid restore/return (`:263-266`) runs unchanged:
```python
# hook #1 — restart loop top (:215), beside the elapsed break:
if self._pause_requested or (self.pause_controller and self.pause_controller.should_pause()):
    self._pause_requested = True
    break
# hook #2 — conflict-repair loop top (:418), beside the per-iteration timeout:
if self.pause_controller and self.pause_controller.should_pause():
    self._pause_requested = True
    break
# after the restart loop, before `return best_result` (:266):
if self._pause_requested and best_result is not None:
    best_result.paused = True
```
`best_grid` (updated at `:256-258`, restored at `:263-264`) is the partial grid handed back — matches the graceful-stop semantics of the Phase-3 preamble (`:536`). (In the realistic flow the flag is touched mid-run, so hook #2 fires inside an attempt and `best_result` is always populated by the time hook #1 breaks.)

### DD5 — Beam + hybrid: forward `pause_controller`, let the native beam writer stay unused
This is the delta beyond the parent's Files list (`:541` names only cli.py/iterative_repair.py/autofill.py) — mandatory because the parent's own interface (`:549`) requires beam graceful-stop and the wrappers currently DROP pause. `BeamSearchAutofill.__init__` (`:31-80`) omits `pause_controller` from its `super().__init__` (`:68-80`), so the orchestrator's polling (`:300-301`) is unreachable via the CLI `beam` path and via hybrid. Extend the wrapper to accept + forward `pause_controller` (default `None`). Do NOT forward `task_id`: the orchestrator's native `_save_state_and_pause` no-ops without it (`:1042-1044`) yet the code after it (best-partial + `result.paused=True` + return at `:306-309`) still runs — so beam stops and returns a paused partial while its beam-format writer stays dormant. This literally realizes the parent's "its native beam-state save stays unused by web" and keeps `orchestrator.py` untouched; the CLI owns the one canonical degenerate save (DD6).
```python
# BeamSearchAutofill.__init__ — add pause_controller=None; pass to super().__init__(..., pause_controller=pause_controller)
# HybridAutofill.__init__ (:32-44) — add pause_controller=None; forward to BOTH:
#   Phase-1 BeamSearchAutofill(..., pause_controller=pause_controller)   (:122-131)
#   Phase-2 IterativeRepair(...,   pause_controller=pause_controller)    (:152-162)
# HybridAutofill.fill:
#   after Phase-1 beam_result (before the success early-return at :136-142):
if beam_result.paused:
    return beam_result            # Phase-1 pause: don't proceed to repair
#   after Phase-2 repair_result (before the beam-vs-repair best-of comparison at :166-190):
if repair_result.paused:
    return repair_result          # Phase-2 pause: the slot-count compare (:175/:183) must not mask it
```
Construct all three engines at the dispatch (`:352`/`:364`/`:375`) with `pause_controller=pause_controller` (which is `None` under `--adaptive` or no `--task-id`, per DD1). Adaptive wrap (`:398-427`) + pause is out of scope (Scope 4).

### DD6 — One CLI-side degenerate save + the paused exit protocol (single site for repair/beam/hybrid)
Insert a paused branch AFTER the fill-call dispatch (`:506`) and BEFORE the cleanup pass (`:508`) and completion block (`:533`) — so cleanup/`progress.update(...,"complete")` never run on pause (a spurious SSE `complete` is exactly what Task 15 must avoid). `result` at this point is always a `FillResult` (classic, `AdaptiveAutofill` — which returns a `FillResult` despite its `-> Dict` annotation, adaptive_autofill.py:172 — or repair/beam/hybrid), so `result.paused` is safe.

Contract of the branch (`if task_id and result.paused:`):
1. **Degenerate save (repair/beam/hybrid only — `algorithm not in ("regex","trie")`):** CSP already persisted its real `CSPState` in `_handle_pause`. For the graceful-stop engines the CLI builds the **degenerate CSPState** (Cross-task literal `:88` — 11 required fields) from `result.grid` and saves it through the SAME `save_csp_state` writer, capturing its returned `Path`. Load-bearing field values and metadata placement:
```python
degenerate = CSPState(
    grid_dict=result.grid.to_dict(),          # current/best partial (to_dict does NOT persist locks — grid.py:257-276)
    domains={}, constraints={}, used_words=[], slot_id_map={},
    slot_list=[], slots_sorted=[], current_slot_index=0, iteration_count=0,
    locked_slots=[],                           # see rationale
    timestamp=datetime.now().isoformat(),      # REQUIRED — omitting is a TypeError
)
state_path = state_manager.save_csp_state(
    task_id=task_id, csp_state=degenerate,
    metadata={"algorithm": algorithm,          # flag → metadata, NOT the envelope tag (format-collision)
              "slots_filled": result.slots_filled, "total_slots": result.total_slots,
              "grid_size": [grid.size, grid.size]},
    compress=True,
)
# stderr 'paused' parity with CSP's _handle_pause, using the RETURNED path (not a reconstructed one):
if progress:
    progress.update(<pct>, f"Paused: {result.slots_filled}/{result.total_slots} slots filled",
                    "paused", {"state_path": str(state_path), "grid": result.grid.to_dict()["grid"]})
```
2. **Paused stdout protocol + exit 0 (all engines):** emit Cross-task literal `:90` and `return` (skipping cleanup/completion):
```python
if json_output:
    click.echo(json.dumps({"paused": True, "task_id": task_id,
                           "slots_filled": result.slots_filled, "total_slots": result.total_slots}))
else:
    click.echo(click.style("⏸ Paused — solver state saved", fg="cyan"))
return
```

Rationale — envelope tag: `save_csp_state` hardcodes top-level `algorithm="csp"` (`:153`); `load_csp_state` VALIDATES it `=="csp"` (`:210-211`, a beam tag would raise), so the run's flag MUST ride in the free-form `metadata` (format-collision hazard; `get_state_info` surfaces `metadata`'s `slots_filled`/`total_slots`/`grid_size`). Rationale — `locked_slots=[]`: `Grid.to_dict` does not persist `locked_cells` (verified `grid.py:257-276`) and the preamble (`:536`) re-locks user edits + theme entries from the MERGED grid on resume (Task 14/16), so the degenerate state's `locked_slots` is not the lock source of truth; `[]` is a legal, round-tripping value. This is a bounded deviation from the parent's literal "`locked_slots` = theme ∪ user-filled" (`:549`), justified because that value would be unconsumed. `save_csp_state` does zero validation, so `domains={}` serializes fine (Cross-task literal `:88`). CSP's own `_handle_pause` metadata is pre-existing and left untouched.

### Scope & deviations (flagged, like the U5 self-review)
1. Added `beam_search_autofill.py` + `hybrid_autofill.py` to the change set beyond the parent's Files list — required to honor the parent interface's beam mandate (`:549`); the wrapper edit is the minimum (forward one param).
2. `FillResult.paused`/`state_path` populated directly (DD2) instead of a new `autofill.was_paused` attr (`:547`) — root-fixes the silent-failure hazard and yields a uniform `result.paused` branch.
3. `orchestrator.py` NOT modified — its native beam writer is left to no-op by withholding `task_id` (DD5); the CLI owns the single degenerate save (DD6).
4. Out of scope (follow-ups, not regressions), all made **crash-safe** by gating pause wiring to `attempts == 1 and not adaptive` (DD1/DD3): pause under `--attempts>1` (`fill_with_restarts` calls `fill()` without `task_id`, autofill.py:304); pause under `--adaptive` (`AdaptiveAutofill.fill(timeout)` has no `task_id` param, adaptive_autofill.py:143 — would `TypeError`/`ValueError`); native beam exact-state resume (M1 out-of-scope, `:31`).

### TDD Steps
- [ ] **Step 1 — write failing tests** in `cli/tests/test_fill_pause_resume.py`. A subprocess helper `_run_fill_until_paused(tmp_path, algorithm, task_id, size=15, timeout=120)`: writes a blank `size×size` grid JSON (all `"."`) to `tmp_path`; spawns `python -m cli.src.cli fill <grid> -w data/wordlists/comprehensive.txt --algorithm <algorithm> -t <timeout> --json-output --task-id <task_id> --state-dir <tmp_path/state> --pause-flag-dir <tmp_path/flags>` via `subprocess.Popen`; `time.sleep(3)`; touches `<tmp_path/flags>/crossword_pause_<task_id>.flag` (Cross-task literal `:85`); `stdout, _ = proc.communicate(timeout=60)`; returns `(proc, stdout, tmp_path/"state")`. Mark B/C/D `@pytest.mark.slow` (Global Constraint `:29`).

  *Test A — options accepted (fast, no pause):* run `fill` on a blank **5×5** with `--allow-nonstandard --json-output -t 15 --algorithm trie` and all three new options into `tmp_path`; `communicate(timeout=45)`. Assert `proc.returncode == 0` (proves Click accepted the options and the run did not crash) and `json.loads(stdout)["success"] is True` (a blank 5×5 fills trivially).

  *Test B — CSP pause saves a real CSPState:* `_run_fill_until_paused(tmp_path, "trie", "tB")`. Assert: `proc.returncode == 0`; `out = json.loads(stdout)`; `out["paused"] is True and out["task_id"] == "tB"`; `isinstance(out["slots_filled"], int)`; `(state_dir / "tB.json.gz").exists()`; unzip via `gzip.open(...,'rt')` + `json.load` → `env["algorithm"] == "csp"` (state-FORMAT tag, top-level, NOT the flag) and `env["state_data"]["domains"]` is a **non-empty** dict.

  *Test C — repair pause saves a degenerate CSPState:* `_run_fill_until_paused(tmp_path, "repair", "tC")`. Assert: `returncode == 0`; stdout `paused is True`; state file exists; `env["algorithm"] == "csp"`; `env["state_data"]["domains"] == {}`; `env["metadata"]["algorithm"] == "repair"`; `env["state_data"]["grid_dict"]["grid"]` is present (best partial captured).

  *Test D — beam pause routes through the same degenerate writer:* `_run_fill_until_paused(tmp_path, "beam", "tD")`. Assert: `returncode == 0`; stdout `paused is True`; state file exists; `env["algorithm"] == "csp"`; `env["state_data"]["domains"] == {}`; `env["metadata"]["algorithm"] == "beam"`. (Hybrid pauses via its Phase-1 forwarding + Phase-2 repair hook, DD5 — covered indirectly; a full hybrid subprocess test is optional and slow, omitted to keep the suite fast.)

- [ ] **Step 2 — run** `pytest cli/tests/test_fill_pause_resume.py -o addopts= -v`. **The `-o addopts=` is load-bearing** — it clears `pytest.ini:8`'s default `addopts = -v -m "not slow"`, without which the slow Tests B/C/D are silently *deselected* and never run. Expected: **all four** FAIL with `Error: no such option: --task-id` (Click exit 2). (Confirm the summary shows 4 failed, not `1 failed, 3 deselected`.)

- [ ] **Step 3 — implement** DD1-DD6. Read the fill command (`cli.py:104-651`) first; add the local imports (`PauseController`, `StateManager`, `CSPState`, `datetime` — sibling pattern at `:1202`/`:1275`/`:1453`). Order: (1) options + params + DD1 construction (with the `not adaptive` + `Path(...) if x else None` guards); (2) DD3 CSP injection at `:396` (`attempts==1` gate) + conditional `task_id=` at `:499`/`:502` (`not adaptive`); (3) DD2 `autofill.py` two-block + `_handle_pause` persist; (4) DD4 repair hooks; (5) DD5 wrapper/hybrid forwarding + both hybrid paused returns; (6) DD6 paused branch. Do NOT try to `except PausedException` in the command — it never escapes `Autofill.fill()` (`:193`).

- [ ] **Step 4 — run** `pytest cli/tests/test_fill_pause_resume.py -o addopts= -v` → Expected: **PASS (A/B/C/D) — the summary MUST read `4 passed`, NOT `1 passed, 3 deselected`** (the `-o addopts=` clears `pytest.ini:8`'s `-m "not slow"` so B/C/D actually execute; a bare `-v` would verify only that the flag parses, never that pause saves state). Then `pytest cli/tests/ -q` (default markers — the fast regression sweep) → Expected: full CLI suite green (no regression to default fills, guaranteed by the `task_id is None` / `not adaptive` no-op gates, DD1).

- [ ] **Step 5 — commit** — `feat(cli): fill --task-id/--state-dir/--pause-flag-dir with pause for csp+repair+beam`


---


## Task 14 — CLI: `fill --resume` + fix `CLIAdapter.fill_with_resume`

> **⚠️ Before executing — apply header Cross-section reconciliation notes 1, 5, 6, 7** (per-task dispatch may not include the header; these OVERRIDE the body below): **(1)** DD4's `metadata["theme_entries"]` lock channel is unsatisfiable — drop it, accept M1 grid-structure-only degradation, do NOT add `theme_entries` to Task 13; **(5)** the DD5 `PAUSE_FLAG_DIR` placeholder is `/tmp` canonically (Task 15); **(6)** DD2's `--task-id` is the fresh SSE id (T2), not `resume_<8hex>` (R1 = the `--resume` file basename); **(7)** Task 13 delivers `result.paused` via the `FillResult` constructor — there is no `self.was_paused` attribute (the opening-note wording is stale).

> **Depends on Task 13** (same branch, lands first). Task 13 has already added the `--task-id/--state-dir/--pause-flag-dir` options + `def fill(...)` params, imported `PauseController`/`StateManager` into the `fill` command, wired them into the engine construction at `cli.py:396` (classic) and `:351-385` (beam/repair/hybrid), added `self.was_paused = True` to **both** `except PausedException` blocks (`autofill.py:193-195` fill *and* `:247-248` `_resume_fill`), and built the post-`fill()` paused-exit check (`paused = getattr(autofill, "was_paused", False) or getattr(result, "paused", False)` → paused stdout protocol + `exit 0`). Task 14 **adds `--resume`** and **reuses** all of that: the resume branches rejoin the Task-13 paused-exit + output path unchanged. If Task 13's `_resume_fill` `was_paused` edit is missing, a **re-pause of a resumed CSP fill is silent** (the `:247-248` swallow — HAZARD) — Task 14 asserts nothing new here but flags it as a hard prerequisite.

### Files

> **Line numbers below are HEAD-relative (9e124b2).** Task 13's option/param/wiring insertions in `cli.py` shift every `cli.py:` seam downward before Task 14 executes — **locate each seam by the shown code, not the absolute line.** The `autofill.py`, `state_manager.py`, `cli_adapter.py`, and test-file citations are not shifted by Task 13 and are exact at HEAD.

- Modify: `cli/src/cli.py` — `fill` command: `grid_file` argument (`:105`), new `--resume` option (add beside `:104-185`), grid-load block (`:210-218`), engine dispatch (`:350-396`), fill-call dispatch (`:462-506`). No change to the output block (`:533-651`) — resume rejoins it.
- Modify: `backend/core/cli_adapter.py:403-476` (`fill_with_resume` argv) + new module-level `STATE_DIR`/`PAUSE_FLAG_DIR` constants.
- Test: extend `cli/tests/test_fill_pause_resume.py` (Task 13 created it — reuse its module-level `WORDLIST` + `_run_fill` helper, do not redefine); extend `backend/tests/unit/test_cli_adapter.py::TestFillWithResume` (`:342-412`).

### Interfaces

**Consumes (all verified at HEAD):**
- `StateManager(storage_dir=Path).load_csp_state(task_id) -> (CSPState, metadata)` (`state_manager.py:175`) — reads `{storage_dir}/{task_id}.json.gz`, hard-validates `version=="1.0"` (`:206-207`) and `algorithm=="csp"` (`:210-211`). Both resume branches load through this (the degenerate graceful-stop state is also `algorithm="csp"` — Task 13 routes its save through `save_csp_state`), so a beam-native state file is correctly rejected with `ValueError`.
- `Autofill.fill(resume_state: CSPState, task_id) -> FillResult` (`autofill.py:115-123`) → dispatches to `_resume_fill` (`:141-142`). **`_resume_fill` restores state itself** — it calls `self.state_manager.restore_to_autofill(self, resume_state)` at `:226`, sets `self.locked_slots` (`:235`), and continues `_backtrack_with_mac` from `resume_state.current_slot_index` (`:242`). So the CLI **does not** call `restore_to_autofill` explicitly; it just constructs a classic `Autofill` and calls `fill(resume_state=…)`. Timeout is governed by the constructor `timeout` (stored on `self`, enforced inside `_backtrack_with_mac`) — the resume `fill()` call passes no `timeout=`.
- `CSPState.domains` / `.grid_dict` / `.locked_slots` (`state_manager.py:27,30,44`) — the content-dispatch discriminator.
- `Grid.from_dict(grid_dict, strict_size=False)` (`cli.py:218` pattern).

**Produces (CLI):** `fill --resume <state.json.gz>` — grid comes from the state, dispatched on **content, not the `--algorithm` flag**:
- `csp_state.domains` **non-empty** (real CSPState from a trie/regex CSP pause) → exact-position resume under classic `Autofill` regardless of `--algorithm`.
- `csp_state.domains` **empty** (degenerate graceful-stop from repair/hybrid/beam) → re-seed the requested `--algorithm` engine from `grid_dict`.
Resumed fills are themselves pausable via the same `--task-id`.

**Produces (adapter):** `fill_with_resume(task_id, state_file_path, wordlist_paths, timeout_seconds=300, min_score=30, algorithm="trie", state_dir=None, pause_flag_dir=None)` — **existing positional order preserved; two defaulted kwargs appended** (see DD5). Builds argv containing `fill --resume <state> --wordlists … --task-id <id> --state-dir <STATE_DIR> --pause-flag-dir <PAUSE_FLAG_DIR> --algorithm … --timeout … --min-score … --output <tmp>` — no `grid_file` positional (DD1), no `--json-output` (DD5).

### DD1 — `grid_file` becomes optional; `--resume` supplies the grid
The `fill` command loads `grid_file` unconditionally at `cli.py:218`; on resume the grid must come from `csp_state.grid_dict`. Make `grid_file` optional and add the resume load as a **short-circuit** of the `:210-218` block.
```python
# cli.py:105  BEFORE:  @click.argument("grid_file", type=click.Path(exists=True))
#              AFTER:   @click.argument("grid_file", type=click.Path(exists=True), required=False)
# new option (add near :104-185); new `resume: Optional[str]` param on def fill(...)
@click.option("--resume", type=click.Path(exists=True), default=None,
              help="Resume a paused fill from a saved state file (<task_id>.json.gz)")
```
Validation near the top of the body: `if not resume and not grid_file: raise click.UsageError("Provide a grid file or --resume <state>")`. When both are given, `--resume` wins (grid_file ignored). Note `--wordlists` stays `required=True` (the engine needs a `WordList` object even on resume) — the tests and the adapter pass it. **Deviation from parent line 574**, which lists `<grid_file>` in the resume argv — see Self-Review.

### DD2 — Two task_ids: state-file id (load) vs `--task-id` (resumed run's saves)
`--task-id` is the **fresh** id for the resumed run's pause plumbing (the backend passes `resume_<8hex>`, Task 15/16). The state file's **original** id is only in its filename. Load using the resume path itself, so the state dir divergence HAZARD (backend `backend/data/autofill_states` vs CLI default `/tmp/crossword_states`) cannot bite — read from wherever the file actually is:
```python
# resume grid-load short-circuit (replaces the :215-218 read when resume is set):
sm_load = StateManager(storage_dir=Path(resume).parent)
csp_state, metadata = sm_load.load_csp_state(Path(resume).name.removesuffix(".json.gz"))  # .json.gz per Cross-task literals (compress=True default)
grid = Grid.from_dict(csp_state.grid_dict, strict_size=False)   # size validated at original-fill time; allow non-standard resume
```
The **save-side** `StateManager` (Task-13-injected into the engine, `storage_dir=Path(state_dir)`) and `PauseController(task_id, pause_dir=Path(pause_flag_dir))` are unchanged — a re-pause writes `{state_dir}/{new_task_id}.json.gz`.

### DD3 — Content dispatch: exact-position vs degenerate re-seed
Three interception seams; **everything else is shared with the fresh-fill path unchanged** (wordlist load `:224-242`, `pattern_matcher` `:314`, `all_valid_words` `:329-348`, `progress`, output `:533-651`, Task-13 paused-exit):

| seam | fresh fill | resume, `domains` non-empty (exact CSP) | resume, `domains` empty (degenerate re-seed) |
|---|---|---|---|
| grid source (`:210-218`) | load `grid_file` | `Grid.from_dict(csp_state.grid_dict, strict_size=False)` (DD2) | same |
| engine choice (`:350-396`) | dispatch on `--algorithm` | **force** classic `Autofill(grid, word_list, None, timeout, min_score, algorithm, progress, pause_controller=pc, state_manager=sm)` — CSPState machinery is CSP-only (parent line 573). The `algorithm` flag passed here only selects the matcher (`=="trie"`→`TriePatternMatcher`, anything else→regex `PatternMatcher`, `autofill.py:85-88`); the default `repair`/other flag values are **harmless, not an error**, and on resume `domains` are restored from state so the matcher choice is non-load-bearing. | existing `--algorithm` dispatch (`:351-396`), Task-13 pause-wired |
| fill call (`:462-506`) | `fill()`/`fill(timeout=)` | `result = autofill.fill(resume_state=csp_state, task_id=task_id)` — leave `use_mac=True` default (pause check lives only in `_backtrack_with_mac:853`, never `_backtrack`) | existing `fill(timeout=timeout)` (repair/hybrid/beam) |

For the exact-position branch the grid handed to the `Autofill` constructor is immaterial — `restore_to_autofill` overwrites `self.grid` at `:424` — but the injected `pause_controller`/`state_manager` survive (set in `__init__`, untouched by restore), so the resumed CSP fill re-pauses correctly.

### DD4 — Degenerate re-seed stays THIN; lock enforcement is Task 13's save contract
The empty-domains branch reconstructs the grid from `grid_dict` and runs the requested engine — **it does NOT re-derive locks by enumerating current words.** Consumer-side lock recomputation is fragile exactly where the degenerate recipe permits `slot_list=[]` (Cross-task literals), leaving `locked_slots` ints mapping to nothing, and it duplicates the single-source rule. **Binding dependency on Task 13:** the graceful-stop save must record locks in a form Task 14 passes straight through (e.g. as a `theme_entries` dict `{(row,col,direction): WORD}` in `metadata`, which the repair/hybrid/beam engines already preserve via `grid.locked_cells`, `iterative_repair.py:191-197`) so `IterativeRepair` will not rip user-edited/theme cells. Task 14 reads `metadata.get("theme_entries")` if present and forwards it to the engine; otherwise the lock degrades to grid-pre-fill preservation only. **Note:** `IterativeRepair` only preserves cells in `grid.locked_cells` and explicitly strips non-locked crossing words (`:298`) — algorithm-placed (non-theme) pre-filled cells are *not* guaranteed to survive a re-seed. **Follow-up (logged):** if the seam leaks (repair rips a cell that should have been locked), fix it in Task 13's save, not here.

### DD5 — Adapter: append-only signature, argv fix, keep the test-only I/O model
`fill_with_resume` is **unused in production** (only `test_cli_adapter.py:342-412` calls it; the `resume_autofill` route does not — Task 15 wires the real web resume through `run_cli_with_progress`, which reads **stdout**). So Task 14's adapter job is narrow: correct the argv. Two constraints:
1. **Do not reorder/replace the signature.** Parent line 574's `(state_file, task_id, options)` is pseudocode; adopting it breaks the three passing tests (`:343-412`). **Append** `state_dir=None, pause_flag_dir=None` after `algorithm="trie"`; fall back to module constants when `None`. (Every token the existing `test_command_construction` asserts — `fill`, `--resume`, `<state>`, `--task-id`, `task-42`, `--timeout`, `60`, `--min-score`, `40`, `--algorithm`, `regex`, `--wordlists`, `w1.txt` — stays present in the new argv, so those tests remain green.)
2. **Do not add `--json-output`.** The method reads its result from the `--output` **file** (`:470-471`); in `--json-output` mode fill writes nothing to `--output` (json branch `:562-613` echoes to stdout only; the `--output` file is written only on the non-json path `:646-651`), so adding it starves the read. Leave the I/O model as-is.

Module constants (Task 14 runs before Task 15, so **this branch executes** — define them concretely; Task 15 later moves them into `backend/core/state_paths.py`):
```python
# cli_adapter.py (module level; Path already imported at :8) — import-or-define per parent line 574
STATE_DIR = Path(__file__).parent.parent / "data" / "autofill_states"      # == Cross-task literals STATE_DIR (backend/data/autofill_states)
PAUSE_FLAG_DIR = STATE_DIR.parent / "autofill_pause_flags"                  # placeholder value; Task 15 finalizes (value not test-load-bearing — test imports the same constant)
```
Corrected argv (fixes the dead-code HAZARD — current `:443-460` emits `--resume`/`--task-id` the pre-Task-13 CLI lacked and omits both dirs):
```python
args = ["fill", "--resume", str(state_path),
        "--task-id", task_id,
        "--state-dir", str(state_dir or STATE_DIR),
        "--pause-flag-dir", str(pause_flag_dir or PAUSE_FLAG_DIR),
        "--output", output_path,
        "--timeout", str(timeout_seconds), "--min-score", str(min_score),
        "--algorithm", algorithm]
for wl in wordlist_paths: args.extend(["--wordlists", wl])
```

### TDD Steps
- [ ] **Step 1 — failing CLI resume test** (`cli/tests/test_fill_pause_resume.py`). Extract Test B's pause flow (from the Task-13 module) into a helper `_pause_a_fill(tmp_path, algorithm, task_id) -> (grid_file, state_dir, flag_dir, state_file)` (blank 15×15, `--algorithm <algo>`, `-t 120`, `--json-output`, the three Task-13 dir/id options into `tmp_path`; `sleep(3)`; touch `<flag_dir>/crossword_pause_<task_id>.flag`; `communicate(timeout=60)`; return the on-disk `<state_dir>/<task_id>.json.gz`). Reuse the Task-13 module's `_run_fill` helper and `WORDLIST` constant (do not redefine). Primary test (mirrors parent Step 1 — slow-test reliability leans on that precedent):
```python
@pytest.mark.slow
def test_resume_trie_exact_position_completes(tmp_path):
    gf, state_dir, flag_dir, state_file = _pause_a_fill(tmp_path, "trie", "orig-1")
    assert state_file.exists()
    proc = _run_fill(["--resume", str(state_file), "-w", WORDLIST,
                      "--task-id", "resume-1", "--state-dir", str(state_dir),
                      "--pause-flag-dir", str(flag_dir),
                      "-t", "120", "--algorithm", "trie", "--json-output"],
                     timeout=180)                      # NB: no grid_file positional (DD1)
    assert proc.returncode == 0
    out = json.loads(proc.stdout.strip())
    assert set(out) >= {"success", "grid", "slots_filled", "total_slots", "fill_percentage",
                        "time_elapsed", "iterations", "problematic_slots_count"}   # Cross-task literals
    assert out["success"] is True and out["slots_filled"] == out["total_slots"]
    assert all("." not in row for row in out["grid"])
```
Secondary (degenerate re-seed — hard assertions are **Task-14-guaranteed only**: survival + a correctly-shaped grid, NOT completion (a re-seeded repair fill is non-deterministic) and NOT blanket letter-survival (repair may legitimately empty a non-locked pre-filled cell, `iterative_repair.py:298` — see DD4)):
```python
@pytest.mark.slow
def test_resume_repair_degenerate_returns_grid(tmp_path):
    gf, state_dir, flag_dir, state_file = _pause_a_fill(tmp_path, "repair", "orig-2")
    import gzip
    saved = json.loads(gzip.open(state_file, "rt").read())["state_data"]["grid_dict"]["grid"]
    black = [(r, c) for r, row in enumerate(saved)
             for c, cell in enumerate(row) if cell == "#"]
    proc = _run_fill(["--resume", str(state_file), "-w", WORDLIST, "--task-id", "resume-2",
                      "--state-dir", str(state_dir), "--pause-flag-dir", str(flag_dir),
                      "-t", "60", "--algorithm", "repair", "--json-output"], timeout=90)
    assert proc.returncode == 0
    out = json.loads(proc.stdout.strip())
    assert "grid" in out and len(out["grid"]) == len(saved)     # a grid of the right size came back
    for (r, c) in black:                                        # black-square structure preserved
        assert out["grid"][r][c] == "#"                         #   (Grid.from_dict rebuilds '#', repair never touches black)
    # DD4 lock-contract canary (deferred): a precise pre-filled-cell survival check must assert
    # only over metadata["theme_entries"] cells — that is Task 13's save responsibility, not asserted
    # here, because non-locked pre-filled cells may be legitimately stripped by repair.
```
Run: `python -m pytest cli/tests/test_fill_pause_resume.py -o addopts= -k resume -x -v` (the `-o addopts=` clears `pytest.ini:8`'s `-m "not slow"`; the resume tests are `@pytest.mark.slow`, so `-k resume` alone AND-ed with the default `-m "not slow"` selects **nothing**).
- [ ] **Step 2 — run → FAIL** with `Error: No such option: --resume` (Task 13 added the three dir/id options but not `--resume`). Implement per DD1-DD4 (grid_file optional + `--resume` option + validation; resume grid-load short-circuit; content dispatch at the three seams; degenerate `theme_entries` pass-through). Re-run → **PASS**; then full `python -m pytest cli/tests/test_fill_pause_resume.py -o addopts= -q` green (again `-o addopts=` so the slow resume tests actually run).
- [ ] **Step 3 — adapter argv test** (`backend/tests/unit/test_cli_adapter.py::TestFillWithResume`). Add the failing assertions to `test_command_construction` (`:375-388`, the argv-assertion block), importing the adapter's own constants so test and code share one source:
```python
from backend.core.cli_adapter import STATE_DIR, PAUSE_FLAG_DIR
assert "--state-dir" in args and str(STATE_DIR) in args
assert "--pause-flag-dir" in args and str(PAUSE_FLAG_DIR) in args
```
The three existing tests (`test_missing_state_file_raises`, `test_command_construction`, `test_resume_timeout_buffer`) must stay green — **append-only** signature change (DD5). Run → the two new asserts FAIL (dirs absent today). Fix the argv + add the constants. Run `python -m pytest backend/tests/unit/test_cli_adapter.py::TestFillWithResume -v` → **PASS**; backend suite `python -m pytest backend/tests/ -q` green.
- [ ] **Step 4 — commit** — `feat(cli): fill --resume consuming saved solver state; fix fill_with_resume adapter`

### Self-Review (reasoned deviations from parent Task 14)
1. **`grid_file` made optional; adapter passes no `grid_file` positional** — deviates from parent line 574's `['fill', <grid_file>, '--resume', …]`. The grid is authoritative in `csp_state.grid_dict`; a required positional would be dead scaffolding forcing the adapter to materialize a grid file it never reads, and the current adapter already passes none — Option A preserves existing structure. (DD1.)
2. **No explicit `StateManager.restore_to_autofill` call** — parent line 573 names it, but it is internal to `_resume_fill` (`autofill.py:226`); the CLI only calls `fill(resume_state=…, task_id=…)`. (Interfaces/Consumes.)
3. **Adapter signature append-only** (parent's `(state_file, task_id, options)` reorders params and would break three passing tests); **`--json-output` deliberately omitted** (would starve the `--output`-file read). Adapter stays test-only until Task 15. (DD5.)
4. **Degenerate re-seed kept thin** — lock enforcement pushed to Task 13's save contract rather than re-derived by word-enumeration in Task 14; degenerate test asserts survival + a correctly-shaped grid with intact black-square structure, not completion and not blanket per-cell letter-survival. (DD4.)


---


## Task 15 — Backend: `resume_task_id` through `/api/fill/with-progress` + one shared state/flag dir + paused SSE termination

Wires the second step of the two-step resume (F14) into the SSE fill route, makes **every** web fill pausable by threading `--task-id/--state-dir/--pause-flag-dir` onto the spawned argv, kills the split-default severance by giving the backend routes, the CLI it spawns, and the pause route a single source for both directories, and closes the paused SSE stream server-side (generator break parity with `complete`/`error`). Depends on Task 14's `fill --resume` contract already landing (the CLI resume argv shape is Task 14's; this task only builds/targets it).

### Files
- **Create:** `backend/core/state_paths.py` (canonical `STATE_DIR` + `PAUSE_FLAG_DIR`, per Cross-task literals §"Web shared dirs")
- **Modify:** `backend/api/routes.py` — add module-level `from backend.core.state_paths import STATE_DIR, PAUSE_FLAG_DIR` (both DD2's flags and DD3's `state_path` resolve through these module globals; the unit tests `monkeypatch.setattr` them). Then `run_cli_with_progress` (:246; paused-terminal branch inside the `returncode == 0` block :330-343), `fill_with_progress` (:434-566; resume-branch + always-on dir/task-id flags in `cmd_args` :507-518, resume read placed right after :442)
- **Modify:** `backend/api/progress_routes.py` — add `"paused"` to the terminal-status break set in `stream_progress`'s `generate()` (:157: `["complete", "error"]` → `["complete", "error", "paused"]`) so the SSE stream actually ends on a paused event (DD4b). This line is inert for all non-pause flows (only the pause path ever emits `status:"paused"`).
- **Modify:** `backend/api/pause_resume_routes.py` — replace local `STATE_STORAGE_DIR` def (:26-27) with an import from `state_paths`; add `pause_dir=PAUSE_FLAG_DIR` to the two `PauseController` constructions (pause :53, cancel :110)
- **Modify:** `backend/core/cli_adapter.py` — `fill_with_resume` (:403-476): single-source its dir arguments from `state_paths` (Task-14-contingent no-op at HEAD — see DD5)
- **Test (create):** `backend/tests/unit/test_fill_resume_route.py`

### Interfaces

**Consumes:**
- `validate_fill_request(data) -> dict` (`validators.py:135`) — **returns the same `data` dict** (`return data` at :224, verified), so `data.get("resume_task_id")` survives validation; `resume_task_id` is NOT in its checked-field set and passes through untouched. `wordlists` is optional (validated only `if "wordlists" in data`), so a `{size, grid}`-only body is valid.
- `create_progress_tracker() -> str` (`progress_routes.py:32`); `send_progress(task_id, progress:int, message:str, status:str="running", data:dict=None)` (`progress_routes.py:48`); `progress_queues: Dict[str, queue.Queue]` (`progress_routes.py:21`) — `send_progress` no-ops unless `task_id in progress_queues` (:65-66).
- `stream_progress`'s `generate()` terminal-break set (`progress_routes.py:157`) — currently `["complete", "error"]`; DD4b extends it. The repo relies on this generator terminating: `client.get('/api/progress/<id>')` **blocks synchronously until the stream ends** (documented at `test_pause_resume_workflow.py:107`).
- `handle_error(code:str, message:str, status:int, details:dict=None)` (`errors.py:10`) — 3-positional-arg form producing `{"error":{"code":..., "message":...}}`; `routes.py` already calls it correctly (`handle_error("INVALID_REQUEST", str(e), 400)` :564).
- Paused stdout protocol + state-file path + `STATE_DIR` value: **Cross-task literals** §"Paused stdout protocol", §"State file", §"Web shared dirs" — do not restate.

**Produces:**
- `backend/core/state_paths.py`: module-level `STATE_DIR: Path` and `PAUSE_FLAG_DIR: Path`, both `mkdir(parents=True, exist_ok=True)` on import (contract snippet in DD1).
- `POST /api/fill/with-progress` gains optional `resume_task_id`; when present and `STATE_DIR/<resume_task_id>.json.gz` exists the spawned argv carries `--resume <state_path>`, else **404** `{"error":{"code":"TASK_NOT_FOUND", ...}}`. Every web fill (fresh or resumed) now carries `--task-id <task_id> --state-dir <STATE_DIR> --pause-flag-dir <PAUSE_FLAG_DIR>`.
- SSE terminal semantics: a paused-protocol stdout (`{"paused": true, ...}`, exit 0) makes `run_cli_with_progress` emit a terminal `status:"paused"` event and **suppress** the spurious `complete` (DD4); **and** the SSE generator (`progress_routes.py:157`) now includes `"paused"` in its terminal-break set, so the stream actually closes on the first `paused` event (DD4b) — parity with `complete`/`error`.

### DD1 — `state_paths.py`: one owner for both dirs, defaults chosen to preserve today's working paths

The severance is real, not merely fragile: the backend reads/writes state at `backend/data/autofill_states` (`pause_resume_routes.py:26`, consumed at the six `StateManager(storage_dir=STATE_STORAGE_DIR)` sites :194,:299,:342,:393,:439,:502), while the CLI's `StateManager` **defaults** to `/tmp/crossword_states` (`state_manager.py:125-126`) — so CLI-written state is invisible to the backend resume route (format-collision hazard). Separately, `PauseController` defaults `pause_dir=/tmp` (`pause_controller.py:34-35`) while `StateManager` defaults to `/tmp/crossword_states` — split defaults (gotcha hazard). `state_paths.py` owns **both**; every backend route and every spawned CLI invocation passes them **explicitly**.

Defaults are picked so nothing that works today breaks:
- `STATE_DIR` default **must** equal the existing `pause_resume_routes.py:26` path so already-saved state stays resolvable — and it does: `state_paths.py` lives in `backend/core/`, so `Path(__file__).resolve().parent.parent == backend/`, giving `backend/data/autofill_states` (same target as the route's `Path(__file__).parent.parent / "data" / "autofill_states"`, where `pause_resume_routes.py` sits in `backend/api/`).
- `PAUSE_FLAG_DIR` default `/tmp` matches both `PauseController`'s default and the backend's current implicit default — so pausing keeps working the instant this lands; it is now single-sourced rather than accidentally agreeing.
- Both env-overridable so tests point them at `tmp_path`.

```python
# backend/core/state_paths.py — contract (load-bearing literals: the two names + defaults)
# requires: import os; from pathlib import Path
STATE_DIR      = Path(os.environ.get("CROSSWORD_STATE_DIR",
                      Path(__file__).resolve().parent.parent / "data" / "autofill_states"))
PAUSE_FLAG_DIR = Path(os.environ.get("CROSSWORD_PAUSE_FLAG_DIR", "/tmp"))
# both: .mkdir(parents=True, exist_ok=True) on import
```

`pause_resume_routes.py` swaps its local block for `from backend.core.state_paths import STATE_DIR as STATE_STORAGE_DIR, PAUSE_FLAG_DIR` — the alias keeps all six `StateManager(storage_dir=STATE_STORAGE_DIR)` call sites unchanged (minimal diff). Add `pause_dir=PAUSE_FLAG_DIR` at the two `PauseController(task_id=task_id)` constructions (:53, :110) so the flag the backend writes lands where the spawned CLI reads.

### DD2 — Fresh-fill argv: always thread task-id + dirs (the whole reason pause is a no-op today)

Today `fill_with_progress` builds `cmd_args` (:507-518) with `fill, grid_file, --timeout, --min-score, --algorithm, --allow-nonstandard, --json-output, --wordlists…` and **no** `--task-id`, so a fresh `/fill/with-progress` cannot be paused at all — `POST /api/fill/pause/<id>` writes `/tmp/crossword_pause_<id>.flag` but the running CLI never constructs a `PauseController` (silent-failure hazard; the consumer machinery exists at `autofill.py:853`, `orchestrator.py:300` but is gated on an injected controller the fresh fill leaves `None`). Task 13 taught the CLI the three options; Task 15 supplies them on every spawn. Append to `cmd_args` unconditionally:

```
--task-id <task_id>  --state-dir <str(STATE_DIR)>  --pause-flag-dir <str(PAUSE_FLAG_DIR)>
```

`<task_id>` is the fresh SSE id from `create_progress_tracker()` (:442) — the same id the pause route targets. This is additive to the existing `cmd_args`; theme/adaptive/partial/cleanup flags (:523-543) are untouched.

### DD3 — Resume branch: resolve the prepared state file, 404 on miss, add `--resume`; keep `grid_file` positional

The resume is two real requests (state-machine amendment F14): the client first calls `POST /api/fill/resume`, which **prepares** merged state under `new_task_id = "resume_<8hex>"` (`f"resume_{uuid.uuid4().hex[:8]}"` :235) and writes it via `StateManager(storage_dir=STATE_STORAGE_DIR).save_csp_state(...)` (`pause_resume_routes.py:238-243`) — **it does not start a fill**. The client then calls `POST /api/fill/with-progress` with `resume_task_id = new_task_id`. So when `fill_with_progress` sees `resume_task_id`, the file already exists at `STATE_DIR/<resume_task_id>.json.gz` (STATE_DIR == the resume route's STATE_STORAGE_DIR, single-sourced by DD1).

Read `resume_task_id = data.get("resume_task_id")` **immediately after `create_progress_tracker()` (:442)** and resolve/return there — **before** the grid temp file is written (:477-480). A 404 that fires after :480 orphans a temp `.json` (this early `return` is not covered by any `finally`; only `run_cli_with_progress`'s thread cleans temp files). When `resume_task_id` is present:
- `state_path = STATE_DIR / f"{resume_task_id}.json.gz"` (path per Cross-task literals §"State file").
- `if not state_path.exists(): return handle_error("TASK_NOT_FOUND", f"No saved state for task {resume_task_id}", 404)` — the **3-arg** form (do NOT copy `pause_resume_routes.py`'s broken `handle_error(e, default_status=500)` at :73/:264 — `errors.py:10` has no `default_status` param, so that shape raises `TypeError`; `routes.py` uses the correct signature at :564).
- Append `--resume str(state_path)` to `cmd_args`, in addition to the DD2 always-on flags.

The `grid_file` positional (written at :477-480 from the client's current/edited grid) **stays** — `fill`'s `grid_file` is a required Click argument (Task 14's resume argv lists `['fill', <grid_file>, '--resume', <state_file>, …]`), and Task 14 dispatches on **state-file content**, treating the state file as authoritative for the resumed slots. Task 15 does not re-encode edits here; the merged edits are already inside the resume state file (written by the resume route). This matches the canonical decision recorded in the Phase-3 preamble (web path = `fill --resume <state-file> --task-id <id>`).

### DD4 — Paused-terminal branch: suppress the spurious `complete` (coupled with the already-correct stderr passthrough)

Two coupled points (gotcha hazard). (i) The stderr passthrough (:305-315) downgrades only `complete`/`error` to `running` (:306-307) and forwards a `status:"paused"` event **verbatim** — already correct, no change. (ii) But after stderr EOF the read loop exits, `communicate()` returns, and control falls into `if process.returncode == 0:` (:330), which **unconditionally** emits `send_progress(..., "complete", result_data)` (:339). Fixing only (i) yields a `paused`-then-`complete` stream. The real fix is here: inside the `returncode == 0` block, after `result_data = json.loads(stdout.strip())` (:333) and **before** the `complete` send (:339), branch:

```
if result_data.get("paused"):
    total = result_data.get("total_slots") or 0
    pct   = int(result_data.get("slots_filled", 0) / total * 100) if total else 0
    send_progress(task_id, pct, "Paused", "paused", result_data)
    return          # end run_cli_with_progress WITHOUT emitting 'complete'
```

The early `return` is safe: temp-file cleanup is in a `finally` (:380-387), which runs regardless. The terminal `paused` is idempotent w.r.t. the mid-stream stderr `paused` — it also guarantees the client sees a `paused` even if the stderr event was dropped.

**Caveat (contract, not verifiable at HEAD):** this branch fires only because Task 13 guarantees the paused CLI **exits 0** (Cross-task literals §"Paused stdout protocol"). If a future change makes pause exit non-zero, detection must also live in the `else` block (:344-366). The paused stdout schema (`{"paused": true, "task_id", "slots_filled", "total_slots"}`) is Task 13's; do not assume a `progress` key — compute `pct` from `slots_filled/total_slots`.

### DD4b — Close the stream server-side: `"paused"` must join the generator's terminal-break set

DD4 stops `run_cli_with_progress` from emitting `complete`, but that alone does **not** end the SSE stream. `stream_progress`'s `generate()` loop breaks only on `event["status"] in ["complete", "error"]` (`progress_routes.py:157`); a `paused` event is yielded and the loop then re-enters `queue.get(timeout=30)`, heartbeating forever until the client disconnects. Since `client.get('/api/progress/<id>')` blocks until the stream ends (`test_pause_resume_workflow.py:107`), an un-terminated paused stream **hangs** the consumer. Fix: extend the break set to `["complete", "error", "paused"]`.

Interaction to rely on (do not re-engineer): DD4 emits a **mid-stream** stderr `paused` (via the :305-315 passthrough, carrying the richer `{state_path, grid}` payload) **before** the terminal stdout `paused`. With the break set extended, the generator breaks on that **first** `paused`, yields it, runs its `finally` (`cleanup_progress_tracker` pops `task_id`), and returns. The DD4 terminal `send_progress` then either no-ops (queue already popped) or is dropped (generator already returned) — harmless either way. Resume opens a **fresh** `task_id` stream, so closing the old one is correct. This line is inert for pattern/fill/export flows, which never emit `paused`.

### DD5 — `cli_adapter.fill_with_resume`: single-source the dirs only (Task-14-contingent, no-op at HEAD)

`fill_with_resume` (`cli_adapter.py:403-476`) is **unused in production** (only `test_cli_adapter.py` calls it; the resume route does not — dead-code hazard). At HEAD its argv (:443-457) carries `--resume … --task-id …` but **no** dir flags and **no local dir literal** (verified: grep for `crossword_states`/`state-dir`/`pause-flag-dir` in `cli_adapter.py` returns nothing). Task 15's only touch is single-sourcing: **if** Task 14 reshaped this argv to add `--state-dir/--pause-flag-dir` backed by a local constant (per its "if executing first, define here and Task 15 moves it" note), delete that constant and import `STATE_DIR`/`PAUSE_FLAG_DIR` from `state_paths`; **if** Task 14 has not yet added dir flags here, this is a pure no-op. No argv reshape, no behavior change — the point is only that a future dir change moves in lockstep.

### TDD Steps

- [ ] **Step 1 — Failing route tests** in `backend/tests/unit/test_fill_resume_route.py`. Reuse the `test_routes.py:44-63` `client` fixture convention (mocked `get_adapter`/`cli_adapter`) — **note it yields a tuple `(c, mock_adapter)`**, so unpack `c, _ = client` in each test that uses it, and `_post_json(c, url, body)` (helper at `test_routes.py:66-68`). Point `state_paths` at `tmp_path` **deterministically** with `monkeypatch.setattr` on the module globals routes.py binds (constants are evaluated at import time, so `setenv`-after-import is a trap):
  ```python
  import backend.api.routes as routes_mod
  monkeypatch.setattr(routes_mod, "STATE_DIR", tmp_path)
  monkeypatch.setattr(routes_mod, "PAUSE_FLAG_DIR", tmp_path)
  ```
  Capture the spawned argv by patching `backend.api.routes.threading.Thread` — the route calls `Thread(target=run_cli_with_progress, args=(task_id, cmd_args, timeout, temp_files), daemon=True)` (:550-554), so `cmd_args = Thread.call_args.kwargs["args"][1]`.

  **(a) fresh fill threads task-id + dirs:**
  ```python
  c, _ = client
  resp = _post_json(c, "/api/fill/with-progress", {"size":5, "grid":[["."]*5]*5})
  assert resp.status_code == 202
  argv = Thread.call_args.kwargs["args"][1]
  assert "--task-id" in argv
  assert argv[argv.index("--state-dir")+1]      == str(tmp_path)
  assert argv[argv.index("--pause-flag-dir")+1] == str(tmp_path)
  assert "--resume" not in argv
  ```
  **(b) resume_task_id + existing state file → `--resume <path>`:** write a dummy `tmp_path/"resume_abc12345.json.gz"` (bytes suffice; the route only checks `.exists()`), then:
  ```python
  c, _ = client
  (tmp_path / "resume_abc12345.json.gz").write_bytes(b"x")
  resp = _post_json(c, "/api/fill/with-progress",
                    {"size":5, "grid":[["."]*5]*5, "resume_task_id":"resume_abc12345"})
  assert resp.status_code == 202
  argv = Thread.call_args.kwargs["args"][1]
  assert argv[argv.index("--resume")+1] == str(tmp_path / "resume_abc12345.json.gz")
  assert "--task-id" in argv                        # fresh SSE id, still pausable
  ```
  **(c) resume_task_id, missing state file → 404 TASK_NOT_FOUND:**
  ```python
  c, _ = client
  resp = _post_json(c, "/api/fill/with-progress",
                    {"size":5, "grid":[["."]*5]*5, "resume_task_id":"resume_missing"})
  assert resp.status_code == 404
  assert resp.get_json()["error"]["code"] == "TASK_NOT_FOUND"
  ```
  **(d) paused stdout → terminal `paused`, no `complete` (queue level):** exercise `run_cli_with_progress` directly with a fake Popen (patch `backend.api.routes.subprocess.Popen`); import `create_progress_tracker, progress_queues` from `backend.api.progress_routes` and `run_cli_with_progress` from `backend.api.routes`. FakePopen: `.pid=123`; `.stderr.readline()` yields one `json.dumps({"type":"progress","progress":40,"message":"Paused: 4/10 slots filled","status":"paused","data":{"state_path":"x","grid":[]}}) + "\n"` then `""` (EOF); `.communicate(timeout=...)` returns `(json.dumps({"paused":True,"task_id":"t","slots_filled":4,"total_slots":10}), "")`; `.returncode=0`.
  ```python
  task_id = create_progress_tracker()
  run_cli_with_progress(task_id, ["fill","g.json","--json-output"])
  events, q = [], progress_queues[task_id]
  while not q.empty(): events.append(q.get_nowait())
  statuses = [e["status"] for e in events]
  assert "paused" in statuses
  assert "complete" not in statuses          # DD4: spurious complete suppressed
  ```
  **(e) paused event ends the SSE stream (generator level — what test (d) cannot see):** DD4b. Pre-populate a tracker's queue with a `paused` event followed by a `complete` sentinel, then read the stream. Post-fix the generator breaks on `paused` and never reaches the sentinel; pre-fix it yields `paused` then `complete` (fails fast, no hang). Use the repo's synchronous-SSE convention (`test_pause_resume_workflow.py:107`, `test_sse_message_format.py`).
  ```python
  from backend.api.progress_routes import create_progress_tracker, send_progress
  c, _ = client
  task_id = create_progress_tracker()
  send_progress(task_id, 40, "Paused", "paused", {"state_path":"x"})
  send_progress(task_id, 100, "Complete", "complete", {})     # sentinel: guarantees pre-fix termination → fail-fast
  body = c.get(f"/api/progress/{task_id}").get_data(as_text=True)
  assert '"status": "paused"' in body
  assert '"status": "complete"' not in body                   # DD4b: generator broke on 'paused' first
  ```

- [ ] **Step 2 — Run:** `pytest backend/tests/unit/test_fill_resume_route.py -x -v` — Expected: FAIL (`ModuleNotFoundError: backend.core.state_paths`, then after creating it: `--task-id` absent from argv / 404 not raised / `"complete"` present in statuses / `"complete"` present in stream body).

- [ ] **Step 3 — Implement** DD1-DD5 + DD4b. Order: create `state_paths.py`; add `from backend.core.state_paths import STATE_DIR, PAUSE_FLAG_DIR` to `routes.py`; repoint `pause_resume_routes.py` import (:26-27) + add `pause_dir=PAUSE_FLAG_DIR` (:53,:110); in `fill_with_progress` read `resume_task_id` right after :442 and do the `.exists()`/404 **before** the temp grid write (:477-480), then add the always-on flags + optional `--resume` to `cmd_args` (:507-518); add the paused-terminal branch to `run_cli_with_progress` (:333, before :339); add `"paused"` to the `generate()` break set (`progress_routes.py:157`); single-source dirs in `cli_adapter.fill_with_resume` (no-op if Task 14 added no dir literal). Do NOT touch the stderr passthrough (:305-315 — already correct). Do NOT reach for `pause_resume_routes.py`'s `handle_error(e, default_status=…)` shape.

- [ ] **Step 4 — Run:** `pytest backend/tests/unit/test_fill_resume_route.py -v` — Expected: PASS. Then regression: `pytest backend/tests/ cli/tests/ -q` — Expected: green (watch `test_pause_resume_routes.py` — the `STATE_STORAGE_DIR` alias and added `pause_dir=` kwarg must not break its existing assertions; watch `test_cli_adapter.py:342-412` `TestFillWithResume` for the `fill_with_resume` dir-import change). **Dependency note:** DD2's always-on `--task-id/--state-dir/--pause-flag-dir` are now on every real fill argv — any test that spawns the **real** CLI `fill` hard-requires Task 13/14's options to exist; if Task 15 lands before Task 14, those integration fills Click-exit-2 **by design**, not by bug.

- [ ] **Step 5 — Commit:** `feat(api): resume_task_id on fill/with-progress; unified state/flag dirs; close paused SSE stream`


---


## Task 16 — F11 + F14: frontend pausing sub-state and two-step resume

> **⚠️ Before executing — apply header Cross-section reconciliation notes 2 & 3** (per-task dispatch may not include the header; these OVERRIDE the body below): **(2)** the `useAutofillMachine` return surface is FLAT — expose/read `machine.taskId`/`.progress`/`.conflict`, never `machine.context.*` (and carry the `state`-vs-`status` PROVISIONAL caveat); **(3)** `conflict` is the object `{ slots, details } | null` (Task 18's shape) — store `conflict = { slots: [], details: err.details }`, and **Step-1 test 6 must assert `conflict.details === '…'`, NOT `conflict === '<string>'`.**

*Expands Task 16 of `2026-07-12-m1-constructors-bench.md:600-611`. Binding references (do not restate): State-machine amendments §115-123 (amendments 1/2/3), Authoritative endpoint contracts rows `/api/fill/{pause,resume,with-progress,state}` + `GET /api/progress` (§41-73), Client-side computation policy §96-112. `useAutofillMachine.js` and `src/components/bench/AutofillPanel.jsx` are **created by Task 11** — every citation into their internals is marked `(PROVISIONAL — re-verify against Task 11 output at execution)`. Everything in `src/api/client.js`, `src/api/gridCodec.js`, the backend contracts, and the `MockEventSource` harness is verifiable at HEAD `9e124b2` and cited solidly.*

### Files
- Modify: `src/hooks/useAutofillMachine.js` (PROVISIONAL — Task 11 file) — add the `pausing` sub-state + resume plumbing (DD1-DD3).
- Modify: `src/components/bench/AutofillPanel.jsx` (PROVISIONAL — Task 11 file) — wire Pause/Resume buttons to the new actions + derived labels (Step 3).
- Modify: `src/App.jsx` (PROVISIONAL — Task 11 replaced the autofill lifecycle at the current `src/App.jsx:269-444`) — gate the edit-handler props (`onSetLetter={setLetter}` / `onToggleBlack={toggleBlackSquare}`, at `src/App.jsx:671-672` today) on `canEdit` (DD4/F13).
- **No change:** `src/api/client.js`. `startFill` **already** maps `resumeTaskId → resume_task_id` (`client.js:141-144`, landed in Task 15). The parent Files line "startFill gains `resumeTaskId`" is **stale** — do NOT re-add it. Listed only to record the no-op.
- Test: `src/hooks/__tests__/useAutofillMachine.test.jsx` (extend — created by Task 11); `src/components/bench/__tests__/AutofillPanel.test.jsx` (extend).

### Interfaces

**Consumes (verifiable NOW — cite solidly):**
- `api.pauseFill(taskId)` → `POST /api/fill/pause/<id>` (`client.js:172-174`). 200 means **flag file written, NOT state saved** (contracts §48) — this is why `pause()` resolving enters `pausing`, never `paused`.
- `api.getFillState(taskId)` → `GET /api/fill/state/<id>` (`client.js:187-189`); 200 body `{task_id, timestamp, algorithm, slots_filled, total_slots, grid_size, iteration_count, grid_preview}`, 404 when no state (contracts §51).
- `api.resumeFill({ taskId, editedGrid, options })` → `POST /api/fill/resume` (`client.js:180-185`); 200 `{success, new_task_id:"resume_<8hex>", original_task_id, message, slots_filled, total_slots}`; **409** flat `{error, details}` → `ApiError{status:409, code:"UNSOLVABLE_EDITS", details}` (synthesized at `client.js:63`, `details` from top-level body at `client.js:52`) (contracts §50). **Does NOT start a fill.**
- `api.startFill({ ...options, resumeTaskId })` → `POST /api/fill/with-progress` (`client.js:141-144`); 202 `{task_id, progress_url}`. The returned `task_id` is minted server-side by `create_progress_tracker()` (`backend/api/routes.py:442`) — see DD2 **three-id** rule.
- `api.deleteFillState(taskId)` → `DELETE /api/fill/state/<id>` (`client.js:196-198`).
- `api.openProgress(taskId, { onEvent, onError })` (`client.js:147-170`): wires `source.onmessage` only (`:149-158`), JSON-parses `e.data`, ignores non-JSON; returns an **idempotent** `{ close() }` (`:163-169`). SSE event shape `{progress, message, status:"running"|"paused"|"complete"|"error", timestamp, data?}`; `paused` passes through verbatim (contracts §47). *(This `status` is the SSE **wire** field — distinct from the machine's `state` field below.)*
- `toCliStrings(grid)` (`gridCodec.js:31`) → `string[][]` of `"#"/"."/UPPER` — the resume payload encoding (DD2).
- Test harness: global `MockEventSource` (`src/__tests__/setupTests.js:30-86`): static `MockEventSource.sendMessage(obj)` fans the object (JSON-stringified) to every live instance's `onmessage` (`:54-62`); `close()` only sets `readyState=2` and **keeps delivering** (`:49-51`); instances cleared per-test (`:84-86`). `useToasts().pushToast({kind,message})` surfaces `kind:'error'` as `role="alert"` (convention: `useSaveMachine.test.jsx:127-129`).

**Produces — the Task-16 delta to the Task-11 machine (PROVISIONAL surface).**

> **NAME RECONCILIATION (verify against Task 11 output before writing tests).** Task 11's Interfaces name the machine's current-state field **`state`** (and also expose `reset()` + `errorCard`). This section uses that field name **`state`**; every `result.current.state` / `autofill.state` below is that field. Do **not** confuse it with the SSE **wire** field `status` (§47, `{progress, message, status:"running"|…}`) — the wire `status` stays `status` in every `sendMessage({status:…})` and `evt.status`. If Task 11 actually shipped this field as `status`, swap the **machine accessor** uniformly (and *only* the machine accessor, never the SSE `status`). Task 11's constructor is `useAutofillMachine()` with `start(options)`; Task 16 adds a controlled `grid` input read via `gridRef` at fire time (mirroring useSaveMachine's `docRef`) and gets `pushToast` from an **internal `useToasts()`** — **not** a constructor arg (the tests wrap in `<ToastProvider>` and assert `role="alert"`, which only works with internal useToasts, exactly `useSaveMachine.js:50`).

```
// added states:  'pausing' (sub-state of running), 'paused', and
//                'submitting' reused with an `isResuming` discriminator.
useAutofillMachine({ grid, gridSize, options }) -> {   // pushToast via internal useToasts()
  state,             // Task 11 field name — ... | 'running' | 'pausing' | 'paused' | 'submitting' | 'failed'
  taskId,            // active SSE channel id (running/pausing = the running task; see DD2)
  progress, message, // last SSE tick
  stateInfo,         // canonical getFillState body, populated on entering 'paused' (DD1.4)
  conflict,          // 409 details string while paused after a rejected resume (F15 seam)
  isResuming,        // true ONLY during resume's submitting leg; false during Task 11's
                     // fresh-start submitting — lets the panel show "resuming…" + render Resume (DD2/Step 3)
  canEdit,           // === (state === 'idle' || state === 'paused')  (DD4)
  pause,             // () => void   (NEW)
  resume,            // () => void   (NEW — reads gridRef at fire time; DD2)
  start, cancel, reset,  // Task 11 (reset + errorCard preserved)
}
```
- Labels (AutofillPanel, derived every render like `useSaveMachine`'s `savedLabel`): `state==='pausing'` → Pause disabled + `"pausing…"`; `state==='submitting' && isResuming` → Resume disabled + `"resuming…"` (fresh-start `submitting` shows no Resume button).

### DD1 — `running.pausing` is a *confirmed* sub-state, never entered on the pause 200 (amendment 1)

`POST /api/fill/pause/<id>` returning 200 only means the flag file landed (contracts §48; the running CLI process may not have polled it yet). So `pause()` awaits `api.pauseFill(taskId)` and, on resolve, enters **`pausing`** — a live sub-state of `running`, not `paused`. Confirmation of an actual stop comes from **either**:
- **(A)** an SSE `status:"paused"` event on the still-open running stream (backend Task 15 emits it, then ends the stream **without** `complete`), **or**
- **(B)** a one-shot fallback `getFillState(taskId)` fired at `PAUSE_POLL_MS = 5000`; a 200 means the state file exists on disk = the process stopped.

A ceiling timer `PAUSE_CEILING_MS = 10000` bounds the wait: neither confirmer within 10 s → back to plain **`running`** (the stream never closed — no pause happened server-side) + `pushToast({kind:'error'})`. Timer discipline mirrors `useSaveMachine`'s `clearAutosave`/`armAutosave` ref pattern (`useSaveMachine.js:65-78`): both the 5 s poll and the 10 s ceiling are ref-held and cleared on confirm, on leaving `pausing`, and on unmount; async resolutions guard on `mountedRef` (`useSaveMachine.js:85`).

**SSE events are STATE-guarded, not just close-guarded.** `MockEventSource.close()` keeps delivering (`setupTests.js:49-51`) and real EventSources can deliver a late/reconnect frame after we close ours, so the `onEvent` handler must early-return unless `state ∈ {running, pausing}`:
```
// onEvent(evt): ignore anything once we've left the streaming states.
if (state !== 'running' && state !== 'pausing') return;   // pausing still accepts — that's how "paused" arrives
if (evt.status === 'paused') { confirmPaused(); return; }  // evt.status = SSE wire field
```
This is why a stray `complete` arriving after we reach `paused` is a no-op (Step-1 test 2), and it is genuinely correct, not just a mock artifact.

**`onError` after pause must not read as `failed`** (hazard: on pause the CLI exits, the stream ends, `source.onerror` fires — `client.js:159-161`). Route SSE `onError` to `failed` **only while `state === 'running'`**; in `pausing` it is the expected end-of-stream and is ignored (the 5 s poll / 10 s ceiling govern the outcome).

**On confirming `paused`:** (1) `close()` the machine's `openProgress` connection — amendment 2 says *paused holds no open stream*; (2) cancel both timers; (3) **canonicalize `stateInfo`** — DD1.4.

**DD1.4 — one `stateInfo` shape regardless of confirmer.** The SSE `paused` frame's `data` is thin (`{state_path, grid}`); `getFillState`'s body is rich (`slots_filled/total_slots/algorithm/grid_size/grid_preview`, §51). To hand Task 17 a single shape, on entering `paused` from confirmer **(A)** fetch `getFillState(taskId)` **once** to populate `stateInfo`; confirmer **(B)** already holds that body — use it directly. A failed canonicalizing fetch soft-degrades (keep `progress`/`message` from the last SSE tick; Task 17's restore path re-fetches). This is the same shape the F12 restore-from-idle entry will reuse.

### DD2 — Two-step resume through one `submitting` state, and the **three-id** rule (amendment 3)

`paused --Resume--> submitting(resume) --202--> running{new channel}`. Resume is two real requests under one `submitting` state (buttons disabled, label `"resuming…"`, `isResuming` true); failure of **either** returns to `paused`, **never** `failed`:

1. `api.resumeFill({ taskId: T1, editedGrid: toCliStrings(gridRef.current), options })`. `resume()` reads a `gridRef` updated every render (read-at-fire-time, mirroring `useSaveMachine.js:57,63,83` `docRef`) and applies `toCliStrings` **at this boundary** — so CLI strings (`"#"/"."/UPPER`) reach the wire, **not** the legacy nested `[['A'],['.']]` shape that `AutofillPanel.jsx:126-128` builds today (that encoding is being retired — do not copy it). On 200 → capture `new_task_id` (R1). On **409** → DD-below. On any other error → back to `paused` + error toast.
2. `api.startFill({ ...options, resumeTaskId: R1 })`. On 202 → enter `running` on `startFill`'s **own** returned `task_id`. On error → back to `paused` + error toast.

**Three distinct ids — do not conflate:**
- **T1** = `originalTaskId` — the run that was paused / the state file to delete later (DD3).
- **R1** = `new_task_id` (`"resume_<8hex>"`) from `resumeFill` — used **only** as the `resumeTaskId` body field. It is **not** an SSE channel.
- **T2** = the `task_id` that `startFill`'s 202 returns — minted fresh by `create_progress_tracker()` (`routes.py:442`) and **distinct from R1**. This is the channel the machine tracks as `taskId` and opens `openProgress` on. Opening the resumed stream on R1 instead of T2 is the bug the Step-1 resume test guards against (three distinct fixtures).

Entering `running` on resume reuses Task 11's fresh-start running-entry (opens `openProgress(T2, …)`) — no separate code path; only the entry taskId differs. `isResuming` is cleared on entering `running`.

**409 conflict (F15 seam, rendered by Task 18):** a rejected `resumeFill` with `code:"UNSOLVABLE_EDITS"` must **stay `paused`**, expose `conflict = err.details` on the returned state, and **must not** call `startFill`. Task 16 only surfaces `conflict`; Task 18 parses the `(r,c) dir` list out of it.

### DD3 — Deferred `deleteFillState` — split by failure kind

The old state file (T1) is deleted **only after the resumed run reaches a terminal state on T2's stream**, never eagerly:
- **Pre-launch failure** (`resumeFill` or `startFill` throws) → back to `paused`, **keep** T1's state file (the user can retry / restore). `deleteFillState` is NOT called.
- **Post-launch terminal** (`done` or `failed` on T2's stream) → `api.deleteFillState(T1)`, best-effort (swallow a 404). Carry T1 through `submitting → running` so the terminal transition can fire it.

Rationale: if the resumed run dies immediately, the original solver state is still restorable. `deleteFillState(T1)` firing during `submitting` or on a resume-call reject is a bug the Step-1 tests assert against.

### DD4 — F13 edit lock enforced now

Grid editing is enabled **only** in `idle` and `paused`. The machine exposes `canEdit = (state === 'idle' || state === 'paused')`; App gates the grid edit handlers on it (PROVISIONAL — App's post-Task-11 shape; today the edit-handler props are `onSetLetter={setLetter}` / `onToggleBlack={toggleBlackSquare}` at `src/App.jsx:671-672`, and the autofill lifecycle Task 11 replaces is at `src/App.jsx:269-444`). This is enforced in Task 16 (not deferred to Task 17) because resume ships the **edits made while paused** via `toCliStrings(gridRef.current)`; letting edits land in `running`/`pausing`/`submitting` would desync the grid from the solver mid-flight.

### TDD Steps

Conventions (mirror `useSaveMachine.test.jsx`): `vi.useFakeTimers()`; `renderHook((props) => useAutofillMachine(props), { initialProps, wrapper: ToastProvider })` (the `(props) =>` form so `initialProps` can carry `grid`/`gridSize`/`options`); `vi.spyOn(api, 'startFill'|'pauseFill'|'getFillState'|'resumeFill'|'deleteFillState')`; drive SSE with `global.EventSource.sendMessage({...})` (its `status` key is the wire field); advance with `await act(async () => vi.advanceTimersByTimeAsync(ms))`; error toast asserted via `screen.getByRole('alert')`. Fixtures: `T1='task-orig'`, `R1='resume_ab12cd34'`, `T2='task-new-sse'`. A shared setup drives `start()` (with `startFill` mocked to return `{task_id:T1}`) to reach `running{taskId:T1}`, and the pause flow (test 2/3) to reach `paused{taskId:T1}` where needed.

- [ ] **Step 1 — failing machine tests (eight)** in `useAutofillMachine.test.jsx`. Drive each from a `running{taskId:T1}` (or `paused{taskId:T1}`) start:
  1. **pause → pausing (not paused):** `act(() => result.current.pause())`; flush. Assert `api.pauseFill` called once with `T1`; `result.current.state === 'pausing'`; `result.current.canEdit === false`. SSE not yet sent → state is NOT `'paused'`.
  2. **SSE paused confirms → paused + stream closed + canonicalized:** in `pausing`, mock `api.getFillState.mockResolvedValue({slots_filled:12,total_slots:72,algorithm:'repair',grid_size:[15,15]})`; `global.EventSource.sendMessage({progress:40, status:'paused', message:'Paused: 12/72 slots filled', data:{state_path:'/s/x.json.gz', grid:[]}})`; flush. Assert `result.current.state === 'paused'`, `taskId === T1`, `canEdit === true`, `stateInfo.total_slots === 72` (canonicalized via `getFillState`, DD1.4). Then a **stray** `sendMessage({status:'complete', progress:100})` → `state` stays `'paused'` (state-guard, DD1). `getFillState` called exactly once.
  3. **getFillState fallback confirms → paused (SSE missed):** in `pausing`, send NO SSE; `api.getFillState.mockResolvedValue({slots_filled:5,total_slots:72,...})`; `advanceTimersByTimeAsync(5000)`; flush. Assert `api.getFillState` called once with `T1`; `result.current.state === 'paused'`; `stateInfo.slots_filled === 5` (poll body used directly).
  4. **pausing ceiling → running + toast (F11 10 s):** in `pausing`, `api.getFillState.mockRejectedValue(new ApiError({status:404,code:'HTTP_404'}))`; advance `5000` (poll rejects, still pausing), then to `10000` total; flush. Assert `result.current.state === 'running'`; `screen.getByRole('alert')` present; `api.getFillState` was attempted once (at 5 s).
  5. **resume issues both calls in order, on the three ids, sending CLI strings:** from `paused{taskId:T1}`, set the grid prop to a known letters/blacks layout; `api.resumeFill.mockResolvedValue({success:true, new_task_id:R1, original_task_id:T1})`; `api.startFill.mockResolvedValue({task_id:T2, progress_url:'/p/'+T2})`; `act(() => result.current.resume())`; flush. Assert, in order: `result.current.state` passed through `'submitting'` (with `result.current.isResuming === true` during that leg); `api.resumeFill` called once with `{ taskId:T1, editedGrid: toCliStrings(grid), options }` — assert `editedGrid` deep-equals `toCliStrings(grid)` (a `string[][]` of `"#"/"."/UPPER`), **not** a nested `[['A'],['.']]` shape; `api.startFill` called once **after** resumeFill with `resumeTaskId:R1`; final `result.current.state === 'running'` and `taskId === T2` (the SSE channel is T2, NOT R1); a new `MockEventSource` instance exists for `/api/progress/${T2}`.
  6. **resume 409 → stay paused, no startFill (F15):** `api.resumeFill.mockRejectedValue(new ApiError({status:409, code:'UNSOLVABLE_EDITS', details:'Empty domains for slots: (3,5) across'}))`; `act(() => result.current.resume())`; flush. Assert `result.current.state === 'paused'` (NOT `'failed'`); `api.startFill` **not** called; `result.current.conflict === 'Empty domains for slots: (3,5) across'`; `api.deleteFillState` **not** called.
  7. **resume startFill failure → back to paused, state kept:** `api.resumeFill.mockResolvedValue({new_task_id:R1, ...})`; `api.startFill.mockRejectedValue(new ApiError({status:0, code:'NETWORK'}))`; resume; flush. Assert `result.current.state === 'paused'` (NOT `'failed'`); `screen.getByRole('alert')` present; `api.deleteFillState` **not** called (T1 must survive for retry).
  8. **deferred cleanup fires only on terminal:** complete a happy-path resume (test 5) to `running{taskId:T2}`; assert `api.deleteFillState` NOT called during `submitting` or on entering `running`; then `global.EventSource.sendMessage({status:'complete', progress:100})` on the T2 stream; flush. Assert `api.deleteFillState` called exactly once with **`T1`** (the original, DD3). (Note in a comment: a `failed` terminal fires the same delete.)

  Run: `npx vitest run src/hooks/__tests__/useAutofillMachine.test.jsx` → **FAIL** (`result.current.pause is not a function` / state never `'pausing'`).

- [ ] **Step 2 — implement the machine delta** (DD1-DD3): `pause()`/`resume()` actions, `pausing`/`paused` states + `isResuming` + the two ref-held timers + state-guarded `onEvent`/`onError`, the three-id resume flow, `conflict`, canonical `stateInfo`, deferred `deleteFillState`, `canEdit`. Full body by implementer. Run → all eight pass.

- [ ] **Step 3 — panel + App wiring** (PROVISIONAL — Task 11 files):
  - `AutofillPanel.jsx`: Pause button `onClick={pause}` (disabled + `"pausing…"` when `state==='pausing'`); Resume button visible/enabled only when `state==='paused'`, `onClick={resume}` (disabled + `"resuming…"` when `state==='submitting' && isResuming`). Retire the legacy raw-axios `handlePause`/`handleResume` and the `[['A'],['.']]` encoding (current `src/components/AutofillPanel.jsx:94-164`).
  - `App.jsx` (DD4): `const canEdit = autofill.state === 'idle' || autofill.state === 'paused';` gate `onSetLetter`/`onToggleBlack`.
  - Component tests in `AutofillPanel.test.jsx`: Pause shows `"pausing…"` disabled while `state==='pausing'`; Resume renders only when `state==='paused'`; Resume shows `"resuming…"` disabled while `state==='submitting' && isResuming` (assert fresh-start `submitting` renders no Resume button).

- [ ] **Step 4 — full suite green; commit.** Run: `npx vitest run` → PASS. Commit: `feat(autofill): confirmed pause + two-step resume consuming solver state (F11,F14)`


---


## Task 17 — F12 + F13: saved-state discovery + live edit preview

> **⚠️ Before executing — apply header Cross-section reconciliation notes 2 & 8** (per-task dispatch may not include the header; these OVERRIDE the body below): **(2)** read Task 16's FLAT machine surface — `result.current.taskId`/`.progress`/`.stateInfo`, never `.context.*`; **(8)** populating `stateInfo` with the `{slots_filled, total_slots, grid_size, algorithm}` subset is OK ONLY because the shared paused UI never reads `stateInfo.grid_preview`/`iteration_count` — if that changes, fetch the full `getFillState` body.

> **Expands Task 17 of `docs/superpowers/plans/2026-07-12-m1-constructors-bench.md:615-627`.**
> **Branch:** `feature/m1-constructors-bench` · **HEAD:** `9e124b2` · **Convention:** signatures/contracts/short snippets only — implementer writes full bodies; concrete test assertions are specified.
> **PROVISIONAL surfaces (Task 11 not landed).** `src/hooks/useAutofillMachine.js` does not exist yet (`ls` confirms absent; `useAutofillMachine` appears in **zero** source files). `EventSource` today lives only in `src/api/client.js` (`openProgress`), `src/hooks/useSSEProgress.js` (PatternMatcher-only), and the test doubles `src/__tests__/setupTests.js` + `src/api/__tests__/client.test.js` — **none is the autofill machine.** Every reference below to the machine's **state names** (`idle`/`running`/`paused`), **events** (`RESTORE`), and **context shape** is `(PROVISIONAL — re-verify against Task 11 output at execution)`. `src/App.jsx` autofill-lifecycle spans (`:269-451` = `handleAutofill` 269 → `handleResetAutofill` 451) will have drifted after Task 11 replaces them — re-anchor by grep, not by the line numbers here. Everything backend-contract / `client.js` / `gridCodec` / `Toast` cited below is verifiable NOW and cited solidly.

### Files
- **Create:** `src/components/bench/ResumeCard.jsx`; `src/components/bench/__tests__/ResumeCard.test.jsx`
- **Modify:** `src/hooks/useAutofillMachine.js` (add `RESTORE` transition — PROVISIONAL, created by Task 11); `src/hooks/__tests__/useAutofillMachine.test.jsx` (add restore-entry test — PROVISIONAL); `src/App.jsx` (render `<ResumeCard>`, add `handleRestore`, delete localStorage task-id hints at `App.jsx:447-448`)
- **Test:** `src/components/bench/__tests__/ResumeCard.test.jsx` (new, primary); `src/hooks/__tests__/useAutofillMachine.test.jsx` (one restore-entry test)

### Interfaces

**Consumes (all verified at HEAD `9e124b2`):**
- `api.listFillStates(maxAgeDays)` → `client.js:191-194` → `{states:[…], count}`. Each state is a `get_state_info` dict (`state_manager.py:268-277`, produced per-state by `list_states` at `state_manager.py:321,330`): `{task_id, timestamp, algorithm, version, slots_filled, total_slots, grid_size, iteration_count}` — **no `grid_preview`** (that field is added only by `getFillState`). `algorithm` here is the envelope state-format tag (see DD4), and it **is** present on every list row.
- `api.getFillState(taskId)` → `client.js:187-189` → `{task_id, timestamp, algorithm, slots_filled, total_slots, grid_size, iteration_count, grid_preview}`; `grid_preview` = `saved_state.grid_dict["grid"]` = **`string[][]` of single-char CLI cells** (`pause_resume_routes.py:310`; each cell is one of `'#'`/`'.'`/`'A'`–`'Z'` — `grid.py get_cell:106-129`, assembled row-of-cells by `to_dict:257-276`); 404 `{error:"State not found for task_id: …"}` when the file is gone (`:312-313`).
- `api.editSummary({taskId, editedGrid})` → `client.js:204-206` → `{filled_count, emptied_count, modified_count, new_words[], removed_words[]}` (contracts table, plan:55); 400/404. `editedGrid` MUST be CLI strings.
- `gridCodec.fromCliStrings(rows)` (`gridCodec.js:42-56`) → canonical cell grid; `gridCodec.toCliStrings(grid)` (`gridCodec.js:31-39`) → `string[][]` CLI rows.
- `useToasts()` (`Toast.jsx:90-96`) → `pushToast({kind,message})` (`Toast.jsx:50-58`; `kind:'error'` renders `role="alert"` at `:68`) — used ONLY for the discovery-fetch failure, **never** for per-edit summary errors (DD5).
- Machine restore action + `state`/`context` — Task 11 (PROVISIONAL, see below).

**Produces:**
- `src/components/bench/ResumeCard.jsx` — **named export** (`export function ResumeCard`, matching `ToolRail`/`Toast` convention). Public prop API:
  ```
  <ResumeCard
    active={boolean}                       // machine state === 'idle' → render F12 discovery list; else nothing
    paused={boolean}                       // machine state === 'paused' → render F13 live edit summary
    pausedTaskId={string|null}             // active paused task id (editSummary target)
    grid={cell[][] | null}                 // current (edited) canonical grid — drives the debounced summary
    onResume={({ grid, taskId, progress, stateInfo }) => void}   // App hydrates + fires machine RESTORE
    onStatesLoaded={(states) => void}      // OPTIONAL seam for Task 18 boot cleanup ordering; default no-op
  />
  ```
  ResumeCard **owns its own** `api.listFillStates`/`api.getFillState`/`api.editSummary` calls (DD1). It never imports axios/fetch/EventSource and never starts a fill.
- `src/App.jsx`: `handleRestore(payload)` = `setGrid(payload.grid)` then `machine.restore({ taskId: payload.taskId, progress: payload.progress, stateInfo: payload.stateInfo })`. Renders `<ResumeCard active={machine.state==='idle'} paused={machine.state==='paused'} pausedTaskId={machine.context.taskId} grid={grid} onResume={handleRestore} />` in the Autofill tool region *(PROVISIONAL placement — Task 11 relocates the autofill surface)*.
- `src/hooks/useAutofillMachine.js` (PROVISIONAL): new `restore({taskId, progress, stateInfo})` action → transition `idle → paused`, context `{taskId, progress, stateInfo}`, **opens NO EventSource** (amendment 2).

### DD1 — Ownership split: ResumeCard owns fetches; machine owns the transition; App owns grid hydration
The discovery list, the on-select `getFillState`, and the debounced `editSummary` all live **inside ResumeCard**; the machine gains only the `RESTORE` transition + `paused` context; App only maps `onResume → setGrid + machine.restore`. **Deliberate deviation, named:** `bench/` components are otherwise controlled-by-convention (ToolRail header: *"Fully controlled: no internal state"*). ResumeCard instead follows the **feature-panel precedent** (`PatternMatcher.jsx`, `WordListPanel.jsx` own their API calls) because (a) it minimizes surface specified against the not-yet-built Task-11 machine, and (b) App already owns `grid`/`setGrid`, so hydration must round-trip through App while the fetches need not. Keep the F12 (discovery/idle) and F13 (preview/paused) modes **cleanly separated within the one file** — two prop-gated sections, no shared state between them.

### DD2 — Restore entry: idle→paused, hydrate from `grid_preview`, NO open stream (amendment 2)
Restore = plan amendment 2 (`plan:120`): `idle --saved state discovered--> paused{task_id, progress}`, **invariant: EventSource is open only in `running`** — on pause the CLI process exits, so `paused` holds no stream. So `handleRestore` must NOT call `openProgress`/construct an EventSource. Grid hydration: `fromCliStrings(detail.grid_preview)` (`gridCodec.js:42`; `grid_preview` is `string[][]` CLI cells per `pause_resume_routes.py:310`). `progress` = `total_slots ? Math.round(slots_filled/total_slots*100) : 0`. App does NOT auto-restore — ResumeCard presents cards, the user picks one (avoids clobbering an in-progress new grid). Restore is offered **only from `idle`** (`active` prop) — no dirty-grid clobber-guard here (Task 18 owns confirm/discard).

### DD3 — Two-request discovery: the list has no `grid_preview`; `getFillState` adds it
`listFillStates(7)` returns `get_state_info` dicts only (`state_manager.py:268-277`, one per state via `list_states:321,330`) — enough for the summary rows (slots, age, format) but **no grid**. Selecting a card MUST issue `api.getFillState(taskId)` to obtain `grid_preview` (`pause_resume_routes.py:310`) before offering "Load grid & resume". Do NOT attempt to hydrate a grid from the list payload — the field isn't there. If `getFillState` 404s (state cleaned up between list and select), show an inline "state no longer available" note and drop that row; do not toast, do not crash.

### DD4 — `algorithm` is the state-FORMAT tag, not the solver flag — render it, label it honestly
`get_state_info` returns the envelope `data["algorithm"]` (`state_manager.py:271`), which `save_csp_state` **hardcodes to `"csp"`** (`state_manager.py:153`; Cross-task literals, plan:87). Every web-resumable graceful-stop pause is written through `save_csp_state` (Task 13 reroutes repair/beam pauses through the degenerate-CSPState writer; at HEAD only the classic-CSP engine and the native beam writer exist), so a web-resumable saved state's envelope reads `algorithm:"csp"` regardless of the `--algorithm` flag the user picked. The parent asks the card to show "algorithm" (plan:623), so **render it, but label it as the state format** (e.g. a muted "csp state" / "beam state" chip), NOT as "solver: repair". The real solver flag lives in the saved `metadata["algorithm"]` (fill command records it there, Cross-task literals plan:87) but is **not surfaced** by `get_state_info` (which reads only `metadata.slots_filled`/`total_slots`/`grid_size`, not `metadata.algorithm`) — surfacing it truthfully is a backend change, out of this frontend task's scope (note it as a follow-up). This keeps faith with the parent without printing a misleading solver name.

### DD5 — F13 live edit summary: 400 ms debounce, CLI-strings payload, sticky-last, error-is-inline-not-toast
While `paused`, a debounced effect (400 ms) posts `api.editSummary({taskId: pausedTaskId, editedGrid: toCliStrings(grid)})` on grid change and renders `filled_count/emptied_count/modified_count` + `new_words`/`removed_words` **chips**. Rules:
- **Baseline guard (DD-critical, per advisor B):** entering `paused` must **NOT** fire `editSummary` — the hydrated grid *equals* the saved state, so an entry-fire is a wasted call rendering `{0,0,0}`. Mount-guard the debounce effect so only a *subsequent* edit triggers it (e.g. skip the first effect run / compare against the entry grid). This is asserted in a test.
- **Sticky-last (no spinner, Global Constraint):** keep the previous summary rendered during an in-flight request AND on rejection — never clear to zero.
- **Error surface:** on `editSummary` reject, keep the last chips + a **small inline note** (e.g. `.xw-summary-stale`). **Never `pushToast`** — a per-keystroke toast storm violates spec 08's four-surface rule. (`useToasts` is imported only for the discovery-fetch failure.)
- **Coalescing:** N rapid edits within the 400 ms window → exactly ONE call, carrying the LATEST grid.

### DD6 — Purge localStorage task-id hints (App-scoped)
Server is the source of truth (F12) — delete the `current_autofill_task`/`paused_autofill_task` code paths. **This task owns only `src/App.jsx:447-448`** (`localStorage.removeItem('current_autofill_task')` / `localStorage.removeItem('paused_autofill_task')` inside `handleResetAutofill`, def at `App.jsx:435`). The legacy `src/components/AutofillPanel.jsx` also references these keys (`:49,76,90,105,106,142,181`) but that whole component is replaced by Task 11/16's `bench/AutofillPanel.jsx`; its hints die with that replacement. **Scope the grep-gate to `src/App.jsx` + `src/components/bench/`** — a global `grep -rn "autofill_task" src/` will legitimately still hit the not-yet-removed legacy panel and must not fail this task.

### DD7 — Machine `paused` context parity with Task 16 (PROVISIONAL)
Task 16 defines the `paused` entry as `paused{taskId, progress, stateInfo}` (plan:607) and the `paused` UI is **shared** between Task 16's SSE-entry and this restore-entry. Restore must populate the **same shape**, not a subset — a subset under-populates the shared UI. Fill `stateInfo` from the `getFillState` result: `{slots_filled, total_slots, grid_size, algorithm}`. Mark the exact field names PROVISIONAL (Task 11/16 own the machine), but specify **parity**, not a reduction.

### TDD Steps

- [ ] **Step 1 — Failing ResumeCard tests** in `src/components/bench/__tests__/ResumeCard.test.jsx`. Conventions mirror `useSaveMachine.test.jsx:15,18,32-45` (real `<ToastProvider>` wrapper; `vi.spyOn` on the mocked module — here `vi.spyOn(api, …)`; fake-timer + `vi.restoreAllMocks` teardown) and `ToolRail.test.jsx` (controlled props, text/`role` queries via `render` + `vi.fn()`). Add a **local deferred-promise helper** (this is test code, inline it): `const d=()=>{let r,j;const p=new Promise((res,rej)=>{r=res;j=rej});return{p,r,j}}`. Import `{ api }` from `../../../api/client`, `{ toCliStrings, fromCliStrings }` from `../../../api/gridCodec`, `{ ResumeCard }` from `../ResumeCard`, `{ ToastProvider }` from `../Toast`.

  **Two setup invariants the implementer MUST honor:**
  1. **Wrap EVERY render in `<ToastProvider>`.** `ResumeCard` calls `useToasts()` unconditionally (React hook rule), so an unwrapped render throws `useToasts() must be called within a <ToastProvider>` — including the paused-mode tests (4–8) that never push a toast.
  2. **Enable fake timers ONLY inside the debounce tests (4–8), never in a global `beforeEach`.** Tests 1–3 use async `findBy*`/`findAllBy*` queries that hang under fake timers.

  Eight tests:

  1. **discovery renders one card per state.** `vi.spyOn(api,'listFillStates').mockResolvedValue({ states:[{task_id:'t1',timestamp:new Date(Date.now()-60000).toISOString(),algorithm:'csp',slots_filled:12,total_slots:40,grid_size:[15,15]},{task_id:'t2',timestamp:new Date(Date.now()-9e6).toISOString(),algorithm:'csp',slots_filled:5,total_slots:60,grid_size:[15,15]}], count:2 })`. Render `<ResumeCard active paused={false} grid={null} onResume={vi.fn()} />` in the `ToastProvider` wrapper. Assert `api.listFillStates` called with `7`; `await screen.findAllByTestId('resume-card-row')` length `2`; row 1 shows text `12/40`.
  2. **empty states renders nothing** (empty-list path). `listFillStates` resolves `{states:[],count:0}`; assert `screen.queryByTestId('resume-card-row')` is `null` and no discovery container heading is rendered.
  3. **select → getFillState → onResume with hydrated grid + parity payload.** One state `t1`. `vi.spyOn(api,'getFillState').mockResolvedValue({ task_id:'t1', slots_filled:2, total_slots:9, grid_size:[3,3], algorithm:'csp', grid_preview:[['C','A','T'],['.','.','.'],['#','.','#']] })`. `onResume=vi.fn()`. Click row `t1` → assert `api.getFillState` called with `'t1'`. Click "Load grid & resume" → assert `onResume` called once with `{ taskId:'t1', progress:22, stateInfo:{slots_filled:2,total_slots:9,grid_size:[3,3],algorithm:'csp'}, grid: <g> }` where `g[0][0].letter==='C'`, `g[2][0].isBlack===true`, `g[1][0].letter===''` (i.e. `g` deep-equals `fromCliStrings(grid_preview)`). (`progress = round(2/9*100) = 22`.)
  4. **live summary: entering paused does NOT fire editSummary (baseline guard, DD5).** `vi.useFakeTimers()`. `const es=vi.spyOn(api,'editSummary')`. Render `<ResumeCard active={false} paused pausedTaskId="t1" grid={gridA} onResume={vi.fn()} />` in the wrapper. `await act(()=>vi.advanceTimersByTimeAsync(400))`. Assert `es.not.toHaveBeenCalled()`.
  5. **live summary: an edit debounces 400 ms into one CLI-strings call + chips.** Mount paused at `gridA` (as in Test 4); `es.mockResolvedValue({filled_count:3,emptied_count:1,modified_count:0,new_words:['CAT'],removed_words:[]})`. `rerender` with `grid=gridB` (gridB = gridA with one letter changed). Assert `es` not called before advance; `await act(()=>vi.advanceTimersByTimeAsync(400))`; assert `es` `toHaveBeenCalledTimes(1)` with `{ taskId:'t1', editedGrid: toCliStrings(gridB) }`; assert `screen.getByText('CAT')` and the filled-count `3` are rendered.
  6. **coalesce:** rerender `gridB→gridC→gridD` within one 400 ms window; advance 400 ms; assert `es` `toHaveBeenCalledTimes(1)` and its `editedGrid` deep-equals `toCliStrings(gridD)` (latest wins).
  7. **sticky-last during flight:** first edit resolves counts A (rendered, assert `getByText('CAT')`); second edit's `editSummary` returns a pending deferred `d().p`; advance the debounce; assert the A chips are **still on screen** while the deferred is unresolved (not cleared to `0/0/0`).
  8. **reject → keep last + inline note, NO toast:** after A is rendered, next `editSummary` rejects (`es.mockRejectedValueOnce(...)`); advance; assert A chips still present; assert an inline note element (`screen.getByTestId('summary-stale')` or text matching `/couldn.?t update|preview unavailable/i`); assert `screen.queryByRole('alert')` is `null` (pushToast never fired for a summary error).

  Run: `npx vitest run src/components/bench/__tests__/ResumeCard.test.jsx` → **Expected: FAIL** (`Failed to resolve import "../ResumeCard"`).

- [ ] **Step 2 — Failing machine restore-entry test** (PROVISIONAL — only if Task 11 has landed `useAutofillMachine.js`; else defer this test into Task 11's suite and note it) in `src/hooks/__tests__/useAutofillMachine.test.jsx`. Uses the global `MockEventSource` from `src/__tests__/setupTests.js:30` (auto-cleared each test via `clearInstances()` at `:85`; instances array pushed at `:39`, reset at `:75`; `global.EventSource = MockEventSource` at `:81`).
  - **RESTORE from idle → paused, no stream opened.** `renderHook(() => useAutofillMachine(<deps>))`; `act(() => result.current.restore({ taskId:'t1', progress:22, stateInfo:{slots_filled:2,total_slots:9} }))`. Assert `result.current.state === 'paused'`; `result.current.context.taskId === 't1'`; `result.current.context.progress === 22`; **`global.EventSource.instances.length === 0`** (amendment 2 — paused holds no open stream).

  Run: `npx vitest run src/hooks/__tests__/useAutofillMachine.test.jsx` → **Expected: FAIL** (no `restore` action).

- [ ] **Step 3 — Implement.**
  - `ResumeCard.jsx`: named export; two prop-gated sections. **F12 (idle):** on mount effect (when `active`) → `api.listFillStates(7)`, call `onStatesLoaded(states)`, render a row per state (slots `slots_filled/total_slots`, relative age from `timestamp`, format chip per DD4); on row click → `api.getFillState(taskId)` (DD3), reveal preview + a button that calls `onResume({ grid: fromCliStrings(detail.grid_preview), taskId, progress, stateInfo })` (DD2). Button label enters `paused` ONLY — no `startFill`/`resumeFill` here (that is Task 16's two-step Resume); pick a label that does not imply a fill starts (e.g. "Load grid to edit"). Discovery-fetch failure → `pushToast({kind:'error',…})`. **F13 (paused):** debounced (400 ms) `editSummary` effect per DD5 (mount-guarded baseline), chips + inline stale-note.
  - `useAutofillMachine.js` (PROVISIONAL): add `restore({taskId,progress,stateInfo})` → `idle→paused` with full context parity (DD7), no EventSource.
  - `App.jsx`: add `handleRestore`, render `<ResumeCard>` (see Interfaces), and **delete `App.jsx:447-448`** (`localStorage.removeItem('current_autofill_task'|'paused_autofill_task')`) per DD6.

- [ ] **Step 4 — Green + scoped grep-gate.**
  - `npx vitest run src/components/bench/__tests__/ResumeCard.test.jsx src/hooks/__tests__/useAutofillMachine.test.jsx` → **Expected: PASS.**
  - `npx vitest run` → full frontend suite green.
  - `grep -rn "autofill_task" src/App.jsx src/components/bench/` → **Expected: no output** (DD6-scoped; the legacy `src/components/AutofillPanel.jsx` is intentionally excluded — Task 16 removes it).

- [ ] **Step 5 — Commit** — `feat(autofill): server-side paused-state discovery + live edit summary (F12,F13)`


---


## Task 18 — F15 + F16: 409 conflict recovery + honest discard/cancel + boot cleanup

> **⚠️ Before executing — apply header Cross-section reconciliation notes 2, 3, 4** (per-task dispatch may not include the header; these OVERRIDE the body below): **(2)** Task 16's machine surface is FLAT — no `context.*` (read `machine.conflict` directly); **(3)** `conflict` is the object `{ slots, details }` (this section's shape wins; Task 16 stores it and Step-1 test 6 asserts `conflict.details`); **(4)** expose cancel/discard as action methods (`cancel()` extended in place + new `discard()`), not dispatched `RESUME_CONFLICT/DISCARD/CANCEL` events — that phrasing is pseudocode.

> Expands Task 18 of `docs/superpowers/plans/2026-07-12-m1-constructors-bench.md:631-641`. **Branch:** `feature/m1-constructors-bench` · **HEAD:** `9e124b2`.
> **Convention:** signatures/contracts/short snippets only — the implementer writes full bodies. Test steps carry concrete assertions.
> **Binding refs (do not restate):** Authoritative endpoint contracts (`…bench.md:35-73`, esp. cancel `:49`, resume-409 `:50`); State-machine amendments (`…bench.md:115-123`, esp. §1 confirmed-stop window, §3 resume-via-`submitting`); Client-side computation policy (`…bench.md:96-112` — slot-extent geometry is *granted*, fill/validity is *denied*); Error surfaces (Global Constraints §"Error surfacing — four surfaces only", `…bench.md:24` — "No `alert()`, no modals-for-errors, no console-only errors"; a `window.confirm` is a modal-for-errors and is therefore banned).

### Scope boundary (read first)
Task 18 **enriches** the `paused` payload and adds three terminal edges (`RESUME_CONFLICT`, `DISCARD`, `CANCEL`) — it does **not** re-declare the `409 → stay paused (never failed)` transition, which amendment §3 and **Task 16 Step 1** already own. Frame DD1 as extending Task 16's resume action. The legacy path — `AutofillPanel.jsx` `window.confirm` (`:167`) and its 409-as-toast (`:151-159`) — is the pattern being **superseded** by the bench components (Task 11/16); it is **not** in this task's Modify list. Likewise App.jsx's HEAD autofill/cancel lifecycle (`handleAutofill`/`handleCancelAutofill`/`eventSourceRef`) is **removed by Task 11** — see the Files note.

### Files
- **Modify:** `src/hooks/useAutofillMachine.js` *(created Task 11 — internals PROVISIONAL, re-verify at execution)*; `src/components/bench/ResumeCard.jsx` *(created Task 17 — PROVISIONAL)*; `src/App.jsx` — Task-18 edits are the `conflict.slots`→`isError` effect (beside the existing verify-words `isError` writer `:472-476`, which is untouched by Task 11) and the once-guarded boot `cleanupFillStates(7)`. **Note:** the HEAD cancel handler `handleCancelAutofill` (`:407-433`, closing the SSE at `:411-415`) is **deleted by Task 11** (F3 — "cancel in 11" per `…bench.md:752`, which folds App's whole EventSource lifecycle into the machine); Task 18's cancel-honesty logic therefore lands in the machine's `CANCEL` transition (PROVISIONAL), **not** in App.jsx. Those HEAD line numbers appear below only as the anti-pattern DD3 corrects.
- **Test:** `src/hooks/__tests__/useAutofillMachine.test.jsx`, `src/components/bench/__tests__/ResumeCard.test.jsx` (extend Task 11/17 files). Pure-helper tests co-located with the machine module.

### Interfaces
- **Consumes (all verifiable NOW):**
  - `api.resumeFill({taskId, editedGrid, options})` — `client.js:180-185`. On 409 the client throws `ApiError{status:409, code:'UNSOLVABLE_EDITS', details}` — code synthesized at `client.js:62-63`, `details` lifted from the flat body's top-level key at `client.js:52`. Backend 409 body: `{error:"User edits create unsolvable configuration", details}` (`pause_resume_routes.py:221-222`).
  - `api.cancelFill(taskId)` — `client.js:176-178`. Returns `{…, state_saved:true}` **hardcoded** (`pause_resume_routes.py:129`); the route writes the pause flag (`:114`) *and* hard-kills the subprocess as a fallback (`cleanup_process`, `:117-119`) — so a saved state is a **race**, never a guarantee.
  - `api.getFillState(taskId)` — `client.js:187-189` (200 body or `ApiError{status:404}`).
  - `api.deleteFillState(taskId)` — `client.js:196-198`.
  - `api.cleanupFillStates(maxAgeDays=7)` — `client.js:200-202`.
  - Geometry: `allSlots(grid) -> {across, down}` (`useGridGeometry.js:82-103`); each slot is `slotAt(...)` output carrying `.cells` (start = `cells[0]`). Cell `isError` is a real rendered field (`bench/CrosswordGrid.jsx:405,411`; canonical default `App.jsx:114`, `gridCodec.js:19`).
  - `useToasts().pushToast({kind, message})` — `bench/Toast.jsx:50-58,90-96`.
- **Produces (pure, testable standalone):**
  ```js
  // src/hooks/useAutofillMachine.js  (named export)
  export function parseConflictSlots(details) { /* -> [{ row:number, col:number, direction:'across'|'down' }] */ }
  ```

---

### DD1 — 409 recovery: parse → mark → banner, extend Task 16's resume action (F15)
The resume action added in Task 16 issues `api.resumeFill(...)`. Task 18 adds a `catch` that recognizes the 409 (`err.status===409 || err.code==='UNSOLVABLE_EDITS'`), runs `parseConflictSlots(err.details)`, and lands back in `paused` with an enriched context — a **self-transition** `paused → paused{conflict}` (never `failed`, per amendment §3). Resume stays **enabled** for retry; the resume card stays open with an inline conflict banner (surface is the card, not a toast — the legacy toast at `AutofillPanel.jsx:154-157` loses positional context; we mark the actual cells instead).

```js
// paused context gains:  conflict: { slots: [{row,col,direction}], details: string } | null
```

**Three traps folded in (advisor + facts sheet):**
1. **Shared-global-regex `lastIndex` trap.** `parseConflictSlots` MUST use `String.prototype.matchAll(/\((\d+),\s*(\d+)\)\s+(across|down)/g)`. `matchAll` clones the regex internally, so a module-level `/…/g` constant is safe with it — the drift hazard is real only for a **shared global regex driven by `.test()`/`.exec()`** (each call mutates `lastIndex` and silently drops matches on alternate invocations); do not implement it that way. `\s*` after the comma is load-bearing — `edit_merger.py:356` emits `(3,5) across` with **no space after the comma**.
2. **Backend caps at 3.** `edit_merger.py:353` slices `empty_domains[:3]`. The banner reports the **parsed count** honestly ("N conflicting slot(s)") and must not imply completeness.
3. **`isError` has a second writer.** `App.jsx:472-476` already sets `cell.isError` from the verify-words pass. Marking is done by an App effect keyed on `conflict.slots`: for each `{row,col,direction}`, find the slot in `allSlots(grid)[direction]` whose `cells[0]` equals `[row,col]` and set `.isError` on every `slot.cells`; **fallback** — if no slot matches (CLI start-convention drift), mark the origin `(row,col)` cell alone rather than no-op. On the next Resume attempt, clear `isError` **only on the previously-conflict-marked cells** (track them; never a grid-wide `isError:false` reset — that would clobber the validation writer).

---

### DD2 — Honest discard: bespoke inline two-step confirm (F16)
The four-surfaces error rule (`…bench.md:24`) forbids `window.confirm`/modals. Replace the legacy `confirm('Discard paused state?…')` (`AutofillPanel.jsx:167`) with an **inline two-step affordance inside `ResumeCard`** — matches the no-portal Toast philosophy (`bench/Toast.jsx:12-13`), stays RTL-testable, adds no global dialog component. Local `confirming` state: Discard → renders `.xw-confirm` row (`Confirm` / `Cancel`); `Confirm` → `api.deleteFillState(taskId)` → machine `DISCARD` → `idle`; `Cancel` → back to the plain card, `deleteFillState` **not** called. `deleteFillState` rejection → red toast (surface #2), card stays.

---

### DD3 — Honest cancel: confirmed-stop that lands in `idle`, then probe (F16)
Cancel is **"pause, then land in `idle` instead of `paused`."** The HEAD handler (`App.jsx:411-415`, within `handleCancelAutofill` `:407-433`) closes the SSE *immediately* then fires cancel — fatal here: the flag-driven save (`pause_resume_routes.py:114`) is **async**, so an immediate `getFillState` 404s nearly always and the "saved state available" branch is dead. Because the route *also* hard-kills (`:117-119`), the save genuinely may not land — this is exactly what the contract's "treat `state_saved` as unverified" warns about. *(This HEAD handler is **deleted by Task 11**; it is shown only as the anti-pattern. Task 18's cancel edit lands in the machine's `CANCEL` transition, below.)*

`CANCEL` from `running` therefore **reuses amendment §1's confirmed-stop window** (keep the SSE open; resolve on the terminal `status:"paused"` SSE event, a `getFillState` 200 fallback poll, an SSE `onerror`/stream-end from the kill, or the ~10 s timeout — whichever first). On resolution: close the SSE, run **one** `getFillState(taskId)` probe →
- **200** (graceful save won the race) → `idle` **and** refetch `api.listFillStates(7)` so the just-saved state resurfaces as a Task-17 resume card (the passive "saved state available" affordance).
- **404** (kill won) → **plain `idle`**, no refetch, no card.

End state is always `idle` — never `paused`, never `failed`. During the window, any late `complete`/`error` SSE event is ignored (funnels to the same probe-then-idle resolution). *(Machine state/event names PROVISIONAL — re-verify the `running` sub-state surface against Task 11.)*

---

### DD4 — Boot cleanup: once, after the list, silent (F16)
`api.cleanupFillStates(7)` fires **once** on app mount, **after** Task-17's `listFillStates(7)` resolves (so the visible list is unaffected by the concurrent delete). Housekeeping only: swallow errors to `console.warn` (**no toast** — a failed cleanup is not a user-facing error, `…bench.md:24`). Guard with a `useRef` once-flag so React 18 StrictMode's double-mount fires it a single time.

---

### TDD Steps

- [ ] **Step 1 — failing tests.**

  **`parseConflictSlots` (pure — fully verifiable now):**
  ```js
  it('parses multi-slot details incl. zero-space-after-comma', () => {
    const details =
      'User edits create unsolvable configuration: Empty domains for slots: (3,5) across, (7,2) down';
    expect(parseConflictSlots(details)).toEqual([
      { row: 3, col: 5, direction: 'across' },
      { row: 7, col: 2, direction: 'down' },
    ]);
  });
  it('is repeatable — no shared-regex lastIndex drift', () => {
    const d = 'Empty domains for slots: (0,0) across, (1,1) down';
    const a = parseConflictSlots(d);
    expect(a).toHaveLength(2);
    expect(parseConflictSlots(d)).toEqual(a); // repeat call must not drop the 2nd match
  });
  it('returns [] when no tokens present', () => expect(parseConflictSlots('boom')).toEqual([]));
  ```

  **409 → paused{conflict}, never failed** (machine; PROVISIONAL event names):
  ```js
  // running→paused; dispatch RESUME; vi.spyOn(api,'resumeFill').mockRejectedValue(
  //   new ApiError({ status:409, code:'UNSOLVABLE_EDITS',
  //     details:'... (3,5) across, (7,2) down' }));
  // await; assert state==='paused' (NOT 'failed'); context.conflict.slots deep-equals the parse;
  //   Resume remains enabled; api.startFill NOT called (no second-step fill on conflict).
  ```

  **isError mark + scoped clear** (geometry verifiable now):
  ```js
  // conflict.slots=[{row:0,col:0,direction:'across'}] on a grid whose (0,0)-across slot spans
  //   (0,0),(0,1),(0,2): after the effect those 3 cells .isError===true, others false.
  // fallback: slot absent -> only (row,col) marked.
  // pre-mark (1,1).isError=true via the validation writer; dispatch RESUME (retry):
  //   the prior conflict cells clear to false, (1,1) stays true (scoped clear, not grid-wide).
  ```

  **Discard confirm (no window.confirm):**
  ```js
  const spy = vi.spyOn(window, 'confirm');
  // render ResumeCard; click Discard -> .xw-confirm visible, api.deleteFillState NOT called;
  //   click Cancel -> affordance gone, still paused, deleteFillState NOT called;
  //   click Discard -> Confirm -> api.deleteFillState called once with taskId -> state 'idle'.
  expect(spy).not.toHaveBeenCalled();
  ```

  **Cancel probe — 200 vs 404** (fake timers + MockEventSource; PROVISIONAL):
  ```js
  // (200) running w/ open SSE; dispatch CANCEL -> api.cancelFill(taskId) once; emit SSE
  //   {status:'paused'}; getFillState resolves 200 -> state 'idle', api.listFillStates refetched,
  //   SSE closed.
  // (404) same, but getFillState rejects ApiError{status:404} after the confirmed-stop window
  //   (advanceTimersByTimeAsync(10000)) -> state 'idle', listFillStates NOT refetched, SSE closed.
  ```

  **Boot cleanup once + silent:**
  ```js
  // mount App under StrictMode (double render); after listFillStates resolves,
  //   api.cleanupFillStates called exactly once with 7.
  // cleanup rejection -> console.warn called, pushToast NOT called.
  ```

- [ ] **Step 2 — run (expect red).** `npx vitest run src/hooks/__tests__/useAutofillMachine.test.jsx src/components/bench/__tests__/ResumeCard.test.jsx` → FAIL (`parseConflictSlots is not a function`; unknown events `RESUME_CONFLICT`/`DISCARD`/`CANCEL`).

- [ ] **Step 3 — implement** DD1–DD4. Machine: `parseConflictSlots` export, the 409 `catch` extending Task 16's resume action, `DISCARD`→idle, `CANCEL`→confirmed-stop→idle(+probe) — this `CANCEL` transition is where the cancel-honesty logic lives (the HEAD `handleCancelAutofill` was already removed by Task 11). `ResumeCard`: inline two-step confirm + conflict banner (parsed count, honest about the 3-slot cap). `App.jsx`: add the `conflict.slots`→`isError` effect with scoped clear beside the existing verify-words writer (`:472-476`, untouched by Task 11); wire the once-guarded boot `cleanupFillStates(7)` after the Task-17 list.

- [ ] **Step 4 — green + full suite.** `npx vitest run src/hooks/__tests__/useAutofillMachine.test.jsx src/components/bench/__tests__/ResumeCard.test.jsx` → PASS, then `npx vitest run` green.

- [ ] **Step 5 — commit** — `feat(autofill): conflict recovery + honest cancel/discard semantics (F15,F16)`


---


## Task 19 — E2E gate: real-subprocess pause→edit→resume + pattern through Flask

### Files
- **Create:** `backend/tests/integration/test_pause_resume_e2e.py`
- **Reuse (no change):** `backend/tests/integration/conftest.py` — the `client` fixture (conftest.py:11-17, auto-injected by param name: `create_app()` + `app.config["TESTING"]=True`) and the **module-level helper** `create_test_grid(size)` (conftest.py:43). Note `create_test_grid` is a plain function, **not** a fixture — the test file must **import** it: `from backend.tests.integration.conftest import create_test_grid` (same pattern as `sse/test_sse_message_format.py:20`).
- **Test:** this file *is* the test — the batch gate proving Tasks 13–15 with **zero mocks**. Marked `@pytest.mark.slow`.

**Meta-rule (binding, from parent §Task 19):** if this fails, fix Tasks 13–15 — **never weaken the test.** Use `superpowers:systematic-debugging`, not test-weakening.

### Interfaces
- **Consumes (real HTTP, no mocks — all contracts from §"Authoritative endpoint contracts"):**
  - `POST /api/fill/with-progress {size, grid, wordlists?, algorithm?, timeout?, min_score?, resume_task_id?}` → `202 {task_id, progress_url}`. Grid is **frontend `{letter, isBlack}` dict cells** — the route converts to CLI strings itself (`backend/api/routes.py:462-475`).
  - `POST /api/fill/pause/<task_id>` (id in **path**) → `200 {success, message, task_id}` (route `pause_resume_routes.py:30-31`, body `:63-65`; 200 = flag written, not state saved — §State-machine amendment 1).
  - `GET /api/fill/state/<task_id>` → `200 {task_id, timestamp, algorithm, version, slots_filled, total_slots, grid_size, iteration_count, grid_preview}` | `404` (route `pause_resume_routes.py:268`; `grid_preview = saved_state.grid_dict["grid"]` = **CLI strings**, `:310`).
  - `POST /api/fill/resume {task_id, edited_grid?}` → `200 {success, new_task_id:"resume_<8hex>", original_task_id, message, slots_filled, total_slots}` | `409` (route `pause_resume_routes.py:141`, `new_task_id` minted `:235`, body `:251-262`; does **not** start a fill — §amendment 3).
  - `POST /api/fill/cancel/<task_id>` (`pause_resume_routes.py:76`), `DELETE /api/fill/state/<task_id>` (`:320`) — teardown only.
  - `POST /api/pattern {pattern, wordlists?}` → `200 {meta, results:[{word, score, source, length, letter_quality}]}` (route returns the CLI JSON verbatim, `routes.py:87`; `results[]`, singular `source`).
- **Produces:** two `@pytest.mark.slow` tests — `test_pause_edit_resume_roundtrip` and `test_pattern_through_flask` — plus a poll helper `_await_state(client, task_id, deadline_s=10)` (returns the state JSON on the first 200, else fails).

### DD1 — Real Flask + real CLI subprocess, zero mocks
Use the conftest `client` fixture (auto-injected; `create_app()` then `app.config["TESTING"]=True` — equivalent to the parent scenario's `create_app(testing=True)`). Do **not** patch `subprocess`, `StateManager`, `PauseController`, or `run_cli_with_progress`. A real `/api/fill/with-progress` spawns a real `python -m cli.src.cli fill …` subprocess (`routes.py:246` `run_cli_with_progress` → `Popen`), which is the *only* thing that exercises the Task 13/14 CLI wiring and the Task 15 shared-dir argv. Module-level `pytestmark = pytest.mark.slow`; the file is excluded from the default run (`pytest.ini` `addopts = -v -m "not slow"`) and only collected under `-m slow`.

### DD2 — Distinct from the in-process `test_e2e_pause_resume.py` (name-collision guard)
A file named `test_e2e_pause_resume.py` **already exists** (`backend/tests/integration/test_e2e_pause_resume.py:29`, `TestEndToEndPauseResume`) — it constructs `BeamSearchOrchestrator`/`StateManager` **in-process** and never touches Flask. Task 19's file is the near-homonym `test_pause_resume_e2e.py` and is the **HTTP-through-Flask** gate. **Do not** merge into, subclass, or import fixtures/word-lists from the in-process file; **do not** rename either file. They coexist on purpose: one proves the algorithm classes, this one proves the wiring.

### DD3 — Grid, algorithm, and the two grid encodings
Blank **15×15** frontend-format grid via `create_test_grid(15)` (rows of `{"letter":"", "isBlack":False}`), `algorithm:"trie"`, `timeout:120`, `wordlists:["comprehensive"]`. `trie` = classic-CSP `Autofill` (§Cross-task literals — there is no `csp` flag value; `cli.py:118` Choice is `regex/trie/beam/repair/hybrid`); this is the **exact-position** path that writes a real `CSPState` (non-empty `domains`) via `save_csp_state`, which is exactly what the resume route's `load_csp_state` → `EditMerger.merge_edits` round-trips. Two encodings appear and both are correct:

| Wire field | Encoding | Why |
|---|---|---|
| `grid` on `/api/fill/with-progress` | frontend `{letter,isBlack}` dicts | route converts (`routes.py:462-475`) |
| `edited_grid` on `/api/fill/resume` | **CLI strings** (`"#"`/`"."`/`"A"`) | resume wraps as `{size:len, grid}` and feeds `EditMerger.merge_edits` → `Grid.from_dict` (`pause_resume_routes.py:208-211`; `Grid.from_dict` is inside `merge_edits`) |

`grid_preview` from `GET /api/fill/state` is *already* CLI strings, so it drops straight into `edited_grid` with no conversion. The graceful-stop degenerate-CSPState path (repair/beam) is deliberately **out of this gate** — it is covered at the CLI level by Task 13 Test C.

### DD4 — What this gate proves (and what it deliberately does not) + debug map
Because the test polls `GET /api/fill/state` rather than draining SSE, it validates: (a) the **pause-flag-dir + state-dir chain** — the backend pause route writes `<PAUSE_FLAG_DIR>/crossword_pause_<task_id>.flag` **and** the spawned fill argv carries the matching `--pause-flag-dir`/`--state-dir` (Task 15 `state_paths.py`), so the running CLI actually *sees* the flag and writes state where `STATE_STORAGE_DIR` (`= backend/data/autofill_states`, `pause_resume_routes.py:26`) reads it; and (b) the resume-route round-trip (`load_csp_state` → `merge_edits` → new `resume_<hex>` state). It does **not** exercise the SSE `paused`/no-spurious-`complete` terminal branch — that is owned by **Task 15 Step 1(d)**'s mocked-Popen unit test. Do not "strengthen" this gate by adding blocking SSE consumption (`collect_sse_messages` blocks until stream end); the on-disk state file is written by the CLI subprocess in `_handle_pause` (`autofill.py:1173`) independent of any SSE consumer.

**If step 3 times out or 404s, the failure is upstream — debug in this order (never the test):**
1. `_await_state` never sees 200 → the CLI never paused. Check Task 13: the `fill` command constructs `PauseController(task_id, pause_dir=…)` and threads `task_id=` into `fill()` (at HEAD it does neither — `routes.py`-spawned fills pass no `--task-id`, so pause is a no-op; this is why the gate is legitimately RED at HEAD).
2. State 404s though the CLI paused → **split dir** (the exact severance this gate exists to catch): CLI wrote `/tmp/crossword_states/…` but the route reads `backend/data/autofill_states`. Check Task 15 `state_paths.STATE_DIR == STATE_STORAGE_DIR` and that `--state-dir` is on the argv.
3. Pause 200 but no state ever → **flag-dir mismatch**: the route wrote the flag to a dir the CLI subprocess wasn't told to watch (`--pause-flag-dir`). Check Task 15 `PAUSE_FLAG_DIR` on both sides.

### DD5 — Determinism: timing, unmodified edit, re-runnability
- **Timing (flake guard):** `time.sleep(3)` before pausing so the CSP is still backtracking when the flag lands. The CSP polls `should_pause()` every 100 iterations (`autofill.py:847`,`:853`); a blank 15×15 `trie` fill at `timeout:120` is comfortably still running at t+3 s (empirically, a blank open 15×15 trie fill runs the full clock — it does not exit early). The step-3 poll deadline is exactly **10 s** — this deadline **is** the F11 `running.pausing` guarantee (§amendment 1); assert a 200 *arrives within 10 s*, not merely eventually. 10 s clears the next `%100` pause checkpoint with margin.
- **Unmodified edit (avoid the 409):** pass `state["grid_preview"]` **verbatim** as `edited_grid`. `EditMerger.merge_edits` still runs (it is not short-circuited on a zero diff), but an unchanged grid introduces **no new empty domains**, so a state that was solvable at save stays solvable and the route returns 200 — `merge_edits` only raises when edits *create* unsolvability (`edit_merger.py:350-361`, gated on `has_domains`). The 409 recovery path is Task 18's unit responsibility, not this gate.
- **Teardown (the gate must be cheaply re-runnable):** step 5 spawns a second real fill (`resp2.json["task_id"]`, `timeout:120`) that would otherwise orphan a ~2-min subprocess and leave flag/state files in the *shared* dirs. Wrap the body in `try/finally` (or an autouse teardown) that: `POST /api/fill/cancel/<resp2 task_id>`; `DELETE /api/fill/state/<original task_id>` and `<new_task_id>` (ignore 404); and unlink the pause flag. Teardown touches no assertion.

### TDD Steps

- [ ] **Step 1: Write the two tests** (the scenario is binding; the executing agent writes the pytest bodies).

  **Module imports** (top of file): `import time`, `import pytest`, and `from backend.tests.integration.conftest import create_test_grid`. Module-level `pytestmark = pytest.mark.slow`. (`client` needs no import — it is a conftest fixture injected by param name.)

  **`_await_state(client, task_id, deadline_s=10)`** — poll `GET /api/fill/state/<task_id>` every 0.5 s until `time.monotonic()` passes the deadline; return `resp.get_json()` on the first `status_code == 200`; return `None` on timeout.

  **`test_pause_edit_resume_roundtrip(client)`** (blank 15×15, `algorithm:"trie"`, exact-position CSP):
  1. `resp = client.post("/api/fill/with-progress", json={"size":15,"grid":create_test_grid(15),"wordlists":["comprehensive"],"algorithm":"trie","timeout":120,"min_score":10})` → `assert resp.status_code == 202`; `task_id = resp.get_json()["task_id"]`; `assert task_id`.
  2. `time.sleep(3)`; `p = client.post(f"/api/fill/pause/{task_id}")` → `assert p.status_code == 200`; `assert p.get_json()["success"] is True`.
  3. `state = _await_state(client, task_id, 10)` → `assert state is not None, "no saved state within the 10s F11 deadline — debug Tasks 13/15, not the test"`; `assert "grid_preview" in state`; `assert state["total_slots"] > 0` (real value: `_handle_pause` writes `total_slots` into metadata at `autofill.py:1165`, so `get_state_info` surfaces it, not its `.get(...,0)` default — 30 for a blank open 15×15); `assert state["algorithm"] == "csp"` (envelope state-format tag, `state_manager.py:271`→hardcode `:153`; a 200 already implies `load_csp_state` validated it, `:210-211`).
  4. `r = client.post("/api/fill/resume", json={"task_id":task_id,"edited_grid":state["grid_preview"]})` → `assert r.status_code == 200`; `new_task_id = r.get_json()["new_task_id"]`; `assert new_task_id.startswith("resume_")`.
  5. `resp2 = client.post("/api/fill/with-progress", json={"size":15,"grid":create_test_grid(15),"wordlists":["comprehensive"],"algorithm":"trie","timeout":120,"min_score":10,"resume_task_id":new_task_id})` → `assert resp2.status_code == 202`; `assert resp2.get_json()["task_id"]`.
  6. **teardown** (`finally`): cancel `resp2`'s task, `DELETE` state for `task_id` and `new_task_id`, clear the pause flag (per DD5).

  **`test_pattern_through_flask(client)`:**
  - `resp = client.post("/api/pattern", json={"pattern":"C?T","wordlists":["comprehensive"]})` → `assert resp.status_code == 200`; `data = resp.get_json()`; `assert data["results"]` (non-empty); `first = data["results"][0]`; `assert "word" in first and "source" in first`; `assert len(first["word"]) == 3 and first["word"][0] == "C" and first["word"][2] == "T"`.

- [ ] **Step 2: Run** `pytest backend/tests/integration/test_pause_resume_e2e.py -m slow -v`
  Expected: `2 passed`. (`-m slow` on the CLI overrides `pytest.ini`'s `-m "not slow"` — `-m` is a single store option, the last value on the effective arg list wins.) If red, debug Tasks 13–15 per DD4's ordered map until green — **do not** touch the assertions or timings (`superpowers:verification-before-completion`).

- [ ] **Step 3: Commit** — `test(e2e): real-subprocess pause→edit→resume + pattern through Flask (slow gate)`


---


---

## Self-Review (coverage + deviations from the parent plan)

**Coverage vs parent Phase 3 (`:530-665`):** Task 13 (CLI pause plumbing + hooks) ✓; Task 14 (`fill --resume` + `fill_with_resume` fix) ✓; Task 15 (`resume_task_id` + `state_paths.py` + paused SSE) ✓; Task 16 (F11 pausing sub-state + F14 two-step resume) ✓; Task 17 (F12 discovery + F13 live edit preview) ✓; Task 18 (F15 409 recovery + F16 honest cancel/discard/boot cleanup) ✓; Task 19 (real-subprocess E2E gate) ✓. State-machine amendments 1/2/3, Authoritative endpoint contracts, and Cross-task literals are referenced, not restated.

**Reasoned deviations from the literal parent plan:**
1. **Task 13 touches 2 files beyond the parent's Files list** (`beam_search_autofill.py`, `hybrid_autofill.py`) — required to honor the parent interface's beam-graceful-stop mandate (`:549`); the wrappers currently *drop* pause. See the Scope decision above.
2. **`FillResult.paused`/`state_path` populated directly** (Task 13 DD2) instead of a new `autofill.was_paused` attr (parent `:547`) — root-fixes the silent-failure where a paused run was indistinguishable from an unsolvable one.
3. **`fill --resume` makes `grid_file` optional** and the adapter passes no `grid_file` positional (deviates from parent `:574`) — the grid is authoritative in `csp_state.grid_dict`.
4. **`state_paths.py` `PAUSE_FLAG_DIR` = `/tmp`** (preserves today's working path) rather than a new dir — minimal-blast-radius single-sourcing.
5. **Task 15 adds a second SSE fix (DD4b)** the parent didn't foresee: suppressing the spurious `complete` (DD4) is insufficient — `"paused"` must also join the generator's terminal-break set or the synchronous SSE consumer hangs.
6. **`--adaptive` and `--attempts>1` pause scoped out** (crash-safe no-ops) — not web-default paths.

## Follow-ups (logged, not done here)

- **[decision] Repair/beam/hybrid pause scope** — resolve the Scope decision above before Task 13.
- **[Task 13 save contract]** Precise theme/user-lock enforcement on the **degenerate** (repair/beam) re-seed is deferred — M1 preserves grid structure + black squares only (reconciliation note 1). The exact-position CSP path is unaffected.
- **[pre-existing bug, parent trust-ledger §E]** `handle_error(…, default_status=…)` at `pause_resume_routes.py:73`/`:264` is a real bug (`errors.py:10` has no `default_status` param → `TypeError` on the error path). Not fixed here; Task 15 explicitly routes *around* it (uses the correct 3-arg form). Log a standalone fix ticket.
- **[dead-code]** `pause_controller.should_pause()`'s 100 ms rate-limit branch is vestigial (both paths return `False` when the flag is absent) — effectively `return self.pause_file.exists()`. Harmless; note for future cleanup.
- **[hazard]** `_handle_pause` raises an **uncaught** `ValueError` if `task_id` is missing while a `pause_controller` is present (`autofill.py:1152-1153`). Task 13 DD3's gating keeps `task_id` present whenever the controller is, so it never fires — but a future caller that breaks that invariant gets a raw traceback, not a `FillResult`.
- **[executor trap]** `/api/fill/resume` docstring shows a stale `edited_grid` shape (reconciliation note 9).
- **[deferred, Task 11 interaction]** `useNumbering`'s two-writer race with the autofill SSE loop (both call `setGrid` during adaptive fill) — flagged in the U5/Task-8 plan; still open. The frontend pause tasks (16–18) enable grid edits only in `idle`/`paused` (F13), which bounds but does not resolve it.

## Provenance / REVIEW RESULTS (2026-07-14)

Built and hardened via a multi-agent workflow, mirroring the U5/Task-8 process:

1. **Recon (6 parallel agents):** re-verified every load-bearing citation against HEAD `9e124b2` (files drifted — `cli.py` 105-614 → 1640 lines) and surfaced **34 hazards** (bugs, dead code, format-collisions, silent-failure traps, races) across the CSP pause path, the repair/beam/hybrid graceful-stop path, state serialization + IPC, the `fill` command, the backend routes/adapter, and the frontend contracts. Findings drove the DD decisions (e.g. the silent `FillResult.paused` gap, the split-dir severance, the envelope `algorithm`-tag collision, the beam-wrapper pause-drop).
2. **Draft (7 architects):** one per task (13–19), each expanding the parent stub into an execution-ready section on the shared verified-facts sheet.
3. **Adversarial verify (7 reviewers):** each section independently re-checked against primary source, fabrications killed, Arthur's no-full-code convention enforced. **All 7 returned HARDENED** (real defects fixed — e.g. Task 15's DD4b SSE-hang BLOCKER, Task 19's `create_test_grid` NameError, Task 13's 5 correctness defects).
4. **Cross-section consistency pass (1 agent, the view no per-section reviewer had):** found the T14 lock-channel error, the T16↔T17↔T18 flat-vs-context surface seam, and the `conflict` string-vs-object collision → the reconciliation notes above; **11 cross-section contracts verified CONSISTENT** (paused stdout keys, `state_paths` constants, `fill --resume` argv, paused-SSE termination, envelope `algorithm=="csp"`, resume payload encoding, and more).
5. **Advisor integration:** scope call (plan all 7, deep-verify what exists, flag only Task-11 internals provisional), and the cross-section-blind-spot catch that prompted step 4.

**Provisional surface (must be re-verified at execution):** all citations into `useAutofillMachine.js` / `AutofillPanel.jsx` internals (Tasks 16–18) — those files are created by **Task 11** (Phase 2, not yet built) and are marked `(PROVISIONAL)` inline. Everything in `src/api/client.js`, `src/api/gridCodec.js`, the CLI, the backend, and the test harnesses is verified against HEAD now.
