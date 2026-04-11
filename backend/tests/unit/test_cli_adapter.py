"""
Unit tests for CLIAdapter.

All subprocess calls are mocked — no real CLI invocations.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.core.cli_adapter import CLIAdapter, cached_normalize, get_adapter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the module-level singleton before every test."""
    import backend.core.cli_adapter as mod

    mod._adapter = None
    # Also clear lru_cache between tests
    cached_normalize.cache_clear()
    yield
    mod._adapter = None


@pytest.fixture
def cli_path(tmp_path):
    """Create a fake CLI executable so the constructor doesn't raise."""
    exe = tmp_path / "crossword"
    exe.touch()
    return str(exe)


@pytest.fixture
def adapter(cli_path):
    """Return a CLIAdapter pointing at a fake executable."""
    return CLIAdapter(cli_path=cli_path)


def _make_completed_process(stdout="", stderr="", returncode=0):
    cp = subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)
    return cp


# ===========================================================================
# Constructor
# ===========================================================================


class TestConstructor:
    def test_raises_when_cli_not_found(self, tmp_path):
        missing = tmp_path / "no_such_file"
        with pytest.raises(FileNotFoundError):
            CLIAdapter(cli_path=str(missing))

    def test_raises_when_path_is_directory(self, tmp_path):
        d = tmp_path / "somedir"
        d.mkdir()
        with pytest.raises(ValueError, match="not a file"):
            CLIAdapter(cli_path=str(d))

    def test_custom_timeout(self, cli_path):
        adapter = CLIAdapter(cli_path=cli_path, timeout=99)
        assert adapter.timeout == 99


# ===========================================================================
# pattern()
# ===========================================================================


class TestPattern:
    def test_empty_pattern_raises(self, adapter):
        with pytest.raises(ValueError, match="empty"):
            adapter.pattern("")

    def test_whitespace_pattern_raises(self, adapter):
        with pytest.raises(ValueError, match="empty"):
            adapter.pattern("   ")

    @patch("subprocess.run")
    def test_command_construction_basic(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout='{"results":[]}')
        adapter.pattern("C?T")

        args = mock_run.call_args[0][0]
        assert "pattern" in args
        assert "C?T" in args
        assert "--json-output" in args
        assert "--algorithm" in args
        assert "regex" in args  # default algorithm

    @patch("subprocess.run")
    def test_command_construction_with_wordlists(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout='{"results":[]}')
        adapter.pattern("A?B", wordlist_paths=["list1.txt", "list2.txt"])

        args = mock_run.call_args[0][0]
        # Each wordlist should be preceded by --wordlists
        wl_indices = [i for i, a in enumerate(args) if a == "--wordlists"]
        assert len(wl_indices) == 2
        assert args[wl_indices[0] + 1] == "list1.txt"
        assert args[wl_indices[1] + 1] == "list2.txt"

    @patch("subprocess.run")
    def test_command_construction_algorithm_trie(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout='{"results":[]}')
        adapter.pattern("??", algorithm="trie")

        args = mock_run.call_args[0][0]
        alg_idx = args.index("--algorithm")
        assert args[alg_idx + 1] == "trie"

    @patch("subprocess.run")
    def test_command_construction_max_results(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout='{"results":[]}')
        adapter.pattern("A?", max_results=50)

        args = mock_run.call_args[0][0]
        mr_idx = args.index("--max-results")
        assert args[mr_idx + 1] == "50"

    @patch("subprocess.run")
    def test_parses_valid_json(self, mock_run, adapter):
        payload = {"results": [{"word": "CAT", "score": 90}]}
        mock_run.return_value = _make_completed_process(stdout=json.dumps(payload))
        result = adapter.pattern("C?T")
        assert result == payload

    @patch("subprocess.run")
    def test_invalid_json_raises(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout="NOT JSON")
        with pytest.raises(ValueError, match="Failed to parse"):
            adapter.pattern("C?T")


# ===========================================================================
# number()
# ===========================================================================


