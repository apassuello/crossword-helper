# Crossword Helper — Architecture

**Version 2.0.0**

## AI READING INSTRUCTION
Read `[SPEC]` and `[BUG]` blocks for authoritative facts.
Read `[NOTE]` only if additional context is needed.
`[?]` blocks are unverified.

---

## Scope

**[NOTE]**
This document explains how the three components fit together — the CLI-as-single-source-of-truth
data flow, why the subprocess seam exists, where state lives, and the structure of pause/resume.
It deliberately does not catalog CLI flags, API endpoints, or test counts: those are derivable
facts that go stale the moment this file is hand-edited, so they live in the canonical docs below
instead.

| For | See |
|---|---|
| Every CLI command and its flags | [docs/specs/CLI_SPEC.md](specs/CLI_SPEC.md) |
| Every HTTP endpoint | [docs/api/openapi.yaml](api/openapi.yaml), [docs/api/API_REFERENCE.md](api/API_REFERENCE.md) |
| Autofill algorithm internals | [docs/ALGORITHM_DEEP_DIVE.md](ALGORITHM_DEEP_DIVE.md) |
| Current test count / pass rate | run `pytest --collect-only -q` |
| Test coverage | run `pytest --cov=backend --cov=cli --cov-report=term` |

---

## 1. System Overview

**[SPEC]**
Three components, one direction of authority:

```
React Frontend (src/)
    │  HTTP + Server-Sent Events
    ▼
Flask Backend (backend/)
    │  subprocess.run()
    ▼
CLI Tool (cli/src/)
    │
    ▼
Core algorithms (NumPy grid, pattern matching, CSP/Beam/Hybrid autofill)
```

- Frontend: React 18 + Vite, talks to the backend over REST and SSE.
- Backend: Flask 3.0, 7 blueprints under `backend/api/` (`routes`, `grid_routes`,
  `theme_routes`, `pause_resume_routes`, `wordlist_routes`, `progress_routes`,
  `constraint_routes`). No business logic — every blueprint delegates to `CLIAdapter`.
- CLI: `cli/src/cli.py`, single source of truth for grid, autofill, pattern-matching, and
  export logic. Runnable standalone or invoked as a subprocess by the backend.

**[NOTE]**
The frontend and CLI never talk to each other directly, and the backend never re-implements
crossword logic — it only translates HTTP requests into CLI subprocess calls and CLI JSON output
into HTTP responses. This is the one architectural rule everything else in this document exists
to support.

---

## 2. Why CLI-as-Single-Source-of-Truth

**[SPEC]**
Decision: put all crossword logic in the CLI; the web backend is a thin HTTP wrapper around
`subprocess.run()` calls into it.

Rationale:
- One implementation serves both the web UI and direct CLI usage — no duplicated grid/autofill/
  pattern-matching code between backend and CLI.
- The CLI is independently testable and independently usable (a constructor can drive it without
  ever starting Flask).
- The integration seam is a single file: `backend/core/cli_adapter.py`.

Trade-offs accepted:
- Per-request subprocess overhead (process spawn + interpreter startup + JSON marshalling).
  Not measured here — see the "Performance" note below for how to measure it if it matters to you.
- Errors cross a process boundary: CLI stderr must be parsed and mapped to HTTP status codes.
- Grid state must stay JSON-serializable.

Alternative considered and rejected: importing CLI modules directly into Flask. Rejected because
it would couple backend and CLI code paths and make the CLI's correctness depend on Flask being
importable, defeating "CLI as standalone tool."

**[NOTE]**
Why the trade-off is acceptable: autofill runtime is dominated by the search itself, not by
process startup — spawn overhead is noise next to it. Pattern and numbering calls are cheap
either way. If this project ever needed high request throughput (many concurrent users hitting
`/api/pattern`), the subprocess-per-request model would need revisiting — see §6.

---

## 3. CLIAdapter — the integration bridge

**[SPEC]**
Location: `backend/core/cli_adapter.py`.

Responsibilities:
- Build the CLI argv, run it via `subprocess.run()` (never `shell=True`).
- Enforce a timeout per call.
- Parse CLI stdout as JSON; parse CLI stderr into an HTTP-appropriate error on failure.

