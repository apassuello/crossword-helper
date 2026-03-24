"""Pytest configuration for CLI tests — adds cli/src to sys.path."""
import sys
import os

# Allow imports like `from core.grid import Grid` in addition to `from src.core.grid import Grid`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
