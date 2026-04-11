"""
Grid helper API routes.

Handles grid manipulation helpers like black square suggestions.
"""

import logging

from flask import Blueprint, jsonify, request

from backend.api.errors import handle_error
from backend.core.black_square_suggester import (
    BlackSquareSuggester,
    validate_grid_for_black_squares,
)

logger = logging.getLogger(__name__)

grid_api = Blueprint("grid", __name__)


@grid_api.route("/grid/suggest-black-square", methods=["POST"])
def suggest_black_square():
    """
    POST /api/grid/suggest-black-square

    Suggest strategic black square placements to resolve stuck fills.

    Request:
    {
        "grid": [[...], ...],
        "grid_size": 15,
        "problematic_slot": {
            "row": 0,
            "col": 0,
            "direction": "across",
            "length": 15,
            "pattern": "???????????????",
            "candidate_count": 0
        },
        "max_suggestions": 3
    }

    Response:
    {
        "suggestions": [
            {
                "position": 7,
                "row": 0,
                "col": 7,
                "score": 850,
                "reasoning": "Balanced split (7+7 letters), Both lengths in sweet spot (3-7), ...",
                "left_length": 7,
                "right_length": 7,
                "symmetric_position": {"row": 14, "col": 7},
                "new_word_count": 77,
                "constraint_reduction": 4
            },
            ...
        ],
        "slot_info": {...}
    }
    """
    try:
        data = request.get_json()

        # Validate input
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        if "grid" not in data:
            return jsonify({"error": "Missing grid"}), 400

        if "problematic_slot" not in data:
            return jsonify({"error": "Missing problematic_slot"}), 400

        grid = data["grid"]
        grid_size = data.get("grid_size", 15)
        slot = data["problematic_slot"]
        max_suggestions = data.get("max_suggestions", 3)

        # Validate slot
        required_slot_fields = ["row", "col", "direction", "length"]
        if not all(field in slot for field in required_slot_fields):
            return jsonify({"error": "Incomplete slot data"}), 400

        # Validate grid
        validation = validate_grid_for_black_squares(grid, grid_size)
        if not validation["valid"]:
            return jsonify({"error": "Invalid grid", "validation": validation}), 400

        # Create suggester and generate suggestions
        suggester = BlackSquareSuggester(grid_size)
        suggestions = suggester.suggest_placements(grid, slot, max_suggestions=max_suggestions)

        # Check if any suggestions found
        if not suggestions:
            return (
                jsonify(
                    {
                        "suggestions": [],
                        "message": "No viable black square positions found for this slot",
                        "slot_info": slot,
                    }
                ),
                200,
            )

        return (
            jsonify(
                {
                    "suggestions": suggestions,
                    "slot_info": slot,
                    "grid_size": grid_size,
                    "validation": validation,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error suggesting black square: {e}", exc_info=True)
        return handle_error(e, default_status=500)


@grid_api.route("/grid/apply-black-squares", methods=["POST"])
def apply_black_squares():
    """
    POST /api/grid/apply-black-squares

    Apply black square placements (symmetric pair) to grid.

    Request:
    {
        "grid": [[...], ...],
        "primary": {"row": 0, "col": 7},
        "symmetric": {"row": 14, "col": 7}
    }

    Response:
    {
        "grid": [[...], ...],  // Updated grid
        "applied": true,
        "positions": [
            {"row": 0, "col": 7},
            {"row": 14, "col": 7}
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or "grid" not in data or "primary" not in data or "symmetric" not in data:
            return jsonify({"error": "Missing grid or positions"}), 400

        grid = data["grid"]
        primary = data["primary"]
        symmetric = data["symmetric"]

        # Apply black squares
        positions = [primary, symmetric]

        for pos in positions:
            row = pos["row"]
            col = pos["col"]

            if not (0 <= row < len(grid) and 0 <= col < len(grid[row])):
                continue

            cell = grid[row][col]
            if isinstance(cell, dict):
                cell["isBlack"] = True
                cell["letter"] = ""
                cell["isThemeLocked"] = False
            else:
                grid[row][col] = "#"

        return jsonify({"grid": grid, "applied": True, "positions": positions}), 200

    except Exception as e:
        logger.error(f"Error applying black squares: {e}", exc_info=True)
        return handle_error(e, default_status=500)


@grid_api.route("/grid/validate", methods=["POST"])
def validate_grid():
    """
    POST /api/grid/validate

    Validate grid quality and statistics.

    Request:
    {
        "grid": [[...], ...],
        "grid_size": 15
    }

    Response:
    {
        "valid": true,
        "word_count": 76,
        "black_square_count": 38,
        "black_square_percentage": 16.8,
        "warnings": [],
        "suggestions": []
    }
    """
    try:
        data = request.get_json()

        if not data or "grid" not in data:
            return jsonify({"error": "Missing grid"}), 400

        grid = data["grid"]
        grid_size = data.get("grid_size", 15)

        # Validate grid structure
        validation = validate_grid_for_black_squares(grid, grid_size)

        # Count words
        suggester = BlackSquareSuggester(grid_size)
        word_count = suggester._count_words(grid)

        # Count black squares
        black_count = sum(
            1 for row in grid for cell in row if (isinstance(cell, dict) and cell.get("isBlack", False)) or cell == "#"
        )

        total_cells = grid_size * grid_size
        black_percentage = (black_count / total_cells) * 100

        # Get word count range
        min_words, max_words = suggester.word_count_ranges.get(grid_size, (70, 80))

        # Generate suggestions
        suggestions = []
        if word_count < min_words:
            suggestions.append(f"Low word count ({word_count}). Try adding black squares to reach {min_words}-{max_words}.")
        elif word_count > max_words:
            suggestions.append(f"High word count ({word_count}). Consider removing some black squares.")

        if black_percentage > 20:
            suggestions.append(f"High black square percentage ({black_percentage:.1f}%). Standard is ~16-18%.")

        return (
            jsonify(
                {
                    "valid": validation["valid"],
                    "word_count": word_count,
                    "black_square_count": black_count,
                    "black_square_percentage": round(black_percentage, 1),
                    "word_count_range": [min_words, max_words],
                    "warnings": validation.get("warnings", []),
                    "suggestions": suggestions,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error validating grid: {e}", exc_info=True)
        return handle_error(e, default_status=500)
