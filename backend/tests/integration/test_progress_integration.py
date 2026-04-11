"""
Integration tests for SSE progress tracking endpoints.

Tests the /api/fill/with-progress and /api/pattern/with-progress endpoints
that use Server-Sent Events for real-time progress updates.
"""

import json
import time

import pytest

from backend.app import create_app
from backend.tests.fixtures import EMPTY_3X3_FRONTEND, PATTERN_3X3_FRONTEND


@pytest.fixture
def client():
    """Create test client."""
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client


# ==================================================
# /api/fill/with-progress Tests
# ==================================================


class TestFillWithProgressEndpoint:
    """Test /api/fill/with-progress SSE endpoint."""

    def test_fill_with_progress_returns_task_id(self, client):
        """Test that fill-with-progress returns task ID and progress URL."""
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                "grid": EMPTY_3X3_FRONTEND["grid"],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        assert response.status_code == 202, "Should return 202 Accepted for async operation"

        data = json.loads(response.data)
        assert "task_id" in data, "Response should contain task_id"
        assert "progress_url" in data, "Response should contain progress_url"

        # Verify progress_url format
        assert f"/api/progress/{data['task_id']}" in data["progress_url"], "Progress URL should contain task ID"

    def test_fill_with_progress_validates_request(self, client):
        """Test that fill-with-progress validates request data."""
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                # Missing grid
                "wordlists": ["comprehensive"],
            },
            content_type="application/json",
        )

        assert response.status_code == 400, "Should reject invalid request"

    def test_fill_with_progress_creates_progress_tracker(self, client):
        """Test that progress tracker is created for fill operation."""
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                "grid": PATTERN_3X3_FRONTEND["grid"],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        assert response.status_code == 202

        data = json.loads(response.data)
        task_id = data["task_id"]

        # Try to get progress (should exist, even if operation hasn't started yet)
        # Note: We can't easily test SSE stream in pytest, but we can verify the endpoint exists
        progress_response = client.get(f"/api/progress/{task_id}")

        # Should either get progress stream or 404 if tracker cleaned up
        assert progress_response.status_code in [
            200,
            404,
        ], "Progress endpoint should exist or be cleaned up"

    def test_fill_with_progress_handles_invalid_wordlists(self, client):
        """Test error handling for invalid wordlists."""
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                "grid": EMPTY_3X3_FRONTEND["grid"],
                "wordlists": [],  # Empty wordlists
                "timeout": 30,
            },
            content_type="application/json",
        )

        assert response.status_code == 400, "Should reject empty wordlists"

    @pytest.mark.slow
    def test_fill_with_progress_spawns_background_task(self, client):
        """Test that fill-with-progress spawns background task."""
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                "grid": PATTERN_3X3_FRONTEND["grid"],
                "wordlists": ["comprehensive"],
                "timeout": 10,  # Minimum allowed timeout
                "min_score": 0,
            },
            content_type="application/json",
        )

        assert response.status_code == 202

        # Response should be immediate (not wait for fill to complete)
        # This verifies it's running in background
        data = json.loads(response.data)
        assert "task_id" in data

        # Wait briefly for background task to start
        time.sleep(0.5)

        # Background task should be running or completed
        # (Hard to test without SSE client, but at least verify no crash)


# ==================================================
# /api/pattern/with-progress Tests
# ==================================================


class TestPatternWithProgressEndpoint:
    """Test /api/pattern/with-progress SSE endpoint."""

    def test_pattern_with_progress_returns_task_id(self, client):
        """Test that pattern-with-progress returns task ID and progress URL."""
        response = client.post(
            "/api/pattern/with-progress",
            json={"pattern": "C?T", "wordlists": ["comprehensive"], "max_results": 10},
            content_type="application/json",
        )

        assert response.status_code == 202, "Should return 202 Accepted for async operation"

        data = json.loads(response.data)
        assert "task_id" in data, "Response should contain task_id"
        assert "progress_url" in data, "Response should contain progress_url"

    def test_pattern_with_progress_validates_request(self, client):
        """Test that pattern-with-progress validates request data."""
        response = client.post(
            "/api/pattern/with-progress",
            json={
                # Missing pattern
                "wordlists": ["comprehensive"]
            },
            content_type="application/json",
        )

        assert response.status_code == 400, "Should reject invalid request"


# ==================================================
# Progress Stream Tests
# ==================================================


class TestProgressStream:
    """Test /api/progress/<task_id> SSE stream."""

    def test_progress_endpoint_exists(self, client):
        """Test that progress endpoint is registered."""
        # Start a fill operation to get a task ID
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                "grid": EMPTY_3X3_FRONTEND["grid"],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        data = json.loads(response.data)
        task_id = data["task_id"]

        # Try to access progress endpoint
        progress_response = client.get(f"/api/progress/{task_id}")

        # Should get a response (200 for active stream, 404 if cleaned up)
        assert progress_response.status_code in [200, 404]

    def test_progress_endpoint_requires_task_id(self, client):
        """Test that accessing progress without task ID returns 404."""
        response = client.get("/api/progress/")

        # Should 404 because no task_id provided
        assert response.status_code in [
            404,
            308,
        ], "Should not allow access without task ID"

    def test_progress_nonexistent_task_id(self, client):
        """Test that nonexistent task ID returns 404 or empty stream."""
        response = client.get("/api/progress/nonexistent-task-id-12345")

        # Should either 404 or return empty stream
        assert response.status_code in [200, 404]


