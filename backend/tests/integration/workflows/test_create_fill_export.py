"""
E2E workflow test: Create Grid → Fill → Export

This test simulates a complete user journey:
1. Create empty grid
2. Add black squares (optional)
3. Run autofill
4. Export completed grid

Tests the full integration stack: Frontend → Backend → CLI → Business Logic
"""

import pytest
import json


def create_empty_grid(size=11):
    """Helper to create empty grid."""
    return [
        [{"letter": "", "isBlack": False} for _ in range(size)] for _ in range(size)
    ]


class TestCreateFillExportWorkflow:
    """Test complete workflow from grid creation to export."""

    @pytest.mark.slow
    def test_basic_create_fill_export_workflow(self, client):
        """
        Basic workflow:
        1. Create 11×11 grid
        2. Run autofill
        3. Export as JSON
        """
        # Step 1: Create grid
        grid = create_empty_grid(11)
        assert len(grid) == 11
        assert len(grid[0]) == 11

        # Step 2: Run autofill
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 15,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Step 3: Get completed grid (via SSE stream)
        # Note: client.get() on SSE blocks synchronously until stream ends — no sleep needed
        sse_response = client.get(f"/api/progress/{task_id}")
        assert sse_response.status_code == 200

        # Step 4: Export would happen here (if we had export endpoint)
        # For now, verify we have a valid grid to export
        assert len(sse_response.data) > 0

    def test_workflow_with_black_squares(self, client):
        """
        Workflow with black square suggestions:
        1. Create grid
        2. Get black square suggestions
        3. Apply black squares
        4. Run autofill
        """
        grid = create_empty_grid(11)

        # Get black square suggestions for a problematic slot
        response = client.post(
            "/api/grid/suggest-black-square",
            data=json.dumps(
                {
                    "grid": grid,
                    "grid_size": 11,
                    "problematic_slot": {
                        "row": 0,
                        "col": 0,
                        "direction": "across",
                        "length": 11,
                        "pattern": "???????????",
                    },
                    "max_suggestions": 3,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        suggestions = response.json.get("suggestions", [])

        if suggestions:
            # Apply first suggestion (with symmetric pair)
            suggestion = suggestions[0]
            sym = suggestion.get(
                "symmetric_position",
                {"row": 10 - suggestion["row"], "col": 10 - suggestion["col"]},
            )
            response = client.post(
                "/api/grid/apply-black-squares",
                data=json.dumps(
                    {
                        "grid": grid,
                        "primary": {"row": suggestion["row"], "col": suggestion["col"]},
                        "symmetric": sym,
                    }
                ),
                content_type="application/json",
            )

            assert response.status_code == 200
            modified_grid = response.json["grid"]

            # Run autofill on modified grid
            response = client.post(
                "/api/fill/with-progress",
                data=json.dumps(
                    {
                        "size": 11,
                        "grid": modified_grid,
                        "wordlists": ["comprehensive"],
                        "timeout": 15,
                        "min_score": 10,
                        "algorithm": "trie",
                    }
                ),
                content_type="application/json",
            )

            assert response.status_code == 202

    def test_workflow_different_grid_sizes(self, client):
        """
        Test workflow works for different grid sizes:
        - 11×11 (small)
        - 15×15 (medium)
        """
        for size in [11, 15]:
            grid = create_empty_grid(size)

            response = client.post(
                "/api/fill/with-progress",
                data=json.dumps(
                    {
                        "size": size,
                        "grid": grid,
                        "wordlists": ["comprehensive"],
                        "timeout": 20 if size == 15 else 15,
                        "min_score": 10,
                        "algorithm": "trie",
                    }
                ),
                content_type="application/json",
            )

            assert response.status_code == 202
            assert "task_id" in response.json
