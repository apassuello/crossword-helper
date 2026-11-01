"""
Clue-check route (clue-authoring spec 0.1.4, section 3.6).

Decision 6 (clue-authoring spec 0.1.4, section 1): the CLI is the only clue
validator; this module only relays its verdict over HTTP.
"""

import subprocess

from flask import Blueprint, jsonify, request

from backend.api.errors import handle_error
from backend.api.validators import validate_grid_request
from backend.core.cli_adapter import ClueCheckOutputError, get_adapter

clue_api = Blueprint("clue", __name__)

cli_adapter = get_adapter()


@clue_api.route("/clues/check", methods=["POST"])
def check_clues():
    """POST /api/clues/check - per-clue status via the CLI.

    Decision 6 (clue-authoring spec 0.1.4, section 1); spec section 3.6.
    ``clues`` is not inspected here: the CLI validates it.
    """
    try:
        if not request.is_json:
            return handle_error("INVALID_CONTENT_TYPE", "Content-Type must be application/json", 400)

        try:
            data = request.get_json()
        except Exception as e:
            return handle_error("INVALID_JSON", f"Failed to parse JSON: {str(e)}", 400)

        if data is None:
            return handle_error("EMPTY_BODY", "Request body cannot be empty", 400)

        try:
            data = validate_grid_request(data)
        except ValueError as e:
            return handle_error("INVALID_GRID", str(e), 400)

        grid_size = data.get("size", len(data.get("grid", [])))
        allow_nonstandard = grid_size not in [11, 15, 21]

        result = cli_adapter.clues_check(grid_data=data, allow_nonstandard=allow_nonstandard)

        if not isinstance(result, dict):
            return handle_error("INTERNAL_ERROR", "Clue check returned unreadable output", 500)

        if result.get("success") is True:
            return jsonify(result), 200

        code = "INVALID_CLUES" if result.get("code") == "INVALID_CLUES" else "INVALID_GRID"
        return handle_error(code, str(result.get("error", "")), 400)

    except ClueCheckOutputError:
        return handle_error("INTERNAL_ERROR", "Clue check returned unreadable output", 500)
    except subprocess.TimeoutExpired:
        return handle_error("TIMEOUT", "Clue check timed out", 504)
    except Exception:
        return handle_error("INTERNAL_ERROR", "Clue check failed", 500)
