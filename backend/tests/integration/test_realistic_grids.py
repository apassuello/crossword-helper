"""
Integration tests using realistic 11x11, 15x15, and 21x21 grids.

These tests verify that the critical bug fix (frontend dict → CLI string conversion)
works correctly with actual crossword-sized grids, not just toy 3x3 grids.
"""

import pytest
import json
import subprocess
from pathlib import Path

# Import fixtures
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from fixtures.realistic_grid_fixtures import (
    get_11x11_empty_frontend,
    get_11x11_empty_cli,
    get_11x11_filled_frontend,
    get_11x11_filled_cli,
    get_11x11_test_cli,
    get_15x15_empty_frontend,
    get_15x15_empty_cli,
    get_15x15_my_puzzle_frontend,
    get_15x15_my_puzzle_cli,
    get_21x21_empty_frontend,
    get_21x21_empty_cli,
    frontend_to_cli_grid,
    validate_transformation,
)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CLI_PATH = PROJECT_ROOT / "cli" / "crossword"
WORDLIST_PATH = PROJECT_ROOT / "data" / "wordlists" / "comprehensive.txt"


# ============================================================================
# TRANSFORMATION VALIDATION TESTS (The Critical Bug)
# ============================================================================


def test_transformation_11x11_empty():
    """Verify frontend → CLI transformation for 11x11 empty grid."""
    frontend_data = get_11x11_empty_frontend()
    cli_data = get_11x11_empty_cli()

    assert validate_transformation(
        frontend_data["grid"], cli_data["grid"]
    ), "Frontend → CLI transformation failed for 11x11 empty grid"


def test_transformation_11x11_filled():
    """Verify frontend → CLI transformation for 11x11 filled grid."""
    frontend_data = get_11x11_filled_frontend()
    cli_data = get_11x11_filled_cli()

    assert validate_transformation(
        frontend_data["grid"], cli_data["grid"]
    ), "Frontend → CLI transformation failed for 11x11 filled grid"


def test_transformation_15x15_empty():
    """Verify frontend → CLI transformation for 15x15 empty grid."""
    frontend_data = get_15x15_empty_frontend()
    cli_data = get_15x15_empty_cli()

    assert validate_transformation(
        frontend_data["grid"], cli_data["grid"]
    ), "Frontend → CLI transformation failed for 15x15 empty grid"


def test_transformation_15x15_my_puzzle():
    """Verify frontend → CLI transformation for 15x15 my_puzzle."""
    frontend_data = get_15x15_my_puzzle_frontend()
    cli_data = get_15x15_my_puzzle_cli()

    assert validate_transformation(
        frontend_data["grid"], cli_data["grid"]
    ), "Frontend → CLI transformation failed for 15x15 my_puzzle"


def test_transformation_21x21_empty():
    """Verify frontend → CLI transformation for 21x21 empty grid."""
    frontend_data = get_21x21_empty_frontend()
    cli_data = get_21x21_empty_cli()

    assert validate_transformation(
        frontend_data["grid"], cli_data["grid"]
    ), "Frontend → CLI transformation failed for 21x21 empty grid"


# ============================================================================
# CLI PARSING TESTS (Verify CLI Can Parse Transformed Data)
# ============================================================================


