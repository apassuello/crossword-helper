# Clue Authoring — Design
**Version 0.1.0** · Claude with Arthur Passuello · 2026-10-31 · status: draft. Every section was approved by the
owner in chat on 2026-10-31, the layering after the CLI-first ruling. Owner review of the written spec is pending.
§9's defaults apply if unruled by 2026-11-14.

---

## AI READING INSTRUCTION

Read `[SPEC]` blocks for authoritative behaviour. Read `[NOTE]` only for context. `[?]` blocks are unverified.
Issue numbers are GitHub issues on `apassuello/crossword-helper`. "Novice spec" means
`docs/superpowers/specs/2026-10-23-novice-readiness-design.md` at version 0.2.23. Names marked as forward
references do not exist yet: this spec introduces them.

---

## 0. Scope and decomposition

**[SPEC]** The clue feature is four sub-projects, each with its own spec, plan and build. This spec is
sub-project 1.

| # | Sub-project | Depends on | Interface to sub-project 1 |
|---|---|---|---|
| 1 | Clue model and authoring (this spec) | — | — |
| 2 | Export with clues (HTML first; PDF and `.puz` later) | 1 | Reads the clue map and each clue's status |
| 3 | Clue lookup (past clues for an answer, from a local corpus) | 1 | Writes a chosen clue's text through the commit path of §4 |
| 4 | AI clue drafts | 1, may use 3 | Same as 3 |

Out of scope here: clue text in any export other than the grid JSON file; lookup; drafts; carrying NYT clues
through `import-nyt`.

---

## 1. Rulings (owner, 2026-10-31)

**[SPEC]**
- **Scope:** authoring, export, lookup and AI drafts are all in scope, built in the order 1 → 2 → {3, 4}.
- **Clue identity:** a clue belongs to its entry's start cell and direction, and records the letters it was
  written for. Changed letters make it **stale**; a destroyed entry makes it **orphaned**. A clue is never
  silently lost. **What it beat:** a clue following its answer word (surprising with repeated words, and a
  one-letter fix makes a clue vanish); a slot with no tracking (a refill silently leaves a clue describing
  another word).
- **Where clues are written:** a Clues panel only. **What it beat:** a focused-entry box under the grid as well
  (an extra component and focus rules, for a clue-while-filling workflow the owner does not use); a box only
  (no overview for a final pass).
- **Stale rule:** any change of the entry's letters, including filling a blank. **What it beat:** only
  contradictions (fewer false alarms, one more rule); no stale tracking.
- **Where clue state lives:** in the document, saved, undone and dirty-tracked with it (approach A). **What it
  beat:** a separate store keyed by document id (no undo, and two lifecycles to keep in step); a backend store
  (one document split across two stores).
- **Layering:** CLI-first. The CLI owns the clue model, its validation, the authoritative status and the
  grid-file round trip. React holds the live document and shows a status reconciled from the server. **What it
  beat:** an owner-ruled exception keeping validation and status in the browser.
- **Grid-file import and export:** clue validation goes through the CLI; the browser's existing import and
  export code stays as it is and is recorded as tech debt (§8). **What it beat:** moving import and export to
  the CLI now (removes the drift, but refactors shipped, hardened code inside this feature); a ruled exception
  with two validators.

---

## 2. Rule conformance

**[SPEC]** The rules, quoted from their sources:

- **R1** (`.claude/CLAUDE.md`, Architecture): "All crossword logic lives in `cli/`."
- **R2** (`.claude/CLAUDE.md`, Code Patterns): "New capability: CLI command → `cli_adapter.py` method → Flask
  route → React. Never skip a layer."
- **R3** (`.claude/CLAUDE.md`, Code Patterns): "the backend↔CLI boundary needs a contract test on argv
  acceptance plus one real subprocess e2e."
- **R4** (`src/hooks/useGridGeometry.js` header): "the GUI MAY compute slot extents, focused-slot pattern
  strings, and the 180° symmetry mirror. It MUST NOT compute word validity, scores, candidate lists, or fills".
- **R5** (`src/hooks/useNumbering.js` header): numbering is computed in the browser for display and always
  reconciled from the server, which is authoritative.
