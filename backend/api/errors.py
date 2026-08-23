"""
Error handling utilities for API responses.

This module provides consistent error response formatting across all API endpoints.
"""

from flask import jsonify


def handle_error(code: str, message: str, status: int, details: dict = None):
    """
    Format error response consistently.

    Args:
        code: Error code (e.g., 'INVALID_PATTERN')
        message: Human-readable message
        status: HTTP status code
        details: Optional additional context

    Returns:
        Flask response tuple (json, status)
    """
    response = {"error": {"code": code, "message": message}}

    if details:
        response["error"]["details"] = details

    return jsonify(response), status
