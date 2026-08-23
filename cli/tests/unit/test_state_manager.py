"""
Unit tests for StateManager - pause/resume state serialization.
"""

import gzip
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from cli.src.core.grid import Grid
from cli.src.fill.autofill import Autofill
from cli.src.fill.state_manager import CSPState, StateManager
from cli.src.fill.word_list import WordList


class TestStateManager:
    """Test StateManager serialization/deserialization."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for state files."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path)

    @pytest.fixture
    def state_manager(self, temp_dir):
        """Create StateManager with temp directory."""
        return StateManager(storage_dir=temp_dir)

    @pytest.fixture
    def simple_csp_state(self):
        """Create a simple CSP state for testing."""
        grid = Grid(15)
        grid.set_black_square(0, 0)  # Add some black squares
        grid.set_letter(0, 1, "A")  # Add some letters

        return CSPState(
            grid_dict=grid.to_dict(),
            domains={
                0: ["WORD", "TEST", "GRID"],
                1: ["ALPHA", "BRAVO"],
                2: ["CROSS", "WORDS"],
            },
            constraints={0: [[1, 0, 2], [2, 1, 0]], 1: [[0, 2, 0]], 2: [[0, 0, 1]]},
            used_words=["WORD", "ALPHA"],
            slot_id_map={
                '[0, 1, "across"]': 0,
                '[0, 1, "down"]': 1,
                '[1, 0, "across"]': 2,
            },
            slot_list=[
                {"row": 0, "col": 1, "direction": "across", "length": 4},
                {"row": 0, "col": 1, "direction": "down", "length": 5},
                {"row": 1, "col": 0, "direction": "across", "length": 5},
            ],
            slots_sorted=[0, 1, 2],
            current_slot_index=1,
            iteration_count=150,
            locked_slots=[0],
            timestamp=datetime.now().isoformat(),
            random_seed=42,
        )

    def test_save_csp_state_compressed(self, state_manager, simple_csp_state, temp_dir):
        """Test saving CSP state with compression."""
        task_id = "test_task_001"
        metadata = {
            "min_score": 50,
            "timeout": 300,
            "grid_size": [15, 15],
            "total_slots": 76,
        }

        # Save state
        file_path = state_manager.save_csp_state(
            task_id=task_id,
            csp_state=simple_csp_state,
            metadata=metadata,
            compress=True,
        )

        # Verify file exists
        assert file_path.exists()
        assert file_path.name == f"{task_id}.json.gz"

        # Verify it's gzipped
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            data = json.load(f)

        # Verify structure
        assert data["version"] == StateManager.VERSION
        assert data["algorithm"] == "csp"
        assert data["task_id"] == task_id
        assert "timestamp" in data
        assert data["metadata"] == metadata
        assert "state_data" in data

    def test_save_csp_state_uncompressed(self, state_manager, simple_csp_state, temp_dir):
        """Test saving CSP state without compression."""
        task_id = "test_task_002"
        metadata = {"test": "data"}

        # Save state
        file_path = state_manager.save_csp_state(
            task_id=task_id,
            csp_state=simple_csp_state,
            metadata=metadata,
            compress=False,
        )

        # Verify file exists
        assert file_path.exists()
        assert file_path.name == f"{task_id}.json"

        # Verify it's plain JSON
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["algorithm"] == "csp"
        assert data["task_id"] == task_id

    def test_load_csp_state_compressed(self, state_manager, simple_csp_state):
        """Test loading compressed CSP state."""
        task_id = "test_task_003"
        metadata = {"min_score": 60}

        # Save state
        state_manager.save_csp_state(
            task_id=task_id,
            csp_state=simple_csp_state,
            metadata=metadata,
            compress=True,
        )

        # Load state
        loaded_state, loaded_metadata = state_manager.load_csp_state(task_id)

        # Verify metadata
        assert loaded_metadata == metadata

        # Verify CSP state fields
        assert loaded_state.current_slot_index == simple_csp_state.current_slot_index
        assert loaded_state.iteration_count == simple_csp_state.iteration_count
        assert loaded_state.used_words == simple_csp_state.used_words
        assert loaded_state.locked_slots == simple_csp_state.locked_slots
        assert loaded_state.random_seed == simple_csp_state.random_seed

        # Verify domains (should be preserved as lists)
        assert loaded_state.domains[0] == simple_csp_state.domains[0]
        assert loaded_state.domains[1] == simple_csp_state.domains[1]

        # Verify grid can be reconstructed
        grid = Grid.from_dict(loaded_state.grid_dict)
        assert grid.size == 15

    def test_load_csp_state_uncompressed(self, state_manager, simple_csp_state):
        """Test loading uncompressed CSP state."""
        task_id = "test_task_004"
        metadata = {}

        # Save uncompressed
        state_manager.save_csp_state(
            task_id=task_id,
            csp_state=simple_csp_state,
            metadata=metadata,
            compress=False,
        )

        # Load state
        loaded_state, loaded_metadata = state_manager.load_csp_state(task_id)

        # Verify key fields
        assert loaded_state.current_slot_index == simple_csp_state.current_slot_index
        assert len(loaded_state.slot_list) == len(simple_csp_state.slot_list)

    def test_load_nonexistent_state(self, state_manager):
        """Test loading state that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            state_manager.load_csp_state("nonexistent_task")

    def _write_truncated_gz(self, state_manager, task_id, simple_csp_state):
        """Save a valid state then truncate the file mid-stream to simulate a torn read."""
        file_path = state_manager.save_csp_state(
            task_id=task_id, csp_state=simple_csp_state, metadata={"slots_filled": 1, "total_slots": 2}, compress=True
        )
        full_size = file_path.stat().st_size
        with open(file_path, "r+b") as f:
            f.truncate(full_size // 2)
        return file_path

    def test_read_state_data_on_truncated_gzip_raises_clean_value_error(self, state_manager, simple_csp_state):
        """A truncated .json.gz must surface the module's ValueError shape, not a raw EOFError."""
        task_id = "truncated_read_state_data"
        file_path = self._write_truncated_gz(state_manager, task_id, simple_csp_state)

        with pytest.raises(ValueError, match="Not a valid autofill state file"):
            state_manager.read_state_data(file_path)

    def test_get_state_info_on_truncated_gzip_raises_clean_value_error(self, state_manager, simple_csp_state):
        """get_state_info bypasses read_state_data internally; it must get the same guard."""
        task_id = "truncated_get_state_info"
        self._write_truncated_gz(state_manager, task_id, simple_csp_state)

        with pytest.raises(ValueError, match="Not a valid autofill state file"):
            state_manager.get_state_info(task_id)

    def test_load_csp_state_on_truncated_gzip_raises_clean_value_error(self, state_manager, simple_csp_state):
        """load_csp_state must not leak the raw EOFError from a torn read either."""
        task_id = "truncated_load_csp_state"
        self._write_truncated_gz(state_manager, task_id, simple_csp_state)

        with pytest.raises(ValueError, match="Not a valid autofill state file"):
            state_manager.load_csp_state(task_id)

    def test_save_csp_state_leaves_no_temp_file_behind(self, state_manager, simple_csp_state, temp_dir):
        """Atomic write (temp file + os.replace) must not leave a .tmp artifact after a successful save."""
        task_id = "atomic_write_cleanup"
        file_path = state_manager.save_csp_state(task_id=task_id, csp_state=simple_csp_state, metadata={}, compress=True)

        assert file_path.exists()
        leftovers = [p for p in temp_dir.iterdir() if p != file_path]
        assert leftovers == [], f"unexpected files left in storage dir: {leftovers}"

    def test_save_csp_state_cleans_up_temp_file_on_failed_replace(
        self, state_manager, simple_csp_state, temp_dir, monkeypatch
    ):
        """If os.replace() fails partway, the temp file must be removed, not orphaned."""
        import cli.src.fill.state_manager as state_manager_module

        def _boom(*args, **kwargs):
            raise OSError("simulated disk failure")

        monkeypatch.setattr(state_manager_module.os, "replace", _boom)

        task_id = "atomic_write_failure"
        with pytest.raises(OSError, match="simulated disk failure"):
            state_manager.save_csp_state(task_id=task_id, csp_state=simple_csp_state, metadata={}, compress=True)

        dest = temp_dir / f"{task_id}.json.gz"
        assert not dest.exists()
        leftovers = list(temp_dir.iterdir())
        assert leftovers == [], f"temp file was not cleaned up after failed replace: {leftovers}"

    def test_get_state_info(self, state_manager, simple_csp_state):
        """Test getting state info without full load."""
        task_id = "test_task_005"
        metadata = {"slots_filled": 38, "total_slots": 76, "grid_size": [15, 15]}

        # Save state
        state_manager.save_csp_state(
            task_id=task_id,
            csp_state=simple_csp_state,
            metadata=metadata,
            compress=True,
        )

        # Get info
        info = state_manager.get_state_info(task_id)

        # Verify info
        assert info["task_id"] == task_id
        assert info["algorithm"] == "csp"
        assert info["version"] == StateManager.VERSION
        assert info["slots_filled"] == 38
        assert info["total_slots"] == 76
        assert info["grid_size"] == [15, 15]
        assert info["iteration_count"] == 150
        assert "timestamp" in info

    def test_delete_state(self, state_manager, simple_csp_state, temp_dir):
        """Test deleting saved state."""
        task_id = "test_task_006"

        # Save state
        file_path = state_manager.save_csp_state(task_id=task_id, csp_state=simple_csp_state, metadata={}, compress=True)

        assert file_path.exists()

        # Delete state
        deleted = state_manager.delete_state(task_id)

        assert deleted is True
        assert not file_path.exists()

        # Delete again should return False
        deleted = state_manager.delete_state(task_id)
        assert deleted is False

    def test_list_states(self, state_manager, simple_csp_state):
        """Test listing all saved states."""
        # Save multiple states
        for i in range(3):
            task_id = f"test_task_00{i+7}"
            state_manager.save_csp_state(
                task_id=task_id,
                csp_state=simple_csp_state,
                metadata={"index": i},
                compress=True,
            )

        # List states
        states = state_manager.list_states()

        # Verify we got all states
        assert len(states) >= 3

        # Verify they're sorted by timestamp (newest first)
        timestamps = [s["timestamp"] for s in states]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_cleanup_old_states(self, state_manager, simple_csp_state, temp_dir):
        """Test cleanup of old state files."""
        task_id = "test_task_old"

        # Save state
        file_path = state_manager.save_csp_state(task_id=task_id, csp_state=simple_csp_state, metadata={}, compress=True)

        # Manually modify file timestamp to make it old
        import os
        import time

        old_time = time.time() - (8 * 24 * 3600)  # 8 days ago
        os.utime(file_path, (old_time, old_time))

        # Cleanup states older than 7 days
        deleted_count = state_manager.cleanup_old_states(max_age_days=7)

        assert deleted_count >= 1
        assert not file_path.exists()

    def test_capture_csp_state(self):
        """Test capturing state from Autofill instance."""
        # Create simple grid and autofill instance
        grid = Grid(11)
        word_list = WordList(words={"TEST": 100, "WORD": 90, "GRID": 85})

        autofill = Autofill(grid=grid, word_list=word_list, min_score=0, timeout=60)

        # Manually set some state
        autofill.domains = {0: {"TEST", "WORD"}, 1: {"GRID"}}
        autofill.constraints = {0: [[1, 0, 1]], 1: [[0, 1, 0]]}
        autofill.used_words = {"TEST"}
        autofill.slot_id_map = {(0, 0, "across"): 0, (0, 0, "down"): 1}
        autofill.slot_list = [
            {"row": 0, "col": 0, "direction": "across", "length": 4},
            {"row": 0, "col": 0, "direction": "down", "length": 4},
        ]
        autofill.iterations = 100
        autofill.random_seed = 123

        # Capture state
        csp_state = StateManager.capture_csp_state(autofill, current_slot_index=1, locked_slots={0})

        # Verify captured state
        assert csp_state.current_slot_index == 1
        assert csp_state.iteration_count == 100
        assert csp_state.random_seed == 123
        assert csp_state.used_words == ["TEST"]
        assert csp_state.locked_slots == [0]
        assert 0 in csp_state.domains
        assert "TEST" in csp_state.domains[0] or "WORD" in csp_state.domains[0]

    def test_restore_to_autofill(self, simple_csp_state):
        """Test restoring state into Autofill instance."""
        # Create empty autofill instance
        grid = Grid(15)
        word_list = WordList(words={"TEST": 100})

        autofill = Autofill(grid=grid, word_list=word_list, min_score=0, timeout=60)

        # Restore state
        StateManager.restore_to_autofill(autofill, simple_csp_state)

        # Verify state was restored
        assert autofill.iterations == simple_csp_state.iteration_count
        assert autofill.random_seed == simple_csp_state.random_seed
        assert autofill.used_words == set(simple_csp_state.used_words)

        # Verify domains restored as sets
        assert isinstance(autofill.domains[0], set)
        assert "WORD" in autofill.domains[0]

        # Verify grid restored
        assert autofill.grid.size == 15

    def test_round_trip_serialization(self, state_manager, simple_csp_state):
        """Test full round-trip: save -> load -> restore."""
        task_id = "test_task_roundtrip"
        metadata = {"test": "roundtrip"}

        # Save state
        state_manager.save_csp_state(
            task_id=task_id,
            csp_state=simple_csp_state,
            metadata=metadata,
            compress=True,
        )

        # Load state
        loaded_state, loaded_metadata = state_manager.load_csp_state(task_id)

        # Verify metadata
        assert loaded_metadata == metadata

        # Restore to autofill instance
        grid = Grid(15)
        word_list = WordList(words={"WORD": 100, "TEST": 90})

        autofill = Autofill(grid=grid, word_list=word_list)
        StateManager.restore_to_autofill(autofill, loaded_state)

        # Verify critical state preserved
        assert autofill.iterations == simple_csp_state.iteration_count
        assert autofill.used_words == set(simple_csp_state.used_words)
        assert len(autofill.domains) == len(simple_csp_state.domains)
        assert len(autofill.constraints) == len(simple_csp_state.constraints)

    def test_large_domain_serialization(self, state_manager):
        """Test serialization with large domains."""
        grid = Grid(15)

        # Create state with large domains
        large_domains = {i: [f"WORD{j:04d}" for j in range(1000)] for i in range(10)}

        csp_state = CSPState(
            grid_dict=grid.to_dict(),
            domains=large_domains,
            constraints={},
            used_words=[],
            slot_id_map={},
            slot_list=[],
            slots_sorted=list(range(10)),
            current_slot_index=5,
            iteration_count=500,
            locked_slots=[],
            timestamp=datetime.now().isoformat(),
        )

        task_id = "test_task_large"
        metadata = {}

        # Save and load
        state_manager.save_csp_state(task_id=task_id, csp_state=csp_state, metadata=metadata, compress=True)

        loaded_state, _ = state_manager.load_csp_state(task_id)

        # Verify large domains preserved
        assert len(loaded_state.domains) == 10
        assert len(loaded_state.domains[0]) == 1000
        assert loaded_state.domains[5][500] == "WORD0500"


class TestPauseController:
    """Test PauseController for pause signaling."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for pause flags."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_pause_controller_basic(self, temp_dir):
        """Test basic pause controller functionality."""
        from cli.src.fill.pause_controller import PauseController

        task_id = "test_task_pause"
        controller = PauseController(task_id=task_id, pause_dir=temp_dir)

        # Initially not paused
        assert not controller.should_pause()
        assert not controller.is_paused()

        # Request pause
        controller.request_pause()

        # Should now be paused
        assert controller.should_pause()
        assert controller.is_paused()

        # Clear pause
        controller.clear_pause()

        # No longer paused
        assert not controller.should_pause()
        assert not controller.is_paused()

    def test_pause_controller_context_manager(self, temp_dir):
        """Test pause controller as context manager."""
        from cli.src.fill.pause_controller import PauseController

        task_id = "test_task_context"

        with PauseController(task_id=task_id, pause_dir=temp_dir) as controller:
            # Request pause during context
            controller.request_pause()
            assert controller.is_paused()

        # After context exit, pause should be cleaned up
        # Create new controller to check
        controller2 = PauseController(task_id=task_id, pause_dir=temp_dir)
        assert not controller2.is_paused()

    def test_pause_controller_rate_limiting(self, temp_dir):
        """should_pause() must not stat the filesystem on every call.

        It runs in solver inner loops. A previous version tracked
        _last_check_time and _check_interval but never applied them, so every
        iteration paid a stat(); the test that was meant to catch this only
        asserted isinstance(result, bool), which holds either way.
        """
        import time

        from cli.src.fill.pause_controller import PauseController

        task_id = "test_task_rate"
        controller = PauseController(task_id=task_id, pause_dir=temp_dir)

        calls = {"n": 0}
        real_exists = type(controller.pause_file).exists

        def counting_exists(self):
            calls["n"] += 1
            return real_exists(self)

        # Not paused: 100 rapid calls must collapse into a single filesystem check
        with patch.object(type(controller.pause_file), "exists", counting_exists):
            assert controller.should_pause() is False
            first = calls["n"]
            for _ in range(100):
                assert controller.should_pause() is False
            assert calls["n"] == first, f"expected the interval to gate the check, got {calls['n']} stats"

            # Past the interval, it checks again
            time.sleep(0.15)
            assert controller.should_pause() is False
            assert calls["n"] == first + 1

        # A locally requested pause is observed immediately, not after the interval
        controller.request_pause()
        assert controller.should_pause() is True

        # And clearing it is likewise observed immediately
        controller.clear_pause()
        assert controller.should_pause() is False