class TestNumber:
    def test_empty_grid_raises(self, adapter):
        with pytest.raises(ValueError, match="empty"):
            adapter.number({})

    @patch("subprocess.run")
    def test_command_construction_standard(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout='{"numbering":[]}')
        adapter.number({"size": 15, "grid": []})

        args = mock_run.call_args[0][0]
        assert "number" in args
        assert "--json-output" in args
        assert "--allow-nonstandard" not in args

    @patch("subprocess.run")
    def test_allow_nonstandard_flag(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout='{"numbering":[]}')
        adapter.number({"size": 15, "grid": []}, allow_nonstandard=True)

        args = mock_run.call_args[0][0]
        assert "--allow-nonstandard" in args

    @patch("subprocess.run")
    def test_temp_file_receives_grid_json(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout='{"numbering":[]}')
        grid_data = {"size": 15, "grid": [["." for _ in range(15)] for _ in range(15)]}
        adapter.number(grid_data)

        # args[0] is cli_path, args[1] is "number", args[2] is the temp file
        args = mock_run.call_args[0][0]
        temp_path_arg = args[2]
        # Temp file is cleaned up, but we verify the path was .json
        assert temp_path_arg.endswith(".json")

    @patch("subprocess.run")
    def test_invalid_json_response_raises(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout="broken")
        with pytest.raises(ValueError, match="Failed to parse"):
            adapter.number({"size": 15, "grid": []})


# ===========================================================================
# fill()
# ===========================================================================


class TestFill:
    def test_empty_grid_raises(self, adapter):
        with pytest.raises(ValueError, match="empty"):
            adapter.fill({}, ["words.txt"])

    def test_no_wordlists_raises(self, adapter):
        with pytest.raises(ValueError, match="wordlist"):
            adapter.fill({"size": 5, "grid": []}, [])

    @patch("subprocess.run")
    def test_command_construction_all_flags(self, mock_run, adapter, tmp_path):
        # Prepare a fake output file that fill() will try to read
        mock_run.return_value = _make_completed_process(stdout="")

        # We need to intercept the output file write. Patch Path.exists and open.
        result_data = {"success": True, "grid": []}
        original_open = open

        def patched_open(path, *a, **kw):
            path_str = str(path)
            if path_str.endswith(".json") and "r" in (a[0] if a else kw.get("mode", "r")):
                # Could be reading the output file
                import io

                return io.StringIO(json.dumps(result_data))
            return original_open(path, *a, **kw)

        with patch("builtins.open", side_effect=patched_open):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "stat") as mock_stat:
                    mock_stat.return_value = MagicMock(st_size=100)
                    with patch.object(Path, "unlink"):
                        adapter.fill(
                            {
                                "size": 7,
                                "grid": [["." for _ in range(7)] for _ in range(7)],
                            },
                            ["w1.txt", "w2.txt"],
                            timeout_seconds=120,
                            min_score=50,
                            algorithm="regex",
                            partial_fill=True,
                        )

        args = mock_run.call_args[0][0]
        assert "fill" in args
        assert "--timeout" in args
        assert "120" in args
        assert "--min-score" in args
        assert "50" in args
        assert "--algorithm" in args
        assert "regex" in args
        assert "--partial-fill" in args
        # Non-standard size 7 => auto-detected
        assert "--allow-nonstandard" in args
        # Two wordlists
        wl_indices = [i for i, a in enumerate(args) if a == "--wordlists"]
        assert len(wl_indices) == 2

    @patch("subprocess.run")
    def test_standard_size_no_nonstandard_flag(self, mock_run, adapter, tmp_path):
        mock_run.return_value = _make_completed_process(stdout="")
        result_data = {"success": True}

        original_open = open

        def patched_open(path, *a, **kw):
            path_str = str(path)
            if path_str.endswith(".json") and "r" in (a[0] if a else kw.get("mode", "r")):
                import io

                return io.StringIO(json.dumps(result_data))
            return original_open(path, *a, **kw)

        with patch("builtins.open", side_effect=patched_open):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "stat") as mock_stat:
                    mock_stat.return_value = MagicMock(st_size=100)
                    with patch.object(Path, "unlink"):
                        adapter.fill(
                            {"size": 15, "grid": []},
                            ["w.txt"],
                        )

        args = mock_run.call_args[0][0]
        assert "--allow-nonstandard" not in args

    @patch("subprocess.run")
    def test_timeout_adds_buffer(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout="")

        result_data = {"success": True}
        original_open = open

        def patched_open(path, *a, **kw):
            path_str = str(path)
            if path_str.endswith(".json") and "r" in (a[0] if a else kw.get("mode", "r")):
                import io

                return io.StringIO(json.dumps(result_data))
            return original_open(path, *a, **kw)

        with patch("builtins.open", side_effect=patched_open):
            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "stat") as mock_stat:
                    mock_stat.return_value = MagicMock(st_size=100)
                    with patch.object(Path, "unlink"):
                        adapter.fill({"size": 15, "grid": []}, ["w.txt"], timeout_seconds=200)

        # subprocess.run should have been called with timeout=210
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 210

    @patch("subprocess.run")
    def test_empty_output_file_returns_error(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout="")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=0)
                with patch.object(Path, "unlink"):
                    result = adapter.fill({"size": 15, "grid": []}, ["w.txt"])

        assert result["success"] is False
        assert "no output" in result["error"].lower()

    @patch("subprocess.run")
    def test_check_success_false_for_fill(self, mock_run, adapter):
        """fill() passes check_success=False to allow partial fills."""
        mock_run.return_value = _make_completed_process(stdout="", returncode=1)

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=0)
                with patch.object(Path, "unlink"):
                    result = adapter.fill({"size": 15, "grid": []}, ["w.txt"])

        # Should NOT raise CalledProcessError — returns error dict instead
        assert result["success"] is False


