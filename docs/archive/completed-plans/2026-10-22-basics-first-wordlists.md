# Basics First: Word Lists — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new user can load the shipped lists, upload their own in any line format the parser reads, see it in the list panel, and get correct pattern-search results from it.

**Architecture:** CLI first (`cli/`), then `backend/core/cli_adapter.py`, then the Flask route, then React. Data cleanup is a file move plus deleting directory sweeps; no new shared definition of "default list".

**Tech Stack:** Python 3.9+ · Click · Flask 3.0 · React 18 · Vite 5 · pytest · vitest

**Spec:** `docs/archive/completed-plans/2026-10-22-basics-first-design.md`. §6 open points carry defaults that apply if unruled by 2026-10-29. Tasks 6, 7, 8 and 10 implement those defaults; re-read §6 before starting them.

## Global Constraints

- Python floor 3.9: module-level type aliases use `typing.Union`, not `|` (CLAUDE.md anti-pattern).
- Crossword logic lives in `cli/`; the backend reaches it only through `cli_adapter.py` (spec §4).
- Work on branch `chore/wordlist-basics` off `main`. Re-check the branch before every commit.
- Run any suite whose result you cite **alone**; read the rc from a redirect, never through a pipe.
- UI tasks are not done until driven in a real browser (build-green plus vitest is not evidence).
- After the last task lands on `main`, re-pin the research bundle once (standing note in `.handoff/log.md`).

---

### Task 1: A cache that cannot load falls back to the text list (spec §3)

**Files:**
- Modify: `cli/src/fill/word_list.py` (`WordList.from_file`, the `cache_mtime >= source_mtime` branch)
- Test: `cli/tests/unit/test_word_list.py`

**Behavioral criteria:**
- Any exception raised by `WordList.from_cache` inside `from_file` (including `ModuleNotFoundError`, `AttributeError`, `pickle.UnpicklingError`, `EOFError`) results in the `.txt` being parsed and returned.
- Exactly one warning line goes to stderr, containing the cache path.
- `from_cache` called directly keeps its current contract.

**Normative cases:**

| cache state | result |
|---|---|
| valid cache, newer than `.txt` | words from cache |
| cache whose pickle names a missing module | words from `.txt`, one stderr warning naming the cache |
| truncated cache file | words from `.txt`, one stderr warning |

- [x] Write a failing test that builds a cache pickling a class under a module path that does not exist, and asserts the `.txt` words come back.
- [x] Run `pytest cli/tests/unit/test_word_list.py -v`; confirm it fails on the propagated exception.
- [x] Implement; rerun; pass.
- [x] Commit `fix(wordlist): fall back to the text list when a cache cannot be unpickled`, with `Refs #44` and `Refs #43` in the body (not `Closes`: `scripts/check-commit-msg.sh` rejects partial-closure trailers).

### Task 2: Stop tracking caches (spec §2)

**Files:** `.gitignore`; index removal of `data/wordlists/comprehensive.pkl` and `data/wordlists/top_100k.pkl`.

**Behavioral criteria:**
- `git ls-files 'data/wordlists/*.pkl'` prints nothing; the files may stay on disk.
- `git check-ignore -v data/wordlists/x.pkl` names the new `.gitignore` line.

- [x] `git rm --cached` both caches; add `data/wordlists/**/*.pkl` to `.gitignore`.
- [x] Commit `chore(wordlists): untrack the stale .pkl caches`, body `Refs #58`.

### Task 3: Move the unfiltered family to `raw/`; panel skips it; metadata cleanup (spec §2)

**Files:**
- Move: `data/wordlists/{comprehensive_scored,comprehensive_intl,top_50k,top_100k,top_200k}.txt` → `data/wordlists/raw/`
- Move: `data/wordlists/spreadthewordlist_caps.dict` → `data/wordlists/external/`
- Modify: `backend/data/wordlist_manager.py` (`list_all`: skipped dirs)
- Modify: `data/wordlists/metadata.json`, `data/wordlists/README.md`
- Modify consumers found by `git grep -n -E "comprehensive_scored|comprehensive_intl|top_(50|100|200)k|spreadthewordlist_caps" -- . ':!data/wordlists' ':!docs/archive' ':!docs/dev/qa'`: at writing, `docs/dev/DEVELOPMENT.md`, `docs/superpowers/specs/2026-09-07-domain-capabilities-design.md`, `scripts/analyze_crossword_datasets.py`, `scripts/validate_hybrid_system.sh`, and a comment in `src/api/client.js`. Re-run the grep; it is the list.
- Test: `backend/tests/unit/test_wordlist_manager.py`, `backend/tests/integration/test_wordlist_metadata.py`

