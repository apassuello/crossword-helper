"""Unit tests for pause/resume API routes."""

import json
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.core.state_paths import PAUSE_FLAG_DIR


@pytest.fixture
def client(mocker):
    """Create Flask test client with mocked dependencies."""
    from backend.app import create_app

    app = create_app(testing=True)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def edit_merger():
    """Return the module-level edit_merger instance (already an EditMerger)."""
    from backend.api import pause_resume_routes

    return pause_resume_routes.edit_merger


@pytest.fixture
def mock_pause_controller(mocker):
    """Patch PauseController at its source module so local imports pick it up."""
    mock_pc = MagicMock()
    mock_pc.is_task_running.return_value = True
    mock_cls = mocker.patch(
        "cli.src.fill.pause_controller.PauseController",
        return_value=mock_pc,
    )
    return mock_cls, mock_pc


@pytest.fixture
def mock_adapter(mocker):
    """Patch the CLI adapter used by the resume route."""
    adapter = MagicMock()
    adapter.fill_with_resume.return_value = {
        "success": True,
        "grid": [["A", "B", "C"]] * 3,
        "slots_filled": 12,
        "total_slots": 40,
        "paused": False,
    }
    mocker.patch(
        "backend.api.pause_resume_routes.get_adapter",
        return_value=adapter,
    )
    return adapter


@pytest.fixture
def mock_state_manager(mocker):
    """Patch StateManager at its source module."""
    mock_sm = MagicMock()
    mocker.patch(
        "cli.src.fill.state_manager.StateManager",
        return_value=mock_sm,
    )
    return mock_sm


@pytest.fixture
def mock_grid(mocker):
    """Patch Grid at its source module."""
    return mocker.patch("cli.src.core.grid.Grid")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_saved_state(grid=None):
    """Helper to create a mock saved_state object."""
    state = SimpleNamespace()
    state.grid_dict = {"size": 3, "grid": grid or [["A", "B", "C"]] * 3}
    state.slot_list = []
    state.slot_id_map = {}
    return state


def _make_metadata(**overrides):
    meta = {"slots_filled": 10, "total_slots": 40}
    meta.update(overrides)
    return meta


# ---------------------------------------------------------------------------
# POST /api/fill/pause/<task_id>
# ---------------------------------------------------------------------------


