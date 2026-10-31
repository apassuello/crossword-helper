# Clue Authoring — Design
**Version 0.1.3** · Claude with Arthur Passuello · 2026-10-31 · status: approved at 0.1.2; 0.1.3's §3.5
amendment awaits owner review. Every section was approved by the owner in chat on 2026-10-31, the layering after
the CLI-first ruling; 0.1.1 applies the first review (§10). The owner approved the written spec on 2026-10-31.
§9's defaults apply if unruled by 2026-11-14.

---

## AI READING INSTRUCTION

Read `[SPEC]` blocks for authoritative behaviour. Read `[NOTE]` only for context. `[?]` blocks are unverified.
Issue numbers are GitHub issues on `apassuello/crossword-helper`. "Novice spec" means
`docs/superpowers/specs/2026-10-23-novice-readiness-design.md` at version 0.2.23. Names marked as forward
references do not exist yet: this spec introduces them. Code that implements a decision of §1 cites it as
"Decision N (clue-authoring spec 0.1.3, section 1)".

---

## 0. Scope and decomposition

**[SPEC]** The clue feature is four sub-projects, each with its own spec, plan and build. This spec is
sub-project 1.

| # | Sub-project | Depends on | Interface to sub-project 1 |
|---|---|---|---|
| 1 | Clue model and authoring (this spec) | — | — |
| 2 | Export with clues (HTML first; PDF and `.puz` later) | 1 | Reads the clue map and each clue's status |
| 3 | Clue lookup (past clues for an answer, from a local corpus) | 1 | Writes a chosen clue's text through the commit path of §3.3 |
| 4 | AI clue drafts | 1, may use 3 | Same as 3 |

Out of scope here: clue text in any export other than the grid JSON file; lookup; drafts; carrying NYT clues
through `import-nyt`.

---

## 1. Decisions (owner, 2026-10-31)

**[SPEC]**
- **Decision 1, scope:** authoring, export, lookup and AI drafts are all in scope, built in the order
  1 → 2 → {3, 4}.
- **Decision 2, clue identity:** a clue belongs to its entry's start cell and direction, and records the
  letters it was written for. Changed letters make it **stale**; a destroyed entry makes it **orphaned**. A clue
  is never silently lost. **What it beat:** a clue following its answer word (surprising with repeated words,
  and a one-letter fix makes a clue vanish); a slot with no tracking (a refill silently leaves a clue describing
  another word).
- **Decision 3, where clues are written:** a Clues panel only. **What it beat:** a focused-entry box under the
  grid as well (an extra component and focus rules, for a clue-while-filling workflow the owner does not use);
  a box only (no overview for a final pass).
- **Decision 4, stale rule:** any change of the entry's letters, including filling a blank. **What it beat:**
  only contradictions (fewer false alarms, one more rule); no stale tracking.
- **Decision 5, where clue state lives:** in the document, saved, undone and dirty-tracked with it. **What it
  beat:** a separate store keyed by document id (no undo, and two lifecycles to keep in step); a backend store
  (one document split across two stores).
- **Decision 6, layering:** CLI-first. The CLI owns the clue model, its validation, the authoritative status and
  the grid-file round trip. React holds the live document and shows a status reconciled from the server.
  **What it beat:** an owner-ruled exception keeping validation and status in the browser.
- **Decision 7, grid-file import and export:** clue validation goes through the CLI; the browser's existing
  import and export code stays as it is and is recorded as tech debt (§8). **What it beat:** moving import and
  export to the CLI now (removes the drift, but refactors shipped, hardened code inside this feature); a ruled
  exception with two validators.

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
| Authoritative clue status (§3.2) | CLI, entries from `Grid.get_word_slots(min_length=2)` | R1 |
| Grid-file round trip of `clues` (§3.5) | CLI `fill`, `resume`, `fill --resume`; the pause state's metadata | R1 |
| `crossword clues check` (§3.6) | CLI | R2 |
| Adapter method and `POST /api/clues/check` (§3.6) | backend | R2, R6 |
| Display status in the panel, reconciled from the route (§5.6) | React | R4, with the R5 pattern |
| Document state, signatures, undo, save (§4) | React | Persistence is the browser save machine's job (novice spec §3.4; `src/lib/storage.js` header). Not crossword logic |
| Clues panel (§5) | React | R2, the last layer |
| Replacement-confirm predicate (§4.5) | `src/lib/gridEdits.js` | Novice spec §3.2, its existing home |
| Browser grid-file parsing and serialization | React | **No rule permits it.** Existing drift, retained by Decision 7 and recorded in §8 |

