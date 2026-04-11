"""
API routes for constraint analysis.

Provides endpoints for grid-wide constraint heatmap data
and single-word placement impact analysis.
"""

from flask import Blueprint, jsonify, request

from backend.core.cli_adapter import CLIAdapter
from backend.core.wordlist_resolver import resolve_wordlist_paths

constraint_bp = Blueprint("constraint_api", __name__)


@constraint_bp.route("/constraints", methods=["POST"])
def get_constraints():
    """
    Get per-cell constraint data for the grid.

    Request body:
        {
            "grid": [[cell, ...], ...],
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

    wordlist_names = data.get("wordlists", ["comprehensive"])
    wordlist_paths = resolve_wordlist_paths(wordlist_names)

    if not wordlist_paths:
        return jsonify({"error": "No valid wordlists found"}), 400

    grid_data = {
        "size": len(grid),
        "grid": grid,
    }

    try:
        adapter = CLIAdapter()
        result = adapter.analyze_constraints(grid_data, wordlist_paths)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@constraint_bp.route("/constraints/impact", methods=["POST"])
def get_placement_impact():
    """
    Get impact of placing a word on crossing slots.

    Request body:
        {
            "grid": [[cell, ...], ...],
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

    wordlist_names = data.get("wordlists", ["comprehensive"])
    wordlist_paths = resolve_wordlist_paths(wordlist_names)

    if not wordlist_paths:
        return jsonify({"error": "No valid wordlists found"}), 400

    grid_data = {
        "size": len(grid),
        "grid": grid,
    }

    try:
        adapter = CLIAdapter()
        result = adapter.analyze_placement_impact(grid_data, word, slot, wordlist_paths)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
