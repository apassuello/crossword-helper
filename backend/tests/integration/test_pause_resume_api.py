"""
Integration tests for pause/resume API endpoints.

Tests the full pause/resume workflow including:
- Pausing active autofill
- Loading saved state
- Merging user edits
- Resuming from saved state
"""

import json
import time

import pytest

from backend.app import create_app
from backend.tests.response_diag import resp_diag
from cli.src.core.grid import Grid
from cli.src.fill.state_manager import CSPState, StateManager


class TestPauseResumeAPI:
    """Test pause/resume API endpoints."""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing."""
        app = create_app(testing=True)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def sample_state(self, tmp_path):
        """Create sample saved state for testing."""
        # Create simple grid
        grid = Grid(11)
        grid.set_black_square(0, 0)
        grid.set_letter(0, 1, "T")
        grid.set_letter(0, 2, "E")
        grid.set_letter(0, 3, "S")
        grid.set_letter(0, 4, "T")

        # Create CSP state
        csp_state = CSPState(
            grid_dict=grid.to_dict(),
            domains={0: ["TEST", "WORD"], 1: ["ALPHA", "BRAVO"]},
            constraints={0: [[1, 0, 1]], 1: [[0, 1, 0]]},
            used_words=["TEST"],
            slot_id_map={'[0, 1, "across"]': 0, '[0, 1, "down"]': 1},
            slot_list=[
                {"row": 0, "col": 1, "direction": "across", "length": 4},
                {"row": 0, "col": 1, "direction": "down", "length": 5},
            ],
            slots_sorted=[0, 1],
            current_slot_index=1,
            iteration_count=100,
            locked_slots=[0],
            timestamp="2025-12-26T10:00:00Z",
            random_seed=42,
        )

        # Save state
        state_manager = StateManager(storage_dir=tmp_path)
        task_id = "test_task_001"
        metadata = {
            "min_score": 50,
            "timeout": 300,
            "grid_size": [11, 11],
            "total_slots": 20,
            "slots_filled": 10,
        }

        state_manager.save_csp_state(task_id=task_id, csp_state=csp_state, metadata=metadata, compress=True)

        return task_id, tmp_path, csp_state, metadata

    @pytest.fixture
    def solvable_state(self, tmp_path):
        """
        Create a saved state whose resumed position actually solves.

        Unlike `sample_state` (a hand-rolled position with only 2 of the
        grid's slots represented in domains/slot_list -- a dead end that
        makes resume fall back to unwind-and-re-search, #9), this captures a
        real CSP checkpoint: a tiny plus-shaped grid (one 5-letter across
        slot and one 5-letter down slot crossing at their middle cell,
        everything else black) run through the actual Autofill setup
        (_initialize_csp + AC-3 + MCV sort) and captured at
        current_slot_index=0 -- the same state fill() itself would
        checkpoint from at the very start of a search. Exact-position resume
        then just continues that tiny, already-consistent search instead of
        exhausting the timeout budget.
        """
        from backend.core.wordlist_resolver import get_default_wordlist_paths
        from cli.src.fill.autofill import Autofill
        from cli.src.fill.trie_pattern_matcher import TriePatternMatcher
        from cli.src.fill.word_list import WordList

        # Same wordlist the resumed CLI subprocess resolves to by default
        # (the test doesn't pass an `options.wordlists`), loaded the same
        # way cli.py's `_load_wordlist_words` does.
        wordlist_path = get_default_wordlist_paths()[0]
        words = []
        with open(wordlist_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                words.append(line.split(";")[0].strip().upper())
        word_list = WordList(words)

        # Plus-shaped grid: a 5-letter across slot and a 5-letter down slot
        # crossing at their middle cell, everything else black.
        # enforce_symmetry=False because the default 180-degree symmetry
        # would mirror these black squares and destroy the shape.
        # min_score=50 (below, and in the resume request) needs slot
        # length >= 5 -- this wordlist's 3-letter words top out around
        # score 36 and would never pass the filter.
        grid = Grid(11)
        for row in range(11):
            for col in range(11):
                white = (row == 5 and 3 <= col <= 7) or (col == 5 and 3 <= row <= 7)
                if not white:
                    grid.set_black_square(row, col, enforce_symmetry=False)

        pattern_matcher = TriePatternMatcher(word_list)
        autofill = Autofill(grid, word_list, pattern_matcher, timeout=30, min_score=50, algorithm="trie")

        slots = grid.get_empty_slots()
        autofill._initialize_csp(slots)
        assert autofill._ac3(), "fixture grid must be AC-3 consistent before capture"
        autofill.slots_sorted = autofill._sort_slots_by_constraint(slots)

        csp_state = StateManager.capture_csp_state(autofill, current_slot_index=0, locked_slots=set())

        state_manager = StateManager(storage_dir=tmp_path)
        task_id = "test_task_solvable"
        metadata = {
            "min_score": 50,
            "timeout": 300,
            "grid_size": [11, 11],
            "total_slots": len(slots),
            "slots_filled": 0,
        }

        state_manager.save_csp_state(task_id=task_id, csp_state=csp_state, metadata=metadata, compress=True)

        return task_id, tmp_path, csp_state, metadata

    def test_pause_request(self, client):
        """Test requesting pause for a running task."""
        from cli.src.fill.pause_controller import PauseController

        task_id = "test_pause_task"

        # Simulate a live CLI fill for this task id (running marker with a
        # live pid) — pause requests are only accepted for running tasks
        controller = PauseController(task_id=task_id)
        controller.mark_running()
        try:
            response = client.post(f"/api/fill/pause/{task_id}")

            assert response.status_code == 200, resp_diag(response)
            data = json.loads(response.data)

            assert data["success"] is True
            assert data["task_id"] == task_id
            assert "message" in data
        finally:
            controller.clear_running()
            controller.clear_pause()

    def test_pause_request_unknown_task_returns_404(self, client):
        """Pausing a task that is not running returns a JSON 404."""
        response = client.post("/api/fill/pause/definitely_not_running_task")

        assert response.status_code == 404, resp_diag(response)
        data = json.loads(response.data)
        assert "error" in data

    def test_get_saved_state(self, client, sample_state, monkeypatch):
        """Test retrieving saved state info."""
        task_id, tmp_path, csp_state, metadata = sample_state

        # Monkeypatch the STATE_STORAGE_DIR
        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        response = client.get(f"/api/fill/state/{task_id}")

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)

        assert data["task_id"] == task_id
        assert data["algorithm"] == "csp"
        assert data["slots_filled"] == 10
        assert data["total_slots"] == 20
        assert data["grid_size"] == [11, 11]
        assert "grid_preview" in data
        assert "timestamp" in data

    def test_get_nonexistent_state(self, client, tmp_path, monkeypatch):
        """Test retrieving state that doesn't exist."""
        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        response = client.get("/api/fill/state/nonexistent")

        assert response.status_code == 404, resp_diag(response)
        data = json.loads(response.data)
        assert "error" in data

    def test_delete_saved_state(self, client, sample_state, monkeypatch):
        """Test deleting saved state."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        # Verify state exists
        response = client.get(f"/api/fill/state/{task_id}")
        assert response.status_code == 200, resp_diag(response)

        # Delete state
        response = client.delete(f"/api/fill/state/{task_id}")

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify state no longer exists
        response = client.get(f"/api/fill/state/{task_id}")
        assert response.status_code == 404, resp_diag(response)

    def test_list_saved_states(self, client, sample_state, monkeypatch):
        """Test listing all saved states."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        response = client.get("/api/fill/states")

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)

        assert "states" in data
        assert "count" in data
        assert data["count"] >= 1

        # Check our state is in the list
        task_ids = [s["task_id"] for s in data["states"]]
        assert task_id in task_ids

    def test_list_states_with_max_age(self, client, sample_state, monkeypatch):
        """Test listing states with max age filter."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        # List states newer than 7 days
        response = client.get("/api/fill/states?max_age_days=7")

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        assert "states" in data

    def test_cleanup_old_states(self, client, tmp_path, monkeypatch):
        """Test cleaning up old state files."""
        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        # Create an old state file
        old_file = tmp_path / "old_task.json.gz"
        old_file.touch()

        # Set modification time to 8 days ago
        import os

        old_time = time.time() - (8 * 24 * 3600)
        os.utime(old_file, (old_time, old_time))

        # Run cleanup
        response = client.post(
            "/api/fill/states/cleanup",
            data=json.dumps({"max_age_days": 7}),
            content_type="application/json",
        )

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)

        assert data["success"] is True
        assert data["deleted_count"] >= 1

    def test_resume_without_edits(self, client, solvable_state, monkeypatch):
        """Test resuming from saved state without user edits."""
        task_id, tmp_path, csp_state, metadata = solvable_state

        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        # Resume without edits.
        #
        # `solvable_state`'s saved position (unlike `sample_state`'s) actually
        # solves via exact-position resume, so this test's runtime is fixed
        # CLI startup plus a near-instant 2-slot search, not a budget-exhausting
        # search. timeout=30 is what a real solve would get -- it's not the
        # thing keeping this test fast. The dead-end fallback this used to
        # exercise (unwind-and-re-search, #9) is covered directly by
        # cli/tests/unit/test_autofill.py::TestResumeUnwinding, so this
        # integration test doesn't need to reach it -- its job is the HTTP seam.
        response = client.post(
            "/api/fill/resume",
            data=json.dumps({"task_id": task_id, "options": {"min_score": 50, "timeout": 30}}),
            content_type="application/json",
        )

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)

        assert data["success"] is True
        assert "new_task_id" in data
        assert data["original_task_id"] == task_id
        assert data["new_task_id"].startswith("resume_")

        # The fixture's whole point is a position that resolves rather than
        # exhausts the timeout budget -- assert that actually happened,
        # not just that the HTTP call returned.
        assert data["result"]["success"] is True
        assert data["slots_filled"] == data["total_slots"] == 2

    def test_resume_with_edits(self, client, sample_state, monkeypatch):
        """Test resuming with user edits."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        # Create edited grid (same structure, different letters)
        edited_grid = csp_state.grid_dict["grid"]

        # Resume with edits
        response = client.post(
            "/api/fill/resume",
            data=json.dumps(
                {
                    "task_id": task_id,
                    "edited_grid": edited_grid,
                    "options": {"min_score": 50, "timeout": 300},
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)

        assert data["success"] is True
        assert "new_task_id" in data

    def test_resume_missing_task_id(self, client):
        """Test resume with missing task_id."""
        response = client.post(
            "/api/fill/resume",
            data=json.dumps({"options": {}}),
            content_type="application/json",
        )

        assert response.status_code == 400, resp_diag(response)
        data = json.loads(response.data)
        assert "error" in data

    def test_resume_nonexistent_state(self, client, tmp_path, monkeypatch):
        """Test resume with nonexistent state."""
        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        response = client.post(
            "/api/fill/resume",
            data=json.dumps({"task_id": "nonexistent", "options": {}}),
            content_type="application/json",
        )

        assert response.status_code == 404, resp_diag(response)
        data = json.loads(response.data)
        assert "error" in data

    def test_get_edit_summary(self, client, sample_state, monkeypatch):
        """Test getting edit summary."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes

        monkeypatch.setattr(pr_routes, "STATE_STORAGE_DIR", tmp_path)

        # Get original grid
        original_grid = csp_state.grid_dict["grid"]

        # Create edited grid (add a letter)
        edited_grid = [row.copy() if isinstance(row, list) else row for row in original_grid]

        # Request edit summary
        response = client.post(
            "/api/fill/edit-summary",
            data=json.dumps({"task_id": task_id, "edited_grid": edited_grid}),
            content_type="application/json",
        )

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)

        assert "filled_count" in data
        assert "emptied_count" in data
        assert "modified_count" in data
        assert "new_words" in data
        assert "removed_words" in data

    def test_edit_summary_missing_fields(self, client):
        """Test edit summary with missing required fields."""
        response = client.post(
            "/api/fill/edit-summary",
            data=json.dumps(
                {
                    "task_id": "test"
                    # Missing edited_grid
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400, resp_diag(response)
        data = json.loads(response.data)
        assert "error" in data


class TestEditMerger:
    """Test EditMerger functionality."""

    @pytest.fixture
    def simple_grid_state(self):
        """Create simple grid and state for testing."""
        grid = Grid(11)
        grid.set_black_square(0, 0)

        csp_state = CSPState(
            grid_dict=grid.to_dict(),
            domains={0: ["WORD", "TEST"], 1: ["GRID", "CELL"]},
            constraints={0: [[1, 0, 0]], 1: [[0, 0, 0]]},
            used_words=[],
            slot_id_map={'[0, 1, "across"]': 0, '[1, 0, "down"]': 1},
            slot_list=[
                {"row": 0, "col": 1, "direction": "across", "length": 4},
                {"row": 1, "col": 0, "direction": "down", "length": 4},
            ],
            slots_sorted=[0, 1],
            current_slot_index=0,
            iteration_count=50,
            locked_slots=[],
            timestamp="2025-12-26T10:00:00Z",
        )

        return grid, csp_state

    def test_merge_no_edits(self, simple_grid_state):
        """Test merging when no edits were made."""
        from backend.core.edit_merger import EditMerger

        grid, csp_state = simple_grid_state
        merger = EditMerger()

        # Same grid, no edits
        updated_state = merger.merge_edits(saved_state=csp_state, edited_grid_dict=grid.to_dict())

        # State should be essentially unchanged
        assert updated_state.iteration_count == csp_state.iteration_count
        assert len(updated_state.locked_slots) == len(csp_state.locked_slots)

    def test_merge_with_filled_slot(self, simple_grid_state):
        """Test merging when user fills a slot."""
        from backend.core.edit_merger import EditMerger

        grid, csp_state = simple_grid_state
        merger = EditMerger()

        # Edit grid: fill first slot with "WORD"
        edited_grid = Grid(11)
        edited_grid.set_black_square(0, 0)
        edited_grid.set_letter(0, 1, "W")
        edited_grid.set_letter(0, 2, "O")
        edited_grid.set_letter(0, 3, "R")
        edited_grid.set_letter(0, 4, "D")

        updated_state = merger.merge_edits(saved_state=csp_state, edited_grid_dict=edited_grid.to_dict())

        # Filled slot should now be locked
        assert 0 in updated_state.locked_slots
        # WORD should be in used_words
        assert "WORD" in updated_state.used_words

    def test_get_edit_summary(self, simple_grid_state):
        """Test getting summary of edits."""
        from backend.core.edit_merger import EditMerger

        grid, csp_state = simple_grid_state
        merger = EditMerger()

        # Edit grid: fill first slot
        edited_grid = Grid(11)
        edited_grid.set_black_square(0, 0)
        edited_grid.set_letter(0, 1, "T")
        edited_grid.set_letter(0, 2, "E")
        edited_grid.set_letter(0, 3, "S")
        edited_grid.set_letter(0, 4, "T")

        summary = merger.get_edit_summary(
            saved_grid_dict=grid.to_dict(),
            edited_grid_dict=edited_grid.to_dict(),
            slot_list=csp_state.slot_list,
            slot_id_map=csp_state.slot_id_map,
        )

        assert "filled_count" in summary
        assert "emptied_count" in summary
        assert "new_words" in summary
        assert summary["filled_count"] >= 0
