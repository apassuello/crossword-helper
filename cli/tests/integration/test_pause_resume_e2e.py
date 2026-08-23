"""
Slow end-to-end tests for the pause/resume cycle and beam timeout enforcement.

Run with: python -m pytest -m slow cli/tests/integration/test_pause_resume_e2e.py
"""

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from cli.src.core.grid import Grid
from cli.src.fill.state_manager import StateManager

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
COMPREHENSIVE = os.path.join(PROJECT_ROOT, "data", "wordlists", "comprehensive.txt")


def _cli_cmd(args):
    return [sys.executable, "-m", "cli.src.cli"] + args


def _make_grid_15(path: Path) -> None:
    """Standard-ish valid 15x15 grid with symmetric black squares."""
    blacks = [
        (0, 4),
        (0, 10),
        (1, 4),
        (1, 10),
        (2, 4),
        (2, 10),
        (3, 6),
        (4, 0),
        (4, 1),
        (4, 13),
        (4, 14),
        (5, 7),
        (6, 11),
        (7, 4),
    ]
    grid = Grid(15)
    for r, c in blacks:
        grid.set_black_square(r, c, enforce_symmetry=True)
    path.write_text(json.dumps(grid.to_dict()))


@pytest.mark.slow
class TestPauseResumeEndToEnd:
    """Full pause -> saved state -> resume cycle through the real CLI."""

    def test_pause_saves_state_and_resume_continues_without_wordlists(self, tmp_path):
        task_id = f"e2e_{uuid.uuid4().hex[:10]}"
        grid_path = tmp_path / "g15.json"
        out_path = tmp_path / "paused_grid.json"
        resumed_path = tmp_path / "resumed_grid.json"
        _make_grid_15(grid_path)

        state_manager = StateManager()
        state_file = Path("/tmp/crossword_states") / f"{task_id}.json.gz"
        running_marker = Path(f"/tmp/crossword_running_{task_id}.pid")

        proc = subprocess.Popen(
            _cli_cmd(
                [
                    "fill",
                    str(grid_path),
                    "-w",
                    COMPREHENSIVE,
                    "-t",
                    "120",
                    "-a",
                    "trie",
                    "--task-id",
                    task_id,
                    "-o",
                    str(out_path),
                ]
            ),
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            # Wait for the fill to register itself as running
            deadline = time.time() + 30
            while time.time() < deadline and not running_marker.exists():
                time.sleep(0.2)
            assert running_marker.exists(), "fill never wrote its running marker"

            # Give the CSP a moment to start iterating, then request a pause
            time.sleep(3)
            pause = subprocess.run(
                _cli_cmd(["pause", task_id, "--json-output"]),
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert pause.returncode == 0, pause.stdout + pause.stderr
            assert json.loads(pause.stdout.splitlines()[-1])["success"] is True

            # The fill must exit well before its 120s timeout
            stdout, stderr = proc.communicate(timeout=90)
            assert proc.returncode == 0, stderr

            # Honest output + saved gzipped state + cleaned-up marker files
            # Bench owns the human-mode copy in the merged tree ("⏸ Paused — solver
            # state saved"); main's version said "PAUSED". The contract under test is
            # that human mode announces the pause, not the exact casing.
            assert "paused" in stdout.lower()
            assert state_file.exists(), "no state file written on pause"
            with open(state_file, "rb") as f:
                assert f.read(2) == b"\x1f\x8b", "state file is not gzipped"
            assert not Path(f"/tmp/crossword_pause_{task_id}.flag").exists()
            assert not running_marker.exists()

            # The partial grid was saved too
            assert out_path.exists()

            # Resume WITHOUT -w: wordlists must come from the state
            resume = subprocess.run(
                _cli_cmd(
                    [
                        "resume",
                        task_id,
                        "-t",
                        "20",
                        "-o",
                        str(resumed_path),
                        "--json-output",
                    ]
                ),
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert resume.returncode == 0, resume.stdout + resume.stderr
            result = json.loads(resume.stdout.splitlines()[-1])
            # Continued with the recorded wordlist and the recorded algorithm
            assert result["wordlists"] == [COMPREHENSIVE]
            assert result["algorithm"] == "trie"
            assert result["total_slots"] > 0
            assert resumed_path.exists(), "resume did not save its output grid"
        finally:
            if proc.poll() is None:
                proc.kill()
            state_manager.delete_state(task_id)
            for leftover in (
                Path(f"/tmp/crossword_pause_{task_id}.flag"),
                running_marker,
            ):
                if leftover.exists():
                    leftover.unlink()

    def test_full_cycle_stays_inside_non_default_dirs(self, tmp_path):
        """
        The real-subprocess half of the seam rule for #25.

        The test above runs the same cycle on the DEFAULT directories, so it
        passes whether or not `pause` / `resume` / `list-states` honour
        --state-dir and --pause-flag-dir -- the library defaults agree with
        `fill`'s by coincidence. This one points every command at tmp_path and
        asserts the cycle completes there AND that nothing was written to the
        default locations, which is the only way the coincidence stops
        masking the defect.
        """
        task_id = f"e2edirs_{uuid.uuid4().hex[:10]}"
        grid_path = tmp_path / "g15.json"
        out_path = tmp_path / "paused_grid.json"
        resumed_path = tmp_path / "resumed_grid.json"
        state_dir = tmp_path / "states"
        flags_dir = tmp_path / "flags"
        _make_grid_15(grid_path)

        state_file = state_dir / f"{task_id}.json.gz"
        running_marker = flags_dir / f"crossword_running_{task_id}.pid"

        # If any of these appear, a command fell back to the library default.
        default_leaks = (
            Path("/tmp/crossword_states") / f"{task_id}.json.gz",
            Path(f"/tmp/crossword_running_{task_id}.pid"),
            Path(f"/tmp/crossword_pause_{task_id}.flag"),
        )

        proc = subprocess.Popen(
            _cli_cmd(
                [
                    "fill",
                    str(grid_path),
                    "-w",
                    COMPREHENSIVE,
                    # Solver budget. Separate from every communicate(timeout=)
                    # below: `-t` bounds solver time, the harness budgets bound
                    # wall time, and they fail independently (CONTRIBUTING §3).
                    "-t",
                    "120",
                    "-a",
                    "trie",
                    "--task-id",
                    task_id,
                    "--state-dir",
                    str(state_dir),
                    "--pause-flag-dir",
                    str(flags_dir),
                    "-o",
                    str(out_path),
                ]
            ),
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.time() + 60
            while time.time() < deadline and not running_marker.exists():
                time.sleep(0.2)
            assert running_marker.exists(), "fill never wrote its running marker into --pause-flag-dir"

            time.sleep(3)

            # Pre-fix this reported "not running": `pause` looked in /tmp.
            pause = subprocess.run(
                _cli_cmd(["pause", task_id, "--pause-flag-dir", str(flags_dir), "--json-output"]),
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            assert pause.returncode == 0, pause.stdout + pause.stderr
            assert json.loads(pause.stdout.splitlines()[-1])["success"] is True

            stdout, stderr = proc.communicate(timeout=120)
            assert proc.returncode == 0, stderr
            assert "paused" in stdout.lower()

            assert state_file.exists(), "no state file written into --state-dir"
            with open(state_file, "rb") as f:
                assert f.read(2) == b"\x1f\x8b", "state file is not gzipped"

            # Pre-fix this listed /tmp/crossword_states and never saw the task.
            listed = subprocess.run(
                _cli_cmd(["list-states", "--state-dir", str(state_dir), "--json-output"]),
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            assert listed.returncode == 0, listed.stdout + listed.stderr
            assert task_id in [st["task_id"] for st in json.loads(listed.stdout)["states"]]

            # Pre-fix this failed with "neither an existing state file nor a
            # known task id in /tmp/crossword_states".
            resume = subprocess.run(
                _cli_cmd(
                    [
                        "resume",
                        task_id,
                        "--state-dir",
                        str(state_dir),
                        "--pause-flag-dir",
                        str(flags_dir),
                        "-t",
                        "20",
                        "-o",
                        str(resumed_path),
                        "--json-output",
                    ]
                ),
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )
            assert resume.returncode == 0, resume.stdout + resume.stderr
            assert json.loads(resume.stdout.splitlines()[-1])["total_slots"] > 0
            assert resumed_path.exists(), "resume did not save its output grid"

            # The point of the test: the whole cycle stayed where it was told.
            leaked = [str(pth) for pth in default_leaks if pth.exists()]
            assert leaked == [], f"wrote to default dirs despite explicit ones: {leaked}"
        finally:
            if proc.poll() is None:
                proc.kill()
            for leftover in default_leaks:
                if leftover.exists():
                    leftover.unlink()


@pytest.mark.slow
class TestBeamTimeoutEnforcement:
    """Regression: beam search overran -t because the deadline was only
    checked between iterations, and a single open-grid iteration could run
    long. Fixed by enforcing the deadline inside the hot paths (orchestrator
    loop, backtracking, expansion, slot selection, LCV ordering) -- see
    cli/src/fill/beam_search/orchestrator.py, commit 2ef7d47."""

    def _load_words(self):
        words = []
        with open(COMPREHENSIVE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    words.append(line.split(";")[0].strip().upper())
        return words

    def test_beam_respects_timeout_on_11x11(self):
        from cli.src.fill.beam_search_autofill import BeamSearchAutofill
        from cli.src.fill.trie_pattern_matcher import TriePatternMatcher
        from cli.src.fill.word_list import WordList

        word_list = WordList(self._load_words())
        matcher = TriePatternMatcher(word_list)
        grid = Grid(11)  # Wide open: the historical worst case

        beam = BeamSearchAutofill(grid, word_list, matcher, min_score=30)

        timeout = 15
        start = time.time()
        result = beam.fill(timeout=timeout)
        wall = time.time() - start

        # Aim: overrun under ~20% (allow a little slack for slow CI)
        assert wall <= timeout * 1.35, f"beam ran {wall:.1f}s for -t {timeout}"
        assert result is not None

    def test_hybrid_inherits_beam_timeout(self):
        from cli.src.fill.hybrid_autofill import HybridAutofill
        from cli.src.fill.trie_pattern_matcher import TriePatternMatcher
        from cli.src.fill.word_list import WordList

        word_list = WordList(self._load_words())
        matcher = TriePatternMatcher(word_list)
        grid = Grid(11)

        hybrid = HybridAutofill(grid, word_list, matcher, min_score=30)

        timeout = 30
        start = time.time()
        result = hybrid.fill(timeout=timeout)
        wall = time.time() - start

        assert wall <= timeout * 1.35, f"hybrid ran {wall:.1f}s for -t {timeout}"
        # Total wall time must be reported, not just the repair phase
        assert result.time_elapsed >= wall * 0.8
