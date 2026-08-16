"""
Pause control mechanism for autofill operations.

Uses file-based signaling to request pause during long-running algorithms.
Simple, reliable, and cross-platform compatible.
"""

import os
import time
from pathlib import Path
from typing import Optional


class PauseController:
    """
    Manages pause signaling for autofill algorithms.

    Uses a simple flag file system:
    - Backend creates pause flag file to request pause
    - CLI checks flag file periodically during execution
    - When detected, CLI saves state and exits gracefully
    - Flag file is cleaned up after pause
    """

    def __init__(self, task_id: str, pause_dir: Optional[Path] = None):
        """
        Initialize pause controller.

        Args:
            task_id: Unique task identifier
            pause_dir: Directory for pause flag files (default: /tmp)
        """
        self.task_id = task_id

        if pause_dir is None:
            pause_dir = Path("/tmp")

        self.pause_dir = Path(pause_dir)
        self.pause_dir.mkdir(parents=True, exist_ok=True)

        self.pause_file = self.pause_dir / f"crossword_pause_{task_id}.flag"
        self.running_file = self.pause_dir / f"crossword_running_{task_id}.pid"
        self._last_check_time = 0.0
        self._check_interval = 0.1  # NOTE: not currently enforced -- should_pause() calls
        # pause_file.exists() unconditionally on every call; this interval has no effect.

    def should_pause(self) -> bool:
        """
        Check if pause has been requested.

        NOTE: rate-limiting fields (_last_check_time, _check_interval) are tracked but
        not enforced -- pause_file.exists() is called unconditionally on every call.

        Returns:
            True if pause requested, False otherwise
        """
        # Check for pause flag file
        paused = self.pause_file.exists()

        # If paused, always return True immediately
        if paused:
            return True

        # If not paused, apply rate limiting to avoid excessive checks
        current_time = time.time()
        if current_time - self._last_check_time < self._check_interval:
            return False

        self._last_check_time = current_time
        return False  # No pause flag exists

    def request_pause(self) -> None:
        """
        Request algorithm to pause.

        Called by backend to signal CLI to pause.
        Creates a flag file that CLI will detect.
        """
        self.pause_file.touch()

    def clear_pause(self) -> None:
        """
        Clear pause flag.

        Called after pause is acknowledged or on completion.
        """
        if self.pause_file.exists():
            try:
                self.pause_file.unlink()
            except FileNotFoundError:
                # Already deleted, that's fine
                pass

    def cleanup(self) -> None:
        """
        Clean up pause flag on completion.

        Should be called when algorithm completes (success or failure).
        """
        self.clear_pause()

    def mark_running(self) -> None:
        """
        Record that a fill process for this task id is running.

        Writes a pid file so `crossword pause` can tell whether a pause
        request will actually be seen by a live process.
        """
        try:
            self.running_file.write_text(str(os.getpid()))
        except OSError:
            pass  # Non-fatal: pause will just report "not running"

    def clear_running(self) -> None:
        """Remove the running marker (call on process exit, pause, or completion)."""
        try:
            self.running_file.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    def is_task_running(self) -> bool:
        """
        Check whether a live fill process is registered for this task id.

        Returns:
            True if the pid file exists and the recorded process is alive.
            A stale pid file (dead process) is cleaned up and reported False.
        """
        if not self.running_file.exists():
            return False
        try:
            pid = int(self.running_file.read_text().strip())
        except (ValueError, OSError):
            self.clear_running()
            return False
        try:
            os.kill(pid, 0)  # Signal 0: existence check only
            return True
        except ProcessLookupError:
            # Stale marker from a dead process — clean it up
            self.clear_running()
            return False
        except PermissionError:
            return True  # Process exists but owned by someone else
        except OSError:
            return False

    def is_paused(self) -> bool:
        """
        Check if currently in paused state.

        Returns:
            True if pause flag exists
        """
        return self.pause_file.exists()

    def __enter__(self):
        """Context manager entry: clear any existing pause flag."""
        self.clear_pause()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: clean up pause flag."""
        self.cleanup()
        return False

    def __repr__(self) -> str:
        return f"PauseController(task_id='{self.task_id}', paused={self.is_paused()})"


class PausedException(Exception):
    """
    Exception raised when algorithm is paused.

    Signals that execution should stop gracefully and save state.
    """

    def __init__(self, message: str = "Autofill paused by user"):
        self.message = message
        super().__init__(self.message)
