"""
CLI Adapter — subprocess interface for calling the crossword CLI from Flask routes.
"""

import json
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Solver-state + pause-flag dirs for the resume argv, single-sourced from state_paths
# (DD5) so routes, the pause route, and this adapter all agree. Re-exported here so the
# resume argv and its tests import one canonical source.
from backend.core.state_paths import PAUSE_FLAG_DIR, STATE_DIR

# The CLI's --timeout bounds SOLVER time only; wall time additionally
# includes interpreter startup, loading the default wordlist, building the
# trie, and (for resume) inflating the gzipped state.
#
# The subprocess ceiling applied at the _run_command() call sites in
# fill() and fill_with_resume() is an ADDEND, not a multiplier:
#     ceiling = timeout_seconds + CLI_STARTUP_BUDGET_SECONDS
# A run that goes to exhaustion has wall = startup + timeout_seconds.
# timeout_seconds cancels out of "does wall stay under ceiling" — the run
# survives only if startup < CLI_STARTUP_BUDGET_SECONDS. The available
# margin IS the startup budget.
#
# Measured in CI run 32003100530 on the Python 3.12 runner (same runner,
# same commit): test_resume_without_edits (--timeout 3, ceiling 93s) took
# 93.4s and got a 504; test_resume_with_edits (--timeout 300, ceiling 390s)
# took 92.3s and passed. Both subprocesses took ~92s wall time; only the
# ceiling differed. The identical subprocess took 8.1s on the Python 3.11
# runner in the same run — startup is runner-dependent and can approach 90s.
CLI_STARTUP_BUDGET_SECONDS = 180