**Behavioral criteria:**
- Before moving, `git check-ignore -v data/wordlists/raw/x.txt` must return rc 1 (not ignored).
- `list_all()` returns no key starting with `raw/`.
- Every key in `metadata.json["wordlists"]` names an existing file; the `comprehensive` description contains no digits.
- The `#` header lines inside moved files are left as they are.

- [x] Failing test: `list_all()` over a fixture dir containing `raw/x.txt` excludes it.
- [x] Move files with `git mv`; edit `list_all`; clean the metadata; update consumers and the word-list README.
- [x] `pytest backend/tests/unit/test_wordlist_manager.py backend/tests/integration/test_wordlist_metadata.py -v`; `scripts/docs-check.sh` after staging.
- [x] Commit `chore(wordlists): move the unfiltered list family to raw/ and drop dead metadata`, body `Refs #58`.

### Task 4: verify-words and clean default to `comprehensive` (spec §2)

**Files:**
- Modify: `backend/api/routes.py` (`verify_words` and `clean_grid`, the no-`wordlists` branches that call `wordlist_dir.rglob("*.txt")`)
- Test: `backend/tests/unit/test_routes.py` (tests that patch `pathlib.Path.rglob` for these routes move to patching `get_default_wordlist_paths`), `backend/tests/test_api.py` (the comment naming the rglob fallback)

**Contract:** both branches call `get_default_wordlist_paths()` from `backend/core/wordlist_resolver.py`; neither calls `rglob`.

**Normative cases:**

| request `wordlists` | lists read |
|---|---|
| omitted | `comprehensive` only |
| `["core/crosswordese"]` | that list only (unchanged) |
| `["nope"]` | 400 `UNKNOWN_WORDLIST` (unchanged) |

- [x] Failing test asserting `wordlist_size` for an omitted `wordlists` equals the `comprehensive` word count read from the file in the test.
- [x] Implement; run `pytest backend/tests/unit/test_routes.py backend/tests/test_api.py -v`.
- [x] Commit `fix(api): verify-words and clean fall back to the default list, not every list`.

### Task 5: `fill` validates against its own lists (spec §2, sub-ruling ii)

**Files:**
- Modify: `cli/src/cli.py` (`fill`: the `all_valid_words` block that sweeps `wordlist_dir.rglob("*.txt")`)
- Test: a CLI unit test beside the existing `fill` tests under `cli/tests/`

**Behavioral criteria:**
- `all_valid_words` is the set of words `fill` loaded from its `-w` lists, with no directory read.
- It is never empty when the loaded list is non-empty. `IterativeRepair._is_valid_word` returns False for every word when the set is empty, so an empty set would flag the whole grid.
- Theme words and theme entries still count as valid (unchanged, in `IterativeRepair`).

**Normative case:** `fill` with `-w` a list that lacks a word present only in `raw/comprehensive_scored.txt` reports that word as invalid if it is placed.

- [x] Failing test on the validation set's contents (inject a tiny `-w` list; assert nothing outside it is in the set).
- [x] Implement; run the new test, then `pytest cli/tests/unit -v` **alone**.
- [x] Commit `fix(fill): validate entries against the loaded lists, not every file on disk`.

### Task 6: One line parser for `fill` and `resume` (spec §4, #51 reader half)