---

## 3. Data model and formats

### 3.1 The clue map

**[SPEC]** The document gains `clues: { [key]: { text, answer } }`.
- **`key`:** `"<row>,<col>,<dir>"`, rows and columns counted from 0 like `numbering`, written without leading
  zeros, `dir` one of `across` and `down`. Example: `"0,0,across"`. A clue is never keyed by its number, which
  changes whenever a black square moves.
- **`text`:** 1 to 200 characters, with no whitespace at either end. Characters are counted as Unicode code
  points. Whitespace is the Unicode `White_Space` set: U+0009–U+000D, U+0020, U+0085, U+00A0, U+1680,
  U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, U+3000.
- **`answer`:** the entry's letters when the text was committed, in the pattern format of `slotAt`: A–Z, and
  `?` for an empty square. Example: `"RO?E"`. Cells hold only A–Z: typing accepts only `[A-Za-z]` and import
  only `A`–`Z`.
- Nothing else is stored. Status is derived (§3.2).
- **Key order**, wherever this spec says "key order": by row, then column, numerically, then `across` before
  `down`. `"2,0,down"` comes before `"10,0,across"`.

### 3.2 Status

**[SPEC]** A clue's status is one of `ok`, `stale`, `orphaned`:
- The **entries** are the white runs of length 2 or more. In the CLI they come from
  `Grid.get_word_slots(min_length=2)`, with each `.` of its `pattern` read as `?`. In the browser they come from
  `allSlots`. `GridNumbering.get_clue_positions` is not used: it calls `get_word_slots()` at its default of
  `min_length=3`, which hides 2-letter entries.
- `orphaned` when no entry starts at `(row, col)` in `dir`.
- `stale` when the entry exists and its pattern differs from `answer`. A change of length is a difference.
- `ok` otherwise.

The shared fixture (§6.1) holds these rows literally. Grids are written as in the grid file (`#` black, `.`
empty), clue key `"0,0,across"`; the `down` rows use the same grids transposed and key `"0,0,down"`.

| Grid | `answer` | Status |
|---|---|---|
| `ROSE` `....` `....` `....` | `ROSE` | `ok` |
| `RODE` `....` `....` `....` | `ROSE` | `stale` |
| `RO.E` `....` `....` `....` | `ROSE` | `stale` |
| `RO#E` `....` `....` `....` | `ROSE` | `stale` (the entry is now `RO`) |
| `RO#E` `....` `....` `....` | `RO` | `ok` (a 2-letter entry) |
| `#OSE` `....` `....` `....` | `ROSE` | `orphaned` |
| `R#SE` `....` `....` `....` | `ROSE` | `orphaned` ((0,0) starts no across entry) |

### 3.3 Commit, Keep and Delete

**[SPEC]**
- **Commit** of a field's draft, checked in this order: the draft trimmed of whitespace (§3.1) equals the
  committed text, or is empty with no clue committed → nothing happens: no write, no undo step, and a stale clue
  stays stale. Trimmed draft empty → the entry is removed. Trimmed draft over 200 characters → refused: no
  write, the field keeps the draft, and the row shows `At most 200 characters.` until the draft changes.
  Otherwise → the entry becomes `{text: <trimmed draft>, answer: <the entry's current pattern>}`, which clears
  stale.
- **Keep:** `answer` becomes the entry's current pattern as the browser computes it; `text` is unchanged.
- **Delete:** the entry is removed.
- Keep is shown on rows whose displayed status (§5.6) is `stale`; Delete on items whose displayed status is
  `orphaned`.

