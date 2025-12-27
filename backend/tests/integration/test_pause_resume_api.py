"""
Integration tests for pause/resume API endpoints.

Tests the full pause/resume workflow including:
- Pausing active autofill
- Loading saved state
- Merging user edits
- Resuming from saved state
"""

import pytest
import json
import time
from pathlib import Path
from flask import Flask

from backend.app import create_app
from cli.src.fill.state_manager import StateManager, CSPState
from cli.src.core.grid import Grid


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
        grid.set_letter(0, 1, 'T')
        grid.set_letter(0, 2, 'E')
        grid.set_letter(0, 3, 'S')
        grid.set_letter(0, 4, 'T')

        # Create CSP state
        csp_state = CSPState(
            grid_dict=grid.to_dict(),
            domains={
                0: ['TEST', 'WORD'],
                1: ['ALPHA', 'BRAVO']
            },
            constraints={
                0: [[1, 0, 1]],
                1: [[0, 1, 0]]
            },
            used_words=['TEST'],
            slot_id_map={
                '[0, 1, "across"]': 0,
                '[0, 1, "down"]': 1
            },
            slot_list=[
                {'row': 0, 'col': 1, 'direction': 'across', 'length': 4},
                {'row': 0, 'col': 1, 'direction': 'down', 'length': 5}
            ],
            slots_sorted=[0, 1],
            current_slot_index=1,
            iteration_count=100,
            locked_slots=[0],
            timestamp='2025-12-26T10:00:00Z',
            random_seed=42
        )

        # Save state
        state_manager = StateManager(storage_dir=tmp_path)
        task_id = "test_task_001"
        metadata = {
            'min_score': 50,
            'timeout': 300,
            'grid_size': [11, 11],
            'total_slots': 20,
            'slots_filled': 10
        }

        state_manager.save_csp_state(
            task_id=task_id,
            csp_state=csp_state,
            metadata=metadata,
            compress=True
        )

        return task_id, tmp_path, csp_state, metadata

    def test_pause_request(self, client):
        """Test requesting pause for a task."""
        task_id = "test_pause_task"

        response = client.post(f'/api/fill/pause/{task_id}')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['task_id'] == task_id
        assert 'message' in data

    def test_get_saved_state(self, client, sample_state, monkeypatch):
        """Test retrieving saved state info."""
        task_id, tmp_path, csp_state, metadata = sample_state

        # Monkeypatch the STATE_STORAGE_DIR
        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        response = client.get(f'/api/fill/state/{task_id}')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['task_id'] == task_id
        assert data['algorithm'] == 'csp'
        assert data['slots_filled'] == 10
        assert data['total_slots'] == 20
        assert data['grid_size'] == [11, 11]
        assert 'grid_preview' in data
        assert 'timestamp' in data

    def test_get_nonexistent_state(self, client, tmp_path, monkeypatch):
        """Test retrieving state that doesn't exist."""
        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        response = client.get('/api/fill/state/nonexistent')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_delete_saved_state(self, client, sample_state, monkeypatch):
        """Test deleting saved state."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        # Verify state exists
        response = client.get(f'/api/fill/state/{task_id}')
        assert response.status_code == 200

        # Delete state
        response = client.delete(f'/api/fill/state/{task_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify state no longer exists
        response = client.get(f'/api/fill/state/{task_id}')
        assert response.status_code == 404

    def test_list_saved_states(self, client, sample_state, monkeypatch):
        """Test listing all saved states."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        response = client.get('/api/fill/states')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'states' in data
        assert 'count' in data
        assert data['count'] >= 1

        # Check our state is in the list
        task_ids = [s['task_id'] for s in data['states']]
        assert task_id in task_ids

    def test_list_states_with_max_age(self, client, sample_state, monkeypatch):
        """Test listing states with max age filter."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        # List states newer than 7 days
        response = client.get('/api/fill/states?max_age_days=7')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'states' in data

    def test_cleanup_old_states(self, client, tmp_path, monkeypatch):
        """Test cleaning up old state files."""
        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        # Create an old state file
        old_file = tmp_path / "old_task.json.gz"
        old_file.touch()

        # Set modification time to 8 days ago
        import os
        old_time = time.time() - (8 * 24 * 3600)
        os.utime(old_file, (old_time, old_time))

        # Run cleanup
        response = client.post(
            '/api/fill/states/cleanup',
            data=json.dumps({'max_age_days': 7}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['deleted_count'] >= 1

    def test_resume_without_edits(self, client, sample_state, monkeypatch):
        """Test resuming from saved state without user edits."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        # Resume without edits
        response = client.post(
            '/api/fill/resume',
            data=json.dumps({
                'task_id': task_id,
                'options': {
                    'min_score': 50,
                    'timeout': 300
                }
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert 'new_task_id' in data
        assert data['original_task_id'] == task_id
        assert data['new_task_id'].startswith('resume_')

    def test_resume_with_edits(self, client, sample_state, monkeypatch):
        """Test resuming with user edits."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        # Create edited grid (same structure, different letters)
        edited_grid = csp_state.grid_dict['grid']

        # Resume with edits
        response = client.post(
            '/api/fill/resume',
            data=json.dumps({
                'task_id': task_id,
                'edited_grid': edited_grid,
                'options': {
                    'min_score': 50,
                    'timeout': 300
                }
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert 'new_task_id' in data

    def test_resume_missing_task_id(self, client):
        """Test resume with missing task_id."""
        response = client.post(
            '/api/fill/resume',
            data=json.dumps({
                'options': {}
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_resume_nonexistent_state(self, client, tmp_path, monkeypatch):
        """Test resume with nonexistent state."""
        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        response = client.post(
            '/api/fill/resume',
            data=json.dumps({
                'task_id': 'nonexistent',
                'options': {}
            }),
            content_type='application/json'
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_edit_summary(self, client, sample_state, monkeypatch):
        """Test getting edit summary."""
        task_id, tmp_path, csp_state, metadata = sample_state

        import backend.api.pause_resume_routes as pr_routes
        monkeypatch.setattr(pr_routes, 'STATE_STORAGE_DIR', tmp_path)

        # Get original grid
        original_grid = csp_state.grid_dict['grid']

        # Create edited grid (add a letter)
        edited_grid = [row.copy() if isinstance(row, list) else row for row in original_grid]

        # Request edit summary
        response = client.post(
            '/api/fill/edit-summary',
            data=json.dumps({
                'task_id': task_id,
                'edited_grid': edited_grid
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'filled_count' in data
        assert 'emptied_count' in data
        assert 'modified_count' in data
        assert 'new_words' in data
        assert 'removed_words' in data

    def test_edit_summary_missing_fields(self, client):
        """Test edit summary with missing required fields."""
        response = client.post(
            '/api/fill/edit-summary',
            data=json.dumps({
                'task_id': 'test'
                # Missing edited_grid
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestEditMerger:
    """Test EditMerger functionality."""

    @pytest.fixture
    def simple_grid_state(self):
        """Create simple grid and state for testing."""
        grid = Grid(11)
        grid.set_black_square(0, 0)

        csp_state = CSPState(
            grid_dict=grid.to_dict(),
            domains={
                0: ['WORD', 'TEST'],
                1: ['GRID', 'CELL']
            },
            constraints={
                0: [[1, 0, 0]],
                1: [[0, 0, 0]]
            },
            used_words=[],
            slot_id_map={
                '[0, 1, "across"]': 0,
                '[1, 0, "down"]': 1
            },
            slot_list=[
                {'row': 0, 'col': 1, 'direction': 'across', 'length': 4},
                {'row': 1, 'col': 0, 'direction': 'down', 'length': 4}
            ],
            slots_sorted=[0, 1],
            current_slot_index=0,
            iteration_count=50,
            locked_slots=[],
            timestamp='2025-12-26T10:00:00Z'
        )

        return grid, csp_state

    def test_merge_no_edits(self, simple_grid_state):
        """Test merging when no edits were made."""
        from backend.core.edit_merger import EditMerger

        grid, csp_state = simple_grid_state
        merger = EditMerger()

        # Same grid, no edits
        updated_state = merger.merge_edits(
            saved_state=csp_state,
            edited_grid_dict=grid.to_dict()
        )

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
        edited_grid.set_letter(0, 1, 'W')
        edited_grid.set_letter(0, 2, 'O')
        edited_grid.set_letter(0, 3, 'R')
        edited_grid.set_letter(0, 4, 'D')

        updated_state = merger.merge_edits(
            saved_state=csp_state,
            edited_grid_dict=edited_grid.to_dict()
        )

        # Filled slot should now be locked
        assert 0 in updated_state.locked_slots
        # WORD should be in used_words
        assert 'WORD' in updated_state.used_words


    def test_get_edit_summary(self, simple_grid_state):
        """Test getting summary of edits."""
        from backend.core.edit_merger import EditMerger

        grid, csp_state = simple_grid_state
        merger = EditMerger()

        # Edit grid: fill first slot
        edited_grid = Grid(11)
        edited_grid.set_black_square(0, 0)
        edited_grid.set_letter(0, 1, 'T')
        edited_grid.set_letter(0, 2, 'E')
        edited_grid.set_letter(0, 3, 'S')
        edited_grid.set_letter(0, 4, 'T')

        summary = merger.get_edit_summary(
            saved_grid_dict=grid.to_dict(),
            edited_grid_dict=edited_grid.to_dict(),
            slot_list=csp_state.slot_list,
            slot_id_map=csp_state.slot_id_map
        )

        assert 'filled_count' in summary
        assert 'emptied_count' in summary
        assert 'new_words' in summary
        assert summary['filled_count'] >= 0
