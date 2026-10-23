"""Unit tests for the fill CLI command's process-level contract.

These tests pin the exit-code contract, which the backend depends on:
backend/core/cli_adapter.py raises CalledProcessError on any non-zero exit
(cli_adapter.py:80), so what fill exits with decides whether a legitimate
partial fill reaches the UI as a result or as an error.

Contract, deliberate:
- exit 0 - the solver ran and produced a result, INCLUDING a partial or
  unsuccessful fill. The JSON `success` field is the outcome signal, not the
  exit code.
- exit 1 - the run could not happen or could not finish: bad arguments,
  missing files, invalid theme entries, an out-of-range timeout.

A caller must never infer fill quality from the exit code.
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_fill(args, cwd=None):
    """Helper: run the fill CLI command and return (stdout, stderr, returncode)."""
    if cwd is None:
        cwd = PROJECT_ROOT
    cmd = [sys.executable, "-m", "cli.src.cli", "fill"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120)
    return result.stdout, result.stderr, result.returncode


def last_json(stdout):
    """Extract the final JSON object from stdout, which is mixed with progress lines."""
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


@pytest.fixture
def small_grid():
    """5x5 grid with symmetric black squares; every slot is 3-5 cells."""
    grid_data = {
        "size": 5,
        "grid": [
            [".", ".", ".", "#", "#"],
            [".", ".", ".", ".", "."],
            [".", ".", ".", ".", "."],
            ["#", ".", ".", ".", "."],
            ["#", "#", ".", ".", "."],
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(grid_data, f)
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def tiny_wordlist():
    """Too few words to fill the grid, so the fill completes but does not succeed."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("CAT\nDOG\nEMU\nABCDE\nFGHIJ\n")
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestFillExitCodes:
    """The process-level contract the backend adapter reads."""

    def test_timeout_below_floor_is_a_clean_error_not_a_traceback(self, small_grid, tiny_wordlist):
        """A -t below the repair algorithm's floor must fail like a CLI, not crash.

        iterative_repair.fill() enforces a 10-second floor with a raw `raise`.
        Uncaught, that reaches the user as a Python traceback.
        """
        stdout, stderr, rc = run_fill([small_grid, "-w", tiny_wordlist, "-t", "5", "--allow-nonstandard"])

        assert rc == 1, f"expected exit 1 for an out-of-range timeout, got {rc}"
        assert "Traceback" not in stderr, f"raw traceback leaked to the user:\n{stderr[-600:]}"
        combined = stdout + stderr
        assert "timeout" in combined.lower(), "the error should name the offending option"

    def test_timeout_below_floor_emits_json_error_when_json_output(self, small_grid, tiny_wordlist):
        """With --json-output the same failure must still be machine-readable."""
        stdout, stderr, rc = run_fill([small_grid, "-w", tiny_wordlist, "-t", "5", "--allow-nonstandard", "--json-output"])

        assert rc == 1
        assert "Traceback" not in stderr
        payload = last_json(stdout)
        assert payload is not None, f"no JSON on stdout; stderr was:\n{stderr[-400:]}"
        assert payload.get("success") is False
        assert "error" in payload

    def test_unsuccessful_fill_still_exits_zero(self, small_grid, tiny_wordlist):
        """A completed-but-unsuccessful fill is a result, not an error.

        This is deliberate. The backend renders partial fills as a normal
        outcome, and cli_adapter.py:80 turns any non-zero exit into an
        exception, so exiting non-zero here would break that path.
        """
        stdout, stderr, rc = run_fill([small_grid, "-w", tiny_wordlist, "-t", "10", "--allow-nonstandard", "--json-output"])

        payload = last_json(stdout)
        assert payload is not None, f"no JSON on stdout; stderr was:\n{stderr[-400:]}"
        assert payload["success"] is False, "fixture should not be fillable with this wordlist"
        assert rc == 0, "a completed run exits 0 regardless of fill success"

    def test_missing_wordlist_exits_one(self, small_grid):
        """Preflight failures are genuine errors and exit non-zero."""
        stdout, stderr, rc = run_fill([small_grid, "-w", "does/not/exist.txt", "-t", "10", "--allow-nonstandard"])

        assert rc == 1
        assert "Traceback" not in stderr


