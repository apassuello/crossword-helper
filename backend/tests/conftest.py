"""
Pytest configuration and shared fixtures.

This module defines pytest fixtures and configuration that are shared
across all test modules in the test suite.
"""

import pytest
import sys
from pathlib import Path

# Add backend to Python path for imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


@pytest.fixture(scope="session")
def cli_available():
    """
    Check if CLI is available for integration tests.

    Returns:
        bool: True if CLI is available, False otherwise
    """
    try:
        from backend.core.cli_adapter import get_adapter

        adapter = get_adapter()
        return adapter.health_check()
    except Exception:
        return False


@pytest.fixture(scope="session")
def skip_if_no_cli(cli_available):
    """Skip test if CLI is not available."""
    if not cli_available:
        pytest.skip("CLI not available - skipping integration test")
