# Phase 0: Code Review Issues

> Generated 2026-03-19 by three parallel review agents (backend/CLI, frontend, integration).

---

## Blockers

### B1: Stale Closure Bug in SSE Handler
- **File:** `src/App.jsx` lines 245, 268
- **Source:** Frontend + Integration review
- **Description:** `grid.map(...)` inside SSE `onmessage` callback captures stale `grid` from `handleAutofill` closure (dependency array includes `grid` at line 340). By the time SSE events arrive, `grid` is outdated. Grid updates overwrite with stale state.
- **Fix:** Replace `grid.map(...)` with `setGrid(prevGrid => prevGrid.map(...))` functional updater at both locations.

### B2: Temp File Leak in `fill_with_progress`
- **File:** `backend/api/routes.py` lines 425-435
- **Source:** Backend + Integration review
- **Description:** `NamedTemporaryFile(delete=False)` creates grid and theme entry files. Neither the background thread (`run_cli_with_progress`) nor any error handler cleans them up.
- **Fix:** Pass temp file paths to background thread; add `finally` block with `Path(f).unlink(missing_ok=True)`.

### B3: Subprocess Not Killed on Timeout
- **File:** `backend/api/routes.py` lines 304, 329-330
- **Source:** Backend review
- **Description:** `process.communicate(timeout=...)` raises `TimeoutExpired` but handler only sends error message — does NOT terminate the process. Zombie subprocess continues consuming resources.
- **Fix:** Add `process.kill()` + `process.wait(timeout=5)` in the `TimeoutExpired` exception handler.

### B4: Zombie Subprocess on SSE Disconnect
- **File:** `backend/api/routes.py` lines 271-304, `progress_routes.py`
- **Source:** Integration review
- **Description:** When client disconnects (browser close, navigation), the background thread and subprocess continue running. `cleanup_progress_tracker()` only removes the queue, not the process.
- **Fix:** Track subprocess PID per task_id; terminate on cleanup. (Scope: nice-to-have for demo — low probability during controlled demo.)
- **Demo risk:** Low — demo operator won't disconnect mid-autofill. **Downgrade to Should-fix for demo.**

### B5: Failing Test `test_beam_only_empty_11x11`
- **File:** `backend/tests/integration/test_all_beam_scenarios.py` lines 114-130
- **Source:** Backend review
- **Description:** Beam search on empty 11×11 exceeds 40s subprocess timeout. Either algorithm is too slow or timeout too aggressive.
- **Fix:** Mark as `@pytest.mark.slow` or increase timeout to 120s.

---

## Should-Fix

### S1: isThemeLocked Not Preserved Visually After Autofill (Needs Verification)
- **File:** `src/App.jsx` lines 243-278
- **Source:** Integration review
- **Description:** SSE returns string grid `["A","#","."]`. The spread `{...cell, letter: cliCell}` should preserve `isThemeLocked` since it spreads the existing cell. **However**, need to verify this actually works — the spread is on the *previous* cell object, so `isThemeLocked` should survive. This is related to B1 (stale closure) — if stale grid is used, the wrong cells get spread.
- **Verdict:** Fixing B1 likely fixes this. Verify after B1 fix.

### S2: Redundant Fill Implementations (CLIAdapter.fill vs SSE path)
- **File:** `backend/api/routes.py` lines 175-242 vs 383-486, `backend/core/cli_adapter.py` lines 220-310
- **Source:** Backend review
- **Description:** Two separate subprocess implementations for fill. SSE path rebuilds everything instead of reusing CLIAdapter. Maintenance burden, inconsistent timeout handling.
- **Fix:** Document for now; refactor post-demo.

### S3: Theme Entries Parsing Missing Error Handling
- **File:** `cli/src/cli.py` lines 265-276
- **Source:** Backend review
- **Description:** `json.load()` can crash on invalid JSON. `int()` conversion can raise ValueError. Silent skip on malformed entries.
- **Fix:** Add try/except with clear error messages.

### S4: CLIAdapter Output File Validation Missing
- **File:** `backend/core/cli_adapter.py` lines 263-310
- **Source:** Backend review
- **Description:** Output temp file created empty, passed to subprocess. If subprocess fails, `json.load()` on empty file raises cryptic error.
- **Fix:** Add existence check and JSON validation before parsing.

### S5: Cancel Flow Race Condition
- **File:** `src/App.jsx` lines 357-364
- **Source:** Integration review
- **Description:** `setCurrentTaskId(null)` called before API cancel completes. If cancel fails, no retry possible.
- **Fix:** Clear task ID only after successful cancel. Low demo risk.

### S6: useCallback Dependency Array Includes grid
- **File:** `src/App.jsx` line 340
- **Source:** Frontend review
- **Description:** `handleAutofill` recreates on every grid change. Old SSE connections may still fire with old handlers.
- **Fix:** Remove `grid` from dependency array after switching to functional `setGrid`. Related to B1 fix.

### S7: getThemeEntries() Boundary Detection Logic
- **File:** `src/components/AutofillPanel.jsx` lines 224-319
- **Source:** Frontend review
- **Description:** Complex logic for detecting theme word boundaries. Works for contiguous locked cells but fragile.
- **Fix:** Test with demo theme words; simplify if issues found.

### S8: Inconsistent Timeout Strategy Between Fill Endpoints
- **File:** `backend/api/routes.py` lines 226, 441, 472
- **Source:** Backend review
- **Description:** Non-SSE path: CLIAdapter adds 10s buffer. SSE path: caller adds 10s. Potential double-buffering.
- **Fix:** Standardize timeout hierarchy. Low demo risk.

---

## Nice-to-Have

### N1: Locked Cell Edit Feedback in GridEditor
- **File:** `src/components/GridEditor.jsx` lines 97-102
- **Description:** Typing on theme-locked cells silently fails. No visual feedback.

### N2: No Process Stall Detection in SSE Heartbeat
- **File:** `backend/api/progress_routes.py` lines 99-148
- **Description:** Can't distinguish "long computation" from "hung process".

### N3: ExportPanel Checkbox Accessibility
- **File:** `src/components/ExportPanel.jsx` lines 163-171
- **Description:** Missing htmlFor on disabled checkbox label.

### N4: Iterative Repair Convergence Not Logged
- **File:** `cli/src/fill/iterative_repair.py` lines 207-293
- **Description:** Loop exits after 50 no-improvement iterations without logging remaining conflicts.

### N5: CORS Origin Hardcoded
- **File:** `backend/app.py` lines 39-44
- **Description:** Only allows localhost. Fine for demo.

---

## Demo Priority Summary

| Priority | Issue | Effort | Fix In |
|----------|-------|--------|--------|
| **Must** | B1: Stale closure in SSE | Small | Phase 2 |
| **Must** | B2: Temp file leak | Small | Phase 2 |
| **Must** | B3: Subprocess not killed on timeout | Small | Phase 2 |
| **Must** | B5: Failing beam search test | Small | Phase 2 |
| Should | S1: isThemeLocked preservation | Verify | Phase 2 |
| Should | S3: Theme entries error handling | Small | Phase 2 |
| Should | S6: Remove grid from useCallback deps | Small | Phase 2 (with B1) |
| Defer | S2, S4, S5, S7, S8 | Medium | Post-demo |
| Defer | N1-N5 | Small-Medium | Post-demo |
