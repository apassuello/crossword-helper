# TASK R — Grid, entry and lookup code of five open-source crossword construction tools

**Run:** Crossword_Tools_CodeRead_RunR_20260902 · **Date:** 2026-09-02
**Method:** primary-source code reading. All six corpora were retrieved to disk and read directly; no
claim here rests on a search-result summary. Every statement carries a `path:line-range` locator.

**Revision pins.** Line ranges are only meaningful against these revisions:

| Corpus | Pin | Last commit |
|---|---|---|
| keiranking/Phil | `28720cc8ef79611761761e785953ed7e4546ccf2` | 2025-01-02 |
| viresh-ratnakar/exet | `ea5711805d7733ebd5350d5a49f082b10389dd40` | 2026-08-19 |
| viresh-ratnakar/exolve | `85dd54908580625e7f5338f1beaef878d8629ab4` | 2026-08-14 |
| ben4808/crosshatch | `e169519b944359bd6f22ab489bf6a672f56f6fe5` | 2021-05-30 |
| paulgb/crossword-composer | `912c5eec86f88fa9fe9cd8a26562e47b35855c5e` | 2020-04-18 |
| Qxw 20200708 | tarball sha256 `ed6c6eff…48d23ea` | release 2020-07-08 |

**Verification.** 206 evidence rows in `evidence.jsonl` pair a locator with a verbatim quote.
`gate_evidence.py` re-reads each cited range from the local clone and asserts the quote occurs inside
it. The gate was run red first — with a deliberately wrong line range and a deliberately mistyped
quote, both of which it rejected — and it caught two genuine transcription errors (`E176`, a
two-line comment cited as one line; `E192`, a locator naming the wrong one of two similar
functions) before passing 198/198.

**Scope note.** Exolve is reported alongside exet rather than as a sixth tool: exet is a construction
UI layered on Exolve's grid and clue objects (`exet/exet.html:206-216`), so exet's answers to R1–R3
are partly Exolve's. Phil's vendored `third_party/glucose-3.0` is likewise reported under Phil: the
crossword-specific grid, entry and lookup code lives in that subtree, not in the JavaScript.

---

## Terminology map

The five codebases use incompatible words for the same three things. Everything below is normalised
to the task's vocabulary — **cell** (one white or black square), **entry** (a maximal run of white
cells in one direction, the thing a word goes into), **candidate** (a word list item that fits).

| This report | crossword-composer | Phil (JS / C++) | CrossHatch | exet / Exolve | Qxw |
|---|---|---|---|---|---|
| cell | **slot** (`crossword-composer/src/grid.rs:3`) | character in a row string / `Coord` | `GridSquare` | `gridCell` | **square**, or **entry** when merged (`qxw-20200708/common.h:154-156`) |
| entry | **word** (`crossword-composer/src/grid.rs:4`) | derived, unnamed / `Word` | `GridWord` | `clue` / *light* | **word** (`qxw-20200708/common.h:157`), a *light* in the UI |
| candidate | dictionary word | match | `EntryCandidate` | `lChoice` | *light* (`qxw-20200708/common.h:278`) |
| black cell | `filled` | `'.'` in the row string | `SquareType.Black` | `!isLight` | `fl` bit 0 (blocked) |

Two traps follow from this table. Crossword Composer's `slot` is a **cell**, not an entry — its
`slot_to_words` is a cell→entry map. Qxw's `entry` is a **cell** (or a merge group of cells), and its
`word` is the task's entry; the report uses Qxw's own words only inside §5, flagged each time.

---

## SOURCES

| id | type | citation | url_or_doi | year | retrieval_status | saved_path | licence_or_access | relevance | what_it_gives_us |
|---|---|---|---|---|---|---|---|---|---|
| **S1** | code | Keiran King et al., *Phil — a free, open-source crossword construction app*. **JavaScript** (with a vendored C++ solver). GitHub, commit `28720cc`. | https://github.com/keiranking/Phil | 2025 | FETCHED | `corpus/repos/phil` | Apache-2.0 (`LICENSE.txt`; per-file headers `phil/cross.js:5-13`) | R1–R6, Phil | Row-of-strings grid model with no entry objects at all; entries and clue identities recomputed on every keystroke. Regex linear scan over per-length buckets for lookup. `.puz`/JSON read and write plus PDF export. |
| **S2** | code | Glucose 3.0 SAT solver (Audemard & Simon; MiniSat by Eén & Sörensson), vendored and modified for crossword filling in `third_party/glucose-3.0`. **C++**, built to WebAssembly via Emscripten. | https://github.com/keiranking/Phil/tree/master/third_party/glucose-3.0 | 2025 | FETCHED | `corpus/repos/phil/third_party/glucose-3.0` | MiniSat/Glucose MIT-style notice, `phil/third_party/glucose-3.0/core/Solver.cc:1-27`, `phil/third_party/glucose-3.0/simp/SimpSolver.cc:1-19`; **no LICENSE file in this subtree** | R1–R5, Phil (solver side) | `simp/Main.cc` holds Phil's real crossword code: a `Grid` with cell→entry index arrays, a `Word` struct, a BFS distance-from-filled metric, a letter-frequency candidate filter, an expanding-radius SAT encoding, and forced-letter computation. |
| **S3** | code | Viresh Ratnakar, *Exet*, v1.08.1 (19 Aug 2026). **JavaScript**. GitHub, commit `ea57118`. | https://github.com/viresh-ratnakar/exet | 2026 | FETCHED | `corpus/repos/exet` | MIT (`LICENSE`; headers `exet/exet.js:1-28`) | R2–R6, exet | A parallel `ExetFillState` over Exolve's grid holding per-cell candidate-letter sets and per-entry candidate lists; an incremental two-phase dead-end sweep; entry identity preserved across black-square edits by cell-list matching; localStorage revision history. |
| **S4** | code | Viresh Ratnakar, *Exolve*. **JavaScript**. GitHub, commit `85dd549`. | https://github.com/viresh-ratnakar/exolve | 2026 | FETCHED | `corpus/repos/exolve` | MIT (`LICENSE`) | R1–R3, R6, exet | Owns the cell and clue objects exet manipulates: 2-D array of plain cell objects, clues keyed by direction+label, per-cell crossing labels and predecessor/successor links, and the two-stage `clearCurr` policy protecting letters shared with a completed crossing entry. |
| **S5** | code | Ben Zoon, *CrossHatch*. **TypeScript** (React). GitHub, commit `e169519`. | https://github.com/ben4808/crosshatch | 2021 | FETCHED | `corpus/repos/crosshatch` | MIT (`License.txt`) | R1–R6, crosshatch | The only repo with explicit per-cell content provenance (`ContentType`), an explicit region abstraction (`Section`) with per-region candidate fills, a precomputed one- and two-position inverted index, and a crossing-aware candidate score. |
| **S6** | code | Paul Butler, *Crossword Composer*. **Rust** (compiled to WebAssembly) plus a **JavaScript/Svelte** UI. GitHub, commit `912c5ee`. | https://github.com/paulgb/crossword-composer | 2020 | FETCHED | `corpus/repos/crossword-composer` | MIT (`LICENSE`) | R1–R6, composer | The Rust/WASM core has no 2-D grid at all: a puzzle is a list of lists of cell indices. Grid, black squares and symmetry live only in the JS UI. Ordering heuristic plus a per-step permuted-dictionary index; no scores, no provenance, no serialisation. |
| **S7** | code | Mark Owen (Windows port by Peter Flippant), *Qxw*, release 20200708. **C** (GTK+2). Tarball sha256 `ed6c6eff…`. | https://www.quinapalus.com/qxw-20200708.tar.gz | 2020 | FETCHED | `corpus/repos/qxw-20200708` | **GPL v2 only** (`LICENCE`; `qxw-20200708/common.h:10-12` — "version 2 of the GNU General Public License") | R1–R6, Qxw | The most explicit data model of the five: a documented square/entry/word terminology, 64-bit alphabet bitmaps per cell per direction, per-cell crossing counts and priorities, an arc-consistency propagation loop with a most-constrained-cell choice rule, and a log-scale multiplicative dictionary score. |
| **S8** | wordlist | Lufz English lexicon (`Lufz-en-v0.10`), bundled with Exet. | https://github.com/viresh-ratnakar/exet/blob/master/lufz-en-lexicon.js | 2026 | FETCHED | `corpus/repos/exet/lufz-en-lexicon.js` | No licence statement in the file; repo `LICENSE` is MIT. Generator at github.com/viresh-ratnakar/lufz (not retrieved). | R4, exet | The shipped index format: a `lexicon` array ordered by popularity plus a sparse `index` object keyed by partially-specified patterns. Top-level keys are `id, language, script, letters, lexicon, index, anagrams, phones, phindex` — **no `scores`**, so score-based ranking is inactive for this list. |
| **S9** | wordlist | Nediger List, bundled with Exet as `nediger-list-part-{1,2}.js` + stems. | https://github.com/viresh-ratnakar/exet/blob/master/nediger-list-part-2.js | 2026 | FETCHED | `corpus/repos/exet/nediger-list-part-2.js` | No licence statement in the files; repo `LICENSE` is MIT | R4, exet | The scored counterpart to S8: part-2 carries a `scores` array of 348,312 values, monotone non-increasing from 100.999978 to 25.0, parallel to `lexicon`. Because it is sorted, a minimum score binary-searches to an index cutoff. |
| **S10** | wordlist | `WL-SP.txt`, Phil's default word list. | https://raw.githubusercontent.com/keiranking/Phil/master/WL-SP.txt | 2025 | FETCHED | `corpus/repos/phil/WL-SP.txt` | No licence statement in the file or repo | R4, Phil | 154,980 lines, one bare uppercase entry per line, **no score field** — confirming Phil's lookup has nothing to rank by. A second bundled list, `WL-MirriamWebster9thCollegiate.txt` (120,996 lines, lower-case), is present but not loaded by default. |
| **S11** | wordlist | `words.txt` shipped with Composer's UI; described in-page as taken from TensorBoard, ~71k terms. | https://github.com/paulgb/crossword-composer/blob/master/ui/public/words.txt | 2020 | FETCHED | `corpus/repos/crossword-composer/ui/public/words.txt` | No licence statement in the file; provenance in `crossword-composer/ui/public/index.html:44-46` | R4, composer | 14,897 lines in the checked-in copy (the page's ~71k figure is not what the repo contains), one bare lower-case word per line, no scores — matching `Dictionary`, which buckets by length only. |
| **S12** | wordlist | CrossHatch sample word list, from Mark Diehl's trim of the Peter Broda list, 7-and-under hand-scored by the CrossHatch author. | https://raw.githubusercontent.com/ben4808/crosswords-dicts/master/sources/Ben/sampleWordList.txt | 2021 | SNIPPET | — | Not stated; only the URL and provenance sentence at `crosshatch/README.md:9-10` were read. File not fetched. | R4, crosshatch | Names the expected input format for crosshatch's parser (`WORD;score` lines). Not retrieved, so the actual score distribution is unverified here. |
| **S13** | format-spec | Across Lite `.puz` binary format, community reverse-engineering wiki, cited as the reference by `crosshatch/src/lib/puzFiles.ts:10`. | https://code.google.com/archive/p/puz/wikis/FileFormat.wiki | 2009 | SNIPPET | — | Public web page; not fetched for this run | R6, Phil + crosshatch | Identified only as the cited authority behind the two independent `.puz` implementations in this set. Its content was not retrieved; every `.puz` claim below comes from reading those two implementations. |
| **S14** | tool-doc | Qxw project page, quinapalus.com. | https://www.quinapalus.com/qxw.html | 2020 | FETCHED | `corpus/qxw.html` | Public web page | Licence/provenance for S7 | States "Qxw is a free (GPL) crossword construction program" and links the download page. |
| **S15** | tool-doc | Qxw download page, quinapalus.com. | https://www.quinapalus.com/qxwdownload.html | 2020 | FETCHED | `corpus/qxwdownload.html` | Public web page | Licence/release for S7 | Confirms 20200708 as the current release and that both Linux and Windows versions are licensed under **version 2** of the GPL. Source tarball link used to retrieve S7. |

---

## 1. crossword-composer [S6]

The smallest codebase in the set: 772 lines across the Rust core and the Svelte UI. Its distinguishing
choice is that **the solver knows nothing about crosswords**. The README states this outright
(`crossword-composer/README.md:14`: "The auto-filler itself is not aware of the structure of crossword puzzles").
Everything two-dimensional is in the browser.

### R1 — Grid data structure

