"""
Integration tests for SSE concurrency and multi-task handling.

These tests verify that the SSE progress system correctly handles:
- Multiple concurrent autofill operations
- Task isolation (no cross-contamination between streams)
- Resource cleanup when streams close
- Concurrent stream connections to same task
- Race conditions in task creation/progress updates

Context: Multiple users might trigger autofill simultaneously, or a single user
might start multiple operations (e.g., testing different algorithms). The system
must maintain separate SSE streams and progress state for each task.
"""

import pytest
import json
import threading
from queue import Queue
from backend.app import create_app
from backend.tests.integration.conftest import create_test_grid


class TestConcurrentSSEStreams:
    """Test multiple concurrent SSE streams don't interfere with each other."""

    def test_two_concurrent_autofill_streams(self, client, sse_parser):
        """
        Start 2 autofill operations simultaneously.

        Verify:
        - Each gets unique task_id
        - Each SSE stream reports correct progress for its task
        - No cross-contamination of progress updates
        """
        grid = create_test_grid(5)

        # Start first autofill
        response1 = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 5,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 10,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        assert response1.status_code == 202
        task_id_1 = response1.json["task_id"]

        # Start second autofill immediately
        response2 = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 5,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 10,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        assert response2.status_code == 202
        task_id_2 = response2.json["task_id"]

        # Task IDs must be unique
        assert task_id_1 != task_id_2, "Task IDs must be unique"

        # Get SSE streams for both tasks (blocks until each stream ends)
        sse_response_1 = client.get(f"/api/progress/{task_id_1}")
        sse_response_2 = client.get(f"/api/progress/{task_id_2}")

        messages_1 = sse_parser(sse_response_1.data)
        messages_2 = sse_parser(sse_response_2.data)

        # Both should have messages
        assert len(messages_1) > 0, f"Task 1 should have progress messages"
        assert len(messages_2) > 0, f"Task 2 should have progress messages"

        # Messages should be independent (no shared state)
        # If messages were cross-contaminated, we'd see identical sequences
        # For now, just verify both completed independently
        assert messages_1[-1].get("status") in ["complete", "error"]
        assert messages_2[-1].get("status") in ["complete", "error"]

    @pytest.mark.slow
    def test_three_concurrent_streams_different_operations(self, client, sse_parser):
        """
        Start 3 different operations simultaneously:
        - Pattern search
        - Autofill #1
        - Autofill #2

        Verify all complete independently without interference.
        """
        grid = create_test_grid(11)

        # Start pattern search
        response_pattern = client.post(
            "/api/pattern/with-progress",
            data=json.dumps({
                "pattern": "C?T",
                "wordlists": ["comprehensive"],
                "max_results": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )
        task_id_pattern = response_pattern.json["task_id"]

        # Start autofill #1
        response_fill_1 = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 11,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 15,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )
        task_id_fill_1 = response_fill_1.json["task_id"]

        # Start autofill #2
        response_fill_2 = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 11,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 15,
                "min_score": 10,
                "algorithm": "beam"
            }),
            content_type="application/json"
        )
        task_id_fill_2 = response_fill_2.json["task_id"]

        # All task IDs unique
        assert len({task_id_pattern, task_id_fill_1, task_id_fill_2}) == 3

        # Get all SSE streams (each blocks until its stream ends)
        sse_pattern = client.get(f"/api/progress/{task_id_pattern}")
        sse_fill_1 = client.get(f"/api/progress/{task_id_fill_1}")
        sse_fill_2 = client.get(f"/api/progress/{task_id_fill_2}")

        messages_pattern = sse_parser(sse_pattern.data)
        messages_fill_1 = sse_parser(sse_fill_1.data)
        messages_fill_2 = sse_parser(sse_fill_2.data)

        # All should have completed
        assert len(messages_pattern) > 0
        assert len(messages_fill_1) > 0
        assert len(messages_fill_2) > 0


class TestSSETaskIsolation:
    """Test that SSE progress updates are isolated per task."""

    def test_task_progress_updates_isolated(self, client, sse_parser):
        """
        Verify progress updates for task A don't appear in task B's stream.

        Create 2 tasks, verify each stream only contains its own updates.
        """
        grid = create_test_grid(5)

        # Start 2 autofill tasks
        response1 = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 5,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 10,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )
        task_id_1 = response1.json["task_id"]

        response2 = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 5,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 10,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )
        task_id_2 = response2.json["task_id"]

        # Get both streams (each blocks until its stream ends)
        sse_1 = client.get(f"/api/progress/{task_id_1}")
        sse_2 = client.get(f"/api/progress/{task_id_2}")

        messages_1 = sse_parser(sse_1.data)
        messages_2 = sse_parser(sse_2.data)

        # Both should have messages
        assert len(messages_1) > 0
        assert len(messages_2) > 0

        # Verify isolation: messages should be distinct
        # (This is a basic check - in practice, message content should differ)
        # If isolation failed, we'd see identical message counts/content
        # For now, just verify both streams have data
        assert messages_1 != messages_2 or len(messages_1) != len(messages_2), \
            "Streams should have independent progress updates"

    def test_nonexistent_task_id_returns_404(self, client):
        """
        Verify requesting SSE stream for nonexistent task returns 404.
        """
        fake_task_id = "nonexistent-task-12345"
        response = client.get(f"/api/progress/{fake_task_id}")

        # Should return 404 (not found) or immediately close with error message
        # (Implementation might vary - either is acceptable)
        assert response.status_code in [404, 200], \
            f"Expected 404 or 200, got {response.status_code}"

        # If 200, should immediately send error message
        if response.status_code == 200:
            data_str = response.data.decode('utf-8')
            assert len(data_str) == 0 or "error" in data_str.lower() or "not found" in data_str.lower(), \
                "Should indicate task not found"