`CLIAdapter`'s own methods (`pattern()`, `number()`, `normalize()`, `fill()`,
`fill_with_resume()`, …) are synchronous — each blocks until the subprocess exits. See
[docs/specs/CLI_SPEC.md](specs/CLI_SPEC.md) for the authoritative flag-by-flag CLI reference —
do not treat any command list in this file as complete.

The SSE-progress-tracked endpoints (`/api/fill/with-progress`, `/api/pattern/with-progress`) do
**not** go through `CLIAdapter`'s blocking methods. `backend/api/routes.py` builds its own argv,
takes only the CLI executable path from `cli_adapter.cli_path`, and drives the subprocess itself
with `subprocess.Popen` on a background thread — see §6.1 for why.

**[NOTE]**
`CLIAdapter` is the integration seam for request/response style calls: if the CLI's argv shape or
JSON schema changes, this is the one file that needs to change for those calls. The progress-
streaming path is a second, parallel seam that exists because streaming a running subprocess's
output doesn't fit a call-and-block method signature — see §6.1.

---

## 4. Autofill algorithms

**[SPEC]**
Location: `cli/src/fill/`. Three strategies, selectable via `--algorithm`:

| Algorithm | File | Best for |
|---|---|---|
| CSP + backtracking (AC-3, MAC, MCV/LCV heuristics) | `autofill.py` | Small grids, guaranteed completeness |
| Beam Search | `beam_search/orchestrator.py` | Medium/large grids, better word quality, no completeness guarantee |
| Hybrid | `hybrid_autofill.py` | Beam Search first, then Iterative Repair |

Iterative Repair (`iterative_repair.py`) is Hybrid's second phase: region-based conflict
detection plus tabu search, used to fix crossing mismatches Beam Search leaves behind.

Adaptive Autofill (`adaptive_autofill.py`) wraps any of the above, detects stalled fills, and
calls `BlackSquareSuggester` to propose black-square placements that unstick them.

### Beam Search package

**[SPEC]**
```
beam_search/
├── orchestrator.py          BeamSearchOrchestrator — composes everything below
├── state.py                 BeamState
├── beam/
│   ├── diversity.py          DiversityManager (Diverse Beam Search)
│   └── manager.py            BeamManager (expansion/pruning)
├── selection/
│   ├── slot_selector.py      MRVSlotSelector
│   └── value_ordering.py     CompositeValueOrdering, LCVValueOrdering,
│                              StratifiedValueOrdering, ThemeWordPriorityOrdering,
│                              ThresholdDiverseOrdering
├── evaluation/
│   └── state_evaluator.py    StateEvaluator
└── utils/
    └── slot_utils.py          SlotIntersectionHelper
```
Confirmed by reading `orchestrator.py`'s import block directly. There is no `constraints/`
package and no `memory/` package under `beam_search/` (the `constraints/` directory that remains
on disk holds only a stale `__pycache__`, no source).

**[NOTE]**
A prior version of this document additionally listed a `MACConstraintEngine`
(`constraints/engine.py`) and a `memory/domain_manager.py` / `grid_snapshot.py` / `pools.py` trio
as active components of the orchestrator. None of that exists in the shipped tree — it read as
either leaked refactor-planning notes or stale documentation. Deleted rather than corrected;
see the changelog.

**[NOTE]**
For the algorithmic detail behind MCV/LCV, AC-3, the beam's risk-scoring, and tabu search tenure —
see [docs/ALGORITHM_DEEP_DIVE.md](ALGORITHM_DEEP_DIVE.md). This document only needs to establish
*which module owns which responsibility*, not how each heuristic scores a candidate.

---

## 5. Pattern matching

**[SPEC]**
`cli/src/fill/`: a regex matcher (`pattern_matcher.py`, simple baseline) and a trie matcher
(`trie_pattern_matcher.py` + `word_trie.py`, length-indexed tries with score-bound pruning,
default for autofill). Both accept `?` as a single-letter wildcard.

---

## 6. Data flow

### 6.1 Autofill request (progress-tracked path)

**[SPEC]**
The frontend's autofill flow uses `/api/fill/with-progress`, not the plain synchronous
`/api/fill`:

1. Frontend POSTs grid + params to `/api/fill/with-progress`.
2. Flask validates the request, resolves wordlist paths, creates a `task_id` (in-process progress
   queue), and starts a background thread — it does **not** call a blocking `CLIAdapter` method.
