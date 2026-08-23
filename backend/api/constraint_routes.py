"""
API routes for constraint analysis.

Provides endpoints for grid-wide constraint heatmap data
and single-word placement impact analysis.
"""

import logging
import subprocess

from flask import Blueprint, jsonify, request

from backend.api.validators import normalize_grid_to_cli
from backend.core.cli_adapter import CLIAdapter
from backend.core.wordlist_resolver import resolve_wordlist_paths_strict

logger = logging.getLogger(__name__)

constraint_bp = Blueprint("constraint_api", __name__)


def _resolve_wordlists_or_error(data):
    """Resolve requested wordlists; return (paths, error_response)."""
    wordlist_names = data.get("wordlists", ["comprehensive"])
    wordlist_paths, missing = resolve_wordlist_paths_strict(wordlist_names)

    if missing:
        return None, (
            jsonify({"error": f"Unknown wordlist(s): {', '.join(missing)}"}),
            400,
        )
    if not wordlist_paths:
        return None, (jsonify({"error": "No valid wordlists found"}), 400)
    return wordlist_paths, None


@constraint_bp.route("/constraints", methods=["POST"])
def get_constraints():
    """
    Get per-cell constraint data for the grid.

    Request body:
        {
            "grid": [[cell, ...], ...],   # CLI strings OR frontend dict cells
            "wordlists": ["comprehensive", ...]
        }

    Returns:
        JSON with 'constraints' and 'summary' keys.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    grid = data.get("grid")
    if not grid:
        return jsonify({"error": "grid is required"}), 400

    # Accept both grid formats: CLI strings ('#'/'.'/letter) and frontend
    # dict cells ({letter, isBlack}); reject malformed grids with a 400.
    try:
        cli_grid = normalize_grid_to_cli(grid)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    wordlist_paths, error = _resolve_wordlists_or_error(data)
    if error:
        return error

    grid_data = {
        "size": len(cli_grid),
        "grid": cli_grid,
    }

    try:
        adapter = CLIAdapter()
        result = adapter.analyze_constraints(grid_data, wordlist_paths)
        return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Constraint analysis timed out"}), 504
    except Exception as e:
        # Log the full details server-side, but never leak the subprocess
        # command line or filesystem paths to the client.
        logger.error(f"Constraint analysis failed: {e}")
        return jsonify({"error": "Constraint analysis failed"}), 500


@constraint_bp.route("/constraints/impact", methods=["POST"])
def get_placement_impact():
    """
    Get impact of placing a word on crossing slots.

    Request body:
        {
            "grid": [[cell, ...], ...],   # CLI strings OR frontend dict cells
            "word": "OCEAN",
            "slot": {"row": 0, "col": 0, "direction": "across", "length": 5},
            "wordlists": ["comprehensive", ...]
        }

    Returns:
        JSON with 'impacts' and 'summary' keys.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    grid = data.get("grid")
    word = data.get("word")
    slot = data.get("slot")

    if not grid:
        return jsonify({"error": "grid is required"}), 400
    if not word:
        return jsonify({"error": "word is required"}), 400
    if not slot:
        return jsonify({"error": "slot is required"}), 400

    for key in ("row", "col", "direction", "length"):
        if key not in slot:
            return jsonify({"error": f"slot.{key} is required"}), 400

    # Accept both grid formats (CLI strings and frontend dict cells)
    try:
        cli_grid = normalize_grid_to_cli(grid)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    wordlist_paths, error = _resolve_wordlists_or_error(data)
    if error:
        return error

    grid_data = {
        "size": len(cli_grid),
        "grid": cli_grid,
    }

    try:
        adapter = CLIAdapter()
        result = adapter.analyze_placement_impact(grid_data, word, slot, wordlist_paths)
        return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Placement impact analysis timed out"}), 504
    except Exception as e:
        logger.error(f"Placement impact analysis failed: {e}")
        return jsonify({"error": "Placement impact analysis failed"}), 500
