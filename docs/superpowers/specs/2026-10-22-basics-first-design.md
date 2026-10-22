# Basics First: Word Lists, Pattern Search and Upload — Design
**Version 0.1.0** · Claude with Arthur Passuello · 2026-10-22 · status: §1–§4 ratified by owner 2026-10-22;
§6 open points carry defaults that apply if unruled by 2026-10-29

---

## AI READING INSTRUCTION

Read `[SPEC]` blocks for authoritative behaviour. Read `[NOTE]` only for context. `[?]` blocks are
unverified. Issue numbers are GitHub issues on `apassuello/crossword-helper`; each carries the QA
evidence and a 2026-10-22 second-review correction comment where one was needed.

---

## 1. Scope and priority

**[SPEC]**
- The most important fixes are the basics that make the app useful: loading word lists, using them in
  pattern search, and importing word lists. Autofill (#40, #41, #59) comes after.
  *Ruled by Arthur 2026-10-22 17:42 CEST. **What it beat:** the QA run's severity order, which put
  autofill (#40) first.*
- In scope for this design: #58, #42, #43, #44, #45, #46, #51, #48.
- Next design, not this one: #55 (new grid) and #47 (restore a saved grid), then the user guide.
  Their rulings are recorded in §5 so they are not re-asked.
- Out of scope: autofill issues; #52–#54, #56, #57, #60.

**[NOTE]** Grid import and HTML export passed the QA run, so "import" here means word-list import.

---

## 2. Word-list inventory and defaults (#58)

**[SPEC]** *Ruled by Arthur 2026-10-22 18:45 CEST: option A plus a list cleanup. **What it beat:**
B, rebuilding the tracked `.pkl` from the curated list, which stays stale whenever the `.txt` changes
and keeps #43; C, treating the unfiltered list as "comprehensive", which contradicts the curated
list's own README.*

- **No cache is tracked.** Every `.pkl` under `data/wordlists/` is removed from the index and ignored.
  A cache exists only where `build-cache` wrote one.
- **The unfiltered family moves to `data/wordlists/raw/`:** `comprehensive_scored.txt`,
  `comprehensive_intl.txt`, `top_50k.txt`, `top_100k.txt`, `top_200k.txt`. They stay loadable by
  explicit path. *Sub-ruling i (move the `top_*` lists too) taken by default on "go".*
- **The default list is `comprehensive` alone**, as `get_default_wordlist_paths()` in
  `backend/core/wordlist_resolver.py` already defines and as `VALIDATION_WORDLISTS` in `src/App.jsx`
  already sends. No new definition of "default" is introduced. *Accepted with the advisor's
  refinement on "go"; it beat a broader default of `comprehensive` + `core/` + `themed/`, which would
  have needed a new shared definition the backend cannot import.*
- **Every code path that swept all lists stops sweeping:**
  - `WordListManager.list_all` (the UI's list panel) skips `raw/` as it skips `archive/` and
    `external/`.
  - `/api/grid/verify-words` and `/api/grid/clean` with no `wordlists` use
    `get_default_wordlist_paths()`.
  - CLI `fill` validates entries against the words it loaded from its own `-w` lists, never a
    directory sweep. *Sub-ruling ii taken by default on "go". This makes the "may be invalid" count
    and the repair cleanup pass stricter: the unfiltered lists no longer vouch for a word.*
- **Metadata:** `data/wordlists/metadata.json` loses every entry whose file does not exist. The
  `comprehensive` description states no word count (counts are computed: `word_count`).
- **`spreadthewordlist_caps.dict`** moves to `data/wordlists/external/`, beside the other `.dict`.

**[NOTE]** The family was committed in `7dfcccf` and `941c1ff` (2025-12-21), before the filtering that
`data/wordlists/README.md` dates 2025-12-27. Sizes: `wc -l data/wordlists/*.txt`.

---

## 3. Cache loading never empties a list (#44, part)

**[SPEC]**
- `WordList.from_file` falls back to the `.txt` whenever a selected cache cannot be loaded, for any
  exception raised while unpickling, and writes one stderr warning naming the cache path.
- A cache failure therefore never yields an empty or missing list.

**[NOTE]** Today the fallback catches only `ValueError` and `FileNotFoundError`; an unpickling
`ModuleNotFoundError` (#43) propagates to `pattern`, which drops the list silently (#44). With caches
untracked (§2), this is reachable only after a manual `build-cache`, but that is the path the README's
CLI section documents.

---

## 4. Word-list upload and scored lines (#46, #51)

**[SPEC]** *Ruled by Arthur 2026-10-22 18:45 CEST: option C. **What it beat:** A, allowing `.txt` and
`.dict` only, which still refuses `.owl`/`.csv` lists the parser reads; B, the same as C without a
preview.*
- **No file-extension gate** on word-list upload. The format is decided by line content.
- **One line format.** `WordList.parse_line` in `cli/src/fill/word_list.py` is the only definition of
  a word-list line: plain `WORD`, `WORD;N`, `word,N`, with a `word,score` header skipped. `fill` and
  `resume` read through it, so file scores are kept and comma-scored lines are no longer dropped.
- **Parsing is a CLI capability** reached through `backend/core/cli_adapter.py`, because the backend
  never imports `cli/` (CLAUDE.md: CLI first, then adapter, then route, then UI).
- **An upload that yields zero valid words is rejected** with the number of skipped lines and their
  reasons. An empty file is one such case.
- **The user sees a preview** of the parsed result before the list is saved, and can confirm or
  cancel.

---

## 5. Rulings for the next design (#47, #55)

**[SPEC]** *Ruled by Arthur 2026-10-22 18:45 CEST.*
- **#47: option C.** On load, the app restores the saved grid and shows a banner naming when it was
  saved, with a "Start new" action. **What it beat:** A, auto-restore with no way out (there is no
  new-grid control yet, #55); B, a Load button a user may never notice.
- C depends on #55's new-grid action, so #55 lands first.

---

## 6. Open points (default applies if unruled by 2026-10-29)

| # | Question | Default |
|---|---|---|
| O1 | #44: how does `pattern` report a list it could not load? | It still searches the other lists. JSON output gains `"errors": [{"wordlist": <path>, "message": <str>}]`; text output prints one warning line per list; the UI shows a warning toast naming the list. Exit code unchanged. |
| O2 | #42: cache freshness rule | `cache_mtime > source_mtime` (strict). With no tracked cache, equal mtimes no longer arise from a ZIP download. |
| O3 | #43: one import root for caches | Deferred; §3 makes the failure loud and harmless. #43 stays open. |
| O4 | Parse command contract | `parse-wordlist <file> --json-output` returns `{"words": [{"word": str, "score": int or null}], "skipped": [{"line": int, "text": str, "reason": str}]}`. |
| O5 | What the import route stores | One canonical line per word: `WORD;N` when a score was given, `WORD` otherwise. `WordListManager.load` strips a `;N` suffix so the list detail, stats and search show the word alone. |
| O6 | How the preview is requested | `POST /api/wordlists/import` with `"dry_run": true` returns the parse result and stores nothing. |
| O7 | Rejection response | HTTP 400, `{"error": "No valid words found", "skipped": <int>, "reasons": {<reason>: <count>}}`. |
| O8 | Preview content | Total valid words, total skipped with reasons, and the first 20 parsed words with scores; Confirm and Cancel. |
| O9 | Theme-words upload (`ThemeWordsPanel.jsx`) | Its `.txt` gate is dropped too; theme parsing is otherwise unchanged. |
| O10 | #48: where `POST /api/wordlists/<name>` puts a name with no category prefix | Under `custom/<name>`, so it is editable and deletable like an upload. Today it lands at the root with category `"."` and every later PUT and DELETE returns 403. |

---

## 7. Amendment record

- 0.1.0 (2026-10-22): first version, from the owner rulings above.
