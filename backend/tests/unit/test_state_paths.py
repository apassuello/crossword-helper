"""
Unit tests for backend.core.state_paths (GitHub issue #21, sub-item 4).

The module used to `mkdir` STATE_DIR and PAUSE_FLAG_DIR at import time, so an
unwritable CROSSWORD_STATE_DIR failed the whole backend import rather than
first use. The fix moves directory creation into `ensure_dirs()`, called once
from the Flask app factory (backend/app.py:create_app) instead of at import.

These tests assert the EFFECT (whether a directory gets created), not merely
that `ensure_dirs` exists.
"""

import importlib
import sys

import backend.core.state_paths as state_paths_module


def _reload_state_paths_with_env(monkeypatch, state_dir, pause_flag_dir):
    """
    Reload backend.core.state_paths with CROSSWORD_STATE_DIR/
    CROSSWORD_PAUSE_FLAG_DIR monkeypatched, returning the freshly reloaded
    module. state_paths reads os.environ at import time, so a plain import
    would just return the cached module with its original values -- an
    importlib.reload against a monkeypatched environment is required to
    actually re-evaluate the module body under the new env.
    """
    monkeypatch.setenv("CROSSWORD_STATE_DIR", str(state_dir))
    monkeypatch.setenv("CROSSWORD_PAUSE_FLAG_DIR", str(pause_flag_dir))
    return importlib.reload(state_paths_module)


def test_import_does_not_create_directories(monkeypatch, tmp_path):
    """Importing/reloading the module must NOT create STATE_DIR or
    PAUSE_FLAG_DIR as a side effect."""
    state_dir = tmp_path / "fresh_state_dir"
    pause_flag_dir = tmp_path / "fresh_pause_dir"
    assert not state_dir.exists()
    assert not pause_flag_dir.exists()

    try:
        reloaded = _reload_state_paths_with_env(monkeypatch, state_dir, pause_flag_dir)

        assert not state_dir.exists(), "import must not create STATE_DIR"
        assert not pause_flag_dir.exists(), "import must not create PAUSE_FLAG_DIR"
        assert reloaded.STATE_DIR == state_dir
        assert reloaded.PAUSE_FLAG_DIR == pause_flag_dir
    finally:
        # Restore module state so later tests in this session import the
        # real (env-default) module, not one left pointed at a tmp_path
        # that is about to be torn down.
        monkeypatch.undo()
        importlib.reload(state_paths_module)


def test_ensure_dirs_creates_directories(monkeypatch, tmp_path):
    """After calling ensure_dirs(), both directories exist."""
    state_dir = tmp_path / "fresh_state_dir2"
    pause_flag_dir = tmp_path / "fresh_pause_dir2"

    try:
        reloaded = _reload_state_paths_with_env(monkeypatch, state_dir, pause_flag_dir)

        reloaded.ensure_dirs()

        assert state_dir.is_dir()
        assert pause_flag_dir.is_dir()
    finally:
        monkeypatch.undo()
        importlib.reload(state_paths_module)


def test_reload_restores_real_module_state():
    """Sanity check that the fixtures above actually restore module state:
    sys.modules still holds the real state_paths module, not a stale one."""
    assert sys.modules["backend.core.state_paths"] is state_paths_module
