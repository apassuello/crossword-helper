"""
Request validation functions for API endpoints.

This module validates incoming request data before processing in service layer.
"""


def validate_pattern_request(data: dict) -> dict:
    """
    Validate pattern search request.

    Checks:
    - pattern exists and is string
    - wordlists is list of strings (if provided)
    - max_results is integer 1-100 (if provided)

    Args:
        data: Request data dictionary

    Returns:
        Validated data dict

    Raises:
        ValueError: With specific message about validation failure
    """
    if not data:
        raise ValueError("Request body is required")

    if 'pattern' not in data:
        raise ValueError("Field 'pattern' is required")

    if not isinstance(data['pattern'], str):
        raise ValueError("Field 'pattern' must be string")

    if 'wordlists' in data:
        if not isinstance(data['wordlists'], list):
            raise ValueError("Field 'wordlists' must be array")
        if not all(isinstance(w, str) for w in data['wordlists']):
            raise ValueError("Field 'wordlists' must contain strings")

    if 'max_results' in data:
        if not isinstance(data['max_results'], int):
            raise ValueError("Field 'max_results' must be integer")
        if not 1 <= data['max_results'] <= 100:
            raise ValueError("Field 'max_results' must be 1-100")

    return data


def validate_grid_request(data: dict) -> dict:
    """
    Validate grid numbering request.

    Checks:
    - size exists and is valid (11, 15, or 21)
    - grid exists and is 2D array
    - numbering (if provided) is dictionary

    Args:
        data: Request data dictionary

    Returns:
        Validated data dict

    Raises:
        ValueError: With specific message about validation failure
    """
    if not data:
        raise ValueError("Request body is required")

    if 'size' not in data:
        raise ValueError("Field 'size' is required")

    if not isinstance(data['size'], int):
        raise ValueError("Field 'size' must be integer")

    # Phase 3: Allow non-standard sizes (CLI handles validation)
    if data['size'] < 3 or data['size'] > 50:
        raise ValueError("Field 'size' must be between 3 and 50")

    if 'grid' not in data:
        raise ValueError("Field 'grid' is required")

    if not isinstance(data['grid'], list):
        raise ValueError("Field 'grid' must be array")

    # Validate grid is 2D array
    for row in data['grid']:
        if not isinstance(row, list):
            raise ValueError("Field 'grid' must be 2D array (array of arrays)")

    if 'numbering' in data:
        if not isinstance(data['numbering'], dict):
            raise ValueError("Field 'numbering' must be object")

    return data


def validate_normalize_request(data: dict) -> dict:
    """
    Validate convention normalization request.

    Checks:
    - text exists and is string
    - text is not empty
    - text length is reasonable (<= 100 chars)

    Args:
        data: Request data dictionary

    Returns:
        Validated data dict

    Raises:
        ValueError: With specific message about validation failure
    """
    if not data:
        raise ValueError("Request body is required")

    if 'text' not in data:
        raise ValueError("Field 'text' is required")

    if not isinstance(data['text'], str):
        raise ValueError("Field 'text' must be string")

    if not data['text'].strip():
        raise ValueError("Field 'text' cannot be empty")

    if len(data['text']) > 100:
        raise ValueError("Field 'text' must be at most 100 characters")

    return data
