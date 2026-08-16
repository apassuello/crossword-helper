"""
Pause/Resume API routes for autofill operations.

Provides endpoints for:
- Pausing active autofill tasks
- Resuming from saved state with optional user edits
- Managing saved state files

State files live in the CLI StateManager's store (/tmp/crossword_states by
default) — the SAME location the CLI writes to when a fill pauses. The
backend used to keep a second, disjoint store (backend/data/autofill_states)
which meant the web API could never see states the CLI saved.
"""

import logging
import subprocess
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

from backend.api.errors import handle_error
from backend.api.validators import normalize_grid_to_cli
from backend.core.cli_adapter import get_adapter
from backend.core.edit_merger import EditMerger
from backend.core.state_paths import PAUSE_FLAG_DIR
from backend.core.state_paths import STATE_DIR as STATE_STORAGE_DIR
from backend.core.wordlist_resolver import (
    get_default_wordlist_paths,
    resolve_wordlist_paths_strict,
)

logger = logging.getLogger(__name__)

pause_resume_api = Blueprint("pause_resume", __name__)

# Initialize edit merger
edit_merger = EditMerger()

# State + pause-flag dirs are single-sourced from backend.core.state_paths (DD1):
# STATE_STORAGE_DIR (alias of STATE_DIR) is read in one place, _get_state_manager()
# below, which every route calls instead of constructing a StateManager itself;
# PAUSE_FLAG_DIR is threaded into the PauseController constructions so the flag the
# backend writes lands where the spawned CLI reads it.


def _get_state_manager():
    """Create a StateManager bound to the shared CLI state store."""
    from cli.src.fill.state_manager import StateManager

    return StateManager(storage_dir=STATE_STORAGE_DIR)


def _normalize_edited_grid(edited_grid, saved_grid_dict):
    """
    Convert a client-submitted edited grid to a CLI-format grid dict.

    Accepts frontend dict cells ({letter, isBlack}), legacy single-letter
    list cells (["A"] / ["."]), and CLI strings. Black squares from the
    saved state are preserved for cell formats that don't carry black-square
    information (the frontend resume payload is lossy in that respect).
    """
    reference = saved_grid_dict.get("grid") if isinstance(saved_grid_dict, dict) else None
    cli_grid = normalize_grid_to_cli(edited_grid, reference_grid=reference)
    return {"size": len(cli_grid), "grid": cli_grid}