class TestFillValidationSet:
    """`fill` validates entries against the lists it loaded, not every file on disk.

    IterativeRepair._is_valid_word returns False for every word when the set is
    empty, so the set must be non-empty whenever the loaded list is.
    """

    def test_set_contains_only_loaded_words(self):
        from cli.src.cli import _validation_words
        from cli.src.fill.word_list import WordList

        words = _validation_words(WordList(["CAT", "DOG", "EMU"]))
        assert words == {"CAT", "DOG", "EMU"}

    def test_word_only_in_raw_comprehensive_list_is_not_in_the_set(self):
        from cli.src.cli import _validation_words
        from cli.src.fill.word_list import WordList

        raw = os.path.join(PROJECT_ROOT, "data", "wordlists", "raw", "comprehensive_scored.txt")
        with open(raw) as f:
            raw_words = {line.split(";")[0].strip().upper() for line in f if line.strip() and not line.startswith("#")}
        only_in_raw = sorted(w for w in raw_words if w.isalpha() and 3 <= len(w) <= 21 and w not in {"CAT", "DOG"})
        assert only_in_raw, "fixture check: raw list must hold words beyond the tiny list"

        words = _validation_words(WordList(["CAT", "DOG"]))
        assert only_in_raw[0] not in words

    def test_set_is_non_empty_when_loaded_list_is_non_empty(self):
        from cli.src.cli import _validation_words
        from cli.src.fill.word_list import WordList

        word_list = WordList(["CAT"])
        assert len(word_list) > 0
        assert _validation_words(word_list)


class TestLoadersParseLines:
    """`fill` and `resume` load word-list lines with WordList.parse_line (spec 4, #51).

    One file, four lines, loaded through each command's own code path. The solver
    is aborted right after the list is built, so the loaded WordList is what is
    asserted on, not a helper called in isolation.
    """

    LINES = "APPLE;50\ngrape,40\nLEMON\nword,score\n"

    class _Abort(Exception):
        pass

    @pytest.fixture
    def wordlist_path(self, tmp_path):
        path = tmp_path / "mixed.txt"
        path.write_text(self.LINES)
        return str(path)

    @pytest.fixture
    def captured(self, monkeypatch):
        """Record every WordList the CLI builds and abort before any solving."""
        import cli.src.cli as cli_mod
        from cli.src.fill.word_list import WordList

        abort = self._Abort
        box = {"lists": [], "validation": None}

        class Recording(WordList):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                box["lists"].append(self)

        real_validation = cli_mod._validation_words

        def recording_validation(word_list):
            box["validation"] = real_validation(word_list)
            raise abort()

        monkeypatch.setattr(cli_mod, "WordList", Recording)
        monkeypatch.setattr(cli_mod, "_validation_words", recording_validation)
        return box

    @staticmethod
    def _scores(word_list):
        return {w.text: w.score for w in word_list.words}

    def _assert_normative_rows(self, word_list):
        from cli.src.fill.word_list import WordList

        scores = self._scores(word_list)
        assert set(scores) == {"APPLE", "GRAPE", "LEMON"}
        assert scores["APPLE"] == 50
        assert scores["GRAPE"] == 40
        assert scores["LEMON"] == WordList(["LEMON"]).words[0].score

    def test_fill_loads_scored_comma_and_header_lines(self, wordlist_path, captured, tmp_path):
        from click.testing import CliRunner

        from cli.src.cli import cli

        grid = tmp_path / "g.json"
        grid.write_text(json.dumps({"size": 11, "grid": [["."] * 11 for _ in range(11)]}))
        result = CliRunner().invoke(cli, ["fill", str(grid), "-w", wordlist_path, "-t", "20"])
        assert isinstance(result.exception, self._Abort), result.output
        assert len(captured["lists"]) == 1
        self._assert_normative_rows(captured["lists"][0])

    def test_fill_validation_set_holds_uppercased_word_texts(self, wordlist_path, captured, tmp_path):
        from click.testing import CliRunner

        from cli.src.cli import cli

        grid = tmp_path / "g.json"
        grid.write_text(json.dumps({"size": 11, "grid": [["."] * 11 for _ in range(11)]}))
        CliRunner().invoke(cli, ["fill", str(grid), "-w", wordlist_path, "-t", "20"])
        assert captured["validation"] == {"APPLE", "GRAPE", "LEMON"}
        assert "grape,40" not in captured["validation"]

    def test_resume_loads_scored_comma_and_header_lines(self, wordlist_path, captured, tmp_path, monkeypatch):
        from datetime import datetime

        from click.testing import CliRunner

        from cli.src.cli import cli
        from cli.src.core.grid import Grid
        from cli.src.fill.state_manager import CSPState, StateManager

        state_dir = tmp_path / "states"
        sm = StateManager(storage_dir=state_dir)
        state = CSPState(
            grid_dict=Grid(11).to_dict(),
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
            task_id="t6",
            csp_state=state,
            metadata={"algorithm": "trie", "wordlists": [], "slots_filled": 0, "total_slots": 0},
            compress=True,
        )

        # resume builds its matcher right after loading the list; stop there. The
        # command may swallow the exception, so assert on the captured list only.
        from cli.src.fill import trie_pattern_matcher

        def stop(*args, **kwargs):
            raise self._Abort()

        monkeypatch.setattr(trie_pattern_matcher, "TriePatternMatcher", stop)
        CliRunner().invoke(cli, ["resume", str(path), "-w", wordlist_path, "-t", "20", "--state-dir", str(state_dir)])
        assert len(captured["lists"]) == 1
        self._assert_normative_rows(captured["lists"][0])