- **R6** (`.claude/CLAUDE.md`, Anti-Patterns): `docs/api/openapi.yaml` is "the documented single source of
  truth for endpoints".

| Component | Layer | Permitted by |
|---|---|---|
| Clue map parsing and validation (§3.1, §3.4) | CLI, a new `clues` module in `cli/src/core/` | R1 |
| Authoritative clue status (§3.2) | CLI, through `GridNumbering.get_clue_positions` | R1 |
| Grid-file round trip of `clues` (§3.5) | CLI commands `fill` and `resume`; the pause state | R1 |
| `crossword clues check` (§3.6) | CLI | R2 |
| Adapter method and `POST /api/clues/check` (§3.6) | backend | R2, R6 |
| Display status in the panel, reconciled from the route (§5.6) | React | R4, with the R5 pattern |
| Document state, signatures, undo, save (§4) | React | Persistence is the browser save machine's job (novice spec §3.4; `src/lib/storage.js` header). Not crossword logic |
| Clues panel (§5) | React | R2, the last layer |
| Replacement-confirm predicate (§4.5) | `src/lib/gridEdits.js` | Novice spec §3.2, its existing home |
| Browser grid-file parsing and serialization | React | **No rule permits it.** Existing drift, retained by ruling (§1) and recorded in §8 |

---

## 3. Data model and formats

### 3.1 The clue map

**[SPEC]** The document gains `clues: { [key]: { text, answer } }`.
- **`key`:** `"<row>,<col>,<dir>"`, rows and columns counted from 0 like `numbering`, `dir` one of `across`
  and `down`. Example: `"0,0,across"`. A clue is never keyed by its number, which changes whenever a black
  square moves.
- **`text`:** the committed text with leading and trailing whitespace trimmed, 1 to 200 characters.
- **`answer`:** the entry's letters when the text was committed, in the pattern format of `slotAt`: A–Z, and
  `?` for an empty square. Example: `"RO?E"`.
- Nothing else is stored. Status is derived (§3.2).

### 3.2 Status

**[SPEC]** A clue's status is one of `ok`, `stale`, `orphaned`:
- `orphaned` when no entry starts at `(row, col)` in `dir`. An entry starts there when the CLI's numbering
  rule says so (`GridNumbering.auto_number`: left or above is black or the edge, and the next cell in `dir`
  exists and is white). Entries of length 2 are entries.
- `stale` when the entry exists and its current pattern differs from `answer`. A change of length is a
  difference.
- `ok` otherwise.

Pinned on a row reading `ROSE`, clue `"0,0,across"` written for `ROSE`:

| Grid change | Status |
|---|---|
| none | `ok` |
| `ROSE` becomes `RODE` | `stale` |
| the `S` is cleared (`RO?E`) | `stale` |
| (0,2) made black, so the entry is `RO` | `stale` |
| (0,0) made black | `orphaned` |
| (0,0) still white but no longer starts an across entry | `orphaned` |

The same table holds for `down`. This table is a shared fixture (§6.1).

### 3.3 Commit, Keep and Delete

**[SPEC]**
- **Commit** of a field's text: the trimmed text equals the committed text → nothing happens: no write, no undo
  step, and a stale clue stays stale. Trimmed text empty → the entry is removed. Otherwise → the entry
  becomes `{text, answer: <the entry's current pattern>}`, which clears stale.
- **Keep** (stale clues only): `answer` becomes the current pattern; `text` is unchanged.
- **Delete** (orphaned clues only): the entry is removed.

### 3.4 Validation

**[SPEC]** One validator, in the CLI. Checked in this order; the first failure rejects the whole map with
`Invalid clue "<key>": <reason>.`:
1. `clues` is an object. Otherwise the message is `Invalid clues: must be an object.`
2. Each key matches `^(\d+),(\d+),(across|down)$` with row and column below `size`. Reason:
   `key must be "row,col,across" or "row,col,down" inside the grid`.
3. Each value is an object with string `text` and string `answer`. Reason: `must have text and answer strings`.
4. `text` after trimming is 1 to 200 characters. Reason: `text must be 1 to 200 characters`.
5. `answer` matches `^[A-Z?]{2,}$`. Reason: `answer must be 2 or more of A-Z or ?`.

