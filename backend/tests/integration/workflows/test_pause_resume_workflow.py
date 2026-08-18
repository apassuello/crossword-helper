"""
E2E workflow test: Pause/Resume Autofill

This test simulates pause/resume with user edits:
1. Start autofill
2. Pause operation
3. User manually edits grid
4. Get edit summary
5. Resume autofill
6. Verify edits preserved
"""

import json
import time

import pytest


def create_empty_grid(size=11):
    return [[{"letter": "", "isBlack": False} for _ in range(size)] for _ in range(size)]


def _await_state(client, task_id, deadline_s=10):
    """Poll GET /api/fill/state/<task_id> every 0.5s until the first 200.

    Returns the response, or the last non-200 response on timeout. Mirrors the
    helper in backend/tests/integration/test_pause_resume_e2e.py -- the deadline
    IS the guarantee being gated, so it stays at 10s.
    """
    deadline = time.monotonic() + deadline_s
    while True:
        response = client.get(f"/api/fill/state/{task_id}")
        if response.status_code == 200 or time.monotonic() >= deadline:
            return response
        time.sleep(0.5)


class TestPauseResumeWorkflow:
    """Test pause/resume workflow with edits."""

    @pytest.mark.slow
    def test_pause_edit_resume_workflow(self, client):
        """
        Complete pause/resume workflow:
        1. Start autofill
        2. Pause after 3s
        3. Edit grid (add letters)
        4. Get edit summary
        5. Resume autofill
        """
        grid = create_empty_grid(11)

        # Step 1: Start autofill
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 30,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Step 2: Pause after 3s
        time.sleep(3)

        response = client.post(f"/api/fill/pause/{task_id}")
        assert response.status_code == 200

        # Step 3: Get saved state.
        #
        # Polled, not a fixed sleep. This was `time.sleep(2)` followed by a single
        # GET -- a 5s budget in total, against a measured local cost of 5.04s for
        # the CLI to load its wordlist, build the CSP and reach a point where the
        # pause flag is observable. It therefore raced on the fastest hardware
        # available here and failed outright on a CI runner. The 10s deadline is
        # unchanged from the one the e2e gates, so this polls for the same
        # guarantee rather than a weaker one; the 3s pre-pause sleep above stays,
        # since removing it would gate "pause before start" instead of "pause a
        # running solver".
        response = _await_state(client, task_id, 10)
        assert response.status_code == 200, "pause did not save state within the 10s deadline"

        # This block used to post a `state_path`/`new_grid`/`size` body against a
        # `task_id`/`edited_grid` API — a shape neither branch ever accepted. It
        # never ran while the state GET returned non-200, so it passed vacuously;
        # it became reachable once pause actually saved state. Corrected against
        # the real contract, not the merge's.
        # Step 4: User edits (simulate by creating modified grid)
        edited_grid = create_empty_grid(11)
        edited_grid[0][0] = {"letter": "C", "isBlack": False}
        edited_grid[0][1] = {"letter": "A", "isBlack": False}
        edited_grid[0][2] = {"letter": "T", "isBlack": False}

        # Get edit summary
        response = client.post(
            "/api/fill/edit-summary",
            data=json.dumps({"task_id": task_id, "edited_grid": edited_grid}),
            content_type="application/json",
        )

        assert response.status_code == 200
        summary = response.json
        assert "filled_count" in summary

        # Step 5: Resume with edits.
        #
        # `timeout` must live under `options` — the route reads
        # `options = data.get("options") or {}` (backend/api/pause_resume_routes.py)
        # and a top-level `timeout` key is silently ignored, falling back to the
        # 300s default. This 11x11 blank grid is unsatisfiable, so the resumed
        # fill fell back to unwind-and-re-search (#9) and burned the full 300s
        # for no reason, same defect as test_pause_resume_e2e.py step 4.
        response = client.post(
            "/api/fill/resume",
            data=json.dumps(
                {
                    "task_id": task_id,
                    "edited_grid": edited_grid,
                    "options": {"timeout": 3},
                }
            ),
            content_type="application/json",
        )

        # 200, not 202: resume is synchronous and reports the completed run.
        # No branch (bench, main, or base) ever returned 202 here — this block was
        # never reachable, so its assertions were never checked against the route.
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["new_task_id"]
        assert response.json["original_task_id"] == task_id

        # The original block subscribed to /api/progress/<new_task_id> here,
        # expecting an async task to observe. Resume is synchronous — it returns
        # the finished run — so no progress channel is ever registered under that
        # id and the subscribe 404s by design. Assert on the completed result
        # instead, which is what this workflow actually produces.
        assert "result" in response.json
        assert response.json["total_slots"] >= response.json["slots_filled"] >= 0

    def test_cancel_autofill_workflow(self, client):
        """
        Test cancel workflow:
        1. Start autofill
        2. Cancel operation
        3. Verify honest state_saved reporting (cancel does NOT save state)
        """
        grid = create_empty_grid(11)

        # Start autofill
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 30,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        task_id = response.json["task_id"]

        # Cancel immediately
        time.sleep(2)
        response = client.post(f"/api/fill/cancel/{task_id}")

        assert response.status_code == 200
        assert response.json.get("success") is True
        # Cancel kills the subprocess without a checkpoint — it must not
        # claim a resumable state was saved (it used to hardcode true)
        assert response.json.get("state_saved") is False