# ---------------------------------------------------------------------------
# --lock-filled / --no-lock-filled and the grid file's "locked" key
# novice-readiness spec 0.2.4 §2.1 (C12)
# ---------------------------------------------------------------------------

L1_LINES = "CAT;50\nCOT;50\nCUT;50\nQUA;50\nXIS;50\n"


def _g33_with_locked(locked):
    return {
        "size": 3,
        "grid": [["C", ".", "."], [".", ".", "."], [".", ".", "."]],
        "locked": locked,
    }


@pytest.mark.parametrize(
    "locked, extra_flags",
    [
        ([[5, 5]], []),
        ([[2, 2]], []),
        ([[5, 5]], ["--no-lock-filled"]),
    ],
    ids=["out-of-bounds", "empty-cell", "out-of-bounds-no-lock-filled"],
)
def test_fill_invalid_locked_list_exits_1(tmp_path, locked, extra_flags):
    grid_path = tmp_path / "g33.json"
    grid_path.write_text(json.dumps(_g33_with_locked(locked)))
    words = tmp_path / "l1.txt"
    words.write_text(L1_LINES)
    stdout, stderr, code = run_fill([str(grid_path), "-w", str(words), "--allow-nonstandard", "--json-output"] + extra_flags)
    assert code == 1, (stdout, stderr)
    result = last_json(stdout)
    assert result is not None, (stdout, stderr)
    assert result["success"] is False
    assert "error" in result
    assert "blocked" not in result