# ===========================================================================
# fill_with_resume()
# ===========================================================================


class TestFillWithResume:
    def test_missing_state_file_raises(self, adapter):
        with pytest.raises(FileNotFoundError, match="State file not found"):
            adapter.fill_with_resume("task-1", "/no/such/file.gz", ["w.txt"])

    @patch("subprocess.run")
    def test_command_construction(self, mock_run, adapter, tmp_path):
        state_file = tmp_path / "state.gz"
        state_file.touch()

        mock_run.return_value = _make_completed_process(stdout="")
        result_data = {"success": True}
        original_open = open

        def patched_open(path, *a, **kw):
            path_str = str(path)
            if path_str.endswith(".json") and "r" in (a[0] if a else kw.get("mode", "r")):
                import io

                return io.StringIO(json.dumps(result_data))
            return original_open(path, *a, **kw)

        with patch("builtins.open", side_effect=patched_open):
            with patch.object(Path, "unlink"):
                adapter.fill_with_resume(
                    "task-42",
                    str(state_file),
                    ["w1.txt"],
                    timeout_seconds=60,
                    min_score=40,
                    algorithm="regex",
                )

        args = mock_run.call_args[0][0]
        assert "fill" in args
        assert "--resume" in args
        assert str(state_file) in args
        assert "--task-id" in args
        assert "task-42" in args
        assert "--timeout" in args
        assert "60" in args
        assert "--min-score" in args
        assert "40" in args
        assert "--algorithm" in args
        assert "regex" in args
        assert "--wordlists" in args
        assert "w1.txt" in args

    @patch("subprocess.run")
    def test_resume_timeout_buffer(self, mock_run, adapter, tmp_path):
        state_file = tmp_path / "state.gz"
        state_file.touch()

        mock_run.return_value = _make_completed_process(stdout="")
        result_data = {"success": True}
        original_open = open

        def patched_open(path, *a, **kw):
            path_str = str(path)
            if path_str.endswith(".json") and "r" in (a[0] if a else kw.get("mode", "r")):
                import io

                return io.StringIO(json.dumps(result_data))
            return original_open(path, *a, **kw)

        with patch("builtins.open", side_effect=patched_open):
            with patch.object(Path, "unlink"):
                adapter.fill_with_resume("t", str(state_file), ["w.txt"], timeout_seconds=100)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 110


