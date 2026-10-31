"""
Theme word API routes.

Handles theme word uploads, placement suggestions, and validation.
"""

import logging

from flask import Blueprint, jsonify, request

from backend.api.errors import handle_error
from backend.core.placement_validation import apply_checked_placement
from backend.core.theme_placer import ThemePlacer

logger = logging.getLogger(__name__)

theme_api = Blueprint("theme", __name__)


@theme_api.route("/theme/upload", methods=["POST"])
def upload_theme_words():
    """
    POST /api/theme/upload

    Upload theme words from file content.

    Request:
    {
        "content": "WORD1\\nWORD2\\nWORD3",
        "grid_size": 15
    }

    Response:
    {
        "words": ["WORD1", "WORD2", "WORD3"],
        "count": 3,
        "validation": {
            "valid": true,
            "errors": [],
            "warnings": []
        }
    }
    """
    try:
        data = request.get_json()

        if not data or "content" not in data:
            return jsonify({"error": "Missing content"}), 400

        grid_size = data.get("grid_size", 15)

        # Parse words from content
        lines = data["content"].split("\n")
        words = [line.strip().upper() for line in lines if line.strip()]

        # Remove duplicates while preserving order
        seen = set()
        unique_words = []
        for word in words:
            if word not in seen and word.isalpha():
                seen.add(word)
                unique_words.append(word)

        # Validate words
        placer = ThemePlacer(grid_size)
        validation = placer.validate_theme_words(unique_words)

        return (
            jsonify(
                {
                    "words": unique_words,
                    "count": len(unique_words),
                    "validation": validation,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error uploading theme words: {e}", exc_info=True)
        return handle_error("INTERNAL_ERROR", str(e), 500)


@theme_api.route("/theme/suggest-placements", methods=["POST"])
def suggest_placements():
    """
    POST /api/theme/suggest-placements

    Suggest optimal placements for theme words.

    Request:
    {
        "theme_words": ["WORD1", "WORD2", "WORD3"],
        "grid_size": 15,
        "existing_grid": [[...], ...],  // Optional
        "max_suggestions": 3
    }

    Response:
    {
        "suggestions": [
            {
                "word": "WORD1",
                "length": 5,
                "suggestions": [
                    {
                        "row": 7,
                        "col": 5,
                        "direction": "across",
                        "score": 95,
                        "reasoning": "Centered placement (symmetric), Good horizontal position"
                    },
                    ...
                ]
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or "theme_words" not in data:
            return jsonify({"error": "Missing theme_words"}), 400

        theme_words = data["theme_words"]
        grid_size = data.get("grid_size", 15)
        existing_grid = data.get("existing_grid")
        max_suggestions = data.get("max_suggestions", 3)

        # Validate input
        if not isinstance(theme_words, list):
            return jsonify({"error": "theme_words must be a list"}), 400

        if not theme_words:
            return jsonify({"error": "theme_words cannot be empty"}), 400

        # Create placer and generate suggestions
        placer = ThemePlacer(grid_size)

        # Validate words first
        validation = placer.validate_theme_words(theme_words)
        if not validation["valid"]:
            return (
                jsonify({"error": "Invalid theme words", "validation": validation}),
                400,
            )

        # Generate suggestions
        suggestions = placer.suggest_placements(
            theme_words,
            existing_grid=existing_grid,
            max_suggestions_per_word=max_suggestions,
        )

        return jsonify({"suggestions": suggestions, "grid_size": grid_size}), 200

    except Exception as e:
        logger.error(f"Error suggesting placements: {e}", exc_info=True)
        return handle_error("INTERNAL_ERROR", str(e), 500)


@theme_api.route("/theme/validate", methods=["POST"])
def validate_theme_words():
    """
    POST /api/theme/validate

    Validate theme words without generating placements.

    Request:
    {
        "theme_words": ["WORD1", "WORD2"],
        "grid_size": 15
    }

    Response:
    {
        "valid": true,
        "errors": [],
        "warnings": ["WORD1: Very long (11 letters), may be hard to place"]
    }
    """
    try:
        data = request.get_json()

        if not data or "theme_words" not in data:
            return jsonify({"error": "Missing theme_words"}), 400

        theme_words = data["theme_words"]
        grid_size = data.get("grid_size", 15)

        # Validate
        placer = ThemePlacer(grid_size)
        validation = placer.validate_theme_words(theme_words)

        return jsonify(validation), 200

    except Exception as e:
        logger.error(f"Error validating theme words: {e}", exc_info=True)
        return handle_error("INTERNAL_ERROR", str(e), 500)


@theme_api.route("/theme/apply-placement", methods=["POST"])
def apply_placement():
    """
    POST /api/theme/apply-placement

    Apply a theme word placement to grid and return updated grid.

    Request:
    {
        "grid": [[...], ...],
        "placement": {
            "word": "EXAMPLE",
            "row": 7,
            "col": 4,
            "direction": "across"
        }
    }

    Response:
    {
        "grid": [[...], ...],  // Updated grid
        "applied": true,
        "added_black_squares": [[0, 4], [10, 6]]  // [row, col] of each black square
                                                  // the apply added: the word's boundary
                                                  // squares and their symmetric twins
    }
    """
    try:
        data = request.get_json()

        if not data or "grid" not in data or "placement" not in data:
            return jsonify({"error": "Missing grid or placement"}), 400

        grid = data["grid"]
        placement = data["placement"]

        # Validate placement
        required_fields = ["word", "row", "col", "direction"]
        if not all(field in placement for field in required_fields):
            return jsonify({"error": "Incomplete placement data"}), 400

        # Single source of truth for conflict detection (cell/intersection
        # conflicts and 180-degree rotational-symmetry boundary conflicts) and
        # for the write step (theme-locked letters, boundary + twin blacks) —
        # see backend/core/placement_validation.py. ThemePlacer's suggestions
        # and joint plan use the same function, so no candidate reaches this
        # endpoint that this check would reject.
        conflicts, added_blacks = apply_checked_placement(grid, placement)

        # If there are conflicts, return error with details
        if conflicts:
            return (
                jsonify(
                    {
                        "error": "Placement conflicts detected",
                        "conflicts": conflicts,
                        "applied": False,
                    }
                ),
                400,
            )

        return jsonify({"grid": grid, "applied": True, "added_black_squares": added_blacks}), 200

    except Exception as e:
        logger.error(f"Error applying placement: {e}", exc_info=True)
        return handle_error("INTERNAL_ERROR", str(e), 500)
