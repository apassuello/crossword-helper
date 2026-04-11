# Test Gap Analysis — 2026-03-23

## Summary

610 total tests, 581 selected by default (29 `@pytest.mark.slow` excluded via `pytest.ini`).
1 file entirely skipped (`test_phase4_regression.py` — deprecated API signatures).

## 0% Coverage Modules (unit tests only)

| Module | Lines | Risk | Notes |
|--------|-------|------|-------|
| `cli/src/cli.py` | 690 | HIGH | All CLI entry points |
| `backend/api/routes.py` | 486 | HIGH | Main API surface |
| `backend/core/cli_adapter.py` | 136 | HIGH | Integration bridge |
| `backend/api/pause_resume_routes.py` | 139 | HIGH | Complex state machine |
| `backend/core/edit_merger.py` | 129 | MED | Grid edit validation |
| `backend/core/black_square_suggester.py` | 187 | MED | Strategic placement |
| `backend/api/progress_routes.py` | 89 | MED | SSE streaming |
| `backend/api/theme_routes.py` | 167 | MED | Theme management |
| `cli/src/core/nyt_parser.py` | 210 | MED | New, zero tests |
| `backend/api/grid_routes.py` | 85 | MED | Grid operations |
| `backend/api/wordlist_routes.py` | 142 | MED | Wordlist management |
| `backend/api/validators.py` | 98 | MED | Input validation |
| `backend/data/wordlist_manager.py` | 121 | MED | Data access |
| `backend/app.py` | 41 | LOW | App factory |
| `cli/src/core/scoring.py` | 17 | LOW | Word quality scoring |
| `cli/src/core/conventions.py` | 22 | LOW | Entry normalization |
| `cli/src/core/progress.py` | 28 | LOW | Progress tracking |

Note: Integration tests cover many of these via subprocess, but they're all slow-marked.

## Skipped / Deprecated

- `cli/tests/unit/test_phase4_regression.py` — module-level `pytest.mark.skip`, reason: "Deprecated: Uses outdated API signatures." Should be deleted or updated.

## 29 Slow-Marked Tests (excluded by default)

Files with `@pytest.mark.slow`:
- `backend/tests/integration/sse/test_sse_error_handling.py`
- `backend/tests/integration/sse/test_sse_message_format.py`
- `backend/tests/integration/sse/test_sse_concurrency.py`
- `backend/tests/integration/test_all_beam_scenarios.py`
- `backend/tests/integration/test_realistic_grids.py`
- `backend/tests/integration/workflows/test_adaptive_workflow.py`
- `backend/tests/integration/workflows/test_pause_resume_workflow.py`
- `backend/tests/integration/test_cli_integration.py`
- `backend/tests/integration/test_progress_integration.py`

## Known Broken Features — Test Gap

### `--theme-entries` CLI flag (documented: does NOT preserve theme words)
- Tests exist in `test_theme_priority.py` and `test_beam_search_pause_resume.py` but test the API path, not the CLI flag directly.
- No end-to-end test verifies the CLI flag actually preserves theme words.

### `--adaptive` CLI flag (documented: does NOT auto-add black squares)
- `test_adaptive_beam_crash_fix.py` only tests it doesn't crash — not functional correctness.
- No test verifies black squares are actually added.

## New Untested Code

- `cli/src/core/nyt_parser.py` (210 lines) — cherry-picked with zero tests.

## Recommendations

1. Run ALL tests (including slow) to establish current baseline
2. Fix or delete `test_phase4_regression.py`
3. Write tests for `nyt_parser.py`
4. Add functional correctness tests for `--theme-entries` and `--adaptive`
5. Add unit tests for `cli_adapter.py` and `routes.py`
