# User Guide Claims Ledger

One row per factual claim in `docs/user-guide/`. A claim with no proving line is cut or marked `[?]` in the
page, never kept on trust. Counts of rows by status are produced by the command at the end of this file, not
typed.

- **Proof** gives the identifier first and `path:line` beside it (an identifier survives edits above it; a
  line number does not).
- **Status**: `verified` (a code line proves it and, where the claim is about behaviour, it was also run),
  `unverified` (no proving line, or not runnable in this Linux sandbox), `false` (contradicted by code or
  by a run).
- **Evidence** names a run captured in this session. Where a command was safe to run, its real output is in
  the page.
- Sandbox: Linux, Python 3.13, Node 22. macOS-specific statements cannot be run here.

| ID | Page | Claim | Proof | Status | Evidence |
|---|---|---|---|---|---|
| I-01 | install-on-macos | Windows is not supported; macOS and Linux are | README.md:18 (policy statement; no Windows branch in `setup.sh`) | verified | read |
| I-02 | install-on-macos | Python 3.9 or later is required | `PYTHON_MISSING` setup.sh:10; version test setup.sh:24 | verified | setup run printed `[ok] Python 3.13` |
| I-03 | install-on-macos | Node.js 18 or later is required | `NODE_MISSING` setup.sh:11; test setup.sh:37 | verified | setup run; `Missing: node` run with node hidden |
| I-04 | install-on-macos | npm comes with Node.js | `NPM_MISSING` setup.sh:12 ("installed with Node.js 18 or later") | verified | setup run |
| I-05 | install-on-macos | The macOS system `python3` is a stub that opens an Xcode command-line-tools dialog | README.md:20-22 | unverified | not macOS; page marks it `[?]` |
| I-06 | install-on-macos | Clone URL is `https://github.com/apassuello/crossword-helper.git` | README.md:27; `git remote get-url origin` | verified | git remote |
| I-07a | install-on-macos | `setup.sh` is committed executable, so a clone needs no `chmod` | `git ls-files -s setup.sh` shows mode 100755 | verified | git index |
| I-07b | install-on-macos | A ZIP download needs `chmod +x setup.sh` | README.md:26-28 | unverified | ZIP not downloaded; wording is the README's |
| I-08 | install-on-macos | `setup.sh` creates `venv/`, installs `requirements.txt`, runs `npm ci`, builds into `frontend/dist/` | `python3 -m venv` setup.sh:71; `pip install -r` setup.sh:83; `npm ci` setup.sh:93; build setup.sh:103-104 | verified | setup run, rc=0 |
| I-09 | install-on-macos | Packages go into `venv/` and `node_modules/` in the project folder | `VENV_DIR` setup.sh:62; `npm ci` in `$SCRIPT_DIR` setup.sh:88-93; both dirs gitignored | verified | `ls`, git status clean after setup |
| I-10 | install-on-macos | The success output ends as shown | `[ok]` echo lines through setup.sh:104; `=== Setup complete ===` setup.sh:108 | verified | `setup-run.txt` (excerpt in page, Linux) |
| I-11 | install-on-macos | A missing tool prints `Missing: ... install from <url>`, and the script stops before creating anything | checks setup.sh:15-48 precede venv creation setup.sh:66-77 | verified | run with node hidden: rc=1, no `venv/` or `node_modules/` |
| I-12 | install-on-macos | `run.py` serves on http://localhost:5000 by default and prints `Running on` | `port = int(os.environ.get("PORT") or "5000")` run.py:56; `app.run(host="localhost"...)` run.py:61 | verified | `run.log` |
| I-13 | install-on-macos | A busy port prints `Port 5000 is in use. Start with PORT=<other> python3 run.py` | run.py:37, run.py:48 | verified | second `run.py` while 5000 busy: rc=1, message printed |
| I-14 | install-on-macos | `PORT=5001 python3 run.py` serves on 5001 | run.py:56 | verified | `run5001.log`, `/api/health` answered on 5001 |
| I-15 | install-on-macos | On macOS, AirPlay Receiver can hold port 5000 | run.py:26-27 (code comment) | unverified | not macOS; page marks it `[?]` |
| I-16 | install-on-macos | Ctrl+C stops the app | server banner `Press CTRL+C to quit` | verified | `run.log` |
| I-17 | install-on-macos | The top-bar status reads "online" when the backend is healthy | `verdictFor` useHealth.js:21-23; label logic TopBar.jsx `label` | verified | code; browser check recorded under T-* |
| I-18 | install-on-macos | `curl http://localhost:5000/api/health` returns the JSON shown | health route routes.py:40 | verified | curl output pasted |
| I-19 | install-on-macos | `python -m cli.src.cli --version` prints `crossword, version 2.0.0` | `@click.version_option(version="2.0.0"` cli.py:35 | cut (D8: GUI only; was verified) | run |
| I-20 | install-on-macos | Re-running `setup.sh` is supported: reports `Virtual environment already exists` and reinstalls | setup.sh:75-76, 84, 93 | verified | `setup-run2.txt`, rc=0 |
| G-01 | set-up-the-grid | New grid sizes are 11×11, 15×15, 21×21 | `NEW_GRID_SIZES` GridPanel.jsx:14 | verified | browser run: `11×11` button present |
| G-02 | set-up-the-grid | A non-empty grid triggers `Replace the current grid? Unsaved changes are lost.` with `Replace` / `Cancel` | `REPLACE_MESSAGE` GridPanel.jsx:12; `gridHasContent` branch GridPanel.jsx:78-80 | verified (code) | not shown in browser run |
| G-03 | set-up-the-grid | The app opens with an empty 15×15 grid | observed: Total 225, Black 0 on first load | verified | the first-look script run, first.png |
| G-04 | set-up-the-grid | `Space` or `.` toggles black; the same key again turns it white | key dispatch CrosswordGrid.jsx:123-127 (`toggleBlack`) | verified (code); Space run in browser | tut2.js: ten Space presses gave Black 20 |
| G-05 | set-up-the-grid | The `Black square` button is disabled with no selection or when the cell cannot be toggled | `disabled = !allowed \|\| editingPaused` GridPanel.jsx:`disabled`; `canToggleBlack` gridEdits | verified (code) | first.png shows it greyed |
| G-06 | set-up-the-grid | A theme-locked square cannot be made black | `if (!cell.isThemeLocked) actions.push({type:'toggleBlack'` CrosswordGrid.jsx:125 | verified (code) | not run |
| G-07 | set-up-the-grid | `Symmetry` is on by default and mirrors black squares 180° | ToolRail `viewToggles.symmetry`; observed class `on`; 10 clicks gave Black 20 | verified | tut2.js |
| G-08 | set-up-the-grid | Clicking `Symmetry` turns mirroring off | `onToggleView('symmetry')` ToolRail.jsx | unverified | toggle not clicked in a run |
| G-09 | set-up-the-grid | The GRID block shows Total, Black (count·percent), Filled, Words | `xw-rail-stat` rows ToolRail.jsx | verified | browser stats text |
| G-10 | set-up-the-grid | VIOLATIONS lists advisory messages and does not block editing | ToolRail.jsx comment "advisory, live"; observed text "High black square count (20)…" | verified | tut2.js |
| G-11 | set-up-the-grid | Clue numbers appear at word starts and update | cell number rendering CrosswordGrid.jsx (`cell.number`); screenshots | verified | s2-autofill-end.png |
| G-12 | set-up-the-grid | Key hint text and key roles (Enter, Tab, Backspace) | hint line observed; CrosswordGrid.jsx:123-160 | verified | first.png |
| G-13 | set-up-the-grid | Undo/Redo keys: Cmd+Z, Cmd+Shift+Z; Ctrl+Z / Ctrl+Y on others | App.jsx undo listener (`k === 'z'`, `'y' && e.ctrlKey`); README.md:63 | verified (code) | not run. NOTE: the page says `Ctrl+Shift+Z` on Linux; code accepts Ctrl+Shift+Z (ctrlKey and shiftKey → redo) |
| G-14 | set-up-the-grid | `validate` exits 0 when valid, 1 when invalid | `sys.exit(0 if is_valid else 1)` cli.py:510 | cut (D8: GUI only; was verified) | `validate` runs: example_15x15 passes, example_11x11 fails |
| G-15 | set-up-the-grid | `validate` checks symmetry, connectivity and minimum word length 3 | validator error strings seen: "lacks 180° rotational symmetry", "isolated white square regions", "only 1 letter (minimum is 3)" | cut (D8: GUI only; was verified) | `validate` runs on example grids |
| G-16 | set-up-the-grid | Rows/cols in validate messages count from 0 | message `Down word at (6, 3)`; `number` prints `row 0, col 0` for clue 1 | cut (D8: GUI only; was verified) | `number` run |
| G-17 | set-up-the-grid | `show` default format is `grid`, which shows clue numbers instead of letters at word starts; `-f text` shows letters; `-f json` prints file contents | `default="grid"` cli.py:1571 area; show body cli.py | cut (D8: GUI only; was verified) | `show` runs |
| G-18 | set-up-the-grid | Some shipped example grids under `data/grids/` fail `validate` | `validate` on example_11x11.json, example_21x21.json, example_15x15_partial_birthday.json: INVALID | cut (D8: GUI only; was verified) | runs (also a README discrepancy, see D4 list) |
| G-19 | set-up-the-grid | `validate` ends `✓ VALID - Grid meets all standards!` on success | validate echo cli.py | cut (D8: GUI only; was verified) | run on example_15x15.json |
| S-01 | save-open-and-recover | `Save grid` opens a prompt `Name this grid` with `Save` and `Cancel`; the name is pre-filled with a suggestion like `11×11 <date> <time>` | SaveNamePrompt.jsx (`Name this grid` label, `Save`, `Cancel`); observed value `11×11 2026-10-29 13:53` | verified | tut2.js |
| S-02 | save-open-and-recover | `Escape` closes the prompt without saving | `onKeyDown ... 'Escape'` SaveNamePrompt.jsx | verified (code) | not pressed in a run |
| S-03 | save-open-and-recover | A name collision asks `Replace the saved grid named "<name>"?` with `Replace` | SaveNamePrompt.jsx collision branch | verified (code) | not run |
| S-04 | save-open-and-recover | The label reads `saved locally · just now`, later `saved locally · Nm ago` | `savedLabel` derivation useSaveMachine.js:55-58; observed `saved locally · just now` | verified | tut2.js |
| S-05 | save-open-and-recover | Autosave happens shortly after edits; delay is `AUTOSAVE_MS` | `const AUTOSAVE_MS` useSaveMachine.js:50; README.md:61 ("saves itself as you work") | verified (code) | not timed in a run |
| S-06 | save-open-and-recover | Saves live in browser localStorage, not the project folder | `SAVE_KEY` + `localStorage.setItem` storage.js:230 | verified | storage.js read |
| S-07 | save-open-and-recover | Saves do not move between browsers/computers; clearing site data removes them | consequence of localStorage (browser behaviour) | unverified | general browser localStorage behaviour, not tested; page marks `[?]` |
| S-08 | save-open-and-recover | `Open saved` lists size, time, `Open`, `Delete` | SavedGridsList.jsx | verified (code) | list not opened in a run |
| S-09 | save-open-and-recover | Opening over a non-empty grid asks the replace confirm | GridPanel.jsx `onOpen` branch (`gridHasContent`) | verified (code) | not run |
| S-10 | save-open-and-recover | `Delete` asks `Delete "<name>"?` | GridPanel.jsx `pending.kind === 'delete'` message | verified (code) | not run |
| S-11 | save-open-and-recover | On reload the newest save is restored with banner `Restored "<name>" (saved <time>)`, `Start blank`, `×` | RestoreBanner.jsx; README.md:179-182 (only newest save restored) | verified (code) | reload not run |
| S-12 | save-open-and-recover | Undo/redo keys and top-bar buttons | TopBar.jsx Undo/Redo; App.jsx undo listener | verified (code) | not run |
| S-13 | save-open-and-recover | One letter is one undo step; placed word, Apply All, clean, finished autofill each one step; undo stops at new grid/import/open | README.md:60-64 | unverified | README wording only; spec 0.2.18 §3.9 not re-derived |
| S-14 | save-open-and-recover | Full storage shows `Could not save: browser storage is full. Delete a saved grid or export this one.` | `QUOTA_MESSAGE` useSaveMachine.js:61-62 | verified (code) | not triggered |
| F-01 | find-words-by-pattern | Search field placeholder is `Enter pattern (e.g., ?I?A)`; a pattern under 3 characters shows `Pattern must be at least 3 characters` | PatternMatcher.jsx:`placeholder`; `setError('Pattern must be at least 3 characters')` PatternMatcher.jsx:52 | verified (code); placeholder seen in browser | s1 browser pass |
| F-02 | find-words-by-pattern | Lowercase is accepted (uppercased) | `pattern: pattern.toUpperCase()` PatternMatcher.jsx | verified (code) | CLI `c.t` run also uppercases |
| F-03 | find-words-by-pattern | `comprehensive` is ticked by default; with none ticked `Select at least one word list` shows and `Search` is disabled | `useState(['comprehensive'])` PatternMatcher.jsx:16; `disabled={loading \|\| noWordlist}` PatternMatcher.jsx:183 | verified (code) | not run with none ticked |
| F-04 | find-words-by-pattern | Results show as `Results (N)` with score, source, length; `C?T` gave CAT CIT COT CRT CST CDT CUT | observed `Results (7)` | verified | tut2.js |
| F-05 | find-words-by-pattern | A UI search returns at most 50 words | `maxResults: 50` PatternMatcher.jsx (startPatternSearch call) | verified (code) | not run |
| F-06 | find-words-by-pattern | `Sort by` options Score/Alphabetical/Length; `Min Score` filter | PatternMatcher.jsx option elements | verified (code) | not run |
| F-07 | find-words-by-pattern | `No matching words found` when nothing fits | `setError('No matching words found')` PatternMatcher.jsx:119 | verified (code) | not run |
| F-08 | find-words-by-pattern | The shipped list has obscure entries/abbreviations (CRT, CST appear at score 31) | observed search + CLI output | verified | runs |
| F-09 | find-words-by-pattern | Clicking a result writes it from the selected square in the selected direction, stopping at black/edge and skipping theme-locked cells | `handlePatternSelect` App.jsx:518; `writePatternWord` gridEdits.js:93-107 | verified (code) | not clicked in a run |
| F-10 | find-words-by-pattern | Enter switches across/down | CrosswordGrid.jsx:130 (`rotateDir`) | verified (code) | |
| F-11 | find-words-by-pattern | Algorithm options `Regex (Classic)` (default) and `Trie (Fast)` | PatternMatcher.jsx:228-229; `useState('regex')` | verified (code) | not run in UI |
| F-12 | find-words-by-pattern | Both algorithms take the same patterns | ARCHITECTURE.md §5 (both accept `?`); `-a trie` CLI run for `c.t` returned the same words as regex | verified | CLI runs (regex and trie) |
| F-13 | find-words-by-pattern | CLI without `-w` searches a tiny built-in list (`source=builtin`) | cli.py `builtin` source label; run output `CAT ... source=builtin` | cut (D8: GUI only; was verified) | run |
| F-14 | find-words-by-pattern | CLI `--max-results` default 20; `-a` default `regex` | `default=20`, `default="regex"` (pattern options, defaults command output) | cut (D8: GUI only; was verified) | defaults command run |
| F-15 | find-words-by-pattern | Patterns: letters A-Z and `?`/`.`, length 3-21, else exit 1 with message | `pattern_error` logic cli.py (pattern fn) | cut (D8: GUI only; was verified) | `C?` run: rc=1 |
| F-16 | find-words-by-pattern | `--json-output` puts results on stdout and progress on stderr | split run: stdout started with `{ "results"`; stderr had progress lines | cut (D8: GUI only; was verified) | run |
| F-17 | find-words-by-pattern | `-w` can be repeated | `multiple=True` cli.py pattern option | cut (D8: GUI only; was verified (code)) | one list used in runs |
| T-01 | first-crossword | Top bar status label reads `online` when the backend is up | TopBar.jsx `label` logic; observed | verified | browser run |
| T-02 | first-crossword | Top bar has `Undo`, `Redo`, `Verify words`, `Clean grid`, `Save grid` | TopBar.jsx button labels | verified | first.png |
| T-03 | first-crossword | Tool rail lists Grid, Search, Autofill, Theme, Lists, Import, Export | `TOOLS` ToolRail.jsx | verified | first.png |
| T-04 | first-crossword | App starts with an empty 15×15 grid | observed Total 225 | verified | look.js |
| T-05 | first-crossword | `11×11` under `New grid` gives an empty 11×11 grid, Total 121, Black 0 | GridPanel.jsx `NEW_GRID_SIZES`; observed | verified | tut2.js |
| T-06 | first-crossword | GRID block shows Total, Black, Filled, Words | ToolRail.jsx `xw-rail-stat` | verified | browser |
| T-07 | first-crossword | `Symmetry` is on by default and highlighted | observed class `on` | verified | tut.js |
| T-08 | first-crossword | With Symmetry on a black square also blackens the 180° opposite square | observed Black 20 after 10 clicks | verified | tut2.js |
| T-09 | first-crossword | Square (1,5) mirrors to (11,7) | 180° symmetry arithmetic `N-1-r`; pattern validated by CLI | verified | t1-blacks.png |
| T-10 | first-crossword | Click a square then Space makes it black | CrosswordGrid.jsx key dispatch (`k === ' '`) | verified | tut2.js |
| T-11 | first-crossword | The ten listed squares give `Black 20 · 16.5%` and `Words 42` | observed | verified | tut.js, tut2.js |
| T-12 | first-crossword | Hint line text under the grid | GridHintLine.jsx | verified | first.png |
| T-13 | first-crossword | VIOLATIONS shows the advisory lines quoted | ToolRail.jsx `violations`; observed | verified | tut2.js |
| T-14 | first-crossword | `Undo` steps back one edit; Cmd+Z / Ctrl+Z | App.jsx undo listener | verified (code) | not run |
| T-15 | first-crossword | Clicking the top-left square and typing J A Z Z fills four squares; `Filled` reads 4.0% | observed | verified | tut.js |
| T-16 | first-crossword | `Verify words` with only JAZZ typed gives `All 5 words valid!` | App.jsx toast `All ${total_checked} words valid!`; observed | verified | tut.js |
| T-17 | first-crossword | If nothing is flagged the message is `All N words valid!` | App.jsx toast | verified | same |
| T-18 | first-crossword | Search placeholder and `Search` button | PatternMatcher.jsx | verified | tut2.js |
| T-19 | first-crossword | `?` stands for one unknown letter | README.md:52; CLI `pattern` docstring | verified | CLI runs |
| T-20 | first-crossword | `C?T` gives `Results (7)` as listed | observed | verified | tut2.js |
| T-21 | first-crossword | The list is large and not every entry is an everyday word (CRT, CST) | observed | verified | runs |
| T-22 | first-crossword | Searching does not change the grid | observed grid unchanged after search; click-to-insert is a separate action (F-09) | verified | tut2.js |
| T-23 | first-crossword | Autofill heading shows a count of empty slots (41 with only JAZZ typed) | AutofillPanel.jsx `countEmptySlots`; observed | verified | tut2.js |
| T-24 | first-crossword | `Algorithm` defaults to `Repair (Recommended)` | `DEFAULT_OPTIONS` AutofillPanel.jsx | verified | browser |
| T-25 | first-crossword | `Timeout` options 1/2/5/10/30 min; default 5 min | AutofillPanel.jsx options; `timeout: 300` | verified | browser |
| T-26 | first-crossword | `Min Score: 30`; Adaptive/Partial/Cleanup unticked; `Comprehensive Dictionary` ticked | `DEFAULT_OPTIONS` (`minScore: 30`, `wordlists: ['comprehensive']`) | verified | s2-autofill-end.png |
| T-27 | first-crossword | `Start Autofill` starts the run | AutofillPanel.jsx | verified | tut2.js |
| T-28 | first-crossword | During a run: `Editing is paused while autofill runs.`, progress bar, `Cancel`, messages like `Repairing 6 invalid words` | CrosswordGrid.jsx status text; observed in t3-autofill.png | verified | tut.js screenshot |
| T-29 | first-crossword | Run ends with `Filled 42/42 slots — 7 entries may be invalid (use Verify Words to check)`, `Keep fill`, `Reset` | useAutofillMachine.js message; observed | verified | tut2.js |
| T-30 | first-crossword | Grid stays as before the run until `Keep fill` is clicked | useAutofillMachine.js header (restores Start snapshot); observed Filled 4.0% at run end | verified | tut2.js |
| T-31 | first-crossword | After `Keep fill`, `Filled` reads 100.0% (that run) and JAZZ stays | observed | verified | tut2.js |
| T-32 | first-crossword | Results differ from run to run | two runs flagged different words | verified | tut2.js (two runs) |
| T-33 | first-crossword | Autofill can return invalid words | observed; README Known Limitations | verified | tut2.js |
| T-34 | first-crossword | README `Known Limitations` holds open autofill issues | README.md "Known Limitations" Autofill bullet | verified | read |
| T-35 | first-crossword | After autofill, `Verify words` gives `7 of 42 words flagged — 7 invalid: …` | App.jsx toast; observed | verified | tut2.js |
| T-36 | first-crossword | Flagged words show red letters and a short red underline | CrosswordGrid.jsx `cell.isError` fill `var(--danger)` (letter colour); underline: agent cites CrosswordGrid.jsx:448-456 | verified (code) for red; underline unverified | not viewed in a screenshot |
| T-37 | first-crossword | `Clean grid` belongs to the check-and-clean how-to | TopBar.jsx title | verified | n/a |
| T-38 | first-crossword | `Save grid` opens `Name this grid`, suggested name like `11×11 2026-10-29 13:53`, `Save`, `Cancel` | SaveNamePrompt.jsx; observed | verified | tut2.js |
| T-39 | first-crossword | After `Save`, label reads `saved locally · just now` | useSaveMachine.js | verified | tut2.js |
| T-40 | first-crossword | Saved grids live in the browser, not the project folder | storage.js `localStorage` | verified | read |
| T-41 | first-crossword | `Open saved` lists the saved grid with `Open` and `Delete` | GridPanel.jsx, SavedGridsList.jsx | verified (code) | not opened in a run |
| T-42 | first-crossword | Export tool: `Export Format` with the three options, `Preview`, `Export` | ExportPanel.jsx | verified | tut2.js |
| T-43 | first-crossword | `Export` with HTML downloads `crossword.html` | `downloadFile('crossword.html'...)` ExportPanel.jsx:31 | verified | tut2.js (`suggestedFilename`) |
| T-44 | first-crossword | The exported file is headed `Crossword Puzzle` with a table of numbers, black squares, letters, no clues | exported file read (agent) | verified | scratchpad/pw/crossword.html |
| T-45 | first-crossword | The downloaded file is in the browser's download location | browser behaviour | unverified | not covered |
| T-46 | first-crossword | How `crossword.html` looks opened/printed | not run; page marks `[?]` | unverified | |
| T-47 | first-crossword | A confirmation may appear when `11×11` replaces a non-empty grid | GridPanel.jsx `REPLACE_MESSAGE`; page marks `[?]` | unverified (also see G-02: code-supported) | not run |
| T-48 | first-crossword | A run with a different ending leaves the grid unchanged; steps 10-11 still work | useAutofillMachine.js header; page marks `[?]` | unverified | not run |
| L-01 | use-your-own-word-lists | Line formats `WORD`, `WORD;50`, `word,50`; blank and `#` lines ignored | `WordList.parse_line` word_list.py:259-291; `_load_wordlist_words` cli.py; parse-wordlist docstring | verified | `parse-wordlist mine.txt` run |
| L-02 | use-your-own-word-lists | Only A-Z kept; accents folded (`CAFÉ`→`CAFE`); `ab-cd`, `HELLO WORLD` skipped `not letters only` | `canonical_word` word_list.py:169; `_is_valid_word` word_list.py:181 | verified | run output |
| L-03 | use-your-own-word-lists | `word,score` header skipped as `malformed score` | `parse_line` returns None on non-numeric score; run output | verified | run |
| L-04 | use-your-own-word-lists | Duplicates: first occurrence kept | parse-wordlist docstring cli.py; `zebra` after `ZEBRA;80` not listed in accepted words | verified | run (JSON listed ZEBRA 80 once) |
| L-05 | use-your-own-word-lists | A word with no score gets a calculated score | parse_line docstring ("WordList computes one"); JSON shows `score: null` for CAFE | verified (null in report); calculation in WordList | run |
| L-06 | use-your-own-word-lists | The app's upload uses the same check as `parse-wordlist` | `_parse_content` wordlist_routes.py:373-381 -> `parse_wordlist` cli_adapter.py:203 | verified | read |
| L-07 | use-your-own-word-lists | `parse-wordlist` output `3 words, 3 skipped` + the three skip lines | run output | cut (D8: GUI only; was verified) | run |
| L-08 | use-your-own-word-lists | `--json-output` lists words with score (`null`) and skipped lines with reason | run output | cut (D8: GUI only; was verified) | run |
| L-09 | use-your-own-word-lists | Lists tool: `Upload Wordlist`, `Wordlist Name:`, `Select File:`, `Upload`, `Preview`, `Confirm`, `Cancel` | WordListPanel.jsx:225,247,257,323; preview block | verified (code) | Lists tool not clicked in a run |
| L-10 | use-your-own-word-lists | `Upload` is a dry run; nothing stored until `Confirm`; preview shows valid count, skipped count/reasons, first 20 words | `handleUpload` dryRun: true, `handleConfirm` dryRun: false WordListPanel.jsx:160-205; preview block | verified (code) | not run |
| L-11 | use-your-own-word-lists | No valid words: upload refused with reason | `"No valid words found"` wordlist_routes.py (import_wordlist) | verified (code) | not run |
| L-12 | use-your-own-word-lists | Stored under `data/wordlists/custom/` in the project folder | `category: 'custom'` WordListPanel.jsx `buildImport`; `WordListManager(wordlist_dir="data/wordlists")` wordlist_manager.py:28 (relative path) | verified (code) | not run. Depends on starting the app from the project folder |
| L-13 | use-your-own-word-lists | Ticked custom list offers `Priority theme list`; selecting it makes the fill prefer that list | AutofillPanel.jsx radio; `--theme-wordlist` help "algorithm will prefer words from this list" cli.py | verified (code); effect not measured | not run |
| L-14 | use-your-own-word-lists | `Add Words` box `Enter words (one per line)`; `Show Stats`; delete asks `Delete wordlist "<name>"? This cannot be undone.` | WordListPanel.jsx:101,415-421,451 | verified (code) | not run |
| L-15 | use-your-own-word-lists | Shipped lists are read-only; overwrite/delete refused | `EDITABLE_CATEGORIES = {"custom","imports"}` wordlist_routes.py:25; `_builtin_refusal` | verified (code) | not run |
| L-16 | use-your-own-word-lists | `build-cache` writes `<name>.pkl`; loaders use it while newer than the text list; prints measured load time | `from_file` word_list.py:~326-346 (`cache_mtime > source_mtime`); run output | cut (D8: GUI only; was verified) | `build-cache` run printed times, wrote cachetest.pkl |
| L-17 | use-your-own-word-lists | The app uses the cache automatically (not only the CLI) | `WordList.from_file(use_cache=True)` default; whether the backend path calls `from_file` not traced | cut (D8: GUI only; was unverified) | page says "the app and the CLI use the cache"; narrowed below |
| H-01 | add-theme-words | Theme file: one word per line; words uppercased; duplicates dropped | `upload_theme_words` theme_routes.py:20-83 (`strip().upper()`, `seen`) | verified (code) | not uploaded in a run |
| H-02 | add-theme-words | A line with a space/hyphen/digit is dropped silently | `word.isalpha()` filter theme_routes.py (`if word not in seen and word.isalpha()`) | verified (code) | not run |
| H-03 | add-theme-words | Too short (<3) or longer than the grid width is an error; too many words refused (`MAX_THEME_WORDS`) | `validate_theme_words` theme_placer.py:457-485 | verified (code) | not run |
| H-04 | add-theme-words | File must be under 1 MB (`File too large (max 1MB)`) | ThemeWordsPanel.jsx:`handleFileSelect` size check | verified (code) | not run |
| H-05 | add-theme-words | Theme tool: `Upload Theme Words`, `Choose File`, `Loaded Words`, `Placement Suggestions`, `Apply All Best Placements` | ThemeWordsPanel.jsx:388,400,422,447,454 | verified (code) | Theme tool not opened in a run |
| H-06 | add-theme-words | Invalid list shows toast `Invalid theme words: <first error>`; valid shows `Loaded N theme words` and auto-analyzes | ThemeWordsPanel.jsx `handleFileContent` | verified (code) | not run |
| H-07 | add-theme-words | Hovering a suggestion previews it; `Apply` places and locks that word | panel help text "Hover over suggestions to preview on grid. Click "Apply" to lock the word." | false | Hover does not change the grid; see V-02. |
| H-08 | add-theme-words | `Apply All Best Placements` applies each best suggestion; skips no-placement or conflicting words; lists skipped with reason | `handleApplyAllPlacements` ThemeWordsPanel.jsx:285-330 | verified (code) | not run |
| H-09 | add-theme-words | Panel positions are 1-based | `Row {suggestion.row + 1}, Col {suggestion.col + 1}` ThemeWordsPanel.jsx:485 | verified (code) | not run |
| H-10 | add-theme-words | Locked cells: corner marker; cannot type over, Backspace or blacken; Clean keeps; autofill fixed | CrosswordGrid.jsx Backspace/Space/letter guards on `isThemeLocked`; `mergeGridPreserveThemeLocked` useAutofillMachine.js:381; `getThemeEntries` AutofillPanel.jsx | verified (code) | not run |
| H-11 | add-theme-words | Suggestions refresh when the grid changes | ThemeWordsPanel.jsx `SUPERSEDED_MSG` 'Suggestions updated for the changed grid.' | verified (code) | not run |
| H-12 | add-theme-words | CLI theme file keys are `"(row,col,direction)"`, 0-based | cli.py `--theme-entries` help; run with `(0,0,across)`/`(0,4,across)` | cut (D8: GUI only; was verified) | run: `Z I P # B O W` placed |
| H-13 | add-theme-words | `fill` lists loaded entries (`Across at (0,0): ZIP`) and errors with `Invalid theme entries:` on a misfit | run output | cut (D8: GUI only; was verified) | run |
| H-14 | add-theme-words | `--theme-wordlist` prefers words from a list without locking | `--theme-wordlist` help cli.py | cut (D8: GUI only; was verified (help text only; effect not measured)) | not run |
| H-15 | add-theme-words | Known problems: Apply All counts hand-placed words; JSON export loses locks, `Save grid` keeps them | README.md:169-172 | unverified | README wording; issues #80 not re-read |
| A-01 | autofill-a-grid | Autofill panel option defaults: algorithm `repair`, timeout 300, min score 30, adaptive off, max adaptations 3, partial fill off, cleanup off, list `comprehensive` | `DEFAULT_OPTIONS` AutofillPanel.jsx:49-52 area (own state, not CLI) | verified | browser pass shows defaults |
| A-02 | autofill-a-grid | Algorithm options: Repair (Recommended), Hybrid (Beam + Repair), Beam Search, Classic CSP | AutofillPanel.jsx `<option>` list | verified | screenshot |
| A-03 | autofill-a-grid | Timeout options 1/2/5/10/30 min | AutofillPanel.jsx options | verified | tut2.js text |
| A-04 | autofill-a-grid | Min Score slider 0-100 step 10 | `type="range" min="0" max="100" step="10"` AutofillPanel.jsx | verified (code) | seen in screenshot |
| A-05 | autofill-a-grid | `Max adaptations` slider 1-5 appears with Adaptive mode | AutofillPanel.jsx `options.adaptiveMode &&` block | verified (code) | not toggled |
| A-06 | autofill-a-grid | Partial fill / Cleanup / Adaptive descriptions | `--partial-fill`, `--cleanup`, `--adaptive` help text cli.py | unverified | descriptions come from CLI help text, which this repo's fabrication log shows can be false; behaviour not measured. Page marks `[?]` |
| A-07 | autofill-a-grid | A ticked Custom list offers `Priority theme list` | AutofillPanel.jsx radio | verified (code) | not run (no custom list ticked) |
| A-08 | autofill-a-grid | README warns Beam/Classic can stop with grid unchanged and no red cell; Repair reworks the letter | README.md:166-168 | unverified | README text; not reproduced |
| A-09 | autofill-a-grid | Min Score at the top of the scale on an open grid fills almost nothing | CLI run `--min-score 100`, 11x11 example: `Slots filled: 3/44` | verified | fill run (CLI, not UI) |
| A-10 | autofill-a-grid | `Start Autofill` is disabled with `Select at least one word list` / `Clear some cells to run autofill again` | AutofillPanel.jsx `disabled={noEmptySlots \|\| noWordlists}` + hints | verified (code) | not run |
| A-11 | autofill-a-grid | During a run: `Editing is paused while autofill runs.`, progress bar, `Cancel` | CrosswordGrid.jsx status; AutofillPanel.jsx; observed | verified | t3-autofill.png |
| A-12 | autofill-a-grid | `Successfully filled N/M slots!` fills the grid immediately | useAutofillMachine.js:389 (`d.success` branch merges grid) | verified (code) | not observed (no run ended in success) |
| A-13 | autofill-a-grid | `Filled N/M slots — K entries may be invalid …` with `Keep fill`/`Reset` | useAutofillMachine.js:405; observed | verified | tut2.js |
| A-14 | autofill-a-grid | `Partial: N/M slots (P%)` with `Keep partial fill (N/M slots)` | useAutofillMachine.js:419-424; AutofillPanel.jsx keepButton label | verified (code) | not observed |
| A-15 | autofill-a-grid | `Autofill could not fill around the highlighted letters.` with red squares | useAutofillMachine.js:418-419 | verified (code) | not observed |
| A-16 | autofill-a-grid | Blocked messages `No word fits the highlighted letters.` / `The selected word lists have no words of length N.` | `blockedMessage` useAutofillMachine.js:102-107 | verified (code) | not observed in UI; CLI exit 3 `Blocked: no word fits HELLO??????` observed |
| A-17 | autofill-a-grid | Grid stays as before the run until `Keep` is clicked | useAutofillMachine.js header `finishRun` restores Start snapshot; observed Filled 4.0% at run end | verified | tut2.js |
| A-18 | autofill-a-grid | `Reset` closes the result without taking the fill | `reset` → `transition({state:'idle'...})` useAutofillMachine.js:661; grid already restored | verified (code) | not clicked |
| A-19 | autofill-a-grid | Autofill does not change typed letters or locked theme words | typed `ZIP` survived CLI fill; JAZZ survived UI fill; `--lock-filled` default True | verified | runs |
| A-20 | autofill-a-grid | Results differ from run to run | two UI runs, different flagged words | verified | tut2.js |
| C-01 | check-and-clean-a-grid | Verify and Clean are disabled when the backend is offline | `disabled={offline \|\| editingPaused}` TopBar.jsx (Verify and Clean buttons) | verified (code) | not run offline |
| C-02 | check-and-clean-a-grid | Verify checks slots against the `comprehensive` list only | `VALIDATION_WORDLISTS = ['comprehensive']` App.jsx:55, used App.jsx:539,592 | verified | read |
| C-03 | check-and-clean-a-grid | Full slot not in list = invalid; partial slot no word fits = unfillable; empty skipped | `verify_words` docstring routes.py:759-766; App.jsx toast builds `invalid`/`unfillable` | verified (code) | invalid case observed; unfillable not observed |
| C-04 | check-and-clean-a-grid | Messages `All N words valid!` and `K of N words flagged — …` with `_` for blanks | App.jsx:557, 563-575 | verified | tut2.js shows both |
| C-05 | check-and-clean-a-grid | Letters of flagged words turn red | CrosswordGrid.jsx `cell.isError ? 'var(--danger)'`; `applyVerifyErrors` | verified (code) | not viewed |
| C-06 | check-and-clean-a-grid | A word only in your own list is flagged invalid | follows from C-02 (own list is not in the verify list) | verified (code) | not run |
| C-07 | check-and-clean-a-grid | Clean clears exactly the red cells, except theme-locked; asks `Clean will remove N letters` with `Clean`/`Cancel` | `clean_grid` docstring routes.py:943-955; App.jsx:806-810, `planClean` | verified (code) | not run |
| C-08 | check-and-clean-a-grid | Undo reverses a clean in one step | `acceptClean` calls `recordStep` App.jsx; README.md:60-63 | verified (code) | not run |
| C-09 | check-and-clean-a-grid | No-op messages `Grid is clean — all words are valid!` / `Nothing removed: theme-locked letters are kept.` | App.jsx:618-622 | verified (code) | not run |
| C-10 | check-and-clean-a-grid | A crossing word is left partly filled; autofill puts letters back | `clean_grid` docstring routes.py | verified (code) | not run |
| C-11 | check-and-clean-a-grid | Red marks can stay after a clean until verify is re-run; toast count can exceed squares emptied | README.md:161-165 (#78, #79) | unverified | README wording |
| E-01 | import-and-export-grids | Import JSON needs `size` and `grid`; square; size 3-25; cells `#`, `.`, A-Z | `validateImportedData` ImportPanel.jsx:60-110; `IMPORT_MIN_SIZE/MAX_SIZE` gridSizes.js:7-8 | verified (code) | import not run in UI |
| E-02 | import-and-export-grids | A `cli new` grid file has this shape, extra keys ignored | `new` output keys `size`,`grid`,`black_squares`,`is_symmetric` (run); importer reads only size/grid | verified (code + run of `new`) | UI import of a CLI file not run |
| E-03 | import-and-export-grids | Upload File accepts `.json` only, else `Invalid file type. Please select a .json file.` | ImportPanel.jsx:120 | verified (code) | not run |
| E-04 | import-and-export-grids | Paste JSON: `Paste JSON Data` + `Validate JSON`; Preview; `Import Grid`; `Clear` | ImportPanel.jsx:280-380 | verified (code) | not run |
| E-05 | import-and-export-grids | Error examples `Grid row 2 has 14 cells, expected 15`; `Invalid cell at (0, 1)…` (0-based) | ImportPanel.jsx messages | verified (code) | not run |
| E-06 | import-and-export-grids | Import over a non-empty grid asks `Replace the current grid? Unsaved changes are lost.` | ImportPanel.jsx:8,360 `confirmingReplace` | verified (code) | not run |
| E-07 | import-and-export-grids | An import starts a new document; undo does not cross it | README.md:63-64 ("Undo stops at a new grid, an import or an opened save") | unverified | README wording |
| E-08 | import-and-export-grids | Export formats: JSON→`crossword.json`, HTML→`crossword.html`, Text→`crossword.txt` (`■`) | ExportPanel.jsx:28,31,34,109; observed `crossword.html` | verified | tut2.js (HTML only run) |
| E-09 | import-and-export-grids | JSON export is "complete grid data that can be reimported" | ExportPanel.jsx Format Information text | unverified | the panel's own help text; round trip not run. Page marks `[?]` |
| E-10 | import-and-export-grids | HTML preview not available in the panel | `setPreview('HTML preview not available - use Export to download')` ExportPanel.jsx:138 | verified (code) | not run |
| E-11 | import-and-export-grids | Exports have no clues | exported HTML read (agent): no clues | verified | crossword.html read |
| E-12 | import-and-export-grids | JSON export loses theme locks; Save keeps them | README.md:169-172 | unverified | README wording |
| E-13 | import-and-export-grids | CLI `export` accepts only `html`; `-t` title default `Crossword Puzzle`; prints `✓ Exported to HTML: <path>` | `click.Choice(["html"])`, `default="Crossword Puzzle"` cli.py:1620-1645; run | cut (D8: GUI only; was verified) | export run with `-t "My First Puzzle"` |
| E-14 | import-and-export-grids | `import-nyt -o`, `--filled`, `--no-verify` behave as described; prints clues; saved grid has letters/blacks, no clues | cli.py import-nyt options; run on a real upstream file | cut (D8: GUI only; was verified) | import-nyt runs |
| E-15 | import-and-export-grids | Not-JSON input ends `Error: Invalid JSON:` exit 1 | run on mine.txt: `Error: Invalid JSON: Expecting value…` rc=1 | cut (D8: GUI only; was verified) | run |
| E-16 | import-and-export-grids | (cut from the page) exported JSON loads back into the CLI | not proven; sentence removed from the page | cut | n/a |
| X-01 | fill-from-the-command-line | `-w` is required; without it: `Error: At least one wordlist is required (-w/--wordlists)`, exit 1 | cli.py fill (wordlist check); run | cut (D8: GUI only; was verified) | run, rc=1 |
| X-02 | fill-from-the-command-line | Without `-o` the command overwrites the input | `--output` help "defaults to overwriting input" cli.py; md5 changed | cut (D8: GUI only; was verified) | run |
| X-03 | fill-from-the-command-line | Success output as shown (Filling 44 empty slots…, SUCCESS, Slots filled 44/44 …, Saved to) | cli.py:1523-1565 echo lines; run | cut (D8: GUI only; was verified) | `fill11.txt` |
| X-04 | fill-from-the-command-line | Verdict lines SUCCESS / FILLED with N problematic entries / PARTIAL / PAUSED | cli.py:1515-1535 | cut (D8: GUI only; was verified (code); SUCCESS and FILLED observed; PARTIAL and PAUSED text from code) | runs |
| X-05 | fill-from-the-command-line | Exit status is 0 and the file is saved even on partial/problematic results | run `--min-score 100`: 3/44, rc=0, `Saved to` | cut (D8: GUI only; was verified) | run |
| X-06 | fill-from-the-command-line | Typed letters locked by default; `locked` key; `--no-lock-filled` | `--lock-filled/--no-lock-filled default=True` cli.py; help text; `ZIP` survived | cut (D8: GUI only; was verified (default, survival); `locked` key from help text) | run |
| X-07 | fill-from-the-command-line | A blocked pre-flight prints `Blocked: no word fits HELLO?????? at 2,0 across` and exits 3 | cli.py:1160 `sys.exit(3)`; run | cut (D8: GUI only; was verified) | run rc=3 |
| X-08 | fill-from-the-command-line | Defaults: timeout 300, min score 30, algorithm repair, beam width 5, attempts 1, max adaptations 3; flags off | `default=` values via defaults command | cut (D8: GUI only; was verified) | defaults command output |
| X-09 | fill-from-the-command-line | Timeout minimums: 10 for repair/beam, 30 for hybrid; error text and exit 1 | iterative_repair.py:194, orchestrator.py:227, hybrid_autofill.py:110; runs `-t 8` rc=1, `-a hybrid -t 25` rc=1 | cut (D8: GUI only; was verified) | runs |
| X-10 | fill-from-the-command-line | `regex`/`trie` are classic CSP; `--theme-wordlist`, `--json-output` descriptions | `--algorithm` / option help text | cut (D8: GUI only; was verified (help text only)) | not run |
| X-11 | fill-from-the-command-line | `--cleanup` on the CLI is the way to remove invalid words after a fill | `--cleanup` help text cli.py | cut (D8: GUI only; was verified (help text only; behaviour not run)) | not run |
| P-01 | pause-and-resume-a-fill | The web app has no pause control; it has `Cancel` | `pauseFill` defined client.js:198, no caller in `src/` (grep, advisor re-check); AutofillPanel.jsx header comment; `Cancel` button | cut (D8: GUI only; was verified) | grep |
| P-02 | pause-and-resume-a-fill | A run needs `--task-id` to be pausable | `--task-id` help "enabling pause polling + state saving (None → pause path inert)" | cut (D8: GUI only; was verified (help text); consistent with run) | run used --task-id |
| P-03 | pause-and-resume-a-fill | Default state dir `/tmp/crossword_states`, pause flag dir `/tmp` | `resume --help` text | cut (D8: GUI only; was verified (help text only)) | not run without dirs |
| P-04 | pause-and-resume-a-fill | `pause` prints `✓ Pause requested for task: demo1` + second line | run output | cut (D8: GUI only; was verified) | run |
| P-05 | pause-and-resume-a-fill | `pause` only writes a flag; the fill stops at its next checkpoint, may take a while | `pause --help`; run: flag file seen, fill still running 8 s later, paused after ≤ ~35 s | cut (D8: GUI only; was verified) | run |
| P-06 | pause-and-resume-a-fill | The fill prints `⏸ Paused — solver state saved`; state is `<dir>/demo1.json.gz`; partial grid saved to `-o` | run: `st/demo1.json.gz`, `big_out.json` existed | cut (D8: GUI only; was verified) | run |
| P-07 | pause-and-resume-a-fill | `--pause-flag-dir` must match between fill and pause | `pause --help` | cut (D8: GUI only; was verified (help text)) | run used matching dirs |
| P-08 | pause-and-resume-a-fill | `list-states` output format; options `--sort-by`, `--max-age-days`, `--json-output` | run output; `list-states --help` | cut (D8: GUI only; was verified) | run |
| P-09 | pause-and-resume-a-fill | `resume` accepts task id or state file path; reuses recorded wordlists and algorithm unless `-w`/`-a`; never overwrites state; default output `resumed_<task id>.json` | `resume --help` | cut (D8: GUI only; was verified (help text); task id form and `-o` observed) | run |
| P-10 | pause-and-resume-a-fill | A mismatched algorithm gives `fresh fill from the saved grid`; here a paused `repair` run was recorded as `csp` | resume output line; `list-states --json-output` showed `"algorithm": "csp"` | cut (D8: GUI only; was verified) | run. Odd: recorded algorithm differs from the one used (see discrepancy list) |
| P-11 | pause-and-resume-a-fill | Resumed run ended `⚠ FILLED with 16 problematic entries` | resume output | cut (D8: GUI only; was verified (one run; varies)) | run |
| R-01 | troubleshoot | `Missing: ...` lines stop setup before anything is created | setup.sh:10-12, 15-48; run with node hidden | verified | run |
| R-02 | troubleshoot | python3-venv message text and cause (Debian/Ubuntu) | `VENV_MISSING` setup.sh:57; comment setup.sh:51-55 | verified (code) | not reproduced (venv works here) |
| R-03 | troubleshoot | `Error: npm ci failed (output above). ...` | setup.sh:95 | verified (code) | not reproduced |
| R-04 | troubleshoot | `Port 5000 is in use...` and `PORT=5001 python3 run.py` | run.py:37,48,56 | verified | run |
| R-05 | troubleshoot | Unbuilt frontend shows "Development Mode / The frontend hasn't been built yet"; fix `./setup.sh` or `npm run build` then restart | backend/app.py:94-115 (`frontend/dist` missing) | verified (code) | not reproduced (dist exists) |
| R-06 | troubleshoot | Status `offline` when backend unreachable; Verify/Clean disabled | TopBar.jsx `offline`; useHealth.js | verified (code) | not reproduced |
| R-07 | troubleshoot | Status `degraded` when the backend reports `degraded` (CLI adapter unhealthy) | routes.py:40-57 `health_check`; TopBar.jsx `label` | verified (code) | not reproduced |
| R-08 | troubleshoot | Autofill endings that need `Keep`; red squares mean letters no word fits | see A-13..A-17 | verified (code) | partly observed |
| R-09 | troubleshoot | Storage-full save message | `QUOTA_MESSAGE` useSaveMachine.js:61 | verified (code) | not triggered |
| R-10 | troubleshoot | Upload preview reports skips; refused if no valid line; shipped lists protected | see L-10, L-11, L-15 | verified (code) | not run |
| R-11 | troubleshoot | Theme file rejection messages and 1 MB limit | see H-03, H-04, H-06 | verified (code) | not run |
| R-12 | troubleshoot | Import rejection messages | see E-03, E-05 | verified (code) | not run |
| W-01 | web-app | Top bar controls and labels (Undo, Redo, Verify words, Clean grid, Save grid, status, saved label, theme button) | TopBar.jsx; useSaveMachine.js:53-58 | verified | first.png |
| W-02 | web-app | Undo/Redo disabled when stack empty, while autofill runs or a batch is open | `disabled={!canUndo \|\| editingPaused \|\| batchOpen}` TopBar.jsx | verified (code) | |
| W-03 | web-app | Status `degraded` = backend reports degraded; `offline` = unreachable | `verdictFor` useHealth.js:21-27; health_check routes.py:40-57 | verified (code) | `online` observed only |
| W-04 | web-app | Theme button switches light/dark and is remembered | `usePersistentState('xw_theme'…)` App.jsx:103-105; `data-theme` App.jsx:374 | verified (code) | not clicked |
| W-05 | web-app | Left rail tools, Symmetry default on, GRID stats, VIOLATIONS tagged `(unverified)` while pending | ToolRail.jsx:`VIOLATIONS{unverified ? ' (unverified)' : ''}` | verified | first.png |
| W-06 | web-app | Grid tool controls and the `Delete "<name>"?` confirm | GridPanel.jsx | verified (code) | |
| W-07 | web-app | Search defaults: `comprehensive`, `Regex (Classic)`, Score, Min Score 0, 50 results | PatternMatcher.jsx:`useState` defaults, `maxResults: 50` | verified (code) | |
| W-08 | web-app | Autofill defaults and choices; sliders | `DEFAULT_OPTIONS` AutofillPanel.jsx; see A-01..A-07 | verified | |
| W-09 | web-app | Autofill heading shows empty slots and theme words | AutofillPanel.jsx heading (`emptySlots`, `themeCount`) | verified (code) | `41 empty slots` observed |
| W-10 | web-app | Theme tool controls | ThemeWordsPanel.jsx:382-455; see H-05..H-08 | verified (code) | |
| W-11 | web-app | `Analyze Placements` button appears when words are loaded and no suggestions yet | ThemeWordsPanel.jsx `!suggestions &&` button | verified (code) | |
| W-12 | web-app | Lists tool controls; `Categories` | WordListPanel.jsx:225,244-260,346,415-421 | verified (code) | |
| W-13 | web-app | Import tool controls | ImportPanel.jsx:280-380 | verified (code) | |
| W-14 | web-app | Export tool controls; HTML preview unavailable | ExportPanel.jsx:148-161, 138 | verified | `Export Format` observed |
| W-15 | web-app | Click selects; letters write and advance; arrows select direction; Space/`.`; Enter; Tab/Shift+Tab; Backspace/Delete rules | CrosswordGrid.jsx:100-170 | verified (code) | typing/Space observed |
| W-16 | web-app | Right-click toggles theme lock on a white square | `handleRightClick` CrosswordGrid.jsx:277-280; `writeToggleThemeLock` gridEdits.js:77-83 | verified (code) | not run |
| W-17 | web-app | Ctrl+Y and Ctrl/Cmd+Shift+Z redo; Cmd/Ctrl+Z undo | App.jsx:162-176 | verified (code) | |
| W-18 | web-app | Hidden features: Clues, Heatmap, Suggest Black Square, PDF/.puz, Include clues; no pause button | ToolRail.jsx header comment; AutofillPanel.jsx header comment; spec 0.2.7 §3.1 (G10); `pauseFill` has no caller | verified | grep; not-visible confirmed in first.png/tut screenshots |
| W-19 | web-app | `×` closes the Theme panel | ThemeWordsPanel.jsx:382 | verified (code) | |
| Z-01 | file-formats | JSON export has `size`, `grid` (`#`, letter, `.`), `numbering` | `gridData` ExportPanel.jsx:16-22 | verified (code) | JSON export not run (HTML export run) |
| Z-02 | file-formats | `numbering` keyed `"row,col"`, 0-based | `gridData.numbering[\`${row},${col}\`]` ExportPanel.jsx:`generateHTML` | verified (code) | |
| Z-03 | file-formats | Importer accepts size 3-25 and the listed rules; a cell may also be `""`, read as empty (PR #108 review) | ImportPanel.jsx:46,102; gridSizes.js:7-8 | verified (code) | |
| Z-04 | file-formats | `numbering` optional on import | `numbering: data.numbering \|\| {}` ImportPanel.jsx | verified (code) | |
| Z-05 | file-formats | HTML export structure: heading `Crossword Puzzle`, one table, number span, black cells, no clues, fixed title | ExportPanel.jsx:56-100; exported file read | verified | crossword.html |
| Z-06 | file-formats | Text export uses `■` for black | ExportPanel.jsx:109 | verified (code) | |
| Z-07 | file-formats | Theme file rules (caps, dedupe, drop non-alpha lines, 3..grid length, `MAX_THEME_WORDS`, 1 MB) | theme_routes.py upload; theme_placer.py:457-485; ThemeWordsPanel.jsx size check | verified (code) | not run |
| Z-08 | file-formats | Word list line forms and rules | see L-01..L-06 | verified | parse-wordlist run |
| Z-09 | file-formats | Uploaded lists stored under `data/wordlists/custom/` | see L-12 | verified (code) | |
| Z-10 | file-formats | Saved grids live in browser local storage, no file | see S-06 | verified | |

| V-01 | save-open-and-recover | `Start blank` only dismisses the banner and opens the Grid tool; the grid is not cleared | `onStartBlank` App.jsx:796-800 ("it creates nothing itself") | verified | independent reviewer's browser run (`Filled 4.1%` before and after) |
| V-02 | add-theme-words, web-app | Hovering a placement suggestion does not change the grid | `handleMouseEnterSuggestion` sets state only, ThemeWordsPanel.jsx:56; panel help text at :449 makes the opposite claim | verified | reviewer compared grid SVG before/during hover: unchanged |
| V-03 | troubleshoot, add-theme-words | A theme line with a space, hyphen or digit is dropped silently; a too-short word is the only reported error; any error rejects the list | `word.isalpha()` theme_routes.py:60; `validation.valid` | verified | my POST to /api/theme/upload: words `AB, HELLO, JAZZ`, errors `AB: Too short`, `valid: false` |
| V-04 | add-theme-words, web-app | Placing a word can add black squares | `added_black_squares` theme_routes.py:262 | verified (code); runtime by reviewer only | reviewer: Apply All of 3 words took Black 0→6; not reproduced by me |
| V-05 | add-theme-words, file-formats | More than 50 theme words is refused | `MAX_THEME_WORDS = 50` theme_placer.py:27 | verified | read |
| V-06 | add-theme-words, web-app | Each suggestion shows `Row r, Col c (direction)` (from 1), a score out of 100, a reason, and the button `✓ Apply This Placement` | ThemeWordsPanel.jsx:485,501 | verified (code) | |
| V-07 | autofill-a-grid | Extra endings: `Cancelled by user`, `No solution found`, `Autofill failed`, `Lost contact with the autofill run.`, `Autofill was paused outside the app.`, and the `some entries may need review` variant | useAutofillMachine.js:67,406,427,437,449,457,551 | verified (code); not reproduced | rows marked `[?]` in the page |
| V-08 | autofill-a-grid, web-app | `Start Autofill` renders only when the machine is idle; `Reset` is needed after any result | `state === 'idle' &&` AutofillPanel.jsx:387 | verified | reviewer runtime: after Keep fill no Start button; after Reset it returned |
| V-09 | autofill-a-grid, web-app, tutorial | The empty-slot count includes partly filled slots | `countEmptySlots` AutofillPanel.jsx:62-66 (`slot.pattern.includes('?')`) | verified (code) | `41` observed with JAZZ typed |
| V-10 | autofill-a-grid, tutorial | `Successfully filled N/M slots!` leaves the grid already filled with only `Reset` | useAutofillMachine.js:377-392 | verified | reviewer runtime: `0 empty slots Successfully filled 42/42 slots! Reset` |
| V-11 | save-open-and-recover, web-app | Save labels `unsaved changes`, `saving…`, `offline — will retry`; autosave about 30 s | useSaveMachine.js:362-375; `AUTOSAVE_MS = 30000` useSaveMachine.js:50 | verified | reviewer runtime: `unsaved changes` then `saved locally · just now` after 34 s |
| V-12 | web-app, add-theme-words | `Cmd/Ctrl+L` toggles theme lock; Shift/Alt-click toggles black; clicking the selected square rotates direction | CrosswordGrid.jsx:91-96 and handleCellClick (:266-272) | verified (code); Ctrl+L also reviewer runtime | Shift/Alt-click and click-rotate code-read only |
| V-13 | set-up-the-grid, web-app | Turning a square black erases its letter, and its mirror's with Symmetry on | `writeToggleBlack` gridEdits.js:62-66 | verified | reviewer runtime: `Filled 0.0%`; one Ctrl+Z restored both |
| V-14 | file-formats, use-your-own-word-lists | A word must be 3-21 letters; else skipped as `length outside 3-21` | `_is_valid_word` word_list.py:195-197; reason string cli.py:2423 | verified | reviewer dry-run import skipped `OK` and a 23-letter line |
| V-15 | find-words-by-pattern, web-app | `Sort by` and `Min Score` apply when `Search` is clicked | `searchPattern` PatternMatcher.jsx:93-125 | verified | reviewer runtime (order changed only after re-search) |
| V-16 | set-up-the-grid | VIOLATIONS carries warnings about the grid (isolated regions, a word under three letters, 0-based positions) as well as advice | `useNumbering` puts warnings and suggestions in the list (useNumbering.js:132); strings from `/api/grid/validate` | verified | reviewer ran the route |
| V-17 | import-and-export-grids | Import errors: `Invalid cell value at (r, c): "x". Must be '#', '.', or A-Z.` and `Invalid cell at (r, c): must be a string, got …`; 0-based | ImportPanel.jsx:99,103 | verified (code) | |
| V-18 | install-on-macos | Uploads change tracked `data/wordlists/metadata.json`; may make `git pull` refuse | reviewer saw the tracked file modified by an upload | unverified | pull conflict inferred, not reproduced; page marks `[?]` |
| V-19 | install-on-macos | Uploaded lists live in `data/wordlists/custom/` inside the project folder | WordListManager default dir wordlist_manager.py:28; `category: 'custom'` | verified (code) | |

## Status counts

`verified` means a code line proves the claim; where the claim is about behaviour it was also run, except
rows marked `verified (code)`, which are read from the code and not run. Counts come from this command, not
from hand:

```bash
python3 - <<'PY'
import re, collections
c = collections.Counter()
for row in open("docs/diataxis/claims.md"):
    if not re.match(r"\| [A-Z]-\d+", row):
        continue
    status = row.strip().strip("|").replace("\\|", "@@").split("|")[4].strip().lower()
    c[status.split(" ")[0].split("(")[0]] += 1
print(dict(c))
PY
```

Rows marked `cut (D8: GUI only)` belong to command-line content removed from the guide when the owner ruled
the command line would not be used. They are kept for the record and are not claims the guide makes.

## Independent review

An independent `review-docs` pass (not the author) over `docs/user-guide/` returned Rejected: three
must-fix findings and sixteen should-fix findings, now fixed in the pages; rows `V-01` to `V-19` record the
claims it touched. Its three must-fix findings were: `Start blank` does not clear the grid; hovering a theme
suggestion does not preview it (the panel's own help text says it does); the troubleshooting page named a
theme-file error that cannot occur. The link checker (all links resolve) and `scripts/docs-check.sh` (only the
failure below) were run by the reviewer and again afterwards.

## Discrepancies found, not fixed (D4: recorded only)

- `docs/ARCHITECTURE.md` changelog states a CLI command count that no longer matches
  `python -m cli.src.cli --help`.
- `README.md` says templates for 11x11, 15x15 and 21x21 are included; `validate` reports errors for
  `data/grids/example_11x11.json` and `data/grids/example_21x21.json` (only the 15x15 passes).
- The Theme panel's own help text says hovering a suggestion previews it on the grid
  (`ThemeWordsPanel.jsx`, "Hover over suggestions to preview on grid"); hovering changes nothing.
- The `Start blank` button on the restore banner does not start a blank grid; it opens the Grid tool.
- `crossword fill` exits 0 and saves its output even when the fill is partial or has invalid entries.
- `crossword list-states --json-output` recorded a paused `repair` run with `"algorithm": "csp"`.
- `.claude/skills/review-docs/scripts/check-doc-links.py` run on the repository root stops with a
  `UnicodeDecodeError` on a non-UTF-8 file; run on `docs/user-guide` it works.
- `scripts/docs-check.sh` failed on `.claude/licenses/README.md`: it cited the upstream plugin name in backticks, which the guard cannot find in the tracked tree. The failure came with the vendoring commit `df4f5b2`. Fixed by writing the name in plain text there, so no allow annotation was needed.