# ===========================================================================
# normalize()
# ===========================================================================


class TestNormalize:
    def test_empty_text_raises(self, adapter):
        with pytest.raises(ValueError, match="empty"):
            adapter.normalize("")

    @patch("subprocess.run")
    def test_command_construction(self, mock_run, adapter):
        payload = {"original": "Tina Fey", "normalized": "TINAFEY"}
        mock_run.return_value = _make_completed_process(stdout=json.dumps(payload))
        result = adapter.normalize("Tina Fey")

        args = mock_run.call_args[0][0]
        assert "normalize" in args
        assert "Tina Fey" in args
        assert "--json-output" in args
        assert result == payload

    @patch("subprocess.run")
    def test_invalid_json_raises(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout="not json!")
        with pytest.raises(ValueError, match="Failed to parse"):
            adapter.normalize("test")


# ===========================================================================
# analyze_constraints() / analyze_placement_impact()
# ===========================================================================


class TestAnalyzeConstraints:
    GRID = {"size": 5, "grid": [["." for _ in range(5)] for _ in range(5)]}
    PAYLOAD = {
        "constraints": {"0,0": {"across_options": 10, "down_options": 5, "min_options": 5}},
        "summary": {"total_cells": 25, "critical_cells": 0, "average_min_options": 5.0},
    }

    def test_empty_grid_raises(self, adapter):
        with pytest.raises(ValueError, match="empty"):
            adapter.analyze_constraints({}, ["words.txt"])

    def test_empty_wordlist_raises(self, adapter):
        with pytest.raises(ValueError, match="wordlist"):
            adapter.analyze_constraints(self.GRID, [])

    @patch("subprocess.run")
    def test_command_construction(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout=json.dumps(self.PAYLOAD))
        adapter.analyze_constraints(self.GRID, ["list1.txt", "list2.txt"])

        args = mock_run.call_args[0][0]
        assert "analyze" in args
        assert "--json-output" in args
        w_indices = [i for i, a in enumerate(args) if a == "-w"]
        assert len(w_indices) == 2
        assert args[w_indices[0] + 1] == "list1.txt"
        assert args[w_indices[1] + 1] == "list2.txt"

    @patch("subprocess.run")
    def test_invalid_json_raises(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout="NOT JSON")
        with pytest.raises(ValueError, match="Failed to parse"):
            adapter.analyze_constraints(self.GRID, ["words.txt"])

    @patch("subprocess.run")
    def test_returns_parsed_result(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout=json.dumps(self.PAYLOAD))
        result = adapter.analyze_constraints(self.GRID, ["words.txt"])
        assert result == self.PAYLOAD


