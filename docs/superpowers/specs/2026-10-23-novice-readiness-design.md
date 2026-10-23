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
  - **Clean (G5, 2026-10-23):** Clean never blanks a theme-locked cell, and before removing any other
    letter it asks `Clean will remove N letters` with Cancel (§3.5). **What it beat:** a guard alone (a
    typed word vanishes silently); a guard plus undo (a new undo state).
  - **Dead export UI (G10, 2026-10-23):** the disabled PDF and `.puz` options, the disabled "Include
    clues" checkbox and their Format Information entries are hidden (§3.1). **What it beat:** leaving
    them as "coming soon".
  - **Theme panel (G11, 2026-10-23):** TH5 is a must-have: the Theme panel must not cover the top bar
    (§3.6). **What it beat:** keeping it stretch and documenting the × close.
  - **Autofilled letters are not "typed" (G12, 2026-10-23):** per-cell provenance. A letter the autofill
    merge wrote carries `isAutofilled`, cleared by any other edit; the UI sends only the other letters
    as locked, and the CLI keeps its own default (P1). Mechanism in §2; UI rule in §3.7. **What it
    beat:** locking every letter in the grid, which makes "Keep partial fill" freeze the next run.
  - **Locked crossing slots (G13, 2026-10-23):** a fully locked crossing slot is valid regardless of list
    membership or score. Mechanism in §2. The run's score floor is not checked a second time before
    Start: a typed pattern that fits only words below the floor passes pre-flight and can still fail
    later, a known limitation. **What it beat:** folding plus a warning-only second `assess` at the
    run's floor.