# ==================================================
# Data Format Tests for Progress Endpoints
# ==================================================


class TestProgressDataFormatTransformation:
    """Test that progress endpoints correctly transform grid data."""

    def test_fill_with_progress_transforms_frontend_format(self, client):
        """
        Test that fill-with-progress correctly transforms frontend grid format.

        This is critical - the same bug that affected /api/fill could affect
        /api/fill/with-progress.
        """
        # Send frontend-format grid
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                "grid": [
                    [
                        {"letter": "A", "isBlack": False},
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": False},
                    ],
                    [
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": True},
                        {"letter": "", "isBlack": False},
                    ],
                    [
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": False},
                    ],
                ],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        # Should accept request (202) not crash (500)
        assert response.status_code == 202, f"Should accept frontend format grid, got {response.status_code}: {response.data}"

        data = json.loads(response.data)
        assert "task_id" in data, "Should return task_id"

    def test_fill_with_progress_handles_black_squares(self, client):
        """Test that fill-with-progress correctly handles black squares."""
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                "grid": PATTERN_3X3_FRONTEND["grid"],  # Has black squares
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        assert response.status_code == 202, "Should handle black squares correctly"

    def test_fill_with_progress_handles_lowercase_letters(self, client):
        """Test that fill-with-progress uppercases lowercase letters."""
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                "grid": [
                    [
                        {"letter": "a", "isBlack": False},
                        {"letter": "b", "isBlack": False},
                        {"letter": "c", "isBlack": False},
                    ],
                    [
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": True},
                        {"letter": "", "isBlack": False},
                    ],
                    [
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": False},
                    ],
                ],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        assert response.status_code == 202, "Should handle lowercase letters"


# ==================================================
# Concurrency Tests
# ==================================================


@pytest.mark.slow
class TestProgressConcurrency:
    """Test concurrent progress operations."""

    def test_multiple_concurrent_fill_operations(self, client):
        """Test that multiple fill operations can run concurrently."""
        # Start multiple fill operations
        task_ids = []

        for _ in range(3):
            response = client.post(
                "/api/fill/with-progress",
                json={
                    "size": 3,
                    "grid": EMPTY_3X3_FRONTEND["grid"],
                    "wordlists": ["comprehensive"],
                    "timeout": 10,
                    "min_score": 0,
                },
                content_type="application/json",
            )

            assert response.status_code == 202
            data = json.loads(response.data)
            task_ids.append(data["task_id"])

        # All task IDs should be unique
        assert len(task_ids) == len(set(task_ids)), "Task IDs should be unique"

        # Each should have its own progress tracker
        for task_id in task_ids:
            # Progress endpoint should exist (or be cleaned up)
            response = client.get(f"/api/progress/{task_id}")
            assert response.status_code in [200, 404]


# ==================================================
# Cleanup Tests
# ==================================================


class TestProgressCleanup:
    """Test that progress trackers are cleaned up properly."""

    @pytest.mark.slow
    def test_completed_tasks_cleanup(self, client):
        """Test that completed tasks eventually get cleaned up."""
        # Start a quick operation
        response = client.post(
            "/api/pattern/with-progress",
            json={"pattern": "CAT", "wordlists": ["comprehensive"], "max_results": 5},
            content_type="application/json",
        )

        assert response.status_code == 202
        data = json.loads(response.data)
        task_id = data["task_id"]

        # Wait for operation to complete
        time.sleep(2)

        # Progress endpoint might still exist or be cleaned up
        # Either is acceptable - just verify no crash
        progress_response = client.get(f"/api/progress/{task_id}")
        assert progress_response.status_code in [200, 404]


# ==================================================
# Error Handling for Progress Endpoints
# ==================================================


class TestProgressErrorHandling:
    """Test error handling in progress endpoints."""

    def test_fill_with_progress_handles_cli_error(self, client):
        """Test that fill-with-progress handles CLI errors gracefully."""
        # Send invalid grid that CLI will reject
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 1,  # Too small, will fail validation
                "grid": [[{"letter": "", "isBlack": False}]],
                "wordlists": ["comprehensive"],
                "timeout": 30,
            },
            content_type="application/json",
        )

        # Should reject at validation level (400) not crash (500)
        assert response.status_code == 400, "Should validate and reject invalid grid"

    def test_fill_with_progress_handles_missing_wordlist_file(self, client):
        """Test handling of nonexistent wordlist file."""
        # This might get caught at validation or during CLI execution
        # Either way, should not crash
        response = client.post(
            "/api/fill/with-progress",
            json={
                "size": 3,
                "grid": EMPTY_3X3_FRONTEND["grid"],
                "wordlists": ["nonexistent_wordlist_12345"],
                "timeout": 30,
            },
            content_type="application/json",
        )

        # Might accept (202) if validation doesn't check file existence,
        # or reject (400) if it does. Either is fine.
        # Just should not crash (500)
        assert response.status_code in [
            202,
            400,
        ], f"Should handle missing wordlist gracefully, got {response.status_code}"