class TestAnalyzePlacementImpact:
    GRID = {"size": 5, "grid": [["." for _ in range(5)] for _ in range(5)]}
    SLOT = {"row": 0, "col": 0, "direction": "across", "length": 5}
    PAYLOAD = {
        "impacts": {"0,1,down": {"before": 100, "after": 10, "delta": -90, "length": 5}},
        "summary": {
            "total_crossings": 1,
            "worst_delta": -90,
            "crossings_eliminated": 0,
        },
    }

    def test_empty_grid_raises(self, adapter):
        with pytest.raises(ValueError, match="empty"):
            adapter.analyze_placement_impact({}, "CATCH", self.SLOT, ["words.txt"])

    def test_empty_word_raises(self, adapter):
        with pytest.raises(ValueError, match="Word"):
            adapter.analyze_placement_impact(self.GRID, "", self.SLOT, ["words.txt"])

    @patch("subprocess.run")
    def test_command_construction(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout=json.dumps(self.PAYLOAD))
        adapter.analyze_placement_impact(self.GRID, "CATCH", self.SLOT, ["list1.txt"])

        args = mock_run.call_args[0][0]
        assert "analyze" in args
        assert "--json-output" in args
        assert "--word" in args
        word_idx = args.index("--word")
        assert args[word_idx + 1] == "CATCH"
        assert "--slot" in args
        slot_idx = args.index("--slot")
        assert args[slot_idx + 1] == "0,0,across,5"

    @patch("subprocess.run")
    def test_invalid_json_raises(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout="NOT JSON")
        with pytest.raises(ValueError, match="Failed to parse"):
            adapter.analyze_placement_impact(self.GRID, "CATCH", self.SLOT, ["words.txt"])

    @patch("subprocess.run")
    def test_returns_parsed_result(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(stdout=json.dumps(self.PAYLOAD))
        result = adapter.analyze_placement_impact(self.GRID, "CATCH", self.SLOT, ["words.txt"])
        assert result == self.PAYLOAD


# ===========================================================================
# health_check()
# ===========================================================================


class TestHealthCheck:
    @patch("subprocess.run")
    def test_returns_true_on_success(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(returncode=0)
        assert adapter.health_check() is True

    @patch("subprocess.run")
    def test_returns_false_on_nonzero(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(returncode=1)
        assert adapter.health_check() is False

    @patch("subprocess.run")
    def test_returns_false_on_timeout(self, mock_run, adapter):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["x"], timeout=5)
        assert adapter.health_check() is False

    @patch("subprocess.run")
    def test_returns_false_on_generic_exception(self, mock_run, adapter):
        mock_run.side_effect = OSError("cannot exec")
        assert adapter.health_check() is False


# ===========================================================================
# _run_command() internals
# ===========================================================================


class TestRunCommand:
    @patch("subprocess.run")
    def test_check_success_raises_on_nonzero(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(returncode=1, stderr="fail")
        with pytest.raises(subprocess.CalledProcessError):
            adapter._run_command(["some", "cmd"], check_success=True)

    @patch("subprocess.run")
    def test_check_success_false_no_raise(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process(returncode=1, stderr="fail")
        stdout, stderr, code = adapter._run_command(["cmd"], check_success=False)
        assert code == 1

    @patch("subprocess.run")
    def test_timeout_expired_is_reraised(self, mock_run, adapter):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["x"], timeout=5)
        with pytest.raises(subprocess.TimeoutExpired):
            adapter._run_command(["cmd"])

    @patch("subprocess.run")
    def test_uses_default_timeout(self, mock_run, cli_path):
        a = CLIAdapter(cli_path=cli_path, timeout=42)
        mock_run.return_value = _make_completed_process()
        a._run_command(["test"])
        assert mock_run.call_args[1]["timeout"] == 42

    @patch("subprocess.run")
    def test_overrides_timeout(self, mock_run, adapter):
        mock_run.return_value = _make_completed_process()
        adapter._run_command(["test"], timeout=99)
        assert mock_run.call_args[1]["timeout"] == 99


# ===========================================================================
# Singleton: get_adapter()
# ===========================================================================


class TestGetAdapter:
    @patch("backend.core.cli_adapter.CLIAdapter.__init__", return_value=None)
    def test_returns_same_instance(self, mock_init):
        a1 = get_adapter()
        a2 = get_adapter()
        assert a1 is a2
        # Constructor called only once
        assert mock_init.call_count == 1


# ===========================================================================
# Caching: cached_normalize()
# ===========================================================================


class TestCachedNormalize:
    @patch("backend.core.cli_adapter.get_adapter")
    def test_cache_hit(self, mock_get_adapter):
        mock_adapter = MagicMock()
        mock_adapter.normalize.return_value = {"normalized": "TEST"}
        mock_get_adapter.return_value = mock_adapter

        # First call
        r1 = cached_normalize("test")
        # Second call — should come from cache
        r2 = cached_normalize("test")

        assert r1 == r2
        # normalize() should have been called only once
        assert mock_adapter.normalize.call_count == 1

    @patch("backend.core.cli_adapter.get_adapter")
    def test_different_inputs_not_cached(self, mock_get_adapter):
        mock_adapter = MagicMock()
        mock_adapter.normalize.side_effect = lambda t: {"normalized": t.upper()}
        mock_get_adapter.return_value = mock_adapter

        cached_normalize("aaa")
        cached_normalize("bbb")

        assert mock_adapter.normalize.call_count == 2
