# Novice Fresh-Install Readiness — Design
**Version 0.1.2** · Claude with Arthur Passuello · 2026-10-23 · status: rulings in §1 given by owner
2026-10-23; the whole document awaits owner review; §7 open points carry defaults that apply if unruled
by 2026-10-30

---

## AI READING INSTRUCTION

Read `[SPEC]` blocks for authoritative behaviour. Read `[NOTE]` only for context. `[?]` blocks are
unverified. Issue numbers are GitHub issues on `apassuello/crossword-helper`. QA case IDs (`G3`, `A2`, …)
are sections of `docs/dev/qa/2026-10-22-fresh-install-run.md`; its evidence files are in
`.handoff/artifacts/2026-10-22-fresh-install/` (gitignored, local to the main checkout).

---

## 1. Goal, scope and rulings

**[SPEC]**
- **Goal** (Arthur, 2026-10-23 10:50 CEST): a novice who knows nothing about this system and has nothing
  installed can install it on a fresh machine and use every feature without issues. Autofill may stay
  buggy, but it must be non-destructive and must never block the workflow.
- **Platforms:** macOS and Linux. Windows is out of scope (ruled 2026-10-23 11:34 CEST); the README says
  so in one line.
- **Rulings, 2026-10-23:**
  - Unfinished UI (Clues #53, "Suggest Black Square" #54, Heatmap #50) is hidden, not built. **What it
    beat:** wiring them up (days, not today); wiring only the two with server routes.
  - Install prerequisites are documented in the README and checked by `setup.sh`. **What it beat:**
    shipping a prebuilt frontend (Python-only install, but a build artefact to maintain); Docker.
  - **Autofill never touches a letter the user typed.** If the solver blocks and would have to clear
    those cells, it stops and shows them in red (Arthur, 11:22 CEST). Implemented as approach A, §2, with
    all three red cases (Arthur, 11:31 CEST). That case 2 marks cells red *without* stopping the run is
    not a ruling: it is Claude's reading of the rule, open as §7 P6. **What it beat:** B, re-applying the user's letters in the UI only (the solver
    still clears them internally, so results come back inconsistent, and the logic leaves `cli/`); C,
    pre-flight only (a solvable grid could still lose letters mid-run).
  - A failed, partial or cancelled run restores the grid as it was at Start and offers the partial fill
    as an explicit choice. **What it beat:** keeping the partial fill plus an undo button.
  - Grid: a "New grid" control with 11/15/21; a black-square button plus a shortcut hint; saved grids
    are auto-restored, named, and listed (§3).
  - #57 item 1: accented letters are folded to A–Z on upload. **What it beat:** rejecting them.
- **Must-have, in order:** §5 install, §2 autofill safety (with #41), §3.1 hiding, §3.3 black squares,
  §3.2 new grid, §3.4 saves, §3.5 grid-edit guards (#62, #63), §4 word-list and CLI rulings.
- **Stretch, if the must-haves land:** #19, #20 and #57 item 4 (theme placement); SR2 (search results
  below the viewport, the rest of #45); TH5 (theme panel covers the top bar).
- **Out of scope:** Windows; solver fill quality beyond #40's default; #26 #28 #29 #36 #37 #38 #39 #52
  #59 (solver internals or pause/resume, which has no UI); #18 #56 #60 (developer-facing); #43.

**[NOTE]** This supersedes the 2026-10-22 basics-first spec's §5 #47 ruling (option C: restore plus a
"Start new" banner). §3.4 keeps that behaviour and adds named saves and a list (owner, 2026-10-23: "All 3").

---

## 2. Autofill: user letters are locked; never destructive, never blocking

### 2.1 CLI `fill`

**[SPEC]**
- **Which letters are locked.** New option `--lock-filled/--no-lock-filled`, **default `--lock-filled`**
  (P1). The input grid file may carry an optional `"locked": [[r, c], ...]` key. On a fresh run (for
  `--resume`, see the last bullet) the lock set is:
  - `--lock-filled` with a `"locked"` key: exactly the listed cells. This is the UI's channel (§2.2): the
    UI lists the letters the user typed and leaves autofilled letters unlocked, so the solver may change
    them.
  - `--lock-filled` without the key: every letter in the input grid. A CLI user's input grid is what they
    typed.
  - `--no-lock-filled`: no input letter, with or without the key.

  Theme entries given with `--theme-entries` are locked by the beam, repair and hybrid solvers as today,
  in all three cases. A listed cell that is out of bounds or holds no letter fails the run through
  `_fail_fill` (exit 1); the list is never trimmed silently.
- **Where the lock set is applied (C12).** `Grid.from_dict` writes `Grid.cells` directly and never calls
  `set_letter`, so it applies the `"locked"` key in its own pass after the cells are populated, and
  defaults to no locks when the key is absent. The other two cases are post-load passes in `cli.py`'s
  `fill`: without the key, `--lock-filled` locks every letter; `--no-lock-filled` empties
  `locked_cells` whatever `from_dict` applied. `place_word` already tolerates a locked cell holding the
  same letter, and `set_letter`'s new check (below) raises only on a different one, so a theme entry
  that is also in the `"locked"` list places cleanly.
- **`locked_cells` survives every grid copy a solver makes.** `Grid.clone` already copies it. Two fill
  paths round-trip through `Grid.to_dict`/`Grid.from_dict`, which drop it: `Autofill.fill_with_restarts`
  (`self.grid = Grid.from_dict(original_grid_state)`) and `AdaptiveAutofill` (`_original_grid_dict`,
  rebuilt by `_skeleton_grid`). `to_dict` gains `include_locks: bool = False`; with `True` it adds
  `"locked"` (sorted row-major, `[]` when none), and only those two round trips pass `True`. With the
  default its output is unchanged, so `-o` files, pause state (`state_manager.py` and the degenerate
  save in `fill`), progress snapshots and `nyt_parser.py` carry no locks (C10). A test copies a locked
  grid through `clone` and through a `to_dict(include_locks=True)`/`from_dict` round trip and asserts
  the set is intact; this is the load-bearing test of §2.1.
- **No write changes the value of a locked cell (D3)**, not only writes that empty it. `Grid.set_letter`
  raises `ValueError` when the cell is locked and the letter differs (today it has no lock check).
  `Grid.remove_word` and `Grid.place_word` already honour `locked_cells`. Other writers of `Grid.cells`
  include `IterativeRepair`'s bulk `cells[:] = ...` restores, `_backtrack_region` and
  `_would_create_gibberish`; the plan enumerates every writer in `cli/src/` with `ast-grep` and a
  positive control, and each one either skips locked cells or is shown to restore a copy taken while the
  locked cells held their input letters.
- **End-to-end postcondition in `cli.py` `fill`.** Before a grid leaves `fill` (the stdout result, the
  paused payload, the `-o` file), every locked cell of the input lock set holds its input letter. On a
  mismatch, `fill` writes no output file and fails closed through `_fail_fill` (exit 1) with
  `Autofill changed a locked letter; nothing was written.` The sweep above is defence in depth; this
  check is the guarantee. Tests: a stub solver that overwrites a locked cell gives exit 1 and no `-o`
  file; and the postcondition holds on a grid with a typed letter under every `--algorithm` value and
  under `--adaptive`.
- **A placement that conflicts with a lock fails that placement (C13).** `Grid.place_word` raises
  `ValueError` on a word that disagrees with a locked letter. Beam search and repair's CSP path already
  catch it and try the next candidate. Three sites call it bare: `Autofill._backtrack`,
  `Autofill._backtrack_with_mac` and `IterativeRepair._repair_invalid_words`; there the error reaches
  `fill`'s `except ValueError` and the run exits 1 (non-destructive, but failed). Each of the three treats
  it as a failed placement instead. Theme entries reach only beam, repair and hybrid (classic `regex` and
  `trie` warn and ignore `--theme-entries`); from the UI, theme-locked letters are also in the `"locked"`
  list, so classic locks them too.
- **Adaptive mode never blacks out a locked letter (D2).** `Grid.set_black_square` raises `ValueError`
  when the cell, or with `enforce_symmetry` its 180° partner, is locked. `AdaptiveAutofill` drops any
  black-square suggestion whose cell or partner is locked or holds a letter, before it reaches
  `_apply_black_square`.
- **A fully locked slot is valid (B1, owner ruling G13).** In `IterativeRepair` (`--algorithm repair`,
  and hybrid's repair phase), a slot whose every cell is locked (`_slot_fully_locked`) is valid
  regardless of list membership or score: `_find_conflicts` does not flag it as an invalid word, and
  `_forward_check` skips `find` for a fully locked crossing slot. This covers a typed word that is not in
  the lists (case 2), a typed listed word that scores below the run's min score, and a theme entry, which
  `IterativeRepair.fill` places with `lock=True`. The theme-entry case is a defect on `main` today:
  `_forward_check` never consults `_is_valid_word`, and the trie the repair matcher searches holds only
  list words and is searched at the run's floor, so a theme entry that is off-list or below the floor rejects every
  CSP placement crossing it. This rule fixes it.
- **Pre-flight** runs on a fresh run (not `--resume`) whose lock set is non-empty, after the word lists
  load and after the `empty_slots` early return, before the solver runs:
  - `model = SlotModel.from_grid(grid)` (not `from_blacks`, which passes NumPy integers through);
    `index = LetterBitsetIndex.from_word_list(word_list)`; `fixed = slot_model.fixed_from_grid(g)`,
    where `g` is `grid.clone()` after `g.clear_unlocked()`, so unlocked letters (autofilled ones sent by
    the UI) take no part; `report = src.domain.fillability.assess(model, index, fixed, min_score=0)`.
  - A **dead slot** is an open slot (its pattern has a `?`) whose own pattern matches no word:
    `index.count_matches(pattern(model, s.id, fixed), min_score=0) == 0`. Pass `min_score=0` explicitly;
    `count_matches` defaults to 30. Only these directly dead slots count, not `report.wiped_slots`:
    `assess`'s cascade empties every slot crossing a dead one, which would turn every typed letter in
    the region red (C1).
  - **Case 1, a dead slot contains a locked cell:** no solver runs. The `--json-output` result is
    `{"success": false, "blocked": true, "reason": "no_word_fits", "blocked_cells": [[r, c], ...],
    "blocked_slots": [{"row": r, "col": c, "direction": "across"|"down", "length": n, "pattern": "C?T"}],
    "off_list_cells": [...], "stuck_cells": [], "grid": <input grid, unchanged>}` and the exit code is
    **3**. `"blocked_slots"` lists every dead slot in slot-model order; `"blocked_cells"` is the locked
    cells inside them. Text output prints `Blocked: no word fits <pattern> at <row>,<col>
    <direction>`, one line per slot.
  - **Dead slots, none containing a locked cell (B2):** the selected lists have no word of that length.
    Same result shape and exit 3, with `"reason": "no_word_of_length"` and `"blocked_cells": []`; text
    output prints `Blocked: the selected word lists have no words of length <n>`, one line per length.
    Without this split, an empty grid on a list with no long words was blocked with nothing to
    highlight.
  - **`report.refuted` with no dead slot** (a refutation only the cascade finds): the run proceeds, and
    case 3 reports what it could not fill.
  - **Case 2, `report.off_list_fixed`:** a fully locked word that is not in the lists does not make the
    fill impossible (the rule above makes it valid), so the run **proceeds**. Its cells are reported in
    `"off_list_cells"`, and the `"warnings"` array gains
    `"Typed words not in the selected word lists: <WORD>, ..."`. Pre-flight also emits one stderr
    progress event, status `running`, whose `data` carries `"off_list_cells"` and that warning, so the UI
    can show it while the run continues (C4); today `warnings` reaches only the final stdout JSON.
  - Pre-flight sees only letters in the input grid. On the bare CLI, entries given with
    `--theme-entries` are placed later, inside the solver, so pre-flight does not check them. From the
    UI they are in the grid and in the lock list.
  - **Imports (C9).** `cli/src/domain/*` use absolute `from src.…` imports, which fail under the
    README's `python -m cli.src.cli` from the repo root (`ModuleNotFoundError: No module named
    'src.domain'`). Pre-flight must import under both entry points (relative imports in
    `cli/src/domain/`, or the `sys.path` bootstrap `adaptive_autofill.py` uses). A test runs the
    README's `fill` example through `python -m cli.src.cli` from the repo root on a grid with at least
    one letter; the shipped example grids have none, so on them pre-flight never runs.
- Pre-flight latency is measured in the plan on `comprehensive` and on the largest `raw/` list, at
  15×15 and 21×21, and recorded there with the command that produced it. If it exceeds 2 s on
  `comprehensive` at 21×21, that is reported to the owner before the task lands.
- **Case 3, end of run (C2):** every result (success, partial, timeout) carries `"stuck_cells"`: the
  locked cells in (a) slots that still contain an empty cell and whose final pattern matches no word at
  the run's min score, and (b) filled slots that the result's `problematic_slots` flags with reason
  `invalid_word`. Repair and hybrid fill invalid words rather than leave `?`, so (a) alone is `[]` on
  them; counting every slot with an empty cell would over-report on a timeout. `[]` when the fill is
  complete.
- **Result keys (C11).** The four `--json-output` fill results (the main result, the already-filled
  early return, the paused payload and the blocked result) carry `"blocked"` (bool), `"blocked_cells"`,
  `"off_list_cells"` and `"stuck_cells"` (lists, `[]` when empty). Errors from `_fail_fill`
  (`{success, error, hint}`) do not. Cell lists are unique, sorted row-major, `[row, col]` zero-based.
- **Pause markers (C6).** `pause_controller.mark_running()` precedes word-list loading, but `fill`'s
  `try`/`finally` covers only `_run_fill`, so every exit between them leaks the markers: the
  theme-entries JSON error `return`, each `_fail_fill` (`sys.exit`), the word-list open error, and now
  the blocked return. The `try` whose `finally:` clears the markers starts immediately after
  `mark_running()`, so one cleanup covers all of them and the `empty_slots` early return.
- `--resume` is unchanged: neither `--lock-filled` nor a `"locked"` key applies, locks are not
  persisted in state files (the DD4 comment in `cli.py`'s `fill`; `to_dict`'s default output stays
  lock-free), pre-flight does not run, and pause/resume has no UI.

**[NOTE]** `assess` is the 2026-09 redesign's fillability capability (spec
2026-09-07-domain-capabilities-design, §8). `refuted` is one-sided: `True` proves no fill exists;
`False` proves nothing, which is why case 3 exists. A dead slot always makes `refuted` true; pre-flight
blocks on dead slots only, so the red cells are the letters that cause the block. Pre-flight uses floor
0 so it blocks only when no listed word fits at all, never because of the score floor.

**[NOTE]** Known limitation (owner ruling G13): a partially locked slot is still searched at the run's
min score. A typed pattern that only below-floor words fit passes pre-flight, and the run cannot fill
that slot; it ends partial or at its timeout, with those cells in `"stuck_cells"`. There is no second
pre-flight at the run's floor.

**[?]** Not read: how `BeamSearchAutofill` and the beam orchestrator judge a fully filled off-list slot,
and the `problematic_slots` shape of solvers other than `IterativeRepair`. The plan checks both before
relying on case 2 under `--algorithm beam` and on case 3 (b) outside repair and hybrid.

### 2.2 Adapter and route

**[SPEC]**
- **The UI's seam is the route (C5).** UI autofill posts to `/api/fill/with-progress`; `routes.py`
  `fill_with_progress` builds the argv and runs it in a thread through `run_cli_with_progress`, which
  today parses stdout only on exit 0 and reports any other exit as `CLI Error (code N)`.
- **Lock channel.** The request body gains `locked_cells: [[r, c], ...]`, built by the UI (§2.3).
  `validate_fill_request` checks it is a list of in-bounds integer pairs. `fill_with_progress` writes it
  into the temp grid file as `"locked"`, beside `"size"` and `"grid"`, and always passes `--lock-filled`
  explicitly. A request without `locked_cells` gets no `"locked"` key, so the CLI locks every letter:
  an older client fails safe.
- **Exit 3.** `run_cli_with_progress` treats exit 3 with parseable stdout JSON carrying
  `"blocked": true` as a result, and emits it as the terminal event with status `complete`. Any other
  non-zero exit stays `error`. Reusing `complete` rather than adding a `blocked` status leaves the three
  places that know the terminal set unchanged (`progress_routes.py`'s `generate()`, `_pump_stderr`'s
  rewrite list, §2.4's cleanup trigger) (B3). The CLI never emits `blocked` on stderr.
- **Ceiling (B4).** `fill_with_progress` passes `timeout + 10` to `run_cli_with_progress`, whose
  `TimeoutExpired` branch sends `Operation timed out` with status `error`. The SSE statuses are
  `running`, `complete`, `paused` and `error`; there is no `failed`. The route's addend becomes
  `CLI_STARTUP_BUDGET_SECONDS` from `cli_adapter.py`, the addend the adapter already uses: `--timeout`
  bounds solver time only, so with `+ 10` a run whose startup (now including pre-flight) exceeds 10 s is
  killed before it can report its partial result (open point, §7). The 202 response gains
  `"ceiling_seconds"`, the value passed, for the client watchdog (§2.4).
- **Tests.** An argv contract test on `fill_with_progress`, in the style of
  `backend/tests/unit/test_fill_resume_route.py`, pins `--lock-filled` and the temp file's `"locked"`
  key (present with `locked_cells`, absent without). One real-subprocess test drives a blocked grid end
  to end to a `complete` event with `blocked: true`.
- `CLIAdapter.fill` (the synchronous `/api/fill`; it reads the `-o` file and passes no
  `--json-output`) is not on the UI's path. It sends no lock list, so the CLI locks every letter, and it
  treats exit 3 as a failure carrying the CLI's message.

### 2.3 UI

**[SPEC]**
- **Provenance (owner ruling G12 (b)).** The canonical cell (`gridCodec.js`'s `makeCell`, and
  `App.jsx`'s `initializeGrid`, which builds cells by hand) gains `isAutofilled: false`. Only the
  autofill merge below sets it `true`. Every other writer that changes a cell's letter, black state or
  theme lock sets it `false` on the cells it changes: a user edit makes the letter the user's. The flag
  is part of the saved document (§3.4 saves cells whole) and of `contentSigOf`, so a restored grid keeps
  its provenance; a grid loaded without the field gets `false`.
- **Lock list.** `useAutofillMachine.start` sends `locked_cells`: every white cell with a letter that is
  not `isAutofilled`, plus every `isThemeLocked` cell with a letter. Autofilled letters go in the grid
  unlocked, so a run started after "Keep partial fill" can still change them.
- **No other grid writer runs while a run is live (D1).** While `autofill.state` is `submitting` or
  `running`, the machine's `onGridUpdate` is the only writer of letters and black squares. Every other
  `setGrid` caller in `App.jsx`, and every control that leads to one (typing and Backspace in
  `CrosswordGrid`, the black-square and theme-lock toggles, Search placement, theme apply, import,
  Verify and Clean, grid size, New grid §3.2, Open saved §3.4), is disabled. Each writer also returns
  early when the check fails at write time, not only at render, so an async handler (Verify, Clean)
  whose response lands after Start writes nothing. `useNumbering` is already gated on the same
  states. While gated, the grid shows `Editing is paused while autofill runs.`
- **Snapshot.** At Start the machine stores a full copy of the grid and the current `gridId`.
- **Merge** (`mergeGridPreserveThemeLocked`, extended) is defined against the **current** grid: a
  progress or result grid writes a cell only if that cell is not theme-locked and is either an empty
  white cell or `isAutofilled`. A cell it gives a letter becomes `isAutofilled: true`; a cell it empties
  or blacks out becomes `isAutofilled: false`. It never changes a user's letter. A merge arriving when
  `gridId` differs from the one stored at Start is dropped.
- **Restore** replaces the grid with the Start snapshot. This is exact because no other writer ran
  during the run: the only changes since Start are the merge's, including adaptive black squares.
- **"Keep partial fill"** applies the last result or progress grid through the same merge, against the
  grid as it is when clicked, so letters the user typed after the run ended stay. It is offered only
  while `gridId` still matches Start's.
- Terminal outcomes:

  | Outcome | Grid afterwards | Offer | Message |
  |---|---|---|---|
  | complete fill (`success: true`) | the result, merged | — | `Successfully filled X/Y slots!` (unchanged) |
  | every slot filled, `success: false` | the snapshot | "Keep fill" | `Filled X/Y slots — N entries may be invalid (use Verify Words to check)` (unchanged text) |
  | partial / timeout | the snapshot | "Keep partial fill (X/Y slots)" | `Autofill could not fill around the highlighted letters.` if `"stuck_cells"` is non-empty, else `Partial: X/Y slots (P%)` |
  | blocked, `"no_word_fits"` | the snapshot | — | `No word fits the highlighted letters.` |
  | blocked, `"no_word_of_length"` | the snapshot | — | `The selected word lists have no words of length N.` |
  | `complete` without a grid | the snapshot | — | `No solution found` (unchanged) |
  | cancelled | the snapshot | "Keep partial fill" if any progress grid filled at least one cell | `Cancelled by user` (unchanged) |
  | paused (no UI control; only an API pause reaches it) | the snapshot | as for cancelled | `Autofill was paused outside the app.` |
  | `error` event, or lost contact (§2.4) | the snapshot | as for cancelled | the error, or `Lost contact with the autofill run.` |

- A blocked run arrives as a `complete` event with `data.blocked === true` (§2.2); `handleEvent`'s
  `complete` branch checks for it first.
- Red cells: a new canonical cell field `isBlocked` (separate from `isError`), set for `"blocked_cells"`,
  `"stuck_cells"` and `"off_list_cells"`. For case 2, `handleEvent`'s `running` branch reads
  `"off_list_cells"` and the warning from the pre-flight event's `data`, marks those cells and shows the
  warning as a toast while the run continues. Red clears on any cell edit, on New grid, and on Start.
- **Zero word lists (I5).** Start is disabled when no word list is ticked, with the hint
  `Select at least one word list` (as Search, §4). Today Start is gated only on there being empty
  slots; the request then sends `wordlists: []` and `validate_fill_request` refuses it with a 400.

### 2.4 #41: the panel never strands

**[SPEC]**
- Server (`backend/api/progress_routes.py`): a subscriber's `generate()` no longer calls
  `cleanup_progress_tracker` in its `finally:`. The tracker is removed 60 s after its terminal event
  (`complete`, `error` or `paused`) is enqueued. A run the backend kills at its ceiling
  (`run_cli_with_progress`'s `TimeoutExpired` branch, §2.2) already enqueues `error` with
  `Operation timed out`, so that path reaches cleanup too. A second subscriber disconnecting therefore
  cannot drop the terminal event.
- **Client watchdog (B4).** Armed when the machine enters `running`, keyed to that `taskId`, it fires
  at Start + `"ceiling_seconds"` + 30 s. When it fires it calls `api.cancelFill(taskId)` (best effort)
  and moves the machine to `failed` with `Lost contact with the autofill run.`, restoring the snapshot
  (table above). It is cleared on every transition out of `running` and on unmount.
- **Stream errors (C8).** `EventSource.onerror` carries no HTTP status, so a 404 from the progress
  stream cannot be told apart from any other stream error. Any stream error while `running` moves the
  machine to `failed` with `Lost contact with the autofill run.` (replacing `Connection error`),
  restoring the snapshot.
- **Cancel (C7).** Today `cancel()` closes the stream and moves to `cancelled` before posting, so a
  Cancel after the run has ended shows `Cancelled by user` for a run that was not cancelled. Instead
  `cancel()` posts `api.cancelFill(taskId)` first and keeps the stream open, the machine staying
  `running` with a cancel pending. On 200 it moves to `cancelled`; an `error` event that arrives while
  the cancel is pending (the killed process) also counts as `cancelled`. On 404 (no process running:
  the run has ended) it keeps waiting on the open stream, and the terminal event, which the server now
  keeps, or the watchdog decides the outcome. A `complete` event that arrives first is shown as what it
  is.

**[NOTE]** Not addressed: two subscribers open at the same time each `get()` from one queue and split the
events (#41's comment, unmeasured). A novice opening a second tab on a running fill is unlikely; the
watchdog bounds the damage.

### 2.5 #40

**[SPEC]** The Autofill panel's default min score is 30 (was 50), the value the README's `fill` example
uses. The comment above `AutofillPanel.jsx`'s defaults is updated to match.

---

## 3. Grid and UI

### 3.1 Hidden controls

**[SPEC]** Not rendered: the Clues tool in the tool rail (#53), the "Suggest Black Square" button (#54),
the Heatmap toggle (#50). The issues stay open. No test may depend on them being present.

### 3.2 New grid (#55)

**[SPEC]**
- The Grid panel has a "New grid" control offering `11×11`, `15×15`, `21×21`.
- If the current grid has any letter or black square, an in-panel confirm (no browser dialog) asks
  `Replace the current grid? Unsaved changes are lost.` with "Replace" and "Cancel".
- The new grid is empty, numbered, with symmetry on. Red cells and autofill results are cleared.
- Disabled while an autofill run is in progress.

### 3.3 Black squares (#50)

**[SPEC]**
- The Grid panel has a "Black square" toggle that acts on the selected cell exactly as the Space and `.`
  keys do: symmetry applies, and it is disabled with no selected cell or on a theme-locked cell.
- An always-visible hint line under the grid reads:
  `Type letters · Arrows move · Space or . black square · Enter switch direction · Tab next word · Backspace clear`
  These are the keys `CrosswordGrid.jsx`'s key handler implements; a test pins the line against it.

### 3.4 Saved grids (#47)

**[SPEC]**
- Storage stays behind `src/lib/storage.js` (its transport contract is unchanged in spirit: `save`
  rejects on a write failure, `load` never rejects). Saved grids are an array in localStorage key
  `crossword_saved_grids`, newest first; each entry is today's save document plus `name`. <!-- docs-check: allow (planned by this spec, not built yet) -->
- A legacy save under `crossword_saved_grid` is migrated once into the array, named `Saved grid`, and the
  legacy key is removed.
- "Save grid" asks for a name in the panel, defaulting to `<size>×<size> <YYYY-MM-DD HH:MM>`. Saving
  under an existing name asks to replace it.
- On load, the newest save is restored, with the banner `Restored "<name>" (saved <time>)` and a
  "Start blank" action (which opens New grid, §3.2).
- "Open saved" lists every save (name, size, saved time) with "Open" and "Delete". Opening asks the §3.2
  confirm when the current grid has content.
- A failed write (quota) shows `Could not save: browser storage is full. Delete a saved grid or export
  this one.` and is never swallowed.

### 3.5 Grid-edit guards (#62, #63)

**[SPEC]**
- **#62:** placing a Search result (`handlePatternSelect`) writes a letter only into a white cell that is
  not theme-locked, exactly the rule the key handler applies to typed letters, and stops at the first
  black square in the slot's direction. Cells it skips keep their content.
- **#63:** Clean with `removed_count === 0` clears `isError` on every cell before its
  `Grid is clean — all words are valid!` toast (Greptile's suggested patch on PR #35).

**[NOTE]** Both came from the 2026-08-23 Greptile audit (PR #35), re-checked on `fd392c9` and filed
2026-10-23. #62 destroys theme-locked letters, the same class as the autofill rule in §2.

---

## 4. Word lists and CLI rulings (#57)

**[SPEC]**
- **Item 1 (L11):** the word-list line parser folds letters to A–Z with Unicode NFKD decomposition,
  dropping combining marks (`CAFÉ` → `CAFE`, `NAÏVE` → `NAIVE`, `ÜBER` → `UBER`). A word that still
  contains a non-A–Z letter after folding is skipped with reason `not letters only`. The upload preview
  shows the folded word.
- **Item 2 (SR4):** with no word list selected, the Search button is disabled with the hint
  `Select at least one word list`. The CLI's built-in fallback list is not reachable from the UI.
- **Item 3 (CLI-normalize):** the default `normalize` rule keeps letters only:
  `normalize "Hello, World!"` → `HELLOWORLD`.
- **Item 4 (TH4):** stretch, with #19/#20.

---

## 5. Install (macOS and Linux)

**[SPEC]**
- **README "Before you start"**, the first section after the screenshots:
  - Python 3.9 or later: on macOS, from python.org (the system `python3` stub opens an Xcode
    command-line-tools install dialog on first use; either path works); on Linux, the distribution's
    `python3` and `python3-venv` packages.
  - Node.js 18 or later (LTS): from nodejs.org, or the distribution package if it is 18 or later.
  - Getting the code: "Download ZIP" from GitHub, or `git clone`.
  - One line: Windows is not supported yet.
- **README "Using the app"**: a short tour, one or two lines per visible tool (Grid, Lists, Search,
  Theme, Autofill, Import/Export), naming the controls as they appear on screen.
- **`setup.sh`:**
  - The existing Python ≥3.9 and Node ≥18 checks print `Missing: <tool> <minimum version> — install from
    <url>` (python.org/downloads, nodejs.org) and exit 1. An `npm` check is added in the same form.
  - `npm install` becomes `npm ci`, which never writes `package-lock.json`, so setup leaves the tracked
    tree clean (#49). `npm ci` fails outright if `package.json` and the lock disagree, so the plan first
    runs it on a fresh clone with the Node LTS the README names; if it fails, the lock is regenerated
    once with that Node and committed, and SETUP-1, SETUP-3 and E2-SETUP-1 confirm it.
- **`run.py`:** `debug=False` by default; `FLASK_DEBUG=1` turns debug on. The docstring and the README's
  dev-mode section say so.

**[NOTE]** ⚠️ Safety: `debug=True` exposes the Werkzeug debugger, which can execute code. On `localhost`
it is still reachable through DNS rebinding. QA graded it S4 (SERVE-1); it is raised here because the
goal is installs by people who will not know it is on.

---

## 6. Acceptance

**[SPEC]** The plan's last task re-runs these cases on a fresh clone under the 2026-10-22 run's method
(E1 and E2 environments, the iframe viewport method of L3/L4), recording each in a new run log next to
the old one:

| Area | Cases | Pass criterion |
|---|---|---|
| Install | SETUP-1, SETUP-2, SETUP-3, E2-SETUP-1, SERVE-1 | Setup completes, the tree stays clean, debug off |
| Grid | G1, G3, G8, G9 | New grid, discoverable black squares, no Heatmap toggle, save restored |
| Grid guards | New: SR-PLACE (place a Search result across a black square and a theme-locked cell); new: CL-CLEAR (Verify flags cells, retype them, Clean) | Protected cells unchanged; no red cells after "Grid is clean" |
| Hidden | CL1, A-SBS | Control absent |
| Autofill | A2, A3, A4 | Panel returns to idle by itself; every letter typed before Start is unchanged |
| Lists, CLI | L11, SR4, CLI-normalize | Per §4 |
| New: AF-LOCK | Type letters, run Repair on the 11x11, cancel and let one run end | Typed letters intact in every progress sample and at the end |
| New: AF-BLOCK | Type a partial pattern no word fits (e.g. `QX` in the first two cells of a 3-letter slot, pattern `QX?`; a fully typed off-list word is case 2, not a block) | Run does not start; those cells red; message as §2.3 |
| New: AF-SUB2 | Open a second progress stream on a running task and close it | The panel still reaches its terminal state |

---

## 7. Open points (default applies if unruled by 2026-10-30)

| # | Question | Default |
|---|---|---|
| P1 | `fill`'s `--lock-filled` default on the CLI, not only from the UI | On. The owner rule is about what the user typed; a CLI user's input grid is what they typed. The shipped `data/grids/example_11x11.json`, `data/grids/example_15x15.json` and `data/grids/example_21x21.json` contain no letters, so the README's `fill` example (R7) is unaffected. |
| P2 | Pre-flight min score | `0`: block only when no listed word fits at all. |
| P3 | Tracker retention after the terminal event | 60 s. |
| P4 | Client watchdog grace | 30 s beyond the run's timeout. |
| P5 | Accent folding scope | Upload/import parsing only; `pattern` input is already A–Z and `?`. |
| P6 | Case 2 (a typed word not in the lists): stop the run, or mark it red and continue | Mark red, warn, continue. The owner rule stops the run when the solver *blocks*; an off-list typed word does not block it, since the solver fills around a fixed slot. Stopping would refuse every grid with a deliberate proper noun. |

---

## 8. Amendment record

- 0.1.0 (2026-10-23): first version, from the owner rulings in §1.
- 0.1.1 (2026-10-23): before owner review. §2.1 gains lock survival across `to_dict`/`from_dict` (the
  `Autofill` restart loop dropped locks), the pinned `SlotModel.from_grid` constructor and a pre-flight
  latency check; §2.4 covers a run killed at the adapter's ceiling; §5 covers a lock/`package.json`
  mismatch under `npm ci`; case 2's continue-on-red moves from §1's rulings to P6.
- 0.1.2 (2026-10-23): §3.5 adds #62 and #63 to the must-haves (Greptile PR #35 findings, filed that day);
  §6 gains their acceptance cases.
