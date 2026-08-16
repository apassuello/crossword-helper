# Crossword Helper API Reference

**Version 2.0.0**

> **Base URL**: `http://localhost:5000/api` — this is a local-only tool; no other deployment exists.
> **Authoritative spec**: [`openapi.yaml`](./openapi.yaml) — endpoint list, request/response schemas, status codes.

This document is prose: what the API is for, how the pieces fit together, and the patterns
(errors, SSE, grid format) that recur across endpoints. It intentionally does not re-list
every endpoint — `openapi.yaml` is the single source of truth for that, and a second
hand-maintained list is exactly what drifted out of sync before this rewrite.

## AI READING INSTRUCTION

Read `[SPEC]` and `[BUG]` blocks for authoritative facts. Read `[NOTE]` only if additional
context is needed. `[?]` blocks are unverified — do not treat them as fact.

---

## Overview

**[NOTE]**
The backend is a thin Flask wrapper around the CLI tool (`cli/src/`). Every route ultimately
either calls `CLIAdapter` (which shells out to the CLI via `subprocess`) or, for a handful of
grid-utility endpoints (`/grid/verify-words`, `/grid/clean`, `/wordlists/*`), does the work
directly in the Flask process against the wordlist files on disk. There is no database and no
authentication layer — see [ARCHITECTURE.md](../ARCHITECTURE.md) for the full picture.

**[SPEC]**
Endpoints are grouped into these categories (see `tags` in `openapi.yaml` for the exact
membership of each):
- Core Operations — pattern search, grid numbering, entry normalization, autofill
- Grid Helpers — black square suggestions, grid validation, word verification/cleanup
- Theme Management — theme word upload, validation, placement suggestion, application
- Pause/Resume — pause, cancel, resume, and inspect saved autofill state
- Progress Tracking — SSE streaming and manual progress-tracker endpoints
- Wordlist Management — CRUD + search + import for wordlists
- Constraint Analysis — per-cell candidate-count heatmap and placement-impact analysis

To get the current, exact list of routes (method + path) straight from the code rather than
from a document that can drift:
```bash
grep -rn '@.*\.route(' backend/api/*.py
```

---

## Quick Start

**[SPEC]**
```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python run.py
# → http://localhost:5000

# Health check
curl http://localhost:5000/api/health

# Pattern search
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "?A?E"}'
```

**[SPEC]**
No authentication exists on any endpoint. `openapi.yaml`'s `security: []` reflects the code,
not a placeholder for a future scheme.

---

## Grid Data Structure

**[SPEC]**
The frontend and most endpoints exchange grids as a 2D array of cell objects:
```json
{
  "grid": [
    [
      {"letter": "", "isBlack": false},
      {"letter": "A", "isBlack": false}
    ]
  ]
}
```
Cell fields: `letter` (single uppercase char or empty), `isBlack`, `number` (nullable),
`isError`, `isHighlighted`, `isThemeLocked`. Full schema: `Cell` / `Grid` in `openapi.yaml`.

**[NOTE]**
A few endpoints (`/constraints`, `/constraints/impact`) accept either that dict form or the
CLI's plain-string form (`#` black, `.` empty, letter) — both are normalized internally by
`backend/api/validators.py::normalize_grid_to_cli`. Endpoints that build responses directly in
Flask (`/grid/verify-words`, `/grid/clean`) accept both formats too and preserve whichever one
was sent when returning the modified grid.

---

## Error Responses

**[BUG] Two incompatible error shapes are both live**
- Symptom: some endpoints return `{"error": {"code": "...", "message": "...", "details": {...}}}`
  (nested); others return `{"error": "plain string"}` (flat), optionally with a sibling
  `validation` object.
- Cause: most routes go through the shared `handle_error()` helper
  (`backend/api/errors.py`, nested shape). Constraint analysis, wordlist search, and several
  validation branches in the grid/theme routes build `jsonify(...)` directly instead (flat
  shape). Both exist in the code today, verified by reading `backend/api/*.py`.
