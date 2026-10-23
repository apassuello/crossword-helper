# Novice Fresh-Install Readiness — Design
**Version 0.1.0** · Claude with Arthur Passuello · 2026-10-23 · status: rulings in §1 given by owner
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
    all three red cases. **What it beat:** B, re-applying the user's letters in the UI only (the solver
    still clears them internally, so results come back inconsistent, and the logic leaves `cli/`); C,
    pre-flight only (a solvable grid could still lose letters mid-run).
  - A failed, partial or cancelled run restores the grid as it was at Start and offers the partial fill
    as an explicit choice. **What it beat:** keeping the partial fill plus an undo button.
  - Grid: a "New grid" control with 11/15/21; a black-square button plus a shortcut hint; saved grids
    are auto-restored, named, and listed (§3).
  - #57 item 1: accented letters are folded to A–Z on upload. **What it beat:** rejecting them.
- **Must-have, in order:** §5 install, §2 autofill safety (with #41), §3.1 hiding, §3.3 black squares,
  §3.2 new grid, §3.4 saves, §4 word-list and CLI rulings.
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
- New option `--lock-filled/--no-lock-filled`, **default `--lock-filled`**. With it, every letter in the
  input grid is placed with `Grid.set_letter(row, col, letter, lock=True)`, so it joins
  `grid.locked_cells`. Theme entries are locked as today.
- **No code path empties a locked cell.** `Grid.remove_word` skips locked cells, and so does every other
  path in `cli/src/` that writes an empty value into `Grid.cells`. The plan enumerates those paths with
  `ast-grep` and a positive control. A solver that tries to place a word conflicting with a locked
  letter fails that placement; it does not overwrite.
- **Pre-flight**, only with `--lock-filled` and only on a fresh run (not `--resume`): before any solver
  runs, call `src.domain.fillability.assess(model, index, fixed, min_score=0)` with
  `fixed = slot_model.fixed_from_grid(grid)`, the model from the input grid, and the index from the
  loaded lists.
  - **Case 1, `report.refuted`:** no solver runs. The `--json-output` result is
    `{"success": false, "blocked": true, "reason": "no_word_fits", "blocked_cells": [[r, c], ...],
    "blocked_slots": [{"row": r, "col": c, "direction": "across"|"down", "length": n, "pattern": "C?T"}],
    "off_list_cells": [...], "stuck_cells": [], "grid": <input grid, unchanged>}` and the exit code is
    **3**. `blocked_slots` lists `report.wiped_slots` in slot-model order; `blocked_cells` is the locked <!-- docs-check: allow (planned by this spec, not built yet) -->
    cells inside those slots. Text output prints `Blocked: no word fits <pattern> at <row>,<col>
    <direction>`, one line per slot.
  - **Case 2, `report.off_list_fixed`:** a typed word that is not in the lists does not make the fill
    impossible, so the run **proceeds**. Its cells are reported in `"off_list_cells"`, and the
    `"warnings"` array gains `"Typed words not in the selected word lists: <WORD>, ..."`.
- **Case 3, end of run:** every result (success, partial, timeout) carries `"stuck_cells"`: the locked <!-- docs-check: allow (planned by this spec, not built yet) -->
  cells in slots that still contain an empty cell. `[]` when the fill is complete.
- Every `--json-output` fill result carries `"blocked"` (bool), `"blocked_cells"`, `"off_list_cells"`
  and `"stuck_cells"` (lists, `[]` when empty). Cell lists are unique, sorted row-major, `[row, col]`
  zero-based.
- `--resume` is unchanged: locks are not persisted in state files (the DD4 comment in `cli.py`'s `fill`),
  and pause/resume has no UI.

**[NOTE]** `assess` is the 2026-09 redesign's fillability capability (spec
2026-09-07-domain-capabilities-design, §8). `refuted` is one-sided: `True` proves no fill exists;
`False` proves nothing, which is why case 3 exists. Pre-flight uses `min_score=0` so it blocks only when
no listed word fits at all, never because of the score floor.

### 2.2 Adapter and route

**[SPEC]**
- `cli_adapter.py` treats exit code 3 with a parseable JSON body as a blocked result, not a CLI failure,
  and returns the body. Any other non-zero exit stays a failure. A contract test pins the argv
  (`--lock-filled` is passed explicitly), and one real-subprocess test drives a blocked grid end to end.
- The fill-with-progress route emits the blocked result as the run's terminal event with status
  `"blocked"`.

### 2.3 UI

**[SPEC]**
- At Start, `useAutofillMachine` stores a full snapshot of the grid.
- A progress or result grid is merged so that it never changes a cell that was non-empty in the
  snapshot or is theme-locked (extending `mergeGridPreserveThemeLocked`).
- Terminal outcomes:

  | Outcome | Grid afterwards | Offer | Message |
  |---|---|---|---|
  | complete fill | the result | — | `Successfully filled X/Y slots!` (unchanged) |
  | partial / timeout | the snapshot | "Keep partial fill (X/Y slots)" | `Autofill could not fill around the highlighted letters.` if `stuck_cells` is non-empty, else `Partial: X/Y slots (P%)` | <!-- docs-check: allow (planned by this spec, not built yet) -->
  | blocked (case 1) | the snapshot | — | `No word fits the highlighted letters.` |
  | cancelled | the snapshot | "Keep partial fill" if any progress grid filled at least one cell | `Cancelled by user` (unchanged) |
  | failed / lost contact | the snapshot | as for cancelled | the error, or `Lost contact with the autofill run.` |

- "Keep partial fill" applies the last result or progress grid through the same merge.
- Red cells: a new canonical cell field `isBlocked` (separate from `isError`), set for `blocked_cells`, <!-- docs-check: allow (planned by this spec, not built yet) -->
  `stuck_cells` and `off_list_cells`. Case 2 shows its warning as a toast while the run continues. Red <!-- docs-check: allow (planned by this spec, not built yet) -->
  clears on any cell edit, on New grid, and on Start.

### 2.4 #41: the panel never strands

**[SPEC]**
- Server (`backend/api/progress_routes.py`): a subscriber's `generate()` no longer calls
  `cleanup_progress_tracker` in its `finally:`. The tracker is removed 60 s after its terminal event is
  enqueued. A second subscriber disconnecting therefore cannot drop the terminal event.
- Client: a watchdog fires at Start + the run's timeout + 30 s, or when the progress stream answers 404.
  Either one moves the machine to `failed` with `Lost contact with the autofill run.`, restoring the
  snapshot (table above).
- Cancel after the run has ended (server 404) shows the run's real terminal state, not
  `Cancelled by user`.

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
  - `npm install` becomes `npm ci`, so setup leaves the tracked `package-lock.json` unchanged (#49).
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
| P1 | `fill`'s `--lock-filled` default on the CLI, not only from the UI | On. The owner rule is about what the user typed; a CLI user's input grid is what they typed. |
| P2 | Pre-flight min score | `0`: block only when no listed word fits at all. |
| P3 | Tracker retention after the terminal event | 60 s. |
| P4 | Client watchdog grace | 30 s beyond the run's timeout. |
| P5 | Accent folding scope | Upload/import parsing only; `pattern` input is already A–Z and `?`. |

---

## 8. Amendment record

- 0.1.0 (2026-10-23): first version, from the owner rulings in §1.