The Rust core has no grid in the ordinary sense. `Grid` is an incidence structure over integers
(`crossword-composer/src/grid.rs:2-6`): `slots: usize`, `words: Vec<Vec<usize>>` mapping an entry to its ordered cell
indices, and `slot_to_words: Vec<Vec<usize>>` mapping a cell back to the entries through it. There is
no row/column notion — the cell count is inferred as `max index + 1` (`crossword-composer/src/grid.rs:25-34`), so a
grid that never mentions its last cell would silently shrink. Black squares are not represented at
all; they are simply cell indices that no entry mentions.

The two-dimensional grid lives only in the UI. `Cell` (`crossword-composer/ui/src/crossword.js:1-8`) holds `filled`,
`value`, `number`, `downWord` and `acrossWord`; the grid is a `dimension × dimension` array of them
(`crossword-composer/ui/src/crossword.js:14-16`). Size is square-only and picked from a fixed list of 3 to 16
(`crossword-composer/ui/src/Crossword.svelte:5-6`) — the 11/15/21 American sizes are a subset, but nothing in the code
knows about them. Symmetry is **hard-wired 180° rotation, not configurable**: `toggle`
(`crossword-composer/ui/src/crossword.js:106-112`) flips the clicked cell and its rotational partner in the same
statement, with no symmetry mode, no toggle and no other axis. There is **no minimum-entry-length
rule and no connectivity check** anywhere in the repository.

### R2 — Entry/slot structure

Entries are enumerated in a single raster scan inside `generateNumbers`
(`crossword-composer/ui/src/crossword.js:36-104`), using the standard start-of-run test — a cell starts a down entry if
the cell above is filled or absent and the cell below is not (`crossword-composer/ui/src/crossword.js:70-72`). The entry
is materialised as a plain array of cell indices pushed into `words`; there is no entry object, no
direction field and no length field.

**Identity is the push order into `words[]`, and `words` is rebuilt from scratch on every toggle**
(`crossword-composer/ui/src/crossword.js:36-37`, called from `toggle` at `:110`). Nothing survives a grid edit — there
are no clues in this tool, so nothing needs to.

Crossings are **stored, not recomputed**, and this is the one place composer invests: the inverse map
is built once in `generate_slot_to_words` (`crossword-composer/src/grid.rs:13-23`) by walking every entry and pushing its
index onto each of its cells. Two entries cross exactly when they share a cell index — the constraint
is structural rather than derived from geometry, which is why the solver can be geometry-blind.

### R3 — Letter ownership

**Not present.** There is no provenance of any kind, per cell or per entry. `Cell` has no flag for
user-typed, suggested or locked (`crossword-composer/ui/src/crossword.js:1-8`). The only letter write path is
`setLetters` (`crossword-composer/ui/src/crossword.js:23-33`), which overwrites every cell from the solver's output
vector at once; there is no path for the user to type a letter at all. A cell that becomes black is
blanked without ceremony (`crossword-composer/ui/src/crossword.js:44-49`). Consequently the question "what happens to
letters shared with a crossing entry when an entry is removed" has no meaning here: entries are never
individually removed.

### R4 — Word lookup

Two structures, both built at load. `Dictionary` (`crossword-composer/src/dictionary.rs:5-7`) is
`HashMap<usize, Vec<Vec<char>>>` — words bucketed by length, nothing more. Then, once the solving
order is fixed, one `Index` per entry (`crossword-composer/src/index.rs:8-13`) maps the tuple of letters that *will
already be known* at that step to the list of `(word id, tuple of unknown letters)` that complete it
(`crossword-composer/src/index.rs:24-32`). The README calls this a permuted dictionary (`crossword-composer/README.md:47`), and notes that
after building the indexes the dictionary itself can be discarded (`crossword-composer/README.md:49`).

Each index answers exactly one pattern shape — the one that entry will face at its position in the
fixed solving order — and cannot answer an arbitrary pattern query. The indexes are built after the
order is chosen (`crossword-composer/src/solver.rs:68-74`) and are invalid if the order changes.

**No scores exist.** `words.txt` is bare words (S11) and `Dictionary::from_vec`
(`crossword-composer/src/dictionary.rs:21-30`) stores only lower-cased character vectors. Candidates are consumed in
index order and the only filter is a duplicate-word rejection scanning the already-assigned prefix
(`crossword-composer/src/solver.rs:88-93`). Ranking is therefore **neither score-based nor crossing-aware — it is
insertion order**.

### R5 — "Where can this word go" / "is this region fillable"

**Not present** as a user-facing or callable routine. The nearest thing is the solving-order heuristic
in `generate_solver_steps` (`crossword-composer/src/solver.rs:29-78`), which repeatedly takes the not-yet-ordered entry
maximising `(constraints[i], words[i].len())` (`crossword-composer/src/solver.rs:41-47`) — most already-constrained
first, longest as tie-break. Its inputs are: the number of times each entry has been touched by a
previously chosen entry's cells, and entry length. It scores entries for *search order*, never for
reporting, and there is no per-entry or per-region output.

> **Observed by reading; consequence not executed.** The `constraints` vector is declared with the
> comment "Word index → number of constraints on this word" but sized `vec![0; grid.slots]`
> (`crossword-composer/src/solver.rs:32-33`), then indexed by word id (`crossword-composer/src/solver.rs:63-65`). In an ordinary crossword
> cells outnumber entries, so the mis-sizing is latent rather than fatal. Not executed.

### R6 — Serialisation

**No puzzle format is read or written**, and nothing is persisted. The only `fetch` is for the word
list, the worker script and the wasm binary (`crossword-composer/ui/src/solver.js:5-10`); a
repository-wide search for `localStorage`, `sessionStorage` and `indexedDB` across `*.js`, `*.svelte`
and `*.html` returned zero hits. The UI page tells the user to take a screenshot
(`crossword-composer/ui/public/index.html:36-39`). A puzzle exists only for as long as the tab is open.

The one place composer does serialise is the **wasm-bindgen boundary**
(`crossword-composer/src/lib.rs:16-53`). The grid crosses as a JS array of arrays of cell indices,
decoded to `Vec<Vec<usize>>` and handed straight to `Grid::new`
(`crossword-composer/src/lib.rs:32-44`); the fill comes back as a JS array of one-character strings
(`crossword-composer/src/lib.rs:46-53`). The word list crosses separately, as an array of strings at
construction (`crossword-composer/src/lib.rs:23-30`), and the worker is torn down and respawned on
every grid edit (`crossword-composer/ui/src/solver.js:41-53`), so no state survives a call.

---

## 2. Phil [S1, S2]

Phil is two programs that share nothing but a string. The JavaScript editor holds a grid of row
strings; the vendored SAT solver parses those strings into its own grid, entry and lookup structures.
Every claim below is tagged with which side it belongs to.

### R1 — Grid data structure

**JS side.** The entire model is `Crossword` (`phil/cross.js:56-71`): `clues`, `title`, `author`, `rows`,
`cols`, and `fill` — **an array of one string per row**. A black square is the character `'.'` inside
that string; blank is `' '` and the pattern wildcard is `'-'` (`phil/cross.js:30-35`). There is no cell
object anywhere; the DOM `<td>` elements carry `data-row`/`data-col` attributes
(`phil/cross.js:82-104`) and are re-queried by selector on every access. Editing a letter is string
splicing (`phil/cross.js:350`).

Symmetry is **180° rotation only**, computed inline in the key handler from the cursor position
(`phil/cross.js:345-346`) and applied when toggling a black square if the global `isSymmetrical` is set
(`phil/cross.js:365-374`). `toggleSymmetry` (`phil/cross.js:704-712`) flips that global. Default size is 15
(`phil/cross.js:35`), and the built-in layout patterns are 15×15 half-grids (`phil/patterns.js:16-32`). No
connectivity check and **no minimum-entry-length rule** exist in the JavaScript.

**Solver side.** `Grid::load` (`phil/third_party/glucose-3.0/simp/Main.cc:161-177`) recovers `cols` and
`rows` by scanning for newlines, then allocates the two cell→entry index arrays. The grid buffer is
the raw string Phil posted, addressed as `data[y * (cols + 1) + x]` (`phil/third_party/glucose-3.0/simp/Main.cc:290-292`) — the
`+1` being the newline. State is dimensions, a `vec<Word>`, and those index arrays
(`phil/third_party/glucose-3.0/simp/Main.cc:293-299`).

### R2 — Entry/slot structure

**JS side: entries are not enumerated into any structure at all.** `updateLabelsAndClues`
(`phil/cross.js:535-566`) rescans the whole grid on every UI update, recomputing which cells start an
across or down entry and renumbering them into the DOM. The current across and down entries are
recomputed on demand by `getWordAt` (`phil/cross.js:586-607`), which slices the row string or builds the
column string and finds the run boundaries.

Entry identity is the **stringified `[row, col, direction]` key** of the start cell — used for the
clue dictionary (`phil/cross.js:554-563`), for setting clues (`phil/cross.js:658-663`) and for PDF generation
(`phil/files.js:447-460`). It is purely positional, and the consequence is explicit in the code: when a
cell stops starting an entry, its clue is **deleted outright** in the same scan
(`phil/cross.js:554-563`, the `delete xw.clues[[i, j, ACROSS]]` branch). Adding a black square destroys
the clues of every entry whose start moves.

**Crossings are neither stored nor computed** on the JS side. Nothing maps a cell to the two entries
through it; the editor only ever needs the two entries at the cursor, which it rebuilds each time.

> **Observed by reading; consequence not executed.** `getWordIndices` (`phil/cross.js:609-615`) bounds its
> search with the constant `DEFAULT_SIZE` (15) rather than the actual row or column length, so on a
> non-15 grid the end index would be wrong. Not executed.

**Solver side.** `Grid::analyze` (`phil/third_party/glucose-3.0/simp/Main.cc:179-205`) enumerates entries in one raster scan and
`add_word` (`phil/third_party/glucose-3.0/simp/Main.cc:207-225`) registers each one, writing its index into `across[]` or `down[]`
at every cell it covers (`phil/third_party/glucose-3.0/simp/Main.cc:297-299`). This is the only place in Phil where **crossings
are stored**, and the BFS in R5 depends on it. Each `Word` (`phil/third_party/glucose-3.0/simp/Main.cc:147-152`) carries its cell
list, a count of already-filled cells, and a distance field.

### R3 — Letter ownership

**Not tracked, at either level.** Placing a candidate (`phil/wordlist.js:136-153`) splices the chosen word
into the row strings (across) or into each row at a fixed column (down) and writes the letters into
the DOM; letters shared with crossing entries are simply overwritten, with no record that they
changed. `clearFill` (`phil/cross.js:718-724`) replaces every word character in every row with a space,
keeping black squares only because the regex matches `\w`.

The single provenance-like distinction is **not per cell and not persistent**: solver-derived forced
letters are held in a parallel array `forced` and rendered in a separate "pencil" class when the
underlying cell is blank (`phil/cross.js:119-124`, repeated in `updateGridUI` at `phil/cross.js:455-460`). The
array is discarded at the start of the next autofill (`phil/cross.js:728`). There is no locked flag, no
user-typed flag and no per-entry ownership anywhere in the repository.

### R4 — Word lookup

**JS side: linear scan, no index, no scores.** The word list is an array of arrays indexed by length,
sized 16 and filled at load (`phil/wordlist.js:16-20`, `:27-34`). `matchFromWordlist`
(`phil/wordlist.js:94-110`) turns the pattern into a regex by replacing dashes with `\w` and then scans
the whole length bucket. Two behaviours follow from `phil/wordlist.js:97-99`: a completely blank entry
returns **no** candidates (the search is skipped), and so does a completely full one.

Ranking is **word-list order**, which after `sortWordlist` (`phil/wordlist.js:36-40`) is alphabetical.
`updateMatchesUI` (`phil/wordlist.js:112-134`) renders the across and down candidate lists uncapped and
unsorted by anything else. There is no crossing-awareness. A per-candidate score display exists but is
commented out (`phil/wordlist.js:122-123`), and the default list carries no score column (S10).

**Solver side.** `Wordlist::get_matching` (`phil/third_party/glucose-3.0/simp/Main.cc:113-136`) is the same idea in C++ — a length
bucket and a character-by-character scan, with a fast path returning the whole bucket for an entirely
blank pattern. The one filter that resembles scoring is `check_freq_constraint`
(`phil/third_party/glucose-3.0/simp/Main.cc:269-282`): a candidate is rejected if it places a letter outside the first `thresh1`
(or `thresh2`) characters of the hard-coded frequency string `"ETAOINSHRDLCUMWFGYPBVKJXQZ"`, where
which threshold applies depends on how far the cell is from already-filled material. This is a
**locality-conditioned alphabet restriction, not a word score** — it prunes the SAT instance, and it
is only enabled in quick mode (`phil/xw_worker.js:19-23`).

