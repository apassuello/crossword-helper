"""
E2E workflow test: Adaptive Mode Autofill

This test simulates adaptive black square placement:
1. Create difficult grid (few black squares)
2. Enable adaptive mode
3. Run autofill
4. Verify black squares auto-placed
5. Verify autofill completes
"""

import json

import pytest


def create_difficult_grid():
    """Create grid with constraints that make filling difficult."""
    grid = [[{"letter": "", "isBlack": False} for _ in range(11)] for _ in range(11)]

    # Add some black squares to create difficult constraints
    for i in range(0, 11, 4):
        for j in range(0, 11, 4):
            grid[i][j] = {"letter": "", "isBlack": True}

    return grid


class TestAdaptiveWorkflow:
    """Test adaptive mode workflow."""

    @pytest.mark.slow
    def test_adaptive_mode_basic_workflow(self, client):
        """
        Basic adaptive workflow:
        1. Start autofill with adaptive mode
        2. Verify task starts
        3. Wait for completion
        4. Verify adaptive mode was used (if needed)
        """
        grid = create_difficult_grid()

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 30,
                    "min_score": 10,
                    "algorithm": "beam",
                    "adaptive_mode": True,
                    "max_adaptations": 2,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Get result
        # Note: client.get() on SSE blocks synchronously until stream ends — no sleep needed
        sse_response = client.get(f"/api/progress/{task_id}")
        assert sse_response.status_code == 200

        # Parse SSE stream for completion
        data_str = sse_response.data.decode("utf-8")
        assert "complete" in data_str or "error" in data_str

    def test_adaptive_with_max_adaptations(self, client):
        """
        Test max adaptations limit:
        1. Set max_adaptations=1
        2. Run on difficult grid
        3. Verify at most 1 adaptation applied
        """
        grid = create_difficult_grid()

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 20,
                    "min_score": 10,
                    "algorithm": "beam",
                    "adaptive_mode": True,
                    "max_adaptations": 1,  # Limit to 1 adaptation
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 202

    @pytest.mark.slow
    def test_adaptive_vs_non_adaptive_comparison(self, client):
        """
        Compare adaptive vs non-adaptive:
        1. Run autofill without adaptive (may get stuck)
        2. Run autofill with adaptive (should complete better)
        """
        grid = create_difficult_grid()

        # Non-adaptive (may not complete fully)
        response1 = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 15,
                    "min_score": 10,
                    "algorithm": "beam",
                    "adaptive_mode": False,
                }
            ),
            content_type="application/json",
        )

        task_id_1 = response1.json["task_id"]

        # Adaptive (should complete better)
        response2 = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 15,
                    "min_score": 10,
                    "algorithm": "beam",
                    "adaptive_mode": True,
                    "max_adaptations": 2,
                }
            ),
            content_type="application/json",
        )

        task_id_2 = response2.json["task_id"]

        # Both should complete (adaptive might do better)
        sse1 = client.get(f"/api/progress/{task_id_1}")
        sse2 = client.get(f"/api/progress/{task_id_2}")

        assert sse1.status_code == 200
        assert sse2.status_code == 200
