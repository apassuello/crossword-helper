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
    validate_normalize_request
)
from backend.api.errors import handle_error
from pathlib import Path
import subprocess

api = Blueprint('api', __name__)

# Get CLI adapter (single source of truth for crossword operations)
cli_adapter = get_adapter()


@api.route('/health', methods=['GET'])
def health_check():
    """GET /api/health - Health check endpoint (Phase 3: checks CLI health)."""
    cli_healthy = cli_adapter.health_check()

    return jsonify({
        'status': 'healthy' if cli_healthy else 'degraded',
        'version': '0.2.0',  # Phase 3 integration
        'architecture': 'cli-backend',
        'components': {
            'cli_adapter': 'ok' if cli_healthy else 'error',
            'api_server': 'ok'
        }
    }), 200 if cli_healthy else 503


@api.route('/pattern', methods=['POST'])
def pattern_search():
    """POST /api/pattern - Pattern search endpoint (Phase 3: uses CLI)."""
    try:
        # Validate request
        data = validate_pattern_request(request.json)

        # Resolve wordlist paths
        wordlist_paths = []
        backend_dir = Path(__file__).parent.parent.parent
        data_dir = backend_dir / 'data' / 'wordlists'

        for wordlist_name in data.get('wordlists', ['personal', 'standard']):
            # Handle both names like "standard" and full paths
            if '/' in wordlist_name or '\\' in wordlist_name:
                wordlist_path = Path(wordlist_name)
            else:
                wordlist_path = data_dir / f"{wordlist_name}.txt"

            if wordlist_path.exists():
                wordlist_paths.append(str(wordlist_path))

        # Delegate to CLI via adapter
        result = cli_adapter.pattern(
            pattern=data['pattern'],
            wordlist_paths=wordlist_paths if wordlist_paths else None,
            max_results=data.get('max_results', 20)
        )

        # CLI output is already in correct format!
        return jsonify(result), 200

    except ValueError as e:
        return handle_error('INVALID_PATTERN', str(e), 400)
    except subprocess.TimeoutExpired:
        return handle_error('TIMEOUT', 'Pattern search timed out', 504)
    except Exception as e:
        return handle_error('INTERNAL_ERROR', str(e), 500)


@api.route('/number', methods=['POST'])
def number_grid():
    """POST /api/number - Grid numbering validation endpoint (Phase 3: uses CLI)."""
    try:
        # Validate request
        data = validate_grid_request(request.json)

        # Check if grid size is non-standard
        grid_size = data.get('size', len(data.get('grid', [])))
        allow_nonstandard = grid_size not in [11, 15, 21]

        # Delegate to CLI via adapter
        result = cli_adapter.number(
            grid_data=data,
            allow_nonstandard=allow_nonstandard
        )

        # Note: User-provided numbering validation is removed in Phase 3
        # as the CLI is the single source of truth for auto-numbering.
        # If validation is needed, it should be added to CLI first.

        # CLI output is already in correct format!
        return jsonify(result), 200

    except ValueError as e:
        return handle_error('INVALID_GRID', str(e), 400)
    except subprocess.TimeoutExpired:
        return handle_error('TIMEOUT', 'Grid numbering timed out', 504)
    except Exception as e:
        return handle_error('INTERNAL_ERROR', str(e), 500)


@api.route('/normalize', methods=['POST'])
def normalize_entry():
    """POST /api/normalize - Convention normalization endpoint (Phase 3: uses CLI)."""
    try:
        # Validate request
        data = validate_normalize_request(request.json)

        # Delegate to CLI via adapter (with caching for performance)
        result = cli_adapter.normalize(data['text'])

        # CLI output is already in correct format!
        return jsonify(result), 200

    except ValueError as e:
        return handle_error('INVALID_TEXT', str(e), 400)
    except subprocess.TimeoutExpired:
        return handle_error('TIMEOUT', 'Normalization timed out', 504)
    except Exception as e:
        return handle_error('INTERNAL_ERROR', str(e), 500)