### R5 — "Where can this word go" / "is this region fillable"

Phil has the most developed region machinery of the four browser tools, and all of it is in the C++.

`Grid::bfs` (`phil/third_party/glucose-3.0/simp/Main.cc:227-253`) computes, for every entry, its **distance from the nearest
partly- or fully-filled entry**, breadth-first over the entry adjacency graph (`dist = 0` for entries
with any filled cell, set in `add_word` at `phil/third_party/glucose-3.0/simp/Main.cc:223`). A cell's distance is the smaller of
its two entries' distances (`phil/third_party/glucose-3.0/simp/Main.cc:264-267`).

That distance is the fillability probe. `fill_core` builds a SAT instance containing **only the
entries within `max_dist` of filled material** (`phil/third_party/glucose-3.0/simp/Main.cc:372-374`), so the question asked is
"can this neighbourhood be filled?" rather than "can the grid be filled?". `fill_iterative`
(`phil/third_party/glucose-3.0/simp/Main.cc:506-539`) starts the radius at 2, and on a dead end widens it by one, restores the
saved grid and retries. Distance also gates which of the solver's answers are written back
(`phil/third_party/glucose-3.0/simp/Main.cc:490`), so a run can commit the near neighbourhood and leave the far one blank.

The inputs the region score consumes are therefore: entry adjacency, which entries already have
letters, the radius, and the frequency thresholds. It does not consume word scores — there are none.

The whole-grid answer is exposed as a **binary signal**: quick mode writes no letters and only adds
the class `sat` or `unsat` to the grid element (`phil/cross.js:759-776`), triggered on every mutation
(`phil/cross.js:437-439`).

`fill_compute_forced` (`phil/third_party/glucose-3.0/simp/Main.cc:541-572`) answers a different and sharper question — which cells
are *forced* — by refilling repeatedly with a reshuffled word list, keeping the cells that agree every
time, and adding a clause forbidding the agreed assignment so the next round must differ.

> **Observed by reading; consequence not executed.** The `-compute-forced` flag defaults to false
> (`phil/third_party/glucose-3.0/simp/Main.cc:577-579`) and is **commented out of its only call site, in both branches**
> (`phil/xw_worker.js:19-23`), while the UI still handles the resulting `'forced'` message
> (`phil/cross.js:783-789`) and still renders `forced[][]` in pencil (`phil/cross.js:455-460`). The receiving
> half of the feature is live; the producing half is disabled. Not executed.

There is **no "where can this word go" routine** — nothing takes a word and returns candidate
locations. The only word→grid path is `fillGridWithMatch` (`phil/wordlist.js:136-153`), which places a
word at the cursor's entry.

### R6 — Serialisation

The richest read/write set of the four browser tools, and no persistence at all.

`PuzReader` (`phil/files.js:21-78`) reads Across Lite `.puz`: dimensions at `0x2c`/`0x2d`, the scrambled
flag at `0x32` (refused, `phil/files.js:44-47`), the solution grid at `0x34`, then the null-terminated
string block, reconstructing clue order by re-deriving entry starts. `PuzWriter`
(`phil/files.js:80-240`) writes `.puz` v1.3 including all four masked checksums
(`phil/files.js:217-231`). `openFile` (`phil/files.js:254-285`) accepts `.json`, `.xw` and `.txt` parsed as
JSON, and `.puz` sniffed for the `ACROSS&DOWN` magic with a JSON fallback for mislabelled files.
`writeFile` (`phil/files.js:352-373`) emits `.puz` or JSON, and `printPDF` (`phil/files.js:409-432`) emits PDF
including an NYT-submission layout.

Two limits are worth recording. Import is **hard-refused for anything but 15×15**
(`phil/files.js:302-307`), regardless of the file's declared size. Rebus squares are flattened to their
first letter on import (`phil/files.js:322`).

The JSON interchange shape (`phil/files.js:375-407`) is `{author, title, size:{rows,cols},
clues:{across:[…], down:[…]}, grid:[…]}` with clues as label-prefixed strings and the grid as a flat
character array — i.e. it round-trips the same information as `.puz`, not Phil's internal state.
There is **no `localStorage`, `sessionStorage` or `indexedDB`** anywhere in the repository (zero hits
across `*.js`/`*.html`).

---

## 3. CrossHatch [S5]

The only repository in the set that models provenance and regions as first-class data. Its `models/`
directory is fifteen small interfaces and enums that together answer R1–R3 almost by themselves.

### R1 — Grid data structure

`GridState` (`crosshatch/src/models/GridState.ts:4-11`) is `height`, `width`, `squares: GridSquare[][]`,
`words: Map<string, GridWord>`, a `usedWords` set for duplicate detection, and a set of region fills
the user has committed. `GridSquare` (`crosshatch/src/models/GridSquare.ts:4-15`) carries `row`, `col`,
`number?`, `type`, `isCircled`, `content?`, `contentType`, and `viableLetters?: string[]` — the
candidate-letter set is stored **on the cell**.

Black squares are a cell type rather than a sentinel character (`crosshatch/src/models/SquareType.ts:1-5`); a
commented-out third value `Blank` suggests an abandoned third state. Grid creation
(`crosshatch/src/lib/grid.ts:171-199`) takes independent width and height, so non-square grids are supported.

Symmetry is the **most general of the five**: a seven-valued enum covering none, 180°, 90°, both
mirrors and both diagonals (`crosshatch/src/models/SymmetryType.ts:1-9`). `getSymmetrySquares`
(`crosshatch/src/lib/grid.ts:213-245`) maps a cell to its whole orbit under the current mode, and the black-square
toggle sets the same type on every member (`crosshatch/src/components/Grid/Grid.tsx:104-116`). There is **no
connectivity check and no minimum-entry-length rule**; the word list is filtered to lengths 2–15
(`crosshatch/src/lib/wordList.ts:48-51`) but nothing rejects a two-cell entry in the grid.

The numbering scan (`crosshatch/src/lib/grid.ts:86-111`) is unusual in explicitly handling **unchecked** cells —
those blocked on both sides in one direction — and numbering a run only if it is a "checked start" or
an "unchecked start" (`crosshatch/src/lib/grid.ts:100-105`).

### R2 — Entry/slot structure

`GridWord` (`crosshatch/src/models/GridWord.ts:3-8`) is `number?`, `direction`, `start: [row,col]`,
`end: [row,col]` — the cell list is derived by walking from start to end
(`crosshatch/src/lib/util.ts:65-76`), not stored. `populateWords` (`crosshatch/src/lib/grid.ts:22-62`) enumerates across
entries in a row-major pass and down entries in a column-major pass, rebuilding
`grid.words` from scratch each time; runs of length 1 are dropped
(`crosshatch/src/lib/grid.ts:39-41`).

Identity is `wordKey` (`crosshatch/src/lib/util.ts:151-153`): the string `` `[${start[0]},${start[1]},${A|D}]` ``.
**Positional, therefore not stable across black-square edits.** `Puzzle.clues`
(`crosshatch/src/models/Puzzle.ts:3-9`) is a `Map<string,string>` keyed by exactly that string, and it lives
outside `GridState`. On a black-square change (`crosshatch/src/components/Grid/Grid.tsx:125-131`) the code calls
`populateWords`, `initializeSessionGlobals`, `clearFill` and `updateGridConstraintInfo` — and nothing
that remaps clue keys. A repository-wide search over `src/**/*.ts,tsx` for `clues` finds it written
only by the `.puz` importer (`crosshatch/src/lib/puzFiles.ts:58`) and the clue editor
(`crosshatch/src/components/CluesView/CluesView.tsx:83`), and a search for `remap|relocat|renumber|migrat`
returns only rebus-mapping hits in `puzFiles.ts`. **Scoped claim:** within the files that search
covers, no clue-remapping routine exists, so clues attached to entries whose start cell moves become
unreachable.

**Crossings are recomputed, and expensively.** `getWordAtSquare` (`crosshatch/src/lib/util.ts:78-91`) iterates
*every entry in the grid* testing containment; `getAllCrosses` (`crosshatch/src/lib/fill.ts:311-317`) calls it
once per cell of an entry. For a 15×15 grid with ~78 entries that is ~78 comparisons per cell and
~550 per entry, executed inside the candidate-scoring inner loop of §R4.

### R3 — Letter ownership

The most explicit answer in the set, and the only one that distinguishes *how* a letter arrived.
`ContentType` (`crosshatch/src/models/ContentType.ts:1-8`) has six values: `User`, `ChosenWord`,
`HoverChosenWord`, `ChosenSection`, `HoverChosenSection`, `Autofill`. It is **per cell**, stored on
`GridSquare.contentType`.

`eraseGridSquare` (`crosshatch/src/lib/grid.ts:254-291`) implements the ownership rule. Erasing a cell first
removes the affected complete entries from `usedWords` (`:262-263`), then branches on the entry's
provenance. If any cell is `Autofill` the entry is dropped without bookkeeping — "autofill is
ephemeral, no need to explicitly delete" (`crosshatch/src/lib/grid.ts:265-267`). Otherwise, for a user- or
word-committed entry, each cell is examined individually (`crosshatch/src/lib/grid.ts:271-285`):

- a cell whose `contentType` is `User` is **left alone entirely** — the user's own letters survive
  the removal of any entry through them;
- a `ChosenWord` cell with no crossing entry is demoted to `Autofill`;
- otherwise, if the crossing entry holds autofill or section content, the cell is demoted to
  `ChosenSection` or `Autofill` depending on whether it lies inside a committed region fill.

Only the clicked cell's own content is then cleared (`crosshatch/src/lib/grid.ts:288-289`). `clearFill`
(`crosshatch/src/lib/grid.ts:305-320`) applies the same principle in bulk: everything that is not user-filled —
where `isUserFilled` (`crosshatch/src/lib/util.ts:181-184`) means `User`, `ChosenWord` or `ChosenSection` — is
wiped. Placing an entry is the mirror image: `processAndInsertChosenEntry`
(`crosshatch/src/lib/insertEntry.ts:20-24`) upgrades a cell's provenance only if it was `Autofill`,
`ChosenSection` or `HoverChosenWord`, so a user-typed letter keeps its status when an entry is laid
over it.

There is **no per-entry provenance and no explicit lock flag**; "locked" is expressed as
`ContentType.User`, which the erase and clear paths both respect.

> **Observed by reading; consequence not executed.** In `eraseGridSquare` the across and down lookups
> at `crosshatch/src/lib/grid.ts:257` and `:260` pass the **same** `dir` argument, so `otherDirWord` is the same
> entry as `word` and the "other direction" branch at `:263` re-tests the entry already tested at
> `:262` instead of the crossing entry. Not executed.

### R4 — Word lookup

The most elaborate lookup structure of the five and the only genuinely precomputed inverted index.
`indexWordList` (`crosshatch/src/lib/wordList.ts:92-138`) builds two nested bucket arrays:

- `oneVal[length-2][position][letter]` — every word of that length with that letter at that position;
- `twoVal[length-2][pos1][pos2-(pos1+1)][letter1][letter2]` — every word matching a *pair* of
  position/letter constraints.

`queryIndexedWordList` (`crosshatch/src/lib/wordList.ts:59-90`) dispatches on how many letters the pattern fixes:
one → a single `oneVal` bucket; all → a membership test; two or more → the `twoVal` bucket for the
first two constraints, then a linear `.filter` for the rest. **A pattern with zero fixed letters falls
through every branch and returns an empty array** (`crosshatch/src/lib/wordList.ts:59-90`) — an entirely blank
entry yields no candidates, the same behaviour as Phil but reached by a different route.

The `twoVal` structure is what makes crosshatch's scoring affordable, and it is also its dominant
memory cost: for lengths 2–15 it is `Σ_L C(L,2) · 26²` posting lists, ~380k arrays before any word is
inserted, with every word of length `L` appearing in `C(L,2)` of them (`crosshatch/src/lib/wordList.ts:131-135`).

**Scores are read and then discarded.** `parseWordList` (`crosshatch/src/lib/wordList.ts:34-57`) splits on `;`,
defaults a missing score to 50, and immediately collapses the number into one of three
`QualityClass` values at thresholds 100 and 50; only the class is stored, in a separate
`Map<string, QualityClass>`. `getWordScore` (`crosshatch/src/lib/fill.ts:355-364`) maps the class back to
12 / 9 / 3 / 1. The original score is unrecoverable. (`crosshatch/README.md:47-51` describes thresholds of 50 and
40 and three tiers named Good/Okay/Iffy — **the documented thresholds do not match the code's 100 and
50**; observed by reading, consequence not executed.)

