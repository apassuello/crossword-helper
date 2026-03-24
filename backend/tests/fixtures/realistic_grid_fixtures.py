"""
Realistic grid fixtures for testing using actual project grids.

These fixtures use real 11x11, 15x15, and 21x21 grids from the test_data directory
and provide them in both CLI format (strings) and frontend format (dicts).
"""

import json
from pathlib import Path
from typing import Dict, List, Any


def cli_to_frontend_grid(cli_grid: List[List[str]]) -> List[List[Dict[str, Any]]]:
    """
    Convert CLI format grid to frontend format.

    CLI format: ["A", "#", ".", ...]
    Frontend format: [{"letter": "A", "isBlack": false}, ...]
    """
    frontend_grid = []
    for row in cli_grid:
        frontend_row = []
        for cell in row:
            if cell == "#":
                frontend_row.append(
                    {
                        "letter": "",
                        "isBlack": True,
                        "number": None,
                        "isThemeLocked": False,
                    }
                )
            elif cell == "." or cell == "":
                frontend_row.append(
                    {
                        "letter": "",
                        "isBlack": False,
                        "number": None,
                        "isThemeLocked": False,
                    }
                )
            else:
                # It's a letter
                frontend_row.append(
                    {
                        "letter": cell,
                        "isBlack": False,
                        "number": None,
                        "isThemeLocked": False,
                    }
                )
        frontend_grid.append(frontend_row)
    return frontend_grid


def frontend_to_cli_grid(frontend_grid: List[List[Dict[str, Any]]]) -> List[List[str]]:
    """
    Convert frontend format grid to CLI format.

    Frontend format: [{"letter": "A", "isBlack": false}, ...]
    CLI format: ["A", "#", ".", ...]
    """
    cli_grid = []
    for row in frontend_grid:
        cli_row = []
        for cell in row:
            if cell.get("isBlack", False):
                cli_row.append("#")
            elif cell.get("letter", ""):
                cli_row.append(cell["letter"].upper())
            else:
                cli_row.append(".")
        cli_grid.append(cli_row)
    return cli_grid


# Load actual test grids from project
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEST_GRIDS_DIR = PROJECT_ROOT / "tests" / "fixtures" / "test_data" / "grids"


def load_cli_grid(filename: str) -> Dict[str, Any]:
    """Load a grid in CLI format from tests/fixtures/test_data/grids/."""
    filepath = TEST_GRIDS_DIR / filename
    with open(filepath) as f:
        data = json.load(f)

    # Ensure size field exists
    if "size" not in data:
        data["size"] = len(data["grid"])

    return data


# ============================================================================
# 11x11 GRIDS
# ============================================================================


def get_11x11_empty_cli():
    """11x11 empty grid in CLI format."""
    return load_cli_grid("demo_11x11_EMPTY.json")


def get_11x11_empty_frontend():
    """11x11 empty grid in frontend format."""
    cli_data = get_11x11_empty_cli()
    return {"size": cli_data["size"], "grid": cli_to_frontend_grid(cli_data["grid"])}


def get_11x11_filled_cli():
    """11x11 filled grid in CLI format."""
    return load_cli_grid("demo_11x11_FILLED.json")


def get_11x11_filled_frontend():
    """11x11 filled grid in frontend format."""
    cli_data = get_11x11_filled_cli()
    return {"size": cli_data["size"], "grid": cli_to_frontend_grid(cli_data["grid"])}


def get_11x11_test_cli():
    """11x11 test grid in CLI format."""
    return load_cli_grid("test_grid_11x11.json")


def get_11x11_test_frontend():
    """11x11 test grid in frontend format."""
    cli_data = get_11x11_test_cli()
    return {"size": cli_data["size"], "grid": cli_to_frontend_grid(cli_data["grid"])}


# ============================================================================
# 15x15 GRIDS
# ============================================================================


