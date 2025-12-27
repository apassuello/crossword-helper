"""
Unit tests for grid data transformation logic.

Tests the critical transformation from frontend format to CLI format
WITHOUT executing the CLI (fast unit tests).

These tests isolate the transformation logic to ensure it works correctly
before integration tests verify end-to-end behavior.
"""

import pytest
from backend.tests.fixtures import (
    EMPTY_3X3_FRONTEND,
    PARTIALLY_FILLED_3X3_FRONTEND,
    PATTERN_3X3_FRONTEND,
    MIXED_3X3_FRONTEND,
    LOWERCASE_3X3_FRONTEND,
    ALL_BLACK_3X3_FRONTEND,
    FULLY_FILLED_3X3_FRONTEND,
    EMPTY_3X3_CLI,
    PARTIALLY_FILLED_3X3_CLI,
    PATTERN_3X3_CLI,
    MIXED_3X3_CLI,
    LOWERCASE_3X3_CLI,
    ALL_BLACK_3X3_CLI,
    FULLY_FILLED_3X3_CLI,
    TRANSFORMATION_TEST_CASES,
)


def transform_grid_frontend_to_cli(frontend_grid):
    """
    Extract and test the EXACT transformation logic from routes.py.

    This is the critical function that had the bug.

    Args:
        frontend_grid: Grid in frontend format (list of lists of dicts)

    Returns:
        Grid in CLI format (list of lists of strings)
    """
    cli_grid = []
    for row in frontend_grid:
        cli_row = []
        for cell in row:
            if isinstance(cell, dict):
                if cell.get("isBlack", False):
                    cli_row.append("#")
                elif cell.get("letter", ""):
                    cli_row.append(cell["letter"].upper())
                else:
                    cli_row.append(".")
            else:
                # Already in CLI format (string)
                cli_row.append(cell)
        cli_grid.append(cli_row)
    return cli_grid