**Ranking is crossing-aware, and this is crosshatch's centrepiece.**
`calculateEntryCandidateScore` (`crosshatch/src/lib/entryCandidates.ts:410-416`) is
`(crossScore/topCrossScore + minCrossScore/topMinCrossScore) × wordScore × (iffy ? 1 : 100)` —
combining the candidate's own quality weight with two normalised measures of how well it leaves the
crossings: the **total** support summed over crossing entries and the **worst** single crossing's
support. Both come from `processEntry` (`crosshatch/src/lib/entryCandidates.ts:215-348`), which tentatively fixes
the candidate and propagates outward in waves: crossing entries are re-queried under the implied
letters, their surviving candidates' letters intersected into the cells, and the wave repeats while
any cell's letter set shrank (`:290-313`). A crossing left with zero candidates marks the whole
candidate non-viable (`:278-281`); a crossing whose anchor combinations exceed 20 is charged a flat
penalty of 300 instead of being explored (`:259-264`).

Two devices keep this tractable. **Anchoring** (`crosshatch/src/lib/entryCandidates.ts:62-97`) picks the two cells
with the fewest viable letters and runs the query once per letter pair, so the search is driven from
the most constrained positions. The pairs are ordered by English letter frequency times a random
factor (`crosshatch/src/lib/entryCandidates.ts:99-107`, `:118-127`), which makes the ordering **non-deterministic
between runs**. And `broadenAnchorPatterns` (`crosshatch/src/lib/entryCandidates.ts:379-408`) expands a pattern
into at most 12 concrete patterns, stopping when the next cell has 6 or more possibilities.

A cheap alternative path exists and is exposed in the UI: `populateNoHeuristicEntryCandidates`
(`crosshatch/src/lib/entryCandidates.ts:39-60`) returns the raw pattern matches sorted by quality class alone
(`crosshatch/README.md:30` describes the toggle).

### R5 — "Where can this word go" / "is this region fillable"

**"Where can this word go" is not present.** "Is this region fillable" is present and is the
architectural centre of the tool.

`Section` (`crosshatch/src/models/Section.ts:5-18`) is a named region: its cells, its entries, its "stack"
entries, a fill order, the crossing entries on its boundary, a map of **complete candidate fills**
(`SectionCandidate`), its own priority queue, and its connections to other regions.

`generateGridSections` (`crosshatch/src/lib/section.ts:83-129`) derives them. Region seeds are **open squares** —
cells whose entire 3×3 neighbourhood is white (`crosshatch/src/lib/section.ts:291-294`) — flood-filled through
neighbouring open squares, then extended to every entry touching any cell reached
(`crosshatch/src/lib/section.ts:93-102`). Section 0 is always the whole grid (`:110-118`); single-cell regions are
discarded (`:125`); and if the grid yields exactly one real region it is deleted as redundant
(`:130`). "Stack" entries are same-direction neighbours overlapping by ≥5 cells
(`crosshatch/src/lib/section.ts:132-162`), and they are filled first, from the middle of each stack outward
(`crosshatch/src/lib/section.ts:226-239`).

A region's answer is a **set of concrete complete fills, each scored**:
`calculateSectionCandidateScore` (`crosshatch/src/lib/section.ts:326-338`) is the mean quality weight over the
region's entries, multiplied by 10 if the fill needed no out-of-list entry. The UI lists them sorted
by that score (`crosshatch/src/components/FillView/FillView.tsx:368`, `:525`), and typing a letter into the grid
filters the list (`updateSectionFilters`, `crosshatch/src/lib/section.ts:15-30`).

The per-cell fillability signal is `viableLetters`, recomputed by
`generateConstraintInfoForSquares` (`crosshatch/src/lib/grid.ts:113-141`) from the entry's candidate list — but
**only when that list has at most 500 members** (`crosshatch/src/lib/grid.ts:126`), so on an open grid the
information is simply absent rather than wrong. An empty `viableLetters` is the "this entry cannot be
filled" marker (`crosshatch/src/lib/util.ts:199-202`).

> **Observed by reading; consequence not executed.** `letterListToLetterMatrix`
> (`crosshatch/src/lib/util.ts:256-261`) writes at `matrix[ltr.charCodeAt(0)]` — omitting the `- 65` offset used
> by its inverse `letterMatrixToLetterList` (`crosshatch/src/lib/util.ts:252-254`) and by every other reader,
> including the intersection at `crosshatch/src/lib/grid.ts:131-136`. Not executed.

### R6 — Serialisation

**`.puz` only, in both directions, and no persistence.** `processPuzData`
(`crosshatch/src/lib/puzFiles.ts:19-123`) checks the `ACROSS&DOWN\0` magic, reads dimensions, builds the grid, and
then walks the extension sections: `GRBS`/`RTBL` for rebus (flattened to the first letter,
`:116`), and `GEXT` bit `0x80` for circled cells (`:102-104`). Imported letters are marked
`ContentType.User` (`:40`) — the importer takes the position that everything in a file is the
constructor's own.

`generatePuzFile` (`crosshatch/src/lib/puzFiles.ts:140-263`) writes v1.3 with the same masked-checksum scheme, and
emits a `GEXT` section only when at least one cell is circled (`:201-221`). The checksum routine
carries an attribution comment to Phil (`crosshatch/src/lib/puzFiles.ts:265-266`) — the two implementations are
related, not independent.

Clue order for the file is a positional sort — row, then column, then across before down
(`crosshatch/src/lib/puzFiles.ts:290-296`) — which is the `.puz` convention, and the reason the clue map's
positional keys survive a round trip even though they do not survive an edit.

The file picker accepts `.puz` and nothing else (`crosshatch/src/components/Menu/Menu.tsx:52`). No
`localStorage`, `sessionStorage` or `indexedDB` appears anywhere in `src/` or `public/` (zero hits).

---

## 4. exet (with Exolve) [S3, S4]

exet is a construction UI over Exolve, the same author's solving/rendering library. `exet/exet.html:206-216`
loads `exolve-m.js` and the four format converters before any exet script, so R1 and most of R2–R3
are Exolve's answers; exet contributes a **second, parallel state** carrying the fill analysis.

### R1 — Grid data structure

**Exolve.** `newGridCell` (`exolve/exolve-m.js:3165-3200`) builds a plain object per cell:
`row`, `col`, `currLetter` (what is displayed, initialised `'?'`), `solution` (the answer letter, or
`'.'` for a block), `isLight`, `prefill`, `isDgmless`, `hasBarAfter`, `hasBarUnder`, `hasCircle`, and
six DOM node handles. The grid is a plain 2-D array of these (`exolve/exolve-m.js:3226-3228`). A black
cell is `isLight === false`, derived from `solution === '.'` (`exolve/exolve-m.js:3179-3183`).

Cell decorators are parsed from the textual grid spec (`exolve/exolve-m.js:3276-3298`): `|` and `_`
for bars, `@` for a circle, `*` for diagramless, `!` for prefill, `~` to skip numbering. **Bars mean
this is the only structure in the set that supports barred grids as a first-class case**, and the
`isConnected` check below walks bars as well as blocks.

**exet.** Black-square toggling is `exet/exet.js:5346-5354`: flip `isLight`, mirror through the 180°
partner unless `asymOK` is set, then re-derive the clues. **Symmetry is 180° only** — there is no
symmetry-mode enum; the same three-line pattern recurs for bars (`exet/exet.js:5355-5378`).

exet is also the **only tool in the set that encodes the NYT-style grid rules as checkable
predicates**. `ExetAnalysis.isConnected` (`exet/exet-analysis.js:99-154`) flood-fills the white cells,
respecting bars, and compares the reached count with the total. `unchequeredOK`
(`exet/exet-analysis.js:386-391`) requires every white cell to be crossed twice and, when
`checkSpanLen` is set, no run shorter than `minSpan = 3` (`exet/exet-analysis.js:417-432`). The
chequered (British) counterpart uses 4 (`exet/exet-analysis.js:306-346`), and automatic block placement
respects the same floor (`exet/exet.js:5156-5157`).

### R2 — Entry/slot structure

**Exolve.** An entry is a `clue` object (`exolve/exolve-m.js:3487-3507`) holding `index`, `dir`,
`label`, **its own `cells` array**, the clue text, enumeration data, `solution` and a `reversed` flag.
Enumeration runs in two stages: `markClueStartsUsingGrid` (`exolve/exolve-m.js:3585-3619`) first
records on each cell the cell list of the light beginning there (`startsAcrossClue`,
`startsDownClue`, `startsZ3dClue`), then a numbering scan creates the clue objects
(`exolve/exolve-m.js:3639-3671`).

**Identity is `dir + label`** — `A1`, `D12` — which is a *renumbering-sensitive* key, exactly like
Phil's and crosshatch's positional keys. What differs is what exet does about it (below).

**Crossings are stored on the cell**: `setCellLightMemberships`
(`exolve/exolve-m.js:3559-3574`) writes `acrossClueLabel` / `downClueLabel` / `z3dClueLabel` onto each
cell of a light, and additionally installs `succA`/`predA`-style links to the neighbouring cell along
that light. Finding the crossing entry at a cell is therefore a field read, not a search — the
opposite of crosshatch.

**exet's contribution is the only stable-identity mechanism in the whole set.**
`ExetFillState.killInvalidatedClues` (`exet/exet-autofill.js:266-303`) builds a throwaway Exolve
puzzle from the edited grid, indexes its clues by `JSON.stringify(clue.cells)`
(`exet/exet-autofill.js:275-277`), and then matches each *old* clue to a new one by that key, trying
the reversed cell list as well (`:288-299`). Clue text, annotation, placeholder, reversal and
parent/child links are carried over onto the new index (`:340-362`); linked clue groups are relocated
only if every member relocates (`:305-333`); and a non-draft clue that fails to relocate is logged as
deleted (`:334-339`). The caller (`exet/exet.js:5499-5520`) extends the same remap to ninas, colours
and per-entry regular expressions. **Entry identity is thus geometric, not positional: an entry keeps
its clue when renumbering moves its label.**

exet also maintains a **parallel state object**. `ExetFillState` (`exet/exet-autofill.js:164-215`)
shallow-copies every cell and clue, deleting any property that is a DOM `Node`, and adds `cChoices`
per cell and `lChoices`/`lRejects` per clue. The analysis therefore never mutates the live grid.

### R3 — Letter ownership

**No per-cell provenance for user-vs-suggested.** `handleGridInput` (`exet/exet.js:5400-5418`) rewrites
each cell's `solution` from whatever `currLetter` currently shows, on every edit — the two are kept
identical, so there is nothing to distinguish a typed letter from a clicked-in candidate. Placing a
candidate (`fillLight`, `exet/exet.js:7167-7248`) writes its letters cell by cell into the shared grid
(`:7223-7228`) and updates the clue's enumeration; crossing entries are simply re-derived afterwards
by `setClueSolution`.

**Removal, however, has the most deliberate letter-ownership policy in the set** — and it is
Exolve's. `clearCurr` (`exolve/exolve-m.js:8854-8950`) partitions the active cells into
`fullCrossers` and `others` (`:8897-8935`): a cell whose crossing entry is *already complete* goes
into `fullCrossers`. Only `others` are cleared (`:8936-8938`); the shared letters are cleared **only
if there is nothing else to clear**, i.e. on a second press (`:8939-8943`). So removing an entry
deliberately leaves intact the letters that a finished crossing entry depends on, and requires an
explicit second action to take them.

`prefill` is the one genuine per-cell ownership flag: prefilled cells are skipped outright by the
clear loop (`exolve/exolve-m.js:8903-8905`). exet lets the constructor set it from the keyboard on any
filled cell (`exet/exet.js:5340-5342`), and temporarily marks nina cells prefilled so they survive a
clear (`exet/exet.js:6078-6092`).

### R4 — Word lookup

**A sparse hash of partially-specified patterns with a generalisation walk** — structurally unlike the
other four.

The shipped index (S8) maps a key string of letters and `?`s to a **sorted array of lexicon indices**.
It is deliberately incomplete: `lufz-en-lexicon.js` holds 1,009 keys, of which 65 fix no letter, 770
fix one, 168 fix two and 6 fix three, over 283,721 lexicon entries and 2,256,498 total postings.
`getLexChoices` (`exet/exet-lexicon.js:454-525`) builds the key, then walks
(`exet/exet-lexicon.js:496-504`) `while (!this.index[gkey])` calling `generalizeKey`
(`exet/exet-lexicon.js:353-364`), which **turns the last specified letter into a `?`**, until a stored
key is found. It then filters the posting list with `keyMatchesPhrase`. The index is a *seek
accelerator*, not a complete map: a pattern like `?A?T` reaches the stored `?A??` and pays a linear
filter over its ~1,700-median-size posting list.