def get_15x15_empty_cli():
    """15x15 empty grid in CLI format."""
    # Create a standard 15x15 empty grid with rotational symmetry
    grid = [["." for _ in range(15)] for _ in range(15)]

    # Add black squares in rotational symmetry pattern
    blacks = [
        (0, 4),
        (0, 9),
        (1, 4),
        (1, 9),
        (2, 4),
        (2, 9),
        (3, 3),
        (3, 10),
        (4, 0),
        (4, 1),
        (4, 2),
        (4, 7),
        (4, 8),
        (6, 5),
        (6, 6),
        (6, 7),
        (6, 8),
        (6, 9),
        (7, 6),
    ]

    for row, col in blacks:
        grid[row][col] = "#"
        # Rotational symmetry
        grid[14 - row][14 - col] = "#"

    return {"size": 15, "grid": grid}


def get_15x15_empty_frontend():
    """15x15 empty grid in frontend format."""
    cli_data = get_15x15_empty_cli()
    return {"size": cli_data["size"], "grid": cli_to_frontend_grid(cli_data["grid"])}


def get_15x15_my_puzzle_cli():
    """15x15 'my_puzzle' in CLI format."""
    return load_cli_grid("my_puzzle.json")


def get_15x15_my_puzzle_frontend():
    """15x15 'my_puzzle' in frontend format."""
    cli_data = get_15x15_my_puzzle_cli()
    return {"size": cli_data["size"], "grid": cli_to_frontend_grid(cli_data["grid"])}


def get_15x15_sarahs_puzzle_cli():
    """15x15 'sarahs_puzzle' in CLI format."""
    return load_cli_grid("sarahs_puzzle.json")


def get_15x15_sarahs_puzzle_frontend():
    """15x15 'sarahs_puzzle' in frontend format."""
    cli_data = get_15x15_sarahs_puzzle_cli()
    return {"size": cli_data["size"], "grid": cli_to_frontend_grid(cli_data["grid"])}


# ============================================================================
# 21x21 GRIDS
# ============================================================================


def get_21x21_empty_cli():
    """21x21 empty grid in CLI format."""
    data = load_cli_grid("demo_21x21_EMPTY.json")
    # Fix missing size field
    if "size" not in data:
        data["size"] = 21
    return data


def get_21x21_empty_frontend():
    """21x21 empty grid in frontend format."""
    cli_data = get_21x21_empty_cli()
    return {"size": 21, "grid": cli_to_frontend_grid(cli_data["grid"])}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def validate_transformation(
    frontend_grid: List[List[Dict]], expected_cli: List[List[str]]
) -> bool:
    """
    Validate that frontend → CLI transformation is correct.

    This is the critical transformation that was broken in the bug.
    """
    transformed_cli = frontend_to_cli_grid(frontend_grid)
    return transformed_cli == expected_cli


def get_all_realistic_grids():
    """Get all realistic test grids for comprehensive testing."""
    return {
        "11x11_empty_cli": get_11x11_empty_cli(),
        "11x11_empty_frontend": get_11x11_empty_frontend(),
        "11x11_filled_cli": get_11x11_filled_cli(),
        "11x11_filled_frontend": get_11x11_filled_frontend(),
        "11x11_test_cli": get_11x11_test_cli(),
        "11x11_test_frontend": get_11x11_test_frontend(),
        "15x15_empty_cli": get_15x15_empty_cli(),
        "15x15_empty_frontend": get_15x15_empty_frontend(),
        "15x15_my_puzzle_cli": get_15x15_my_puzzle_cli(),
        "15x15_my_puzzle_frontend": get_15x15_my_puzzle_frontend(),
        "15x15_sarahs_cli": get_15x15_sarahs_puzzle_cli(),
        "15x15_sarahs_frontend": get_15x15_sarahs_puzzle_frontend(),
        "21x21_empty_cli": get_21x21_empty_cli(),
        "21x21_empty_frontend": get_21x21_empty_frontend(),
    }
