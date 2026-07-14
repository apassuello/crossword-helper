"""
Canonical solver-state and pause-flag directories (DD1, M1 Phase 3 / Task 15).

Single owner for BOTH the saved-state dir and the pause-flag dir. Every backend
route AND every CLI invocation the backend spawns must pass these explicitly — the
split between StateManager's default (/tmp/crossword_states) and PauseController's
default (/tmp) is what made web pause a silent no-op before this landed.

Defaults are chosen so nothing that works today breaks:
- STATE_DIR resolves to backend/data/autofill_states — the same path the pause/resume
  routes already read/write (pause_resume_routes.py), so already-saved state stays
  resolvable (this file lives in backend/core/, so parent.parent == backend/).
- PAUSE_FLAG_DIR defaults to /tmp — matching PauseController's default — now
  single-sourced rather than accidentally agreeing.
Both are env-overridable so tests can point them at a tmp dir.
"""

import os
from pathlib import Path

STATE_DIR = Path(
    os.environ.get(
        "CROSSWORD_STATE_DIR",
        Path(__file__).resolve().parent.parent / "data" / "autofill_states",
    )
)
PAUSE_FLAG_DIR = Path(os.environ.get("CROSSWORD_PAUSE_FLAG_DIR", "/tmp"))

STATE_DIR.mkdir(parents=True, exist_ok=True)
PAUSE_FLAG_DIR.mkdir(parents=True, exist_ok=True)
