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
from pathlib import Path

STATE_DIR = Path(os.environ.get("CROSSWORD_STATE_DIR", "/tmp/crossword_states"))
PAUSE_FLAG_DIR = Path(os.environ.get("CROSSWORD_PAUSE_FLAG_DIR", "/tmp"))

STATE_DIR.mkdir(parents=True, exist_ok=True)
PAUSE_FLAG_DIR.mkdir(parents=True, exist_ok=True)