- **Must-have, in order:** §5 install, §2 autofill safety (with #41), §3.1 hiding, §3.3 black squares,
  §3.2 new grid, §3.4 saves, §3.5 grid-edit guards (#62, #63, Clean), §3.6 Theme panel and top bar
  (TH5), §3.7 grid-writer provenance, §4 word-list and CLI rulings.
- **Stretch, if the must-haves land:** #19, #20 and #57 item 4 (theme placement); SR2 (search results
  below the viewport, the rest of #45).
- **Out of scope:** Windows; solver fill quality beyond #40's default; #26 #28 #29 #36 #37 #38 #39 #52
  #59 (solver internals or pause/resume, which has no UI); #18 #56 #60 (developer-facing); #43; #64 (NaN%, see the §3.3 NOTE).

**[NOTE]** This supersedes the 2026-10-22 basics-first spec's §5 #47 ruling (option C: restore plus a
"Start new" banner). That ruling was never built: `storage.load` has no non-test caller, and
`useSaveMachine.js` only calls `storage.save`. §3.4 therefore adds restore-on-load and the banner as
new work, together with named saves and a list (owner, 2026-10-23: "All 3").

---

## 2. Autofill: user letters are locked; never destructive, never blocking

### 2.1 CLI `fill`

**[SPEC]**
- New option `--lock-filled/--no-lock-filled`, **default `--lock-filled`**. With it, every letter in the
  input grid is placed with `Grid.set_letter(row, col, letter, lock=True)`, so it joins
  `grid.locked_cells`. Theme entries are locked as today.
- **`locked_cells` survives every grid copy a solver makes.** `Grid.clone` already copies it, but
  `Grid.to_dict`/`Grid.from_dict` drop it, and two fill paths round-trip through them: the restart loop
  in `Autofill` (`self.grid = Grid.from_dict(original_grid_state)`) and `AdaptiveAutofill`. `to_dict` gains
  `"locked": [[r, c], ...]` (sorted row-major, `[]` when none) and `from_dict` restores it, defaulting to
  none when the key is absent so older state files still load. A test copies a locked grid through
  `clone` and through a `to_dict`/`from_dict` round trip and asserts the set is intact; this is the
  load-bearing test of §2.1.
- **No code path empties a locked cell.** `Grid.remove_word` skips locked cells, and so does every other
  path in `cli/src/` that writes an empty value into `Grid.cells`. The plan enumerates those paths with
  `ast-grep` and a positive control. (`remove_word` and `place_word` already honour `locked_cells` for
  theme entries; the sweep is for every other writer.) A solver that tries to place a word conflicting with a locked
  letter fails that placement; it does not overwrite.
- **Pre-flight**, only with `--lock-filled` and only on a fresh run (not `--resume`): before any solver
  runs, call `src.domain.fillability.assess(model, index, fixed, min_score=0)` with
  `model = SlotModel.from_grid(grid)` (not `from_blacks`, which passes NumPy integers through),
  `fixed = slot_model.fixed_from_grid(grid)`, and the index built from the loaded lists.
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
- Pre-flight latency is measured in the plan on `comprehensive` and on the largest `raw/` list, at
  15×15 and 21×21, and recorded there with the command that produced it. If it exceeds 2 s on
  `comprehensive` at 21×21, that is reported to the owner before the task lands.
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
  enqueued. A run the backend kills at its wall-clock ceiling (`timeout_seconds +
  CLI_STARTUP_BUDGET_SECONDS` in `cli_adapter.py`) enqueues a `failed` terminal event, so that path
  reaches cleanup too. A second subscriber disconnecting therefore cannot drop the terminal event.
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
the Heatmap toggle (#50), and in `ExportPanel.jsx` the disabled `PDF (coming soon)` and
`.puz (coming soon)` format options, the disabled `Include clues (if available)` checkbox, and the
`PDF` and `.puz` entries of its Format Information list (G10). The issues stay open. No test may depend
on them being present: the plan edits `ToolRail.test.jsx` (its `TOOL_LABELS` assertions for Clues and
Heatmap) and `AutofillPanel.test.jsx` (its "Suggest Black Square" assertion), and adds an assertion
that none of the hidden labels renders.

### 3.2 New grid (#55)

**[SPEC]**
- The Grid panel is **new**: for tool `edit`, `App.jsx` today renders only the static
  `xw-inspector-empty` "Grid editor" placeholder, and this panel replaces it. It holds "New grid"
  (here), the "Black square" toggle (§3.3) and "Open saved" (§3.4).
- The Grid panel has a "New grid" control offering `11×11`, `15×15`, `21×21`.
- If the current grid has any letter or black square, an in-panel confirm (no browser dialog) asks
  `Replace the current grid? Unsaved changes are lost.` with "Replace" and "Cancel".
- The new grid is empty, numbered, with symmetry on. Red cells and autofill results are cleared.
- Disabled while an autofill run is in progress.
- **Ordering:** §2.3 says red cells clear on New grid, but the control lands here. This task owns the
  clearing: it resets `isBlocked`, `isError` and any retained snapshot or "Keep partial fill" offer when
  the new grid is created. If `isBlocked` does not exist yet, there is nothing to clear for it.

### 3.3 Black squares (#50)

**[SPEC]**
- The Grid panel has a "Black square" toggle that acts on the selected cell exactly as the Space and `.`
  keys do: symmetry applies, and it is disabled with no selected cell, or when the selected cell or, with
  symmetry on, its symmetric partner is theme-locked (G7). `toggleBlackSquare` in `App.jsx` enforces the
  same rule itself, because its symmetry branch today sets the partner's `isBlack` without checking
  `isThemeLocked`; the key path and the button both go through it.
- An always-visible hint line under the grid reads:
  `Type letters · Arrows move · Space or . black square · Enter switch direction · Tab next word · Backspace clear`
  The line lists the primary keys only. `dispatchGridKey` in `CrosswordGrid.jsx` also handles Delete,
  Shift+Tab (previous word) and Ctrl/Cmd+L (theme lock). A test asserts that every key the line names is
  handled by `dispatchGridKey`; it does not require the reverse.

**[NOTE]** #64 (NaN%) becomes easier to reach once the Black square button exists. It stays out of
scope here.

### 3.4 Saved grids (#47)

**[SPEC]**
- Storage stays behind `src/lib/storage.js` (its transport contract is unchanged in spirit: `save`
  rejects on a write failure, `load` never rejects). Saved grids are an array in localStorage key
  `crossword_saved_grids`, newest first; each entry is today's save document plus `name`, keyed by the <!-- docs-check: allow (planned by this spec, not built yet) -->
  document's `doc.id`. Each cell carries `isAutofilled` (§3.7); an entry without it reads as
  `false`, so letters in an old save count as typed and stay locked. <!-- docs-check: allow (planned by this spec, not built yet) -->
- `storage.js` gains `list()` (all entries, newest first), `remove(id)` and an upsert-by-id `save(doc)`;
  `load()` returns the newest entry. <!-- docs-check: allow (planned by this spec, not built yet) -->
- **Autosave and named saves (G3):** `useSaveMachine.js`'s 30 s autosave (`AUTOSAVE_MS`) updates the one
  entry for the current `doc.id`, creating it under the default name below if absent, and never prompts.
  Only the explicit Save button in `TopBar` (`src/components/bench/TopBar.jsx`, the `onSave` prop) opens
  the name prompt, which sits under that button, prefilled with the entry's current name.
- A legacy save under `crossword_saved_grid` is migrated once into the array, named `Saved grid`, and the
  legacy key is removed.
- Confirming a name renames the document's own entry. A name already used by a *different* entry asks to
  replace that entry. The default name is `<size>×<size> <YYYY-MM-DD HH:MM>`.
- On load, the newest save is restored, with the banner `Restored "<name>" (saved <time>)` and a
  "Start blank" action (which opens New grid, §3.2).
- "Open saved", a button in the Grid panel (§3.2), lists every save (name, size, saved time) with "Open"
  and "Delete". Opening asks the §3.2 confirm when the current grid has content, and is disabled while an
  autofill run is in progress.
- **Failed writes (G4):** a failed **explicit** Save shows `Could not save: browser storage is full.
  Delete a saved grid or export this one.` and is never swallowed. A failed **autosave** keeps today's
  behaviour, pinned by existing tests: the toast `Couldn’t save — will retry.` (U+2019), the
  `offline — will retry` status label, and the unbounded 30 s re-arm. **[?]** Whether autosave should
  also show the quota text is open (§7 proposal in the amendment report).

### 3.5 Grid-edit guards (#62, #63)

**[SPEC]**
- **#62:** placing a Search result (`handlePatternSelect`) writes a letter only into a white cell that is
  not theme-locked, exactly the rule the key handler applies to typed letters, and stops at the first
  black square in the slot's direction. Cells it skips keep their content.
  `handlePatternSelect` today copies rows only and then mutates `newGrid[row][col+i].letter` on the
  shared cell objects (G6). The fix writes a **new** cell object for each changed cell
  (`newGrid[row][col+i] = { ...cell, letter }`), never mutating the previous grid's cells.
- **#63:** Clean with `removed_count === 0` clears `isError` on every cell before its
  `Grid is clean — all words are valid!` toast (Greptile's suggested patch on PR #35).
- **Clean never destroys a theme-locked letter, and asks before removing any other (G5).**
  `handleCleanGrid` in `App.jsx` sends only `{letter, isBlack}` per cell and writes the cleaned letters
  over every cell, so today it blanks theme-locked cells while keeping `isThemeLocked` on the emptied
  cell. After the `api.cleanGrid` response and before any `setGrid`:
  1. Every cell that is `isThemeLocked` in the pre-clean grid keeps its pre-clean `letter` and
     `isThemeLocked`; the frontend restores them from the pre-clean grid. The server is unchanged.
  2. `N` = the number of cells that are not theme-locked, held a letter before, and hold none in the
     cleaned result. If `N > 0`, an in-panel confirm (the §3.2 component, no browser dialog) asks
     `Clean will remove N letters` (`1 letter` when `N` is 1) with "Clean" and "Cancel". Cancel leaves
     the grid, `isError` flags and toasts exactly as they were.
  3. If `N === 0` after step 1, no confirm is shown and the #63 rule applies: `isError` is cleared on
     every cell. The toast is `Grid is clean — all words are valid!` only when `removed_count === 0`;
     when the server wanted to remove only theme-locked letters it reads
     `Nothing removed: theme-locked letters are kept.`

**[NOTE]** `verify_words` and `clean_grid` are defined in `backend/api/routes.py` and have no CLI
command. That deviates from "the CLI is the single source of truth" (`.claude/CLAUDE.md`). Moving them is
out of scope here; recorded only.

**[NOTE]** #62 and #63 came from the 2026-08-23 Greptile audit (PR #35), re-checked on `fd392c9` and filed
2026-10-23. #62 and Clean (G5) destroy theme-locked letters, the same class as the autofill rule in §2.

### 3.6 Theme panel and the top bar (TH5, G11)

**[SPEC]**
- With the Theme panel open, the top bar, including the Save button, is fully visible and clickable. The
  panel is laid out below the top bar (offset by the top bar's height, taken from the layout's own
  value, not a copied pixel count), or in flow in the inspector column.
- `ThemeWordsPanel.scss` today positions the panel `fixed` with `z-index: 1000`, which covers the top
  bar. That is the defect.
- The panel's existing × close keeps working.

**[NOTE]** Why it is must-have: the Save button in `TopBar` is the only save control. There is no Cmd+S
shortcut and no Escape handler, so a covered top bar makes Save unreachable until the panel is closed.

### 3.7 Grid writers and `isAutofilled` (G12, UI side)

**[SPEC]**
- Each cell gains a boolean `isAutofilled`. The autofill merge (`mergeGridPreserveThemeLocked` and the
  "Keep partial fill" path of §2.3) sets it on a letter it wrote into a cell that was empty at Start,
  and on no other cell.
- **Every other UI writer clears it** on the cell it changes: `setLetter`, `toggleBlackSquare` (both the
  cell and its symmetric partner), `handlePatternSelect`, `handleThemeWordApplied`, `handleGridImport`,
  `handleCleanGrid`, and New grid (§3.2). A cell the user retypes with the same letter is user-typed.
- Saved grids carry the field per cell (§3.4); an entry without it reads as `false`. JSON export may
  include it; import ignores it, so every imported letter counts as typed.
- The UI sends only cells with a letter and `isAutofilled` false as locked letters; the lock channel
  through the route and the CLI argv is §2. This section owns the flag and its writers, §2 owns what is
  locked.

---

## 4. Word lists and CLI rulings (#57)

**[SPEC]**
- **Item 1 (L11):** the word-list line parser folds letters to A–Z with Unicode NFKD decomposition,
  dropping combining marks (`CAFÉ` → `CAFE`, `NAÏVE` → `NAIVE`, `ÜBER` → `UBER`). A word that still
  contains a non-A–Z letter after folding is skipped with reason `not letters only`. The upload preview
  shows the folded word. `ß`, `Æ` and `Ø` have no NFKD decomposition and are skipped with that reason.
  The fold lives in the shared load path, `WordList.from_file → parse_line → add_words` in
  `cli/src/fill/word_list.py`, so the solver and the upload preview fold identically (the solver loads
  lists via `from_file`, not through the upload parser). `WordList._is_valid_word` is tightened from
  `isalpha()` plus `isupper()`, which accept non-ASCII letters, to require ASCII A–Z.
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
  - Getting the code: "Download ZIP" from GitHub, or `git clone`. After a ZIP extract the README's
    `chmod +x setup.sh` line is part of the steps.
  - One line: Windows is not supported yet.
- **README "Using the app"**: a short tour, one or two lines per visible tool (Grid, Lists, Search,
  Theme, Autofill, Import/Export), naming the controls as they appear on screen.
- **`setup.sh`:**
  - The existing Python ≥3.9 and Node ≥18 checks print `Missing: <tool> <minimum version> — install from
    <url>` (python.org/downloads, nodejs.org) and exit 1. An `npm` check is added in the same form.
  - After `python3 -m venv`, `setup.sh` checks that `venv/bin/pip` exists. If not (Debian and Ubuntu
    without `python3-venv` leave a partial `venv/`), it removes the venv it just created and prints
    `Install python3-venv (for example: sudo apt install python3-venv), then run ./setup.sh again`,
    and exits 1. The "already exists" branch runs the same check, so a partial venv from an earlier
    run is repaired rather than trusted.
  - `package.json` gains `"engines": {"node": ">=18"}`, matching the README floor. **[?]** Whether the
    repo also gets an `.nvmrc` is open; this spec does not require one.
  - `npm install` becomes `npm ci`, which never writes `package-lock.json`, so setup leaves the tracked
    tree clean (#49). `npm ci` fails outright if `package.json` and the lock disagree, so the plan first
    runs it on a fresh clone with the Node LTS the README names; if it fails, the lock is regenerated
    once with that Node and committed, and SETUP-1, SETUP-3 and E2-SETUP-1 confirm it.
- **`run.py`:** `debug=False` by default; `FLASK_DEBUG=1` turns debug on. The docstring and the README's
  dev-mode section say so.
- **Port (I6):** `run.py` reads the `PORT` environment variable, default 5000 (it hard-codes 5000 today).
  On "address already in use" it prints `Port <n> is in use. Start with PORT=<other> python3 run.py`
  instead of a traceback. **[?]** On a stock macOS, AirPlay Receiver may hold :5000; this is from
  general knowledge, not measured here, so the plan checks `lsof -i :5000` on a stock Mac. The Vite
  proxy target in `vite.config.js` is `http://localhost:5000` and would need to follow `PORT`; how is
  left to the plan.

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
| New: ZIP | SETUP-1 and the README `pattern`, `analyze` and `fill` examples on a GitHub "Download ZIP" extract (not a clone), following the README's `chmod +x setup.sh` | Setup completes; the examples run; Search for `C?T` returns CAT, COT and CUT; `chmod +x` alone is enough |
| New: LINUX | `./setup.sh` on Debian or Ubuntu with and without `python3-venv`; `npm ci` on Node 18 | With: completes. Without: exits 1 with the `Install python3-venv` message and no partial `venv/` left; a re-run after installing it succeeds. Node 18: `npm ci` completes and leaves `package-lock.json` unchanged |
| Grid | G1, G3, G8, G9 | New grid, discoverable black squares, no Heatmap toggle, save restored |
| New: SAVE-NAMED | Autosave a grid, then Save under a name, Open saved, Delete; fill storage until a write fails | Autosave keeps one entry per grid; the name prompt appears only on Save; Open asks the confirm; the quota text shows on an explicit Save |
| Grid guards | New: SR-PLACE (place a Search result across a black square and a theme-locked cell); new: CL-CLEAR (Verify flags cells, retype them, Clean) | Protected cells unchanged; no red cells after "Grid is clean" |
| New: CL-CLEAN-GUARD | Theme-lock a word, type an invalid word elsewhere, press Clean; once with Cancel, once with the confirm accepted | The confirm shows `Clean will remove N letters` with `N` equal to the typed invalid letters only; Cancel changes nothing, including `isError`; accepting removes those letters and every theme-locked letter is unchanged |
| Hidden | CL1, A-SBS, new: EXPORT-HIDE | Control absent; the Export panel shows no PDF or `.puz` option, no "Include clues" checkbox, and no PDF or `.puz` line under Format Information |
| New: TH5 | Open the Theme panel at the desktop viewport and at the narrowest width the app supports | The top bar and Save are visible and clickable; Save succeeds with the panel open |
| Autofill | A2, A3, A4 | Panel returns to idle by itself; every letter typed before Start is unchanged |
| Lists, CLI | L11, SR4, CLI-normalize | Per §4 |
| New: AF-LOCK | Type letters, run Repair on the 11x11, cancel and let one run end | Typed letters intact in every progress sample and at the end |
| New: AF-BLOCK | Type a partial pattern no word fits (e.g. `QX` in the first two cells of a 3-letter slot, pattern `QX?`; a fully typed off-list word is case 2, not a block) | Run does not start; those cells red; message as §2.3 |
| New: AF-DEFAULTS | Press Start with all panel defaults on the shipped 11x11 and 15x15 example grids, after typing a few letters | `Successfully filled`; every typed letter intact |
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
