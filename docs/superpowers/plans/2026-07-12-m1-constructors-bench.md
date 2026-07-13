# Milestone 1 — "Constructor's Bench" GUI Reskin Implementation Plan

> **For agentic workers:** Execute task-by-task (workflow-orchestrated; fresh agent per task). Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Plan style (Arthur's convention):** this plan carries decisions, contracts, signatures, and assertion checklists — **the executing agent writes all code.** Short snippets appear only where a literal is load-bearing. If a step seems underspecified, the binding references are (in order): the task's Interfaces block, the Authoritative endpoint contracts table, the Cross-task literals section, and the actual source files cited by file:line.

**Goal:** Reskin the crossword-helper web GUI to the "Constructor's Bench" design (editorial print aesthetic, SVG grid, tool rail, 460px inspector), wire every panel to the REAL existing backend endpoints, and restore a working pause→edit→resume autofill loop — with zero NEW endpoint surface.

**Architecture:** The Flask backend and CLI stay the single source of truth; the React frontend is rebuilt in place (same `src/`, feature branch, panel by panel) on top of a single API-client module that encapsulates every real endpoint contract. The pause→edit→resume restore is plumbing behind existing endpoints: the CLI `fill` command learns `--task-id`/`--resume`/`--state-dir`/`--pause-flag-dir` (matching the pre-existing `CLIAdapter.fill_with_resume` contract at `backend/core/cli_adapter.py:403`), and the frontend consumes the two-step resume that the backend already implements.

**Tech Stack:** React 18 + Vite 5 (existing), vitest + jsdom (existing), Flask 3 (existing), Click CLI (existing), `@fontsource-variable/*` for self-hosted fonts, plain hand-written CSS with `xw-` prefix and CSS custom properties (no CSS framework).

**Design bundle (source material, NOT in this repo):**
`/Users/apa/projects/RustyBoï/crossword/Claude_Design_GUI_downloads/` — `grid.jsx`, `panels.jsx`, `Crossword Helper.html` (CSS + App shell), `docs/spec/00-09*.md`. `wordlist.js` and `tweaks-panel.jsx` are on the **never-copy list** (truncated demo data / artifact-host tooling). Screenshots are never committed.

---

## Global Constraints

- **Public repo — scrub rule:** No personal strings from the design bundle may enter any tracked file. The patterns live in `.handoff/scrub-list.txt` (gitignored); Task 1 installs a pre-commit guard from them. `wordlist.js` and bundle screenshots are never copied. **The FIRST commit containing bundle-derived content (Task 4) requires Arthur's explicit go-ahead — hard STOP gate.**
- **CLI is the single source of truth. The GUI never solves.** Client-side computation policy (grant/deny list) is in §"Client-side computation policy" below; every task must respect it.
- **All API URLs and payload shapes live ONLY in `src/api/client.js`.** No component may call axios/fetch/EventSource directly. Enforced by the Task 1 pre-commit guard.
- **Real backend contracts win over the design spec.** The spec (bundle `docs/spec/*`) claims contracts that are wrong; the authoritative table is §"Authoritative endpoint contracts" below. Never wire to a spec-named path without checking that table.
- **Error surfacing — four surfaces only** (per spec 08, which we keep): inline-below-field (validator 400s), red toast top-right (~6s, request/timeout/network), orange-banded autofill error card (SSE `status:"error"`), red top-bar health dot (`GET /api/health` poll every 30s). No `alert()`, no modals-for-errors, no console-only errors.
- **No spinners.** Keep previous results visible during in-flight requests. Skeletons only where there is no prior content.
- **State machines** follow spec 06 exactly, plus the three amendments in §"State-machine amendments" (pausing sub-state, restore entry, resume-via-submitting). No other extra or merged states.
- **Fonts self-hosted** via `@fontsource-variable/fraunces`, `@fontsource-variable/work-sans`, `@fontsource-variable/jetbrains-mono` (all OFL). No Google Fonts CDN, no CDN React/Babel.
- **Timeout bounds:** fill `timeout` int 10–1800 s; pattern `max_results` 1–100; grid `size` int 3–50 (`--allow-nonstandard` handled server-side).
- **Testing:** pytest for backend/cli (`pytest backend/tests/ cli/tests/`), vitest for frontend (`npx vitest run`). New slow E2E tests get `@pytest.mark.slow`. Run the relevant suite before every commit.
- **Commits:** conventional messages `type(scope): description`. Do not push. Do not use `--no-verify`.
- **Out of scope for M1** (deferred to Milestone 2): server-side save/library (B1/B8), import/export formats + PDF (B2/B3), plural `sources` per pattern match (B4), `prefer_personal` scoring (B5), SSE Last-Event-ID replay (B6), F8 (recent-imports/publish), beam exact-state resume, offline bundled-wordlist fallback (localhost app — backend down means features disable with a banner, not degrade to junk data).

---

## Authoritative endpoint contracts (reality, verified 2026-07-12)

The design spec's 04-api-reference claims marked ✗ below are WRONG. This table is the contract; `src/api/client.js` implements exactly this.

| Real endpoint | Request (JSON unless noted) | Response (200 unless noted) | Spec deviation |
|---|---|---|---|
| `GET /api/health` | — | `{status:"healthy"\|"degraded", version, architecture, components:{cli_adapter, api_server}}`; 503 when degraded | ✗ spec invents `components.cli/wordlists` |
| `POST /api/pattern` | `{pattern, wordlists?=["comprehensive"], max_results?=20, algorithm?="regex"}` | `{meta, results:[{word, score, source, length, letter_quality}]}` | ✗ spec says `matches[]` + `sources[]`; real key is `results[]`, singular `source` already present |
| `POST /api/pattern/with-progress` | same as `/api/pattern` | `202 {task_id, progress_url}` | ✓ |
| `POST /api/number` | `{size?, grid}` (CLI-string cells) | `{numbering:{"(r,c)": n}, grid_info:{size:[r,c], black_squares, black_square_percentage, white_squares, word_count, meets_nyt_standards}}` | ✗ spec invents `{grid, slots, violations[]}` — none exist; numbers come as `"(r,c)"`-keyed map |
| `POST /api/grid/validate` | `{grid, grid_size?=15}` | `{valid, word_count, black_square_count, black_square_percentage, word_count_range, warnings[], suggestions[]}` (200 even when invalid) | spec doesn't know this endpoint; use it for F2 violations |
| `POST /api/fill/with-progress` | `{size, grid, wordlists?, themeList?, theme_entries?, timeout?=300, min_score?=30, algorithm?="repair", adaptive_mode?, max_adaptations?, partial_fill?, cleanup?}` | `202 {task_id, progress_url}` | ✗ spec adds `prefer_personal` (not accepted). Task 15 adds `resume_task_id` |
| `GET /api/progress/<task_id>` (SSE) | — | `data: {progress, message, status:"running"\|"paused"\|"complete"\|"error", timestamp, data?}` — **no `event:` name, no `id:`, no replay**; heartbeat comment every 30 s; stream ends after complete/error | ✗ spec invents `event: progress` + Last-Event-ID replay (B6, deferred). Premature `complete`/`error` from CLI stderr is ALREADY handled by `run_cli_with_progress` (routes.py:305-307) — **downgraded to `running` and forwarded** (not dropped); `paused` passes through verbatim |
| `POST /api/fill/pause/<task_id>` | — (task_id in **path**) | `{success, message, task_id}` — 200 means "flag file written", NOT "state saved" | ✗ spec says body `{task_id}` → `{task_id, phase}` with 404/409; none of that exists |
| `POST /api/fill/cancel/<task_id>` | — (path) | `{success, task_id, message, state_saved:true}` — `state_saved` is hardcoded, treat as unverified | ✗ same |
| `POST /api/fill/resume` | `{task_id, edited_grid?, options?}` | `{success, new_task_id:"resume_<8hex>", original_task_id, message, slots_filled, total_slots}`; 400 missing task_id; 404 no state; **409 `{error:"User edits create unsolvable configuration", details}`** (flat-string error + **top-level** `details`). **Does NOT start a fill** — client must start one with `resume_task_id` | ✗ spec draws one `paused→running` arrow; reality is two-step |
| `GET /api/fill/state/<task_id>` | — | `{task_id, timestamp, algorithm, slots_filled, total_slots, grid_size, iteration_count, grid_preview}`; 404 | spec omits |
| `DELETE /api/fill/state/<task_id>` | — | `{success, message}`; 404 | spec omits |
| `GET /api/fill/states?max_age_days=` | — | `{states:[...], count}` | spec omits |
| `POST /api/fill/states/cleanup` | `{max_age_days?=7}` | `{success, deleted_count, message}` | spec omits |
| `POST /api/fill/edit-summary` | `{task_id, edited_grid}` | `{filled_count, emptied_count, modified_count, new_words[], removed_words[]}`; 400/404 | spec omits |
| `POST /api/grid/verify-words` | `{grid, size?, wordlists?}` | `{invalid_words:[{word, direction, cells:[[r,c]], status:"invalid"\|"unfillable"}], invalid_count, total_checked, wordlist_size}` | ✓ (FlagReport matches) |
| `POST /api/grid/clean` | `{grid, size?}` | `{grid, removed_count, valid_count, cleared_cells?, message}` | ✗ spec says `{size, grid}`; extras exist |
| `POST /api/normalize` | `{text}` (≤100 chars) | CLI passthrough | ✓ |
| `POST /api/grid/suggest-black-square` | `{grid, problematic_slot:{row,col,direction,length,...}, grid_size?=15, max_suggestions?=3}` | `{suggestions:[...], slot_info, grid_size, validation}` or `{suggestions:[], message, slot_info}` | ✗ spec calls it `/api/grid/suggest-black` with `{near}`; real REQUIRES `problematic_slot` (Task 20 makes the CLI provide it) |
| `POST /api/grid/apply-black-squares` | `{grid, primary:{row,col}, symmetric:{row,col}}` | `{grid, applied:true, positions}` | spec omits |
| `GET /api/wordlists?category=` | — | `{wordlists:[...], categories:{...}, tags:{...}}` | ✗ spec invents `{lists:[{id,name,group,count,...}]}` |
| `GET /api/wordlists/<name>?stats=true` | — | `{metadata, words, stats?}` | spec omits |
| `PUT /api/wordlists/<name>` | `{words?}` XOR `{add_words?, remove_words?}`, `{metadata?}` | `{message}` | ✗ spec's `/api/wordlists/personal/{add,remove,score}` DO NOT EXIST; add/remove maps here; per-word score unsupported (M2) |
| `DELETE /api/wordlists/<name>` | — | `{message}`; 404 | spec omits |
| `POST /api/wordlists/import` | `{name, content, category?="imports", metadata?}` | `201 {message, name:"<category>/<name>", word_count}` | ✗ spec says multipart `/api/wordlists/upload`; real is JSON `import` |
| `POST /api/wordlists/search` | `{pattern, wordlists?}` | `{pattern, total_matches, results:[{word, sources[]}]}` | spec omits (note: this one DOES have plural sources) |
| `POST /api/theme/upload` | `{content, grid_size?=15}` (JSON, not multipart) | `{words[], count, validation:{valid, errors, warnings}}` | ✗ spec implies multipart |
| `POST /api/theme/validate` | `{theme_words[], grid_size?=15}` | `{valid, errors[], warnings[]}` | ✗ spec says `{entries[], size}` → `{results[]}` |
| `POST /api/theme/suggest-placements` | `{theme_words[], grid_size?=15, existing_grid?, max_suggestions?=3}` | `{suggestions:[{word, length, suggestions:[{row, col, direction, score, reasoning}]}], grid_size}` | ✗ spec says singular `suggest-placement`, `{placements:[{entry, candidates}]}` |
| `POST /api/theme/apply-placement` | `{grid, placement:{word, row, col, direction}}` | `{grid, applied:true}`; 400 `{error:"Placement conflicts detected", conflicts[], applied:false}` | spec omits |
| `POST /api/constraints` | `{grid, wordlists?=["comprehensive"]}` | CLI passthrough `{constraints, summary}` (per-cell `{across_options, down_options, min_options}`) | ✗ spec calls it `/api/constraint`; Task 20 extends payload with `most_constrained_slot` + `slots[]` |
| `POST /api/constraints/impact` | `{grid, word, slot:{row,col,direction,length}, wordlists?}` | CLI passthrough `{impacts, summary}` | spec omits |

**Error envelope reality:** `handle_error()` (backend/api/errors.py) returns `{error:{code, message, details?}}` — matches spec 08. BUT: app-level 404/405 return flat `{error:"string"}` (fixed in Task 3), TIMEOUT responses use status 505/506/507 (typos for 504, fixed in Task 3), and several blueprints (wordlist/theme/grid/constraint) return flat `{error:"string"}` 400s — the client must handle both shapes (Task 2's normalization rules).

**Grid cell encodings.** Three exist; the client owns all conversions (Task 2):
1. **Frontend canonical:** `{letter:"", isBlack:false, isThemeLocked:false, number:null, isError:false}`
2. **CLI strings** (all backend calls, including resume/edit-summary — verified: `Grid.from_dict` crashes on dict cells, grid.py:343): `"#"` black, `"."` empty, `"A"` letter, always **uppercase**
3. `numbering` response keys: `"(r,c)"` strings — parse with `/^\((\d+),\s*(\d+)\)$/`.

## Cross-task literals (single source — reference these, never restate)

Tasks 13/14/15/19 all depend on these agreeing; they are stated ONLY here.

- **Pause flag file:** `<pause_flag_dir>/crossword_pause_<task_id>.flag` (built at pause_controller.py:40; dir mkdir'd with parents=True).
- **State file:** `<state_dir>/<task_id>.json.gz` (gzipped JSON; state_manager.py:164-167).
- **Serialized state envelope** (state_manager.py:89-102): top-level keys `{version, algorithm:"csp"|"beam", task_id, timestamp, metadata, state_data}`. `algorithm` here is the STATE FORMAT — always `"csp"` for anything `save_csp_state` writes, independent of the `--algorithm` flag value. `state_data` is `asdict(CSPState)` and contains `domains`. `metadata` is caller-supplied (the fill command records the flag value there, e.g. `{"algorithm": "repair"}`).
- **Degenerate CSPState — 11 required fields, no defaults** (state_manager.py:18-51): `grid_dict, domains, constraints, used_words, slot_id_map, slot_list, slots_sorted, current_slot_index, iteration_count, locked_slots, timestamp` (ISO string — omitting `timestamp` is a `TypeError` at construction). Optional: `random_seed`, `letter_frequency_table`. `save_csp_state` (kwarg name `csp_state`) does asdict+json+gzip with no validation — empty `domains={}` saves fine.
- **Fill success stdout keys** (verified against a real run, 2026-07-12; built at cli.py:564-573): `success, grid, fill_percentage, iterations, slots_filled, total_slots, problematic_slots_count, time_elapsed`. The empty-grid early return (cli.py:~437-450) emits the same keys plus `message` — a superset, not a conflict.
- **Paused stdout protocol** (new, Task 13): `{"paused": true, "task_id": ..., "slots_filled": n, "total_slots": m}`, exit code **0**.
- **Web shared dirs** (new, Task 15): `backend/core/state_paths.py` exports `STATE_DIR` (= `backend/data/autofill_states`) and `PAUSE_FLAG_DIR`; backend routes AND every CLI invocation the backend spawns must use these explicitly — split defaults are how the current severance happened.
- **Algorithm flag values** (verified cli.py:120 — there is NO `csp` value): `regex`/`trie` = classic CSP `Autofill`; `beam`; `repair`; `hybrid` = beam+repair. Web default: `repair`.

---

## Client-side computation policy

Written once here so no task re-litigates it.

**The GUI MAY compute (geometry / derived views):**
- Slot extents from the grid (start/end of the word through a cell in a direction) — needed for focus highlight, pattern strings, clue enumeration.
- The focused slot's pattern string (`"C?T"` style) sent to `/api/pattern`.
- 180° symmetry mirror position of a toggled cell.
- **Display-only optimistic clue numbers** immediately after a structural edit, ALWAYS reconciled by the `/api/number` response when it arrives (spec F2 mandates apply-local-reconcile; this is a deliberate, documented single-source-of-truth exception — the server response is authoritative and overwrites).
- Grid stats already returned by the backend may be re-derived locally for instant display (black-square count, word count) but validity verdicts must come from `/api/grid/validate`.

**The GUI MUST NOT compute:**
- Word/pattern search or candidate lists (`/api/pattern` only; no bundled fallback in M1).
- Word validity or scores (`/api/grid/verify-words`, `score` from pattern results).
- Fill of any kind.
- Constraint/fillability judgments (`/api/constraints`; the "most constrained slot" verdict comes from the server after Task 20).

---

## State-machine amendments (to spec 06)

06 §1 (autofill) is kept with three amendments, justified by real backend behavior:

1. **`pausing` sub-state of `running`** (F11): `running --Pause clicked--> running.pausing`; enter `paused{task_id, progress}` only when the SSE stream emits `status:"paused"` OR `GET /api/fill/state/<id>` returns 200. If neither within 10 s → back to plain `running` + red toast. Rationale: pause 200 only means "flag written".
2. **Restore entry** (F12): `idle --saved state discovered--> paused{task_id, progress}`. Amended invariant: **the EventSource is open only in `running`** (paused never holds an open stream — on pause the CLI process exits after saving state, ending the stream).
3. **Resume via `submitting`** (F14): `paused --Resume--> submitting(resume) --202--> running{new task_id}`. Two real requests: `POST /api/fill/resume` (409 → stay `paused` with conflict data, F15), then `POST /api/fill/with-progress {resume_task_id}`. Failure of either returns to `paused`, never `failed`.

06 §3 (save) is implemented over an async storage adapter with localStorage transport in M1 (Task 7); M2 swaps the transport to `POST /api/grid/save` without touching the machine.

---

## File Structure

**Create:**
```
.scrub-patterns                       # gitignored; copied from .handoff/scrub-list.txt (Task 1)
scripts/check-guards.sh               # pre-commit guard: scrub + URL confinement (Task 1)
src/api/client.js                     # ALL endpoint contracts (Task 2)
src/api/gridCodec.js                  # cell-format conversions + numbering-key parser (Task 2)
src/api/__tests__/client.test.js
src/api/__tests__/gridCodec.test.js
src/styles/bench/tokens.css           # CSS custom properties, light+dark (Task 4)
src/styles/bench/base.css             # xw- component classes (Task 4)
src/components/bench/CrosswordGrid.jsx        # ported grid (Task 5)
src/components/bench/TopBar.jsx               # (Task 6)
src/components/bench/ToolRail.jsx             # (Task 6)
src/components/bench/FlagBanner.jsx           # (Task 10)
src/components/bench/ClueInspector.jsx        # (Task 9)
src/components/bench/PatternSearchPanel.jsx   # (Task 9)
src/components/bench/AutofillPanel.jsx        # (Task 11)
src/components/bench/ResumeCard.jsx           # (Tasks 16–18)
src/components/bench/WordListsPanel.jsx       # (Task 12)
src/components/bench/ClueListPanel.jsx        # (Task 12)
src/components/bench/GridEditPanel.jsx        # (Task 12)
src/components/bench/ThemeWordsPanel.jsx      # (Task 21)
src/components/bench/BlackSquareOverlay.jsx   # (Task 20)
src/components/bench/Toast.jsx                # (Task 6)
src/hooks/useHealth.js                # (Task 6)
src/hooks/useSaveMachine.js           # (Task 7)
src/hooks/useAutofillMachine.js       # (Tasks 11, 16–18)
src/hooks/useGridGeometry.js          # slot extents, patterns, symmetry (Task 5)
src/lib/storage.js                    # async save adapter over localStorage (Task 7)
backend/tests/integration/test_pause_resume_e2e.py   # slow, real subprocess (Task 19)
cli/tests/test_fill_pause_resume.py   # (Tasks 13–14)
```

**Modify:**
- `.pre-commit-config.yaml`, `.gitignore` (Task 1)
- `backend/api/routes.py` (Task 3: 504 fixes; Task 15: `resume_task_id`)
- `backend/app.py` (Task 3: 404/405 envelope)
- `backend/core/cli_adapter.py` (Task 14: fix `fill_with_resume` state-dir/flags)
- `backend/api/pause_resume_routes.py` (Task 15: explicit shared state dir constant)
- `cli/src/cli.py` (Tasks 13–14: fill command flags)
- `cli/src/fill/iterative_repair.py` (Task 13: pause hook)
- `cli/src/fill/autofill.py` (Task 13: `was_paused` flag, two lines)
- `src/App.jsx` (progressively: Tasks 5–18)
- `src/main.jsx` (Task 4: font + CSS imports)
- `package.json` (Task 4: fontsource deps)

**Delete (with their tests — disposition per task):** `src/components/GridEditor.jsx` (Task 5), `src/components/ToolPanel.jsx` (Task 6), old `AutofillPanel/PatternMatcher/WordListPanel/ThemeWordsPanel/BlackSquareSuggestions/ProgressIndicator` (Tasks 9–12, 20–21 as each replacement lands), old SCSS as panels stop using it (Task 23 sweeps).

**Test disposition rule (D5):** every task that replaces a component states: *port* (test logic still applies → rewrite against new component), *rewrite* (behavior changed → new tests written first, TDD), or *delete* (feature removed → delete test with one-line reason in commit message). A task is not done while `npx vitest run` is red.

---

## Phase 0 — Guards & foundations

### Task 1: Repo guards (scrub + URL confinement)

**Files:**
- Create: `scripts/check-guards.sh`, `.scrub-patterns`
- Modify: `.gitignore`, `.pre-commit-config.yaml`

**Interfaces:**
- Produces: a pre-commit hook `check-guards` that fails any commit whose staged files contain a scrub pattern, and fails if `axios`/`fetch(`/`new EventSource` appear in staged `src/` files outside `src/api/` and `src/__tests__/`.

- [ ] **Step 1: Create the local pattern file (never committed)**

Copy the non-comment, non-empty lines of `.handoff/scrub-list.txt` into `.scrub-patterns`; append `.scrub-patterns` to `.gitignore`.

- [ ] **Step 2: Write `scripts/check-guards.sh` (executable) meeting ALL of these requirements**

1. Operates on **staged blob content** (`git show :<file>` over `git diff --cached --name-only --diff-filter=ACM`), never the working tree — partially-staged files must be checked as staged.
2. Exits 0 immediately when nothing is staged.
3. Scrub check uses **fixed-string** matching (`grep -F`) against `.scrub-patterns`; **skips silently if `.scrub-patterns` is absent** (it's gitignored — other clones/CI must not fail).
4. URL confinement: staged files under `src/` — excluding `src/api/` and `src/__tests__/` — must not contain `axios`, `fetch(`, or `new EventSource`.
5. On violation: print which files and which guard, exit 1.

Register it in `.pre-commit-config.yaml` as a `repo: local` hook:

```yaml
      - id: check-guards
        name: scrub + api-url confinement guard
        entry: scripts/check-guards.sh
        language: system
        pass_filenames: false
        always_run: true
```

(The three keys `language: system`, `pass_filenames: false`, `always_run: true` are load-bearing — wrong values fail silently.)

- [ ] **Step 3: Verify the guard blocks a poisoned commit**

```bash
head -1 .scrub-patterns > poison_test.js && git add poison_test.js
git commit -m "test" ; echo "exit=$?"   # Expected: BLOCKED message, nonzero exit
git reset HEAD poison_test.js && rm poison_test.js
```

- [ ] **Step 4: Verify the guard passes clean, then commit**

```bash
git add .gitignore .pre-commit-config.yaml scripts/check-guards.sh
git commit -m "chore(guards): pre-commit scrub + api-url confinement"
```

---

### Task 2: API client module (`src/api/client.js` + `src/api/gridCodec.js`)

**Files:**
- Create: `src/api/gridCodec.js`, `src/api/client.js`, `src/api/__tests__/gridCodec.test.js`, `src/api/__tests__/client.test.js`

**Interfaces:**
- Produces (gridCodec): `makeCell()`, `makeGrid(size)`, `toCliStrings(grid) -> string[][]`, `fromCliStrings(rows) -> grid`, `applyNumbering(grid, numberingMap) -> grid` (immutable; sets `.number`, clears stale ones), all per the Grid cell encodings section. Letters are **uppercased** in both directions.
- Produces (client): one exported async function per row of the contracts table. Signatures used by ALL later tasks (this block is the single binding reference — later tasks consume these exact names):

```js
// every function returns parsed JSON or throws ApiError{status, code, message, details}
export class ApiError extends Error {}
export const api = {
  health(),                                       // GET /api/health (returns body even on 503)
  numberGrid({ size, grid }),                     // grid: string[][] (CLI strings)
  validateGrid({ grid, gridSize }),
  searchPattern({ pattern, wordlists, maxResults = 40, algorithm = "trie" }),
  startFill(options),                             // POST /api/fill/with-progress; options.resumeTaskId? added Task 15
  openProgress(taskId, { onEvent, onError }),     // returns { close() }; parses SSE data lines
  pauseFill(taskId), cancelFill(taskId),
  resumeFill({ taskId, editedGrid, options }),    // editedGrid: string[][] CLI strings
  getFillState(taskId), listFillStates(maxAgeDays), deleteFillState(taskId),
  cleanupFillStates(maxAgeDays = 7),
  editSummary({ taskId, editedGrid }),
  verifyWords({ grid, size, wordlists }), cleanGrid({ grid, size }),
  normalize(text),
  suggestBlackSquare({ grid, problematicSlot, gridSize, maxSuggestions = 3 }),
  applyBlackSquares({ grid, primary, symmetric }),
  getWordlists(), getWordlist(name, { stats } = {}), updateWordlist(name, body),
  deleteWordlist(name), importWordlist({ name, content, category, metadata }),
  searchWordlists({ pattern, wordlists }),
  themeUpload({ content, gridSize }), themeValidate({ themeWords, gridSize }),
  themeSuggestPlacements({ themeWords, gridSize, existingGrid, maxSuggestions = 3 }),
  themeApplyPlacement({ grid, placement }),
  getConstraints({ grid, wordlists }),
};
```

**Error-normalization rules (binding — these exist nowhere else):**
1. Network failure (fetch rejects) → `ApiError{status: 0, code: "NETWORK"}`.
2. Unparseable/empty response body is swallowed to `{}` — never throw on JSON parse.
3. Flat-string error bodies (`{"error": "Missing grid"}`) and envelope bodies (`{"error": {"code", "message"}}`) both produce a coherent `ApiError` (message from the string or `err.message`).
4. Code synthesis for non-envelope errors: HTTP 409 → `"UNSOLVABLE_EDITS"`, otherwise `"HTTP_<status>"`.
5. `details` is read from top-level `data.details` **or** nested `err.details` — the real resume-409 body has a flat-string `error` with a **top-level** `details` sibling (contracts table).
6. `health()` returns the body on HTTP 503 (degraded is data, not an exception).

**SSE:** `openProgress` wraps `new EventSource('/api/progress/' + taskId)` using the **`onmessage` property handler** (no named events server-side — and the test `MockEventSource` in `src/__tests__/setupTests.js:30-81` supports only property handlers, not `addEventListener`; tests push events via the static `MockEventSource.sendMessage(obj)`, broadcast to all live instances). `close()` must be idempotent.

- [ ] **Step 1: Write failing gridCodec tests.** Must assert: canonical↔CLI-strings round-trip (black → `"#"`, letter → uppercase, empty → `"."`); `applyNumbering` parses real `"(r,c)"` keys, sets numbers, and **clears stale numbers** on cells absent from the map.
- [ ] **Step 2: Run to verify failure** — `npx vitest run src/api/__tests__/gridCodec.test.js` — Expected: FAIL ("module not found").
- [ ] **Step 3: Implement `gridCodec.js`; run — Expected: PASS.**
- [ ] **Step 4: Write failing client tests (mock `fetch`).** Must assert at minimum: (a) `searchPattern` posts to `/api/pattern` with the defaults from the signature and returns `results` untouched; (b) `pauseFill("t1")` POSTs to `/api/fill/pause/t1` with no body; (c) `resumeFill` 409 → `ApiError{status:409, details}` populated from a **top-level** `details`; (d) flat-string AND envelope error bodies both normalize (rules 3–4); (e) `openProgress` parses `data:` JSON via `MockEventSource.sendMessage`.
- [ ] **Step 5: Run — Expected: FAIL. Implement `client.js` per the contracts table + rules above.**
- [ ] **Step 6: Run all frontend tests — Expected: PASS (`npx vitest run`).**
- [ ] **Step 7: Commit**

```bash
git add src/api .gitignore
git commit -m "feat(api): client module encapsulating real backend contracts"
```

---

### Task 3: Backend hygiene — TIMEOUT status typos + 404/405 envelope

**Files:**
- Modify: `backend/api/routes.py:90` (505→504), `routes.py:166` (506→504), `routes.py:236` (507→504), `backend/app.py:62-74`
- Test: `backend/tests/unit/test_error_hygiene.py` (create)

**Interfaces:**
- Produces: all TIMEOUT responses are HTTP 504 `{error:{code:"TIMEOUT",...}}`; app-level 404/405 return `{error:{code:"NOT_FOUND"|"METHOD_NOT_ALLOWED", message}}` (same envelope shape `handle_error` uses).

- [ ] **Step 1: Check for tests asserting the old codes**

Run: `grep -rn "505\|506\|507" backend/tests/ cli/tests/` — if any assert those statuses, update them in the same commit.

- [ ] **Step 2: Write failing tests.** Using the Flask test client (`create_app(testing=True)`), assert: (a) `GET /api/nonexistent` → 404 with `body.error.code == "NOT_FOUND"` and a string message; (b) `GET /api/pattern` (POST-only route) → 405 with `code == "METHOD_NOT_ALLOWED"`; (c) with `CLIAdapter.pattern` mocked to raise `subprocess.TimeoutExpired`, `POST /api/pattern` → **504**.
- [ ] **Step 3: Run** `pytest backend/tests/unit/test_error_hygiene.py -v` — Expected: FAIL (flat 404 body; 505 status).
- [ ] **Step 4: Implement** — replace the two flat app-level handlers in `backend/app.py`; change the three TIMEOUT statuses in `routes.py` to 504.
- [ ] **Step 5: Run backend suite — Expected: PASS (`pytest backend/tests/`).**
- [ ] **Step 6: Commit** — `fix(api): TIMEOUT status 504 everywhere; envelope for 404/405`

---

## Phase 1 — Design shell

> **⛔ STOP GATE — before Task 4's commit.** Task 4 is the first commit containing bundle-derived content (design tokens/CSS). Present the scrubbed diff to Arthur and get an explicit go-ahead. Do not proceed to commit without it. Subsequent tasks ride normal commits (the pre-commit guard enforces the scrub).

### Task 4: Design tokens + self-hosted fonts + dark mode

**Files:**
- Create: `src/styles/bench/tokens.css`, `src/styles/bench/base.css`
- Modify: `src/main.jsx`, `package.json`

**Interfaces:**
- Produces: CSS custom properties (`--paper`, `--paper-2`, `--paper-3`, `--ink`, `--ink-2/3/4`, `--ink-08`, `--accent`, `--accent-ink`, `--accent-15/06/60`, `--danger`, `--warn`, `--good`, `--card`, `--card-edge`, `--cell-px`), dark overrides under `[data-theme="dark"]`, `xw-` base classes; fonts available under the `--font-display/--font-ui/--font-mono` custom properties.

- [ ] **Step 1: Install fonts** — `npm install @fontsource-variable/fraunces @fontsource-variable/work-sans @fontsource-variable/jetbrains-mono`
- [ ] **Step 2: Port the stylesheet.** Source: `Crossword Helper.html` lines ~11–355 (the inline `<style>` block) → `tokens.css` (`:root` + `[data-theme="dark"]` variable blocks) and `base.css` (all `xw-*` classes). Drop all `twk-*` rules (tweaks shell — never-copy). Replace the Google Fonts families with exactly these (the `" Variable"` suffix is load-bearing — `"Fraunces"` alone silently falls back to Georgia):

```css
:root {
  --font-display: "Fraunces Variable", Georgia, serif;
  --font-ui: "Work Sans Variable", system-ui, sans-serif;
  --font-mono: "JetBrains Mono Variable", ui-monospace, monospace;
}
```

Scrub check: run `grep -Ff .scrub-patterns src/styles/bench/*.css` — expect empty.

- [ ] **Step 3: Wire into the app entry** — in `src/main.jsx`, import order matters (fonts first, then bench CSS, before legacy styles):

```js
import "@fontsource-variable/fraunces";
import "@fontsource-variable/work-sans";
import "@fontsource-variable/jetbrains-mono";
import "./styles/bench/tokens.css";
import "./styles/bench/base.css";
```

- [ ] **Step 4: Verify** — `npm run build` succeeds; `npm run dev` renders the existing app unbroken (tokens are additive; legacy SCSS still loaded). `npx vitest run` green.
- [ ] **Step 5: ⛔ STOP — show Arthur the diff, get explicit go-ahead, then commit** — `feat(ui): Constructor's Bench design tokens + self-hosted fonts`

---

### Task 4.5: Migrate `src/App.jsx` network calls onto the `api` client

**Purpose:** Guard 2 (`scripts/check-guards.sh`) blocks any staged `src/` file outside `src/api/` + `src/__tests__/` that contains `axios`, `fetch(`, or `new EventSource`. `App.jsx` still uses `axios` + a raw `EventSource`, so the next task that re-stages it would be blocked. Standalone task (Arthur chose this over folding the migration into the top of Task 5) so the transport swap lands as one reviewable, side-effect-free commit.

**Scope:** Pure, behavior-preserving transport swap onto the existing `src/api/client.js` surface — request payloads stay **byte-identical** (values, defaults, encoding), only the transport changes. No new behavior, no test rewrites, no `App.test.jsx` (Tasks 5–18 rewrite this lifecycle). **verify/clean keep their object-cell `{letter,isBlack}` payloads** — they hit a dict-tolerant backend path and byte-identical payload = identical behavior. Encoding cleanup (object-cell → `gridCodec`) is **Task 10's** job, not this one.

**Files:**
- Modify: `src/App.jsx` only (swap `import axios` → `import { api } from './api/client'`).
- Untouched by design: `axios` stays in `package.json` (other components import it); `src/hooks/useSSEProgress.js` stays (Task 11 deletes it).

**Interfaces (contracts consumed, all from `src/api/client.js`):**
- `api.startFill(options)` — POST `/api/fill/with-progress`; returns parsed body (`{ task_id }`) directly, no `.data`. Caller owns grid encoding; client passes `grid` through verbatim.
- `api.openProgress(taskId, { onEvent, onError })` → handle with idempotent `close()`. `onEvent` receives the **already-parsed** SSE object (client owns `JSON.parse`).
- `api.cancelFill(taskId)`, `api.verifyWords({ grid, size, wordlists })`, `api.cleanGrid({ grid, size })` — each returns parsed body or throws `ApiError{status,code,message,details}` (no `.response`).

**The 5 migrated sites:**
1. **startFill** — hand the *exact* old object literal (`size`, CLI-string `grid`, `wordlists`, `timeout`, `min_score` from `minScore ?? 50`, `algorithm`, `theme_entries`, `adaptive_mode`, `max_adaptations`, `partial_fill`, `cleanup`) to `api.startFill({…})`; destructure `const { task_id } = await …` (drop the old `initResponse.data`). *Not* `api.startFill(options)` — that would ship camelCase keys, lose the `?? 50` default, and send an unencoded grid.
2. **SSE** — `api.openProgress(task_id, { onEvent, onError })` stored in `eventSourceRef.current`. `onEvent` body = the old `onmessage` body verbatim **minus** the `JSON.parse` line, keeping the inner `try/catch` (it guards the `data.data.grid` mapping, not just the parse), both `isThemeLocked` grid-map guards, and the complete/paused/error branch asymmetry (paused deliberately does *not* clear `currentTaskId`). `onError` replicates the old `onerror` exactly. Every inner `eventSource.close()` → `eventSourceRef.current?.close()` (idempotent).
3. **cancel** — `api.cancelFill(taskId).catch(…)` (keep the `.catch`).
4. **verify** — `api.verifyWords({ grid: <object-cell matrix>, size, wordlists: ['comprehensive'] })`; destructure the awaited body (drop `response.data`).
5. **clean** — `api.cleanGrid({ grid: <object-cell matrix>, size })`; destructure the awaited body (drop `response.data`).
- `handleCancelAutofill` / `handleResetAutofill` call `eventSourceRef.current.close()` unchanged — the handle exposes `close()`, so they keep working without edits.

**Verification:**
- `grep -nE "axios|fetch\(|new EventSource" src/App.jsx` → empty (Guard 2 clears).
- `npm run build` + `npx vitest run` green — **regression-only**: no test imports `App`, so these prove syntax/imports, *not* SSE correctness.
- Real check is an **adversarial payload diff**: read the moved SSE body line-by-line against the original; confirm startFill serializes byte-identically and verify/clean keep object-cell encoding.
- Manual **browser SSE smoke** (start → incremental grid updates → complete/paused/error) when a dev server is up.

---

### Task 5: Port CrosswordGrid + grid geometry hook

**Files:**
- Create: `src/components/bench/CrosswordGrid.jsx`, `src/hooks/useGridGeometry.js`, tests for both
- Modify: `src/App.jsx` (swap GridEditor → CrosswordGrid)
- Delete: `src/components/GridEditor.jsx` + its test file (**disposition:** interaction tests *rewritten* against CrosswordGrid; heatmap-fetch tests *ported* later in Task 22 — until then keep the old heatmap test file skipped with `describe.skip` and a `// re-enabled in Task 22` note)

**Interfaces:**
- Consumes: nothing new.
- Produces: `<CrosswordGrid grid focus selectedDir heatmap={null|number[][]} onFocus(r,c) onSetLetter(r,c,ch) onToggleBlack(r,c) onToggleLock(r,c) onRotateDir() onMoveFocus(r,c) />` — fully controlled, no internal grid state. `useGridGeometry(grid)` → `{ slotAt(r,c,dir) -> {cells:[[r,c]], pattern, number, length}, allSlots() -> {across:[], down:[]}, mirrorOf(r,c,size) }`.

- [ ] **Step 1: ESM-convert the prototype grid.** Source: bundle `grid.jsx` (263 lines). Mechanical recipe: add the React import, delete the trailing `Object.assign(window, {CrosswordGrid})`, add a default export. Keep all rendering (cells, numbers, focus/word highlight, theme-lock marker, error underline, heatmap shading, paper texture) verbatim — colors already flow from the Task 4 CSS variables.
- [ ] **Step 2: Fix the keydown-rebind defect.** The prototype re-attaches its keydown listener on every state change (effect deps include `grid`). Required structure, in prose: (a) all handlers/state live in a ref that is updated every render; (b) the listener is attached exactly once (empty-deps effect) and reads through the ref; (c) the prototype's key-dispatch switch is lifted to a pure function so it can be unit-tested without mounting.
- [ ] **Step 3: Port Tab-to-next-word (regression guard — current GridEditor HAS it).** Reference implementation: `src/components/GridEditor.jsx:156-182` (`moveToNextWord`). In the new keyboard model: Tab advances to the next word start (Shift+Tab previous), wrapping and switching direction after the last across/down slot — mirror the old GridEditor's semantics via `useGridGeometry().allSlots()`. Enter keeps the prototype's rotate behavior.
- [ ] **Step 4: Write tests first** (`npx vitest run` red→green). Must assert — geometry: `slotAt` extents around black squares; `mirrorOf(0,0,15) === [14,14]`; pattern strings use `?` for empties. Grid: typing advances focus in `selectedDir`; typing blocked on black + theme-locked cells; Tab jumps to next word start; Space toggles black via callback; heatmap prop renders shading.
- [ ] **Step 5: Swap into App.jsx** — map App's existing handlers (`handleCellClick`, letter setter, `toggleBlackSquare` with symmetry, right-click lock) onto the controlled props; delete `GridEditor.jsx`. App's grid state shape already matches the canonical cell.
- [ ] **Step 6: Full frontend suite green; visual check via `npm run dev`; commit** — `feat(ui): port Constructor's Bench SVG grid with fixed keyboard model`

---

### Task 6: Shell layout — TopBar, ToolRail, Toast, health dot

**Files:**
- Create: `src/components/bench/TopBar.jsx`, `ToolRail.jsx`, `Toast.jsx`, `src/hooks/useHealth.js`, tests
- Modify: `src/App.jsx` (layout: 54px topbar / 112px rail / fluid canvas / 460px inspector)
- Delete: `src/components/ToolPanel.jsx` (**disposition:** stats/size/symmetry controls *ported* into ToolRail + GridEditPanel (Task 12); its tests rewritten across those two)

**Interfaces:**
- Consumes: `api.health()` (Task 2).
- Produces: `<TopBar status savedLabel onVerify onSave onToggleTheme />`; `<ToolRail tool onSelectTool viewToggles={{symmetry, heatmap}} onToggleView stats />`; `useToasts()` context → `pushToast({kind:"error"|"info", message})` rendered top-right, auto-dismiss 6 s; `useHealth()` → `{online: bool, degraded: bool}` polling every 30 s (no backoff — spec 08).

- [ ] **Step 1: Port TopBar/ToolRail markup** from bundle `panels.jsx:46-140` (ESM recipe as Task 5). Dark-mode toggle sets `document.documentElement.dataset.theme`, persisted to `localStorage["xw_theme"]`.
- [ ] **Step 2: TDD `useHealth`** — vitest fake timers: 200 healthy → `online:true`; fetch rejection → `online:false`; 503 body → `online:true, degraded:true`. 30 s interval.
- [ ] **Step 3: Toast context TDD** — pushes render; auto-dismiss at 6 s; multiple stack.
- [ ] **Step 4: Recompose App.jsx layout** — grid canvas center, right inspector hosts the CURRENT panels for now (they restyle in later tasks); offline behavior per 07 §3.3: red dot + disable Verify/Clean/Autofill-Start buttons with `title` tooltips (wire actual disabling as each panel is ported; TopBar's Verify disabled now).
- [ ] **Step 5: Suite green; commit** — `feat(ui): bench shell layout, health dot, toast surface`

---

### Task 7: Save machine over async local storage (F9/F10 — local variant)

**Files:**
- Create: `src/lib/storage.js`, `src/hooks/useSaveMachine.js`, tests
- Modify: `src/App.jsx` (replace ad-hoc `crossword_saved_grid` handling), `src/components/bench/TopBar.jsx` (savedLabel)

**Interfaces:**
- Produces: `storage.save(doc) -> Promise<{savedAt}>`, `storage.load() -> Promise<doc|null>` (async wrapper over localStorage — M2 swaps transport to `POST /api/grid/save` without touching the machine); `useSaveMachine({doc, isDirty})` implementing spec 06 §3 exactly: `pristine → dirty → saving → saved(ts)`, 30 s auto-save timer **runs only in `dirty`**, save failure → `dirty` + error toast, label derived from timestamp on every render (never stored as string).

- [ ] **Step 1: TDD the machine with fake timers** — edits mark dirty; timer fires at 30 s only when dirty; success transitions to `saved(ts)` and clears the timer; a rejected `storage.save` returns to `dirty` and pushes a toast; **no timer leaks across doc identity change (F10)** — changing `doc.id`/grid reference resets cleanly (assert via fake timers).
- [ ] **Step 2: Implement; TopBar shows `saved locally · Xm ago` (re-rendered per minute), or `unsaved changes`, or `offline — will retry` when a save rejects.**
- [ ] **Step 3: Migrate App's existing `crossword_saved_grid` read/write to `storage.js` (same key — old saves must still load). Suite green; commit** — `feat(ui): save state machine over async local storage`

---

## Phase 2 — Panel wiring (existing endpoints)

### Task 8: F2 — server-authoritative numbering + violations

**Files:**
- Modify: `src/App.jsx` (or extract `src/hooks/useNumbering.js` — preferred), tests

**Interfaces:**
- Consumes: `api.numberGrid`, `api.validateGrid`, `gridCodec.applyNumbering`, `useGridGeometry`.
- Produces: `useNumbering(grid)` — after every **structural** edit (black toggle, size change, load): (1) optimistic local renumber for display (policy exception — port the numbering pass from bundle HTML:365-410 `numberGrid` helper as `localNumber(grid)`; display-only), (2) `POST /api/number` with CLI strings, reconcile via `applyNumbering` on response (server wins), (3) `POST /api/grid/validate` in parallel; `violations = [...warnings, ...suggestions]` surfaced in ToolRail stats block. Letter edits never renumber. Debounce 150 ms; discard out-of-order responses with a token.

- [ ] **Step 1: TDD** — black-toggle triggers both calls (mock `api`); response numbering overwrites optimistic numbers when they differ; out-of-order response discarded; letter typing triggers neither; API failure → toast + optimistic numbers stay (labelled `unverified` flag on the hook's return for the stats block).
- [ ] **Step 2: Implement; remove App's legacy client-only numbering path. Latency note:** the spec's <80 ms budget is unmeetable over subprocess (~120–180 ms) — accepted deviation; optimistic-apply keeps typing unblocked.
- [ ] **Step 3: Suite green; commit** — `feat(grid): server-reconciled numbering + validation surfacing (F2)`

---

### Task 9: F1 — ClueInspector + PatternSearchPanel on real `/api/pattern`

**Files:**
- Create: `src/components/bench/ClueInspector.jsx`, `src/components/bench/PatternSearchPanel.jsx`, tests
- Delete: `src/components/PatternMatcher.jsx` + tests (**disposition:** *rewrite* — the SSE-progress pattern flow is dropped in favor of the spec's debounced sync search; keep `useSSEProgress` as reference until Task 11 deletes it)

**Interfaces:**
- Consumes: `api.searchPattern`, `useGridGeometry` (focused slot pattern), `useToasts`.
- Produces: inspector bound to focused cell/slot per bundle `panels.jsx:184-286`; candidate click → `onApplyWord(slot, word)` writes letters into App grid (marks dirty).

- [ ] **Step 1: Port both components** (ESM recipe). **Fix the rules-of-hooks bug** (`panels.jsx:185-198`: early return before `useMemo`) — hoist all hooks above the `if (!focused)` return.
- [ ] **Step 2: Replace `window.patternMatch` with the real client, spec semantics:** debounce 120 ms; keep previous results during flight (no spinner — 06 §4: `lastResults` + `inFlightToken`, discard out-of-order); failure → toast, results stay. Map real fields: `results[].word/score/source/length`; score grades a/b/c/d from score (≥70 a, ≥50 b, ≥30 c, else d); source badge renders `source` directly. Min-score/sort controls filter client-side over returned results (display filtering, not solving). **No bundled offline fallback** — when `useHealth().online === false`, show the inspector's banner "backend offline — search unavailable" and keep last results.
- [ ] **Step 3: TDD:** debounce coalesces keystrokes (fake timers); stale response discarded; empty state uses descriptive copy; hooks-order regression test (toggle focused null→set → no crash); apply-word writes letters + marks save-machine dirty.
- [ ] **Step 4: Suite green; commit** — `feat(inspector): live pattern search on /api/pattern (F1)`

---

### Task 10: F5 — Verify & Clean + FlagBanner

**Files:**
- Create: `src/components/bench/FlagBanner.jsx`, tests
- Modify: `src/App.jsx` (verify/clean handlers move to the 06 §2 machine)

**Interfaces:**
- Consumes: `api.verifyWords`, `api.cleanGrid`, TopBar's `onVerify`.
- Produces: verify machine `idle → checking → flagged{report} → cleaning → idle`, `flagged --Dismiss--> idle`; cells in `invalid_words[].cells` get `isError:true`; user edit clears `isError` locally on touched cells only, banner persists until Dismiss/re-Verify (06 invariant).

- [ ] **Step 1: Port FlagBanner** (bundle `panels.jsx:143-181`) — chips for `invalid` vs `unfillable` from the REAL FlagReport fields; wordlist meta line uses `total_checked`/`wordlist_size`.
- [ ] **Step 2: TDD the machine:** verify → checking (banner "checking…", previous chips stay); response → flagged + isError cells; Clean → cleaning → idle with server grid replacing local (the ONLY grid-replacement outside autofill-done); editing a flagged cell clears only that cell's isError; offline disables both buttons with tooltip.
- [ ] **Step 3: Suite green; commit** — `feat(verify): real verify-words/clean flow with flag banner (F5)`

---

### Task 11: F3 — AutofillPanel with real SSE (start/cancel; pause lands in Phase 3)

**Files:**
- Create: `src/components/bench/AutofillPanel.jsx`, `src/hooks/useAutofillMachine.js`, tests
- Delete: old `src/components/AutofillPanel.jsx`, `src/components/ProgressIndicator.jsx`, `src/hooks/useSSEProgress.js` + tests (**disposition:** SSE-parsing tests *ported* into `useAutofillMachine` tests; resume-prompt tests *rewritten* in Tasks 16–18; spinner component *deleted* — design forbids spinners)

**Interfaces:**
- Consumes: `api.startFill`, `api.openProgress`, `api.cancelFill`, `gridCodec.toCliStrings`.
- Produces: `useAutofillMachine()` implementing 06 §1 (+amendments): `{state, start(options), cancel(), reset(), progress, message, errorCard}`; `done` is the only state that replaces the grid with `event.data` solver output; leaving `running` closes the EventSource; SSE `status:"error"` → orange error card (not toast). Options panel maps to REAL fill fields (algorithm select `repair/hybrid/beam/trie` — trie labelled "Classic CSP"; there is no `csp` value; timeout 1/2/5/10/30 min → seconds, min_score, adaptive_mode + max_adaptations, partial_fill, cleanup, wordlist multi-select from `api.getWordlists`, theme entries from isThemeLocked cells — port `getThemeEntries` from old panel:224). **No `prefer_personal` checkbox** (endpoint rejects it — B5 deferred).
- Produces for Phase 3: machine internals kept as a pure transition function so Tasks 16–18 extend rather than rewrite.

- [ ] **Step 1: TDD the machine** (mock api + MockEventSource): start → submitting → 202 → running (EventSource opened); running progress events update `{progress, message}` monotonic; `complete` → done + grid callback with `data`; `error` event → failed + error card content; cancel → POST + close stream + cancelled → idle; SSE `paused` status → paused state (UI affordance completed Phase 3; for now paused renders the card "paused — resume support lands with F11" and Reset).
- [ ] **Step 2: Port the panel design** (bundle `panels.jsx:359-462`): progress model maps `{pct: progress, label: message}`; drop the mock ticker; "Suggest black square" button renders disabled with `title="lands in Task 20"` for now.
- [ ] **Step 3: Wire App: remove App.jsx's inline EventSource/autofill lifecycle (App.jsx:206-345) in favor of the hook; incremental `running` partial-grid previews (`event.data` on running) applied as before.**
- [ ] **Step 4: Suite green; manual smoke: run a real 5×5 fill via `npm run dev` + `python run.py`. Commit** — `feat(autofill): SSE-driven autofill machine per spec 06 (F3)`

---

### Task 12: Remaining panel ports — WordLists, ClueList, GridEdit, Import/Export shells

**Files:**
- Create: `src/components/bench/WordListsPanel.jsx`, `ClueListPanel.jsx`, `GridEditPanel.jsx`, tests
- Modify: `src/components/ExportPanel.jsx`, `src/components/ImportPanel.jsx` (restyle with xw- classes only — client-side logic unchanged)
- Delete: old `WordListPanel.jsx` + tests (**disposition:** endpoint-CRUD tests *ported* to the new panel — same api calls)

**Interfaces:**
- Consumes: `api.getWordlists/getWordlist/updateWordlist/deleteWordlist/importWordlist`, `api.normalize` (clue text normalize button).
- Produces: WordListsPanel with REAL catalog (`{wordlists, categories, tags}` — not the spec's fake `{lists}` shape); selection state feeds the `wordlists[]` array used by pattern/fill/verify calls (App-level state `selectedWordlists`). ClueListPanel (bundle `panels.jsx:638-672`): clue text keyed by **slot identity `${dir}-${number}-${length}`** (bundle's `dir-number` keys orphan clues on renumbering — fix by re-keying through numbering reconciliation; document the mapping in the component). GridEditPanel: size selector + clear + symmetry toggle (moved from old ToolPanel — **ToolPanel was deleted in Task 6, so size-selector + Clear Grid must be REBUILT here; recover the source verbatim from `git show pre-toolpanel-removal:src/components/ToolPanel.jsx` (tag → commit `c758c07`). Symmetry already survived on App's `symmetryEnabled` state; only size + clear were orphaned Tasks 6–11**); **drop the fake preset cards** (all four call the same seed — decorative fiction).

- [ ] **Step 1: TDD WordListsPanel** — catalog render from real shape; import posts `{name, content, category}`; add/remove words via PUT `{add_words}/{remove_words}`; personal-list add/remove maps to `updateWordlist("custom/personal", {add_words:[word]})` (NO `/api/wordlists/personal/*` — doesn't exist). No per-word scoring UI (unsupported — M2).
- [ ] **Step 2: TDD ClueListPanel** — enumerates slots via `useGridGeometry.allSlots()` + numbering; clue survives renumber when slot identity stable; clues persist in the save-machine doc.
- [ ] **Step 3: Restyle Import/Export panels; remove nothing functional; scrub check on ported markup (the bundle's fake "Recent imports"/"Publish" rows are never ported — decorative fiction).**
- [ ] **Step 4: Suite green; commit** — `feat(panels): wordlists/clues/grid-edit panels on real contracts`

---

## Phase 3 — pause → edit → resume restore

> Canonical resume path decision (recorded): the web path is `fill --resume <state-file> --task-id <id>` matching `CLIAdapter.fill_with_resume` (cli_adapter.py:403). The standalone `crossword resume` CLI command is untouched in M1 and documented as CLI-only/legacy; web code never calls it.
>
> Algorithm mapping and all filenames/envelope shapes: see **Cross-task literals** — do not restate them; reference them.
>
> Uniform pause semantics: **trie/regex (classic CSP)** = exact-position resume (existing CSPState machinery); **repair/hybrid/beam** = graceful-stop (serialize grid + locked slots as a degenerate CSPState with empty domains; resume seeds a fresh fill from the merged grid with user edits + theme entries locked). One UI, honest labels.

### Task 13: CLI — `fill --task-id/--state-dir/--pause-flag-dir` + pause hooks for all web algorithms

**Files:**
- Modify: `cli/src/cli.py` (fill command, cli.py:105-614), `cli/src/fill/iterative_repair.py`, `cli/src/fill/autofill.py` (two-line change: `was_paused` flag)
- No changes needed (verified 2026-07-12): `pause_controller.py` already takes `PauseController(task_id, pause_dir=None)` (pause_controller.py:24, mkdirs any dir); `state_manager.py` already takes `StateManager(storage_dir=None)` (state_manager.py:118-129); `Autofill.__init__` already accepts `pause_controller` + `state_manager` injection (autofill.py:59-60) and `fill()` accepts `task_id` (autofill.py:122).
- Test: `cli/tests/test_fill_pause_resume.py` (create)

**Interfaces:**
- Produces (CLI options on `fill`): `--task-id TEXT` (enables pause polling + state saving), `--state-dir PATH` (default keeps `/tmp/crossword_states`), `--pause-flag-dir PATH` (default keeps current `/tmp`). With `--task-id`: construct `PauseController(task_id, pause_dir=Path(pause_flag_dir))` and `StateManager(storage_dir=Path(state_dir))` and pass BOTH into the `Autofill(...)` constructor call at cli.py:396, plus `task_id=` into `fill()`.
- **Pause detection (CSP path — verified):** `_backtrack_with_mac` checks `should_pause()` at autofill.py:853, `_handle_pause` saves state + emits the stderr `paused` progress event (autofill.py:1140-1182, save at :1173), then autofill.py:855 raises `PausedException` (defined pause_controller.py:121) — **which `Autofill.fill()` swallows internally at autofill.py:193 (and `_resume_fill` at :247), returning `FillResult(success=False)`. The CLI can NOT catch it.** Add `self.was_paused = True` in those two except blocks; the fill command checks `autofill.was_paused` after `fill()` returns.
- Produces (pause exit): when pause is detected (`was_paused` for CSP; the graceful-stop return for repair/beam), the command prints the **paused stdout protocol** (Cross-task literals) and exits 0. The stderr `paused` progress event is already emitted by `_handle_pause`; the repair/beam path emits its own equivalent line.
- Produces (repair/hybrid/beam): `iterative_repair` gains an optional `pause_controller` checked at TWO points (verified insertion sites): the restart loop `for restart in range(max_restarts):` at iterative_repair.py:215 (beside the existing `elapsed > timeout * 0.95` break at :216-218) and — for responsive pausing, since a region attempt can run tens of seconds — the conflict-repair loop `while conflicts:` at :418 (beside its per-iteration timeout check at :419-421). On pause it stops gracefully returning the current best grid; the fill command serializes the **degenerate CSPState** (Cross-task literals: 11 required fields, `domains={}`, `locked_slots` = theme entries ∪ user-filled slots, `grid_dict` = current grid, `metadata={"algorithm": "<flag value>"}`). Hybrid reuses the repair hook in its repair phase; beam reuses its existing orchestrator pause polling but routes the save through the same degenerate-CSPState writer (its native beam-state save stays unused by web).

- [ ] **Step 1: Write failing CLI tests** in `cli/tests/test_fill_pause_resume.py`. Three tests:

*Test A — options accepted:* run `fill` on a blank 5×5 grid file (subprocess, `--allow-nonstandard --json-output`, `-t 15`, `--algorithm trie`) with all three new options pointing into tmp_path; assert exit 0.

*Test B — CSP pause saves state:* start `fill` as a subprocess on a **blank 15×15** grid (`--algorithm trie`, `-t 120` — the size and timeout matter: the fill must still be running at t+3 s when the flag lands, or the test flakes), `sleep(3)`, then touch the pause flag file (name per Cross-task literals) in the test's flag dir; `communicate(timeout=60)`. Assert: exit 0; stdout parses to the paused stdout protocol (`paused: true`); the state file exists in the test's state dir; the gunzipped payload has `algorithm == "csp"` (state FORMAT, not the flag) and non-empty `state_data["domains"]`.

*Test C — repair pause saves degenerate state:* same shape as B with `--algorithm repair`; assert `state_data["domains"] == {}` and `metadata["algorithm"] == "repair"`.

- [ ] **Step 2: Run** `pytest cli/tests/test_fill_pause_resume.py -x -v` — Expected: FAIL with `no such option: --task-id`.
- [ ] **Step 3: Implement.** Read the fill command (cli.py:105-614) first; add the three Click options. CSP path: inject `PauseController`/`StateManager` at the cli.py:396 construction, pass `task_id=` to `fill()`, add `was_paused` in the two except blocks, check it after `fill()` returns → paused exit protocol (do NOT try to catch `PausedException` in the command — it never propagates out of `Autofill.fill()`). Repair/hybrid/beam path: add the `should_pause()` checks at iterative_repair.py:215 and :418; on pause write the degenerate CSPState and follow the same exit protocol.
- [ ] **Step 4: Run cli tests — Expected: PASS. Full `pytest cli/tests/` green.**
- [ ] **Step 5: Commit** — `feat(cli): fill --task-id/--state-dir/--pause-flag-dir with pause for csp+repair+beam`

---

### Task 14: CLI — `fill --resume` + fix `CLIAdapter.fill_with_resume`

**Files:**
- Modify: `cli/src/cli.py` (fill command), `backend/core/cli_adapter.py:403-476`
- Test: extend `cli/tests/test_fill_pause_resume.py`; `backend/tests/unit/test_cli_adapter.py` (resume method)

**Interfaces:**
- Produces (CLI): `fill --resume <state-file.json.gz>` — loads the state and dispatches on its CONTENT, not the flag: if `state_data.domains` is non-empty (a real CSPState) → `StateManager.restore_to_autofill` exact-position resume (`Autofill.fill(resume_state=…, task_id=…)` per autofill.py:115-142, runs under trie/regex classic CSP); if `domains` is empty (degenerate graceful-stop state) → seed the requested `--algorithm` from `grid_dict` with `locked_slots` locked. Resumed fills are themselves pausable (same `--task-id` plumbing).
- Produces (adapter): `fill_with_resume(state_file, task_id, options)` builds exactly `['fill', <grid_file>, '--resume', <state_file>, '--task-id', <task_id>, '--state-dir', STATE_DIR, '--pause-flag-dir', PAUSE_FLAG_DIR, …]` — flags now real; dirs imported from `backend/core/state_paths.py` (created in Task 15; if executing this task first, define the constant here and Task 15 moves it).

- [ ] **Step 1: Write the failing resume test.** Extract Test B's pause flow into a helper (`_pause_a_fill(tmp_path, algorithm, task_id)` → returns grid file + dirs). New test: pause a `trie` fill per the helper, then run `fill` again with `--resume <state file>` plus a fresh `--task-id` and the same dirs, `-t 120`, subprocess `timeout=180`. Assert: exit 0; stdout parses to the **fill success keys** (Cross-task literals); `result["success"] is True`; `slots_filled == total_slots`; no `"."` remains in any row of `result["grid"]`.
- [ ] **Step 2: Run — Expected: FAIL (`no such option: --resume`). Implement per Interfaces. Run — PASS.**
- [ ] **Step 3: Adapter unit test (mocked subprocess) asserting the exact argv built by `fill_with_resume` (it currently emits flags the CLI lacked and omits the dirs — fix both). Backend suite green.**
- [ ] **Step 4: Commit** — `feat(cli): fill --resume consuming saved solver state; fix fill_with_resume adapter`

---

### Task 15: Backend — `resume_task_id` through `/api/fill/with-progress` + one shared state dir

**Files:**
- Modify: `backend/api/routes.py:435` (fill_with_progress), `backend/api/routes.py:246` (run_cli_with_progress — pass task-id/dirs on EVERY fill), `backend/api/pause_resume_routes.py:26`, `backend/core/cli_adapter.py`
- Create: `backend/core/state_paths.py`; Test: `backend/tests/unit/test_fill_resume_route.py`

**Interfaces:**
- Produces: `backend/core/state_paths.py` per Cross-task literals — imported by pause_resume_routes, routes.py, and cli_adapter (no more split defaults). `pause_autofill` must construct `PauseController(task_id, PAUSE_FLAG_DIR)`.
- Produces: `POST /api/fill/with-progress` accepts optional `resume_task_id`; when present, the spawned command is the Task 14 resume argv (state file per Cross-task literals; 404 envelope `TASK_NOT_FOUND` if missing). ALL web fills (fresh or resumed) now pass `--task-id <task_id> --state-dir --pause-flag-dir`, making every web fill pausable.
- Produces (SSE): a stderr `{"status":"paused"}` line passes through to SSE verbatim (verified: routes.py:305-307 downgrades only `complete`/`error` stderr statuses to `running` and forwards everything; `paused` is untouched). The exit-code-0 handler currently parses stdout and always emits a final `complete` — this task must branch: if stdout is the paused protocol (`{"paused": true, ...}`), end the stream after the paused event WITHOUT emitting `complete`.

- [ ] **Step 1: Failing route tests (mock subprocess).** Must assert: (a) fresh fill argv contains `--task-id <uuid> --state-dir … --pause-flag-dir …`; (b) `resume_task_id` present + state file exists → argv contains `--resume <state path>`; (c) missing state file → 404 `{error:{code:"TASK_NOT_FOUND"}}`; (d) with a fake Popen scripted to emit a stderr `paused` line then a paused-protocol stdout, the progress queue receives the `paused` event and NO `complete` event follows.
- [ ] **Step 2: Implement.**
- [ ] **Step 3: Backend suite green; commit** — `feat(api): resume_task_id on fill/with-progress; unified state/flag dirs`

---

### Task 16: F11 + F14 — frontend pausing sub-state and two-step resume

**Files:**
- Modify: `src/hooks/useAutofillMachine.js`, `src/components/bench/AutofillPanel.jsx`, `src/api/client.js` (startFill gains `resumeTaskId` → `resume_task_id`), tests

**Interfaces:**
- Consumes: Tasks 13–15 backend; machine internals from Task 11.
- Produces: Pause button → `api.pauseFill(taskId)` → sub-state `running.pausing` (button disabled, label "pausing…"); transition to `paused{taskId, progress, stateInfo}` on SSE `status:"paused"` **or** a one-shot `getFillState` 200 fallback poll at 5 s; 10 s without either → back to `running` + toast. Resume button → `api.resumeFill({taskId, editedGrid: toCliStrings(currentGrid), options})` → on 200 `api.startFill({...options, resumeTaskId: new_task_id})` → running with new task id (submitting state reused between the two calls). Old state file deleted only after the resumed run reaches done/failed (`api.deleteFillState(originalTaskId)` fired from those transitions).

- [ ] **Step 1: TDD the machine transitions** (fake timers + MockEventSource): pause→pausing→(SSE paused)→paused; pausing timeout → running + toast; resume happy path issues the two calls in order and carries `new_task_id`; failure of either call returns to `paused` (never `failed`).
- [ ] **Step 2: Implement; grid editing is enabled ONLY in `idle` and `paused` (App locks `onSetLetter/onToggleBlack` otherwise — F13 invariant, enforce now).**
- [ ] **Step 3: Suite green; commit** — `feat(autofill): confirmed pause + two-step resume consuming solver state (F11,F14)`

---

### Task 17: F12 + F13 — saved-state discovery + live edit preview

**Files:**
- Create: `src/components/bench/ResumeCard.jsx`, tests
- Modify: `src/hooks/useAutofillMachine.js`, `src/App.jsx`

**Interfaces:**
- Consumes: `api.listFillStates`, `api.getFillState`, `api.editSummary`.
- Produces: on app mount, `listFillStates(7)` → resume card per state (`slots_filled/total_slots`, age, algorithm); selecting one loads `getFillState` and offers "Load grid & resume" (hydrates grid from `grid_preview` via `fromCliStrings`, enters `paused{taskId}` — restore entry amendment). While `paused`, every grid mutation debounced 400 ms into `editSummary({taskId, editedGrid})`; render filled/emptied/modified counts + `new_words`/`removed_words` chips; previous summary stays visible during flight (no spinner). localStorage task-id hints removed entirely — server is the source of truth.

- [ ] **Step 1: TDD:** mount fetch renders cards; restore hydrates grid + paused state with NO EventSource open (amendment 2); edit in paused triggers debounced summary; summary error → chip area keeps last + small inline note (NOT a toast per keystroke).
- [ ] **Step 2: Implement; delete `paused_autofill_task`/`current_autofill_task` localStorage code paths.**
- [ ] **Step 3: Suite green; commit** — `feat(autofill): server-side paused-state discovery + live edit summary (F12,F13)`

---

### Task 18: F15 + F16 — 409 recovery, honest discard/cancel, boot cleanup

**Files:**
- Modify: `src/hooks/useAutofillMachine.js`, `src/components/bench/ResumeCard.jsx`, `src/App.jsx`, tests

**Interfaces:**
- Consumes: `api.resumeFill` 409 path, `api.deleteFillState`, `api.cancelFill`, `api.getFillState`, `api.cleanupFillStates`.
- Produces: **409 recovery:** parse `details` for `(row,col) direction` tokens (regex `/\((\d+),\s*(\d+)\)\s+(across|down)/g` — EditMerger formats offending slots that way, edit_merger.py:350-362), mark those slots' cells `isError`, keep the resume card open with an inline conflict banner, Resume stays enabled for retry — self-transition `paused → paused{conflict}` (never `failed`). **Discard:** in-app confirm (xw-styled, not `window.confirm`) → `deleteFillState` → idle. **Cancel (running):** `cancelFill`, treat `state_saved` as unverified — probe `getFillState` once; on 200 show passive "saved state available" affordance in idle (feeds the F12 list), else plain idle. **Boot:** `cleanupFillStates(7)` fired once on app mount (after the F12 list loads, so the list shows only fresh states).

- [ ] **Step 1: TDD each flow** (409 parse incl. multi-slot details; discard confirm; cancel probe 200 vs 404; cleanup called once).
- [ ] **Step 2: Implement. Suite green; commit** — `feat(autofill): conflict recovery + honest cancel/discard semantics (F15,F16)`

---

### Task 19: E2E gate — real-subprocess pause→edit→resume + pattern through Flask

**Files:**
- Create: `backend/tests/integration/test_pause_resume_e2e.py`

**Interfaces:**
- Produces: the batch gate proving the wiring with ZERO mocks. Marked `@pytest.mark.slow`. **Meta-rule: if this fails, fix Tasks 13–15 — never weaken the test.**

- [ ] **Step 1: Write the two tests** (the executing agent writes the pytest; the scenario below is binding):

*Test 1 — pause→edit→resume roundtrip* (Flask test client, `create_app(testing=True)`, blank 15×15 grid, `algorithm: "trie"` — classic CSP, the exact-position path, `timeout: 120`):
1. `POST /api/fill/with-progress` → assert 202, capture `task_id`.
2. Sleep 3 s (fill must still be running), then `POST /api/fill/pause/<task_id>` → assert 200.
3. Poll `GET /api/fill/state/<task_id>` up to **10 s** (this deadline IS the F11 guarantee — the pausing sub-state's timeout) → assert a 200 arrives; capture the state body.
4. Use the state's `grid_preview` **unmodified** as `edited_grid` (keeps the gate deterministic) in `POST /api/fill/resume {task_id, edited_grid}` → assert 200, capture `new_task_id`.
5. `POST /api/fill/with-progress` again with the same grid + `resume_task_id: new_task_id` → assert 202.

*Test 2 — pattern through Flask, no mocks:* `POST /api/pattern {pattern: "C?T", wordlists: ["comprehensive"]}` → assert 200, non-empty `results`, first result has `word` and `source`.

- [ ] **Step 2: Run** `pytest backend/tests/integration/test_pause_resume_e2e.py -m slow -v` — Expected: PASS. Debug Tasks 13–15 until it does (systematic-debugging, not test-weakening).
- [ ] **Step 3: Commit** — `test(e2e): real-subprocess pause→edit→resume gate`

---

## Phase 4 — Assisted construction (F6, F7, B7)

### Task 20: F6 — suggest-black with server-verdict slot + diff overlay

**Files:**
- Modify: `cli/src/core/constraint_analyzer.py` (~lines 29-93), `src/components/bench/AutofillPanel.jsx`
- Create: `src/components/bench/BlackSquareOverlay.jsx`, tests both sides
- Delete: `src/components/BlackSquareSuggestions.jsx` + tests (**disposition:** *rewrite* — modal becomes overlay; endpoint tests ported); delete old `findMostConstrainedSlot` client heuristic (policy violation)

**Interfaces:**
- Produces (CLI, ~10 lines): `analyze` output gains `"slots": [{row, col, direction, length, candidate_count}]` and `"most_constrained_slot": {row, col, direction, length, candidate_count}` derived from the existing `slot_counts` dict (constraint_analyzer.py:29-34). Passes through `/api/constraints` verbatim (no route change).
- Produces (GUI): "Suggest black square" → `api.getConstraints` → take `most_constrained_slot` → `api.suggestBlackSquare({grid, problematicSlot, gridSize})` → render proposed cells as a temporary diff overlay on CrosswordGrid (accent-colored ghost squares + rationale line); Apply → `api.applyBlackSquares({grid, primary, symmetric})` replaces grid + renumber (Task 8 hook fires); Dismiss → overlay clears.

- [ ] **Step 1: CLI TDD:** failing test in `cli/tests/` asserting `analyze --json-output` includes `most_constrained_slot` with the 5 fields on a seeded grid; implement; cli suite green.
- [ ] **Step 2: GUI TDD:** button → two API calls chained with the server slot (assert NO local slot computation); overlay renders `suggestions[0]` cells; apply posts and grid updates; empty suggestions → toast "no viable placements".
- [ ] **Step 3: Suites green; commit** — `feat(construct): server-verdict suggest-black with diff overlay (F6)`

---

### Task 21: F7 — theme placement picker

**Files:**
- Create: `src/components/bench/ThemeWordsPanel.jsx`, tests
- Delete: old `src/components/ThemeWordsPanel.jsx` + tests (**disposition:** endpoint tests *ported* — same three real endpoints; apply-all loop logic ported as-is)

**Interfaces:**
- Consumes: `api.themeUpload/themeValidate/themeSuggestPlacements/themeApplyPlacement`, `api.normalize` for entry normalization on add.
- Produces: bench-styled panel (bundle `panels.jsx:511-536` markup): add entry (validated via `themeValidate` — inline error below field on invalid), upload .txt (JSON `content`, not multipart), "Place" → `themeSuggestPlacements` renders candidate slots as clickable ghost previews on the grid (score + reasoning tooltip); user picks one → `themeApplyPlacement` → grid replace + isThemeLocked cells render lock markers; conflicts (400 `applied:false`) → inline conflict list. **No default theme entries seeded** (the bundle's seed set is on the scrub list).

- [ ] **Step 1: TDD:** add→validate inline error path; place→suggestions render; pick→apply→locked cells; conflict response → inline list; upload path.
- [ ] **Step 2: Implement; suite green; commit** — `feat(theme): placement suggestion picker on real endpoints (F7)`

---

### Task 22: B7 — constraint heatmap on real data

**Files:**
- Modify: `src/components/bench/CrosswordGrid.jsx` (heatmap prop already ported), `src/App.jsx` or `src/hooks/useHeatmap.js` (create), ToolRail VIEW toggle
- Re-enable: the `describe.skip` heatmap tests from Task 5 (ported to the new data flow)

**Interfaces:**
- Consumes: `api.getConstraints` (`constraints` per-cell `{across_options, down_options, min_options}`).
- Produces: `useHeatmap(grid, enabled)` — debounced 500 ms on grid change while enabled (port timing from old GridEditor.jsx:36-75); maps `min_options` to the grid's tension shading; keeps previous heatmap during flight; disables + clears when toggled off or offline.

- [ ] **Step 1: TDD (port + adapt the skipped tests); implement; suite green; commit** — `feat(grid): crossing-quality heatmap wired to /api/constraints (B7)`

---

## Phase 5 — Acceptance

### Task 23: M1 acceptance gate

**Files:**
- Modify: `.claude/CLAUDE.md` (status line + working-features list), this plan (check off)
- Create: `docs/dev/M1_ACCEPTANCE.md` (the checklist below, with results)

- [ ] **Step 1: Full suites:** `pytest` (default set green; count recorded), `pytest -m slow` (E2E green), `npx vitest run` (green), `npm run build` (clean).
- [ ] **Step 2: Legacy sweep:** delete any now-unused legacy components/SCSS (grep imports); `grep -rn "window.confirm\|alert(" src/` → empty; `grep -rn "axios" src/` → empty; guard hook still passes.
- [ ] **Step 3: Scripted manual smoke (record pass/fail per line in M1_ACCEPTANCE.md):**
  1. Boot with backend down → red dot, Start/Verify/Clean disabled with tooltips, pattern banner.
  2. Backend up → dot green within 30 s.
  3. Draw a 15×15 skeleton: numbers reconcile after each black toggle; `grid_info` stats update; typing never blocks.
  4. Focused-cell inspector: candidates < 500 ms, previous results persist during typing, source badge shows.
  5. Verify → flagged chips + red cells; Clean → invalid cleared, valid crossings intact; banner rules per 06 §2.
  6. Autofill (repair) on a fresh 15×15: SSE progress bar, no spinner; complete replaces grid once.
  7. **Pause (repair) mid-fill → paused card within 10 s; edit two cells; edit-summary chips update; Resume → completes with edits intact and locked.**
  8. **Pause (trie = classic CSP) mid-fill → resume → iteration count continues (exact-position, check `/api/fill/state` before resume).**
  9. Force a 409 (fill a slot with a non-word while paused) → inline conflict cells + banner; fix → resume succeeds.
  10. Reload mid-pause → resume card appears from server list (no localStorage).
  11. Cancel a running fill → probe result honest ("saved state available" only if state exists).
  12. Suggest black square → overlay → apply → renumber.
  13. Theme: add, place via picker, locked cells survive autofill.
  14. Dark mode toggle: both themes complete (no unstyled panels); reload persists.
  15. Save: edit → "unsaved changes" → 30 s → "saved locally · just now"; reload restores.
  16. Latency notes: `/api/number` and `/api/pattern` round-trips recorded (info only; <80 ms budget is documented-deviation).
- [ ] **Step 4: Error-model conformance audit:** every failure path observed lands in one of the four surfaces (walk each panel with backend stopped, then with a 500-injecting mock if needed).
- [ ] **Step 5: Update `.claude/CLAUDE.md` (status + features), commit** — `docs: M1 acceptance record + status`. Then run `/handoff-distill` (four pending [DISTILL] markers + this plan's recorded decisions).

---

## Self-review record (author)

- **Format:** rewritten 2026-07-12 to Arthur's plan convention — signatures/contracts/checklists only; executing agents write all code. Advisor-verified that every decision formerly expressed only in code blocks survives in prose (error-normalization rules → Task 2; guard semantics → Task 1; state envelope + test tuning → Cross-task literals + Task 13; verified output keys → Cross-task literals).
- **Spec coverage:** F1 (T9), F2 (T8), F3 (T11), F4 (T11+T16 — cancel in 11, pause/resume in 16), F5 (T10), F6 (T20), F7 (T21), F9/F10 (T7, local-transport variant), F11–F16 (T16–T18), B7 (T22); F8/B1/B2/B3/B4/B5/B6/B8 explicitly deferred (Global Constraints). Shell/design system: T4–T6, T12. Plumbing: T13–T15, gate T19.
- **Known simplifications (deliberate):** no bundled offline wordlist fallback (deviation from spec 01 §40 — recorded); spec's `/api/number <80ms` budget accepted as unmeetable; beam exact-state resume deferred (uniform graceful-stop semantics instead); `prefer_personal` UI omitted until B5.
- **Consistency rule:** every cross-task literal lives ONLY in §Cross-task literals; the api-client signatures live ONLY in Task 2's Interfaces block. Tasks reference, never restate.
