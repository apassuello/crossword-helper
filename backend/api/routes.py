"""
Flask API routes for pattern matching, grid numbering, and autofill.
"""

import json
import logging
import re
import subprocess
import threading
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from backend.api.errors import handle_error
from backend.api.progress_routes import create_progress_tracker, send_progress
from backend.api.validators import (
    validate_fill_request,
    validate_grid_request,
    validate_normalize_request,
    validate_pattern_request,
)
from backend.core.cli_adapter import get_adapter
from backend.core.wordlist_resolver import resolve_wordlist_paths

logger = logging.getLogger(__name__)

api = Blueprint("api", __name__)

# Get CLI adapter (single source of truth for crossword operations)
cli_adapter = get_adapter()


@api.route("/health", methods=["GET"])
def health_check():
    """GET /api/health - Health check endpoint."""
    cli_healthy = cli_adapter.health_check()

    return jsonify(
        {
            "status": "healthy" if cli_healthy else "degraded",
            "version": "2.0.0",
            "architecture": "cli-backend",
            "components": {
                "cli_adapter": "ok" if cli_healthy else "error",
                "api_server": "ok",
            },
        }
    ), (200 if cli_healthy else 503)


@api.route("/pattern", methods=["POST"])
def pattern_search():
    """POST /api/pattern - Pattern search endpoint."""
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

        # Resolve wordlist paths using shared resolver
        wordlist_names = data.get("wordlists", ["comprehensive"])
        wordlist_paths = resolve_wordlist_paths(wordlist_names)

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
    """POST /api/number - Grid numbering validation endpoint."""
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

        # CLI is the single source of truth for auto-numbering.

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
    """POST /api/normalize - Convention normalization endpoint."""
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
    """POST /api/fill - Autofill crossword grid endpoint."""
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

        # Resolve wordlist paths using shared resolver
        wordlist_names = data.get("wordlists", ["comprehensive"])
        wordlist_paths = resolve_wordlist_paths(wordlist_names)

        if not wordlist_paths:
            return handle_error("INVALID_WORDLISTS", "No valid wordlists found", 400)

        # Convert frontend grid format to CLI format
        # Frontend: [{"letter": "A", "isBlack": false}, ...]
        # CLI: ["A", "#", ".", ...]
        cli_grid = []
        for row in data["grid"]:
            cli_row = []
            for cell in row:
                if isinstance(cell, dict):
                    if cell.get("isBlack", False):
                        cli_row.append("#")
                    elif cell.get("letter", ""):
                        cli_row.append(cell["letter"].upper())
                    else:
                        cli_row.append(".")
                else:
                    # Already in CLI format (string)
                    cli_row.append(cell)
            cli_grid.append(cli_row)

        # Prepare grid data
        grid_data = {"size": data["size"], "grid": cli_grid}

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