class TestPauseAutofill:
    def test_pause_returns_200(self, client, mock_pause_controller):
        mock_cls, mock_pc = mock_pause_controller

        resp = client.post("/api/fill/pause/task_abc")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert "task_abc" in data["message"]
        assert data["task_id"] == "task_abc"
        # DD1: the pause route now single-sources pause_dir so the flag lands where the
        # spawned CLI reads it.
        mock_cls.assert_called_once_with(task_id="task_abc", pause_dir=PAUSE_FLAG_DIR)
        mock_pc.request_pause.assert_called_once()

    def test_pause_calls_request_pause(self, client, mock_pause_controller):
        _, mock_pc = mock_pause_controller

        client.post("/api/fill/pause/task_xyz")

        mock_pc.request_pause.assert_called_once()

    def test_pause_nonexistent_task_returns_404(self, client, mock_pause_controller, mocker):
        """Regression: pausing a task that is not running must 404 with JSON,
        not return 200 success."""
        _, mock_pc = mock_pause_controller
        mock_pc.is_task_running.return_value = False
        mocker.patch(
            "backend.api.progress_routes.is_process_running",
            return_value=False,
        )

        resp = client.post("/api/fill/pause/no_such_task")
        data = resp.get_json()

        assert resp.status_code == 404
        assert "error" in data
        mock_pc.request_pause.assert_not_called()

    def test_pause_exception_returns_error(self, client, mocker):
        mocker.patch(
            "cli.src.fill.pause_controller.PauseController",
            side_effect=RuntimeError("disk full"),
        )

        resp = client.post("/api/fill/pause/task_err")
        data = resp.get_json()

        # Errors must come back as JSON, never an HTML debugger page
        assert resp.status_code == 500
        assert resp.content_type.startswith("application/json")
        assert data["error"]["code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# POST /api/fill/cancel/<task_id>
# ---------------------------------------------------------------------------


class TestCancelAutofill:
    def test_cancel_returns_200_and_honest_state_saved(self, client, mock_pause_controller, mocker):
        """Regression: cancel must NOT claim state_saved: true — killing the
        subprocess saves nothing."""
        mocker.patch(
            "backend.api.progress_routes.is_process_running",
            return_value=True,
        )
        mocker.patch(
            "backend.api.progress_routes.cleanup_process",
            return_value=True,
        )

        resp = client.post("/api/fill/cancel/task_c1")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["task_id"] == "task_c1"
        assert data["state_saved"] is False
        assert "cancelled" in data["message"].lower()

    def test_cancel_kills_process_and_clears_flags(self, client, mock_pause_controller, mocker):
        _, mock_pc = mock_pause_controller
        mocker.patch(
            "backend.api.progress_routes.is_process_running",
            return_value=True,
        )
        mock_cleanup = mocker.patch(
            "backend.api.progress_routes.cleanup_process",
            return_value=True,
        )

        client.post("/api/fill/cancel/task_c2")

        mock_cleanup.assert_called_once_with("task_c2")
        # Cancel is a hard stop: it must clear stale flags, not request pause
        mock_pc.request_pause.assert_not_called()
        mock_pc.clear_pause.assert_called_once()
        mock_pc.clear_running.assert_called_once()

    def test_cancel_nonexistent_task_returns_404(self, client, mock_pause_controller, mocker):
        """Regression: cancelling an unknown/finished task must 404 with JSON,
        not return 200 success."""
        mocker.patch(
            "backend.api.progress_routes.is_process_running",
            return_value=False,
        )
        mock_cleanup = mocker.patch(
            "backend.api.progress_routes.cleanup_process",
        )

        resp = client.post("/api/fill/cancel/no_such_task")
        data = resp.get_json()

        assert resp.status_code == 404
        assert "error" in data
        mock_cleanup.assert_not_called()

    def test_cancel_exception_returns_error(self, client, mocker):
        mocker.patch(
            "backend.api.progress_routes.is_process_running",
            side_effect=RuntimeError("boom"),
        )

        resp = client.post("/api/fill/cancel/task_err")
        data = resp.get_json()

        # Errors must come back as JSON, never an HTML debugger page
        assert resp.status_code == 500
        assert resp.content_type.startswith("application/json")
        assert data["error"]["code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# POST /api/fill/resume
# ---------------------------------------------------------------------------


class TestResumeAutofill:
    def test_resume_valid_request_no_edits(self, client, mock_state_manager, mock_adapter):
        saved = _make_saved_state()
        meta = _make_metadata()
        mock_state_manager.load_csp_state.return_value = (saved, meta)

        resp = client.post(
            "/api/fill/resume",
            json={"task_id": "task_r1", "options": {"min_score": 50}},
        )
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["original_task_id"] == "task_r1"
        assert data["new_task_id"].startswith("resume_")
        assert data["result"]["slots_filled"] == 12
        assert data["total_slots"] == 40
        mock_state_manager.save_csp_state.assert_called_once()
        mock_adapter.fill_with_resume.assert_called_once()

    def test_resume_actually_runs_cli_resume(self, client, mock_state_manager, mock_adapter):
        """Regression (headline): /api/fill/resume must actually RUN the
        resumed fill via the CLI, from the shared /tmp/crossword_states
        store — not just re-save the state and return."""
        saved = _make_saved_state()
        meta = _make_metadata(algorithm="csp", wordlists=[])
        mock_state_manager.load_csp_state.return_value = (saved, meta)

        resp = client.post(
            "/api/fill/resume",
            json={"task_id": "task_run", "options": {"timeout": 60, "min_score": 40}},
        )
        data = resp.get_json()

        assert resp.status_code == 200
        kwargs = mock_adapter.fill_with_resume.call_args.kwargs
        # The state file handed to the CLI lives in the CLI's own store
        assert kwargs["state_file_path"].startswith("/tmp/crossword_states/")
        assert kwargs["state_file_path"].endswith(f"{data['new_task_id']}.json.gz")
        assert kwargs["task_id"] == data["new_task_id"]
        assert kwargs["timeout_seconds"] == 60
        assert kwargs["min_score"] == 40
        # 'csp' (state manager's name for classic fills) maps to CLI 'trie'
        assert kwargs["algorithm"] == "trie"
        assert kwargs["wordlist_paths"], "resume must run with a real wordlist"

    def test_resume_with_edited_grid(self, client, mock_state_manager, edit_merger, mocker, mock_adapter):
        saved = _make_saved_state()
        meta = _make_metadata()
        mock_state_manager.load_csp_state.return_value = (saved, meta)

        # Mock the module-level edit_merger's merge_edits
        mocker.patch.object(edit_merger, "merge_edits", return_value=saved)

        edited = [["X", "B", "C"]] * 3
        resp = client.post(
            "/api/fill/resume",
            json={"task_id": "task_r2", "edited_grid": edited},
        )
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        edit_merger.merge_edits.assert_called_once()

    def test_resume_accepts_frontend_cell_formats(self, client, mock_state_manager, edit_merger, mocker, mock_adapter):
        """Regression: the exact frontend payload (dict cells and
        single-letter list cells) used to crash resume with an
        AttributeError. It must be normalized to CLI strings, preserving
        black squares from the saved state."""
        saved = _make_saved_state(grid=[["A", "B", "#"], [".", ".", "."], [".", ".", "."]])
        meta = _make_metadata()
        mock_state_manager.load_csp_state.return_value = (saved, meta)
        mocker.patch.object(edit_merger, "merge_edits", return_value=saved)

        # Row 0: frontend dict cells (carry isBlack); rows 1-2: legacy
        # ["A"] / ["."] cells, which are LOSSY — the saved state's black
        # square at (1, 2)... none here, but blacks in list rows must be
        # inherited from the saved grid.
        saved.grid_dict["grid"][1][2] = "#"
        edited = [
            [
                {"letter": "A", "isBlack": False},
                {"letter": "Q", "isBlack": False},
                {"letter": "", "isBlack": True},
            ],
            [["C"], ["."], ["."]],  # (1,2) is '#' in saved state
            [["."], ["."], ["."]],
        ]
        resp = client.post(
            "/api/fill/resume",
            json={"task_id": "task_fmt", "edited_grid": edited},
        )

        assert resp.status_code == 200
        merged_grid_dict = edit_merger.merge_edits.call_args.kwargs["edited_grid_dict"]
        assert merged_grid_dict["grid"][0] == ["A", "Q", "#"]  # dict isBlack honored
        assert merged_grid_dict["grid"][1] == ["C", ".", "#"]  # black inherited

    def test_resume_missing_task_id_returns_400(self, client):
        resp = client.post("/api/fill/resume", json={"options": {}})
        data = resp.get_json()

        assert resp.status_code == 400
        assert "task_id" in data["error"]

    def test_resume_empty_body_returns_400(self, client, mocker):
        mocker.patch(
            "backend.api.pause_resume_routes.handle_error",
            return_value=(json.dumps({"error": "bad request"}), 400),
        )

        resp = client.post(
            "/api/fill/resume",
            data="",
            content_type="application/json",
        )

        assert resp.status_code == 400

    def test_resume_state_not_found_returns_404(self, client, mock_state_manager):
        mock_state_manager.load_csp_state.side_effect = FileNotFoundError("gone")

        resp = client.post("/api/fill/resume", json={"task_id": "task_missing"})
        data = resp.get_json()

        assert resp.status_code == 404
        assert "not found" in data["error"].lower()

    def test_resume_unsolvable_edits_returns_409(self, client, mock_state_manager, edit_merger, mocker):
        saved = _make_saved_state()
        meta = _make_metadata()
        mock_state_manager.load_csp_state.return_value = (saved, meta)
        mocker.patch.object(edit_merger, "merge_edits", side_effect=ValueError("unsolvable"))

        resp = client.post(
            "/api/fill/resume",
            json={
                "task_id": "task_r3",
                "edited_grid": [["Z", "Z", "Z"]] * 3,
            },
        )
        data = resp.get_json()

        assert resp.status_code == 409
        assert "unsolvable" in data["error"].lower()

    def test_resume_saves_with_correct_metadata(self, client, mock_state_manager, mock_adapter):
        saved = _make_saved_state()
        meta = _make_metadata(algorithm="csp")
        mock_state_manager.load_csp_state.return_value = (saved, meta)

        resp = client.post(
            "/api/fill/resume",
            json={"task_id": "task_r4", "options": {"timeout": 300}},
        )

        assert resp.status_code == 200
        call_kwargs = mock_state_manager.save_csp_state.call_args
        saved_meta = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert saved_meta["resumed_from"] == "task_r4"
        assert saved_meta["resume_options"] == {"timeout": 300}

    def test_resume_no_options_defaults_to_empty(self, client, mock_state_manager, mock_adapter):
        saved = _make_saved_state()
        meta = _make_metadata()
        mock_state_manager.load_csp_state.return_value = (saved, meta)

        resp = client.post("/api/fill/resume", json={"task_id": "task_r5"})
        resp.get_json()

        assert resp.status_code == 200
        call_kwargs = mock_state_manager.save_csp_state.call_args
        saved_meta = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert saved_meta["resume_options"] == {}


class TestResumeOptionShapes:
    """
    Issue #24: /api/fill/resume was the only route in the API surface reading
    its options from a nested `options` object. Every other fill route reads
    `timeout` at the top level (backend/api/routes.py:239, :558, :615), so a
    caller who followed that pattern got the 300s default silently -- no error,
    no warning, no 400. Two tests in this repo, both written by people working
    directly on this seam, already made exactly that mistake.

    Top level is now canonical and wins; nested stays accepted. These assert the
    value that actually reaches the CLI adapter, not merely that the request
    returned 200 -- the old behaviour returned 200 too.
    """

    def _post(self, client, mock_state_manager, body):
        mock_state_manager.load_csp_state.return_value = (_make_saved_state(), _make_metadata())
        return client.post("/api/fill/resume", json={"task_id": "task_opt", **body})

    def test_top_level_timeout_reaches_the_adapter(self, client, mock_state_manager, mock_adapter):
        # The regression itself: before #24 this silently became 300.
        resp = self._post(client, mock_state_manager, {"timeout": 30})

        assert resp.status_code == 200
        assert mock_adapter.fill_with_resume.call_args.kwargs["timeout_seconds"] == 30

    def test_nested_options_still_work(self, client, mock_state_manager, mock_adapter):
        # Compatibility: backend/tests/integration/workflows/
        # test_pause_resume_workflow.py sends this shape.
        resp = self._post(client, mock_state_manager, {"options": {"timeout": 30}})

        assert resp.status_code == 200
        assert mock_adapter.fill_with_resume.call_args.kwargs["timeout_seconds"] == 30

    def test_top_level_wins_when_both_are_given(self, client, mock_state_manager, mock_adapter):
        resp = self._post(client, mock_state_manager, {"timeout": 30, "options": {"timeout": 300}})

        assert resp.status_code == 200
        assert mock_adapter.fill_with_resume.call_args.kwargs["timeout_seconds"] == 30

    def test_algorithm_and_min_score_are_accepted_top_level_too(self, client, mock_state_manager, mock_adapter):
        # Scoping the fix to `timeout` alone would leave two more silent-default
        # traps of the identical class inside the same route.
        resp = self._post(client, mock_state_manager, {"algorithm": "beam", "min_score": 55})

        assert resp.status_code == 200
        kwargs = mock_adapter.fill_with_resume.call_args.kwargs
        assert kwargs["algorithm"] == "beam"
        assert kwargs["min_score"] == 55

    def test_wordlists_are_accepted_top_level_too(self, client, mock_state_manager, mock_adapter, mocker):
        resolve = mocker.patch(
            "backend.api.pause_resume_routes.resolve_wordlist_paths_strict",
            return_value=(["/tmp/wl.txt"], []),
        )

        resp = self._post(client, mock_state_manager, {"wordlists": ["comprehensive"]})

        assert resp.status_code == 200
        resolve.assert_called_once_with(["comprehensive"])

    def test_unknown_top_level_key_is_logged_and_ignored_not_rejected(self, client, mock_state_manager, mock_adapter, caplog):
        # Deliberately not a 400: the defect is a silently-ignored parameter,
        # which accept-both already closes. Rejecting would be a behaviour
        # change on a route whose callers are not enumerated.
        with caplog.at_level(logging.WARNING, logger="backend.api.pause_resume_routes"):
            resp = self._post(client, mock_state_manager, {"timeuot": 30})

        assert resp.status_code == 200
        assert "timeuot" in caplog.text
        # The typo must not be smuggled into the options dict.
        assert mock_adapter.fill_with_resume.call_args.kwargs["timeout_seconds"] == 300


# ---------------------------------------------------------------------------
# GET /api/fill/state/<task_id>
# ---------------------------------------------------------------------------


class TestGetSavedState:
    def test_state_found_returns_200(self, client, mock_state_manager):
        saved = _make_saved_state(grid=[["A", ".", "#"]] * 3)
        meta = _make_metadata()
        info = {"task_id": "task_s1", "timestamp": "2025-12-26T10:00:00Z"}

        mock_state_manager.get_state_info.return_value = info
        mock_state_manager.load_csp_state.return_value = (saved, meta)

        resp = client.get("/api/fill/state/task_s1")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["task_id"] == "task_s1"
        assert "grid_preview" in data

    def test_state_not_found_returns_404(self, client, mock_state_manager):
        mock_state_manager.get_state_info.side_effect = FileNotFoundError("nope")

        resp = client.get("/api/fill/state/task_missing")
        data = resp.get_json()

        assert resp.status_code == 404
        assert "not found" in data["error"].lower()

    def test_state_includes_grid_preview(self, client, mock_state_manager, mock_grid):
        grid_data = [["C", "A", "T"], ["D", "O", "G"], [".", ".", "."]]
        saved = _make_saved_state(grid=grid_data)
        meta = _make_metadata()

        mock_state_manager.get_state_info.return_value = {"task_id": "task_gp"}
        mock_state_manager.load_csp_state.return_value = (saved, meta)

        resp = client.get("/api/fill/state/task_gp")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["grid_preview"] == grid_data


# ---------------------------------------------------------------------------
# DELETE /api/fill/state/<task_id>
# ---------------------------------------------------------------------------


class TestDeleteSavedState:
    def test_delete_existing_returns_200(self, client, mock_state_manager):
        mock_state_manager.delete_state.return_value = True

        resp = client.delete("/api/fill/state/task_d1")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True

    def test_delete_missing_returns_404(self, client, mock_state_manager):
        mock_state_manager.delete_state.return_value = False

        resp = client.delete("/api/fill/state/task_gone")
        data = resp.get_json()

        assert resp.status_code == 404
        assert "not found" in data["error"].lower()

    def test_delete_message_includes_task_id(self, client, mock_state_manager):
        mock_state_manager.delete_state.return_value = True

        resp = client.delete("/api/fill/state/task_d3")
        data = resp.get_json()

        assert "task_d3" in data["message"]


# ---------------------------------------------------------------------------
# GET /api/fill/states
# ---------------------------------------------------------------------------


class TestListSavedStates:
    def test_list_returns_states(self, client, mock_state_manager):
        states = [
            {"task_id": "t1", "slots_filled": 5},
            {"task_id": "t2", "slots_filled": 12},
        ]
        mock_state_manager.list_states.return_value = states

        resp = client.get("/api/fill/states")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["count"] == 2
        assert len(data["states"]) == 2

    def test_list_with_max_age_days(self, client, mock_state_manager):
        mock_state_manager.list_states.return_value = []

        resp = client.get("/api/fill/states?max_age_days=3")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["count"] == 0
        mock_state_manager.list_states.assert_called_once_with(max_age_days=3)

    def test_list_without_max_age(self, client, mock_state_manager):
        mock_state_manager.list_states.return_value = []

        client.get("/api/fill/states")

        mock_state_manager.list_states.assert_called_once_with(max_age_days=None)

    def test_list_empty_returns_zero_count(self, client, mock_state_manager):
        mock_state_manager.list_states.return_value = []

        resp = client.get("/api/fill/states")
        data = resp.get_json()

        assert data["count"] == 0
        assert data["states"] == []


# ---------------------------------------------------------------------------
# POST /api/fill/states/cleanup
# ---------------------------------------------------------------------------


class TestCleanupOldStates:
    def test_cleanup_returns_deleted_count(self, client, mock_state_manager):
        mock_state_manager.cleanup_old_states.return_value = 5

        resp = client.post("/api/fill/states/cleanup", json={"max_age_days": 14})
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["deleted_count"] == 5
        mock_state_manager.cleanup_old_states.assert_called_once_with(max_age_days=14)

    def test_cleanup_defaults_to_7_days(self, client, mock_state_manager):
        mock_state_manager.cleanup_old_states.return_value = 0

        resp = client.post("/api/fill/states/cleanup", json={})
        resp.get_json()

        assert resp.status_code == 200
        mock_state_manager.cleanup_old_states.assert_called_once_with(max_age_days=7)

    def test_cleanup_no_body_defaults_to_7(self, client, mock_state_manager):
        mock_state_manager.cleanup_old_states.return_value = 0

        # Send valid empty JSON object (not empty string)
        resp = client.post("/api/fill/states/cleanup", json={})

        assert resp.status_code == 200
        mock_state_manager.cleanup_old_states.assert_called_once_with(max_age_days=7)

    def test_cleanup_message_includes_count(self, client, mock_state_manager):
        mock_state_manager.cleanup_old_states.return_value = 3

        resp = client.post("/api/fill/states/cleanup", json={"max_age_days": 1})
        data = resp.get_json()

        assert "3" in data["message"]


# ---------------------------------------------------------------------------
# POST /api/fill/edit-summary
# ---------------------------------------------------------------------------


class TestEditSummary:
    def test_valid_request_returns_summary(self, client, mock_state_manager, edit_merger, mocker):
        saved = _make_saved_state()
        meta = _make_metadata()
        mock_state_manager.load_csp_state.return_value = (saved, meta)

        summary = {
            "filled_count": 3,
            "emptied_count": 1,
            "modified_count": 0,
            "new_words": ["CAT"],
            "removed_words": [],
        }
        mocker.patch.object(edit_merger, "get_edit_summary", return_value=summary)

        resp = client.post(
            "/api/fill/edit-summary",
            json={
                "task_id": "task_e1",
                "edited_grid": [["X", "Y", "Z"]] * 3,
            },
        )
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["filled_count"] == 3
        assert data["new_words"] == ["CAT"]

    def test_missing_task_id_returns_400(self, client):
        resp = client.post(
            "/api/fill/edit-summary",
            json={"edited_grid": [["A"]]},
        )
        data = resp.get_json()

        assert resp.status_code == 400
        assert "task_id" in data["error"]

    def test_missing_edited_grid_returns_400(self, client):
        resp = client.post(
            "/api/fill/edit-summary",
            json={"task_id": "task_e2"},
        )
        data = resp.get_json()

        assert resp.status_code == 400
        assert "edited_grid" in data["error"]

    def test_state_not_found_returns_404(self, client, mock_state_manager):
        mock_state_manager.load_csp_state.side_effect = FileNotFoundError("gone")

        resp = client.post(
            "/api/fill/edit-summary",
            json={"task_id": "task_nope", "edited_grid": [["A"]]},
        )
        data = resp.get_json()

        assert resp.status_code == 404
        assert "not found" in data["error"].lower()

    def test_empty_body_returns_400(self, client, mocker):
        mocker.patch(
            "backend.api.pause_resume_routes.handle_error",
            return_value=(json.dumps({"error": "bad request"}), 400),
        )

        resp = client.post(
            "/api/fill/edit-summary",
            data="",
            content_type="application/json",
        )

        assert resp.status_code == 400


class TestTaskIdValidation:
    """
    #21.3 — a task id taken from the JSON request body reaches a filesystem path.

    Flask's default URL converter cannot match "/", so ids arriving as a URL
    segment (/fill/pause/<task_id>, /fill/cancel/<task_id>, /fill/state/<task_id>)
    cannot express traversal. The body-sourced ones can: POST /api/fill/resume
    reads data["task_id"], and POST /api/fill reads data["resume_task_id"].

    Exploitability is limited — the target must already exist and parse as a valid
    state envelope, and writes always use a server-minted uuid — so this rejects
    the malformed id rather than claiming to close an exploit.
    """

    @pytest.mark.parametrize(
        "bad_id",
        [
            "../../../etc/passwd",
            "..",
            "sub/dir",
            "has space",
            "trailing.dot",
            "",
            "x" * 65,
        ],
    )
    def test_resume_rejects_malformed_task_id(self, client, bad_id):
        resp = client.post("/api/fill/resume", json={"task_id": bad_id})

        assert resp.status_code == 400, f"{bad_id!r} was not rejected"
        assert b"task_id" in resp.data

    @pytest.mark.parametrize("good_id", ["task_abc123", "resume_9f2c1a0b", "A-b_9", "x" * 64])
    def test_resume_accepts_wellformed_task_id(self, client, good_id):
        """A conforming id must get past validation — 404 (no such state), never 400."""
        resp = client.post("/api/fill/resume", json={"task_id": good_id})

        assert resp.status_code != 400, f"{good_id!r} was wrongly rejected"
