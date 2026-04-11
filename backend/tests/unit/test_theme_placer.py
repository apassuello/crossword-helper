"""
Unit tests for ThemePlacer.
"""

from backend.core.theme_placer import ThemePlacer


class TestThemePlacer:
    """Test suite for theme word placement suggester."""

    def test_initialization(self):
        """Test ThemePlacer initialization."""
        placer = ThemePlacer(15)
        assert placer.grid_size == 15
        assert len(placer.grid) == 15
        assert len(placer.grid[0]) == 15
        assert placer.placed_words == []

    def test_validate_theme_words(self):
        """Test theme word validation."""
        placer = ThemePlacer(15)

        # Valid words
        result = placer.validate_theme_words(["HELLO", "WORLD"])
        assert result["valid"] is True
        assert len(result["errors"]) == 0

        # Too long word
        result = placer.validate_theme_words(["THISWORDISTOOLONGFORTHEGRID"])
        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert "Too long" in result["errors"][0]

        # Too short word
        result = placer.validate_theme_words(["HI"])
        assert result["valid"] is False
        assert "Too short" in result["errors"][0]

        # Non-alphabetic
        result = placer.validate_theme_words(["HELLO123"])
        assert result["valid"] is False
        assert "non-alphabetic" in result["errors"][0]

    def test_single_word_placement(self):
        """Test placement suggestions for a single word."""
        placer = ThemePlacer(15)
        results = placer.suggest_placements(["HELLO"])

        assert len(results) == 1
        assert results[0]["word"] == "HELLO"
        assert results[0]["length"] == 5

        # Should have suggestions
        suggestions = results[0]["suggestions"]
        assert len(suggestions) > 0
        assert suggestions[0]["word"] == "HELLO"
        assert "row" in suggestions[0]
        assert "col" in suggestions[0]
        assert suggestions[0]["direction"] in ["across", "down"]
        assert suggestions[0]["score"] > 0
        assert suggestions[0]["reasoning"] != ""

    def test_multiple_word_placement_no_overlaps(self):
        """Test that multiple words get different placement suggestions."""
        placer = ThemePlacer(21)  # Larger grid for more options

        # Use words of different lengths to ensure variety
        words = ["CELEBRATION", "HAPPINESS", "FAMILY", "JOY"]
        results = placer.suggest_placements(words)

        assert len(results) == len(words)

        # Collect top placements
        placements = []
        for result in results:
            if result["suggestions"]:
                top = result["suggestions"][0]
                # Check if it's a non-overlapping suggestion
                if "WARNING: Overlaps" not in top["reasoning"]:
                    placements.append((top["row"], top["col"], top["direction"]))

        # All words should have been placed without overlaps in a 21x21 grid
        assert len(placements) == len(words), "All words should be placed without overlaps"

        # Check that positions are diverse (not all in same row/col)
        rows = [p[0] for p in placements]
        cols = [p[1] for p in placements]

        # At least 2 different rows and columns should be used
        assert len(set(rows)) >= 2, "Placements should use different rows"
        assert len(set(cols)) >= 2, "Placements should use different columns"

    def test_placement_with_existing_grid(self):
        """Test placement suggestions with existing grid content."""
        placer = ThemePlacer(15)

        # Create a grid with some letters already placed
        existing_grid = [["." for _ in range(15)] for _ in range(15)]
        # Place "CAT" horizontally at row 7, col 6
        existing_grid[7][6] = "C"
        existing_grid[7][7] = "A"
        existing_grid[7][8] = "T"

        results = placer.suggest_placements(["APPLE"], existing_grid=existing_grid)

        assert len(results) == 1
        suggestions = results[0]["suggestions"]
        assert len(suggestions) > 0

        # Check if intersection is detected when APPLE is placed vertically through 'A'
        # (This would be at col 7, intersecting with the 'A' in CAT)
        found_intersection = False
        for sugg in suggestions:
            if "Intersects" in sugg["reasoning"]:
                found_intersection = True
                break

        # Should find at least one placement that intersects with existing word
        assert found_intersection, "Should detect possible intersections with existing content"

    def test_apply_placement(self):
        """Test applying a placement to the internal grid."""
        placer = ThemePlacer(15)

        placement = {"word": "HELLO", "row": 7, "col": 5, "direction": "across"}

        placer.apply_placement(placement)

        # Check that word was placed in grid
        assert placer.grid[7][5] == "H"
        assert placer.grid[7][6] == "E"
        assert placer.grid[7][7] == "L"
        assert placer.grid[7][8] == "L"
        assert placer.grid[7][9] == "O"

        # Check that placement was tracked
        assert len(placer.placed_words) == 1
        assert placer.placed_words[0] == placement

    def test_scoring_prefers_centered_placements(self):
        """Test that centered placements get higher scores."""
        placer = ThemePlacer(15)

        # Create two placements: one centered, one at edge
        centered = {"row": 7, "col": 5, "direction": "across", "word": "HELLO"}
        edge = {"row": 0, "col": 0, "direction": "across", "word": "HELLO"}

        score_centered = placer._score_placement(centered, "HELLO")
        score_edge = placer._score_placement(edge, "HELLO")

        assert score_centered > score_edge, "Centered placement should score higher"

    def test_diversity_in_large_grid(self):
        """Test that many theme words spread across a large grid."""
        placer = ThemePlacer(21)

        # 15 theme words as mentioned in the problem
        theme_words = [
            "ANNIVERSARY",
            "HAPPINESS",
            "CELEBRATION",
            "MEMORIES",
            "TOGETHER",
            "FAMILY",
            "FRIENDS",
            "JOURNEY",
            "BLESSING",
            "GRATITUDE",
            "CHERISH",
            "FOREVER",
            "JOYFUL",
            "SPECIAL",
            "MILESTONE",
        ]

        results = placer.suggest_placements(theme_words)

        # Count successful placements (without overlaps)
        placed_count = 0
        positions = []

        for result in results:
            if result["suggestions"]:
                top = result["suggestions"][0]
                if "WARNING: Overlaps" not in top["reasoning"]:
                    placed_count += 1
                    positions.append((top["row"], top["col"]))

        # Should place at least 10 words successfully
        assert placed_count >= 10, f"Should place at least 10 words, got {placed_count}"

        # Check for reasonable distribution
        if placed_count >= 10:
            rows = [p[0] for p in positions]
            cols = [p[1] for p in positions]

            # Should use a good spread of the grid
            assert max(rows) - min(rows) > 5, "Words should spread vertically"
            assert max(cols) - min(cols) > 5, "Words should spread horizontally"

    def test_overlap_detection(self):
        """Test that placer avoids overlapping with existing placements."""
        placer = ThemePlacer(15)

        # Place first word
        placement1 = {"word": "HELLO", "row": 7, "col": 5, "direction": "across"}
        placer.apply_placement(placement1)

        # Get suggestions for second word
        results = placer.suggest_placements(["WORLD"])
        suggestions = results[0]["suggestions"]

        # Any suggestion that overlaps HELLO's cells (row 7, cols 5-9) must be
        # flagged with a warning in its reasoning string.
        for sugg in suggestions:
            if sugg["direction"] == "across" and sugg["row"] == 7:
                sugg_end = sugg["col"] + len("WORLD") - 1
                overlaps = sugg["col"] <= 9 and sugg_end >= 5
                if overlaps:
                    assert "WARNING: Overlaps" in sugg["reasoning"], (
                        f"Overlapping across suggestion at row={sugg['row']}, " f"col={sugg['col']} was not flagged"
                    )

    def test_intersection_scoring(self):
        """Test that intersections are detected and contribute to scoring."""
        placer = ThemePlacer(15)

        # Place "HELLO" horizontally at row 7, columns 5-9
        # H(7,5), E(7,6), L(7,7), L(7,8), O(7,9)
        placement1 = {"word": "HELLO", "row": 7, "col": 5, "direction": "across"}
        placer.apply_placement(placement1)

        # Check that intersection count works
        # Place "BELL" vertically through the 'L' at column 7
        # If we place at (5,7), we get: B(5,7), E(6,7), L(7,7), L(8,7)
        # This should intersect with HELLO's L at (7,7)
        placement_with_intersection = {
            "row": 5,
            "col": 7,
            "direction": "down",
            "word": "BELL",
        }

        # Place at column 2 should have no intersection
        placement_no_intersection = {
            "row": 5,
            "col": 2,
            "direction": "down",
            "word": "BELL",
        }

        intersections_good = placer._count_intersections(placement_with_intersection, "BELL")
        intersections_bad = placer._count_intersections(placement_no_intersection, "BELL")

        # Should detect the 'L' intersection at (7,7)
        assert intersections_good == 1, f"Should detect one intersection, got {intersections_good}"
        assert intersections_bad == 0, "Should detect no intersections"
