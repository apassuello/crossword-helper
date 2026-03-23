"""
Integration tests for SSE (Server-Sent Events) message format compliance.

These tests verify that SSE streams follow the EventSource specification:
- Correct Content-Type header
- Proper message format (data: {...}\n\n)
- Message sequence integrity
- Progressive updates during long operations
- Error state handling

Context: SSE is used for real-time progress updates during autofill operations
that can take 30s-5min. These tests ensure the frontend can reliably consume
the event stream.
"""

import pytest
import json
import time
import threading
from backend.app import create_app


@pytest.fixture
def client():
    """Create Flask test client with SSE support."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sse_parser():
    """
    Parse SSE message format.

    SSE format spec:
    ```
    data: {"key": "value"}\n
    \n
    ```

    Returns a function that parses SSE stream into list of messages.
    """
    def parse_sse_stream(data_bytes):
        """
        Parse SSE stream bytes into list of message dicts.

        Args:
            data_bytes: Raw SSE stream data

        Returns:
            List of parsed JSON messages
        """
        messages = []
        data_str = data_bytes.decode('utf-8')

        # Split by double newline (message separator)
        for chunk in data_str.split('\n\n'):
            if not chunk.strip():
                continue

            # Extract data line
            for line in chunk.split('\n'):
                if line.startswith('data: '):
                    try:
                        message_json = line[6:]  # Remove "data: " prefix
                        messages.append(json.loads(message_json))
                    except json.JSONDecodeError as e:
                        # Invalid JSON - this is a test failure
                        pytest.fail(f"Invalid JSON in SSE message: {line}\nError: {e}")

        return messages

    return parse_sse_stream


def create_test_grid(size=11):
    """Helper to create empty grid for testing."""
    return [[{"letter": "", "isBlack": False} for _ in range(size)] for _ in range(size)]


class TestSSEMessageFormatCompliance:
    """Test SSE stream follows EventSource specification."""

    def test_sse_headers_correct(self, client):
        """
        Verify SSE endpoint returns correct headers.

        Required headers:
        - Content-Type: text/event-stream
        - Cache-Control: no-cache
        - Connection: keep-alive (implied by streaming)
        """
        # Start autofill to get task ID
        grid = create_test_grid(11)
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 11,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 15,  # Increased timeout to avoid validation rejection
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        # API might reject short timeout at validation (400) or accept it (202)
        if response.status_code == 400:
            # Validation rejected - skip header test (can't test headers without task)
            pytest.skip("Validation rejected parameters - cannot test SSE headers")

        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Connect to SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")

        # Verify headers
        assert sse_response.status_code == 200
        # Content-Type may include charset parameter
        assert "text/event-stream" in sse_response.headers["Content-Type"]
        assert sse_response.headers["Cache-Control"] == "no-cache"

        # Note: Connection header may not be explicitly set in test client,
        # but in production Flask handles this automatically for streaming responses

    def test_sse_message_format_valid_json(self, client, sse_parser):
        """
        Verify all SSE messages are valid JSON.

        Each message should be:
        data: {"key": "value"}\n\n
        """
        # Start pattern search (faster than autofill for testing)
        response = client.post(
            "/api/pattern/with-progress",
            data=json.dumps({
                "pattern": "C?T",
                "wordlists": ["comprehensive"],
                "max_results": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Wait briefly for task to start
        time.sleep(0.5)

        # Get SSE stream (will collect all messages until stream closes)
        sse_response = client.get(f"/api/progress/{task_id}")

        # Parse messages
        messages = sse_parser(sse_response.data)

        # Should have at least one message
        assert len(messages) > 0, "SSE stream should contain at least one message"

        # All messages should be valid dicts (already validated by parser)
        for msg in messages:
            assert isinstance(msg, dict), f"Message should be dict, got {type(msg)}"

    def test_sse_message_sequence_for_autofill(self, client, sse_parser):
        """
        Verify SSE messages follow expected sequence for autofill operation.

        Expected sequence:
        1. Initial message (progress=0-10, status='running')
        2. Progressive updates (progress increasing, status='running')
        3. Final message (progress=100 OR status='complete'/'error')
        """
        # Start autofill with small grid (fills in <1s)
        grid = create_test_grid(5)
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

        # Wait for operation to complete
        time.sleep(5)

        # Get SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should have multiple messages
        assert len(messages) >= 2, f"Expected multiple progress updates, got {len(messages)}"

        # First message should indicate start
        first_msg = messages[0]
        assert "progress" in first_msg or "message" in first_msg

        # Last message should indicate completion or error
        last_msg = messages[-1]
        assert last_msg.get("status") in ["complete", "error"] or last_msg.get("progress") == 100, \
            f"Final message should indicate completion, got: {last_msg}"

        # Progress should be monotonically increasing (or stay at 100)
        prev_progress = -1
        for msg in messages:
            if "progress" in msg:
                current_progress = msg["progress"]
                assert current_progress >= prev_progress, \
                    f"Progress should increase monotonically: {prev_progress} -> {current_progress}"
                prev_progress = current_progress

    def test_sse_message_contains_required_fields(self, client, sse_parser):
        """
        Verify SSE messages contain required fields.

        Each progress message should have:
        - progress (int, 0-100)
        - message (str)
        - status (str: 'running', 'complete', 'error')

        Optional fields:
        - data (dict with grid, slots_filled, etc.)
        """
        # Start pattern search
        response = client.post(
            "/api/pattern/with-progress",
            data=json.dumps({
                "pattern": "C?T",
                "wordlists": ["comprehensive"],
                "max_results": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        task_id = response.json["task_id"]
        time.sleep(1)  # Wait for completion

        # Get SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Verify each message has required fields
        for msg in messages:
            # At minimum, should have message and status
            assert "message" in msg or "progress" in msg, \
                f"Message missing required fields: {msg}"

            # If status present, should be valid
            if "status" in msg:
                assert msg["status"] in ["running", "complete", "error", "paused"], \
                    f"Invalid status: {msg['status']}"

            # If progress present, should be 0-100
            if "progress" in msg:
                assert 0 <= msg["progress"] <= 100, \
                    f"Progress out of range: {msg['progress']}"


class TestSSEProgressiveUpdates:
    """Test SSE provides progressive updates during long operations."""

    @pytest.mark.slow
    def test_sse_provides_intermediate_updates(self, client, sse_parser):
        """
        Verify SSE sends intermediate updates during autofill, not just start/end.

        For operations >5s, should receive updates every 1-2s.
        """
        # Start autofill with small grid (should take ~5-15s)
        grid = create_test_grid(11)
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

        # Wait for operation to complete
        time.sleep(25)

        # Get SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should have received multiple intermediate updates
        # (not just start + end)
        assert len(messages) >= 3, \
            f"Expected at least 3 messages (start, progress, end), got {len(messages)}"

        # Should have at least one message with status='running'
        running_messages = [m for m in messages if m.get("status") == "running"]
        assert len(running_messages) >= 1, \
            "Should have intermediate 'running' status messages"


class TestSSEErrorHandling:
    """Test SSE error state handling."""

    def test_sse_reports_cli_errors(self, client, sse_parser):
        """
        Verify SSE stream reports CLI errors gracefully.

        If CLI subprocess fails, SSE should:
        1. Send error status
        2. Include error message
        3. Close stream cleanly
        """
        # Start autofill with invalid parameters (should cause CLI error)
        grid = create_test_grid(11)
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 11,
                "grid": grid,
                "wordlists": ["nonexistent_wordlist"],  # Invalid wordlist
                "timeout": 10,
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        # Should still return 202 (task started)
        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Wait for error to occur
        time.sleep(2)

        # Get SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should have at least one message
        assert len(messages) > 0

        # Last message should indicate error
        last_msg = messages[-1]
        assert last_msg.get("status") == "error" or "error" in last_msg.get("message", "").lower(), \
            f"Expected error status, got: {last_msg}"

    def test_sse_handles_timeout(self, client, sse_parser):
        """
        Verify SSE handles operation timeout gracefully.

        If operation times out, SSE should:
        1. Send error or timeout status
        2. Include timeout message
        3. Close stream
        """
        # Start autofill with very short timeout (1s - will timeout)
        grid = create_test_grid(11)
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps({
                "size": 11,
                "grid": grid,
                "wordlists": ["comprehensive"],
                "timeout": 1,  # Very short timeout
                "min_score": 10,
                "algorithm": "trie"
            }),
            content_type="application/json"
        )

        # API might reject very short timeout at validation (400) or accept it (202)
        if response.status_code == 400:
            # Validation rejected short timeout - this is acceptable behavior
            assert "error" in response.json or "message" in response.json
            return  # Test passes - validation is working correctly

        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Wait for timeout to occur
        time.sleep(3)

        # Get SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should have messages
        assert len(messages) > 0

        # Should indicate timeout or partial completion
        # (Timeout might result in partial fill with status='complete' or 'error')
        last_msg = messages[-1]
        assert last_msg.get("status") in ["error", "complete"], \
            f"Expected error or complete status after timeout, got: {last_msg}"


class TestSSEDataPayload:
    """Test SSE data payload structure for autofill completion."""

    @pytest.mark.slow
    def test_sse_completion_includes_grid_data(self, client, sse_parser):
        """
        Verify SSE completion message includes filled grid data.

        Final message should include:
        - grid: Filled grid array
        - slots_filled: Number of slots filled
        - success: Boolean indicating completion
        """
        # Start autofill
        grid = create_test_grid(11)
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

        # Wait for completion
        time.sleep(25)

        # Get SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Find completion message
        completion_msg = messages[-1]

        # Should have grid data if successful
        if completion_msg.get("status") == "complete" and completion_msg.get("success"):
            # Check for grid data (might be in top-level or nested in 'data' field)
            has_grid_data = "grid" in completion_msg or (
                "data" in completion_msg and "grid" in completion_msg["data"]
            )
            assert has_grid_data, \
                f"Completion message should include grid data: {completion_msg.keys()}"


# Mark slow tests
pytest.mark.slow(TestSSEProgressiveUpdates)
pytest.mark.slow(TestSSEDataPayload.test_sse_completion_includes_grid_data)