**Scores are optional and index position is the real rank.** The lexicon array is ordered by
popularity, so the posting lists are index-ordered and a popularity cutoff is the bound
`if (idx >= indexLimit) break` (`exet/exet-lexicon.js:505-521`) — an O(1) truncation.
`ExetFillState.setScore` (`exet/exet-autofill.js:455-467`) scores a fill by
`(startLen - pindex) / startLen`, i.e. rank alone. A `scores` array is used only if the lexicon has
one (`exet/exet-lexicon.js:122-149`), in which case it must be sorted so a minimum score can be
binary-searched to an index cutoff. **The two bundled English lists differ here:** Lufz has no
`scores` key (S8), so its score UI is inactive; the Nediger list carries 348,312 scores, monotone
non-increasing from 100.999978 to 25.0 (S9).

What the constructor sees per candidate (`exet/exet.js:7482-7501`) is its rank in the word list, its
score if present, and its stem. Two lists are rendered side by side — surviving candidates and
**rejected** ones — both clickable and both capped at `shownLightChoices`
(`exet/exet.js:7503-7567`). Preferred fills ("preflex") are appended to the lexicon array and indexed
by length so they are offered ahead of the ranked list (`exet/exet.js:7296-7323`).

Ranking is **not** crossing-aware in the scoring sense: the crossing information enters as *filtering*
(§R5 removes non-viable candidates) rather than as a score term. A secondary re-sort by enumeration
punctuation match is applied when the clue declares one (`exet/exet.js:7503-7529`).

### R5 — "Where can this word go" / "is this region fillable"

**"Where can this word go" is not present.** What exet has instead is the most developed *live
constraint analysis* of the five, running continuously on a timer.

`refineLightChoices` (`exet/exet.js:6556-6666`) is the grid sweep. For every unfilled entry it drops
candidates that disagree with any of its cells' current `cChoices` sets (`:6598-6624`), records the
rejects (`noteNonViableChoice`, `exet/exet.js:6866-6876`, capped at 1000), then intersects the letters
the survivors can still place into each cell (`:6626-6638`). An entry whose surviving set is *forced* —
every cell down to one letter — has its candidates added to `dontReuse` so no other entry claims them
(`:6639-6645`). A cell left with no letters sets `fillState.viable = false` (`exet/exet.js:6652-6663`).

That produces two constructor-visible outputs. Per cell, `viability`
(`exet/exet.js:7096-7099`) is `1 + log2(n)` saturating at 5, rendered by `updateViablots`
(`exet/exet.js:6672-6725`) as a dot whose radius grows as the cell tightens, magenta when dead and red
when merely constrained, plus a grey forced letter drawn in place when only one remains
(`:6694-6717`). Per entry, `findConstrainedCluesSorted` (`exet/exet.js:6982-7007`) ranks unfilled
entries by fewest surviving candidates, and `jumpToMostConstrained` (`exet/exet.js:7015-7038`) exposes
that ranking as a keyboard jump that cycles through the ranking on repeated presses. This is the
closest thing in any of the five to "which entry is the problem".

The deeper probe is `findDeadendsByClue` (`exet/exet.js:6879-6929`): take the next few candidates of
the most constrained entry, tentatively pin the entry to each on a **copy** of the fill state
(`:6912-6918`), and ask `someClueTurnsNonViable` (`exet/exet.js:6777-6864`) whether any *other* entry
loses all of its candidates. Candidates that do are moved to the reject list.

The two phases alternate on a `setTimeout` chain (`findAllDeadendFills`, `exet/exet.js:7046-7094`):
grid sweep until it stops removing anything, then the clue sweep, then back to the grid sweep if the
clue sweep changed anything. The analysis is therefore incremental and interruptible, not a blocking
computation. `acceptAll` (`exet/exet.js:6727-6773`) is the converse action: commit every cell whose
letter set has collapsed to one and every entry with a single candidate.

There is **no region abstraction** — no analogue of crosshatch's `Section` or Phil's BFS radius.
exet's unit of analysis is the whole grid, made affordable by incrementality and by the
`sweepMaxChoices` limits rather than by spatial decomposition.

### R6 — Serialisation

The widest format coverage of the five, and the only one with persistence.

The **native format is Exolve text**, regenerated from the live puzzle by `getExolve`
(`exet/exet.js:6440-6517`) — a line-oriented section format (`exolve-width`, `exolve-grid`,
`exolve-across`, …) that carries the grid, both clue lists, colours, ninas, reversals and a
`exolve-maker` provenance block naming the Exet version, the lexicon id and a timestamp
(`:6442-6446`). `getHTML` (`exet/exet.js:6519-6522`) wraps it in the surrounding page.

Import (`exetLoadFile`, `exet/exet.js:7913-7939`) tries Exolve text first by searching for
`exolve-begin`, then `.puz` via `exolveFromPuz`, then `.ipuz` via `exolveFromIpuz` — each converter
returning Exolve text, so **all three formats converge on one internal representation**. Export
mirrors this: `.puz` and `.ipuz` through `exolveToPuz` / `exolveToIpuz`
(`exet/exet.js:3611-3631`), plus SVG, print and clipboard paths (`exet/exet.js:3565-3610`).

Persistence is a **revision history in `localStorage`**. `saveRev`
(`exet/exet-storage.js:608-676`) keeps, per puzzle id, a list of revisions each holding the entire
Exolve text plus the session settings — preferred/avoided fill hashes, proper-noun and stem-duplicate
flags, minimum popularity and score, lexicon id, per-entry regexps, and the cursor position
(`:654-674`) — and skips the write entirely if nothing changed (`:633-652`). Reloading a file restores
those settings from the last revision (`exet/exet.js:7962-7984`).

> **Observed by reading; consequence not executed.** The file header states "Code related to managing
> localStorage and IndexedDB for Exet" (`exet/exet-storage.js:10-12`), but no `indexedDB` reference
> exists in any exet script. Not executed.

---

## 5. Qxw [S7]

13,454 lines of C, GPL v2 only. It is the only tool in the set whose header file documents its own
data model in prose, and the only one that generalises past rectangular block grids. **Terminology
warning:** in this section Qxw's own words are used, mapped as `square`→cell, `entry`→cell-slot,
`word`→the task's entry.

The author's glossary is worth quoting because it explains the three-level structure
(`qxw-20200708/common.h:154-159`):

> A `square' is the quantum of area in the grid; one or more squares (a `merge group') form an
> `entry', which is a single enclosed white area in the grid where a letter (or group of letters)
> will appear. A `word' is a sequence of entries to be filled.

The middle level — *entry* — exists because Qxw supports merged cells and de-checked cells, so the
mapping from grid squares to letter positions is not the identity.

### R1 — Grid data structure

`struct square` (`qxw-20200708/common.h:230-246`) is a fat record: bar presence and merge flags per direction, a
flags byte (bit 0 blocked, bit 3 not part of the grid, bit 4 selected), a per-direction selection
byte, **per-direction content**, style properties, per-direction light properties, then the derived
back-pointers, violation flags, number and grid-order index.

The content field is the interesting one (`qxw-20200708/common.h:236-237`): `ctlen[MAXNDIR]` and
`ctbm[MAXNDIR][MXCT]` — a cell holds not a letter but a **string of 64-bit alphabet bitmaps**, and can
hold *different content in each direction* for de-checked cells. `ABM` is
`unsigned long long` with `ICCTOABM(x) = 1ULL << (x-1)` (`qxw-20200708/common.h:148-152`), giving up to 60
alphabet codes plus a dash in one word. Bit-counting and single-bit tests are one-liners
(`qxw-20200708/qxw.c:124-125`).

The grid itself is **one statically-sized array**, `struct square gsq[MXSZ][MXSZ]`
(`qxw-20200708/common.h:258`) with `MXSZ` = 63 (`qxw-20200708/common.h:62`), regardless of the puzzle's actual size. There are
13 grid types (`qxw-20200708/common.h:60`) with up to 3 directions (`qxw-20200708/common.h:61`) — square, two hexagonal
orientations, and two circular variants (`qxw-20200708/qxw.c:64`).

Symmetry is **three independent settings** (`qxw-20200708/qxw.c:66`): `symmr` rotational order, `symmm` mirror
axes, `symmd` translational up-down/left-right. Which values are legal depends on the grid shape —
`symmrmask` (`qxw-20200708/qxw.c:653-673`) returns orders {1,2,4} for square grids and *every divisor of the width*
for circular ones. Every grid edit is applied through the orbit by `symmdo`
(`qxw-20200708/qxw.c:1071-1114`), which composes rotation, then mirrors (`symmdo1`/`symmdo2`, `qxw-20200708/qxw.c:1008-1038`),
then the translational flags (`symmdo3`/`symmdo4`, `qxw-20200708/qxw.c:998-1005`), and finally the bounds check
(`symmdo5`, `qxw-20200708/qxw.c:983-985`). Hexagonal rotation goes through a six-fold coordinate transform
(`rot6`, `qxw-20200708/qxw.c:1055-1067`).

There is **no minimum-entry-length rule**. Qxw's structural bounds are instead on the *proportion of
crossed cells* in an entry: `mincheck` and `maxcheck` (`qxw-20200708/common.h:343-344`), applied in `bldstructs`
(`qxw-20200708/qxw.c:963-964`).

### R2 — Entry/slot structure

`struct word` (`qxw-20200708/common.h:202-219`) holds the number of cell-slots, the length of its candidate
strings, its start position and direction, a pointer to its **feasible candidate list** and that
list's length, a commit depth, the array of pointers to its cell-slots, and its light properties.
`struct entry` (`qxw-20200708/common.h:220-229`) — the cell-slot — holds its feasible-letter bitmap, a display copy
of it, its grid position, `checking` (the count of entries crossing it), a **per-letter score vector**
`double score[MAXICC+1]`, and `crux`, a priority.

Enumeration is a full rebuild: `bldstructs` (`qxw-20200708/qxw.c:886-979`) counts, allocates, assigns cell-slots to
merge-representative cells (`:911-935`), then walks every direction and every start-of-light calling
`addwordfd` (`qxw-20200708/qxw.c:742-779`), then adds virtual lights (`:943`). Identity is the array index into
`words[]`, valid only until the next rebuild — the same "no stable identity" position as Phil,
crosshatch and composer, and unlike exet.

**Crossings are stored in both directions.** The cell keeps `ents[MAXNDIR][MXCT]` and
`w[MAXNDIR][MXMUX]` (`qxw-20200708/common.h:241-242`); the word keeps `e[MXFL]`, the array of cell-slot pointers
(`qxw-20200708/common.h:214`), written in `addwordfd` (`qxw-20200708/qxw.c:764-771`). The crossing count per cell-slot is then a
one-pass tally (`qxw-20200708/qxw.c:945-948`).

Qxw is also the only tool with **virtual lights** — `struct vl` (`qxw-20200708/common.h:247-253`), arbitrary
user-defined cell sequences treated as entries alongside the geometric ones, with their own
properties and their own `word` record.

### R3 — Letter ownership

Qxw's answer is structural rather than flag-based.

There is **no per-cell provenance flag**, because a letter is not owned by an entry: it is a
constraint attached to the cell's bitmap, shared by every entry through that cell by construction. Writing a letter sets the bitmap to a single bit; passing `-1` restores the full normal
set (`seteicc`, `qxw-20200708/qxw.c:611-621`). `clrcont` (`qxw-20200708/qxw.c:623-627`) resets every direction's bitmaps to
`ABM_NRM`. Removing an entry is therefore not an operation the data model has — the constructor clears
cells, and any entry through them re-widens automatically.

What Qxw separates instead is **user constraint from machine deduction**, by putting them in different
structures. The grid's `ctbm` holds what the constructor asserted; the solver's deductions live in
`entries[].flbm`, with `flbmh` a copy "provided by solver to running display"
(`qxw-20200708/common.h:221-222`). The display shows deductions without them becoming content. The one path by
which a deduction becomes user content is explicit and manual: `m_accept`
(`qxw-20200708/gui.c:668-691`) walks the grid and copies every *single-bit* deduction into the cell bitmap
(`qxw-20200708/gui.c:683-687`), with a comment noting the author considered dropping the single-bit test and
decided it would be confusing.

