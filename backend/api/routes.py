"""
Flask API routes for crossword helper endpoints.

This module defines HTTP endpoints for pattern matching, grid numbering,
and convention normalization.

PHASE 3 REFACTORING: Routes now delegate to CLI via CLIAdapter for
single source of truth architecture.
"""

from flask import Blueprint, request, jsonify
from backend.core.cli_adapter import get_adapter
from backend.api.validators import (
    validate_pattern_request,
    validate_grid_request,
    validate_normalize_request,
    validate_fill_request,
)
from backend.api.errors import handle_error
from backend.api.progress_routes import create_progress_tracker, send_progress, cleanup_progress_tracker
from pathlib import Path
import subprocess
import threading
import json

api = Blueprint("api", __name__)

# Get CLI adapter (single source of truth for crossword operations)
cli_adapter = get_adapter()


@api.route("/health", methods=["GET"])
def health_check():
    """GET /api/health - Health check endpoint (Phase 3: checks CLI health)."""
    cli_healthy = cli_adapter.health_check()

    return jsonify(
        {
            "status": "healthy" if cli_healthy else "degraded",
            "version": "0.2.0",  # Phase 3 integration
            "architecture": "cli-backend",
            "components": {
                "cli_adapter": "ok" if cli_healthy else "error",
                "api_server": "ok",
            },
        }
    ), (200 if cli_healthy else 503)


@api.route("/pattern", methods=["POST"])
def pattern_search():
    """POST /api/pattern - Pattern search endpoint (Phase 3: uses CLI)."""
    try:
        # Check Content-Type
        if not request.is_json:
            return handle_error("INVALID_CONTENT_TYPE", "Content-Type must be application/json", 400)

        # Parse JSON with error handling
        try:
            data = request.get_json()
        except Exception as e:
            return handle_error("INVALID_JSON", f"Failed to parse JSON: {str(e)}", 400)

        # Check for empty body
        if data is None:
            return handle_error("EMPTY_BODY", "Request body cannot be empty", 400)

        # Validate request
        data = validate_pattern_request(data)

        # Resolve wordlist paths
        wordlist_paths = []
        backend_dir = Path(__file__).parent.parent.parent
        data_dir = backend_dir / "data" / "wordlists"

        for wordlist_name in data.get("wordlists", ["comprehensive"]):
            # Handle paths with category (e.g., "core/standard") or without
            if "/" in wordlist_name or "\\" in wordlist_name:
                # Could be a category path like "core/standard"
                wordlist_path = data_dir / f"{wordlist_name}.txt"
                if not wordlist_path.exists():
                    # Try as absolute path
                    wordlist_path = Path(wordlist_name)
            else:
                # Simple name, try in root then common locations
                wordlist_path = data_dir / f"{wordlist_name}.txt"
                if not wordlist_path.exists():
                    # Try in core directory
                    wordlist_path = data_dir / "core" / f"{wordlist_name}.txt"

            if wordlist_path.exists():
                wordlist_paths.append(str(wordlist_path))

        # Delegate to CLI via adapter
        result = cli_adapter.pattern(
            pattern=data["pattern"],
            wordlist_paths=wordlist_paths if wordlist_paths else None,
            max_results=data.get("max_results", 20),
            algorithm=data.get("algorithm", "regex"),
        )

        # CLI output is already in correct format!
        return jsonify(result), 200

    except ValueError as e:
        return handle_error("INVALID_PATTERN", str(e), 400)
    except subprocess.TimeoutExpired:
        return handle_error("TIMEOUT", "Pattern search timed out", 505)
    except Exception as e:
        return handle_error("INTERNAL_ERROR", str(e), 500)


@api.route("/number", methods=["POST"])
def number_grid():
    """POST /api/number - Grid numbering validation endpoint (Phase 3: uses CLI)."""
    try:
        # Check Content-Type
        if not request.is_json:
            return handle_error("INVALID_CONTENT_TYPE", "Content-Type must be application/json", 400)

        # Parse JSON with error handling
        try:
            data = request.get_json()
        except Exception as e:
            return handle_error("INVALID_JSON", f"Failed to parse JSON: {str(e)}", 400)

        # Check for empty body
        if data is None:
            return handle_error("EMPTY_BODY", "Request body cannot be empty", 400)

        # Validate request
        data = validate_grid_request(data)

        # Check if grid size is non-standard
        grid_size = data.get("size", len(data.get("grid", [])))
        allow_nonstandard = grid_size not in [11, 15, 21]

        # Delegate to CLI via adapter
        result = cli_adapter.number(grid_data=data, allow_nonstandard=allow_nonstandard)

        # Note: User-provided numbering validation is removed in Phase 3
        # as the CLI is the single source of truth for auto-numbering.
        # If validation is needed, it should be added to CLI first.

        # CLI output is already in correct format!
        return jsonify(result), 200

    except ValueError as e:
        return handle_error("INVALID_GRID", str(e), 400)
    except subprocess.TimeoutExpired:
        return handle_error("TIMEOUT", "Grid numbering timed out", 504)
    except Exception as e:
        return handle_error("INTERNAL_ERROR", str(e), 500)


