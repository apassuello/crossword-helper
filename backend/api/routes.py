"""
Flask API routes for crossword helper endpoints.

This module defines HTTP endpoints for pattern matching, grid numbering,
and convention normalization.
"""

from flask import Blueprint, request, jsonify
from backend.core.pattern_matcher import PatternMatcher
from backend.core.numbering import NumberingValidator
from backend.core.conventions import ConventionHelper
from backend.core.scoring import analyze_letters
from backend.api.validators import (
    validate_pattern_request,
    validate_grid_request,
    validate_normalize_request
)
from backend.api.errors import handle_error

api = Blueprint('api', __name__)

# Initialize services (shared across requests)
pattern_matcher = PatternMatcher(['personal', 'standard'])
numbering_validator = NumberingValidator()
convention_helper = ConventionHelper()


@api.route('/health', methods=['GET'])
def health_check():
    """GET /api/health - Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'version': '0.1.0',
        'components': {
            'pattern_matcher': 'ok',
            'numbering_validator': 'ok',
            'convention_helper': 'ok'
        }
    }), 200


@api.route('/pattern', methods=['POST'])
def pattern_search():
    """POST /api/pattern - Pattern search endpoint."""
    try:
        # Validate request
        data = validate_pattern_request(request.json)

        # Delegate to service
        results = pattern_matcher.search(
            pattern=data['pattern'],
            max_results=data.get('max_results', 20)
        )

        # Format response
        return jsonify({
            'results': [
                {
                    'word': word,
                    'score': score,
                    'source': source,
                    'length': len(word),
                    'letter_quality': analyze_letters(word)
                }
                for word, score, source in results
            ],
            'meta': {
                'pattern': data['pattern'],
                'total_found': len(results),
                'results_returned': min(len(results), data.get('max_results', 20)),
                'sources_searched': data.get('wordlists', ['personal', 'standard'])
            }
        }), 200

    except ValueError as e:
        return handle_error('INVALID_PATTERN', str(e), 400)
    except Exception as e:
        return handle_error('INTERNAL_ERROR', str(e), 500)


@api.route('/number', methods=['POST'])
def number_grid():
    """POST /api/number - Grid numbering validation endpoint."""
    try:
        # Validate request
        data = validate_grid_request(request.json)

        # Extract grid
        grid = data['grid']

        # Auto-number the grid
        numbering = numbering_validator.auto_number(grid)

        # Convert tuple keys to strings for JSON serialization
        numbering_serializable = {
            f"({k[0]},{k[1]})": v
            for k, v in numbering.items()
        }

        # If user provided numbering, validate it
        validation_results = None
        if 'numbering' in data:
            user_numbering = {}
            for pos_str, num in data['numbering'].items():
                # Parse "(row,col)" format
                pos_str = pos_str.strip('()')
                row, col = map(int, pos_str.split(','))
                user_numbering[(row, col)] = num

            is_valid, errors = numbering_validator.validate(grid, user_numbering)
            validation_results = {
                'is_valid': is_valid,
                'errors': errors
            }

        # Analyze grid characteristics
        grid_info = numbering_validator.analyze_grid(grid)

        return jsonify({
            'numbering': numbering_serializable,
            'validation': validation_results,
            'grid_info': grid_info
        }), 200

    except ValueError as e:
        return handle_error('INVALID_GRID', str(e), 400)
    except Exception as e:
        return handle_error('INTERNAL_ERROR', str(e), 500)


@api.route('/normalize', methods=['POST'])
def normalize_entry():
    """POST /api/normalize - Convention normalization endpoint."""
    try:
        # Validate request
        data = validate_normalize_request(request.json)

        # Normalize text
        normalized, rule_info = convention_helper.normalize(data['text'])

        # Get alternatives
        alternatives = convention_helper.get_alternatives(data['text'], normalized)

        return jsonify({
            'original': data['text'],
            'normalized': normalized,
            'rule': rule_info,
            'alternatives': alternatives
        }), 200

    except ValueError as e:
        return handle_error('INVALID_TEXT', str(e), 400)
    except Exception as e:
        return handle_error('INTERNAL_ERROR', str(e), 500)
