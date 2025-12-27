"""
Test fixtures for grid data in various formats.

Provides sample grids in both frontend format (with objects) and CLI format (with strings)
to test data transformation and integration points.
"""

# ==================================================
# Frontend Format Fixtures
# ==================================================
# These represent the format sent from the React frontend

EMPTY_3X3_FRONTEND = {
    "size": 3,
    "grid": [
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}]
    ]
}

PARTIALLY_FILLED_3X3_FRONTEND = {
    "size": 3,
    "grid": [
        [{"letter": "C", "isBlack": False}, {"letter": "A", "isBlack": False}, {"letter": "T", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "#", "isBlack": True}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}]
    ]
}

# Grid with black squares in pattern
PATTERN_3X3_FRONTEND = {
    "size": 3,
    "grid": [
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}]
    ]
}

# Mixed empty and filled cells
MIXED_3X3_FRONTEND = {
    "size": 3,
    "grid": [
        [{"letter": "A", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "C", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": False}],
        [{"letter": "G", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "I", "isBlack": False}]
    ]
}

# 5x5 grid for slightly larger tests
EMPTY_5X5_FRONTEND = {
    "size": 5,
    "grid": [
        [{"letter": "", "isBlack": False}] * 5,
        [{"letter": "", "isBlack": False}] * 5,
        [{"letter": "", "isBlack": False}] * 5,
        [{"letter": "", "isBlack": False}] * 5,
        [{"letter": "", "isBlack": False}] * 5
    ]
}

# 5x5 with standard crossword pattern
PATTERN_5X5_FRONTEND = {
    "size": 5,
    "grid": [
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}]
    ]
}

# ==================================================
# Expected CLI Format Fixtures
# ==================================================
# These represent what the CLI should receive after transformation

EMPTY_3X3_CLI = {
    "size": 3,
    "grid": [
        [".", ".", "."],
        [".", ".", "."],
        [".", ".", "."]
    ]
}

PARTIALLY_FILLED_3X3_CLI = {
    "size": 3,
    "grid": [
        ["C", "A", "T"],
        [".", "#", "."],
        [".", ".", "."]
    ]
}

PATTERN_3X3_CLI = {
    "size": 3,
    "grid": [
        [".", ".", "."],
        [".", "#", "."],
        [".", ".", "."]
    ]
}

MIXED_3X3_CLI = {
    "size": 3,
    "grid": [
        ["A", ".", "C"],
        [".", "#", "."],
        ["G", ".", "I"]
    ]
}

EMPTY_5X5_CLI = {
    "size": 5,
    "grid": [
        [".", ".", ".", ".", "."],
        [".", ".", ".", ".", "."],
        [".", ".", ".", ".", "."],
        [".", ".", ".", ".", "."],
        [".", ".", ".", ".", "."]
    ]
}

PATTERN_5X5_CLI = {
    "size": 5,
    "grid": [
        [".", ".", ".", ".", "."],
        [".", "#", ".", "#", "."],
        [".", ".", ".", ".", "."],
        [".", "#", ".", "#", "."],
        [".", ".", ".", ".", "."]
    ]
}

# ==================================================
# Edge Cases
# ==================================================