@api.route("/normalize", methods=["POST"])
def normalize_entry():
    """POST /api/normalize - Convention normalization endpoint (Phase 3: uses CLI)."""
    try:
        # Check Content-Type
        if not request.is_json:
            return handle_error("INVALID_CONTENT_TYPE", "Content-Type must be application/json", 400)

        # Parse JSON with error handling
        try:
            data = request.get_json()
        except Exception as e:
            return handle_error("INVALID_JSON", f"Failed to parse JSON: {str(e)}", 400)

        # Check for empty body
        if data is None:
            return handle_error("EMPTY_BODY", "Request body cannot be empty", 400)

        # Validate request
        data = validate_normalize_request(data)

        # Delegate to CLI via adapter (with caching for performance)
        result = cli_adapter.normalize(data["text"])

        # CLI output is already in correct format!
        return jsonify(result), 200

    except ValueError as e:
        return handle_error("INVALID_TEXT", str(e), 400)
    except subprocess.TimeoutExpired:
        return handle_error("TIMEOUT", "Normalization timed out", 506)
    except Exception as e:
        return handle_error("INTERNAL_ERROR", str(e), 500)


@api.route("/fill", methods=["POST"])
def fill_grid():
    """POST /api/fill - Autofill crossword grid endpoint (Phase 3.3: uses CLI)."""
    try:
        # Check Content-Type
        if not request.is_json:
            return handle_error("INVALID_CONTENT_TYPE", "Content-Type must be application/json", 400)

        # Parse JSON with error handling
        try:
            data = request.get_json()
        except Exception as e:
            return handle_error("INVALID_JSON", f"Failed to parse JSON: {str(e)}", 400)

        # Check for empty body
        if data is None:
            return handle_error("EMPTY_BODY", "Request body cannot be empty", 400)

        # Validate request
        data = validate_fill_request(data)

        # Resolve wordlist paths
        wordlist_paths = []
        backend_dir = Path(__file__).parent.parent.parent
        data_dir = backend_dir / "data" / "wordlists"

        for wordlist_name in data.get("wordlists", ["comprehensive"]):
            # Handle paths with category (e.g., "core/standard") or without
            if "/" in wordlist_name or "\\" in wordlist_name:
                # Could be a category path like "core/standard"
                wordlist_path = data_dir / f"{wordlist_name}.txt"
                if not wordlist_path.exists():
                    # Try as absolute path
                    wordlist_path = Path(wordlist_name)
            else:
                # Simple name, try in root then common locations
                wordlist_path = data_dir / f"{wordlist_name}.txt"
                if not wordlist_path.exists():
                    # Try in core directory
                    wordlist_path = data_dir / "core" / f"{wordlist_name}.txt"

            if wordlist_path.exists():
                wordlist_paths.append(str(wordlist_path))

        if not wordlist_paths:
            return handle_error("INVALID_WORDLISTS", "No valid wordlists found", 400)

        # Prepare grid data
        grid_data = {"size": data["size"], "grid": data["grid"]}

        # Delegate to CLI via adapter
        result = cli_adapter.fill(
            grid_data=grid_data,
            wordlist_paths=wordlist_paths,
            timeout_seconds=data.get("timeout", 300),
            min_score=data.get("min_score", 30),
            algorithm=data.get("algorithm", "trie"),  # 'regex' or 'trie'
        )

        # CLI returns filled grid with metadata
        return jsonify(result), 200

    except ValueError as e:
        return handle_error("INVALID_REQUEST", str(e), 400)
    except subprocess.TimeoutExpired:
        return handle_error("TIMEOUT", "Grid fill timed out", 507)
    except Exception as e:
        return handle_error("INTERNAL_ERROR", str(e), 500)


# ==================================================
# SSE-enabled routes for real-time progress tracking
# ==================================================

def run_cli_with_progress(task_id, cmd_args, timeout=300):
    """
    Run CLI command and send progress updates via SSE.

    Args:
        task_id: Progress tracker task ID
        cmd_args: CLI command arguments
        timeout: Command timeout in seconds
    """
    import sys

    try:
        # Build full command
        cli_path = cli_adapter.cli_path
        cmd = [str(cli_path)] + cmd_args

        send_progress(task_id, 5, 'Starting CLI process...', 'running')

        # Start process with stderr capture
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cli_path.parent,
            bufsize=1,  # Line buffered
        )

        send_progress(task_id, 10, 'CLI process running...', 'running')

        # Read stderr in real-time for progress updates
        while True:
            line = process.stderr.readline()
            if not line:
                break

            # Parse progress JSON from stderr
            try:
                progress_data = json.loads(line.strip())
                if progress_data.get('type') == 'progress':
                    send_progress(
                        task_id,
                        progress_data.get('progress', 0),
                        progress_data.get('message', 'Processing...'),
                        progress_data.get('status', 'running'),
                        progress_data.get('data')  # Forward grid data if present
                    )
            except json.JSONDecodeError:
                # Not a progress update, ignore
                pass

        # Wait for completion
        stdout, stderr = process.communicate(timeout=timeout)

        if process.returncode == 0:
            # Parse filled grid from stdout JSON
            try:
                result_data = json.loads(stdout.strip())
                # Send completion with grid data
                send_progress(task_id, 100, 'Complete', 'complete', result_data)
            except (json.JSONDecodeError, Exception) as e:
                send_progress(task_id, 100, 'Complete', 'complete')
        else:
            send_progress(task_id, 0, f'Error: {stderr[:200]}', 'error')

    except subprocess.TimeoutExpired:
        send_progress(task_id, 0, 'Operation timed out', 'error')
    except Exception as e:
        import traceback
        traceback.print_exc()
        send_progress(task_id, 0, f'Error: {str(e)}', 'error')