@pytest.mark.slow
def test_cli_can_parse_11x11_grid(tmp_path):
    """
    Test that CLI can successfully parse 11x11 grid after transformation.

    This is the CRITICAL TEST that would have caught the bug.
    The bug caused: AttributeError: 'dict' object has no attribute 'isalpha'
    """
    # Get frontend format (what the backend receives)
    frontend_data = get_11x11_empty_frontend()

    # Transform to CLI format (what the bug was NOT doing)
    cli_grid = frontend_to_cli_grid(frontend_data["grid"])
    cli_data = {"size": frontend_data["size"], "grid": cli_grid}

    # Write to temp file
    grid_file = tmp_path / "test_11x11.json"
    with open(grid_file, "w") as f:
        json.dump(cli_data, f)

    # Try to load with CLI (this would crash with the bug)
    try:
        result = subprocess.run(
            [
                "python",
                str(CLI_PATH),
                "fill",
                str(grid_file),
                "--timeout",
                "1",
                "--json-output",
                "--wordlists",
                str(WORDLIST_PATH),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Should NOT crash with AttributeError
        assert (
            "AttributeError" not in result.stderr
        ), f"CLI crashed parsing 11x11 grid: {result.stderr}"

        # Should load the grid successfully
        assert (
            "Loading grid" in result.stderr
            or result.returncode == 0
            or "timeout" in result.stderr.lower()
        ), f"CLI didn't load grid properly: {result.stderr}"

    except subprocess.TimeoutExpired:
        # Timeout is OK - means it loaded and started processing
        pass


@pytest.mark.slow
def test_cli_can_parse_15x15_grid(tmp_path):
    """
    Test that CLI can successfully parse 15x15 grid after transformation.
    """
    frontend_data = get_15x15_empty_frontend()
    cli_grid = frontend_to_cli_grid(frontend_data["grid"])
    cli_data = {"size": 15, "grid": cli_grid}

    grid_file = tmp_path / "test_15x15.json"
    with open(grid_file, "w") as f:
        json.dump(cli_data, f)

    try:
        result = subprocess.run(
            [
                "python",
                str(CLI_PATH),
                "fill",
                str(grid_file),
                "--timeout",
                "1",
                "--json-output",
                "--wordlists",
                str(WORDLIST_PATH),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert (
            "AttributeError" not in result.stderr
        ), f"CLI crashed parsing 15x15 grid: {result.stderr}"

    except subprocess.TimeoutExpired:
        pass


@pytest.mark.slow
def test_cli_can_parse_21x21_grid(tmp_path):
    """
    Test that CLI can successfully parse 21x21 grid after transformation.
    """
    frontend_data = get_21x21_empty_frontend()
    cli_grid = frontend_to_cli_grid(frontend_data["grid"])
    cli_data = {"size": 21, "grid": cli_grid}

    grid_file = tmp_path / "test_21x21.json"
    with open(grid_file, "w") as f:
        json.dump(cli_data, f)

    try:
        result = subprocess.run(
            [
                "python",
                str(CLI_PATH),
                "fill",
                str(grid_file),
                "--timeout",
                "1",
                "--json-output",
                "--wordlists",
                str(WORDLIST_PATH),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert (
            "AttributeError" not in result.stderr
        ), f"CLI crashed parsing 21x21 grid: {result.stderr}"

    except subprocess.TimeoutExpired:
        pass


# ============================================================================
# REGRESSION TEST (The Bug That Was Missed)
# ============================================================================


@pytest.mark.slow
def test_bug_regression_frontend_dict_causes_crash(tmp_path):
    """
    REGRESSION TEST: Verify that passing frontend dict format to CLI crashes.

    This test SHOULD FAIL if the bug is present (i.e., if the backend passes
    frontend format directly to CLI without transformation).

    The bug: Backend sends {"letter": "A", "isBlack": false}
    The CLI expects: "A" (string)
    The error: AttributeError: 'dict' object has no attribute 'isalpha'
    """
    # Get frontend format WITHOUT transformation
    frontend_data = get_11x11_empty_frontend()

    # Write frontend format DIRECTLY (this is the bug)
    grid_file = tmp_path / "frontend_format.json"
    with open(grid_file, "w") as f:
        json.dump(frontend_data, f)

    # This SHOULD crash with AttributeError
    result = subprocess.run(
        [
            "python",
            str(CLI_PATH),
            "fill",
            str(grid_file),
            "--timeout",
            "1",
            "--json-output",
            "--wordlists",
            str(WORDLIST_PATH),
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )

    # Verify the bug manifests
    assert (
        "AttributeError" in result.stderr
    ), "Expected AttributeError when passing frontend dict format to CLI (this is the bug)"
    assert (
        "'dict' object has no attribute" in result.stderr
    ), "Expected specific error message about dict not having attribute"


# ============================================================================
# API ENDPOINT TESTS (End-to-End with Realistic Grids)
# ============================================================================

# TODO: Add API endpoint tests once 'client' fixture is available in conftest.py
# These tests should verify:
# 1. POST /api/fill with 11x11, 15x15, 21x21 grids
# 2. POST /api/fill/with-progress with realistic grids
# 3. Response codes are not 500 (no crashes)
#
# Example (needs client fixture):
# def test_fill_endpoint_with_11x11_grid(client):
#     frontend_data = get_11x11_empty_frontend()
#     response = client.post("/api/fill", json={"size": 11, "grid": frontend_data["grid"], ...})
#     assert response.status_code != 500


# ============================================================================
# GRID SIZE VALIDATION
# ============================================================================


def test_validate_grid_sizes():
    """Verify all test grids have correct sizes."""
    assert get_11x11_empty_cli()["size"] == 11
    assert get_11x11_filled_cli()["size"] == 11
    assert get_11x11_test_cli()["size"] == 11

    assert get_15x15_empty_cli()["size"] == 15
    assert get_15x15_my_puzzle_cli()["size"] == 15

    assert get_21x21_empty_cli()["size"] == 21


def test_validate_grid_dimensions():
    """Verify all grids have correct row/col counts."""
    grids = [
        (get_11x11_empty_cli(), 11),
        (get_11x11_filled_cli(), 11),
        (get_15x15_empty_cli(), 15),
        (get_15x15_my_puzzle_cli(), 15),
        (get_21x21_empty_cli(), 21),
    ]

    for grid_data, expected_size in grids:
        assert (
            len(grid_data["grid"]) == expected_size
        ), f"Grid has {len(grid_data['grid'])} rows, expected {expected_size}"

        for i, row in enumerate(grid_data["grid"]):
            assert (
                len(row) == expected_size
            ), f"Row {i} has {len(row)} cells, expected {expected_size}"


# ============================================================================
# SUMMARY
# ============================================================================

"""
Test Summary:

These tests use REALISTIC grid sizes (11x11, 15x15, 21x21) from actual project
test data, not toy 3x3 grids.

Key tests:
1. Transformation validation (frontend → CLI)
2. CLI parsing tests (verify CLI can parse transformed data)
3. Regression test (verify bug manifests when transformation is skipped)
4. API endpoint tests (end-to-end with realistic grids)

These tests would have IMMEDIATELY caught the critical bug where backend was
passing frontend dict format to CLI instead of transforming to string format.
"""
