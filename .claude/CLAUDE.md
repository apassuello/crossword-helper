# Claude Assistant Guide

This document provides context for AI assistants working on the Crossword Construction Helper project.

## Project Overview

This is a Flask-based web application designed to help crossword puzzle constructors with three main tasks:

1. **Pattern Matching**: Finding words that match partial patterns (e.g., "?AT?RN" matches "PATTERN")
2. **Numbering Validation**: Validating and generating numbering schemes for crossword grids
3. **Convention Normalization**: Normalizing crossword entries according to publication standards

## Architecture

The project follows a clean separation between:
- **Backend**: Flask application with core business logic
- **Frontend**: Static HTML/CSS/JS served by Flask
- **Data Layer**: Local wordlists and external API integration (OneLook)

## Development Workflow

1. Architecture documents should be placed in `docs/` before implementation
2. All business logic goes in `backend/core/`
3. API endpoints are defined in `backend/api/routes.py`
4. Tests should be written alongside feature implementation
5. Follow the existing module structure and docstring conventions

## Testing

- Unit tests go in `tests/unit/`
- Integration tests go in `tests/integration/`
- Run tests with `pytest` from the project root
- Aim for high coverage of core business logic

## Key Dependencies

- Flask 3.0.0: Web framework
- requests 2.31.0: HTTP client for external APIs
- pytest 7.4.3: Testing framework

## Notes

- The project structure is complete but implementation is pending
- Refer to architecture documents in `docs/` for design decisions
- All Python files currently have docstrings but no implementation