3. That thread spawns `crossword fill ...` via `subprocess.Popen` with `stdout` and `stderr`
   piped, and reads `stderr` line by line as the process runs.
4. The CLI's `ProgressReporter` (`cli/src/core/progress.py`) writes one JSON progress event per
   line to **stderr** as it works; it never writes progress to a file. The reading thread parses
   each line and pushes it into the task's in-process queue.
5. `progress_routes.py`'s SSE endpoint streams that queue to the frontend — no file is tailed;
   the queue is in-memory and lives only as long as the Flask process.
6. When the subprocess exits, the thread reads the *final* result (filled grid, or unfillable-
   slot errors, or a paused-state marker) from **stdout** — kept separate from the stderr
   progress stream specifically so a terminal-looking progress event doesn't get mistaken for the
   real result before it arrives.

**[NOTE]**
This is a second integration seam alongside `CLIAdapter` (§3), not a variant of it: streaming a
running subprocess's line-by-line output doesn't fit `CLIAdapter`'s call-and-block method shape,
so `routes.py` drives `Popen` directly instead. `CLIAdapter.fill()` (blocking, no progress) still
exists and is used by callers that don't need streaming updates.

### 6.2 Pause/resume

**[SPEC]**
This is the one piece of state management worth documenting structurally, because it crosses
the process boundary twice.

1. **Pause:** backend writes a signal file. The CLI subprocess polls for it between iterations
   (rate-limited, not checked every iteration) and, on detecting it, serializes its complete
   in-memory state — grid, algorithm position (backtrack stack or beam), remaining candidate
   domains, constraint-propagation state, iteration count — to gzip-compressed JSON, then exits
   with a "paused" status.
2. **Edit:** the user edits the grid client-side while the process is gone. No process is running
   during this window — the paused state lives entirely on disk.