- Fix: none applied here — this is a documentation pass, not a code change. `openapi.yaml`'s
  `Error` schema now models both shapes (`ErrorEnvelope` / `ErrorFlat`) as a `oneOf` instead of
  asserting one canonical shape. Check the specific endpoint's response schema, or the source,
  before parsing an error body positionally.

**[BUG] Every subprocess timeout returns 504, not per-endpoint codes**
- Symptom: earlier versions of this document (and of `openapi.yaml`) claimed pattern search
  timed out with `505`, normalization with `506`, and grid fill with `507` — each endpoint
  supposedly carrying its own invented status code.
- Cause: those codes were never returned by any handler. Fabricated, not stale.
- Fix: verified every `except subprocess.TimeoutExpired` branch across `backend/api/*.py` —
  every one returns `504`. Both `openapi.yaml` and this document now say `504` everywhere a
  timeout is documented. Re-verify with:
  ```bash
  grep -rn -A1 TimeoutExpired backend/api/*.py
  ```

---

## Server-Sent Events (SSE) Pattern

**[SPEC]**
Long-running operations follow a start/stream split:
1. `POST` the operation's `/with-progress` variant (e.g. `/fill/with-progress`,
   `/pattern/with-progress`) → `202 {"task_id": "...", "progress_url": "/api/progress/<id>"}`
2. `GET /progress/<task_id>` → SSE stream. Each event: `data: {"progress": 0-100, "message":
   "...", "status": "running"|"complete"|"error", "data": {...}}`. The stream closes itself on
   `complete`, `error`, or `paused`; a `: heartbeat` comment keeps idle connections alive.

**[NOTE]**
`/progress/start` and `/progress/{task_id}/update` exist as a lower-level pair for callers that
want to drive their own progress reporting instead of using a `/with-progress` endpoint (the
route docstring says "for testing"). One behavior worth knowing before you rely on it: pushing
an update for a `task_id` that was never created (or already finished) still returns
`200 {"success": true}` — the update is silently dropped rather than rejected. There is no way
to tell "delivered" from "discarded" from the response.

---

## Pause / Resume / Cancel

**[SPEC]**
There are three distinct ways to stop an in-flight autofill, verified against
`backend/api/pause_resume_routes.py`: pausing saves full algorithm state to gzipped JSON and is
resumable; cancelling hard-kills the subprocess immediately and is never resumable (no
checkpoint is written); resuming restarts a paused task, optionally merging user edits first.
Exact paths and request/response shapes: `openapi.yaml`, tag `Pause/Resume`.

Use `/fill/edit-summary` to preview what a set of user edits will change before committing to
`/fill/resume`.

---

## Constraint Analysis

**[?]**
`/constraints` and `/constraints/impact` delegate to `CLIAdapter.analyze_constraints` /
`analyze_placement_impact`, which shell out to the CLI and return whatever JSON it produces.
The route code and docstrings claim the top-level keys are `constraints`/`summary` and
`impacts`/`summary` respectively, but the actual field shapes are defined deep in the CLI, not
re-validated by the backend, and were not traced end-to-end for this rewrite. `openapi.yaml`
documents those two endpoints' response bodies as open objects (`additionalProperties: true`)
rather than asserting a shape that wasn't independently confirmed. If you need the exact
fields, trace `cli_adapter.py::analyze_constraints` into the CLI, or inspect a live response.

---

## Example Workflows

**[NOTE]**
These are illustrative curl sequences, not a substitute for `openapi.yaml`'s per-endpoint
schemas — field names should be checked there, not copied from memory.

### Pattern search → manual pick → autofill the rest
```bash
curl -X POST http://localhost:5000/api/pattern \
  -H "Content-Type: application/json" \
  -d '{"pattern": "?A?E", "max_results": 20}'

# ...update grid client-side with the chosen word...

curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{"grid": [...], "size": 15, "min_score": 30}'
```