# All black squares (invalid but should be handled gracefully)
ALL_BLACK_3X3_FRONTEND = {
    "size": 3,
    "grid": [
        [{"letter": "", "isBlack": True}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": True}],
        [{"letter": "", "isBlack": True}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": True}],
        [{"letter": "", "isBlack": True}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": True}]
    ]
}

ALL_BLACK_3X3_CLI = {
    "size": 3,
    "grid": [
        ["#", "#", "#"],
        ["#", "#", "#"],
        ["#", "#", "#"]
    ]
}

# Completely filled grid
FULLY_FILLED_3X3_FRONTEND = {
    "size": 3,
    "grid": [
        [{"letter": "C", "isBlack": False}, {"letter": "A", "isBlack": False}, {"letter": "T", "isBlack": False}],
        [{"letter": "A", "isBlack": False}, {"letter": "#", "isBlack": True}, {"letter": "R", "isBlack": False}],
        [{"letter": "R", "isBlack": False}, {"letter": "A", "isBlack": False}, {"letter": "T", "isBlack": False}]
    ]
}

FULLY_FILLED_3X3_CLI = {
    "size": 3,
    "grid": [
        ["C", "A", "T"],
        ["A", "#", "R"],
        ["R", "A", "T"]
    ]
}

# Grid with lowercase letters (should be uppercased)
LOWERCASE_3X3_FRONTEND = {
    "size": 3,
    "grid": [
        [{"letter": "c", "isBlack": False}, {"letter": "a", "isBlack": False}, {"letter": "t", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": True}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}]
    ]
}

LOWERCASE_3X3_CLI = {
    "size": 3,
    "grid": [
        ["C", "A", "T"],  # Should be uppercased
        [".", "#", "."],
        [".", ".", "."]
    ]
}

# ==================================================
# Test Pairs (Frontend -> CLI)
# ==================================================
# Convenient for transformation tests

TRANSFORMATION_TEST_CASES = [
    ("empty_3x3", EMPTY_3X3_FRONTEND, EMPTY_3X3_CLI),
    ("partially_filled_3x3", PARTIALLY_FILLED_3X3_FRONTEND, PARTIALLY_FILLED_3X3_CLI),
    ("pattern_3x3", PATTERN_3X3_FRONTEND, PATTERN_3X3_CLI),
    ("mixed_3x3", MIXED_3X3_FRONTEND, MIXED_3X3_CLI),
    ("empty_5x5", EMPTY_5X5_FRONTEND, EMPTY_5X5_CLI),
    ("pattern_5x5", PATTERN_5X5_FRONTEND, PATTERN_5X5_CLI),
    ("all_black_3x3", ALL_BLACK_3X3_FRONTEND, ALL_BLACK_3X3_CLI),
    ("fully_filled_3x3", FULLY_FILLED_3X3_FRONTEND, FULLY_FILLED_3X3_CLI),
    ("lowercase_3x3", LOWERCASE_3X3_FRONTEND, LOWERCASE_3X3_CLI),
]

# ==================================================
# Invalid Grids (for error handling tests)
# ==================================================

INVALID_GRID_MISSING_SIZE = {
    "grid": [
        [{"letter": "", "isBlack": False}]
    ]
}

INVALID_GRID_MISSING_GRID = {
    "size": 3
}

INVALID_GRID_WRONG_SIZE = {
    "size": 2,  # Too small (min is 3)
    "grid": [
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}],
        [{"letter": "", "isBlack": False}, {"letter": "", "isBlack": False}]
    ]
}

INVALID_GRID_MALFORMED_CELLS = {
    "size": 3,
    "grid": [
        ["not", "a", "dict"],  # Should be objects with letter/isBlack
        ["array", "of", "strings"],
        [".", ".", "."]
    ]
}

# ==================================================
# API Request Fixtures
# ==================================================

VALID_FILL_REQUEST_3X3 = {
    "size": 3,
    "grid": EMPTY_3X3_FRONTEND["grid"],
    "wordlists": ["comprehensive"],
    "timeout": 30,
    "min_score": 30
}

VALID_FILL_REQUEST_WITH_PATTERN = {
    "size": 3,
    "grid": PATTERN_3X3_FRONTEND["grid"],
    "wordlists": ["comprehensive"],
    "timeout": 60,
    "min_score": 40,
    "algorithm": "trie"
}

VALID_FILL_REQUEST_WITH_THEME = {
    "size": 5,
    "grid": PATTERN_5X5_FRONTEND["grid"],
    "wordlists": ["comprehensive"],
    "timeout": 120,
    "min_score": 50,
    "theme_entries": {
        "(0,0,across)": "THEME",
        "(2,0,across)": "ENTRY"
    }
}