def run_cli_with_progress(task_id, cmd_args, timeout=300, temp_files=None):
    """
    Run CLI command and send progress updates via SSE.

    Args:
        task_id: Progress tracker task ID
        cmd_args: CLI command arguments
        timeout: Command timeout in seconds
        temp_files: List of temp file paths to clean up when done
    """

    try:
        # Build full command
        cli_path = cli_adapter.cli_path
        cmd = [str(cli_path)] + cmd_args

        # Log the full CLI command for debugging
        logger.info(f"Executing CLI command: {' '.join(cmd)}")
        logger.debug(f"CLI working directory: {cli_path.parent}")

        send_progress(task_id, 5, "Starting CLI process...", "running")

        # Start process with stderr capture
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cli_path.parent,
            bufsize=1,  # Line buffered
        )

        # Register process for cleanup on client disconnect
        from .progress_routes import register_process

        register_process(task_id, process)

        logger.info(f"[CLI DEBUG] PID={process.pid}, cmd={' '.join(cmd)}")
        send_progress(task_id, 10, "CLI process running...", "running")

        # Read stderr in real-time for progress updates
        stderr_lines = []
        while True:
            line = process.stderr.readline()
            if not line:
                break

            stderr_lines.append(line.rstrip())
            logger.info(f"[CLI STDERR] {line.rstrip()}")

            # Parse progress JSON from stderr
            try:
                progress_data = json.loads(line.strip())
                if progress_data.get("type") == "progress":
                    # CRITICAL: Never forward 'complete'/'error' from stderr.
                    # The CLI sends a 'complete' progress event to stderr BEFORE
                    # writing the actual result (with grid data) to stdout.
                    # If we forward 'complete' here, the SSE generator breaks
                    # before the real result arrives, causing "No solution found".
                    stderr_status = progress_data.get("status", "running")
                    if stderr_status in ("complete", "error"):
                        stderr_status = "running"

                    send_progress(
                        task_id,
                        progress_data.get("progress", 0),
                        progress_data.get("message", "Processing..."),
                        stderr_status,
                        progress_data.get("data"),
                    )
            except json.JSONDecodeError:
                pass

        # Wait for completion
        stdout, stderr = process.communicate(timeout=timeout)

        logger.info(f"[CLI DEBUG] Process exited with code {process.returncode}")
        logger.info(f"[CLI DEBUG] stdout length: {len(stdout)} chars")
        logger.info(f"[CLI DEBUG] remaining stderr length: {len(stderr)} chars")
        if stdout:
            logger.info(f"[CLI STDOUT] {stdout[:1000]}")
        if stderr:
            logger.info(f"[CLI STDERR remaining] {stderr[:500]}")

        if process.returncode == 0:
            # Parse filled grid from stdout JSON
            try:
                result_data = json.loads(stdout.strip())
                logger.info(
                    f"[CLI DEBUG] Parsed result: success={result_data.get('success')}, "
                    f"filled={result_data.get('slots_filled')}/{result_data.get('total_slots')}"
                )
                # Send completion with grid data
                send_progress(task_id, 100, "Complete", "complete", result_data)
            except (json.JSONDecodeError, Exception) as e:
                logger.error(f"[CLI DEBUG] Failed to parse stdout JSON: {e}")
                logger.error(f"[CLI DEBUG] Raw stdout: {repr(stdout[:500])}")
                send_progress(task_id, 100, "Complete", "complete")
        else:
            # Log full error for debugging
            logger.error(f"CLI process failed with return code {process.returncode}")
            logger.error(f"CLI command: {' '.join(cmd)}")
            logger.error("STDOUT (first 200 lines):")
            for i, line in enumerate(stdout.split("\n")[:200]):
                logger.error(f"  {i+1}: {line}")
            logger.error("STDERR (first 200 lines):")
            for i, line in enumerate(stderr.split("\n")[:200]):
                logger.error(f"  {i+1}: {line}")

            # Send user-friendly error message — combine all stderr sources
            all_stderr = "\n".join(stderr_lines) + "\n" + stderr if stderr else "\n".join(stderr_lines)
            all_stderr = all_stderr.strip()
            # Filter out progress JSON lines to find actual errors
            error_lines = [line for line in all_stderr.split("\n") if line and not line.startswith("{")]
            error_preview = "\n".join(error_lines[-10:]) if error_lines else (stdout[:500] if stdout else "Unknown error")
            send_progress(
                task_id,
                0,
                f"CLI Error (code {process.returncode}): {error_preview}",
                "error",
            )

    except subprocess.TimeoutExpired:
        try:
            process.terminate()
            process.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            process.kill()
        send_progress(task_id, 0, "Operation timed out", "error")
    except Exception as e:
        import traceback

        traceback.print_exc()
        send_progress(task_id, 0, f"Error: {str(e)}", "error")
    finally:
        # Clean up temp files
        if temp_files:
            for temp_file in temp_files:
                try:
                    Path(temp_file).unlink(missing_ok=True)
                except Exception:
                    pass