Keys orphaned in the grid are valid; they show as orphaned. Keys are checked in sorted order, so the reported
key does not depend on the file's key order.

### 3.5 Grid file and saved document

**[SPEC]**
- **Saved document** (browser storage): `{id, size, grid, numbering, symmetryEnabled, clues}`. An entry saved
  before this feature has no `clues` and loads as `{}`.
- **Grid JSON file, browser:** Export always writes `clues` (`{}` when there are none). Import with no `clues`
  key applies `{}`. Import with a `clues` key first sends `{size, grid, clues}` to `POST /api/clues/check`; a
  rejection shows the CLI's message and applies nothing. If the request fails (no response, or a status other
  than 200 or 400), the import is refused with `Could not check the clues: <error>.` and nothing is applied.
- **Grid JSON file, CLI:** every command that reads a grid file and writes a grid file carries the input's
  `clues` unchanged: `fill`'s pause write and result write, including the default in-place write to the input
  file. The pause state stores the input's `clues` as an opaque value that the solver never reads, and `resume`
  writes them into its output. `new` and `import-nyt` write no `clues`. A file with no `clues` key gets none.
- **`reference/file-formats.md`** gains the `clues` row (§7).

### 3.6 CLI command and route

**[SPEC]**
- `crossword clues check <grid.json> [--allow-nonstandard] --json-output` <!-- docs-check: allow (forward reference: command introduced by this spec) -->
  - valid → exit 0, `{"success": true, "statuses": {"<key>": "ok" | "stale" | "orphaned", ...}}` with one
    entry per clue;
  - invalid → exit 1, `{"success": false, "error": "<the §3.4 message>"}`;
  - a grid file with no `clues` key → `{"success": true, "statuses": {}}`.
- **Adapter:** a method on `CLIAdapter` that writes the request to a temporary file and runs the command, as
  `number` does.
- **Route:** `POST /api/clues/check`, body `{size, grid, clues}`. The body passes `validate_grid_request` for its
  `size` and `grid`; the route does not inspect `clues` (the CLI is the only validator). A CLI rejection →
  400 `{"error": {"code": "INVALID_CLUES", "message": "<the §3.4 message>"}}` in the shape of `handle_error`;
  timeout → 504; other failures → 500. `allow_nonstandard` follows `/api/number`'s rule (sizes other than 11, 15,
  21). Documented in `docs/api/openapi.yaml`.

---

## 4. Signatures, undo and save

### 4.1 Two signatures

**[SPEC]** `src/lib/contentSig.js` keeps `contentSigOf(size, grid)`, the **grid signature**, unchanged, and gains
the **document signature**: the grid signature's content plus the clues as `[key, text, answer]` triples sorted
by key. Two maps with the same entries give byte-identical strings whatever their insertion order.

| Consumer | Site | Reads |
|---|---|---|
| Dirty state (`contentSig`, `isDirty`) | `App.jsx` | document |
| Clean point (`savedSig`) after a save, open, restore, New grid, import | `App.jsx` (`onSaved`, `adoptSavedEntry`, `initializeGrid`, `handleGridImport`) | document |
| The save machine's `contentSig` (re-arms autosave after `forget()`) | `useSaveMachine.js` | document |
| Undo snapshot and step decision | `lib/history.js` `snapshotContent`, `useUndoHistory.js` | document |
| Restored-banner close | `App.jsx` | document |
| Clean confirm dismissal | `App.jsx` (`pendingClean`) | grid |
| Theme suggestion staleness | `ThemeWordsPanel.jsx` (its own signature) | grid, unchanged |
| Numbering | `useNumbering.js` (`structuralSigOf`) | unchanged |

### 4.2 Lifecycle

**[SPEC]** New grid and a grid-size change start with `clues = {}`; import applies the file's map (§3.5); Open
and restore apply `entry.clues ?? {}`. All of them clear the undo history, as they do today. A save fork keeps
both the clues and the history.

### 4.3 Undo

**[SPEC]**
- A snapshot holds `clues` alongside the grid fields, and its signature is the document signature. Restore
  writes the clues back. Snapshots of the grid alone are recorded with the current clues; this is correct because
  grid edits never change clues and clues cannot change during a run (§4.4).
