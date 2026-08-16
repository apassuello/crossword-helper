"""
Regression tests for the pause/resume subsystem and fill algorithm bugs.

Covers:
- Autofill._handle_pause crashing with a TypeError (keyword mismatch with
  StateManager.capture_csp_state) so no state file was ever written on pause
- slots_sorted serialized as slot dicts but used as list indices on restore
- `resume` unable to load a real .json.gz state file by path (utf-8 error)
- `resume` silently loading a stored task id while ignoring the content of
  the file actually passed
- `resume` running with an empty wordlist (wordlists now stored in the state)
- `resume` defaulting to hybrid (with its t>=30 restriction) instead of the
  algorithm recorded in the state
- `pause` reporting success for tasks that are not running
- `fill -a regex` crashing with TypeError (max_results=None)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from cli.src.core.grid import Grid
from cli.src.fill.autofill import Autofill
from cli.src.fill.pattern_matcher import PatternMatcher
from cli.src.fill.pause_controller import PauseController
from cli.src.fill.state_manager import CSPState, StateManager
from cli.src.fill.word_list import WordList

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_cli(args, cwd=None, timeout=120):
    """Run a CLI command and return (stdout, stderr, returncode)."""
    if cwd is None:
        cwd = PROJECT_ROOT
    cmd = [sys.executable, "-m", "cli.src.cli"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    return result.stdout, result.stderr, result.returncode


@pytest.fixture
def temp_dir():
    path = Path(tempfile.mkdtemp())
    yield path
    if path.exists():
        shutil.rmtree(path)


@pytest.fixture
def small_words():
    return [
        "CAT",
        "COT",
        "CUT",
        "DOG",
        "EAT",
        "TEA",
        "ATE",
        "TAE",
        "OAT",
        "TOT",
        "TAT",
        "ACT",
        "TAB",
        "BAT",
        "CAB",
        "ABC",
    ]


@pytest.fixture
def wordlist_file(temp_dir, small_words):
    path = temp_dir / "words.txt"
    path.write_text("\n".join(small_words) + "\n")
    return str(path)


def _make_autofill_with_csp(temp_dir, small_words):
    """Build an Autofill on an 11x11 grid with an initialized CSP."""
    grid = Grid(11)
    word_list = WordList(small_words)
    state_manager = StateManager(storage_dir=temp_dir / "states")
    pause_controller = PauseController(task_id="regress", pause_dir=temp_dir)
    autofill = Autofill(
        grid,
        word_list,
        None,
        60,
        0,
        "trie",
        None,
        pause_controller=pause_controller,
        state_manager=state_manager,
    )
    slots = grid.get_empty_slots()
    autofill._initialize_csp(slots)
    autofill.slots_sorted = autofill._sort_slots_by_constraint(slots)
    return autofill, state_manager, len(slots)


class TestPauseStateSaving:
    """Regression: pausing crashed with TypeError and never saved a state."""

    def test_handle_pause_writes_state_file(self, temp_dir, small_words):
        autofill, state_manager, total = _make_autofill_with_csp(temp_dir, small_words)
        autofill.wordlist_paths = ["some/wordlist.txt"]

        # Old code: TypeError: capture_csp_state() got an unexpected keyword
        # argument 'current_index' — and no state file was ever written
        autofill._handle_pause(2, "regress", total)

        state_path = Path(autofill.paused_state_path)
        assert state_path.exists()
        assert state_path.name == "regress.json.gz"

        # State must round-trip and record the wordlists for resume
        csp_state, metadata = state_manager.load_csp_state("regress")
        assert metadata["wordlists"] == ["some/wordlist.txt"]
        assert metadata["algorithm"] == "trie"
        assert csp_state.current_slot_index == 2

    def test_handle_pause_consumes_pause_flag(self, temp_dir, small_words):
        autofill, _, total = _make_autofill_with_csp(temp_dir, small_words)
        autofill.pause_controller.request_pause()
        assert autofill.pause_controller.is_paused()

        autofill._handle_pause(0, "regress", total)

        # The flag is consumed so it cannot pause a future run
        assert not autofill.pause_controller.is_paused()


class TestSlotsSortedSerialization:
    """Regression: slots_sorted saved as dicts but indexed as ints on restore."""

    def test_capture_converts_slot_dicts_to_ids(self, temp_dir, small_words):
        autofill, _, _ = _make_autofill_with_csp(temp_dir, small_words)

        # Autofill stores slots_sorted as a list of slot DICTS
        assert all(isinstance(s, dict) for s in autofill.slots_sorted)

        csp_state = StateManager.capture_csp_state(autofill, 0, set())

        # Serialized form must be slot IDs (ints) — resume indexes by them
        assert all(isinstance(i, int) for i in csp_state.slots_sorted)
        assert len(csp_state.slots_sorted) == len(autofill.slots_sorted)

    def test_restore_always_sets_slots_sorted(self, temp_dir, small_words):
        autofill, _, _ = _make_autofill_with_csp(temp_dir, small_words)
        csp_state = StateManager.capture_csp_state(autofill, 0, set())

        fresh = Autofill(Grid(11), WordList(small_words), None, 60, 0, "trie", None)
        # Old code: `if not hasattr(...)` never fired because __init__ sets
        # slots_sorted = [], so the saved ordering was silently dropped
        StateManager.restore_to_autofill(fresh, csp_state)
        assert fresh.slots_sorted == csp_state.slots_sorted

    def test_resume_fill_does_not_crash_on_restored_state(self, temp_dir, small_words):
        autofill, _, _ = _make_autofill_with_csp(temp_dir, small_words)
        csp_state = StateManager.capture_csp_state(autofill, 0, set())

        fresh = Autofill(Grid(11), WordList(small_words), None, 5, 0, "trie", None)
        # Old code: TypeError: list indices must be integers or slices, not dict
        result = fresh.fill(timeout=5, resume_state=csp_state)
        assert result is not None
        assert result.total_slots > 0


class TestStateFileLoading:
    """Regression: resume could not open its own .json.gz files by path."""

    def _write_state(self, state_manager, task_id, metadata=None, grid=None):
        if grid is None:
            grid = Grid(11)
            # Fill the whole grid so a resumed fill completes instantly
            for row in range(11):
                grid.place_word("A" * 11, row, 0, "across")
        csp_state = CSPState(
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
        )
        return state_manager.save_csp_state(
            task_id=task_id,
            csp_state=csp_state,
            metadata=metadata or {},
            compress=True,
        )

    def test_load_state_file_by_path_handles_gzip(self, temp_dir):
        sm = StateManager(storage_dir=temp_dir)
        path = self._write_state(sm, "gziptask", metadata={"algorithm": "trie"})

        # Old code derived task id 'gziptask.json' from the stem, missed the
        # lookup, and read the gzip file as utf-8 text
        algorithm, state, metadata, task_id = sm.load_state_file(path)
        assert algorithm == "csp"
        assert task_id == "gziptask"
        assert metadata["algorithm"] == "trie"
        assert state.grid_dict["size"] == 11

    def test_read_state_data_rejects_non_state_file(self, temp_dir):
        sm = StateManager(storage_dir=temp_dir)
        junk = temp_dir / "junk.json.gz"
        junk.write_text("IGNORED CONTENT")
        with pytest.raises(ValueError, match="Not a valid autofill state file"):
            sm.read_state_data(junk)

    def test_read_state_data_rejects_json_without_state_fields(self, temp_dir):
        sm = StateManager(storage_dir=temp_dir)
        not_a_state = temp_dir / "grid.json"
        not_a_state.write_text(json.dumps({"size": 11, "grid": []}))
        with pytest.raises(ValueError, match="Not a valid autofill state file"):
            sm.read_state_data(not_a_state)


class TestResumeCommand:
    """CLI-level resume regressions (uses the real /tmp/crossword_states dir)."""

    @pytest.fixture
    def stored_state(self, wordlist_file):
        """A complete-grid CSP state stored under a unique task id."""
        task_id = f"regress_{uuid.uuid4().hex[:10]}"
        sm = StateManager()  # Default dir — what the CLI resume command uses
        grid = Grid(11)
        for row in range(11):
            grid.place_word("A" * 11, row, 0, "across")
        csp_state = CSPState(
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
        )
        path = sm.save_csp_state(
            task_id=task_id,
            csp_state=csp_state,
            metadata={
                "algorithm": "trie",
                "wordlists": [wordlist_file],
                "slots_filled": 0,
                "total_slots": 0,
            },
            compress=True,
        )
        yield task_id, str(path)
        sm.delete_state(task_id)

    def test_resume_real_gz_path(self, stored_state, temp_dir):
        """Passing the actual .json.gz path must load THAT file (old: utf-8 error)."""
        task_id, path = stored_state
        out = temp_dir / "out.json"
        stdout, stderr, code = run_cli(["resume", path, "-t", "20", "-o", str(out), "--json-output"])
        assert code == 0, stderr
        result = json.loads(stdout.splitlines()[-1])
        assert result["success"] is True
        assert result["task_id"] == task_id
        assert out.exists()

    def test_resume_bare_task_id(self, stored_state, temp_dir):
        task_id, _ = stored_state
        out = temp_dir / "out.json"
        stdout, stderr, code = run_cli(["resume", task_id, "-t", "20", "-o", str(out), "--json-output"])
        assert code == 0, stderr
        result = json.loads(stdout.splitlines()[-1])
        assert result["success"] is True

    def test_fill_resume_bare_task_id_without_wordlists(self, stored_state, temp_dir):
        """`fill --resume` accepts a bare task id AND falls back to the state's wordlists.

        Approved decision 3 plus the obligation main's --wordlists help documents
        ("Required unless --resume is used with a state that recorded its wordlists").
        Part G dropped `fill`'s delegation to _execute_resume, so `fill --resume` now
        resolves the argument itself; every other test in this file exercises the
        `resume` command instead, which still goes through _execute_resume.

        -a is passed explicitly: `fill`'s Click default is `repair`, not the state's
        recorded algorithm (see CLI_SPEC.md's NOTE).
        """
        task_id, _ = stored_state
        out = temp_dir / "out.json"
        stdout, stderr, code = run_cli(
            ["fill", "--resume", task_id, "-a", "trie", "-t", "20", "-o", str(out), "--json-output"]
        )
        assert code == 0, stderr
        result = json.loads(stdout.splitlines()[-1])
        # Bare id resolved against the state dir (not treated as a cwd-relative path),
        # and adopted as the run's task id so the resumed run stays pausable
        assert result["task_id"] == task_id
        # Wordlists came from the saved state, with no -w on the command line
        assert result["wordlists"], "wordlists should fall back to the saved state"
        assert result["wordlists"][0].endswith("words.txt")

    def test_fill_resume_unknown_task_id_errors_cleanly(self, temp_dir):
        """An unresolvable --resume value must be a clean CLI error, not a traceback."""
        out = temp_dir / "out.json"
        stdout, stderr, code = run_cli(
            ["fill", "--resume", "no_such_task_xyz", "-a", "trie", "-t", "20", "-o", str(out), "--json-output"]
        )
        assert code == 1
        payload = json.loads(stdout.splitlines()[-1])
        assert payload["success"] is False
        assert "neither an existing state file nor a known" in payload["error"]

    def test_resume_uses_wordlists_from_state(self, stored_state, temp_dir):
        """No -w given: the wordlists recorded in the state must be used."""
        task_id, _ = stored_state
        out = temp_dir / "out.json"
        stdout, stderr, code = run_cli(["resume", task_id, "-t", "20", "-o", str(out), "--json-output"])
        assert code == 0, stderr
        result = json.loads(stdout.splitlines()[-1])
        assert result["wordlists"], "wordlists from state should be reported"
        assert result["wordlists"][0].endswith("words.txt")

    def test_resume_algorithm_defaults_from_state_not_hybrid(self, stored_state, temp_dir):
        """-t 20 with a trie state must work (old default hybrid demanded t>=30)."""
        task_id, _ = stored_state
        out = temp_dir / "out.json"
        stdout, stderr, code = run_cli(["resume", task_id, "-t", "20", "-o", str(out), "--json-output"])
        assert code == 0, stderr
        result = json.loads(stdout.splitlines()[-1])
        assert result["algorithm"] == "trie"

    def test_resume_garbage_file_matching_task_id_errors(self, stored_state, temp_dir):
        """A real file whose NAME matches a stored task id must NOT silently
        load the stored state — the passed file's content wins (and errors)."""
        task_id, _ = stored_state
        decoy = temp_dir / f"{task_id}.json"
        decoy.write_text("IGNORED CONTENT")
        stdout, stderr, code = run_cli(["resume", str(decoy), "-t", "20", "--json-output"])
        assert code == 1
        result = json.loads(stdout.splitlines()[-1])
        assert result["success"] is False
        assert "Not a valid autofill state file" in result["error"]

    def test_resume_unknown_task_id_errors(self):
        stdout, stderr, code = run_cli(["resume", "definitely_not_a_task_xyz", "-t", "20", "--json-output"])
        assert code == 1
        result = json.loads(stdout.splitlines()[-1])
        assert result["success"] is False
        assert "neither an existing state file nor a known task id" in result["error"]

    def test_resume_without_wordlists_anywhere_errors(self, temp_dir):
        """State without recorded wordlists + no -w must be a clear error."""
        task_id = f"regress_{uuid.uuid4().hex[:10]}"
        sm = StateManager()
        grid = Grid(11)
        csp_state = CSPState(
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
        )
        sm.save_csp_state(task_id=task_id, csp_state=csp_state, metadata={"algorithm": "trie"}, compress=True)
        try:
            stdout, stderr, code = run_cli(["resume", task_id, "-t", "20", "--json-output"])
            assert code == 1
            result = json.loads(stdout.splitlines()[-1])
            assert result["success"] is False
            assert "No wordlists available" in result["error"]
        finally:
            sm.delete_state(task_id)


class TestPauseCommand:
    """Regression: pause reported success for tasks that are not running."""

    def test_pause_nonexistent_task_fails(self):
        task_id = f"ghost_{uuid.uuid4().hex[:10]}"
        stdout, stderr, code = run_cli(["pause", task_id, "--json-output"])
        assert code == 1
        result = json.loads(stdout.splitlines()[-1])
        assert result["success"] is False
        assert "not running" in result["error"]
        # No orphaned flag file left behind
        assert not Path(f"/tmp/crossword_pause_{task_id}.flag").exists()

    def test_pause_running_task_succeeds(self, temp_dir):
        """A live pid marker makes pause succeed and write the flag."""
        task_id = f"live_{uuid.uuid4().hex[:10]}"
        controller = PauseController(task_id=task_id)
        controller.mark_running()  # This test process is 'the fill'
        try:
            stdout, stderr, code = run_cli(["pause", task_id, "--json-output"])
            assert code == 0
            result = json.loads(stdout.splitlines()[-1])
            assert result["success"] is True
            assert controller.is_paused()
        finally:
            controller.clear_pause()
            controller.clear_running()

    def test_is_task_running_cleans_stale_pid(self, temp_dir):
        controller = PauseController(task_id="stalepid", pause_dir=temp_dir)
        controller.running_file.write_text("999999999")  # Dead pid
        assert controller.is_task_running() is False
        assert not controller.running_file.exists()  # Stale marker cleaned


class TestRegexAlgorithm:
    """Regression: fill -a regex crashed with TypeError (max_results=None)."""

    def test_pattern_matcher_accepts_none_max_results(self, small_words):
        matcher = PatternMatcher(WordList(small_words))
        # Old code: TypeError: '>=' not supported between int and NoneType
        matches = matcher.find("C?T", min_score=0, max_results=None)
        assert {w for w, _ in matches} == {"CAT", "COT", "CUT"}

    def test_regex_autofill_initializes_domains(self, small_words):
        """The CSP init path passes max_results=None to the regex matcher."""
        grid = Grid(11)
        autofill = Autofill(Grid(11), WordList(small_words), None, 5, 0, "regex", None)
        slots = grid.get_empty_slots()
        autofill._initialize_csp(slots)  # Old code crashed here
        assert autofill.domains


class TestFillCommandContract:
    """fill command contract used by the backend (task-id / resume flags)."""

    def test_fill_help_lists_task_id_and_resume(self):
        stdout, stderr, code = run_cli(["fill", "--help"])
        assert code == 0
        assert "--task-id" in stdout
        assert "--resume" in stdout

    def test_fill_requires_grid_or_resume(self):
        stdout, stderr, code = run_cli(["fill", "-w", "nowhere.txt", "--json-output"])
        assert code == 1
        result = json.loads(stdout.splitlines()[-1])
        assert "GRID_FILE" in result["error"]

    def test_fill_requires_wordlists_without_resume(self, temp_dir):
        grid_path = temp_dir / "g.json"
        grid_path.write_text(json.dumps(Grid(11).to_dict()))
        stdout, stderr, code = run_cli(["fill", str(grid_path), "--json-output"])
        assert code == 1
        result = json.loads(stdout.splitlines()[-1])
        assert "wordlist" in result["error"].lower()