### 3.4 Validation

**[SPEC]** One validator, in the CLI. The first failure rejects the whole map:
1. `clues` is an object (not `null`, not an array). Otherwise: `Invalid clues: must be an object.`
2. Every key is an ASCII full match of `^(0|[1-9][0-9]*),(0|[1-9][0-9]*),(across|down)$` with row and column
   below `size`. Keys are checked in code-point string order. Reason: `key must be "row,col,across" or
   "row,col,down" inside the grid`.
3. Then, key by key in key order (§3.1), rules 3 to 6 in turn. The value is an object with string `text` and
   string `answer`. Reason: `must have text and answer strings`.
4. `text` has no whitespace at either end. Reason: `text must not start or end with whitespace`.
5. `text` is 1 to 200 characters. Reason: `text must be 1 to 200 characters`.
6. `answer` is an ASCII full match of `^[A-Z?]{2,}$`. Reason: `answer must be 2 or more of A-Z or ?`.

Rules 2 to 6 report `Invalid clue "<key>": <reason>.` Keys orphaned in the grid are valid; they show as
orphaned.

### 3.5 Grid file and saved document

**[SPEC]**
- **Saved document** (browser storage): `{id, size, grid, numbering, symmetryEnabled, clues}`. An entry with no
  `clues` loads as `{}`. `isAdoptableEntry` gains: `clues`, when present, is a plain object whose every value is
  an object with string `text` and string `answer`; otherwise the entry is not adoptable, and Open shows the
  existing `Could not open this saved grid.`
- **Grid JSON file, browser export:** always writes `clues` (`{}` when there are none). `ExportPanel` receives
  the clue map.
- **Grid JSON file, browser import:**
  - `validateImportedData` returns `clues` alongside `size`, `grid` and `numbering`, and the import handler
    applies it.
  - The existing replacement confirm (§4.5) comes first. Then, if the file has a `clues` key (including `{}`
    and `null`), `{size, grid, clues}` is sent to `POST /api/clues/check`. A file with no `clues` key applies
    `{}` with no request.
  - A 400 reply shows its `error.message` and applies nothing.
  - No reply, or any status other than 200 or 400, refuses the import with
    `Could not check the clues: <error>.` and applies nothing.
  - Edits made to the grid while the check runs are replaced when the import applies, on the terms an Open
    that waits already has (novice spec §3.4).
