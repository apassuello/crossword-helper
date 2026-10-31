"""
Tests that ``clues`` survive fill -> pause -> resume (clue-authoring spec 0.1.4,
section 3.5 "Grid JSON file, CLI" bullets, section 6.1 "Round trip" and the
third "Seam" bullet, section 6.3 the ``fill`` row, section 9 CA-2).

Three kinds of pause state exist and each is its own save site:

* CSP state, saved by the CSP engine (``fill --algorithm trie``);
* the CLI's degenerate CSP-type state, saved by ``fill`` for every other
  algorithm (``--algorithm repair``, and ``--algorithm beam``, see below);
* beam-type state, saved by ``save_beam_search_state``.

Beam finding (measured 2026-10-31, Task 3 RED): a real ``fill --algorithm beam``
that is paused leaves the CLI's *degenerate CSP-type* state as
``<state-dir>/<task_id>.json.gz`` (envelope ``algorithm == "csp"``,
``metadata["algorithm"] == "beam"``). The orchestrator's own save needs a
``task_id`` that ``BeamSearchAutofill`` never forwards, and it would write
through a default ``StateManager`` rather than ``--state-dir`` anyway. So no
beam-type state survives the CLI path, and the beam-type row below builds one
with ``save_beam_search_state``.

Every real-pause test names its algorithm explicitly. Every end-to-end test
checks the pause state's ``metadata["clues"]`` as well as the resumed file.
``clues`` are compared by equality with the value written into the input; no
statuses are asserted. "No clues" means the key is absent, not ``{}``.
"""

import gzip
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

from cli.src.core.grid import Grid
from cli.src.fill.beam_search.state import BeamState
from cli.src.fill.state_manager import BeamSearchState, CSPState, StateManager

REPO_ROOT = Path(__file__).resolve().parents[3]
WORDLIST = REPO_ROOT / "data" / "wordlists" / "comprehensive.txt"

CLUES = {
    "0,0,across": {"text": "Opening entry", "answer": "???????????"},
    "0,0,down": {"text": "Opening entry, down", "answer": "???????????"},
    "5,5,across": {"text": "Orphaned once the grid is filled in", "answer": "XY"},
}
OTHER_CLUES = {"0,0,across": {"text": "From a different file", "answer": "AB"}}

TASK_ID = "clues_task"
# fill and resume reject a timeout under 10 s; a resumed blank 11x11 does not finish in it.
RESUME_TIMEOUT = "10"


# --- helpers -----------------------------------------------------------------