**Per-entry state does exist, and it is derived rather than declared.** `struct word.fe` — the
"fully-entered flag" (`qxw-20200708/common.h:217`) — is recomputed at the start of every filler run:
an entry is fully entered when every one of its cells already has exactly one feasible letter
(`qxw-20200708/filler.c:1044-1047`). It is inferred from grid content, not from a record of who typed
what. What it buys is the important part: an emptied candidate list proves the state impossible
**only for an entry the constructor did not type in full** (`qxw-20200708/filler.c:525-525`, repeated
at `:532`), so a word present in no dictionary can stand in the grid without the analysis declaring
the grid dead. A fully-entered entry is also skipped when pushing letters back to cells
(`qxw-20200708/filler.c:556-558`), skipped when scoring (`qxw-20200708/filler.c:684-685`), and has its
feasible-character display suppressed (`qxw-20200708/gui.c:3242-3250`). This is the only mechanism in
the five tools by which an out-of-list entry is tolerated by the analysis rather than flagged;
crosshatch's nearest analogue, the "iffy" entry (`crosshatch/src/models/EntryCandidate.ts:7-8`), is a
*generated* out-of-list string rather than a constructor-typed one.

Reversibility is handled at a different granularity from everything else in the set: undo is a
circular buffer of **fifty complete snapshots** of the 63×63 square array
(`qxw-20200708/qxw.c:1305-1306`, `UNDOS` = 50 at `qxw-20200708/common.h:82`), plus parallel snapshots of the grid type,
dimensions, defaults, virtual lights and treatment settings (`qxw-20200708/qxw.c:1306-1319`).

### R4 — Word lookup

**Two-level: a linear scan to build, then bitmask intersection to narrow.**

The dictionary is two structures. `struct answer` (`qxw-20200708/common.h:266-276`) is a word as found in one or
more dictionaries — hash link, a **bitmask of which of the 9 dictionaries** contain it
(`qxw-20200708/dicts.h:31`), a score, its citation form, and its canonical form. `struct light`
(`qxw-20200708/common.h:278-288`) is a concrete grid-fillable string derived from an answer by an entry method or a
treatment, carrying its own letter bitmap `lbm` and a letter histogram `hist[MAXICC+1]`.

**Scores are a log scale.** A dictionary line is `word score`, the trailing number after a space,
defaulting to 0.0 and clamped to ±10 (`qxw-20200708/dicts.c:775-787`). It is stored as **one byte**,
`floor(f*10.0 + 128.5)` (`qxw-20200708/dicts.c:538`), i.e. offset-binary at one-decimal resolution — the file
format comment at `qxw-20200708/dicts.c:439` records the 28..228 range. On load it is decoded as
`pow(10.0, (byte - 128) / 10.0)` (`qxw-20200708/dicts.c:888`), so **the file's score is a decibel-like exponent and
the working score is a multiplicative weight**, 1.0 for an unscored word. Duplicates across
dictionaries are merged and their scores **multiplied** (`qxw-20200708/dicts.c:906-913`), then clamped to ±1e10
(`qxw-20200708/dicts.c:926-929`).

The initial candidate list for an entry is built by `getinitflist`
(`qxw-20200708/treatment.c:591-664`) as a **linear scan over every answer in the dictionary**
(`qxw-20200708/treatment.c:640-648`), filtered by dictionary mask and ban flag. Length is the first test inside
that scan (`qxw-20200708/treatment.c:243-262`, `if(l != lightlength) return 0`), and each allowed entry method then
contributes its own string — so reversals, cyclic shifts and reversed cyclic shifts become *separate
candidates* of the same answer (`qxw-20200708/treatment.c:255-282`). There is **no trie, no DAWG and no inverted
index**; the cost is paid once per entry per rebuild, and only for the entries actually needed
(`qxw-20200708/filler.c:882`).

Narrowing thereafter is `listisect` (`qxw-20200708/filler.c:394-398`): walk the surviving candidate list, keep the
entries whose character at position `wp` is in the cell's bitmap, compact in place. This is the
bitmask counterpart of crosshatch's `filter`: one 64-bit test per candidate per position, with no
allocation.

The list the constructor sees is the filler's surviving list for the entry under the cursor, copied by
`mkfeas` (`qxw-20200708/qxw.c:2402-2420`) and **sorted by dictionary score** (`cmpscores`, `qxw-20200708/qxw.c:2390-2399`). So
ranking is score-only at the display level — but the list has already been filtered to viability by
the propagation of §R5, which is a stronger form of crossing-awareness than a score term.

### R5 — "Where can this word go" / "is this region fillable"

**"Where can this word go" is not present.** "Is this region fillable" is answered as *propagation to
a fixed point*, exposed live.

The two halves are `settleents` (`qxw-20200708/filler.c:422-541`) and `settlewds` (`qxw-20200708/filler.c:543-588`).
`settleents` walks every entry whose cells changed and intersects its candidate list against each
cell's bitmap; **an emptied list on an entry the user did not fully type proves the state
impossible** (`qxw-20200708/filler.c:525`, `if(l==0&&!w->fe) return -2`). `settlewds` runs the reverse: for each
updated entry it ORs together the letters its surviving candidates can place at each cell
(`qxw-20200708/filler.c:568`) and intersects that union into the cell's bitmap, flagging the cell if it shrank
(`qxw-20200708/filler.c:576-583`). `search` alternates the two to a fixed point before any guess
(`qxw-20200708/filler.c:929-941`, labelled `"unit propagation"`), and backtracks immediately on a proof of
impossibility.

The scoring layer sits on top. `mkscores` (`qxw-20200708/filler.c:671-729`) initialises every cell-letter score to
1.0, then for each entry sums each surviving candidate's dictionary score into the letter it places at
each position (`qxw-20200708/filler.c:701-705`) and **multiplies** that into the cell's per-letter score
(`qxw-20200708/filler.c:722`) — so a cell's score for a letter is the product, over the entries through it, of the
total dictionary weight of the candidates that would place that letter there. `crux`
(`qxw-20200708/filler.c:724-727`) is the largest such score over all letters still possible at that cell.

`findcritent` (`qxw-20200708/filler.c:400-420`) then chooses where to branch: consider the **most-crossed** cells
first (highest `checking`), and among those take the one with the **lowest** `crux`. Guessing order at
that cell is `getposs` (`qxw-20200708/filler.c:733-753`), letters in descending score with an optional randomising
swap.

What makes this a constructor-facing analysis rather than a solver internal is `ifamode` — interactive
fill assistance, with three settings: off, current entry only, entire grid (`qxw-20200708/gui.c:3501-3503`). In
that mode the search **stops after the first fixed point** (`qxw-20200708/filler.c:943`) and never guesses, so what
the constructor sees is pure propagation. The output for the cursor cell is the list of letters still
possible, or the statement that none are (`qxw-20200708/gui.c:3244-3247`).

Separately, `bldstructs` computes **structural diagnostics on every rebuild** (`qxw-20200708/qxw.c:950-971`):
double and triple unchecked runs, entries below `mincheck` or above `maxcheck` percent crossed, plus
length histograms and per-length minimum/maximum crossing counts. These are stored per cell per
direction as `vflags` (`qxw-20200708/common.h:243`) so the grid can be marked up, and aggregated into a statistics
window.

### R6 — Serialisation

**Three read formats, one write format, six export formats.**

The native format (`a_save`, `qxw-20200708/qxw.c:2049-2103`) is versioned line-oriented text: a magic line
`#QXW2v5 http://www.quinapalus.com` (`qxw-20200708/qxw.c:2057`), then grid parameters including all three symmetry
settings (`:2058`), title, author, one `ALP` record per alphabet character with its equivalents
(`:2061-2065`), the global light and square property defaults, the treatment configuration, the nine
dictionary filenames and their two PCRE filters each (`:2075-2077`), then **one record per square for
each of flags, style, corner marks, per-direction light properties and contents**
(`:2078-2094`), then virtual lights, then `END`. It is a complete dump of the editable state; nothing
derived is written.

`a_load` (`qxw-20200708/qxw.c:1669-2046`) branches three ways on the first line: `#QXW2` for the native format,
tolerating a **newer** version with a warning rather than a refusal (`qxw-20200708/qxw.c:1688-1695`, `:2034`);
a Sympathy file, detected by `"ympath"` at offset 2 and parsed on a best-effort basis — the comment
says "necessarily incomplete as we don't have documentation" (`qxw-20200708/qxw.c:1909-1912`); and the pre-QXW2
legacy layout, whose symmetry codes are remapped on load (`qxw-20200708/qxw.c:1995-2006`). A fourth, narrower path
imports virtual-light definitions as coordinate lists (`a_importvls`, `qxw-20200708/qxw.c:2105-2147`).

Export is one-way and covers both graphics and text. `a_exportg`
(`qxw-20200708/draw.c:1377-1415`) drives Cairo to **EPS** (PostScript level 2 with the EPS flag), **SVG 1.1**, or
**PNG**. `panswers` (`qxw-20200708/draw.c:1106-1114`) has six text modes: plain text, block HTML with enumeration,
block HTML, table HTML, and two Crossword Compiler XML streams. `a_exportccwxml`
(`qxw-20200708/draw.c:1514-1536`) writes the Crossword Compiler XML document, and is explicit about what it cannot
represent — it refuses non-rectangular grids, and refuses merged, de-checked or multi-character cells
(`qxw-20200708/draw.c:1517-1530`). **Neither `.puz` nor `.ipuz` is read or written.**

---

## 6. Comparison

### 6.1 R1–R6 across the five tools