3. **Resume:** the backend's `EditMerger` validates the user's edits against the puzzle's
   constraints (re-running arc-consistency to check they're still solvable) before resuming.
   The resume path runs a *new* `crossword fill --resume <state_path> --task-id <id>` subprocess
   (same `fill` command, not a separate `resume` invocation), which deserializes the saved state,
   applies the validated edits, locks the edited cells (treated like theme entries — the
   algorithm will not overwrite them), and continues from the exact algorithmic position it
   paused at, under a fresh timeout window.

**[NOTE]**
Why file-based IPC instead of in-memory state + threads: the CLI subprocess is a genuinely
separate OS process, or the pause signal would compete with the fill loop for the GIL and add
threading-correctness risk to a batch algorithm that was not written to be interrupted safely
mid-mutation. File-based signaling also means paused state survives a backend restart or a
browser refresh, and can be inspected directly for debugging.

### 6.3 Theme-entry locking

**[SPEC]**
Theme entries are cells locked before autofill starts (as opposed to pause/resume locks, which
happen mid-fill). Slots that intersect a locked entry are constrained to patterns compatible
with the locked letters before the algorithm ever tries to fill them; the algorithm itself never
overwrites a theme-entry slot.

---

## 7. Key decisions

**[SPEC]**

| Decision | Chose | Rejected | Why |
|---|---|---|---|
| Backend framework | Flask (sync) | FastAPI (async) | The backend's I/O is a blocking subprocess call either way — async buys nothing here, and Flask's blueprint model is simpler for this shape of app. |
| Frontend framework | React | Vanilla JS | Grid editor state (keyboard nav, symmetry enforcement, theme locking, SSE-driven progress) outgrew a vanilla-JS component model early. |
| Grid representation | NumPy 2D array | Python nested lists | Vectorized symmetry checks (180° rotation via `np.rot90`) and repeated cell access are both meaningfully faster and simpler to express. |
| Backend↔CLI integration | `subprocess.run()`, no `shell=True`, array argv | Direct Python import of CLI modules | Keeps the CLI a genuinely standalone tool and avoids coupling backend and CLI import graphs; array argv avoids shell-injection risk entirely rather than sanitizing against it. |
| Persistence | Flat JSON / gzipped JSON files | A database | Single-user, local-only tool; file-based state is simpler to inspect, version, and back up, and there is no concurrent-writer problem to solve. |
| Default autofill algorithm | Iterative Repair (`--algorithm` default is `repair`) | Beam Search alone / CSP alone | Beam Search finds a high-quality partial fill quickly but has no completeness guarantee; Iterative Repair spends the remainder of the timeout resolving the crossing conflicts Beam Search leaves behind. |

---

## 8. Security posture

**[SPEC]**
Threat model: localhost-only, trusted single/dual user, no internet exposure, no multi-tenant
auth, no database (so no SQL injection surface).

Subprocess safety:
- Argv is always an array, never a shell string — `subprocess.run(['crossword', 'pattern', ...])`,
  never `shell=True`. This eliminates shell injection structurally rather than by sanitizing input.
- Every subprocess call has a timeout.
- CLI executable path is fixed by the application, never user-controlled.

Input validation lives in `backend/api/validators.py` — pattern length/charset limits, grid size
bounds, wordlist upload extension/size checks. See that file directly for current limits; treat
any number quoted for them here as unverified.

**[?]**
Whether CORS origins, upload size caps, or other specific limits in `validators.py` match what a
prior version of this document claimed was not re-verified line-by-line for this rewrite — read
`backend/api/validators.py` and `backend/app.py` directly rather than trusting a transcribed number.

---

## 9. Performance

**[NOTE]**
Prior versions of this document quoted specific millisecond and megabyte figures for subprocess
overhead, autofill duration by grid size, memory usage, and disk I/O, with no benchmark script or
date attached. None of those numbers could be re-verified from the current codebase and are
deleted rather than carried forward. If you need current numbers:

- Subprocess/API latency: time a request against a running `python run.py`.
- Autofill duration by grid size and algorithm: run `crossword fill` with `--json-output` and
  read the reported timing/iteration fields, or use `cli/src/core/progress.py`'s output directly.
- Memory: profile the running process (e.g. `psutil`) rather than trusting a static figure here —
  memory scales with wordlist size, beam width, and grid size, all of which are runtime choices.

---

## 10. Deployment

**[SPEC]**
Current: local-only. `python run.py` serves the built frontend (after `npm run build`) on
`localhost:5000`; `npm run dev` gives hot-reload on `localhost:3000` proxying API calls to 5000.
See the Quick Start in [CLAUDE.md](../.claude/CLAUDE.md) for exact commands.

**[NOTE]**
A previous version of this document listed backend configuration environment variables
(`SUBPROCESS_TIMEOUT`, `CACHE_SIZE`, `WORDLIST_DIR`, `CLI_PATH`, `TEMP_DIR`, `LOG_FILE`,
`LOG_LEVEL`) as active configuration surface. `grep` across `backend/` and `run.py` for each of
these names returns no matches outside test files — none of them are actually read by the running
application. Deleted rather than corrected; if configuration by environment variable is wanted,
it does not exist yet and would need to be implemented, not documented as already there.

A cloud/production deployment topology (Nginx + Gunicorn + multi-worker Flask) was previously
described here as a future plan. No such deployment exists or is being built against; removed as
speculative content with no bearing on the current architecture.

---

## Changelog

- **2.0.0** — Rewritten to HADS format. Removed: test-count/coverage header line, the entire
  "Testing Architecture" section (fabricated per-file test counts, several cited test files do
  not exist, and it self-contradicted the document's own header count), the full CLI command
  catalog and full API endpoint catalog (both now single pointers to their canonical specs, which
  already existed and were drifting out of sync with this file), the non-existent Beam Search
  `constraints/` and `memory/` submodules, the unused environment-variable configuration table,
  the speculative cloud-deployment diagram, and all unattributed timing/memory benchmark figures.
  Verified against code: beam_search package tree, backend blueprint count (7), CLI command count
  (14, via `cli/src/cli.py`), CLIAdapter's actual methods and their synchronous/blocking nature,
  the separate `Popen`+thread progress-streaming path in `backend/api/routes.py` (progress travels
  as JSON lines over the CLI subprocess's stderr, not a polled file), the `fill --resume
  <state_path>` resume invocation (not `--resume-from`), and pause/resume's file-based IPC
  (`PauseController`, rate-limited signal checks, `/tmp/crossword_states/`).
- Prior version (pre-HADS, ~1842 lines): superseded.
