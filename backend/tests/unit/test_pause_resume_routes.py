"""Unit tests for pause/resume API routes."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


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
    mock_cls = mocker.patch(
        "cli.src.fill.pause_controller.PauseController",
        return_value=mock_pc,
    )
    return mock_cls, mock_pc


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
        mock_cls.assert_called_once_with(task_id="task_abc")
        mock_pc.request_pause.assert_called_once()

    def test_pause_calls_request_pause(self, client, mock_pause_controller):
        _, mock_pc = mock_pause_controller

        client.post("/api/fill/pause/task_xyz")

        mock_pc.request_pause.assert_called_once()

    def test_pause_exception_returns_error(self, client, mocker):
        mocker.patch(
            "cli.src.fill.pause_controller.PauseController",
            side_effect=RuntimeError("disk full"),
        )
        mock_handle = mocker.patch(
            "backend.api.pause_resume_routes.handle_error",
            return_value=(json.dumps({"error": "fail"}), 500),
        )

        resp = client.post("/api/fill/pause/task_err")

        assert resp.status_code == 500
        mock_handle.assert_called_once()


# ---------------------------------------------------------------------------
# POST /api/fill/cancel/<task_id>
# ---------------------------------------------------------------------------


class TestCancelAutofill:
    def test_cancel_returns_200(self, client, mock_pause_controller, mocker):
        mocker.patch(
            "backend.api.progress_routes.cleanup_process",
        )

        resp = client.post("/api/fill/cancel/task_c1")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["task_id"] == "task_c1"
        assert data["state_saved"] is True
        assert "cancelled" in data["message"].lower()

    def test_cancel_requests_pause_and_cleanup(self, client, mock_pause_controller, mocker):
        _, mock_pc = mock_pause_controller
        mock_cleanup = mocker.patch(
            "backend.api.progress_routes.cleanup_process",
        )

        client.post("/api/fill/cancel/task_c2")

        mock_pc.request_pause.assert_called_once()
        mock_cleanup.assert_called_once_with("task_c2")

    def test_cancel_exception_returns_error(self, client, mocker):
        mocker.patch(
            "cli.src.fill.pause_controller.PauseController",
            side_effect=RuntimeError("boom"),
        )
        mocker.patch(
            "backend.api.pause_resume_routes.handle_error",
            return_value=(json.dumps({"error": "fail"}), 500),
        )

        resp = client.post("/api/fill/cancel/task_err")

        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/fill/resume
# ---------------------------------------------------------------------------


class TestResumeAutofill:
    def test_resume_valid_request_no_edits(self, client, mock_state_manager):
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
        assert data["slots_filled"] == 10
        assert data["total_slots"] == 40
        mock_state_manager.save_csp_state.assert_called_once()

    def test_resume_with_edited_grid(self, client, mock_state_manager, edit_merger, mocker):
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

    def test_resume_saves_with_correct_metadata(self, client, mock_state_manager):
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

    def test_resume_no_options_defaults_to_empty(self, client, mock_state_manager):
        saved = _make_saved_state()
        meta = _make_metadata()
        mock_state_manager.load_csp_state.return_value = (saved, meta)

        resp = client.post("/api/fill/resume", json={"task_id": "task_r5"})
        resp.get_json()

        assert resp.status_code == 200
        call_kwargs = mock_state_manager.save_csp_state.call_args
        saved_meta = call_kwargs.kwargs.get("metadata") or call_kwargs[1].get("metadata")
        assert saved_meta["resume_options"] == {}


# ---------------------------------------------------------------------------
# GET /api/fill/state/<task_id>
# ---------------------------------------------------------------------------


class TestGetSavedState:
    def test_state_found_returns_200(self, client, mock_state_manager, mock_grid):
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
        mock_grid.from_dict.assert_called_once()

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
