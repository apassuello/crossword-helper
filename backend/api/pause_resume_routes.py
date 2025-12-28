"""
Pause/Resume API routes for autofill operations.

Provides endpoints for:
- Pausing active autofill tasks
- Resuming from saved state with optional user edits
- Managing saved state files
"""

from flask import Blueprint, request, jsonify
from backend.core.edit_merger import EditMerger
from backend.api.errors import handle_error
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

pause_resume_api = Blueprint("pause_resume", __name__)

# Initialize edit merger
edit_merger = EditMerger()

# State storage directory
STATE_STORAGE_DIR = Path(__file__).parent.parent / "data" / "autofill_states"
STATE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


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

        # Create pause controller for this task
        pause_controller = PauseController(task_id=task_id)

        # Request pause
        pause_controller.request_pause()

        logger.info(f"Pause requested for task: {task_id}")

        return jsonify({
            "success": True,
            "message": f"Pause requested for task {task_id}",
            "task_id": task_id
        }), 200

    except Exception as e:
        logger.error(f"Error requesting pause for task {task_id}: {e}")
        return handle_error(e, default_status=500)


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
                "state_saved": true
            }
        404: Task not found or already completed
        500: Server error

    Example:
        POST /api/fill/cancel/task_abc123
        -> {"success": true, "message": "Autofill cancelled"}

    Behavior:
        - Sets pause flag to stop CLI process gracefully
        - CLI will save state before exiting (can resume later if desired)
        - Similar to pause, but signals user intent to abandon task
    """
    try:
        from cli.src.fill.pause_controller import PauseController

        # Create pause controller for this task
        pause_controller = PauseController(task_id=task_id)

        # Request pause (same mechanism as pause, but semantically different)
        # The CLI will save state and exit. Frontend marks this as "cancelled"
        pause_controller.request_pause()

        logger.info(f"Cancel requested for task: {task_id}")

        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "Autofill cancelled",
            "state_saved": True  # CLI saves state before exiting
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        return handle_error(e, default_status=500)


@pause_resume_api.route("/fill/resume", methods=["POST"])
def resume_autofill():
    """
    POST /api/fill/resume

    Resume paused autofill with optional user edits.

    Request Body:
        {
            "task_id": "task_abc123",
            "edited_grid": [[...], ...],  # Optional: grid with user edits
            "options": {                   # Same as original fill options
                "min_score": 50,
                "timeout": 300,
                "wordlists": ["comprehensive"],
                "algorithm": "trie"
            }
        }

    Returns:
        200: Resume started successfully
            {
                "success": true,
                "new_task_id": "task_xyz456",
                "original_task_id": "task_abc123",
                "message": "Resume started"
            }
        400: Invalid request (missing task_id, invalid grid, etc.)
        404: Saved state not found
        409: State incompatible with edits (unsolvable)
        500: Server error

    Example:
        POST /api/fill/resume
        {
            "task_id": "task_abc123",
            "edited_grid": [[["R"], ["A"], ...], ...],
            "options": {"min_score": 50, "timeout": 300}
        }
    """
    try:
        data = request.get_json()

        # Validate request
        if not data or 'task_id' not in data:
            return jsonify({
                "error": "Missing required field: task_id"
            }), 400

        task_id = data['task_id']
        edited_grid = data.get('edited_grid')
        options = data.get('options', {})

        # Load saved state
        from cli.src.fill.state_manager import StateManager

        state_manager = StateManager(storage_dir=STATE_STORAGE_DIR)

        try:
            saved_state, metadata = state_manager.load_csp_state(task_id)
        except FileNotFoundError:
            return jsonify({
                "error": f"Saved state not found for task_id: {task_id}"
            }), 404

        # If user provided edited grid, merge edits
        if edited_grid is not None:
            try:
                # Convert edited_grid to proper dict format
                edited_grid_dict = {
                    'size': len(edited_grid),
                    'grid': edited_grid
                }

                # Merge edits into saved state
                updated_state = edit_merger.merge_edits(
                    saved_state=saved_state,
                    edited_grid_dict=edited_grid_dict
                )

                logger.info(f"Merged user edits into state for task {task_id}")

            except ValueError as e:
                # Edits create unsolvable state
                logger.warning(f"User edits create unsolvable state: {e}")
                return jsonify({
                    "error": "User edits create unsolvable configuration",
                    "details": str(e)
                }), 409

        else:
            # No edits, use saved state as-is
            updated_state = saved_state

        # Generate new task ID for resume
        import uuid
        new_task_id = f"resume_{uuid.uuid4().hex[:8]}"

        # Save updated state with new task ID
        state_manager.save_csp_state(
            task_id=new_task_id,
            csp_state=updated_state,
            metadata={
                **metadata,
                'resumed_from': task_id,
                'resume_options': options
            },
            compress=True
        )

        logger.info(f"Resume prepared: {task_id} -> {new_task_id}")

        # Return new task ID for client to start autofill
        return jsonify({
            "success": True,
            "new_task_id": new_task_id,
            "original_task_id": task_id,
            "message": "Resume state prepared",
            "slots_filled": metadata.get('slots_filled', 0),
            "total_slots": metadata.get('total_slots', 0)
        }), 200

    except Exception as e:
        logger.error(f"Error resuming autofill: {e}", exc_info=True)
        return handle_error(e, default_status=500)


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
        from cli.src.fill.state_manager import StateManager
        from cli.src.core.grid import Grid

        state_manager = StateManager(storage_dir=STATE_STORAGE_DIR)

        try:
            # Get state info (lightweight)
            info = state_manager.get_state_info(task_id)

            # Load full state to get grid preview
            saved_state, metadata = state_manager.load_csp_state(task_id)
            grid = Grid.from_dict(saved_state.grid_dict)

            # Return info with grid preview
            return jsonify({
                **info,
                "grid_preview": saved_state.grid_dict['grid']
            }), 200

        except FileNotFoundError:
            return jsonify({
                "error": f"State not found for task_id: {task_id}"
            }), 404

    except Exception as e:
        logger.error(f"Error getting state info for {task_id}: {e}")
        return handle_error(e, default_status=500)


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
        from cli.src.fill.state_manager import StateManager

        state_manager = StateManager(storage_dir=STATE_STORAGE_DIR)

        deleted = state_manager.delete_state(task_id)

        if deleted:
            logger.info(f"Deleted state for task: {task_id}")
            return jsonify({
                "success": True,
                "message": f"State deleted for task {task_id}"
            }), 200
        else:
            return jsonify({
                "error": f"State not found for task_id: {task_id}"
            }), 404

    except Exception as e:
        logger.error(f"Error deleting state for {task_id}: {e}")
        return handle_error(e, default_status=500)


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
        from cli.src.fill.state_manager import StateManager

        state_manager = StateManager(storage_dir=STATE_STORAGE_DIR)

        # Get optional max_age parameter
        max_age_days = request.args.get('max_age_days', type=int)

        # List states
        states = state_manager.list_states(max_age_days=max_age_days)

        return jsonify({
            "states": states,
            "count": len(states)
        }), 200

    except Exception as e:
        logger.error(f"Error listing states: {e}")
        return handle_error(e, default_status=500)


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
        from cli.src.fill.state_manager import StateManager

        data = request.get_json() or {}
        max_age_days = data.get('max_age_days', 7)

        state_manager = StateManager(storage_dir=STATE_STORAGE_DIR)

        deleted_count = state_manager.cleanup_old_states(max_age_days=max_age_days)

        logger.info(f"Cleaned up {deleted_count} old state files")

        return jsonify({
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} old state files"
        }), 200

    except Exception as e:
        logger.error(f"Error cleaning up states: {e}")
        return handle_error(e, default_status=500)


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
                "new_words": ["WORD1", "WORD2"],
                "removed_words": ["OLD1"]
            }
        400: Invalid request
        404: State not found
        500: Server error
    """
    try:
        data = request.get_json()

        if not data or 'task_id' not in data or 'edited_grid' not in data:
            return jsonify({
                "error": "Missing required fields: task_id, edited_grid"
            }), 400

        task_id = data['task_id']
        edited_grid = data['edited_grid']

        # Load saved state
        from cli.src.fill.state_manager import StateManager

        state_manager = StateManager(storage_dir=STATE_STORAGE_DIR)

        try:
            saved_state, _ = state_manager.load_csp_state(task_id)
        except FileNotFoundError:
            return jsonify({
                "error": f"Saved state not found for task_id: {task_id}"
            }), 404

        # Convert edited_grid to proper dict format
        edited_grid_dict = {
            'size': len(edited_grid),
            'grid': edited_grid
        }

        # Get edit summary
        summary = edit_merger.get_edit_summary(
            saved_grid_dict=saved_state.grid_dict,
            edited_grid_dict=edited_grid_dict,
            slot_list=saved_state.slot_list,
            slot_id_map=saved_state.slot_id_map
        )

        return jsonify(summary), 200

    except Exception as e:
        logger.error(f"Error getting edit summary: {e}")
        return handle_error(e, default_status=500)