- **One step each:** a commit that changes the map, Keep, Delete. **Not steps:** keystrokes in a clue field.
  In-field Cmd/Ctrl+Z is the browser's text undo (`App.jsx` already leaves those keys to an `input`).
- A commit while an Apply All batch is open belongs to that batch's step, as every other edit does (novice
  spec §3.9).
- An undo or redo that changes only clues is not a grid change, so it does not dismiss an open Clean confirm.

### 4.4 Gating during a run

**[SPEC]** Commit, Keep and Delete join the novice spec's D1 writer list (§2.3): disabled while a run is live,
and each returns early when the check fails at write time. The notice stays on the grid only.

### 4.5 Replacement confirm

**[SPEC]** The confirm asked before New grid, a grid-size change, Open saved and Import fires when the
document has content: `gridHasContent(grid)` or at least one clue. The new predicate sits in
`src/lib/gridEdits.js` beside `gridHasContent` and replaces it at the three call sites (`GridPanel.jsx` for New
grid and Open, and `App.jsx`'s `gridHasContent` prop to `ImportPanel`).

### 4.6 An Open that waits

**[SPEC]** Novice spec §3.4 accepts that letters typed into an empty grid during a waiting Open are lost
unannounced. With §4.5, a document with clues is not empty, so the confirm shows. On a document with no
content, a clue committed during the wait is lost unannounced in the same way, and is accepted on the same terms.

---

## 5. Clues panel

### 5.1 Rail

**[SPEC]** A `Clues` tool, id `clues`, between `Autofill` and `Theme` in the rail, with a three-line icon (three
horizontal strokes, the last one shorter). It is an ordinary tool: it replaces the inspector, and selecting it
closes the Theme panel by the existing path (novice spec §3.6).

### 5.2 Layout

**[SPEC]** Styles are the existing `.xw-clue*` and `.xw-clues*` classes in `src/styles/bench/base.css`.
- **Header:** title `Clues`. Sub-line `<A> across · <D> down`, followed by ` · <S> stale` and ` · <O> orphaned`
  when those counts are not zero.
- **Groups:** `Across`, then `Down`, each headed `<Across|Down> · <count>`. Rows are in number order. An empty
  group shows `No across words yet.` or `No down words yet.`
- **Row:** a number button (the start cell's number, `–` before numbering has assigned one); the entry's
  squares as small boxes, a letter or `·` each; a text input with placeholder `Write a clue…` and a maximum
  length of 200.
- **Stale row:** also shows `Written for <answer>` with each `?` shown as `·`, and a `Keep` button.
- **Orphaned section:** after Down, only when there are orphans. Heading `Orphaned · <count>`, then the line
  `These entries no longer exist. Copy a clue into an entry, or delete it.` Each item shows its recorded
  answer as boxes, its text (read-only and selectable) and a `Delete` button. Items are ordered by row, then
  column, then across before down.

### 5.3 Selection

**[SPEC]**
- Focusing a row's input, or clicking its number, sets the selection to the entry's start cell and direction,
  so the grid highlights the entry. Clicking the number also focuses that row's input.
- When the selection changes on the grid, the row for the entry under it in its direction is highlighted
  (`.on`) and scrolled into view with `block: 'nearest'`. The grid keeps focus.

### 5.4 Keys in a clue input

**[SPEC]** Enter commits and focuses the next row's input; after the last Across row comes the first Down row,
and on the last Down row focus stays. Escape restores the committed text and keeps focus. Leaving the field
commits. Grid keys never reach the grid from a clue input: `CrosswordGrid` listens on its own container.

### 5.5 Disabled state

**[SPEC]** While a run is live, the inputs, `Keep` and `Delete` are disabled, following the existing panel
pattern (an `editingPaused` prop). Number buttons still select: selecting is not a write.

### 5.6 Status display and reconciliation

**[SPEC]** The panel shows each clue's status as computed in the browser by the §3.2 rule, for display only
(R4). It calls `POST /api/clues/check` when it opens and whenever the document signature changes while it is
open, 300 ms after the last change. Only the reply to the latest request is applied, by the request-token
pattern `ThemeWordsPanel` uses. The server's statuses replace the browser's. A failed request changes nothing
and shows nothing.

---

## 6. Testing

### 6.1 CLI (pytest)

**[SPEC]**
- **Validation:** each §3.4 rule, asserting its exact message; keys reported in sorted order; an orphan key is
  valid.
- **Status:** the §3.2 table for both directions, read from one JSON fixture that the frontend tests also read.
  A length-2 entry's clue is `ok`.
- **Round trip:** `fill grid.json` with the in-place default keeps `clues`; `fill -o` keeps them; a file with no
  `clues` gets none.
- **Seam (R3):** an argv contract test that the adapter's `clues check` arguments are accepted by the real CLI
  parser; one real-subprocess end-to-end test from the route through the adapter to the CLI; one real fill,
  pause and resume end-to-end test in which the resumed file keeps `clues`.

### 6.2 Frontend (vitest)

**[SPEC]**
- **Pure functions:** the browser status rule against the shared fixture; the document signature (changes on a
  clue edit, changes on a grid edit, identical for the same entries in another insertion order); the grid
  signature unaffected by clues; a history snapshot holds clues and restore writes them; the replacement
  predicate is true for a white grid with one clue and false with none; a saved entry without `clues` loads `{}`.
- **Undo:** one changed commit is exactly one step; typing five characters then leaving is one step; undo
  restores the text and redo reapplies it; undo back to the saved content leaves the document clean; a clue-only
  undo leaves an open Clean confirm open; a commit during an open Apply All batch belongs to its step.
- **Save:** a commit makes the document dirty and a save makes it clean; Open restores clues; after `forget()`,
  a clue commit re-arms autosave; a clue commit closes the restored banner.
- **Confirm:** New grid, Open saved and Import each ask on a white grid with a clue.
- **Gating:** during a run the controls are disabled, and a handler called anyway writes nothing.
- **Import:** a file with `clues` calls the route; a 400 shows the CLI's message and applies nothing; a failed
  request refuses the import with `Could not check the clues: <error>.` and leaves the grid unchanged.
- **Panel:** rows in number order; a stale row shows `Written for` and `Keep`, and Keep clears it; orphans in key
  order, Delete is one step; Enter moves on and passes from Across to Down; Escape restores; a number click
  selects the entry; a grid selection highlights its row; only the latest reconcile reply is applied.
- **Rail:** the existing assertions that Clues and the Heatmap toggle are absent are split; Heatmap stays absent,
  Clues is present.

### 6.3 Mutation proof

**[SPEC]** Each test below counts only when the named defect, introduced on purpose, makes its target assertion
fail at its own line (CONTRIBUTING §3).

| Defect introduced | Test that must fail |
|---|---|
| The snapshot signature reverts to the grid signature | one changed commit is exactly one step |
| The replacement predicate ignores clues | New grid asks on a white grid with a clue |
| The document signature does not sort entries | identical for another insertion order |
| `isDirty` reads the grid signature | a commit makes the document dirty |
| `fill`'s result write drops `clues` | `fill grid.json` keeps `clues` |

### 6.4 Acceptance (driven in the browser)

**[SPEC]**

| Id | Steps | Expected |
|---|---|---|
| CLU-1 | Write a clue, Save, reload the page | The clue is in its row |
| CLU-2 | Change one letter of a clued entry | `Written for …` and `Keep` show; Keep clears them |
| CLU-3 | Make a clued entry's start square black; Delete the orphan; Undo | The orphan is listed; it goes; Undo brings it back |
| CLU-4 | Commit a clue, click the grid, press Cmd+Z | The clue reverts |
| CLU-5 | Start a run; try a clue input, Keep and Delete | All disabled; the grid shows `Editing is paused while autofill runs.` |
| CLU-6 | On a white grid with one clue, choose New grid | The confirm shows |
| CLU-7 | Export JSON with an orphaned clue; New grid; Import the file | The clues are back, the orphan included |
| CLU-8 | Export a clued grid; run `crossword fill` on the file in a terminal; Import the result | The clues are still there |

---

## 7. Amendments to other documents

**[SPEC]** Applied when this feature is built, not before: the novice spec belongs to the release in progress.

**Novice spec:**
- §2.3 D1, the writer list: after "Undo and Redo §3.9" add ", and the Clues panel's commit, Keep and Delete
  (clue-authoring spec §4.4)".
- §3.1: remove "the Clues tool in the tool rail (#53),". Add: "The `Include clues (if available)` checkbox
  stays hidden until clue export (clue-authoring spec §0, sub-project 2)."
- §3.4, An Open that waits: replace "when it was empty, Open shows no confirm" with "when it had no content
  (§3.2: no letters, black squares or clues), Open shows no confirm", and add "Clues committed during the wait
  are lost on the same terms."
- §3.4, Banner: replace "on any grid edit" with "on any edit, to the grid or to a clue".
- §3.4, Deleting the open grid's own entry: replace "The next grid edit autosaves it" with "The next edit, to the
  grid or to a clue, autosaves it".
- §3.9, What one step is: add "committing a changed clue, Keep, and deleting an orphaned clue (one committed
  clue is one step; beat: a step per keystroke)".
- §3.9, What a step holds: replace "exactly the fields `contentSigOf` reads (size and each cell's `letter`,
  `isBlack`, `isThemeLocked`, `isAutofilled`)" with "exactly the fields the document signature reads: size,
  each cell's `letter`, `isBlack`, `isThemeLocked` and `isAutofilled`, and the clue map (clue-authoring spec
  §4.1)".