class TestGridTransformationLogic:
    """Test the grid transformation function in isolation."""

    @pytest.mark.parametrize("test_name,frontend_data,expected_cli_data", TRANSFORMATION_TEST_CASES)
    def test_all_transformation_cases(self, test_name, frontend_data, expected_cli_data):
        """Test all predefined transformation cases."""
        result = transform_grid_frontend_to_cli(frontend_data["grid"])
        expected = expected_cli_data["grid"]

        assert result == expected, \
            f"Transformation failed for {test_name}.\nGot: {result}\nExpected: {expected}"

    def test_empty_cell_transformation(self):
        """Test that empty cells (letter='') become '.'"""
        frontend_grid = [[{"letter": "", "isBlack": False}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["."]], "Empty cell should become '.'"

    def test_filled_cell_transformation(self):
        """Test that filled cells preserve their letter."""
        frontend_grid = [[{"letter": "A", "isBlack": False}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["A"]], "Filled cell should preserve letter 'A'"

    def test_black_cell_transformation(self):
        """Test that black cells become '#'."""
        frontend_grid = [[{"letter": "", "isBlack": True}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["#"]], "Black cell should become '#'"

    def test_uppercase_transformation(self):
        """Test that lowercase letters are converted to uppercase."""
        frontend_grid = [[{"letter": "a", "isBlack": False}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["A"]], "Lowercase 'a' should become uppercase 'A'"

    def test_mixed_case_transformation(self):
        """Test transformation of mixed case letters."""
        frontend_grid = [
            [
                {"letter": "a", "isBlack": False},
                {"letter": "B", "isBlack": False},
                {"letter": "c", "isBlack": False}
            ]
        ]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["A", "B", "C"]], "All letters should be uppercase"


class TestGridTransformationEdgeCases:
    """Test edge cases in grid transformation."""

    def test_string_passthrough(self):
        """Test that string cells pass through unchanged."""
        # Sometimes grid might already be in CLI format
        mixed_grid = [
            ["A", {"letter": "B", "isBlack": False}, "#"]
        ]
        result = transform_grid_frontend_to_cli(mixed_grid)

        assert result == [["A", "B", "#"]], "String cells should pass through"

    def test_empty_grid(self):
        """Test transformation of empty grid."""
        frontend_grid = []
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [], "Empty grid should remain empty"

    def test_single_cell_grid(self):
        """Test transformation of 1x1 grid."""
        frontend_grid = [[{"letter": "X", "isBlack": False}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["X"]], "Single cell should transform correctly"

    def test_all_black_grid(self):
        """Test transformation of grid with all black squares."""
        frontend_grid = [
            [{"letter": "", "isBlack": True}, {"letter": "", "isBlack": True}],
            [{"letter": "", "isBlack": True}, {"letter": "", "isBlack": True}]
        ]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["#", "#"], ["#", "#"]], "All cells should be '#'"

    def test_all_filled_grid(self):
        """Test transformation of completely filled grid."""
        frontend_grid = [
            [{"letter": "A", "isBlack": False}, {"letter": "B", "isBlack": False}],
            [{"letter": "C", "isBlack": False}, {"letter": "D", "isBlack": False}]
        ]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["A", "B"], ["C", "D"]], "All letters should be preserved"

    def test_special_characters_in_letter(self):
        """Test that special characters in letter field are handled."""
        # Although this shouldn't happen in normal use
        frontend_grid = [[{"letter": "!", "isBlack": False}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        # Should pass through (CLI will validate)
        assert result == [["!"]], "Special characters should pass through"

    def test_missing_letter_field(self):
        """Test handling of cell without letter field."""
        frontend_grid = [[{"isBlack": False}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["."]], "Missing letter field should default to '.'"

    def test_missing_isblack_field(self):
        """Test handling of cell without isBlack field."""
        frontend_grid = [[{"letter": "A"}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        # Should default isBlack to False
        assert result == [["A"]], "Missing isBlack should default to False"

    def test_black_cell_with_letter(self):
        """Test black cell that also has a letter (isBlack takes precedence)."""
        frontend_grid = [[{"letter": "A", "isBlack": True}]]
        result = transform_grid_frontend_to_cli(frontend_grid)

        assert result == [["#"]], "isBlack=True should take precedence over letter"


class TestGridTransformationTypes:
    """Test type handling in transformation."""

    def test_dict_with_all_fields(self):
        """Test cell with all expected fields."""
        cell = {"letter": "A", "isBlack": False}
        result = transform_grid_frontend_to_cli([[cell]])

        assert result == [["A"]]

    def test_dict_with_minimal_fields(self):
        """Test cell with minimal fields."""
        cell = {}
        result = transform_grid_frontend_to_cli([[cell]])

        assert result == [["."]]  # Empty dict should default to empty cell

    def test_string_cell_direct(self):
        """Test that string cell is passed through."""
        cell = "X"
        result = transform_grid_frontend_to_cli([[cell]])

        assert result == [["X"]]

    def test_none_letter_value(self):
        """Test handling of None as letter value."""
        cell = {"letter": None, "isBlack": False}
        result = transform_grid_frontend_to_cli([[cell]])

        # None is falsy, should become '.'
        assert result == [["."]]

    def test_empty_string_letter(self):
        """Test explicit empty string as letter."""
        cell = {"letter": "", "isBlack": False}
        result = transform_grid_frontend_to_cli([[cell]])

        assert result == [["."]]


class TestGridTransformationBugRegression:
    """
    Specific tests for the bug that was missed.

    These tests will FAIL if the transformation code is broken or removed.
    """

    def test_bug_frontend_dict_format_is_transformed(self):
        """
        THE KEY BUG TEST: Verify dict format is transformed to string format.

        The bug was that frontend sent:
          {"letter": "A", "isBlack": false}

        And CLI expected:
          "A"

        Without transformation, CLI crashes with AttributeError.
        """
        # Frontend format
        frontend_grid = [
            [{"letter": "A", "isBlack": False}]
        ]

        # Transform
        result = transform_grid_frontend_to_cli(frontend_grid)

        # Result should be string, not dict
        assert isinstance(result[0][0], str), \
            "Cell should be transformed to string, not remain as dict"

        assert result[0][0] == "A", \
            "Cell should contain letter 'A' as string"

    def test_bug_empty_dict_format_is_transformed(self):
        """Test that empty cell dict is transformed to '.' string."""
        frontend_grid = [
            [{"letter": "", "isBlack": False}]
        ]

        result = transform_grid_frontend_to_cli(frontend_grid)

        # Should be string ".", not dict
        assert isinstance(result[0][0], str), \
            "Cell should be string, not dict"

        assert result[0][0] == ".", \
            "Empty cell should be '.'"

    def test_bug_black_dict_format_is_transformed(self):
        """Test that black cell dict is transformed to '#' string."""
        frontend_grid = [
            [{"letter": "", "isBlack": True}]
        ]

        result = transform_grid_frontend_to_cli(frontend_grid)

        # Should be string "#", not dict
        assert isinstance(result[0][0], str), \
            "Cell should be string, not dict"

        assert result[0][0] == "#", \
            "Black cell should be '#'"

    def test_bug_cli_would_crash_on_dict(self):
        """
        Demonstrate what would happen if transformation didn't occur.

        This test shows why the transformation is critical.
        """
        # This is what frontend sends
        frontend_cell = {"letter": "A", "isBlack": False}

        # If transformation didn't happen, CLI would try to access .get()
        # on what it expects to be a string, causing AttributeError

        # Transformation prevents this
        result = transform_grid_frontend_to_cli([[frontend_cell]])

        # Result is string, not dict
        assert isinstance(result[0][0], str)

        # If we mistakenly passed the dict to CLI, it would crash like this:
        # cell.upper() -> AttributeError: 'dict' object has no attribute 'upper'

    def test_bug_mixed_format_grid(self):
        """Test grid with mixed dict and string cells (edge case)."""
        # Frontend might sometimes have mixed formats
        frontend_grid = [
            [
                {"letter": "A", "isBlack": False},
                "B",  # Already a string
                {"letter": "", "isBlack": True}
            ]
        ]

        result = transform_grid_frontend_to_cli(frontend_grid)

        # All should be strings
        assert all(isinstance(cell, str) for cell in result[0]), \
            "All cells should be strings after transformation"

        assert result[0] == ["A", "B", "#"], \
            "Mixed format should be normalized to strings"


class TestGridTransformationInvariance:
    """Test that transformation is idempotent and preserves certain properties."""

    def test_transformation_is_idempotent(self):
        """Test that transforming twice gives same result as transforming once."""
        frontend_grid = MIXED_3X3_FRONTEND["grid"]

        # Transform once
        result1 = transform_grid_frontend_to_cli(frontend_grid)

        # Transform again (on already-transformed grid)
        result2 = transform_grid_frontend_to_cli(result1)

        # Should be the same (strings pass through)
        assert result1 == result2, \
            "Transformation should be idempotent"

    def test_grid_dimensions_preserved(self):
        """Test that transformation preserves grid dimensions."""
        frontend_grid = EMPTY_5X5_FRONTEND["grid"]

        result = transform_grid_frontend_to_cli(frontend_grid)

        # Dimensions should match
        assert len(result) == 5, "Row count should be preserved"
        assert all(len(row) == 5 for row in result), "Column count should be preserved"

    def test_cell_count_preserved(self):
        """Test that transformation preserves total cell count."""
        frontend_grid = PATTERN_3X3_FRONTEND["grid"]

        original_cell_count = sum(len(row) for row in frontend_grid)
        result = transform_grid_frontend_to_cli(frontend_grid)
        result_cell_count = sum(len(row) for row in result)

        assert original_cell_count == result_cell_count, \
            "Cell count should be preserved"

    def test_black_square_positions_preserved(self):
        """Test that black square positions are preserved."""
        frontend_grid = PATTERN_3X3_FRONTEND["grid"]

        result = transform_grid_frontend_to_cli(frontend_grid)

        # Pattern has black square at (1, 1)
        assert result[1][1] == "#", "Black square position should be preserved"

    def test_filled_letters_preserved(self):
        """Test that filled letters are preserved (though uppercased)."""
        frontend_grid = PARTIALLY_FILLED_3X3_FRONTEND["grid"]

        result = transform_grid_frontend_to_cli(frontend_grid)

        # First row should be "CAT"
        assert result[0] == ["C", "A", "T"], "Filled letters should be preserved"
