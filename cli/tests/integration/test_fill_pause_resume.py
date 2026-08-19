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
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from cli.src.core.grid import Grid
from cli.src.fill.pause_controller import PauseController
from cli.src.fill.state_manager import CSPState, StateManager

REPO_ROOT = Path(__file__).resolve().parents[3]
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


def _diag(stdout: str, stderr: str, limit: int = 1200) -> str:
    """
    Assertion message for any check on a child spawned by these tests.

    The child's stderr carries its progress stream and any traceback. Without it a
    non-zero exit code is undiagnosable after the fact, and no rerun of the assertion
    can recover it: CI run 32230539895 failed `[hybrid]` on a bare
    `assert proc.returncode == 0` and the log records no cause.
    """
    return f"child stderr tail:\n{stderr[-limit:]}\n\nchild stdout tail:\n{stdout[-limit:]}"


def _run_fill_until_paused(tmp_path, algorithm, task_id, size=15, timeout=120, wait_for_search=False):
    """
    Spawn `fill` on a size×size grid tuned for `algorithm`, let it run, touch the
    pause flag, and collect the paused stdout.

    `wait_for_search` selects when the flag is touched. False (default) sleeps a
    fixed 3s, which is what the repair and beam hooks need. True waits for the
    searching marker, so the pause provably lands after CSP setup and is saved as
    a real CSPState -- required by any test asserting populated domains, since
    setup outlasts a 3s sleep on a blank 15×15.

    Returns (proc, stdout, stderr, state_dir). stderr is returned rather than
    discarded so a caller's assertion can report why the child exited (`_diag`).
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

    # Get the engine past the point this test needs, then request pause.
    if wait_for_search:
        _wait_for_search_marker(flags_dir, task_id)
    else:
        time.sleep(3)
    flags_dir.mkdir(parents=True, exist_ok=True)
    flag_file = flags_dir / f"crossword_pause_{task_id}.flag"
    flag_file.touch()

    stdout, stderr = proc.communicate(timeout=60)
    return proc, stdout, stderr, state_dir


def _wait_for_running_marker(flags_dir: Path, task_id: str, timeout: float = 10.0) -> None:
    """
    Block until `fill`'s early pause/resume registration has written its running
    marker (crossword_running_<task_id>.pid). `mark_running()` runs immediately
    after `clear_pause()` on the SAME PauseController (cli.py), so marker-exists
    implies clear_pause() already ran against `flags_dir` — a pause flag touched
    right after this returns lands strictly after that clear and cannot be wiped
    as a stale flag.
    """
    marker = flags_dir / f"crossword_running_{task_id}.pid"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if marker.exists():
            return
        time.sleep(0.02)
    raise AssertionError(f"running marker never appeared in {flags_dir} for task {task_id}")


def _wait_for_search_marker(flags_dir: Path, task_id: str, timeout: float = 60.0) -> None:
    """
    Block until `fill` has finished CSP setup and entered the search loop
    (crossword_searching_<task_id>.flag).

    A fixed sleep races setup: `_initialize_csp` -> `_ac3` -> `_sort_slots_by_constraint`
    runs for seconds on a blank grid and the window grows with grid and wordlist size.
    A pause landing inside it is handled by `_handle_setup_pause`, which drops the
    half-built domains -- so a test that needs a populated CSPState must wait for
    setup to finish rather than guess a duration.

    `mark_searching()` runs on the same PauseController as the earlier
    `clear_pause()`/`mark_running()` pair (cli.py), so marker-exists also implies a
    pause flag touched afterwards lands strictly after that clear and cannot be
    wiped as stale -- the same ordering guarantee `_wait_for_running_marker` relies on.
    """
    marker = flags_dir / f"crossword_searching_{task_id}.flag"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if marker.exists():
            return
        time.sleep(0.02)
    raise AssertionError(f"search marker never appeared in {flags_dir} for task {task_id}")


def _run_fill(args, timeout=180):
    """Spawn `fill` with the given extra args (NO grid_file positional on resume);
    return the finished CompletedProcess."""
    return subprocess.run(
        [sys.executable, "-m", "cli.src.cli", "fill", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _pause_a_fill(tmp_path, algorithm, task_id, wait_for_search=False):
    """
    Run a fill, pause it mid-run (Task-13 flow), and return
    (grid_file, state_dir, flag_dir, state_file). state_file is the on-disk
    <state_dir>/<task_id>.json.gz written at pause.
    """
    proc, stdout, stderr, state_dir = _run_fill_until_paused(tmp_path, algorithm, task_id, wait_for_search=wait_for_search)
    assert proc.returncode == 0, _diag(stdout, stderr)
    assert json.loads(stdout)["paused"] is True, _diag(stdout, stderr)
    grid_file = tmp_path / "grid.json"
    flag_dir = tmp_path / "flags"
    state_file = state_dir / f"{task_id}.json.gz"
    return grid_file, state_dir, flag_dir, state_file


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
        # 120s of SOLVER budget, not 15. `-t` is wall-clock inside the solver, so
        # the coverage tax lands on it too: this fill needs 0.96s of solver time
        # uninstrumented and 4.35s under coverage locally, and a CI runner is
        # several times slower again -- at 15s the solve did not finish there and
        # the command returned success=False. Sized for margin, not for the wire:
        # nothing here waits out the budget, a solvable 5x5 returns as soon as it
        # is solved.
        "-t",
        "120",
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
    # 300s, not 45s. This is the only test in this file without @pytest.mark.slow,
    # so it is the only one the coverage-instrumented `test (3.12)` matrix job runs
    # -- and pytest-cov instruments the spawned CLI subprocess too. Measured
    # locally: 1.95s without --cov, 34.37s with it, already 76% of the old 45s
    # budget on fast hardware, which is why 3.12 failed while 3.9/3.10/3.11 passed
    # the identical test.
    #
    # Unlike the pause deadlines in the seam tests, this timeout gates nothing: the
    # test asserts that the three options parse and a trivial fill succeeds, and the
    # budget is only a guard against hanging forever. Raising it therefore weakens
    # no guarantee. The marker stays off deliberately -- this is the argv-acceptance
    # contract test the seam rule in .claude/CLAUDE.md requires, so it has to keep
    # running in the default suite a developer gets from plain `pytest`.
    stdout, stderr = proc.communicate(timeout=300)

    assert proc.returncode == 0, _diag(stdout, stderr)
    assert json.loads(stdout)["success"] is True, _diag(stdout, stderr)


def test_pause_resume_list_states_accept_and_honour_the_dir_options(tmp_path):
    """
    Test A2 -- the argv-acceptance half of the seam rule for #25.

    `--state-dir` / `--pause-flag-dir` were declared on `fill` only. `pause`,
    `resume` and `list-states` built StateManager()/PauseController() bare, so
    they read /tmp regardless and agreed with `fill` only because the library
    defaults happen to match. Point `fill` anywhere else and its own companion
    commands stop seeing it, reporting "not found" as though the task were
    missing rather than the path misconfigured.

    Each command is asserted to ACT on the directory it is given, not merely to
    accept the flag without erroring -- a parse-only check would pass against
    the bare constructions this fixes. No solver runs here: state and markers
    are planted directly, so this stays in the default (non-slow) suite, which
    is where the seam rule wants the argv contract test.
    """
    state_dir = tmp_path / "states"
    flags_dir = tmp_path / "flags"
    task_id = "diropts"

    # A wordlist the resumed fill can load, and a state whose grid is already
    # complete so the resume returns without searching.
    wordlist = tmp_path / "wl.txt"
    wordlist.write_text("A" * 11 + "\n")

    # Fully filled, so the resumed fill has no empty slot and returns at once.
    grid = Grid(11)
    for row in range(11):
        grid.place_word("A" * 11, row, 0, "across")
    state_manager = StateManager(storage_dir=state_dir)
    state_manager.save_csp_state(
        task_id=task_id,
        csp_state=CSPState(
            grid_dict=grid.to_dict(),
            domains={},
            constraints={},
            used_words=[],
            slot_id_map={},
            slot_list=[],
            slots_sorted=[],
            current_slot_index=0,
            iteration_count=1,
            locked_slots=[],
            timestamp=datetime.now().isoformat(),
        ),
        metadata={"algorithm": "trie", "wordlists": [str(wordlist)]},
        compress=True,
    )

    def _run(args):
        proc = subprocess.Popen(
            [sys.executable, "-m", "cli.src.cli"] + args,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # 300s like Test A above, and for the same reason: pytest-cov
        # instruments the spawned CLI, which cost that test a ~17x wall tax.
        # Nothing here waits out the budget -- it only guards against a hang.
        return proc, *proc.communicate(timeout=300)

    # --- list-states reads --state-dir, not /tmp/crossword_states ---
    proc, stdout, stderr = _run(["list-states", "--state-dir", str(state_dir), "--json-output"])
    assert proc.returncode == 0, stderr
    listed = json.loads(stdout)
    assert [s["task_id"] for s in listed["states"]] == [task_id], listed

    # --- pause writes its flag into --pause-flag-dir and finds the marker there ---
    # A live pid, so is_task_running() sees a running task rather than a stale file.
    PauseController(task_id=task_id, pause_dir=flags_dir).mark_running()

    proc, stdout, stderr = _run(["pause", task_id, "--pause-flag-dir", str(flags_dir), "--json-output"])
    assert proc.returncode == 0, stderr
    assert json.loads(stdout)["success"] is True
    assert (flags_dir / f"crossword_pause_{task_id}.flag").exists(), "pause flag must land in --pause-flag-dir"

    # --- resume looks the task id up in --state-dir ---
    proc, stdout, stderr = _run(
        [
            "resume",
            task_id,
            "--state-dir",
            str(state_dir),
            "--pause-flag-dir",
            str(flags_dir),
            "-o",
            str(tmp_path / "resumed.json"),
            "-t",
            "120",
            "--json-output",
        ]
    )
    assert proc.returncode == 0, stderr
    assert json.loads(stdout)["success"] is True


@pytest.mark.slow
def test_csp_pause_saves_real_csp_state(tmp_path):
    """Test B — trie/CSP pause persists its real CSPState (populated domains)."""
    proc, stdout, stderr, state_dir = _run_fill_until_paused(tmp_path, "trie", "tB", wait_for_search=True)

    assert proc.returncode == 0, _diag(stdout, stderr)
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
    proc, stdout, stderr, state_dir = _run_fill_until_paused(tmp_path, "repair", "tC")

    assert proc.returncode == 0, _diag(stdout, stderr)
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
    proc, stdout, stderr, state_dir = _run_fill_until_paused(tmp_path, "beam", "tD")

    assert proc.returncode == 0, _diag(stdout, stderr)
    out = json.loads(stdout)
    assert out["paused"] is True

    state_file = state_dir / "tD.json.gz"
    assert state_file.exists()

    with gzip.open(state_file, "rt", encoding="utf-8") as f:
        env = json.load(f)
    assert env["algorithm"] == "csp"
    assert env["state_data"]["domains"] == {}
    assert env["metadata"]["algorithm"] == "beam"


@pytest.mark.slow
def test_repair_pause_before_restart_exits_cleanly(tmp_path):
    """
    None-guard (Task 13 hardening): if the pause flag already exists at restart 0's
    hook #1 check, IterativeRepair.fill() breaks with best_result never populated
    and returns None. The CLI paused branch must treat a None result under an
    active task as a paused-with-no-progress outcome (using the original grid),
    NOT crash on None.paused.

    Synchronization: the flag is touched right after `fill`'s running marker
    appears (crossword_running_tNone.pid) — NOT before the subprocess starts.
    `mark_running()` runs immediately after `clear_pause()` on the same
    PauseController (cli.py), so marker-exists implies clear_pause() already ran
    against --pause-flag-dir and cannot wipe a flag touched afterward. Touching
    the flag before Popen used to "work" only as a symptom of the bug this file's
    Fix-1 companion guards against: clear_pause() used to run against the wrong
    (default /tmp) directory while the solver's separately-constructed controller
    pointed at --pause-flag-dir and was never cleared, so a pre-existing flag
    there survived by accident. Now that clear_pause() correctly targets
    --pause-flag-dir, a flag set before the process starts is legitimately
    treated as stale and cleared — so the pre-existing-flag trick no longer
    reaches hook #1 with a set flag, and the marker-wait handles that instead.
    """
    grid_file = _write_pause_grid(tmp_path / "grid.json", "repair", 15)
    state_dir = tmp_path / "state"
    flags_dir = tmp_path / "flags"
    flags_dir.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "cli.src.cli",
            "fill",
            str(grid_file),
            "-w",
            str(WORDLIST),
            "--algorithm",
            "repair",
            "-t",
            "60",
            "--json-output",
            "--task-id",
            "tNone",
            "--state-dir",
            str(state_dir),
            "--pause-flag-dir",
            str(flags_dir),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    _wait_for_running_marker(flags_dir, "tNone")
    (flags_dir / "crossword_pause_tNone.flag").touch()  # after clear_pause() → pause at restart 0

    stdout, stderr = proc.communicate(timeout=90)

    assert proc.returncode == 0, f"CLI crashed on None result:\n{stderr[-800:]}"
    out = json.loads(stdout)
    assert out["paused"] is True and out["task_id"] == "tNone"
    assert out["slots_filled"] == 0
    assert (state_dir / "tNone.json.gz").exists()


# ---------------------------------------------------------------------------
# Task 14 — `fill --resume`
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_resume_repair_degenerate_reseed_without_wordlists(tmp_path):
    """
    Guard for the DD6 degenerate-save metadata: pausing under -a repair (Click's
    default algorithm for `fill`) must record `wordlists` in the saved state's
    metadata so `fill --resume` with no -w can find them, the same way a CSP
    (regex/trie) pause already does via Autofill._handle_pause.

    Before the fix, the degenerate metadata dict recorded only algorithm/
    slots_filled/total_slots/grid_size — no wordlists — so this resume failed at
    the CLI's wordlist-fallback check ("No wordlists available: none passed with
    -w and none recorded in the saved state") even though the paused run's own
    -w was right there in its argv.

    Uses the same marker-wait synchronization as
    test_repair_pause_before_restart_exits_cleanly (pause hook #1, zero progress)
    on a small blank grid: the point of this test is the wordlists round-trip
    through metadata, not fill quality on a deliberately-hard grid, so both
    phases stay fast and success is not gated on solving a fully-open 15x15.
    The flag is touched only after fill's running marker appears — i.e. after
    its clear_pause() already ran against --pause-flag-dir — so it cannot be
    wiped as stale; see that test's docstring for why touching it before Popen
    would no longer be deterministic.
    """
    grid_file = _write_blank_grid(tmp_path / "grid.json", 5)
    state_dir = tmp_path / "state"
    flags_dir = tmp_path / "flags"
    flags_dir.mkdir(parents=True, exist_ok=True)

    pause_proc_h = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "cli.src.cli",
            "fill",
            str(grid_file),
            "-w",
            str(WORDLIST),
            "--algorithm",
            "repair",
            "-t",
            "30",
            "--allow-nonstandard",
            "--json-output",
            "--task-id",
            "tWL",
            "--state-dir",
            str(state_dir),
            "--pause-flag-dir",
            str(flags_dir),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    _wait_for_running_marker(flags_dir, "tWL")
    (flags_dir / "crossword_pause_tWL.flag").touch()  # after clear_pause() → pause at restart 0
    pause_stdout, pause_stderr = pause_proc_h.communicate(timeout=60)

    assert pause_proc_h.returncode == 0, pause_stderr[-800:]
    paused_out = json.loads(pause_stdout)
    assert paused_out["paused"] is True

    state_file = state_dir / "tWL.json.gz"
    assert state_file.exists()
    with gzip.open(state_file, "rt", encoding="utf-8") as f:
        env = json.load(f)
    assert env["metadata"]["algorithm"] == "repair"
    assert env["metadata"].get("wordlists"), "degenerate save must record wordlists for a -w-less resume"

    resume_proc = _run_fill(
        [
            "--resume",
            str(state_file),
            "--task-id",
            "resume-tWL",
            "--state-dir",
            str(state_dir),
            "--pause-flag-dir",
            str(flags_dir),
            "-t",
            "60",
            "--json-output",
        ],
        timeout=90,
    )
    assert resume_proc.returncode == 0, resume_proc.stderr[-800:]
    result = json.loads(resume_proc.stdout.strip())
    assert result.get("success") is True, result


@pytest.mark.slow
def test_resume_trie_exact_position_runs(tmp_path):
    """
    Exact-position resume: a real CSPState (non-empty domains) from a paused trie
    fill resumes under classic Autofill with NO grid_file positional — grid + solver
    state come from --resume (DD1/DD2/DD3). Proves the resume path runs end-to-end
    and emits the terminal fill schema.

    Completion is deliberately NOT asserted: the pause grid is an all-white 15×15,
    which is not fully solvable (empirically success=False, ~4/30). Like Task 19,
    this gates the resume MECHANISM, not fill quality.
    """
    gf, state_dir, flag_dir, state_file = _pause_a_fill(tmp_path, "trie", "orig-1", wait_for_search=True)
    assert state_file.exists()
    # Sanity: the saved state is a real (non-degenerate) CSPState → exact-position path.
    with gzip.open(state_file, "rt", encoding="utf-8") as f:
        env = json.load(f)
    assert len(env["state_data"]["domains"]) > 0

    proc = _run_fill(
        [
            "--resume",
            str(state_file),
            "-w",
            str(WORDLIST),
            "--task-id",
            "resume-1",
            "--state-dir",
            str(state_dir),
            "--pause-flag-dir",
            str(flag_dir),
            "-t",
            "10",
            "--algorithm",
            "trie",
            "--json-output",
        ],
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    out = json.loads(proc.stdout.strip())
    assert set(out) >= {
        "success",
        "grid",
        "slots_filled",
        "total_slots",
        "fill_percentage",
        "time_elapsed",
        "iterations",
        "problematic_slots_count",
    }
    assert len(out["grid"]) == 15 and all(len(r) == 15 for r in out["grid"])


@pytest.mark.slow
def test_resume_degenerate_reseed_preserves_structure(tmp_path):
    """
    Degenerate re-seed: a graceful-stop state (empty domains) re-seeds the requested
    engine from grid_dict (DD3/DD4). Pauses a BEAM fill (black-squared 3×3-block grid,
    so the black-square assertion is non-vacuous) then resumes with --algorithm repair
    (cross-engine re-seed; repair is the web default).

    Smoke gate: proves it runs and returns a correctly-shaped grid with black-square
    structure intact. Does NOT assert completion or per-cell letter survival — repair
    may legitimately strip non-locked pre-filled cells (DD4 accepted M1 degradation).
    """
    gf, state_dir, flag_dir, state_file = _pause_a_fill(tmp_path, "beam", "orig-2")
    assert state_file.exists()
    with gzip.open(state_file, "rt", encoding="utf-8") as f:
        env = json.load(f)
    assert env["state_data"]["domains"] == {}  # degenerate
    saved = env["state_data"]["grid_dict"]["grid"]
    black = [(r, c) for r, row in enumerate(saved) for c, cell in enumerate(row) if cell == "#"]
    assert black, "fixture must contain black squares for a non-vacuous check"

    proc = _run_fill(
        [
            "--resume",
            str(state_file),
            "-w",
            str(WORDLIST),
            "--task-id",
            "resume-2",
            "--state-dir",
            str(state_dir),
            "--pause-flag-dir",
            str(flag_dir),
            "-t",
            "10",
            "--algorithm",
            "repair",
            "--json-output",
        ],
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    out = json.loads(proc.stdout.strip())
    assert "grid" in out and len(out["grid"]) == len(saved)
    for r, c in black:
        assert out["grid"][r][c] == "#"  # black-square structure preserved


@pytest.mark.slow
@pytest.mark.parametrize("algorithm", ["beam", "hybrid"])
def test_no_orphaned_beam_state_in_default_dir(tmp_path, algorithm):
    """
    #26 finding 2 — the orchestrator's native beam-state writer must stay inert.

    It builds a bare StateManager(), so it ignores --state-dir and always writes
    `<task_id>.json.gz` under the default store. The CLI's canonical degenerate
    save writes the same basename immediately afterwards, so the beam file is
    either orphaned in the default dir (--state-dir set, as here) or overwritten
    outright (--state-dir omitted). Nothing reads it either way.

    Pinned end-to-end because the guard lives in a constructor argument
    (BeamSearchAutofill passes task_id=None to the orchestrator) and a future
    "fix" that re-forwards it would be invisible to any CLI-level assertion.
    Hybrid is included because its phase-1 solver is built through the same
    wrapper (hybrid_autofill.py:138).
    """
    task_id = f"orph{algorithm}{uuid.uuid4().hex[:8]}"
    default_store = StateManager().storage_dir
    orphan = default_store / f"{task_id}.json.gz"

    try:
        proc, stdout, stderr, state_dir = _run_fill_until_paused(tmp_path, algorithm, task_id)

        assert proc.returncode == 0, _diag(stdout, stderr)
        assert json.loads(stdout)["paused"] is True, _diag(stdout, stderr)

        assert not orphan.exists(), (
            f"orchestrator wrote a native beam state to the default store " f"({orphan}); --state-dir was {state_dir}"
        )

        # The one canonical save is the CLI's, in --state-dir, and it is degenerate.
        with gzip.open(state_dir / f"{task_id}.json.gz", "rt", encoding="utf-8") as f:
            env = json.load(f)
        assert env["algorithm"] == "csp"
        assert env["metadata"]["algorithm"] == algorithm
    finally:
        orphan.unlink(missing_ok=True)


@pytest.mark.slow
@pytest.mark.parametrize("algorithm", ["repair", "beam", "hybrid", "trie"])
def test_pause_flag_cleared_only_after_state_is_durable(tmp_path, algorithm):
    """
    #21.2 — the pause-flag lifecycle contract, stated once and pinned for every engine.

    Contract: whoever durably writes the paused state clears the flag immediately
    after the write. CSP (regex/trie) does it engine-side in Autofill._handle_pause;
    repair/beam/hybrid are written by the CLI's degenerate save, so the CLI clears
    there. The `finally` block keeps clearing on any NON-paused exit.

    The ordering is load-bearing: `finally` runs BEFORE the degenerate save, so a
    clear placed there would consume the pause request before the state is on disk,
    and a save that then failed would leave the user with a pause that did nothing
    and nothing to resume from — the vanish mode #26 documents.

    Before this, only CSP cleared. Beam appeared to, via its native state writer,
    but that writer is deliberately inert (#26 finding 2), so its clear was
    unreachable in practice.
    """
    task_id = f"flag{algorithm}{uuid.uuid4().hex[:8]}"
    proc, stdout, stderr, state_dir = _run_fill_until_paused(
        tmp_path, algorithm, task_id, wait_for_search=(algorithm == "trie")
    )

    assert proc.returncode == 0, _diag(stdout, stderr)
    assert json.loads(stdout)["paused"] is True, _diag(stdout, stderr)

    state_file = state_dir / f"{task_id}.json.gz"
    assert state_file.exists(), "precondition: the paused state must be durable"

    flag = tmp_path / "flags" / f"crossword_pause_{task_id}.flag"
    assert not flag.exists(), (
        f"{algorithm} consumed the pause but left its flag behind; the next run "
        f"reusing this task id relies on the start-of-run stale sweep to survive"
    )
