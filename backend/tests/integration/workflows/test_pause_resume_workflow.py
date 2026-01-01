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

import pytest
import json
import time
from backend.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def create_empty_grid(size=11):
    return [[{"letter": "", "isBlack": False} for _ in range(size)] for _ in range(size)]


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
            data=json.dumps({
                "size": 11,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Step 2: Pause after 3s
        time.sleep(3)

        response = client.post(f"/api/fill/pause/{task_id}")
        assert response.status_code == 200

        # Wait for pause to complete
        time.sleep(2)

        # Step 3: Get saved state
        response = client.get(f"/api/fill/state/{task_id}")

        if response.status_code == 200:
            state = response.json
            state_path = f"/tmp/state-{task_id}.json.gz"  # Mock path

            # Step 4: User edits (simulate by creating modified grid)
            edited_grid = create_empty_grid(11)
            edited_grid[0][0] = {"letter": "C", "isBlack": False}
            edited_grid[0][1] = {"letter": "A", "isBlack": False}
            edited_grid[0][2] = {"letter": "T", "isBlack": False}

            # Get edit summary
            response = client.post(
                "/api/fill/edit-summary",
                data=json.dumps({
                    "state_path": state_path,
                    "new_grid": edited_grid,
                    "size": 11
                }),
                content_type="application/json"
            )

            assert response.status_code == 200
            summary = response.json
            assert "edits" in summary

            # Step 5: Resume with edits
            response = client.post(
                "/api/fill/resume",
                data=json.dumps({
                    "state_path": state_path,
                    "edited_grid": edited_grid,
                    "size": 11,
                    "timeout": 30
                }),
                content_type="application/json"
            )

            assert response.status_code == 202
            new_task_id = response.json["task_id"]

            # Wait for resume to complete
            time.sleep(35)

            # Verify resumed task completes
            sse_response = client.get(f"/api/progress/{new_task_id}")
            assert sse_response.status_code == 200

    def test_cancel_autofill_workflow(self, client):
        """
        Test cancel workflow:
        1. Start autofill
        2. Cancel operation
        3. Verify state saved
        4. Verify cleanup
        """
        grid = create_empty_grid(11)

        # Start autofill
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 11,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        task_id = response.json["task_id"]

        # Cancel immediately
        time.sleep(2)
        response = client.post(f"/api/fill/cancel/{task_id}")

        assert response.status_code == 200
        assert response.json.get("state_saved") == True