@pause_resume_api.route("/fill/pause/<task_id>", methods=["POST"])
def pause_autofill(task_id: str):
    """
    POST /api/fill/pause/<task_id>

    Request autofill to pause.

    Path Parameters:
        task_id: Unique task identifier

    Returns:
        200: Pause requested successfully
        404: Task not found or not running
        500: Server error

    Example:
        POST /api/fill/pause/task_abc123
        -> {"success": true, "message": "Pause requested"}
    """
    try:
        from cli.src.fill.pause_controller import PauseController

        from .progress_routes import is_process_running

        # Create pause controller for this task
        pause_controller = PauseController(task_id=task_id, pause_dir=PAUSE_FLAG_DIR)

        # Only accept pause requests for tasks that are actually running:
        # either a subprocess this backend launched, or a CLI fill that
        # registered a running marker for this task id.
        if not (is_process_running(task_id) or pause_controller.is_task_running()):
            return handle_error(
                "TASK_NOT_FOUND",
                f"No running fill found for task {task_id}",
                404,
            )

        # Request pause
        pause_controller.request_pause()

        logger.info(f"Pause requested for task: {task_id}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Pause requested for task {task_id}",
                    "task_id": task_id,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error requesting pause for task {task_id}: {e}")
        return handle_error("INTERNAL_ERROR", str(e), 500)


@pause_resume_api.route("/fill/cancel/<task_id>", methods=["POST"])
def cancel_autofill(task_id: str):
    """
    POST /api/fill/cancel/<task_id>

    Cancel a running autofill task.

    Path Parameters:
        task_id: Unique task identifier

    Returns:
        200: Cancel request processed
            {
                "success": true,
                "task_id": "task_abc123",
                "message": "Autofill cancelled",
                "state_saved": false
            }
        404: Task not found or already completed
        500: Server error

    Behavior:
        - Terminates the CLI subprocess immediately (hard stop)
        - No state is saved — cancel is NOT resumable (use pause for that)
        - Clears any stale pause flag / running marker for the task id
    """
    try:
        from cli.src.fill.pause_controller import PauseController

        from .progress_routes import cleanup_process, is_process_running

        # Create pause controller for this task
        pause_controller = PauseController(task_id=task_id, pause_dir=PAUSE_FLAG_DIR)

        if not is_process_running(task_id):
            return handle_error(
                "TASK_NOT_FOUND",
                f"No running fill found for task {task_id}",
                404,
            )

        # Terminate the subprocess (hard stop — the CLI does not checkpoint)
        cleanup_process(task_id)

        # Clean up any pause/running marker files so a stale flag can't
        # instantly pause a future run reusing this task id.
        pause_controller = PauseController(task_id=task_id, pause_dir=PAUSE_FLAG_DIR)
        pause_controller.clear_pause()
        pause_controller.clear_running()

        logger.info(f"Cancel requested for task: {task_id}")

        return (
            jsonify(
                {
                    "success": True,
                    "task_id": task_id,
                    "message": "Autofill cancelled",
                    # Honest reporting: cancelling kills the process without
                    # a checkpoint, so there is nothing to resume from.
                    "state_saved": False,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return handle_error("INTERNAL_ERROR", str(e), 500)


@pause_resume_api.route("/fill/resume", methods=["POST"])
def resume_autofill():
    """
    POST /api/fill/resume

    Resume paused autofill with optional user edits. Merges any edits into
    the saved state, saves it under a new task id, then runs the CLI resume
    (`fill --resume <state> --task-id <new_id> ...`) and returns the result.

    Request Body:
        {
            "task_id": "task_abc123",
            "edited_grid": [[...], ...],  # Optional: grid with user edits
                                          # (dict cells, ["A"] cells, or strings)
            "options": {                   # Same as original fill options
                "min_score": 50,
                "timeout": 300,
                "wordlists": ["comprehensive"],
                "algorithm": "trie"
            }
        }

    Returns:
        200: Resume completed (fill ran to completion, partial, or re-paused)
            {
                "success": true,
                "new_task_id": "resume_xyz456",
                "original_task_id": "task_abc123",
                "message": "...",
                "result": { ... CLI fill result: grid, slots_filled, ... }
            }
        400: Invalid request (missing task_id, invalid grid, etc.)
        404: Saved state not found
        409: State incompatible with edits (unsolvable)
        504: Resume timed out
        500: Server error
    """
    try:
        data = request.get_json(silent=True)

        # Validate request
        if not data or "task_id" not in data:
            return jsonify({"error": "Missing required field: task_id"}), 400

        task_id = data["task_id"]
        edited_grid = data.get("edited_grid")
        options = data.get("options") or {}

        # Load saved state from the shared CLI state store
        state_manager = _get_state_manager()

        try:
            saved_state, metadata = state_manager.load_csp_state(task_id)
        except FileNotFoundError:
            return (
                jsonify({"error": f"Saved state not found for task_id: {task_id}"}),
                404,
            )

        # If user provided edited grid, merge edits
        if edited_grid is not None:
            try:
                # Convert edited_grid to CLI-format dict (handles frontend
                # dict cells and ["A"]-style cells; preserves black squares)
                edited_grid_dict = _normalize_edited_grid(edited_grid, saved_state.grid_dict)

                # Merge edits into saved state
                updated_state = edit_merger.merge_edits(saved_state=saved_state, edited_grid_dict=edited_grid_dict)

                logger.info(f"Merged user edits into state for task {task_id}")

            except ValueError as e:
                # Edits create unsolvable state
                logger.warning(f"User edits create unsolvable state: {e}")
                return (
                    jsonify(
                        {
                            "error": "User edits create unsolvable configuration",
                            "details": str(e),
                        }
                    ),
                    409,
                )

        else:
            # No edits, use saved state as-is
            updated_state = saved_state

        # Generate new task ID for resume
        new_task_id = f"resume_{uuid.uuid4().hex[:8]}"

        # Save updated state with new task ID (into the shared store)
        state_manager.save_csp_state(
            task_id=new_task_id,
            csp_state=updated_state,
            metadata={**metadata, "resumed_from": task_id, "resume_options": options},
            compress=True,
        )
        state_file_path = STATE_STORAGE_DIR / f"{new_task_id}.json.gz"

        # Resolve wordlists: request options take precedence, then the
        # wordlists recorded in the saved state, then the default list.
        wordlist_names = options.get("wordlists")
        if wordlist_names:
            wordlist_paths, missing = resolve_wordlist_paths_strict(wordlist_names)
            if missing:
                return handle_error(
                    "UNKNOWN_WORDLIST",
                    f"Unknown wordlist(s): {', '.join(missing)}",
                    400,
                    details={"unknown_wordlists": missing},
                )
        else:
            wordlist_paths = [wp for wp in metadata.get("wordlists", []) if Path(wp).exists()]
            if not wordlist_paths:
                wordlist_paths = get_default_wordlist_paths()

        if not wordlist_paths:
            return handle_error("INVALID_WORDLISTS", "No valid wordlists found for resume", 400)

        # Algorithm: request option, else the algorithm recorded in the state
        # (the state manager records classic CSP fills as 'csp' — map that
        # back to the CLI's 'trie' option)
        saved_algorithm = metadata.get("algorithm")
        algorithm = options.get("algorithm") or {"csp": "trie"}.get(saved_algorithm, saved_algorithm) or "trie"

        timeout_seconds = int(options.get("timeout", 300))
        min_score = int(options.get("min_score", metadata.get("min_score", 30)))

        logger.info(f"Resume prepared: {task_id} -> {new_task_id} " f"(algorithm={algorithm}, timeout={timeout_seconds}s)")

        # Run the resumed fill via the CLI (verified invocation:
        # fill --resume <state> --output <o> --timeout T --min-score S
        #      --algorithm A --task-id X --wordlists ...)
        adapter = get_adapter()
        result = adapter.fill_with_resume(
            task_id=new_task_id,
            state_file_path=str(state_file_path),
            wordlist_paths=wordlist_paths,
            timeout_seconds=timeout_seconds,
            min_score=min_score,
            algorithm=algorithm,
        )

        return (
            jsonify(
                {
                    "success": True,
                    "new_task_id": new_task_id,
                    "original_task_id": task_id,
                    "message": "Resume completed",
                    "slots_filled": result.get("slots_filled", metadata.get("slots_filled", 0)),
                    "total_slots": result.get("total_slots", metadata.get("total_slots", 0)),
                    "result": result,
                }
            ),
            200,
        )

    except subprocess.TimeoutExpired:
        return handle_error("TIMEOUT", "Resume timed out", 504)
    except ValueError as e:
        return handle_error("INVALID_REQUEST", str(e), 400)
    except Exception as e:
        logger.error(f"Error resuming autofill: {e}", exc_info=True)
        return handle_error("INTERNAL_ERROR", str(e), 500)


@pause_resume_api.route("/fill/state/<task_id>", methods=["GET"])
def get_saved_state(task_id: str):
    """
    GET /api/fill/state/<task_id>

    Get metadata about saved state without loading full state.

    Path Parameters:
        task_id: Unique task identifier

    Returns:
        200: State info retrieved
            {
                "task_id": "task_abc123",
                "timestamp": "2025-12-26T10:30:00Z",
                "algorithm": "csp",
                "slots_filled": 38,
                "total_slots": 76,
                "grid_size": [15, 15],
                "iteration_count": 1250,
                "grid_preview": [[...], ...]
            }
        404: State not found
        500: Server error

    Example:
        GET /api/fill/state/task_abc123
    """
    try:
        state_manager = _get_state_manager()

        try:
            # Get state info (lightweight)
            info = state_manager.get_state_info(task_id)

            # Load full state to get grid preview
            saved_state, metadata = state_manager.load_csp_state(task_id)

            # Return info with grid preview
            return jsonify({**info, "grid_preview": saved_state.grid_dict["grid"]}), 200

        except FileNotFoundError:
            return jsonify({"error": f"State not found for task_id: {task_id}"}), 404

    except Exception as e:
        logger.error(f"Error getting state info for {task_id}: {e}")
        return handle_error("INTERNAL_ERROR", str(e), 500)


@pause_resume_api.route("/fill/state/<task_id>", methods=["DELETE"])
def delete_saved_state(task_id: str):
    """
    DELETE /api/fill/state/<task_id>

    Delete saved state file.

    Path Parameters:
        task_id: Unique task identifier

    Returns:
        200: State deleted successfully
        404: State not found
        500: Server error

    Example:
        DELETE /api/fill/state/task_abc123
        -> {"success": true, "message": "State deleted"}
    """
    try:
        state_manager = _get_state_manager()

        deleted = state_manager.delete_state(task_id)

        if deleted:
            logger.info(f"Deleted state for task: {task_id}")
            return (
                jsonify({"success": True, "message": f"State deleted for task {task_id}"}),
                200,
            )
        else:
            return jsonify({"error": f"State not found for task_id: {task_id}"}), 404

    except Exception as e:
        logger.error(f"Error deleting state for {task_id}: {e}")
        return handle_error("INTERNAL_ERROR", str(e), 500)


@pause_resume_api.route("/fill/states", methods=["GET"])
def list_saved_states():
    """
    GET /api/fill/states

    List all saved states.

    Query Parameters:
        max_age_days: Only return states newer than this (optional)

    Returns:
        200: List of saved states
            {
                "states": [
                    {
                        "task_id": "task_abc123",
                        "timestamp": "2025-12-26T10:30:00Z",
                        "slots_filled": 38,
                        "total_slots": 76,
                        "grid_size": [15, 15]
                    },
                    ...
                ],
                "count": 5
            }
        500: Server error

    Example:
        GET /api/fill/states?max_age_days=7
    """
    try:
        state_manager = _get_state_manager()

        # Get optional max_age parameter
        max_age_days = request.args.get("max_age_days", type=int)

        # List states
        states = state_manager.list_states(max_age_days=max_age_days)

        return jsonify({"states": states, "count": len(states)}), 200

    except Exception as e:
        logger.error(f"Error listing states: {e}")
        return handle_error("INTERNAL_ERROR", str(e), 500)


@pause_resume_api.route("/fill/states/cleanup", methods=["POST"])
def cleanup_old_states():
    """
    POST /api/fill/states/cleanup

    Delete state files older than specified days.

    Request Body:
        {
            "max_age_days": 7  # Optional, defaults to 7
        }

    Returns:
        200: Cleanup completed
            {
                "success": true,
                "deleted_count": 3,
                "message": "Deleted 3 old state files"
            }
        500: Server error

    Example:
        POST /api/fill/states/cleanup
        {"max_age_days": 7}
    """
    try:
        data = request.get_json(silent=True) or {}
        max_age_days = data.get("max_age_days", 7)

        state_manager = _get_state_manager()

        deleted_count = state_manager.cleanup_old_states(max_age_days=max_age_days)

        logger.info(f"Cleaned up {deleted_count} old state files")

        return (
            jsonify(
                {
                    "success": True,
                    "deleted_count": deleted_count,
                    "message": f"Deleted {deleted_count} old state files",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error cleaning up states: {e}")
        return handle_error("INTERNAL_ERROR", str(e), 500)


@pause_resume_api.route("/fill/edit-summary", methods=["POST"])
def get_edit_summary():
    """
    POST /api/fill/edit-summary

    Get summary of edits without full merge (preview mode).

    Request Body:
        {
            "task_id": "task_abc123",
            "edited_grid": [[...], ...]
        }

    Returns:
        200: Edit summary
            {
                "filled_count": 5,
                "emptied_count": 2,
                "modified_count": 1,
                "partial_count": 1,
                "cells_filled": 3,
                "cells_emptied": 0,
                "cells_changed": 1,
                "new_words": ["WORD1", "WORD2"],
                "removed_words": ["OLD1"]
            }
        400: Invalid request
        404: State not found
        500: Server error
    """
    try:
        data = request.get_json(silent=True)

        if not data or "task_id" not in data or "edited_grid" not in data:
            return (
                jsonify({"error": "Missing required fields: task_id, edited_grid"}),
                400,
            )

        task_id = data["task_id"]
        edited_grid = data["edited_grid"]

        # Load saved state from the shared CLI state store
        state_manager = _get_state_manager()

        try:
            saved_state, _ = state_manager.load_csp_state(task_id)
        except FileNotFoundError:
            return (
                jsonify({"error": f"Saved state not found for task_id: {task_id}"}),
                404,
            )

        # Convert edited_grid to CLI-format dict (handles frontend dict
        # cells and ["A"]-style cells; preserves black squares)
        edited_grid_dict = _normalize_edited_grid(edited_grid, saved_state.grid_dict)

        # Get edit summary
        summary = edit_merger.get_edit_summary(
            saved_grid_dict=saved_state.grid_dict,
            edited_grid_dict=edited_grid_dict,
            slot_list=saved_state.slot_list,
            slot_id_map=saved_state.slot_id_map,
        )

        return jsonify(summary), 200

    except ValueError as e:
        return handle_error("INVALID_REQUEST", str(e), 400)
    except Exception as e:
        logger.error(f"Error getting edit summary: {e}")
        return handle_error("INTERNAL_ERROR", str(e), 500)