@api.route("/pattern/with-progress", methods=["POST"])
def pattern_search_with_progress():
    """POST /api/pattern/with-progress - Pattern search with SSE progress tracking."""
    try:
        # Validate request
        data = validate_pattern_request(request.json)

        # Create progress tracker
        task_id = create_progress_tracker()

        # Resolve wordlist paths (same as regular pattern route)
        wordlist_paths = []
        backend_dir = Path(__file__).parent.parent.parent
        data_dir = backend_dir / "data" / "wordlists"

        for wordlist_name in data.get("wordlists", ["comprehensive"]):
            if "/" in wordlist_name or "\\" in wordlist_name:
                wordlist_path = data_dir / f"{wordlist_name}.txt"
                if not wordlist_path.exists():
                    wordlist_path = Path(wordlist_name)
            else:
                wordlist_path = data_dir / f"{wordlist_name}.txt"
                if not wordlist_path.exists():
                    wordlist_path = data_dir / "core" / f"{wordlist_name}.txt"

            if wordlist_path.exists():
                wordlist_paths.append(str(wordlist_path))

        # Build CLI command
        cmd_args = [
            "pattern",
            data["pattern"],
            "--json-output",
            "--max-results", str(data.get("max_results", 20)),
            "--algorithm", data.get("algorithm", "regex")
        ]

        for wp in wordlist_paths:
            cmd_args.extend(["--wordlists", wp])

        # Start background task
        thread = threading.Thread(
            target=run_cli_with_progress,
            args=(task_id, cmd_args, 60),
            daemon=True
        )
        thread.start()

        # Return task ID for SSE connection
        return jsonify({
            "task_id": task_id,
            "progress_url": f"/api/progress/{task_id}"
        }), 202

    except ValueError as e:
        return handle_error("INVALID_REQUEST", str(e), 400)
    except Exception as e:
        return handle_error("INTERNAL_ERROR", str(e), 500)


@api.route("/fill/with-progress", methods=["POST"])
def fill_with_progress():
    """POST /api/fill/with-progress - Grid fill with SSE progress tracking."""
    try:
        # Validate request
        data = validate_fill_request(request.json)

        # Create progress tracker
        task_id = create_progress_tracker()

        # Resolve wordlist paths (same as regular fill route)
        wordlist_paths = []
        backend_dir = Path(__file__).parent.parent.parent
        data_dir = backend_dir / "data" / "wordlists"

        for wordlist_name in data.get("wordlists", ["comprehensive"]):
            if "/" in wordlist_name or "\\" in wordlist_name:
                wordlist_path = data_dir / f"{wordlist_name}.txt"
                if not wordlist_path.exists():
                    wordlist_path = Path(wordlist_name)
            else:
                wordlist_path = data_dir / f"{wordlist_name}.txt"
                if not wordlist_path.exists():
                    wordlist_path = data_dir / "core" / f"{wordlist_name}.txt"

            if wordlist_path.exists():
                wordlist_paths.append(str(wordlist_path))

        # Save grid to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            grid_data = {"size": data["size"], "grid": data["grid"]}
            json.dump(grid_data, f)
            grid_file = f.name

        # Save theme entries to temp file if provided (Phase 3.2)
        theme_entries_file = None
        if "theme_entries" in data and data["theme_entries"]:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(data["theme_entries"], f)
                theme_entries_file = f.name

        # Build CLI command
        cmd_args = [
            "fill",
            grid_file,
            "--timeout", str(data.get("timeout", 300)),
            "--min-score", str(data.get("min_score", 30)),
            "--algorithm", data.get("algorithm", "trie"),
            "--allow-nonstandard",
            "--json-output"  # Enable progress reporting via stderr
        ]

        for wp in wordlist_paths:
            cmd_args.extend(["--wordlists", wp])

        # Add theme entries flag if provided
        if theme_entries_file:
            cmd_args.extend(["--theme-entries", theme_entries_file])

        # Start background task
        thread = threading.Thread(
            target=run_cli_with_progress,
            args=(task_id, cmd_args, data.get("timeout", 300) + 10),
            daemon=True
        )
        thread.start()

        # Return task ID for SSE connection
        return jsonify({
            "task_id": task_id,
            "progress_url": f"/api/progress/{task_id}"
        }), 202

    except ValueError as e:
        return handle_error("INVALID_REQUEST", str(e), 400)
    except Exception as e:
        return handle_error("INTERNAL_ERROR", str(e), 500)