@api.route("/pattern/with-progress", methods=["POST"])
def pattern_search_with_progress():
    """POST /api/pattern/with-progress - Pattern search with SSE progress tracking."""
    try:
        # Validate request
        data = validate_pattern_request(request.json)

        # Create progress tracker
        task_id = create_progress_tracker()

        # Resolve wordlist paths using shared resolver
        wordlist_names = data.get("wordlists", ["comprehensive"])
        wordlist_paths = resolve_wordlist_paths(wordlist_names)

        # Build CLI command
        cmd_args = [
            "pattern",
            data["pattern"],
            "--json-output",
            "--max-results",
            str(data.get("max_results", 20)),
            "--algorithm",
            data.get("algorithm", "regex"),
        ]

        for wp in wordlist_paths:
            cmd_args.extend(["--wordlists", wp])

        # Start background task
        thread = threading.Thread(target=run_cli_with_progress, args=(task_id, cmd_args, 60), daemon=True)
        thread.start()

        # Return task ID for SSE connection
        return (
            jsonify({"task_id": task_id, "progress_url": f"/api/progress/{task_id}"}),
            202,
        )

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

        # Resolve wordlist paths using shared resolver
        wordlist_names = data.get("wordlists", ["comprehensive"])
        wordlist_paths = resolve_wordlist_paths(wordlist_names)

        # Resolve theme wordlist if specified
        theme_wordlist_path = None
        if "themeList" in data and data["themeList"]:
            theme_paths = resolve_wordlist_paths([data["themeList"]])
            if theme_paths:
                theme_wordlist_path = theme_paths[0]

        # Save grid to temp file
        # Convert frontend grid format to CLI format
        # Frontend: [{"letter": "A", "isBlack": false}, ...]
        # CLI: ["A", "#", ".", ...]
        import tempfile

        cli_grid = []
        for row in data["grid"]:
            cli_row = []
            for cell in row:
                if isinstance(cell, dict):
                    if cell.get("isBlack", False):
                        cli_row.append("#")
                    elif cell.get("letter", ""):
                        cli_row.append(cell["letter"].upper())
                    else:
                        cli_row.append(".")
                else:
                    # Already in CLI format (string)
                    cli_row.append(cell)
            cli_grid.append(cli_row)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            grid_data = {"size": data["size"], "grid": cli_grid}
            json.dump(grid_data, f)
            grid_file = f.name

        # Save theme entries to temp file if provided
        theme_entries_file = None
        if "theme_entries" in data and data["theme_entries"]:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(data["theme_entries"], f)
                theme_entries_file = f.name

        # Debug: log what we're sending to CLI
        logger.info(f"[AUTOFILL DEBUG] Grid size: {data['size']}x{data['size']}")
        logger.info(f"[AUTOFILL DEBUG] Grid file: {grid_file}")
        logger.info(f"[AUTOFILL DEBUG] Wordlist names requested: {wordlist_names}")
        logger.info(f"[AUTOFILL DEBUG] Wordlist paths resolved: {wordlist_paths}")
        logger.info(f"[AUTOFILL DEBUG] Algorithm: {data.get('algorithm', 'repair')}")
        logger.info(f"[AUTOFILL DEBUG] Timeout: {data.get('timeout', 300)}")
        logger.info(f"[AUTOFILL DEBUG] Min score: {data.get('min_score', 30)}")
        logger.info(f"[AUTOFILL DEBUG] Theme entries: {bool(data.get('theme_entries'))}")

        # Count non-empty cells in grid
        filled_cells = sum(1 for row in cli_grid for c in row if c not in (".", "#", ""))
        black_cells = sum(1 for row in cli_grid for c in row if c == "#")
        total_cells = data["size"] * data["size"]
        empty_cells = total_cells - filled_cells - black_cells
        logger.info(f"[AUTOFILL DEBUG] Grid cells: {filled_cells} filled, " f"{black_cells} black, {empty_cells} empty")

        # Build CLI command
        cmd_args = [
            "fill",
            grid_file,
            "--timeout",
            str(data.get("timeout", 300)),
            "--min-score",
            str(data.get("min_score", 30)),
            "--algorithm",
            data.get("algorithm", "repair"),
            "--allow-nonstandard",
            "--json-output",  # Enable progress reporting via stderr
        ]

        for wp in wordlist_paths:
            cmd_args.extend(["--wordlists", wp])

        # Add theme entries flag if provided
        if theme_entries_file:
            cmd_args.extend(["--theme-entries", theme_entries_file])

        # Add theme wordlist flag if specified
        if theme_wordlist_path:
            cmd_args.extend(["--theme-wordlist", theme_wordlist_path])

        # Add adaptive mode flag if enabled (auto black square placement)
        if data.get("adaptive_mode", False):
            cmd_args.append("--adaptive")
            if "max_adaptations" in data:
                cmd_args.extend(["--max-adaptations", str(data["max_adaptations"])])

        # Add partial fill flag if enabled (collaborative mode)
        if data.get("partial_fill", False):
            cmd_args.append("--partial-fill")

        # Add cleanup flag (remove invalid words, keep valid crossing letters)
        if data.get("cleanup", False):
            cmd_args.append("--cleanup")

        # Start background task
        temp_files = [grid_file]
        if theme_entries_file:
            temp_files.append(theme_entries_file)

        thread = threading.Thread(
            target=run_cli_with_progress,
            args=(task_id, cmd_args, data.get("timeout", 300) + 10, temp_files),
            daemon=True,
        )
        thread.start()

        # Return task ID for SSE connection
        return (
            jsonify({"task_id": task_id, "progress_url": f"/api/progress/{task_id}"}),
            202,
        )

    except ValueError as e:
        return handle_error("INVALID_REQUEST", str(e), 400)
    except Exception as e:
        return handle_error("INTERNAL_ERROR", str(e), 500)