| | **crossword-composer** [S6] | **Phil** [S1, S2] | **CrossHatch** [S5] | **exet / Exolve** [S3, S4] | **Qxw** [S7] |
|---|---|---|---|---|---|
| **R1 Grid** | Rust core: no grid, only `slots`+`words`+`slot_to_words` (`crossword-composer/src/grid.rs:2-6`). UI: `Cell[][]` (`crossword-composer/ui/src/crossword.js:1-16`) | Array of row **strings**; black = `'.'` (`phil/cross.js:56-71`, `:30-35`). Solver re-parses into its own `Grid` (`phil/third_party/glucose-3.0/simp/Main.cc:161-177`) | `GridSquare[][]` with content, provenance and candidate letters on the cell (`crosshatch/src/models/GridState.ts:4-11`, `crosshatch/src/models/GridSquare.ts:4-15`) | Exolve `gridCell` objects incl. DOM handles (`exolve/exolve-m.js:3165-3200`), 2-D array (`:3226-3228`) | `struct square gsq[63][63]`, per-direction bitmap strings (`qxw-20200708/common.h:230-246`, `:258`) |
| **Black square** | `filled: bool` | `'.'` character in the row string | `SquareType.Black` enum (`crosshatch/src/models/SquareType.ts:1-5`) | `isLight === false` (`exolve/exolve-m.js:3179-3183`) | `fl` bit 0; bit 3 = cut out of grid (`qxw-20200708/common.h:234`) |
| **Sizes / shapes** | square 3–16 only (`crossword-composer/ui/src/Crossword.svelte:5-6`) | any rows×cols, default 15 (`phil/cross.js:35`); import 15×15 only (`phil/files.js:302-307`) | independent w×h (`crosshatch/src/lib/grid.ts:171-199`) | any; also 3-D and barred grids (`exolve/exolve-m.js:3276-3298`) | 13 grid types incl. hex and circular, ≤63×63 (`qxw-20200708/common.h:60-62`) |
| **Symmetry** | 180° hard-wired into `toggle` (`crossword-composer/ui/src/crossword.js:106-112`) | 180° only, global on/off (`phil/cross.js:345-346`, `:704-712`) | **7-value enum** (rot 180/90, 2 mirrors, 2 diagonals) (`crosshatch/src/models/SymmetryType.ts:1-9`) | 180° only, `asymOK` disables (`exet/exet.js:5346-5354`) | **rotation order + mirrors + translation**, legality by grid shape (`qxw-20200708/qxw.c:66`, `:653-673`, `:1071-1114`) |
| **NYT rule checks** | none | none | none | `isConnected` + `unchequeredOK` (min length 3, all cells doubly crossed) (`exet/exet-analysis.js:99-154`, `:417-432`) | crossing-percentage bounds, unch runs (`qxw-20200708/qxw.c:950-971`) — **not** a length rule |
| **R2 Entry object** | list of cell indices (`crossword-composer/src/grid.rs:4`) | **none** — recomputed per keystroke (`phil/cross.js:535-566`) / `Word` in C++ (`phil/third_party/glucose-3.0/simp/Main.cc:147-152`) | `GridWord` = start/end/dir; cells derived (`crosshatch/src/models/GridWord.ts:3-8`) | Exolve `clue` **owns its cell list** (`exolve/exolve-m.js:3487-3507`) | `struct word` owns cell-slot pointers (`qxw-20200708/common.h:202-219`) |
| **R2 Identity** | array index, rebuilt per toggle | `[row,col,dir]` string; **clue deleted** when start moves (`phil/cross.js:554-563`) | `[row,col,A\|D]` string; clue map **not remapped** on edit (`crosshatch/src/lib/util.ts:151-153`, `crosshatch/src/components/Grid/Grid.tsx:125-131`) | `dir+label`, but **remapped by cell-list match** on every edit (`exet/exet-autofill.js:266-303`) | array index, rebuilt by `bldstructs` (`qxw-20200708/qxw.c:886-979`) |
| **R2 Crossings** | **stored**, cell→entries (`crossword-composer/src/grid.rs:13-23`) | JS: **absent**. C++: **stored**, `across[]`/`down[]` (`phil/third_party/glucose-3.0/simp/Main.cc:297-299`) | **recomputed** by linear scan over all entries (`crosshatch/src/lib/util.ts:78-91`) | **stored on the cell** as labels + succ/pred links (`exolve/exolve-m.js:3559-3574`) | **stored both ways** + crossing count (`qxw-20200708/common.h:241-242`, `qxw-20200708/qxw.c:945-948`) |
| **R3 Provenance** | **not present** | **not present**; solver-forced letters in a parallel array, discarded per run (`phil/cross.js:119-124`, `:728`) | **per cell**, 6-value `ContentType` (`crosshatch/src/models/ContentType.ts:1-8`) | user-vs-suggested **not present** (`exet/exet.js:5400-5418`); `prefill` is the one per-cell flag | no per-cell flag — user constraint in `ctbm`, deduction in `flbm` (`qxw-20200708/common.h:221-222`, `:236-237`); **per-entry `fe`** derived per run (`qxw-20200708/filler.c:1044-1047`) |
| **R3 On removal** | n/a (entries never individually removed) | overwritten silently (`phil/wordlist.js:136-153`) | per-cell demotion by crossing provenance; `User` cells untouched (`crosshatch/src/lib/grid.ts:271-285`) | **two-stage**: cells with a *complete* crossing entry are spared on the first clear (`exolve/exolve-m.js:8897-8943`) | n/a — clearing a cell re-widens its bitmap (`qxw-20200708/qxw.c:623-627`) |
| **R4 Structure** | length buckets + one permuted index **per solving step** (`crossword-composer/src/dictionary.rs:5-7`, `crossword-composer/src/index.rs:8-13`) | length buckets + **regex linear scan** (`phil/wordlist.js:16-20`, `:94-110`) | **precomputed inverted index**, 1-pos and 2-pos buckets (`crosshatch/src/lib/wordList.ts:92-138`) | **sparse hash of partial patterns** + generalisation walk (`exet/exet-lexicon.js:454-525`, `:496-504`) | **linear scan over all answers**, then bitmask intersection (`qxw-20200708/treatment.c:640-648`, `qxw-20200708/filler.c:394-398`) |
| **R4 Scores** | **none** (S11) | **none** (S10); score UI commented out (`phil/wordlist.js:122-123`) | read then **discarded** → 3 classes → 12/9/3/1 (`crosshatch/src/lib/wordList.ts:34-57`, `crosshatch/src/lib/fill.ts:355-364`) | **rank = index**; optional sorted `scores` array (S8 has none, S9 has 348,312) (`exet/exet-lexicon.js:122-149`) | `10^((byte-128)/10)`, multiplicative, duplicates multiply (`qxw-20200708/dicts.c:538`, `:888`, `:906-913`) |
| **R4 Ranking** | insertion order (`crossword-composer/src/solver.rs:88-93`) | word-list (alphabetical) order (`phil/wordlist.js:112-134`) | **crossing-aware score**: total + worst cross support × quality (`crosshatch/src/lib/entryCandidates.ts:410-416`) | score/rank order, **crossing enters as filtering** not scoring (`exet/exet.js:7503-7567`) | score order over an **already-propagated** list (`qxw-20200708/qxw.c:2390-2420`) |
| **R5 "where can word go"** | **not present** | **not present** | **not present** | **not present** | **not present** |
| **R5 Region fillability** | order heuristic only (`crossword-composer/src/solver.rs:41-47`) | **BFS radius from filled cells**; expanding-radius SAT; whole-grid sat/unsat class (`phil/third_party/glucose-3.0/simp/Main.cc:227-253`, `:372-374`, `phil/cross.js:759-776`) | **`Section` regions** from open squares, each with scored complete fills (`crosshatch/src/lib/section.ts:83-129`, `:326-338`) | **whole-grid incremental propagation**, per-cell viability dots + most-constrained-entry ranking (`exet/exet.js:6556-6666`, `:6982-7038`) | **propagation to fixed point**; `crux` priority; interactive assist stops before guessing (`qxw-20200708/filler.c:422-588`, `:943`) |
| **R5 over-constrained — *entry* level** | not present | not present | not present | **entries ranked by fewest candidates + keyboard jump** (`exet/exet.js:6982-7038`) | not present |
| **R5 over-constrained — *cell* level** | not present | BFS distance per cell (`phil/third_party/glucose-3.0/simp/Main.cc:264-267`) | empty `viableLetters` (`crosshatch/src/lib/util.ts:199-202`) | viability dot per cell (`exet/exet.js:6672-6725`) | most-crossed, lowest-`crux` cell (`qxw-20200708/filler.c:400-420`) |
| **R6 Reads** | **nothing** | `.puz`, JSON/`.xw`/`.txt` (`phil/files.js:254-285`) | `.puz` only (`crosshatch/src/components/Menu/Menu.tsx:52`) | Exolve text, `.puz`, `.ipuz` (`exet/exet.js:7913-7939`) | `#QXW2`, Sympathy, pre-QXW2 legacy (`qxw-20200708/qxw.c:1688-1695`, `:1909-1912`, `:1995-1998`) |
| **R6 Writes** | **nothing** | `.puz`, JSON, PDF (`phil/files.js:352-373`, `:409-432`) | `.puz` (`crosshatch/src/lib/puzFiles.ts:140-263`) | Exolve text/HTML, `.puz`, `.ipuz`, SVG (`exet/exet.js:6440-6522`, `:3611-3631`) | `#QXW2`; exports EPS/SVG/PNG, 4 text/HTML modes, Crossword Compiler XML (`qxw-20200708/qxw.c:2049-2103`, `qxw-20200708/draw.c:1377-1415`, `:1106-1114`, `:1514-1536`) |
| **R6 Persistence** | none | none | none | **`localStorage` revision history** with full session settings (`exet/exet-storage.js:608-676`) | undo = 50 full grid snapshots (`qxw-20200708/qxw.c:1305-1306`); no autosave |

### 6.2 Axes relevant to a Rust/WASM port

The task notes a planned port of the core to Rust/WebAssembly, so these four rows extract what the
five codebases imply about memory layout and serialisability. **These are observations about the
sources, not recommendations.**

| Axis | composer | Phil | CrossHatch | exet / Exolve | Qxw |
|---|---|---|---|---|---|
| **Per-cell candidate-letter set** | not present | not on the cell — SAT-derived `forced[][]` string produced externally (`phil/cross.js:455-460`) | `viableLetters?: string[]`, with a `boolean[26]` scratch matrix (`crosshatch/src/models/GridSquare.ts:14`, `crosshatch/src/lib/grid.ts:131-139`) | `cChoices` as an **object used as a set**, `{letter: true}` (`exet/exet-autofill.js:369-387`), plus a float `viability` | **one `u64` bitmap**, `ABM` (`qxw-20200708/common.h:148-152`) — the only fixed-width, allocation-free representation in the set |
| **Entry↔cell linkage** | `Vec<Vec<usize>>` both ways (`crossword-composer/src/grid.rs:4-5`) | `vec<int> across`/`down`, one int per cell (`phil/third_party/glucose-3.0/simp/Main.cc:297-299`) | `Map<string, GridWord>` keyed by a formatted tuple; reverse lookup is an **O(entries) scan** (`crosshatch/src/lib/util.ts:78-91`) | label strings on the cell + per-cell succ/pred link objects (`exolve/exolve-m.js:3559-3574`) | raw pointers both ways: `ents[][]`, `w[][]` on the cell, `e[]` on the word (`qxw-20200708/common.h:214`, `:241-242`) |
| **Serialisability of working state** | two flat `Vec`s; crosses the wasm boundary as JS arrays of numbers in, one-char strings out (`crossword-composer/src/lib.rs:32-53`) | grid is a string array; solver state is opaque C++ inside wasm | `deepClone` of the **whole `GridState` per search node** (`crosshatch/src/lib/fill.ts:265-289`, `crosshatch/src/lib/util.ts:25-51`) | must **strip `instanceof Node` properties** to copy at all — cells and clues carry DOM handles (`exet/exet-autofill.js:175-179`, `:197-201`) | `struct square` is POD-ish and snapshot-copied wholesale, 50 deep (`qxw-20200708/qxw.c:1305-1306`) |
| **Entry identity across black-square edits** | regenerated; nothing attached to survive (`crossword-composer/ui/src/crossword.js:36-37`) | clue **deleted** when its start cell stops starting an entry (`phil/cross.js:554-563`) | map rebuilt; clue map keyed by old positional keys is **not** remapped (`crosshatch/src/components/Grid/Grid.tsx:125-131`) | **rematched by `JSON.stringify(cells)`**, forwards or reversed; clue text, links, ninas, colours and regexps all carried over (`exet/exet-autofill.js:274-303`, `exet/exet.js:5499-5520`) | `words[]` rebuilt wholesale; nothing is attached to an entry to survive (`qxw-20200708/qxw.c:886-979`) |

Two patterns are worth stating plainly because they cut across the table.

**Four of five store the crossing; one recomputes it.** Composer, Phil's C++, Exolve and
Qxw all keep a cell→entry map and pay a rebuild on structural edits. CrossHatch alone recomputes,
and it pays for that inside its candidate-scoring inner loop, where `getAllCrosses`
(`crosshatch/src/lib/fill.ts:311-317`) invokes an all-entries scan once per cell.

**Entry identity is positional in four of five; only exet remaps it.**
Phil, CrossHatch, Qxw and composer all key or index entries by position and rebuild on edit; the
clue-loss consequence is explicit in Phil's code (`phil/cross.js:554-563`) and implicit in CrossHatch's
(no remap exists). exet's `killInvalidatedClues` (`exet/exet-autofill.js:266-303`) is the one mechanism in
the set that makes an entry's identity **geometric** — the serialised cell list — so a renumbering
does not orphan what was attached to it.

---

## 7. Defects observed by reading

Every item here was found by reading the cited lines. **None was executed, and no runtime consequence
below was tested.** They are recorded because each sits inside code this task asked about.

| # | Source | Location | Observation |
|---|---|---|---|
| D1 | [S6] | `crossword-composer/src/solver.rs:32-33`, `:63-65` | `constraints` is commented "Word index → number of constraints" and indexed by word id, but sized `vec![0; grid.slots]`. Latent while cells outnumber entries. |
| D2 | [S1] | `phil/cross.js:609-615` | `getWordIndices` bounds its scan with the constant `DEFAULT_SIZE` (15) rather than the row/column length. |
| D3 | [S1, S2] | `phil/xw_worker.js:19-23` vs `phil/cross.js:783-789`, `phil/third_party/glucose-3.0/simp/Main.cc:577-579` | `-compute-forced` is commented out of its only call site in both branches and defaults to false, while the UI still handles the `'forced'` message and renders `forced[][]` in pencil. Producing half disabled, receiving half live. |
| D4 | [S5] | `crosshatch/src/lib/grid.ts:257`, `:260` | The across and down lookups in `eraseGridSquare` pass the same `dir`, so `otherDirWord === word` and the crossing entry is never examined at `:263`. |
| D5 | [S5] | `crosshatch/src/lib/util.ts:256-261` | `letterListToLetterMatrix` writes at `charCodeAt(0)` without the `- 65` offset used by its inverse and by the reader at `crosshatch/src/lib/grid.ts:131-136`. |
| D6 | [S5] | `crosshatch/README.md:47-51` vs `crosshatch/src/lib/wordList.ts:44-46` | The README documents quality thresholds of 50 and 40 with tiers Good/Okay/Iffy; the code uses 100 and 50 with `Lively`/`Normal`/`Crosswordese`. |
| D7 | [S3] | `exet/exet-storage.js:10-12` | The file header states it manages "localStorage and IndexedDB"; no `indexedDB` reference exists in any exet script. |
| D8 | [S6] | `crossword-composer/ui/public/index.html:44-46` vs `ui/public/words.txt` | The page states the vocabulary is ~71k terms; the checked-in `words.txt` has 14,897 lines. |
| D9 | [S2] | `phil/third_party/glucose-3.0/simp/Makefile:9-16` | The wasm targets `xwsolve.js` / `xwsolve.wasm` that `phil/xw_worker.js:5-9` loads are **build products and are not in the repository** — a fresh clone cannot run autofill without an Emscripten build. |

