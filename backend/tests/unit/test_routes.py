"""
Unit tests for backend.api.routes.

All CLI adapter calls are mocked -- no real subprocess invocations.
"""

import json
import subprocess
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_grid(size=5, fill="."):
    """Build a simple size x size grid of strings."""
    return [[fill] * size for _ in range(size)]


def _make_dict_grid(size=5):
    """Build a size x size grid using frontend dict format."""
    return [[{"letter": "", "isBlack": False}] * size for _ in range(size)]


def _fill_request(size=5, **overrides):
    """Return a minimal valid /api/fill request body."""
    body = {
        "size": size,
        "grid": _make_grid(size),
        "wordlists": ["comprehensive"],
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(mocker):
    """Create a Flask test client with the CLI adapter mocked out."""
    # Patch get_adapter before importing app so the module-level call is safe
    mock_adapter = MagicMock()
    mock_adapter.health_check.return_value = True
    mocker.patch("backend.api.routes.get_adapter", return_value=mock_adapter)
    # Also patch the module-level cli_adapter that is already bound
    mocker.patch("backend.api.routes.cli_adapter", mock_adapter)
    # Patch resolve_wordlist_paths to return deterministic paths
    mocker.patch(
        "backend.api.routes.resolve_wordlist_paths",
        return_value=["/fake/wordlists/comprehensive.txt"],
    )

    from backend.app import create_app

    app = create_app(testing=True)
    with app.test_client() as c:
        yield c, mock_adapter


def _post_json(client, url, data):
    """Helper to POST JSON and return the Flask test response."""
    return client.post(url, data=json.dumps(data), content_type="application/json")


# ===================================================================
# GET /api/health
# ===================================================================


class TestHealthCheck:
    def test_healthy(self, client):
        c, mock_adapter = client
        mock_adapter.health_check.return_value = True

        resp = c.get("/api/health")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "healthy"
        assert body["components"]["cli_adapter"] == "ok"
        assert body["components"]["api_server"] == "ok"

    def test_degraded(self, client):
        c, mock_adapter = client
        mock_adapter.health_check.return_value = False

        resp = c.get("/api/health")
        assert resp.status_code == 503
        body = resp.get_json()
        assert body["status"] == "degraded"
        assert body["components"]["cli_adapter"] == "error"


# ===================================================================
# POST /api/pattern
# ===================================================================


class TestPatternSearch:
    def test_valid_request(self, client):
        c, mock_adapter = client
        mock_adapter.pattern.return_value = {"results": [{"word": "CAT", "score": 90}]}

        resp = _post_json(c, "/api/pattern", {"pattern": "C?T"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["results"][0]["word"] == "CAT"
        mock_adapter.pattern.assert_called_once()

    def test_missing_pattern_field(self, client):
        c, _ = client
        resp = _post_json(c, "/api/pattern", {"wordlists": ["comprehensive"]})
        assert resp.status_code == 400

    def test_empty_body(self, client):
        c, _ = client
        resp = c.post(
            "/api/pattern",
            data=json.dumps(None),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_no_json_content_type(self, client):
        c, _ = client
        resp = c.post("/api/pattern", data="not json", content_type="text/plain")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "INVALID_CONTENT_TYPE"

    def test_with_max_results(self, client):
        c, mock_adapter = client
        mock_adapter.pattern.return_value = {"results": []}

        resp = _post_json(c, "/api/pattern", {"pattern": "A?B", "max_results": 10})
        assert resp.status_code == 200
        _, kwargs = mock_adapter.pattern.call_args
        assert kwargs["max_results"] == 10

    def test_with_algorithm(self, client):
        c, mock_adapter = client
        mock_adapter.pattern.return_value = {"results": []}

        resp = _post_json(c, "/api/pattern", {"pattern": "A?B", "algorithm": "trie"})
        assert resp.status_code == 200
        _, kwargs = mock_adapter.pattern.call_args
        assert kwargs["algorithm"] == "trie"

    def test_adapter_raises_value_error(self, client):
        c, mock_adapter = client
        mock_adapter.pattern.side_effect = ValueError("bad pattern")

        resp = _post_json(c, "/api/pattern", {"pattern": "???"})
        assert resp.status_code == 400
        assert "bad pattern" in resp.get_json()["error"]["message"]

    def test_adapter_timeout(self, client):
        c, mock_adapter = client
        mock_adapter.pattern.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=30)

        resp = _post_json(c, "/api/pattern", {"pattern": "A?B"})
        assert resp.status_code == 505

    def test_adapter_internal_error(self, client):
        c, mock_adapter = client
        mock_adapter.pattern.side_effect = RuntimeError("boom")

        resp = _post_json(c, "/api/pattern", {"pattern": "A?B"})
        assert resp.status_code == 500
        assert "boom" in resp.get_json()["error"]["message"]

    def test_pattern_not_string(self, client):
        c, _ = client
        resp = _post_json(c, "/api/pattern", {"pattern": 123})
        assert resp.status_code == 400


# ===================================================================
# POST /api/number
# ===================================================================


class TestNumberGrid:
    def _valid_body(self, size=5):
        return {"size": size, "grid": _make_grid(size)}

    def test_valid_request(self, client):
        c, mock_adapter = client
        mock_adapter.number.return_value = {"numbering": {"1": [0, 0]}}

        resp = _post_json(c, "/api/number", self._valid_body())
        assert resp.status_code == 200
        mock_adapter.number.assert_called_once()

    def test_missing_grid(self, client):
        c, _ = client
        resp = _post_json(c, "/api/number", {"size": 5})
        assert resp.status_code == 400

    def test_missing_size(self, client):
        c, _ = client
        resp = _post_json(c, "/api/number", {"grid": _make_grid(5)})
        assert resp.status_code == 400

    def test_no_json_content_type(self, client):
        c, _ = client
        resp = c.post("/api/number", data="text", content_type="text/plain")
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_CONTENT_TYPE"

    def test_empty_body(self, client):
        c, _ = client
        resp = c.post(
            "/api/number",
            data=json.dumps(None),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_nonstandard_size_passes(self, client):
        c, mock_adapter = client
        mock_adapter.number.return_value = {"numbering": {}}

        resp = _post_json(c, "/api/number", self._valid_body(7))
        assert resp.status_code == 200
        _, kwargs = mock_adapter.number.call_args
        # 7 is non-standard so allow_nonstandard should be True
        assert kwargs["allow_nonstandard"] is True

    def test_standard_size_15(self, client):
        c, mock_adapter = client
        mock_adapter.number.return_value = {"numbering": {}}

        resp = _post_json(c, "/api/number", self._valid_body(15))
        assert resp.status_code == 200
        _, kwargs = mock_adapter.number.call_args
        assert kwargs["allow_nonstandard"] is False

    def test_adapter_timeout(self, client):
        c, mock_adapter = client
        mock_adapter.number.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=30)

        resp = _post_json(c, "/api/number", self._valid_body())
        assert resp.status_code == 504

    def test_adapter_internal_error(self, client):
        c, mock_adapter = client
        mock_adapter.number.side_effect = RuntimeError("crash")

        resp = _post_json(c, "/api/number", self._valid_body())
        assert resp.status_code == 500


# ===================================================================
# POST /api/normalize
# ===================================================================


class TestNormalizeEntry:
    def test_valid_request(self, client):
        c, mock_adapter = client
        mock_adapter.normalize.return_value = {"normalized": "HELLO WORLD"}

        resp = _post_json(c, "/api/normalize", {"text": "hello world"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["normalized"] == "HELLO WORLD"
        mock_adapter.normalize.assert_called_once_with("hello world")

    def test_missing_text(self, client):
        c, _ = client
        resp = _post_json(c, "/api/normalize", {"foo": "bar"})
        assert resp.status_code == 400

    def test_empty_text(self, client):
        c, _ = client
        resp = _post_json(c, "/api/normalize", {"text": "   "})
        assert resp.status_code == 400

    def test_text_too_long(self, client):
        c, _ = client
        resp = _post_json(c, "/api/normalize", {"text": "A" * 101})
        assert resp.status_code == 400

    def test_no_json_content_type(self, client):
        c, _ = client
        resp = c.post("/api/normalize", data="text", content_type="text/plain")
        assert resp.status_code == 400

    def test_adapter_timeout(self, client):
        c, mock_adapter = client
        mock_adapter.normalize.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=10)

        resp = _post_json(c, "/api/normalize", {"text": "foo"})
        assert resp.status_code == 506

    def test_adapter_internal_error(self, client):
        c, mock_adapter = client
        mock_adapter.normalize.side_effect = RuntimeError("fail")

        resp = _post_json(c, "/api/normalize", {"text": "foo"})
        assert resp.status_code == 500


# ===================================================================
# POST /api/fill
# ===================================================================


class TestFillGrid:
    def test_valid_request(self, client):
        c, mock_adapter = client
        mock_adapter.fill.return_value = {"success": True, "grid": _make_grid(5, "A")}

        resp = _post_json(c, "/api/fill", _fill_request())
        assert resp.status_code == 200
        mock_adapter.fill.assert_called_once()

    def test_missing_grid(self, client):
        c, _ = client
        resp = _post_json(c, "/api/fill", {"size": 5, "wordlists": ["comprehensive"]})
        assert resp.status_code == 400

    def test_missing_size(self, client):
        c, _ = client
        resp = _post_json(c, "/api/fill", {"grid": _make_grid(5), "wordlists": ["comprehensive"]})
        assert resp.status_code == 400

    def test_no_json_content_type(self, client):
        c, _ = client
        resp = c.post("/api/fill", data="text", content_type="text/plain")
        assert resp.status_code == 400

    def test_frontend_dict_grid_conversion(self, client):
        """Frontend sends grid cells as dicts; route should convert to CLI format."""
        c, mock_adapter = client
        mock_adapter.fill.return_value = {"success": True, "grid": []}

        grid = [
            [
                {"letter": "A", "isBlack": False},
                {"letter": "", "isBlack": True},
                {"letter": "", "isBlack": False},
            ]
        ] * 3
        resp = _post_json(c, "/api/fill", {"size": 3, "grid": grid})
        assert resp.status_code == 200

        call_kwargs = mock_adapter.fill.call_args[1]
        cli_grid = call_kwargs["grid_data"]["grid"]
        # First row should be ["A", "#", "."]
        assert cli_grid[0] == ["A", "#", "."]

    def test_already_cli_format_grid(self, client):
        """Grid cells already in string format should pass through."""
        c, mock_adapter = client
        mock_adapter.fill.return_value = {"success": True}

        grid = [["A", "#", "."] * 2 for _ in range(6)]
        resp = _post_json(c, "/api/fill", {"size": 6, "grid": grid})
        assert resp.status_code == 200

    def test_no_valid_wordlists(self, client, mocker):
        c, _ = client
        # Override resolve_wordlist_paths to return empty list
        mocker.patch(
            "backend.api.routes.resolve_wordlist_paths",
            return_value=[],
        )

        resp = _post_json(c, "/api/fill", _fill_request())
        assert resp.status_code == 400
        assert "wordlist" in resp.get_json()["error"]["message"].lower()

    def test_custom_timeout_and_min_score(self, client):
        c, mock_adapter = client
        mock_adapter.fill.return_value = {"success": True}

        resp = _post_json(c, "/api/fill", _fill_request(timeout=60, min_score=50))
        assert resp.status_code == 200
        call_kwargs = mock_adapter.fill.call_args[1]
        assert call_kwargs["timeout_seconds"] == 60
        assert call_kwargs["min_score"] == 50

    def test_adapter_timeout(self, client):
        c, mock_adapter = client
        mock_adapter.fill.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=300)

        resp = _post_json(c, "/api/fill", _fill_request())
        assert resp.status_code == 507

    def test_adapter_internal_error(self, client):
        c, mock_adapter = client
        mock_adapter.fill.side_effect = RuntimeError("oom")

        resp = _post_json(c, "/api/fill", _fill_request())
        assert resp.status_code == 500


# ===================================================================
# POST /api/fill/with-progress
# ===================================================================


class TestFillWithProgress:
    def test_valid_request_returns_202(self, client, mocker):
        c, mock_adapter = client
        mock_adapter.cli_path = MagicMock()
        mock_adapter.cli_path.parent = "/fake"
        mocker.patch("backend.api.routes.create_progress_tracker", return_value="task-123")
        mock_thread = mocker.patch("backend.api.routes.threading.Thread")

        resp = _post_json(c, "/api/fill/with-progress", _fill_request())
        assert resp.status_code == 202
        body = resp.get_json()
        assert body["task_id"] == "task-123"
        assert body["progress_url"] == "/api/progress/task-123"
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    def test_missing_grid_returns_400(self, client):
        c, _ = client
        resp = _post_json(c, "/api/fill/with-progress", {"size": 5, "wordlists": ["comprehensive"]})
        assert resp.status_code == 400

    def test_theme_entries_passed_through(self, client, mocker):
        c, mock_adapter = client
        mock_adapter.cli_path = MagicMock()
        mock_adapter.cli_path.parent = "/fake"
        mocker.patch("backend.api.routes.create_progress_tracker", return_value="t1")
        mock_thread = mocker.patch("backend.api.routes.threading.Thread")

        body = _fill_request(theme_entries={"(0,0,across)": "HELLO"})
        resp = _post_json(c, "/api/fill/with-progress", body)
        assert resp.status_code == 202

        # Verify the thread was started (theme entries handled in background)
        mock_thread.return_value.start.assert_called_once()

    def test_adaptive_mode_flag(self, client, mocker):
        c, mock_adapter = client
        mock_adapter.cli_path = MagicMock()
        mock_adapter.cli_path.parent = "/fake"
        mocker.patch("backend.api.routes.create_progress_tracker", return_value="t2")
        mock_thread = mocker.patch("backend.api.routes.threading.Thread")

        body = _fill_request(adaptive_mode=True, max_adaptations=5)
        resp = _post_json(c, "/api/fill/with-progress", body)
        assert resp.status_code == 202

        # Check that --adaptive and --max-adaptations appear in cmd_args
        thread_call_args = mock_thread.call_args
        cmd_args = thread_call_args[1]["args"][1]  # second positional arg to run_cli_with_progress
        assert "--adaptive" in cmd_args
        assert "--max-adaptations" in cmd_args
        assert "5" in cmd_args

    def test_partial_fill_flag(self, client, mocker):
        c, mock_adapter = client
        mock_adapter.cli_path = MagicMock()
        mock_adapter.cli_path.parent = "/fake"
        mocker.patch("backend.api.routes.create_progress_tracker", return_value="t3")
        mock_thread = mocker.patch("backend.api.routes.threading.Thread")

        body = _fill_request(partial_fill=True)
        resp = _post_json(c, "/api/fill/with-progress", body)
        assert resp.status_code == 202

        cmd_args = mock_thread.call_args[1]["args"][1]
        assert "--partial-fill" in cmd_args

    def test_cleanup_flag(self, client, mocker):
        c, mock_adapter = client
        mock_adapter.cli_path = MagicMock()
        mock_adapter.cli_path.parent = "/fake"
        mocker.patch("backend.api.routes.create_progress_tracker", return_value="t4")
        mock_thread = mocker.patch("backend.api.routes.threading.Thread")

        body = _fill_request(cleanup=True)
        resp = _post_json(c, "/api/fill/with-progress", body)
        assert resp.status_code == 202

        cmd_args = mock_thread.call_args[1]["args"][1]
        assert "--cleanup" in cmd_args

    def test_internal_error(self, client, mocker):
        c, _ = client
        mocker.patch(
            "backend.api.routes.validate_fill_request",
            side_effect=RuntimeError("unexpected"),
        )

        resp = _post_json(c, "/api/fill/with-progress", _fill_request())
        assert resp.status_code == 500


# ===================================================================
# POST /api/grid/verify-words
# ===================================================================


class TestVerifyWords:
    def test_missing_grid_field(self, client):
        c, _ = client
        resp = _post_json(c, "/api/grid/verify-words", {"size": 3})
        assert resp.status_code == 400

    def test_empty_body(self, client):
        c, _ = client
        resp = c.post(
            "/api/grid/verify-words",
            data=json.dumps(None),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_all_empty_grid(self, client, mocker):
        """Fully empty grid should have zero checked slots."""
        c, _ = client
        # Mock wordlist file reading to avoid filesystem dependency
        mocker.patch("pathlib.Path.rglob", return_value=[])

        grid = _make_grid(5, ".")
        resp = _post_json(c, "/api/grid/verify-words", {"grid": grid, "size": 5})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total_checked"] == 0

    def test_valid_word_in_grid(self, client, mocker, tmp_path):
        """A word that exists in the wordlist should not be flagged."""
        c, _ = client
        # Create a temp wordlist file
        wl = tmp_path / "words.txt"
        wl.write_text("CAT\nDOG\nBAT\n")
        mocker.patch("pathlib.Path.rglob", return_value=[wl])

        # 3x3 grid: CAT across top row
        grid = [
            ["C", "A", "T"],
            [".", ".", "."],
            [".", ".", "."],
        ]
        resp = _post_json(c, "/api/grid/verify-words", {"grid": grid, "size": 3})
        assert resp.status_code == 200
        body = resp.get_json()
        # CAT is valid, should not be in invalid_words
        invalid_words = [w["word"] for w in body["invalid_words"]]
        assert "CAT" not in invalid_words

    def test_invalid_word_in_grid(self, client, mocker, tmp_path):
        """A fully-filled word not in wordlist should be flagged as invalid."""
        c, _ = client
        wl = tmp_path / "words.txt"
        wl.write_text("DOG\nBAT\n")
        mocker.patch("pathlib.Path.rglob", return_value=[wl])

        # 3x3 grid: XYZ across top row -- not in wordlist
        grid = [
            ["X", "Y", "Z"],
            [".", ".", "."],
            [".", ".", "."],
        ]
        resp = _post_json(c, "/api/grid/verify-words", {"grid": grid, "size": 3})
        assert resp.status_code == 200
        body = resp.get_json()
        invalid_words = [w["word"] for w in body["invalid_words"]]
        assert "XYZ" in invalid_words


# ===================================================================
# POST /api/grid/clean
# ===================================================================


class TestCleanGrid:
    def test_missing_grid_field(self, client):
        c, _ = client
        resp = _post_json(c, "/api/grid/clean", {"size": 3})
        assert resp.status_code == 400

    def test_all_valid_words(self, client, mocker, tmp_path):
        """Grid with all valid words should return unchanged."""
        c, _ = client
        wl = tmp_path / "words.txt"
        wl.write_text("CAT\nCOB\nATM\nTMX\n")
        mocker.patch("pathlib.Path.rglob", return_value=[wl])

        grid = [
            ["C", "A", "T"],
            ["O", ".", "."],
            ["B", ".", "."],
        ]
        resp = _post_json(c, "/api/grid/clean", {"grid": grid, "size": 3})
        assert resp.status_code == 200
        body = resp.get_json()
        # COB is valid across, CAT is valid across
        # Only report on fully filled slots
        assert body["removed_count"] == 0 or "nothing to clean" in body.get("message", "").lower()

    def test_empty_body(self, client):
        c, _ = client
        resp = c.post(
            "/api/grid/clean",
            data=json.dumps(None),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ===================================================================
# POST /api/pattern/with-progress
# ===================================================================


class TestPatternWithProgress:
    def test_valid_request_returns_202(self, client, mocker):
        c, mock_adapter = client
        mock_adapter.cli_path = MagicMock()
        mock_adapter.cli_path.parent = "/fake"
        mocker.patch("backend.api.routes.create_progress_tracker", return_value="pat-1")
        mock_thread = mocker.patch("backend.api.routes.threading.Thread")

        resp = _post_json(c, "/api/pattern/with-progress", {"pattern": "C?T"})
        assert resp.status_code == 202
        body = resp.get_json()
        assert body["task_id"] == "pat-1"
        assert "/api/progress/pat-1" in body["progress_url"]
        mock_thread.return_value.start.assert_called_once()

    def test_missing_pattern_returns_400(self, client):
        c, _ = client
        resp = _post_json(c, "/api/pattern/with-progress", {"wordlists": ["comprehensive"]})
        assert resp.status_code == 400

    def test_internal_error(self, client, mocker):
        c, _ = client
        mocker.patch(
            "backend.api.routes.validate_pattern_request",
            side_effect=RuntimeError("oops"),
        )
        resp = _post_json(c, "/api/pattern/with-progress", {"pattern": "A?B"})
        assert resp.status_code == 500