- **Grid JSON file, CLI:** the commands that write a grid file are `fill` (its pause write and its result
  write), `resume` (through `_execute_resume`), `fill --resume` (which resolves the state in `fill` itself and
  writes through `fill`'s two writes), `new` and `import-nyt`.
  - `fill` carries the input file's `clues` unchanged into both of its writes. In human mode with no `-o`,
    `fill` writes back to its input file, so the clues are kept in place. With `--json-output`, the file is
    written only when `-o` is given.
  - Every pause state saved on the `fill` path stores the input's `clues` as `metadata["clues"]`. The save
    sites are the CSP engine (`autofill.py`), the beam orchestrator (`beam_search/orchestrator.py`) and the
    CLI's state for other algorithms (`cli.py`); the CLI passes the value to the engines. The solver never
    reads it.
  - `resume` and `fill --resume` read `metadata["clues"]` and write it into their output and into any pause
    state they save. With `--resume`, the `clues` of a grid file also given are not read: the saved state is
    authoritative, as it already is for the grid (`fill`: "--resume wins when both are given"). A state with no
    `clues` in its metadata gives output with none. The backend's resume route re-saves `**metadata` and so
    keeps it with no change.
  - `new` and `import-nyt` write no `clues`. Input with no `clues` key gives output with none.
- **`docs/user-guide/reference/file-formats.md`** gains the `clues` row (§7).

### 3.6 CLI command and route

**[SPEC]**
- `crossword clues check <grid.json> [--allow-nonstandard] --json-output` <!-- docs-check: allow (forward reference: command introduced by this spec) -->
  - valid → exit 0, `{"success": true, "statuses": {"<key>": "ok" | "stale" | "orphaned", ...}}` with one
    entry per clue;
  - a §3.4 failure → exit 1, `{"success": false, "code": "INVALID_CLUES", "error": "<the §3.4 message>"}`;
  - a grid the CLI cannot load → exit 1, the existing `{"success": false, "error": ...}` with no `code`;
  - a grid file with no `clues` key → `{"success": true, "statuses": {}}`.
- **Adapter:** a method on `CLIAdapter` that writes the request to a temporary file, as `number` does, and runs
  the command with `check_success=False`, so a rejection's stdout is read rather than raised as
  `CalledProcessError`.
- **Route:** `POST /api/clues/check`, body `{size, grid, clues}`. The body passes `validate_grid_request` for its
  `size` and `grid`; the route does not inspect `clues` (the CLI is the only validator). Replies, in the
  `handle_error` shape:
  - CLI `success: true` → 200 with the CLI's JSON;
  - CLI `code: "INVALID_CLUES"` → 400, code `INVALID_CLUES`, the CLI's message;
  - any other CLI `success: false` → 400, code `INVALID_GRID`, the CLI's message;
  - output that is not JSON → 500, code `INTERNAL_ERROR`;
  - timeout → 504, code `TIMEOUT`, message `Clue check timed out`.
  `allow_nonstandard` follows `/api/number`'s rule (sizes other than 11, 15, 21). Documented in
  `docs/api/openapi.yaml`.

---

## 4. Signatures, undo and save

### 4.1 Two signatures

**[SPEC]** `src/lib/contentSig.js` keeps `contentSigOf(size, grid)`, the **grid signature**, unchanged, and gains
the **document signature**: `JSON.stringify({size, cells, clues})`, where `size` and `cells` are exactly what the
grid signature serializes and `clues` is the list of `[key, text, answer]` triples in key order. Example, one
clue on a 2×2: `{"size":2,"cells":[...],"clues":[["0,0,across","Flower","RO"]]}`. Two maps with the same entries
give byte-identical strings.

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
  writes the clues back.
- A grid edit's snapshot takes the clues as they are before the edit. App keeps them in a ref advanced the same
  way `editGrid` advances its grid ref, so a clue commit and a grid edit in one render tick are two steps, each
  with the right "before" (the novice spec §3.9 rule for two edits before one render).
- **One step each:** a commit that changes the map, Keep, Delete. **Not steps:** keystrokes in a clue field.
  In-field Cmd/Ctrl+Z is the browser's text undo (`App.jsx` already leaves those keys to an `input`).
- Clicking the Undo button while a draft is open blurs the field first, so the draft commits (one step), and
  the undo then undoes that commit.
- A commit while an Apply All batch is open belongs to that batch's step, as every other edit does (novice
  spec §3.9). Apply All is not an autofill run; §4.4 does not apply to it.
- An undo or redo that changes only clues is not a grid change, so it does not dismiss an open Clean confirm.

### 4.4 Gating during an autofill run

**[SPEC]** Commit, Keep and Delete join the novice spec's D1 writer list (§2.3): disabled while an autofill run
is live, and each returns early when the check fails at write time. The notice stays on the grid only. A run
starts only from the Autofill tool, so the Clues panel is closed, and its drafts committed (§5.4), when one
starts.

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
- **Groups:** `Across`, then `Down`, each headed `<Across|Down> · <count>`. The rows are the entries of
  `allSlots`, in reading order of their start cell (row, then column), which is number order. An empty group
  shows `No across words yet.` or `No down words yet.`