### Theme words → placement suggestion → locked fill
```bash
curl -X POST http://localhost:5000/api/theme/upload \
  -H "Content-Type: application/json" \
  -d '{"content": "PARTNERNAME\nANNIVERSARY"}'

curl -X POST http://localhost:5000/api/theme/suggest-placements \
  -H "Content-Type: application/json" \
  -d '{"theme_words": ["PARTNERNAME", "ANNIVERSARY"], "grid_size": 15}'

curl -X POST http://localhost:5000/api/theme/apply-placement \
  -H "Content-Type: application/json" \
  -d '{"grid": [...], "placement": {"word": "PARTNERNAME", "row": 0, "col": 0, "direction": "across"}}'

# Fill with the theme entry locked (theme_entries survives the fill — see openapi.yaml AutofillRequest)
curl -X POST http://localhost:5000/api/fill \
  -H "Content-Type: application/json" \
  -d '{"grid": [...], "size": 15, "theme_entries": {"(0,0,across)": "PARTNERNAME"}}'
```

### Pause, edit, resume
```bash
curl -X POST http://localhost:5000/api/fill/with-progress \
  -H "Content-Type: application/json" -d '{"grid": [...], "size": 15}'
# → {"task_id": "abc123", "progress_url": "/api/progress/abc123"}

curl -X POST http://localhost:5000/api/fill/pause/abc123

curl http://localhost:5000/api/fill/state/abc123   # inspect saved state

# ...user edits the grid client-side...

curl -X POST http://localhost:5000/api/fill/edit-summary \
  -H "Content-Type: application/json" \
  -d '{"task_id": "abc123", "edited_grid": [...]}'

curl -X POST http://localhost:5000/api/fill/resume \
  -H "Content-Type: application/json" \
  -d '{"task_id": "abc123", "edited_grid": [...]}'
```

---

## Related Documentation

**[SPEC]**
- [`openapi.yaml`](./openapi.yaml) — authoritative endpoint, schema, and status-code reference
- [ARCHITECTURE.md](../ARCHITECTURE.md) — system architecture
- [CLI_SPEC.md](../specs/CLI_SPEC.md) — CLI command reference (the layer this API wraps)

**[?]**
A `BACKEND_SPEC.md` was referenced by earlier drafts of this document but is no longer part of
the maintained doc set — it was moved to `.archive/docs/BACKEND_SPEC.md` (commit `d3fea26`), and
a second, differently-named copy exists at `docs/archive/legacy-specs/BACKEND_SPECIFICATION.md`.
Both are archival snapshots (see the "frozen point-in-time" rule — their contents were not
re-verified for this rewrite); treat neither as current, and prefer `ARCHITECTURE.md` and this
document for anything still true today.

---

## Changelog

**[NOTE]**
- Rewrote as a HADS document. Removed the per-route endpoint table — it had independently
  drifted from both the code and from `openapi.yaml`; `openapi.yaml` is now the only place
  endpoints are enumerated.
- Added documentation for 10 endpoints that existed in code but were undocumented in
  `openapi.yaml`: `/constraints`, `/constraints/impact`, `/fill/cancel/{task_id}`,
  `/pattern/with-progress`, `/grid/verify-words`, `/grid/clean`, `/theme/validate`,
  `/wordlists/search`, `/progress/start`, `/progress/{task_id}/update`.
- Corrected the timeout status code for pattern search, normalization, and grid fill: all three
  were documented with distinct fabricated codes (`505`, `506`, `507`); the code returns `504`
  for all of them, and always has.
- Removed the `/fill/cancel/{task_id}` "not yet implemented, planned Phase 3.1" notice — the
  endpoint is implemented and working (`backend/api/pause_resume_routes.py`); the notice was
  false, not stale.
- Removed the fabricated production server URL and the `apiKey` security scheme from
  `openapi.yaml` — neither was ever built; there is no non-local deployment and no auth.
- Replaced the single flat `Error` schema (which matched no endpoint) with a `oneOf` of the two
  shapes actually returned by the code.
- Fixed the dead `BACKEND_SPEC.md` link.