- §6, AF-GATE: add "the Clues panel's inputs, Keep and Delete" to the list of writers.

**Code comments:** the `ToolRail.jsx` header ("Not rendered … the Clues tool (#53)") keeps the Heatmap only; the
`useSaveMachine.js` comments that say "grid edit" for the `contentSig` re-arm say "edit, to the grid or to a
clue"; the `gridHasContent` docstring's purpose ("replacing the grid would lose work") moves to the new
predicate.

**Tests:** `App.test.jsx` ("renders no Clues tool and no Heatmap toggle") and `ToolRail.test.jsx` ("does not
render the Clues tool or the Heatmap toggle") are split (§6.2). `ExportPanel.test.jsx`'s `Include clues`
assertion is unchanged.

**User documentation:**
- `README.md`, the tool list after "The tool rail on the left switches between tools": add Clues.
- `docs/user-guide/tutorials/first-crossword.md`, the tool-rail sentence: add Clues.
- `docs/user-guide/reference/web-app.md`: the left-rail section gains Clues; the "not shown in the interface"
  paragraph drops "a Clues tool" and keeps `Include clues`.
- `docs/user-guide/how-to/import-and-export-grids.md`: "The exports hold the grid only; they have no clues"
  becomes: the JSON export carries clues; the HTML export has none.
- `docs/user-guide/reference/file-formats.md`: a `clues` row in the grid-file table; the HTML export's "with no
  clues" stays true.
- A new how-to for writing clues, covering stale clues, Keep and orphans.
- `cli/README.md`: the `clues check` command.

**API:** `docs/api/openapi.yaml` gains `POST /api/clues/check`.

---

## 8. Tech debt recorded

**[SPEC]** The browser parses and validates the grid part of an imported grid file (`ImportPanel.jsx`) and
serializes the exported file (`ExportPanel.jsx`). No rule permits this, `Grid.from_dict` already validates the
same format, and there is no import or export route. It is retained by ruling (§1). One tech-debt issue
records it when this feature is built.

---

## 9. Open points (default applies if unruled by 2026-11-14)

| Id | Section | Question | Default |
|---|---|---|---|
| CA-1 | §3.1 | Maximum clue length | 200 characters |
| CA-2 | §3.5 | Carry `clues` through the pause state so `resume` keeps them | Yes, as an opaque value |
| CA-3 | §5.6 | Reconcile delay after the last change | 300 ms |
| CA-4 | §8 | File the tech-debt issue | When this feature is built |
| CA-5 | §0 | A feature issue for clue authoring (#53 was closed by hiding the tool) | The owner files it |

---

## 10. Amendment record

- 0.1.0 (2026-10-31): first written version, from the sections approved in chat on 2026-10-31.