**Files:**
- Modify: `cli/src/cli.py` (`fill`'s loading loop that does `line.split(";")[0]`; `_load_wordlist_words`)
- Test: `cli/tests/unit/` (beside the existing `parse_line` tests in `test_word_list.py`)

**Behavioral criteria:**
- Both loaders parse each line with `WordList.parse_line` and keep the file score: `WordList` receives `(word, score)` tuples, so a file score overrides the computed one (existing `add_words` contract).
- `word,50` lines load; a `word,score` header is skipped.

**Normative cases** (one file, loaded by both `fill` and `resume`):

| line | loaded word | score |
|---|---|---|
| `APPLE;50` | `APPLE` | 50 |
| `grape,40` | `GRAPE` | 40 |
| `LEMON` | `LEMON` | computed |
| `word,score` | (skipped) | — |

- [x] Failing tests for both loaders over that file.
- [x] Implement; run; commit `fix(cli): fill and resume parse word-list lines with parse_line`, body `Refs #51`.

### Task 7: `parse-wordlist` command and adapter method (spec §4, O4)

**Files:**
- Modify: `cli/src/cli.py` (new command), `backend/core/cli_adapter.py` (new method)
- Test: `cli/tests/unit/` and `backend/tests/unit/test_cli_adapter.py`, plus one real-subprocess test (CLAUDE.md seam rule)

**Contract:**

```
python -m cli.src.cli parse-wordlist <file> --json-output
→ {"words": [{"word": str, "score": int|null}], "skipped": [{"line": int, "text": str, "reason": str}]}
```

```python
def parse_wordlist(self, path: str) -> Dict[str, Any]: ...   # CLIAdapter
```

**Behavioral criteria:**
- A line is valid iff `parse_line` returns a tuple **and** the word passes `WordList._is_valid_word`. Every other non-blank, non-`#` line is in `skipped` with a reason from: `"malformed score"`, `"not letters only"`, `"length outside 3-21"`.
- Duplicates keep the first occurrence.
- `line` is 1-based.

**Normative cases:**

| line | outcome |
|---|---|
| `APPLE;50` | word `APPLE`, score 50 |
| `apple,x` | skipped, `malformed score` |
| `CAFÉ` | word `CAFÉ`, score null. `_is_valid_word` accepts it (`'CAFÉ'.isalpha()` is True). Whether accented words should be accepted is #57 item 1, unruled; do not change it here. |
| `AB` | skipped, `length outside 3-21` |
| `ONE TWO` | skipped, `not letters only` |

- [x] Failing CLI tests, failing adapter argv contract test, then implement both, then the real-subprocess test.
- [x] Commit `feat(cli): parse-wordlist reports parsed words and skipped lines`, body `Refs #51 #46`.

### Task 8: Import route parses, rejects, stores canonically, previews (spec §4, O5–O7; #48 §1)

**Files:**
- Modify: `backend/api/wordlist_routes.py` (`import_wordlist`), `backend/data/wordlist_manager.py` (`load`, `get_wordlist_info`, `add_words`)
- Modify: `docs/api/openapi.yaml` (`/wordlists/import`: `dry_run`, 400 body)
- Test: `backend/tests/unit/` and `backend/tests/integration/test_wordlist_metadata.py`

**Behavioral criteria:**
- The route writes `content` to a temp file and parses it via `CLIAdapter.parse_wordlist`.
- Zero valid words → 400 with body per O7; nothing stored.
- `dry_run: true` → 200 with the parse result; nothing stored, metadata untouched.
- Otherwise the list is stored one canonical line per word (O5), and the metadata entry is **merged**, never replaced: it keeps `name` (display name = last path segment, `_` → space, title case, the rule `get_wordlist_info` already uses).
- `WordListManager.load` strips a trailing `;N`.
- `get_wordlist_info` returns a copy; calling it never changes `_metadata`.
- `POST /api/wordlists/<name>` with no category prefix creates `custom/<name>` (O10); a later PUT and DELETE on it succeed.

**Normative cases:**

| request | status | stored / metadata |
|---|---|---|
| content `"APPLE;50\ngrape,40\n"` | 201 | lines `APPLE;50`, `GRAPE;40`; entry has `name` |
| content `""` | 400 | nothing |
| content `"!!\n12\n"` | 400, `skipped` 2 | nothing |
| same as row 1 with `dry_run: true` | 200 | nothing |
| GET per-list after import | 200 | `metadata.json` on disk byte-identical before and after |
| `POST /api/wordlists/qa-put` then PUT, then DELETE | each the success code `docs/api/openapi.yaml` documents for it (not 403) | entry `custom/qa-put`, category `custom`, then gone |

- [x] Failing tests per row; implement; `pytest backend/tests -v` alone.
- [x] Commit `fix(api): import parses via the CLI, rejects empty lists, keeps metadata names`, body `Refs #46 #48 #51`.

### Task 9: Upload UI — no extension gate, preview, confirm (spec §4, O6, O8, O9)

**Files:**
- Modify: `src/components/WordListPanel.jsx` (`handleFileSelect`, `handleUpload`, the `accept=".txt"` input and its label), `src/components/ThemeWordsPanel.jsx` (`handleFileSelect`, `accept=".txt"`), `src/api/client.js` (`importWordlist` gains `dryRun`)
- Test: the components' `__tests__` files (vitest)

**Behavioral criteria:**
- No extension check and no `accept` attribute restricting extensions in either panel; the size limits stay.
- Selecting a file and pressing Upload first calls import with `dry_run: true` and shows the preview (O8). Confirm sends the real import; Cancel sends nothing more.
- A 400 shows the server's `error` plus the skipped count and reasons; nothing is added to the list.

- [x] Failing vitest cases: a `.dict` file reaches the dry-run call; Cancel sends one request in total; a 400 renders the reasons.
- [x] Implement; `npx vitest run` alone; `npm run build`.
- [x] **Browser:** with `python run.py`, upload `data/wordlists/external/crossword_nexus.dict` (first 20 lines copied to a temp file), see the preview, confirm, see the list in the panel, run a pattern search on it. Record what was seen. *(Done with a deviation: the 20-line excerpt is all digit lines, so it was rejected with reasons; the preview, confirm and pattern search were driven with a mixed `.owl` file. Ledger, Task 9.)*
- [x] Commit `feat(ui): word-list upload previews any text file before saving`, body `Refs #46`.

### Task 10: `pattern` reports a list it could not load (spec O1, #44 remainder) and strict cache freshness (O2, #42)

**Files:**
- Modify: `cli/src/cli.py` (`pattern`: the `except Exception` around `WordList.from_file`), `cli/src/fill/word_list.py` (`cache_mtime >= source_mtime` → `>`)
- Modify: `src/` pattern-search panel: surface `errors` as a warning toast. Find its call site with `git grep -n "api.pattern\|searchPattern" -- src`.
- Test: `cli/tests/unit/`, the panel's vitest file

**Behavioral criteria:** per O1 and O2.

- [x] Failing tests; implement; run; commit `fix(pattern): report lists that failed to load instead of dropping them`, body `Refs #44 #42`.

### Task 11: The list panel is visible on open (#45)

**Files:** `src/components/WordListPanel.scss` (`.sidebar`, `.wordlist-list`), `src/components/WordListPanel.jsx` if structure must change.

**Behavioral criteria (measured, not judged):** at 1440×900 and 1024×768, in production (`python run.py`) **and** dev (`npm run dev`), immediately on opening the Lists tool:
- the first `.wordlist-list` row's bounding rect lies inside the viewport and inside `.sidebar`'s visible rect;
- the list scrolls when it is taller than the space left (its own `overflow-y`, or the sidebar's, but reachable without scrolling past the category buttons first).

Use the QA run's method (same-origin iframe at exact sizes, `docs/dev/qa/2026-10-22-fresh-install-run.md` cases L3/L4/L16) and paste the DOM JSON for each of the four combinations.

- [x] Measure before (expect the QA failure); fix; measure after; `npx vitest run`; `npm run build`.
- [x] Commit `fix(ui): show the word-list box inside the sidebar on open`, body `Refs #45`.

### Task 12: Close-out

- [x] `pytest` alone, `npx vitest run`, `npm run build`, `scripts/docs-check.sh`, `scripts/check-guards.sh --full-tree`: each rc read from a redirect.
- [x] Fast-forward `main`; re-pin the bundle (standing note); comment on each issue with what landed (draft, then post in a separate call). *(Fast-forward and re-pin done 2026-10-23. Per Arthur's ruling that day, the comments go out with the PR that carries these commits, not as standalone posts.)*
- [x] Move this plan and its spec to `docs/archive/completed-plans/` once every task is checked.