@api.route("/grid/verify-words", methods=["POST"])
def verify_words():
    """POST /api/grid/verify-words - Check all slots against wordlist.

    Fully-filled slots: checks exact word exists in wordlist.
    Partially-filled slots (has letters + empty cells): checks if any matching
    word exists using '?' wildcards for empty cells. If no match, slot is unfillable.
    Fully-empty slots are skipped.
    """
    try:
        data = request.get_json()
        if not data or "grid" not in data:
            return handle_error("INVALID_REQUEST", "Missing 'grid' field", 400)

        grid_data = data["grid"]
        size = data.get("size", len(grid_data))
        wordlist_names = data.get("wordlists", ["comprehensive"])
        wordlist_paths = resolve_wordlist_paths(wordlist_names)

        # Load ALL available wordlists for validation (not just selected ones)
        words_set = set()
        words_by_length = {}  # length -> set of words
        wordlist_dir = Path(current_app.root_path).parent / "data" / "wordlists"
        all_wl_paths = list(wordlist_dir.rglob("*.txt"))
        # Filter out archive and custom
        all_wl_paths = [p for p in all_wl_paths if "archive" not in p.parts and "custom" not in p.parts]
        # Also include the explicitly requested wordlists (in case of custom paths)
        for wp in wordlist_paths:
            wp_path = Path(wp)
            if wp_path not in all_wl_paths:
                all_wl_paths.append(wp_path)

        for wp in all_wl_paths:
            try:
                with open(wp, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        # Support WORD;SCORE format
                        w = line.split(";")[0].strip().upper()
                        if w and w.isalpha() and 3 <= len(w) <= 21:
                            words_set.add(w)
                            words_by_length.setdefault(len(w), set()).add(w)
            except Exception:
                pass

        def get_cell(cell):
            """Returns (letter_or_empty, is_black)."""
            if isinstance(cell, dict):
                if cell.get("isBlack"):
                    return "", True
                letter = (cell.get("letter") or "").strip().upper()
                return letter, False
            if cell == "#":
                return "", True
            if not cell or cell == "." or cell == "":
                return "", False
            return cell.upper(), False

        invalid_words = []
        checked_count = [0]  # mutable for closure

        def check_slot(cells_in_slot, direction):
            """Check a slot against wordlist.

            Fully filled: exact lookup.
            Partially filled: pattern match with regex (? = any letter).
            Fully empty: skip.
            """
            pattern = ""
            positions = []
            has_empty = False
            has_letter = False
            for r, c in cells_in_slot:
                letter, is_black = get_cell(grid_data[r][c])
                if is_black:
                    return
                positions.append([r, c])
                if letter:
                    pattern += letter
                    has_letter = True
                else:
                    pattern += "?"
                    has_empty = True

            # Skip slots shorter than 3 (wordlist has no 2-letter words)
            if len(pattern) < 3:
                return

            # Skip fully empty slots — nothing to validate
            if not has_letter:
                return

            checked_count[0] += 1

            if not has_empty:
                # Fully filled — exact lookup
                if pattern not in words_set:
                    invalid_words.append(
                        {
                            "word": pattern,
                            "direction": direction,
                            "cells": positions,
                            "status": "invalid",
                        }
                    )
            else:
                # Partially filled — check if any word matches the pattern
                candidates = words_by_length.get(len(pattern))
                if not candidates:
                    # No words of this length at all
                    invalid_words.append(
                        {
                            "word": pattern,
                            "direction": direction,
                            "cells": positions,
                            "status": "unfillable",
                        }
                    )
                    return
                # Build regex: replace ? with [A-Z]
                regex = re.compile("^" + pattern.replace("?", "[A-Z]") + "$")
                if not any(regex.match(w) for w in candidates):
                    invalid_words.append(
                        {
                            "word": pattern,
                            "direction": direction,
                            "cells": positions,
                            "status": "unfillable",
                        }
                    )

        # Find all across slots (boundary to boundary)
        for r in range(size):
            c = 0
            while c < size:
                _, is_black = get_cell(grid_data[r][c])
                if is_black:
                    c += 1
                    continue
                # Start of a slot — collect until next black/edge
                slot_cells = []
                while c < size:
                    _, is_black = get_cell(grid_data[r][c])
                    if is_black:
                        break
                    slot_cells.append((r, c))
                    c += 1
                if len(slot_cells) >= 3:
                    check_slot(slot_cells, "across")

        # Find all down slots (boundary to boundary)
        for c in range(size):
            r = 0
            while r < size:
                _, is_black = get_cell(grid_data[r][c])
                if is_black:
                    r += 1
                    continue
                slot_cells = []
                while r < size:
                    _, is_black = get_cell(grid_data[r][c])
                    if is_black:
                        break
                    slot_cells.append((r, c))
                    r += 1
                if len(slot_cells) >= 3:
                    check_slot(slot_cells, "down")

        return (
            jsonify(
                {
                    "invalid_words": invalid_words,
                    "invalid_count": len(invalid_words),
                    "total_checked": checked_count[0],
                    "wordlist_size": len(words_set),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error verifying words: {e}")
        return handle_error("INTERNAL_ERROR", str(e), 500)


@api.route("/grid/clean", methods=["POST"])
def clean_grid():
    """POST /api/grid/clean - Remove invalid words, keep valid ones intact.

    For each filled word slot:
    - If the word is valid (exists in any wordlist): keep all letters
    - If invalid: clear letters UNLESS they belong to a valid crossing word

    Returns the cleaned grid with only valid words preserved.
    """
    try:
        data = request.get_json()
        if not data or "grid" not in data:
            return handle_error("INVALID_REQUEST", "Missing 'grid' field", 400)

        grid_data = data["grid"]
        size = data.get("size", len(grid_data))

        # Load all wordlists
        words_set = set()
        wordlist_dir = Path(current_app.root_path).parent / "data" / "wordlists"
        for wp in wordlist_dir.rglob("*.txt"):
            if "archive" in wp.parts:
                continue
            try:
                with open(wp, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        w = line.split(";")[0].strip().upper()
                        if w and w.isalpha() and 3 <= len(w) <= 21:
                            words_set.add(w)
            except Exception:
                pass

        def get_letter(r, c):
            """Extract letter from cell at (r,c). Returns None for black, '' for empty."""
            cell = grid_data[r][c]
            if isinstance(cell, dict):
                if cell.get("isBlack"):
                    return None  # black square
                return (cell.get("letter") or "").strip().upper() or ""
            if cell == "#":
                return None
            if not cell or cell == ".":
                return ""
            return cell.upper()

        def set_letter(r, c, letter):
            """Set letter in grid cell, preserving format."""
            if isinstance(grid_data[r][c], dict):
                grid_data[r][c] = {**grid_data[r][c], "letter": letter}
            else:
                grid_data[r][c] = letter if letter else "."

        # Step 1: Extract all slots and their words
        slots = []  # [(cells_list, direction, word)]

        # Across slots
        for r in range(size):
            c = 0
            while c < size:
                if get_letter(r, c) is None:
                    c += 1
                    continue
                slot_cells = []
                while c < size and get_letter(r, c) is not None:
                    slot_cells.append((r, c))
                    c += 1
                if len(slot_cells) >= 3:
                    word = "".join(get_letter(r2, c2) for r2, c2 in slot_cells)
                    slots.append((slot_cells, "across", word))

        # Down slots
        for c in range(size):
            r = 0
            while r < size:
                if get_letter(r, c) is None:
                    r += 1
                    continue
                slot_cells = []
                while r < size and get_letter(r, c) is not None:
                    slot_cells.append((r, c))
                    r += 1
                if len(slot_cells) >= 3:
                    word = "".join(get_letter(r2, c2) for r2, c2 in slot_cells)
                    slots.append((slot_cells, "down", word))

        # Step 2: Classify each slot
        valid_slots = set()  # indices into slots[]
        invalid_slots = set()

        for i, (cells, direction, word) in enumerate(slots):
            # Skip slots that aren't fully filled with letters
            if len(word) != len(cells) or not word.isalpha():
                continue
            if word in words_set:
                valid_slots.add(i)
            else:
                invalid_slots.add(i)

        if not invalid_slots:
            return (
                jsonify(
                    {
                        "grid": grid_data,
                        "removed_count": 0,
                        "valid_count": len(valid_slots),
                        "message": "All words are valid, nothing to clean",
                    }
                ),
                200,
            )

        # Step 3: Build set of cells protected by valid words
        protected_cells = set()
        for i in valid_slots:
            cells, _, _ = slots[i]
            for r, c in cells:
                protected_cells.add((r, c))

        # Step 4: Clear letters in invalid words (except protected cells)
        cleared_cells = 0
        for i in invalid_slots:
            cells, _, word = slots[i]
            for r, c in cells:
                if (r, c) not in protected_cells:
                    set_letter(r, c, "")
                    cleared_cells += 1

        return (
            jsonify(
                {
                    "grid": grid_data,
                    "removed_count": len(invalid_slots),
                    "valid_count": len(valid_slots),
                    "cleared_cells": cleared_cells,
                    "message": (
                        f"Removed {len(invalid_slots)} invalid words "
                        f"({cleared_cells} cells cleared), "
                        f"kept {len(valid_slots)} valid words"
                    ),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error cleaning grid: {e}")
        return handle_error("INTERNAL_ERROR", str(e), 500)