def run_cli(args, timeout=180):
    return subprocess.run(
        [sys.executable, "-m", "cli.src.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=timeout,
    )


def diag(proc):
    return f"stderr tail:\n{proc.stderr[-800:]}\nstdout tail:\n{proc.stdout[-400:]}"


def read_envelope(state_file):
    with gzip.open(state_file, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_grid(path, algorithm, **extra):
    """An 11x11 grid that stays unsolved long enough to be paused.

    Beam polls the pause flag every 10 slot expansions, and an expansion over
    full-width slots on an open grid never gets there; 3x3 open blocks keep each
    expansion cheap. The other engines churn on a blank grid.
    """
    size = 11
    if algorithm == "beam":
        grid = [["#" if (r % 4 == 3 or c % 4 == 3) else "." for c in range(size)] for r in range(size)]
    else:
        grid = [["." for _ in range(size)] for _ in range(size)]
    doc = {"size": size, "grid": grid}
    doc.update(extra)
    path.write_text(json.dumps(doc))
    return path


def wait_for_marker(flags_dir, kind, task_id, timeout=60.0):
    """Block until crossword_<kind>_<task_id>.{pid,flag} exists in flags_dir.

    `running` is written right after the run clears any stale pause flag, so a
    pause flag touched after it cannot be wiped. `searching` is written by the CSP
    engine once setup is done.
    """
    suffix = "pid" if kind == "running" else "flag"
    marker = flags_dir / f"crossword_{kind}_{task_id}.{suffix}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if marker.exists():
            return
        time.sleep(0.02)
    raise AssertionError(f"{kind} marker never appeared in {flags_dir} for task {task_id}")


def run_until_paused(cmd, flags_dir, task_id, wait):
    """Spawn `cmd`, wait per `wait`, request a pause, return (proc, stdout, stderr).

    wait == "searching": wait for the CSP search marker, so the pause lands in the
    search loop (a saved CSPState with populated domains).
    wait == "sleep": wait for the running marker, then 3 s, as the existing seam
    tests do for the beam hook (and for a resumed CSP run, which never writes the
    search marker).
    wait == "immediate": touch the flag right after the running marker, so it is
    seen at the engine's first hook. For repair that is "paused before any work":
    the saved grid is the untouched input, still with empty slots. A repair left to
    run is saved fully filled (with conflicts), and a `fill --resume` of a full
    grid returns early without writing anything.
    """
    flags_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        wait_for_marker(flags_dir, "running", task_id)
        if wait == "searching":
            wait_for_marker(flags_dir, "searching", task_id)
        elif wait == "sleep":
            time.sleep(3)
        (flags_dir / f"crossword_pause_{task_id}.flag").touch()
        stdout, stderr = proc.communicate(timeout=120)
    finally:
        if proc.poll() is None:
            proc.kill()
    return proc, stdout, stderr


class Paused:
    """A real `fill` that was paused: paths for everything a test may read."""

    def __init__(self, root, algorithm):
        self.root = root
        self.algorithm = algorithm
        self.grid_file = root / "grid.json"
        self.paused_grid_file = root / "paused_grid.json"
        self.state_dir = root / "state"
        self.flags_dir = root / "flags"
        self.state_file = self.state_dir / f"{TASK_ID}.json.gz"


def pause_real_fill(root, algorithm, human_mode=False, clues=CLUES):
    """Run a real `fill --algorithm <algorithm>` carrying `clues` and pause it."""
    paused = Paused(root, algorithm)
    write_grid(paused.grid_file, algorithm, clues=clues)
    cmd = [
        sys.executable,
        "-m",
        "cli.src.cli",
        "fill",
        str(paused.grid_file),
        "-w",
        str(WORDLIST),
        "--algorithm",
        algorithm,
        "-t",
        "120",
        "--task-id",
        TASK_ID,
        "--state-dir",
        str(paused.state_dir),
        "--pause-flag-dir",
        str(paused.flags_dir),
    ]
    if not human_mode:
        cmd += ["--json-output", "-o", str(paused.paused_grid_file)]
    wait = {"trie": "searching", "repair": "immediate", "beam": "sleep"}[algorithm]
    proc, stdout, stderr = run_until_paused(cmd, paused.flags_dir, TASK_ID, wait)
    assert proc.returncode == 0, f"stderr tail:\n{stderr[-800:]}\nstdout tail:\n{stdout[-400:]}"
    assert paused.state_file.exists(), f"no state file after pause\nstdout tail:\n{stdout[-400:]}"
    if not human_mode:
        assert json.loads(stdout.strip().splitlines()[-1])["paused"] is True, stdout[-400:]
    saved_grid = read_envelope(paused.state_file)["state_data"]
    saved_grid = saved_grid["grid_dict"] if "grid_dict" in saved_grid else saved_grid["beam"][0]["grid_dict"]
    assert any(cell == "." for row in saved_grid["grid"] for cell in row), "the paused grid has no empty slot left to resume"
    return paused


@pytest.fixture(scope="module")
def paused_fill(tmp_path_factory):
    """Factory: one real paused fill per algorithm, shared by the resume tests.

    The resume tests only read the state file (a resume that pauses again works on
    a copy), so sharing keeps the suite to one pause per algorithm.
    """
    cache = {}

    def get(algorithm):
        if algorithm not in cache:
            cache[algorithm] = pause_real_fill(tmp_path_factory.mktemp(f"paused_{algorithm}"), algorithm)
        return cache[algorithm]

    return get


def resume_cmd(paused, out_file, *, state_dir=None, flags_dir=None, extra=()):
    return [
        "resume",
        str(paused.state_file),
        "--state-dir",
        str(state_dir or paused.state_dir),
        "--pause-flag-dir",
        str(flags_dir or paused.flags_dir),
        "-o",
        str(out_file),
        "--json-output",
        *extra,
    ]


def fill_resume_cmd(paused, out_file, *, grid_file=None, state_dir=None, flags_dir=None, extra=()):
    return [
        "fill",
        *([str(grid_file)] if grid_file else []),
        "--resume",
        str(paused.state_file),
        "--state-dir",
        str(state_dir or paused.state_dir),
        "--pause-flag-dir",
        str(flags_dir or paused.flags_dir),
        "-o",
        str(out_file),
        "--json-output",
        *extra,
    ]


def copy_state_dir(paused, tmp_path):
    """A private copy of the paused state, for a resume that overwrites it."""
    state_dir = tmp_path / "state"
    shutil.copytree(paused.state_dir, state_dir)
    return state_dir


# --- real fill -> pause: each pause state carries the clues ------------------


# What each algorithm's pause state must look like, so the test is known to
# exercise the save site it is named for (envelope algorithm, domains populated).
SAVE_SITES = {
    "trie": ("csp", True),  # the CSP engine's own save (autofill.py)
    "repair": ("csp", False),  # the CLI's degenerate save (cli.py)
    "beam": ("csp", False),  # the same degenerate save: no beam-type state survives the CLI
}


@pytest.mark.slow
@pytest.mark.parametrize("algorithm", ["trie", "repair", "beam"])
def test_pause_state_carries_clues(paused_fill, algorithm):
    paused = paused_fill(algorithm)

    envelope = read_envelope(paused.state_file)
    envelope_algorithm, has_domains = SAVE_SITES[algorithm]
    assert envelope["algorithm"] == envelope_algorithm
    assert envelope["metadata"]["algorithm"] == algorithm
    assert (len(envelope["state_data"]["domains"]) > 0) is has_domains
    assert envelope["metadata"].get("clues") == CLUES


@pytest.mark.slow
@pytest.mark.parametrize("algorithm", ["trie", "repair", "beam"])
def test_paused_grid_file_carries_clues(paused_fill, algorithm):
    paused = paused_fill(algorithm)

    assert json.loads(paused.paused_grid_file.read_text()).get("clues") == CLUES


@pytest.mark.slow
def test_csp_pause_in_human_mode_writes_the_clues_back_into_the_input(tmp_path):
    paused = pause_real_fill(tmp_path, "trie", human_mode=True)

    data = json.loads(paused.grid_file.read_text())
    assert any(cell != "." for row in data["grid"] for cell in row), "input file was not rewritten"
    assert data.get("clues") == CLUES
    assert read_envelope(paused.state_file)["metadata"].get("clues") == CLUES


# --- real fill -> pause -> resume --------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize("algorithm", ["trie", "repair", "beam"])
def test_resume_command_writes_the_clues_of_the_paused_fill(paused_fill, tmp_path, algorithm):
    paused = paused_fill(algorithm)
    out_file = tmp_path / "resumed.json"

    proc = run_cli(resume_cmd(paused, out_file, extra=["-t", RESUME_TIMEOUT]))

    assert proc.returncode == 0, diag(proc)
    assert json.loads(out_file.read_text()).get("clues") == CLUES
    assert read_envelope(paused.state_file)["metadata"].get("clues") == CLUES


@pytest.mark.slow
@pytest.mark.parametrize("algorithm", ["trie", "repair", "beam"])
def test_fill_resume_writes_the_clues_of_the_paused_fill(paused_fill, tmp_path, algorithm):
    paused = paused_fill(algorithm)
    out_file = tmp_path / "resumed.json"

    proc = run_cli(fill_resume_cmd(paused, out_file, extra=["-t", RESUME_TIMEOUT]))

    assert proc.returncode == 0, diag(proc)
    assert json.loads(out_file.read_text()).get("clues") == CLUES
    assert read_envelope(paused.state_file)["metadata"].get("clues") == CLUES


@pytest.mark.slow
def test_fill_resume_ignores_the_clues_of_a_given_grid_file(paused_fill, tmp_path):
    # Spec 3.5: with --resume a grid file's clues are not read; the saved state is
    # authoritative.
    paused = paused_fill("trie")
    other_grid = write_grid(tmp_path / "other.json", "trie", clues=OTHER_CLUES)
    out_file = tmp_path / "resumed.json"

    proc = run_cli(fill_resume_cmd(paused, out_file, grid_file=other_grid, extra=["-t", RESUME_TIMEOUT]))

    assert proc.returncode == 0, diag(proc)
    assert json.loads(out_file.read_text()).get("clues") == CLUES
    assert read_envelope(paused.state_file)["metadata"].get("clues") == CLUES


# --- a resumed run that pauses again keeps the clues -------------------------


@pytest.mark.slow
def test_resume_command_pausing_again_saves_a_state_with_the_clues(paused_fill, tmp_path):
    paused = paused_fill("trie")
    state_dir = copy_state_dir(paused, tmp_path)
    flags_dir = tmp_path / "flags"
    out_file = tmp_path / "resumed.json"
    cmd = [
        sys.executable,
        "-m",
        "cli.src.cli",
        *resume_cmd(paused, out_file, state_dir=state_dir, flags_dir=flags_dir, extra=["-t", "120"]),
    ]
    before = (state_dir / f"{TASK_ID}.json.gz").stat().st_mtime_ns

    proc, stdout, stderr = run_until_paused(cmd, flags_dir, TASK_ID, "sleep")

    assert proc.returncode == 0, f"stderr tail:\n{stderr[-800:]}\nstdout tail:\n{stdout[-400:]}"
    assert json.loads(stdout.strip().splitlines()[-1])["paused"] is True, stdout[-400:]
    new_state = state_dir / f"{TASK_ID}.json.gz"
    assert new_state.stat().st_mtime_ns != before, "the resumed run did not save a new pause state"
    assert json.loads(out_file.read_text()).get("clues") == CLUES
    assert read_envelope(new_state)["metadata"].get("clues") == CLUES


@pytest.mark.slow
def test_fill_resume_pausing_again_saves_a_state_with_the_clues(paused_fill, tmp_path):
    # repair: its paused-again state is written by the CLI's degenerate save, the
    # other save site a resumed run reaches.
    paused = paused_fill("repair")
    state_dir = copy_state_dir(paused, tmp_path)
    flags_dir = tmp_path / "flags"
    out_file = tmp_path / "resumed.json"
    cmd = [
        sys.executable,
        "-m",
        "cli.src.cli",
        *fill_resume_cmd(paused, out_file, state_dir=state_dir, flags_dir=flags_dir, extra=["-t", "120"]),
    ]
    before = (state_dir / f"{TASK_ID}.json.gz").stat().st_mtime_ns

    proc, stdout, stderr = run_until_paused(cmd, flags_dir, TASK_ID, "immediate")

    assert proc.returncode == 0, f"stderr tail:\n{stderr[-800:]}\nstdout tail:\n{stdout[-400:]}"
    assert json.loads(stdout.strip().splitlines()[-1])["paused"] is True, stdout[-400:]
    new_state = state_dir / f"{TASK_ID}.json.gz"
    assert new_state.stat().st_mtime_ns != before, "the resumed run did not save a new pause state"
    assert json.loads(out_file.read_text()).get("clues") == CLUES
    assert read_envelope(new_state)["metadata"].get("clues") == CLUES


# --- hand-built states: the load side, fast ----------------------------------

SMALL_TASK = "small_task"


def full_grid():
    """An 11x11 grid with no empty slot, so a resume returns without searching."""
    grid = Grid(11)
    for row in range(11):
        grid.place_word("A" * 11, row, 0, "across")
    return grid


def two_block_grid():
    """An 11x11 grid whose only open cells are two 3x3 corner blocks.

    A resume solves it in well under a second, so the resumed file is a real
    result write. Black squares are symmetric, so the grid is a legal pattern.
    """
    open_cells = {(r, c) for r in range(3) for c in range(3)} | {(r, c) for r in range(8, 11) for c in range(8, 11)}
    return Grid.from_dict({"size": 11, "grid": [["." if (r, c) in open_cells else "#" for c in range(11)] for r in range(11)]})


def save_small_csp_state(state_dir, **extra_metadata):
    """A degenerate CSP-type state (empty domains) on the two-block grid."""
    state = CSPState(
        grid_dict=two_block_grid().to_dict(),
        domains={},
        constraints={},
        used_words=[],
        slot_id_map={},
        slot_list=[],
        slots_sorted=[],
        current_slot_index=0,
        iteration_count=0,
        locked_slots=[],
        timestamp=datetime.now().isoformat(),
    )
    metadata = {"algorithm": "repair", "wordlists": [str(WORDLIST)], "slots_filled": 0, "total_slots": 12}
    metadata.update(extra_metadata)
    return StateManager(storage_dir=state_dir).save_csp_state(
        task_id=SMALL_TASK, csp_state=state, metadata=metadata, compress=True
    )


def save_small_beam_state(state_dir, **extra_metadata):
    """A beam-type state holding a completed grid, so the resume returns at once."""
    beam = BeamState(grid=full_grid(), slots_filled=0, total_slots=0, score=50.0)
    state = BeamSearchState(
        beam=[StateManager.serialize_beam_state(beam)],
        filled_slots=[],
        slot_idx=0,
        iterations=1,
        slot_attempt_history={},
        recently_failed=[],
        beam_width=1,
        candidates_per_slot=10,
        min_score=0,
        diversity_bonus=0.1,
        theme_entries={},
        all_slots=[],
        total_slots=0,
        timestamp=datetime.now().isoformat(),
    )
    metadata = {"algorithm": "beam", "wordlists": [str(WORDLIST)], "slots_filled": 0, "total_slots": 0}
    metadata.update(extra_metadata)
    return StateManager(storage_dir=state_dir).save_beam_search_state(
        task_id=SMALL_TASK, beam_state=state, metadata=metadata, compress=True
    )


class SmallState:
    def __init__(self, tmp_path):
        self.state_dir = tmp_path / "state"
        self.flags_dir = tmp_path / "flags"
        self.out_file = tmp_path / "resumed.json"

    def resume_args(self, state_file):
        return [
            "resume",
            str(state_file),
            "--state-dir",
            str(self.state_dir),
            "--pause-flag-dir",
            str(self.flags_dir),
            "-o",
            str(self.out_file),
            "-t",
            "60",
            "--json-output",
        ]

    def fill_resume_args(self, state_file, grid_file=None):
        return [
            "fill",
            *([str(grid_file)] if grid_file else []),
            "--resume",
            str(state_file),
            "--state-dir",
            str(self.state_dir),
            "--pause-flag-dir",
            str(self.flags_dir),
            "-o",
            str(self.out_file),
            "-t",
            "60",
            "--json-output",
        ]


def assert_resumed_grid(data):
    """The file is a result write: no open cell is left empty."""
    assert "." not in [cell for row in data["grid"] for cell in row], data["grid"]


def test_resume_command_reads_clues_from_a_csp_state_metadata(tmp_path):
    small = SmallState(tmp_path)
    state_file = save_small_csp_state(small.state_dir, clues=CLUES)

    proc = run_cli(small.resume_args(state_file))

    assert proc.returncode == 0, diag(proc)
    data = json.loads(small.out_file.read_text())
    assert_resumed_grid(data)
    assert data.get("clues") == CLUES


def test_fill_resume_reads_clues_from_a_csp_state_metadata(tmp_path):
    small = SmallState(tmp_path)
    state_file = save_small_csp_state(small.state_dir, clues=CLUES)

    proc = run_cli(small.fill_resume_args(state_file))

    assert proc.returncode == 0, diag(proc)
    data = json.loads(small.out_file.read_text())
    assert_resumed_grid(data)
    assert data.get("clues") == CLUES


def test_resume_command_reads_clues_from_a_beam_type_state_metadata(tmp_path):
    small = SmallState(tmp_path)
    state_file = save_small_beam_state(small.state_dir, clues=CLUES)
    assert read_envelope(state_file)["algorithm"] == "beam"  # the fixture is beam-type

    proc = run_cli(small.resume_args(state_file))

    assert proc.returncode == 0, diag(proc)
    data = json.loads(small.out_file.read_text())
    assert_resumed_grid(data)
    assert data.get("clues") == CLUES


def test_fill_resume_given_a_grid_file_with_other_clues_writes_the_states_clues(tmp_path):
    small = SmallState(tmp_path)
    state_file = save_small_csp_state(small.state_dir, clues=CLUES)
    other_grid = tmp_path / "other.json"
    other_grid.write_text(json.dumps({"size": 11, "grid": two_block_grid().to_dict()["grid"], "clues": OTHER_CLUES}))

    proc = run_cli(small.fill_resume_args(state_file, grid_file=other_grid))

    assert proc.returncode == 0, diag(proc)
    data = json.loads(small.out_file.read_text())
    assert_resumed_grid(data)
    assert data.get("clues") == CLUES


def test_fill_resume_with_a_grid_file_but_a_state_without_clues_writes_no_clues(tmp_path):
    # The grid file's clues are not read, so they cannot stand in for a missing
    # state value either.
    small = SmallState(tmp_path)
    state_file = save_small_csp_state(small.state_dir)
    other_grid = tmp_path / "other.json"
    other_grid.write_text(json.dumps({"size": 11, "grid": two_block_grid().to_dict()["grid"], "clues": OTHER_CLUES}))

    proc = run_cli(small.fill_resume_args(state_file, grid_file=other_grid))

    assert proc.returncode == 0, diag(proc)
    data = json.loads(small.out_file.read_text())
    assert_resumed_grid(data)
    assert "clues" not in data


@pytest.mark.parametrize("command", ["resume", "fill --resume"])
def test_csp_state_without_clues_gives_resumed_output_without_a_clues_key(tmp_path, command):
    small = SmallState(tmp_path)
    state_file = save_small_csp_state(small.state_dir)
    assert "clues" not in read_envelope(state_file)["metadata"]
    args = small.resume_args(state_file) if command == "resume" else small.fill_resume_args(state_file)

    proc = run_cli(args)

    assert proc.returncode == 0, diag(proc)
    data = json.loads(small.out_file.read_text())
    assert_resumed_grid(data)
    assert "clues" not in data


def test_beam_type_state_without_clues_gives_resumed_output_without_a_clues_key(tmp_path):
    small = SmallState(tmp_path)
    state_file = save_small_beam_state(small.state_dir)
    assert "clues" not in read_envelope(state_file)["metadata"]

    proc = run_cli(small.resume_args(state_file))

    assert proc.returncode == 0, diag(proc)
    data = json.loads(small.out_file.read_text())
    assert_resumed_grid(data)
    assert "clues" not in data


# --- "clues": null is a present value and is carried unchanged ---------------
#
# Controller ruling 2026-10-31: spec 3.5 has fill carry the input's `clues`
# "unchanged", and `fill` is not a validator, so null is carried like any value.
# The sentinel makes a dropped key fail on the assertion's own line.


def assert_null_carried(container, what):
    assert container.get("clues", "ABSENT") is None, f"{what}: clues was not carried as null"


@pytest.mark.slow
def test_null_clues_survive_the_csp_engines_pause_state_and_resume(tmp_path):
    paused = pause_real_fill(tmp_path, "trie", clues=None)
    assert json.loads(paused.grid_file.read_text())["clues"] is None  # the input does hold null
    out_file = tmp_path / "resumed.json"

    assert_null_carried(read_envelope(paused.state_file)["metadata"], "pause state metadata")

    proc = run_cli(resume_cmd(paused, out_file, extra=["-t", RESUME_TIMEOUT]))

    assert proc.returncode == 0, diag(proc)
    assert_null_carried(json.loads(out_file.read_text()), "resumed output")


@pytest.mark.slow
def test_a_resumed_null_state_that_pauses_again_keeps_the_null(paused_fill, tmp_path):
    # The first state is the real CSP pause with its metadata["clues"] rewritten to
    # null, so this row does not depend on the first pause carrying null.
    paused = paused_fill("trie")
    state_dir = copy_state_dir(paused, tmp_path)
    state_file = state_dir / f"{TASK_ID}.json.gz"
    envelope = read_envelope(state_file)
    envelope["metadata"]["clues"] = None
    with gzip.open(state_file, "wt", encoding="utf-8") as f:
        json.dump(envelope, f)
    assert_null_carried(read_envelope(state_file)["metadata"], "rewritten state")
    flags_dir = tmp_path / "flags"
    out_file = tmp_path / "resumed.json"
    # resume_cmd names paused.state_file, the original; point it at the rewritten copy.
    args = resume_cmd(paused, out_file, state_dir=state_dir, flags_dir=flags_dir, extra=["-t", "120"])
    args[1] = str(state_file)
    cmd = [sys.executable, "-m", "cli.src.cli", *args]
    before = state_file.stat().st_mtime_ns

    proc, stdout, stderr = run_until_paused(cmd, flags_dir, TASK_ID, "sleep")

    assert proc.returncode == 0, f"stderr tail:\n{stderr[-800:]}\nstdout tail:\n{stdout[-400:]}"
    assert json.loads(stdout.strip().splitlines()[-1])["paused"] is True, stdout[-400:]
    assert state_file.stat().st_mtime_ns != before, "the resumed run did not save a new pause state"
    assert_null_carried(json.loads(out_file.read_text()), "paused-again output")
    assert_null_carried(read_envelope(state_file)["metadata"], "paused-again state metadata")