- **Row:** a number button (the start cell's number, `–` before numbering has assigned one); the entry's
  squares as small boxes, a letter or `·` each; a text input with placeholder `Write a clue…`. The input has no
  length limit; §3.3 refuses a commit over 200.
- **Stale row:** also shows `Written for <answer>` with each `?` shown as `·`, and a `Keep` button.
- **Orphaned section:** after Down, only when there are orphans. Heading `Orphaned · <count>`, then the line
  `These entries no longer exist. Copy a clue into an entry, or delete it.` Each item shows its recorded
  answer as boxes, its text (read-only and selectable) and a `Delete` button. Items are in key order (§3.1).
- Status is re-derived on every change: a clue whose entry exists again leaves the Orphaned section for its
  row, and one whose entry goes leaves its row for the Orphaned section.

### 5.3 Selection

**[SPEC]**
- Focusing a row's input, or clicking its number, sets the selection to the entry's start cell and direction,
  so the grid highlights the entry. Clicking the number also focuses that row's input.
- When the selection changes on the grid, the row for the entry under it in its direction is highlighted
  (`.on`) and scrolled into view with `block: 'nearest'`. A cell with no entry in that direction highlights no
  row. The grid keeps focus.

### 5.4 Drafts and keys

**[SPEC]**
- A draft belongs to its input. It commits (§3.3) on blur, on Enter, and when the panel unmounts (a tool
  switch). It is replaced by the committed text when the committed text changes beneath it (undo, redo), and
  discarded when the document is replaced (New grid, size change, Open, import).
- Enter commits and focuses the next row's input; after the last Across row comes the first Down row. When
  there is no next row, focus stays.
- Escape restores the committed text and keeps focus. After Enter, the committed text is the text just
  committed.
- Grid keys never reach the grid from a clue input: `CrosswordGrid` listens on its own container.

### 5.5 Disabled state

**[SPEC]** While an autofill run is live, the inputs, `Keep` and `Delete` are disabled, following the existing
panel pattern (an `editingPaused` prop). Number buttons still select: selecting is not a write.

### 5.6 Status display and reconciliation

**[SPEC]**
- The **status signature** is the grid signature plus the clue keys and answers (not the text): exactly what a
  status depends on.
- The browser computes each clue's status by the §3.2 rule, for display (R4).
- While the panel is open and no autofill run is live, it sends `POST /api/clues/check` when it opens and 300 ms
  after the status signature last changed. Each request carries the status signature it was built from.
- A reply is applied only if its status signature equals the current one. Then each clue's **displayed status**
  is the server's; a clue missing from the reply shows the browser's.
- When the status signature has moved on since the last applied reply, when a request fails, or while a run is
  live, every displayed status is the browser's. A failure shows nothing.
- Keep and Delete follow the displayed status (§3.3). Keep writes the browser's current pattern.

---

## 6. Testing

### 6.1 CLI and backend (pytest)

**[SPEC]**
- **Validation:** each §3.4 rule with its exact message; `null` and an array rejected by rule 1;
  `"00,0,across"` rejected by rule 2; key-2 errors reported in code-point order and value errors in key order;
  text with a leading U+00A0 rejected by rule 4; 200 code points accepted and 201 rejected, counting an emoji as
  one; an orphan key valid.
- **Status:** the §3.2 rows for both directions, read from one JSON fixture that the frontend tests also read.
- **Round trip:** `fill grid.json` in human mode with no `-o` keeps `clues` in place; `fill -o` keeps them; a
  file with no `clues` gets none; `new` and `import-nyt` write none.
- **Seam (R3):**
  - an argv contract test: the adapter's `clues check` arguments are accepted by the real CLI parser;
  - one real-subprocess end-to-end test from the route through the adapter to the CLI, covering 200, a clue
    rejection (exit 1 → 400 `INVALID_CLUES`) and a grid the CLI cannot load (400 `INVALID_GRID`);
  - a real fill, pause and resume end-to-end test for each state type (CSP, beam, and the CLI's state for
    other algorithms) in which the resumed file keeps `clues`, through `resume` and through `fill --resume`.
- **Route shapes:** non-JSON output → 500 `INTERNAL_ERROR`; timeout → 504 `TIMEOUT` (adapter mocked).

### 6.2 Frontend (vitest)

**[SPEC]**
- **Pure functions:** the browser status rule against the shared fixture; the document signature matches the
  §4.1 example, changes on a clue edit and on a grid edit, and is identical for another insertion order; the
  grid signature is unaffected by clues; the status signature ignores clue text; a history snapshot holds clues
  and restore writes them; the replacement predicate is true for a white grid with one clue and false with
  none; `isAdoptableEntry` accepts absent `clues` and rejects a non-object.
- **Commit:** unchanged text is a no-op and a stale clue stays stale; a whitespace-only draft on an entry with no
  clue is a no-op; an empty draft removes; 201 code points is refused with `At most 200 characters.` and the
  draft kept.
- **Undo:** one changed commit is exactly one step; typing five characters then leaving is one step; a commit
  and a grid edit in one tick are two steps; undo restores the text and redo reapplies it; undo back to the saved
  content leaves the document clean; a clue-only undo leaves an open Clean confirm open; a commit during an open
  Apply All batch belongs to its step; clicking Undo with a draft open commits then undoes it.
- **Save:** a commit makes the document dirty and a save makes it clean; Open restores clues; after `forget()`,
  a clue commit re-arms autosave; a clue commit closes the restored banner.
- **Lifecycle:** New grid and a size change start with no clues; a save fork keeps clues and history.
- **Confirm:** New grid, Open saved and Import each ask on a white grid with a clue.
- **Gating:** during a run the controls are disabled, and a handler called anyway writes nothing.
- **Import:** confirm before the check; a `clues` key (including `{}`) calls the route and no key does not; a
  400 shows `error.message` and applies nothing; a failed request refuses with
  `Could not check the clues: <error>.`; a valid import applies the clues.
- **Panel:** the header sub-line and empty-group texts; `–` before numbering; rows in reading order; a stale row
  shows `Written for` and `Keep`, and Keep clears it; orphans in key order, and Delete is one step; a clue moves
  between its row and the Orphaned section as its entry goes and returns; Enter moves on, passes from Across to
  Down, and stays on the last row; Escape restores; a tool switch commits a draft; a number click selects the
  entry; a grid selection highlights its row.
- **Reconciliation:** no request during a run; one request 300 ms after the last status change, none for a
  text-only change; a reply for an older status signature is not applied; a key missing from a reply shows the
  browser's status; a failure shows the browser's statuses.
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
| `fill`'s result write drops `clues` | `fill grid.json` keeps `clues` in place |
| The CLI status uses `get_word_slots()` at its default | the 2-letter `RO` row is `ok` |
| The reconcile applies a reply without comparing signatures | a reply for an older status signature is not applied |

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
| CLU-9 | Clue a 2-letter entry and wait for the panel to reconcile | The clue shows no stale or orphaned mark |

---

## 7. Amendments to other documents

**[SPEC]** Applied when this feature is built, not before: the novice spec belongs to the release in progress.

**Novice spec:**
- §2.3 D1, the writer list: after "Undo and Redo §3.9" add ", and the Clues panel's commit, Keep and Delete
  (clue-authoring spec §4.4)".
- §3.1: remove "the Clues tool in the tool rail (#53),". Add: "The `Include clues (if available)` checkbox
  stays hidden until clue export (clue-authoring spec §0, sub-project 2)."
- §3.2: in "If the current grid has any letter or black square, an in-panel confirm", replace "any letter or
  black square" with "any letter, black square or clue". In the Import bullet, "Importing over a grid that has
  any letter or black square asks", the same replacement.
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
- §3.9, History ends with the document: replace "an empty grid loses only its redo stack" with "a document with
  no content (§3.2) loses only its redo stack".
- §6, AF-GATE: add "the Clues panel's inputs, Keep and Delete" to the list of writers.

**Code comments:** the `ToolRail.jsx` header ("Not rendered … the Clues tool (#53)") keeps the Heatmap only; the
`useSaveMachine.js` comments that say "grid edit" for the `contentSig` re-arm say "edit, to the grid or to a
clue"; the `gridHasContent` docstring's purpose ("replacing the grid would lose work") moves to the new
predicate; the `cli.py` comment ending "metadata is therefore intentionally unused on load" says that
`metadata["clues"]` is read on load.

**Tests:** `App.test.jsx` ("renders no Clues tool and no Heatmap toggle") and `ToolRail.test.jsx` ("does not
render the Clues tool or the Heatmap toggle") are split (§6.2). `ExportPanel.test.jsx`'s `Include clues`
assertion is unchanged.

**CLI and API documentation:**
- `docs/specs/CLI_SPEC.md`: the Command Reference gains `clues check`; Grid File Format gains `clues`;
  Pause/Resume Workflow says the state carries `clues` and resume writes them.
- `docs/api/openapi.yaml` and `docs/api/API_REFERENCE.md` gain `POST /api/clues/check`.
- `cli/README.md`: the `clues check` command.

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

---

## 8. Tech debt recorded

**[SPEC]** The browser parses and validates the grid part of an imported grid file (`ImportPanel.jsx`) and
serializes the exported file (`ExportPanel.jsx`). No rule permits this, `Grid.from_dict` already validates the
same format, and there is no import or export route. It is retained by Decision 7. One tech-debt issue
records it when this feature is built.

**[SPEC]** `Grid.get_word_slots`' docstring gives its `pattern` as `'C?T'`, but the body joins raw `get_cell`
values, so an empty square is `.` (`cli/src/core/grid.py`). The pattern builder used for matching is a separate
path and does emit `?`. §3.2 relies on the `.` form. The clue-status task corrects the docstring and pins the `.`
form in a test, because it is the first code to read that `pattern`.

---

## 9. Open points (default applies if unruled by 2026-11-14)

| Id | Section | Question | Default |
|---|---|---|---|
| CA-1 | §3.1 | Maximum clue length | 200 characters |
| CA-2 | §3.5 | Carry `clues` through the pause state so resume keeps them | Yes, as `metadata["clues"]` |
| CA-3 | §5.6 | Reconcile delay after the last status change | 300 ms |
| CA-4 | §8 | When the tech-debt issue is filed | When this feature is built |
| CA-5 | §0 | A feature issue for clue authoring (#53 was closed by hiding the tool) | None is filed; this spec is the record until the feature is scheduled |

---

## 10. Amendment record

- 0.1.0 (2026-10-31): first written version, from the sections approved in chat on 2026-10-31.
- 0.1.1 (2026-10-31): first review, three reviewers on 0.1.0 (A facts, B design, C rules and integration).
  Blocking: the status oracle hid 2-letter entries (A F1, C B1; §2, §3.2); a reconcile reply could apply to a
  newer document (B B4; §5.6 rewritten around a status signature, gated during a run, C S4). Should-fix: key
  order and validation order (B B1, B2); key grammar, whitespace and code-point length (B2, B3); adapter and
  route errors (A F2, C S2, B B7); pause-state carrier and every grid writer (A F4, C S1, B B8); in-place write
  in human mode only (A F3); drafts (B B5); import order and plumbing (B B6, C M1); stored `clues` shape (C S3);
  rows and selection (B B10, B B11); same-tick undo (C M2); amendments to CLI_SPEC, API_REFERENCE, novice §3.2
  and §3.9 (C S5); decisions numbered (C M3); CA-5 given an outcome (C M4); smaller points (B B12, A F5).
  Rejected: C M5 (this repo's specs keep "What it beat" in `[SPEC]`; #53's closing comment was read, and "the
  solver never reads it" is a requirement); B B12's ß case (cells hold only A–Z).
- 0.1.2 (2026-10-31): owner approval. §8 records the `get_word_slots` docstring/body mismatch on the
  empty-square encoding, found while verifying the handoff's constraints.
- 0.1.3 (2026-10-31, found while writing the plan): §3.5 said `resume` and `fill --resume` both go through
  `_execute_resume`. `fill --resume` resolves the state in `fill` itself (`cli.py`, the `resume_state_file`
  branch of `fill`). §3.5 now names both paths and says, for `fill --resume` given a grid file as well, that
  `clues` come from the state, following `fill`'s existing "--resume wins" rule for the grid. What it beat:
  reading the grid file's `clues` (they could describe a different grid from the one being resumed).
