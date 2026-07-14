"""
Tests for `fill` pause support via --task-id/--state-dir/--pause-flag-dir.

Covers Task 13 (M1 Phase 3): the CLI fill command gains three pause options and
a uniform paused-outcome protocol across csp (trie/regex), repair, beam, and
hybrid engines.

Test A is fast (no pause). Tests B/C/D spawn a real subprocess, let it run,
touch the pause flag, and assert the paused stdout protocol + saved state file;
they are marked @pytest.mark.slow (deselected by default per pytest.ini).
"""

import gzip
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORDLIST = REPO_ROOT / "data" / "wordlists" / "comprehensive.txt"


def _write_blank_grid(path: Path, size: int) -> Path:
    """Write a blank size×size grid JSON (all '.', no black squares)."""
    grid = [["." for _ in range(size)] for _ in range(size)]
    data = {"size": size, "grid": grid, "black_squares": 0, "is_symmetric": True}
    path.write_text(json.dumps(data))
    return path


def _write_pause_grid(path: Path, algorithm: str, size: int) -> Path:
    """
    Write a size×size grid tuned so `algorithm` reaches its pause hook while the
    grid stays too hard to finish in the pause window.

    - csp (regex/trie) polls every 100 backtracking descents and repair loops on
      conflicts: a fully-open grid (all length-`size` slots) churns indefinitely,
      so both reach their hook well before finishing.
    - beam polls every 10 slot-expansions, and a single length-`size` expansion on
      an open grid is so expensive it never advances 10 iterations. Short slots
      (3×3 open blocks) make each expansion cheap, so iterations climb to the poll,
      while the ~96 slots guarantee it cannot solve before pausing.
    """
    if algorithm in ("beam", "hybrid"):
        grid = [["#" if (r % 4 == 3 or c % 4 == 3) else "." for c in range(size)] for r in range(size)]
    else:
        grid = [["." for _ in range(size)] for _ in range(size)]
    data = {"size": size, "grid": grid}
    path.write_text(json.dumps(data))
    return path


def _run_fill_until_paused(tmp_path, algorithm, task_id, size=15, timeout=120):
    """
    Spawn `fill` on a size×size grid tuned for `algorithm`, let it run 3s, touch
    the pause flag, and collect the paused stdout.

    Returns (proc, stdout, state_dir).
    """
    grid_file = _write_pause_grid(tmp_path / "grid.json", algorithm, size)
    state_dir = tmp_path / "state"
    flags_dir = tmp_path / "flags"

    cmd = [
        sys.executable,
        "-m",
        "cli.src.cli",
        "fill",
        str(grid_file),
        "-w",
        str(WORDLIST),
        "--algorithm",
        algorithm,
        "-t",
        str(timeout),
        "--json-output",
        "--task-id",
        task_id,
        "--state-dir",
        str(state_dir),
        "--pause-flag-dir",
        str(flags_dir),
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Let the engine get well into filling, then request pause.
    time.sleep(3)
    flags_dir.mkdir(parents=True, exist_ok=True)
    flag_file = flags_dir / f"crossword_pause_{task_id}.flag"
    flag_file.touch()

    stdout, _ = proc.communicate(timeout=60)
    return proc, stdout, state_dir


def test_fill_accepts_pause_options(tmp_path):
    """Test A — the three new options parse and a trivial fill still succeeds."""
    grid_file = _write_blank_grid(tmp_path / "grid.json", 5)
    state_dir = tmp_path / "state"
    flags_dir = tmp_path / "flags"

    cmd = [
        sys.executable,
        "-m",
        "cli.src.cli",
        "fill",
        str(grid_file),
        "-w",
        str(WORDLIST),
        "--algorithm",
        "trie",
        "-t",
        "15",
        "--allow-nonstandard",
        "--json-output",
        "--task-id",
        "tA",
        "--state-dir",
        str(state_dir),
        "--pause-flag-dir",
        str(flags_dir),
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, _ = proc.communicate(timeout=45)

    assert proc.returncode == 0
    assert json.loads(stdout)["success"] is True


@pytest.mark.slow
def test_csp_pause_saves_real_csp_state(tmp_path):
    """Test B — trie/CSP pause persists its real CSPState (populated domains)."""
    proc, stdout, state_dir = _run_fill_until_paused(tmp_path, "trie", "tB")

    assert proc.returncode == 0
    out = json.loads(stdout)
    assert out["paused"] is True and out["task_id"] == "tB"
    assert isinstance(out["slots_filled"], int)

    state_file = state_dir / "tB.json.gz"
    assert state_file.exists()

    with gzip.open(state_file, "rt", encoding="utf-8") as f:
        env = json.load(f)
    assert env["algorithm"] == "csp"
    assert isinstance(env["state_data"]["domains"], dict)
    assert len(env["state_data"]["domains"]) > 0


@pytest.mark.slow
def test_repair_pause_saves_degenerate_csp_state(tmp_path):
    """Test C — repair pause routes through the CLI degenerate CSPState writer."""
    proc, stdout, state_dir = _run_fill_until_paused(tmp_path, "repair", "tC")

    assert proc.returncode == 0
    out = json.loads(stdout)
    assert out["paused"] is True

    state_file = state_dir / "tC.json.gz"
    assert state_file.exists()

    with gzip.open(state_file, "rt", encoding="utf-8") as f:
        env = json.load(f)
    assert env["algorithm"] == "csp"
    assert env["state_data"]["domains"] == {}
    assert env["metadata"]["algorithm"] == "repair"
    assert env["state_data"]["grid_dict"]["grid"] is not None


@pytest.mark.slow
def test_beam_pause_routes_through_degenerate_writer(tmp_path):
    """Test D — beam pause routes through the same CLI degenerate writer."""
    proc, stdout, state_dir = _run_fill_until_paused(tmp_path, "beam", "tD")

    assert proc.returncode == 0
    out = json.loads(stdout)
    assert out["paused"] is True

    state_file = state_dir / "tD.json.gz"
    assert state_file.exists()

    with gzip.open(state_file, "rt", encoding="utf-8") as f:
        env = json.load(f)
    assert env["algorithm"] == "csp"
    assert env["state_data"]["domains"] == {}
    assert env["metadata"]["algorithm"] == "beam"