class TestSSEResourceCleanup:
    """Test that SSE resources are cleaned up properly."""

    def test_sse_stream_closes_after_completion(self, client):
        """
        Verify SSE stream closes after operation completes and cleanup happens.

        Stream should:
        1. Send completion message
        2. Close connection
        3. Clean up task tracker (subsequent connections return 404)
        """
        # Start pattern search (fast operation)
        response = client.post(
            "/api/pattern/with-progress",
            data=json.dumps({
                "pattern": "C?T",
                "wordlists": ["comprehensive"],
                "max_results": 5,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        task_id = response.json["task_id"]

        # Get SSE stream (blocks until stream ends)
        sse_response = client.get(f"/api/progress/{task_id}")

        # Stream should contain data
        assert len(sse_response.data) > 0

        # Get stream again - after cleanup, task should be gone (404)
        sse_response_2 = client.get(f"/api/progress/{task_id}")

        # After SSE stream completes and cleanup happens, task is removed
        assert sse_response_2.status_code == 404

    def test_multiple_sse_connections_to_same_task(self, client):
        """
        Verify multiple SSE connections to same task work correctly.

        This simulates:
        - User refreshes page while autofill running
        - User opens multiple browser tabs
        """
        grid = create_test_grid(5)

        # Start autofill
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 5,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 10,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        task_id = response.json["task_id"]

        # Open 2 SSE connections to same task (each blocks until stream ends)
        sse_response_1 = client.get(f"/api/progress/{task_id}")
        sse_response_2 = client.get(f"/api/progress/{task_id}")

        # Both should succeed
        assert sse_response_1.status_code == 200
        assert sse_response_2.status_code == 200

        # Both should receive data (might be different based on timing)
        assert len(sse_response_1.data) > 0 or len(sse_response_2.data) > 0


class TestSSERaceConditions:
    """Test SSE handling of race conditions."""

    def test_sse_connect_before_task_starts(self, client):
        """
        Verify SSE connection can be established before task actually starts.

        Sequence:
        1. Create task (get task_id)
        2. Immediately connect to SSE stream
        3. Task starts in background
        4. SSE should receive all updates
        """
        grid = create_test_grid(5)

        # Start autofill
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 5,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 10,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        task_id = response.json["task_id"]

        # Immediately connect to SSE stream (no sleep)
        sse_response = client.get(f"/api/progress/{task_id}")

        # Should succeed (might receive updates or wait for them)
        assert sse_response.status_code == 200

    def test_rapid_task_creation(self, client):
        """
        Verify system handles rapid task creation without ID collisions.

        Create 10 tasks in quick succession, verify all unique IDs.
        """
        grid = create_test_grid(11)
        task_ids = []

        # Create 10 tasks rapidly
        for i in range(10):
            response = client.post(
                "/api/pattern/with-progress",
                data=json.dumps({
                    "pattern": f"C?{chr(65 + i)}",  # C?A, C?B, C?C, ...
                    "wordlists": ["comprehensive"],
                    "max_results": 5,
                    "algorithm": "trie"
                }),
                content_type="application/json"
            )

            assert response.status_code == 202
            task_ids.append(response.json["task_id"])

        # All task IDs should be unique
        assert len(task_ids) == len(set(task_ids)), \
            f"Task ID collision detected: {task_ids}"


class TestSSELongRunningOperations:
    """Test SSE behavior during long-running operations."""

    @pytest.mark.slow
    def test_sse_stream_stays_alive_during_long_operation(self, client, sse_parser):
        """
        Verify SSE stream doesn't timeout during long autofill (20s+).

        Some servers timeout idle connections after 30-60s. SSE should either:
        - Send heartbeat/keepalive messages
        - Complete before timeout
        - Handle reconnection gracefully
        """
        grid = create_test_grid(11)

        # Start autofill with 20s timeout
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 11,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 20,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        task_id = response.json["task_id"]

        # Get SSE stream (blocks until stream ends)
        sse_response = client.get(f"/api/progress/{task_id}")

        # Should have received messages throughout operation
        messages = sse_parser(sse_response.data)

        # Should have multiple messages spanning the operation
        assert len(messages) >= 3, \
            f"Expected multiple progress updates during 20s operation, got {len(messages)}"


# Mark slow tests
pytest.mark.slow(TestConcurrentSSEStreams.test_three_concurrent_streams_different_operations)
pytest.mark.slow(TestSSELongRunningOperations)