---

## 8. Gaps

### 8.1 Negative results — features looked for and not found

These are findings, not omissions. Each was searched for across all five corpora.

- **"Where can this word go", in the sense the task means it — take one user-supplied word and rank
  the entries of a known grid it could occupy — is absent from all five tools.** The only word→grid
  paths are place-at-cursor: `phil/wordlist.js:136-153`, `crosshatch/src/lib/grid.ts:247-252`,
  `exet/exet.js:7167-7248`. Search frame: `grep -rniI` over all six clones (excluding `.git`, the
  lexicon blobs and `*.txt`) for `placement|whereCan|candidateSlot|possibleLocation|findSlots|
  slotsFor|wordFits|canPlace|placeAt|locationsFor`.
- **That search did surface one placement engine, and it is a different problem.**
  `ExolveGridInferrer` (`exolve/exolve-from-text.js:866-905`) takes a *complete* set of lights plus a
  width, height and candidate symmetry, and searches recursively for an assignment of every light to
  a start cell that yields a consistent grid (`exolve/exolve-from-text.js:1158-1175`), reporting
  progress as "placement combos" for the first ten lights
  (`exolve/exolve-from-text.js:1126-1156`). It answers "what grid could these words have come from",
  not "where in this grid could this word go", and it is **not loaded by exet** — a grep for
  `from-text` across `exet/exet.html` and every `exet/*.js` returns nothing. Recorded because the
  absence claim above is only as wide as its search frame, and this is what the frame caught.
- **Only Qxw carries per-entry state, and it is derived, not declared.** Provenance in the four
  browser tools is per cell (`crosshatch/src/models/ContentType.ts:1-8`, `exolve/exolve-m.js:3185`)
  or absent. Qxw's `word.fe` (`qxw-20200708/common.h:217`) is recomputed each filler run from whether
  every cell of the entry is already determined (`qxw-20200708/filler.c:1044-1047`), and exempts that
  entry from the dictionary constraint (`qxw-20200708/filler.c:525-525`). No repository stores a
  per-entry record of *who* placed an entry.
- **Only exet keeps entry identity stable across a black-square edit**
  (`exet/exet-autofill.js:266-303`). The other four rebuild and lose whatever was attached.
- **No repository has a trie or DAWG.** Search frame: `grep -rniI` over all six clones (same
  exclusions) for `\btrie\b|\bdawg\b|prefix.?tree|patricia|radix.?tree|suffix.?automat` — zero hits.
  The five lookup structures are: length buckets + regex scan
  (Phil), length buckets + per-step permuted index (composer), precomputed 1-/2-position inverted
  index (crosshatch), sparse partial-pattern hash with generalisation (exet), linear scan +
  bitmask intersection (Qxw).
- **Only exet encodes the NYT-style grid rules** (connectivity, all cells doubly crossed, minimum
  length 3) as checkable predicates (`exet/exet-analysis.js:99-154`, `:417-432`). Phil, crosshatch
  and composer have no connectivity check and no minimum-length rule; Qxw constrains the *proportion*
  of crossed cells instead (`qxw-20200708/qxw.c:963-964`).
- **Only exet persists anything.** A repository-wide search for `localStorage`, `sessionStorage` and
  `indexedDB` over `*.js`, `*.ts`, `*.tsx`, `*.svelte` and `*.html` returned 0 hits for Phil,
  crosshatch and composer, and 66 for exet.
- **Searched Phil, crosshatch and composer for a per-candidate score; nothing found.** Phil's is
  commented out (`phil/wordlist.js:122-123`) and its default list has no score column (S10);
  composer's dictionary has no score field at all (`crossword-composer/src/dictionary.rs:5-7`);
  crosshatch reads a score and discards it in favour of a three-way class
  (`crosshatch/src/lib/wordList.ts:34-57`).

### 8.2 Not answered by this run

- **Whether any observed defect actually manifests.** Nothing in §7 was executed. D2, D4, D5 and D8
  in particular would need a running build to confirm, and D9 says a Phil build is not available from
  a fresh clone without Emscripten.
- **The `.puz` specification itself** [S13] was not retrieved. Every `.puz` claim here is read off
  Phil's and crosshatch's implementations, which are related (`crosshatch/src/lib/puzFiles.ts:265-266`
  attributes the checksum routine to Phil) and therefore not independent witnesses to the format.
- **The `.ipuz` and Crossword Compiler XML specifications** were likewise not retrieved; exet's
  handling of `.ipuz` is delegated to `exolve-from-ipuz.js`/`exolve-to-ipuz.js`, which were **not
  read** (only their loading at `exet/exet.html:206-216` and their call sites at
  `exet/exet.js:3611-3631` and `:7913-7939`).
- **CrossHatch's sample word list** [S12] was not fetched, so its score distribution — and hence
  whether the code's 100/50 thresholds or the README's 50/40 are the ones that match the data — is
  unverified.
- **The Qxw user guide** (`qxw-guide-20200708.pdf`, linked from S14) was not retrieved. It was not
  needed: `qxw-20200708/common.h:154-159` states the terminology in the author's own words. It would
  be the source to consult for the *intended* meaning of the interactive-assist modes.
- **The Lufz generator** (github.com/viresh-ratnakar/lufz), which produces S8's index, was not
  retrieved, so *why* the index materialises the 1,009 keys it does — rather than some other set — is
  not established here. The generalisation walk (`exet/exet-lexicon.js:496-504`) tolerates any subset,
  so the choice is a tuning decision made outside this repository.
- **Runtime cost.** No profiling was done. Claims like "crosshatch recomputes crossings by linear
  scan" describe the code shape (`crosshatch/src/lib/util.ts:78-91`), not a measured cost.

### 8.3 "Cited by" rule — not applicable

The run rules require checking the "cited by" list of every founding paper confirmed. **No papers were
consulted in TASK R**: the task named five code repositories, and all six corpora retrieved are source
code, documentation pages or word lists. There is therefore no citation graph to walk. The nearest
thing to a scholarly lineage in the material is Phil's vendored solver, whose provenance chain is
recorded in its own headers — Glucose 3.0 (Audemard & Simon) derived from MiniSat (Eén & Sörensson),
`phil/third_party/glucose-3.0/core/Solver.cc:1-27` — and composer's README pointing at Qxw and at
Steven Morse's integer-programming write-up (`crossword-composer/README.md:65-66`), neither of which
was retrieved.

### 8.4 What was read and what was dropped

**Read in full or in the cited regions:** `crossword-composer` — all of `src/*.rs` and `ui/src/*`.
`phil` — `cross.js`, `wordlist.js`, `patterns.js`, `xw_worker.js`, `files.js`, and
`third_party/glucose-3.0/simp/Main.cc`. `crosshatch` — all of `src/models/*.ts`, `src/lib/*.ts`, and
the handler regions of `Grid.tsx`, `Menu.tsx`, `FillView.tsx`. `exet` — the fill-analysis, storage,
lexicon and grid-edit regions of `exet.js`, plus `exet-autofill.js`, `exet-lexicon.js`,
`exet-analysis.js`, `exet-storage.js`. `exolve` — the grid, clue and clear regions of `exolve-m.js`.
`qxw` — `common.h`, `dicts.h`, `deck.h`, `filler.c`, and the structural regions of `qxw.c`, `dicts.c`,
`treatment.c`, `draw.c`, `gui.c`.

**Dropped, each as outside R1–R6:**

| Dropped | Why |
|---|---|
| `qxw-20200708/gui.c` beyond `m_accept`, `m_autofill`, `m_ifamode` and the feasible-list display | GTK widget construction and dialogue plumbing |
| `qxw-20200708/draw.c` beyond the export block | Cairo rendering of the grid |
| `qxw-20200708/alphabets.c` (1,589 lines), `deck.c` (480) | Unicode alphabet tables and the "deck" plug-in interface; neither touches grid, entry or lookup structure |
| `qxw-20200708/treatment.c` beyond `getinitflist`, `addlight`, `treatedanswerICC` | Answer-treatment plug-in machinery (a Qxw-specific cryptic feature) |
| `phil/third_party/glucose-3.0/core/*`, `mtl/*`, `utils/*` | Upstream SAT solver internals, unmodified; only the licence headers were read |
| `exet/exet.js` clue-editor, indicator, research and charade tabs (~4,000 lines) | Cryptic clue-writing aids, not grid or lookup structure |
| `exet/lufz-hi-lexicon.js`, `lufz-pt-br-lexicon.js` | Non-English lexicons; only their top-level key sets were checked (neither carries `scores`) |
| `exolve/exolve-m-old.js`, `exolve-embedder.js`, `exolve-widget-creator.js` | Legacy and embedding paths not reachable from exet |
| `exolve/exolve-from-text.js` beyond `ExolveGridInferrer` | Not loaded by exet; the inferrer itself was read after the §8.1 search surfaced it |
| `exolve/exolve-from-puz.js`, `exolve-to-puz.js`, `exolve-from-ipuz.js`, `exolve-to-ipuz.js` | Format converters; **read as call sites only** — a gap, noted in §8.2 |
| `crosshatch/src/components/**` beyond the keyboard handlers and the candidate/fill lists | React rendering and SCSS |
| `crossword-composer/ui/rollup.config.js`, `Cargo.toml` | Build configuration |

**Stop criterion.** The task fixed the corpus at five repositories, so the "two consecutive search
angles surface nothing new" rule applied only to the one open question the task implied — whether
exet's grid structures were its own. Two angles settled it: the `<script>` list at
`exet/exet.html:206-216` and the absence of any cell or clue constructor in exet's own scripts. Exolve
was then added as S4. No further expansion of the corpus was undertaken.

### 8.5 Retrieval Access

All seven code and word-list sources were read from a local clone or extracted tarball
(`access_mode: local-clone` on every one of the 206 evidence rows) — no source below was judged from
an HTTP probe alone.

| Source | Access | Note |
|---|---|---|
| S1–S12, S14, S15 | FETCHED | Local clone, extracted tarball, or a page fetched with `curl` and read in full |
| S13 (`.puz` format wiki) | SNIPPET | Cited by `crosshatch/src/lib/puzFiles.ts:10` but **not fetched**. No claim in this report rests on it; all `.puz` statements come from reading the two implementations. |
| S12 (crosshatch sample word list) | SNIPPET | URL and provenance sentence read from `crosshatch/README.md:9-10`; the file itself **not fetched**. |

One retrieval note worth recording for reuse: the Qxw download link is an **unquoted** HTML attribute
(`<a href=qxwdownload.html>`), so a `href="..."` extraction pattern returns nothing and the page reads
as having no download. It was found by re-grepping without the quotes.

---

## Verification record

| Gate | Scope | Red probe | Result |
|---|---|---|---|
| `gate_evidence.py` | 198 evidence rows: quote must occur verbatim inside its cited line range | planted a wrong line range and a mistyped quote; both rejected | **PASS 206/206** — caught two genuine errors (`E176`, `E192`) before passing |
| `gate_citations.py` | every code citation in this report — **469 qualified** (`path:N-M`) **and 72 bare** (`:N-M`, resolved against the nearest preceding qualified path): file must exist, range must be in bounds | planted an out-of-bounds range, a bare ref with no preceding path, and a non-existent file; all rejected | **PASS 541/541** — caught 51 under-qualified paths, all since fully qualified |

The bare-citation watch set was added after the first version of `gate_citations.py` was found to
match only qualified paths — 72 references in this report inherit their file from context, and a gate
that skipped them would have reported "every line range is in bounds" while guarding four fifths of
the citations.

**No `claims.jsonl` or `validation_report.json` is emitted for this run.** The deep-research
validators check `[N]`-style citation markers against a numbered Bibliography; this report cites
sources as `[S1]`–`[S15]` and code as `path:line`, with no numbered bibliography, so those validators
would either pass vacuously or fail on a format they were not given. The claim ledger for this run is
the `note` field of each row in `evidence.jsonl`, which is what the two gates above actually check.

Artefacts: `sources.jsonl` (15), `evidence.jsonl` (206), `build_evidence.py`, `gate_evidence.py`,
`gate_citations.py`, `run_manifest.json`, `corpus/` (six clones plus the Qxw tarball and two pages).