def _paused_state_file(tmp_path):
    """A complete-grid CSP state file for `fill --resume`, plus a word list."""
    from datetime import datetime

    from cli.src.core.grid import Grid as _Grid
    from cli.src.fill.state_manager import CSPState, StateManager

    grid = _Grid(11)
    for row in range(11):
        grid.place_word("A" * 11, row, 0, "across")
    state = CSPState(
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
    sm = StateManager(storage_dir=tmp_path / "states")
    path = sm.save_csp_state(
        task_id="lockmode_resume",
        csp_state=state,
        metadata={"algorithm": "trie", "wordlists": [], "slots_filled": 0, "total_slots": 0},
        compress=True,
    )
    words = tmp_path / "words.txt"
    words.write_text(L1_LINES)
    return str(path), str(words)


def test_fill_resume_never_calls_apply_lock_mode(tmp_path, monkeypatch):
    """§2.1 last bullet: on --resume neither --lock-filled nor a "locked" key applies."""
    from click.testing import CliRunner

    import cli.src.cli as cli_module

    def _boom(*args, **kwargs):
        raise AssertionError("apply_lock_mode must not run on --resume")

    monkeypatch.setattr(cli_module, "apply_lock_mode", _boom)
    state_path, words = _paused_state_file(tmp_path)
    result = CliRunner().invoke(
        cli_module.cli,
        [
            "fill",
            "--resume",
            state_path,
            "-w",
            words,
            "-a",
            "trie",
            "-t",
            "20",
            "-o",
            str(tmp_path / "out.json"),
            "--json-output",
        ],
    )
    assert not isinstance(result.exception, AssertionError), result.output
    assert result.exit_code == 0, (result.output, result.exception)


def test_fill_fresh_run_calls_apply_lock_mode(tmp_path, monkeypatch):
    """Control for the --resume test: the spy does fire on the fresh branch."""
    from click.testing import CliRunner

    import cli.src.cli as cli_module

    calls = []
    real = cli_module.apply_lock_mode

    def _spy(grid, grid_data, lock_filled):
        calls.append(lock_filled)
        return real(grid, grid_data, lock_filled)

    monkeypatch.setattr(cli_module, "apply_lock_mode", _spy)
    grid_path = tmp_path / "g33.json"
    grid_path.write_text(json.dumps({"size": 3, "grid": [["C", ".", "."], [".", ".", "."], [".", ".", "."]]}))
    words = tmp_path / "l1.txt"
    words.write_text(L1_LINES)
    CliRunner().invoke(
        cli_module.cli,
        ["fill", str(grid_path), "-w", str(words), "--allow-nonstandard", "--no-lock-filled", "-t", "10", "--json-output"],
    )
    assert calls == [False]


# ---------------------------------------------------------------------------
# End-to-end postcondition: a changed locked letter writes nothing
# novice-readiness spec 0.2.4 §2.1 (D3)
# ---------------------------------------------------------------------------

L6_LINES = "CAT;50\nORE;50\nWED;50\nCOW;50\nARE;50\nTED;50\n"
POSTCONDITION_TEXT = "Autofill changed a locked letter; nothing was written."


def _stub_repair(monkeypatch, *, letter="D", paused=False, touch=None, cleanup_letter=None):
    """Replace the repair solver with one that returns a grid whose (0,0) is `letter`."""
    import cli.src.fill.iterative_repair as repair_module
    from cli.src.core.grid import Grid as _Grid
    from cli.src.fill.autofill import FillResult

    class _StubRepair:
        def __init__(self, grid, *args, **kwargs):
            self.grid = grid

        def cleanup_grid(self):
            out = _Grid(3, validate_size=False)
            out.set_letter(0, 0, cleanup_letter)
            return FillResult(
                success=True,
                grid=out,
                time_elapsed=0.1,
                slots_filled=6,
                total_slots=6,
                problematic_slots=[],
                iterations=1,
            )

        def fill(self, timeout=None):
            if touch is not None:
                touch()
            out = _Grid(3, validate_size=False)
            out.set_letter(0, 0, letter)
            return FillResult(
                success=True,
                grid=out,
                time_elapsed=0.1,
                slots_filled=6,
                total_slots=6,
                problematic_slots=[],
                iterations=1,
                paused=paused,
            )

    monkeypatch.setattr(repair_module, "IterativeRepair", _StubRepair)


def _g33_c_at_origin(tmp_path):
    grid_path = tmp_path / "g33.json"
    grid_path.write_text(json.dumps({"size": 3, "grid": [["C", ".", "."], [".", ".", "."], [".", ".", "."]]}))
    words = tmp_path / "l6.txt"
    words.write_text(L6_LINES)
    return grid_path, words


def test_pc6_changed_locked_letter_json_writes_nothing(tmp_path, monkeypatch):
    from click.testing import CliRunner

    import cli.src.cli as cli_module

    _stub_repair(monkeypatch)
    grid_path, words = _g33_c_at_origin(tmp_path)
    out = tmp_path / "out.json"
    result = CliRunner().invoke(
        cli_module.cli,
        ["fill", str(grid_path), "-w", str(words), "--allow-nonstandard", "-o", str(out), "--json-output"],
    )
    assert result.exit_code == 1, (result.output, result.exception)
    payload = last_json(result.output)
    assert payload is not None, result.output
    assert payload["success"] is False
    assert payload["error"] == POSTCONDITION_TEXT
    assert not out.exists()


def test_pc9_cleanup_changing_a_locked_letter_writes_nothing(tmp_path, monkeypatch):
    """Check (b): the solver keeps C at (0,0) so check (a) passes; only --cleanup changes it."""
    from click.testing import CliRunner

    import cli.src.cli as cli_module

    _stub_repair(monkeypatch, letter="C", cleanup_letter="D")
    grid_path, words = _g33_c_at_origin(tmp_path)
    out = tmp_path / "out.json"
    result = CliRunner().invoke(
        cli_module.cli,
        [
            "fill",
            str(grid_path),
            "-w",
            str(words),
            "--allow-nonstandard",
            "--cleanup",
            "--algorithm",
            "repair",
            "-o",
            str(out),
            "--json-output",
        ],
    )
    assert result.exit_code == 1, (result.output, result.exception)
    payload = last_json(result.output)
    assert payload is not None, result.output
    assert payload["error"] == POSTCONDITION_TEXT
    assert not out.exists()


def test_pc7_changed_locked_letter_human_leaves_input_bytes(tmp_path, monkeypatch):
    from click.testing import CliRunner

    import cli.src.cli as cli_module

    _stub_repair(monkeypatch)
    grid_path, words = _g33_c_at_origin(tmp_path)
    before = grid_path.read_bytes()
    result = CliRunner().invoke(cli_module.cli, ["fill", str(grid_path), "-w", str(words), "--allow-nonstandard"])
    assert result.exit_code == 1, (result.output, result.exception)
    assert grid_path.read_bytes() == before


def test_pc8_changed_locked_letter_on_paused_result_clears_markers(tmp_path, monkeypatch):
    from click.testing import CliRunner

    import cli.src.cli as cli_module

    state_dir = tmp_path / "states"
    flag_dir = tmp_path / "flags"
    flag_dir.mkdir()
    _stub_repair(monkeypatch, paused=True, touch=lambda: (flag_dir / "crossword_pause_t1.flag").touch())
    grid_path, words = _g33_c_at_origin(tmp_path)
    out = tmp_path / "out.json"
    result = CliRunner().invoke(
        cli_module.cli,
        [
            "fill",
            str(grid_path),
            "-w",
            str(words),
            "--allow-nonstandard",
            "-o",
            str(out),
            "--json-output",
            "--task-id",
            "t1",
            "--state-dir",
            str(state_dir),
            "--pause-flag-dir",
            str(flag_dir),
        ],
    )
    assert result.exit_code == 1, (result.output, result.exception)
    payload = last_json(result.output)
    assert payload is not None and payload.get("paused") is not True, result.output
    assert payload["error"] == POSTCONDITION_TEXT
    assert not out.exists()
    assert not state_dir.exists() or list(state_dir.iterdir()) == []
    assert not (flag_dir / "crossword_pause_t1.flag").exists()
    assert not (flag_dir / "crossword_running_t1.pid").exists()
    assert not (flag_dir / "crossword_searching_t1.flag").exists()


@pytest.mark.slow
@pytest.mark.parametrize(
    "extra, timeout",
    [
        (["--algorithm", "regex"], "10"),
        (["--algorithm", "trie"], "10"),
        (["--algorithm", "beam"], "10"),
        (["--algorithm", "repair"], "10"),
        (["--algorithm", "hybrid"], "30"),
        (["--adaptive"], "10"),
    ],
    ids=["regex", "trie", "beam", "repair", "hybrid", "adaptive"],
)
def test_pc9_subprocess_keeps_locked_letter(tmp_path, extra, timeout):
    grid_path, words = _g33_c_at_origin(tmp_path)
    stdout, stderr, code = run_fill(
        [str(grid_path), "-w", str(words), "--allow-nonstandard", "--json-output", "--timeout", timeout] + extra
    )
    assert code != 1, (stdout, stderr)
    result = last_json(stdout)
    assert result is not None, (stdout, stderr)
    assert result["grid"][0][0] == "C"
