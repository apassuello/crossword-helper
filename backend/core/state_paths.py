"""
Canonical solver-state and pause-flag directories (DD1, M1 Phase 3 / Task 15).

Single owner for BOTH the saved-state dir and the pause-flag dir. Every backend
route AND every CLI invocation the backend spawns must pass these explicitly — the
split between StateManager's default (/tmp/crossword_states) and PauseController's
default (/tmp) is what made web pause a silent no-op before this landed.

Defaults:
- STATE_DIR defaults to /tmp/crossword_states — the same path the CLI's StateManager
  uses by default (cli/src/fill/state_manager.py), so the backend can see states a
  bare CLI fill saved without the web API and the CLI re-splitting the store.
- PAUSE_FLAG_DIR defaults to /tmp — matching PauseController's default — now
  single-sourced rather than accidentally agreeing.
Both are env-overridable so tests can point them at a tmp dir.
"""

import os
import re
from pathlib import Path

STATE_DIR = Path(os.environ.get("CROSSWORD_STATE_DIR", "/tmp/crossword_states"))
PAUSE_FLAG_DIR = Path(os.environ.get("CROSSWORD_PAUSE_FLAG_DIR", "/tmp"))


def ensure_dirs() -> None:
    """Create STATE_DIR and PAUSE_FLAG_DIR. Called once from the Flask app factory
    at startup, not at import time and not per request."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PAUSE_FLAG_DIR.mkdir(parents=True, exist_ok=True)


# A task id is interpolated straight into a state-file or pause-flag name, so it
# must not be able to express a path. Ids arriving as a URL segment are already
# safe (Flask's default converter cannot match "/"); ids read from a JSON request
# body are not, and those are the callers of this check. See #21.3.
TASK_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def is_valid_task_id(task_id) -> bool:
    """True if task_id is safe to interpolate into a state/flag filename."""
    return isinstance(task_id, str) and bool(TASK_ID_RE.match(task_id))
