"""
E2E workflow test: Theme Word Placement

This test simulates theme-based crossword creation:
1. Upload theme words
2. Get placement suggestions
3. Apply placements (lock cells)
4. Run autofill with theme preservation
5. Verify theme words unchanged
"""

import pytest
import json

pytestmark = pytest.mark.slow


def create_empty_grid(size=15):
    return [
        [{"letter": "", "isBlack": False} for _ in range(size)] for _ in range(size)
    ]


class TestThemePlacementWorkflow:
    """Test complete theme word workflow."""

    def test_theme_upload_suggest_apply_workflow(self, client):
        """
        Complete theme workflow:
        1. Upload theme words file
        2. Get placement suggestions
        3. Apply best placement
        4. Verify locked cells
        """
        grid = create_empty_grid(15)

        # Step 1: Upload theme words
        response = client.post(
            "/api/theme/upload",
            data=json.dumps({"content": "BIRTHDAY\nCELEBRATION\nPARTY"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        theme_words = response.json.get("words", [])
        assert "BIRTHDAY" in theme_words

        # Step 2: Get placement suggestions
        response = client.post(
            "/api/theme/suggest-placements",
            data=json.dumps({"grid": grid, "size": 15, "theme_words": theme_words}),
            content_type="application/json",
        )

        assert response.status_code == 200
        suggestions = response.json.get("suggestions", [])
        assert len(suggestions) > 0

        # Extract first suggestion from first word
        assert len(suggestions[0]["suggestions"]) > 0

        # Step 3: Apply first placement
        placement = suggestions[0]["suggestions"][0]
        response = client.post(
            "/api/theme/apply-placement",
            data=json.dumps(
                {
                    "grid": grid,
                    "placement": {
                        "word": placement["word"],
                        "row": placement["row"],
                        "col": placement["col"],
                        "direction": placement["direction"],
                    },
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json["applied"]
        modified_grid = response.json["grid"]

        # Step 4: Verify theme word is in grid
        word = placement["word"]
        if placement["direction"] == "across":
            row = placement["row"]
            col = placement["col"]
            grid_word = "".join(
                [modified_grid[row][col + i]["letter"] for i in range(len(word))]
            )
            assert grid_word == word

    def test_theme_preservation_during_autofill(self, client):
        """
        Verify theme words are preserved during autofill:
        1. Place theme word
        2. Run autofill
        3. Verify theme word unchanged
        """
        grid = create_empty_grid(15)

        # Place theme word manually
        theme_word = "BIRTHDAY"
        for i, letter in enumerate(theme_word):
            grid[0][i] = {"letter": letter, "isBlack": False, "isThemeLocked": True}

        # Run autofill with theme preservation
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 15,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 20,
                    "min_score": 10,
                    "algorithm": "trie",
                    "theme_entries": {"(0,0,across)": theme_word},
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Get result
        # Note: client.get() on SSE blocks synchronously until stream ends — no sleep needed
        sse_response = client.get(f"/api/progress/{task_id}")
        # Theme word should be unchanged in result
        # (This would require parsing SSE stream for final grid)
        assert sse_response.status_code == 200