class CLIAdapter:
    """
    Adapter for calling crossword CLI commands from web API.

    Provides methods that wrap CLI commands and return parsed JSON results.
    Handles errors, timeouts, and caching.
    """

    def __init__(self, cli_path: Optional[str] = None, timeout: int = 30):
        """
        Initialize CLI adapter.

        Args:
            cli_path: Path to crossword CLI executable (auto-detected if None)
            timeout: Default timeout for CLI commands in seconds
        """
        if cli_path is None:
            # Auto-detect CLI path (relative to backend directory)
            backend_dir = Path(__file__).parent.parent
            project_root = backend_dir.parent
            cli_path = project_root / "cli" / "crossword"

        self.cli_path = Path(cli_path)
        self.timeout = timeout

        if not self.cli_path.exists():
            raise FileNotFoundError(f"CLI executable not found at {self.cli_path}")

        if not self.cli_path.is_file():
            raise ValueError(f"CLI path is not a file: {self.cli_path}")

    def _run_command(self, args: List[str], timeout: Optional[int] = None, check_success: bool = True) -> Tuple[str, str, int]:
        """
        Run a CLI command and return stdout, stderr, and return code.

        Args:
            args: Command arguments (e.g., ['pattern', 'C?T', '--json-output'])
            timeout: Timeout in seconds (uses default if None)
            check_success: Raise error if return code is non-zero

        Returns:
            Tuple of (stdout, stderr, return_code)

        Raises:
            subprocess.TimeoutExpired: If command times out
            subprocess.CalledProcessError: If command fails and check_success=True
        """
        timeout = timeout or self.timeout

        # Build full command
        cmd = [str(self.cli_path)] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.cli_path.parent,  # Run from CLI directory
            )

            if check_success and result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)

            return result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired as e:
            raise subprocess.TimeoutExpired(
                cmd,
                timeout,
                output=getattr(e, "output", None),
                stderr=getattr(e, "stderr", None),
            )

    def pattern(
        self,
        pattern: str,
        wordlist_paths: Optional[List[str]] = None,
        max_results: int = 20,
        algorithm: str = "regex",
    ) -> Dict[str, Any]:
        """
        Find words matching a pattern.

        Args:
            pattern: Pattern to search (e.g., "C?T")
            wordlist_paths: List of paths to word list files
            max_results: Maximum number of results to return
            algorithm: Pattern matching algorithm ("regex" or "trie")

        Returns:
            Dict with 'results' and 'meta' keys

        Raises:
            ValueError: If pattern is invalid
            subprocess.TimeoutExpired: If command times out
        """
        if not pattern or not pattern.strip():
            raise ValueError("Pattern cannot be empty")

        # Build command args
        args = [
            "pattern",
            pattern,
            "--json-output",
            "--max-results",
            str(max_results),
            "--algorithm",
            algorithm,
        ]

        if wordlist_paths:
            for wordlist_path in wordlist_paths:
                args.extend(["--wordlists", wordlist_path])

        # Run command. The CLI validates patterns itself and exits 1 with a
        # JSON error object for invalid input — surface that as ValueError so
        # routes can return a 400 instead of a generic 500.
        stdout, stderr, returncode = self._run_command(args, timeout=300, check_success=False)

        if returncode != 0:
            try:
                error_data = json.loads(stdout)
                message = error_data.get("error", "Pattern search failed")
            except json.JSONDecodeError:
                message = "Pattern search failed"
            raise ValueError(message)

        # Parse JSON output
        try:
            result = json.loads(stdout)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse CLI output as JSON: {e}\nOutput: {stdout}")

    def normalize(self, text: str) -> Dict[str, Any]:
        """
        Normalize a crossword entry according to conventions.

        Args:
            text: Text to normalize (e.g., "Tina Fey")

        Returns:
            Dict with 'original', 'normalized', 'rule', and 'alternatives' keys

        Raises:
            ValueError: If text is invalid
            subprocess.TimeoutExpired: If command times out
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Build command args
        args = ["normalize", text, "--json-output"]

        # Run command (use very short timeout for this simple operation)
        stdout, stderr, _ = self._run_command(args, timeout=5)

        # Parse JSON output
        try:
            result = json.loads(stdout)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse CLI output as JSON: {e}\nOutput: {stdout}")

    def number(self, grid_data: Dict[str, Any], allow_nonstandard: bool = False) -> Dict[str, Any]:
        """
        Auto-number a crossword grid.

        Args:
            grid_data: Grid data dictionary (will be written to temp file)
            allow_nonstandard: Allow non-standard grid sizes (not 11/15/21)

        Returns:
            Dict with 'numbering' and 'grid_info' keys

        Raises:
            ValueError: If grid data is invalid
            subprocess.TimeoutExpired: If command times out
        """
        if not grid_data:
            raise ValueError("Grid data cannot be empty")

        # Write grid to temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grid_data, f)
            temp_path = f.name

        try:
            # Build command args
            args = ["number", temp_path, "--json-output"]

            if allow_nonstandard:
                args.append("--allow-nonstandard")

            # Run command (allow more time for large grids)
            stdout, stderr, _ = self._run_command(args, timeout=60)

            # Parse JSON output
            try:
                result = json.loads(stdout)
                return result
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse CLI output as JSON: {e}\nOutput: {stdout}")
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    def analyze_constraints(
        self,
        grid_data: Dict[str, Any],
        wordlist_paths: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze grid constraints (per-cell option counts).

        Args:
            grid_data: Grid data dictionary
            wordlist_paths: List of wordlist file paths

        Returns:
            Dict with 'constraints' and 'summary' keys
        """
        if not grid_data:
            raise ValueError("Grid data cannot be empty")
        if not wordlist_paths:
            raise ValueError("At least one wordlist path is required")

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grid_data, f)
            temp_path = f.name

        try:
            args = ["analyze", temp_path, "--json-output"]
            for wl in wordlist_paths:
                args.extend(["-w", wl])

            stdout, stderr, _ = self._run_command(args, timeout=30)

            try:
                return json.loads(stdout)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse CLI output: {e}\nOutput: {stdout}")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def analyze_placement_impact(
        self,
        grid_data: Dict[str, Any],
        word: str,
        slot: Dict[str, Any],
        wordlist_paths: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze how placing a word affects crossing slots.

        Args:
            grid_data: Grid data dictionary
            word: Word to place
            slot: Slot dict with row, col, direction, length
            wordlist_paths: List of wordlist file paths

        Returns:
            Dict with 'impacts' and 'summary' keys
        """
        if not grid_data:
            raise ValueError("Grid data cannot be empty")
        if not word:
            raise ValueError("Word cannot be empty")

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grid_data, f)
            temp_path = f.name

        try:
            slot_str = f"{slot['row']},{slot['col']},{slot['direction']},{slot['length']}"
            args = [
                "analyze",
                temp_path,
                "--json-output",
                "--word",
                word,
                "--slot",
                slot_str,
            ]
            for wl in wordlist_paths:
                args.extend(["-w", wl])

            stdout, stderr, _ = self._run_command(args, timeout=30)

            try:
                return json.loads(stdout)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse CLI output: {e}\nOutput: {stdout}")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def fill(
        self,
        grid_data: Dict[str, Any],
        wordlist_paths: List[str],
        timeout_seconds: int = 300,
        min_score: int = 30,
        algorithm: str = "trie",
        allow_nonstandard: bool = None,
        partial_fill: bool = False,
    ) -> Dict[str, Any]:
        """
        Auto-fill a crossword grid using CSP solver.

        Args:
            grid_data: Grid data dictionary
            wordlist_paths: List of paths to word list files
            timeout_seconds: Maximum time to spend filling
            min_score: Minimum word quality score
            algorithm: Pattern matching algorithm ('regex' or 'trie')
            allow_nonstandard: Allow non-standard grid sizes (auto-detected if None)
            partial_fill: Enable collaborative partial fill mode (stops when stuck, preserves valid words)

        Returns:
            Dict with filled grid and metadata

        Raises:
            ValueError: If grid data is invalid
            subprocess.TimeoutExpired: If command times out
        """
        if not grid_data:
            raise ValueError("Grid data cannot be empty")

        if not wordlist_paths:
            raise ValueError("At least one wordlist path required")

        # Auto-detect if grid size is non-standard
        if allow_nonstandard is None:
            grid_size = grid_data.get("size", len(grid_data.get("grid", [])))
            allow_nonstandard = grid_size not in [11, 15, 21]

        # Write grid to temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grid_data, f)
            grid_path = f.name

        # Create temp output file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            # Build command args
            args = [
                "fill",
                grid_path,
                "--output",
                output_path,
                "--timeout",
                str(timeout_seconds),
                "--min-score",
                str(min_score),
                "--algorithm",
                algorithm,
            ]

            if allow_nonstandard:
                args.append("--allow-nonstandard")

            if partial_fill:
                args.append("--partial-fill")

            for wordlist_path in wordlist_paths:
                args.extend(["--wordlists", wordlist_path])

            # Run command (with extended timeout)
            stdout, stderr, _ = self._run_command(
                args,
                timeout=timeout_seconds + CLI_STARTUP_BUDGET_SECONDS,
                check_success=False,  # Partial fills are OK
            )

            # Read filled grid from output file
            if not Path(output_path).exists() or Path(output_path).stat().st_size == 0:
                return {"success": False, "error": "CLI produced no output"}

            try:
                with open(output_path, "r") as f:
                    result = json.load(f)
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"CLI produced invalid JSON: {e}"}

            return result
        finally:
            # Clean up temp files
            Path(grid_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def fill_with_resume(
        self,
        task_id: str,
        state_file_path: str,
        wordlist_paths: List[str],
        timeout_seconds: int = 300,
        min_score: int = 30,
        algorithm: str = "trie",
        state_dir: Optional[str] = None,
        pause_flag_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resume auto-fill from saved state.

        Args:
            task_id: Task ID for pause control
            state_file_path: Path to saved CSP state file
            wordlist_paths: List of paths to word list files
            timeout_seconds: Maximum time to spend filling
            min_score: Minimum word quality score
            algorithm: Pattern matching algorithm ('regex' or 'trie')
            state_dir: Dir for the resumed run's re-pause state (defaults to STATE_DIR)
            pause_flag_dir: Dir watched for the re-pause flag (defaults to PAUSE_FLAG_DIR)

        Returns:
            Dict with filled grid and metadata

        Raises:
            ValueError: If state file is invalid
            FileNotFoundError: If state file not found
            subprocess.TimeoutExpired: If command times out
        """
        state_path = Path(state_file_path)
        if not state_path.exists():
            raise FileNotFoundError(f"State file not found: {state_file_path}")

        # Create temp output file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            # Build command args. DD5: always thread --state-dir/--pause-flag-dir so the
            # resumed run is itself re-pausable and both dirs are single-sourced (never
            # left to the CLI's split defaults). --json-output puts the full result object
            # on stdout — the contract `docs/specs/CLI_SPEC.md` ratifies — with the
            # --output file kept as a fallback for readers that only need the grid.
            args = [
                "fill",
                "--resume",
                str(state_path),
                "--task-id",
                task_id,
                "--state-dir",
                str(state_dir or STATE_DIR),
                "--pause-flag-dir",
                str(pause_flag_dir or PAUSE_FLAG_DIR),
                "--output",
                output_path,
                "--timeout",
                str(timeout_seconds),
                "--min-score",
                str(min_score),
                "--algorithm",
                algorithm,
                "--json-output",
            ]

            for wordlist_path in wordlist_paths:
                args.extend(["--wordlists", wordlist_path])

            # Run command (with extended timeout)
            stdout, stderr, _ = self._run_command(
                args,
                timeout=timeout_seconds + CLI_STARTUP_BUDGET_SECONDS,
                check_success=False,  # Partial fills are OK
            )

            # Prefer the full result object from stdout (--json-output):
            # success, grid, slots_filled, total_slots, paused, ...
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                pass

            # Fallback: read the saved grid from the output file
            with open(output_path, "r") as f:
                result = json.load(f)

            return result
        finally:
            # Clean up temp output file
            Path(output_path).unlink(missing_ok=True)

    def health_check(self) -> bool:
        """
        Check if CLI is accessible and working.

        Returns:
            True if CLI is healthy, False otherwise
        """
        try:
            # Try running a simple command
            stdout, stderr, code = self._run_command(["normalize", "TEST", "--json-output"], timeout=5, check_success=False)
            return code == 0
        except Exception:
            return False


# Global adapter instance (initialized on first import)
_adapter = None


def get_adapter() -> CLIAdapter:
    """
    Get the global CLI adapter instance.

    Returns:
        CLIAdapter instance
    """
    global _adapter
    if _adapter is None:
        _adapter = CLIAdapter()
    return _adapter


# Cached wrapper functions for better performance
@lru_cache(maxsize=128)
def cached_normalize(text: str) -> str:
    """
    Cached version of normalize (returns JSON string for caching).

    Args:
        text: Text to normalize

    Returns:
        JSON string of normalized result
    """
    adapter = get_adapter()
    result = adapter.normalize(text)
    return json.dumps(result)


def normalize_cached(text: str) -> Dict[str, Any]:
    """
    Normalize text with caching.

    Args:
        text: Text to normalize

    Returns:
        Normalized result dictionary
    """
    result_json = cached_normalize(text)
    return json.loads(result_json)
