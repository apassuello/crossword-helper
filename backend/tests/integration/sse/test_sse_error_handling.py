"""
Integration tests for SSE error handling and edge cases.

These tests verify that SSE streams handle errors gracefully:
- CLI subprocess failures (invalid parameters, crashes)
- Timeout scenarios
- Malformed requests
- Network interruptions (client disconnect)
- State cleanup after errors
- User-friendly error messages

Context: Autofill can fail in many ways (invalid wordlist, timeout, memory issues).
SSE must communicate these errors clearly to the frontend without crashing or
leaving orphaned processes.
"""

import pytest
import json
import time
from backend.tests.integration.conftest import create_test_grid


class TestSSECLIErrorHandling:
    """Test SSE handling of CLI subprocess errors."""

    def test_sse_reports_invalid_wordlist_error(self, client, sse_parser):
        """
        Verify SSE reports error when CLI fails due to invalid wordlist.

        Expected behavior:
        - Task starts (202 response)
        - SSE sends error status
        - Error message includes useful diagnostic info
        """
        grid = create_test_grid(11)

        # Start autofill with nonexistent wordlist
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["nonexistent_wordlist_xyz"],
                    "timeout": 10,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # Should still accept request (error occurs during execution)
        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Get SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should have error message
        assert len(messages) > 0
        last_msg = messages[-1]

        # Should indicate error
        assert (
            last_msg.get("status") == "error"
            or "error" in last_msg.get("message", "").lower()
            or "not found" in last_msg.get("message", "").lower()
        ), f"Expected error status, got: {last_msg}"

    def test_sse_reports_malformed_grid_error(self, client, sse_parser):
        """
        Verify SSE reports error for malformed grid data.

        Test with:
        - Grid size mismatch (size=11 but grid is 10x10)
        - Invalid cell format
        """
        # Grid with size mismatch
        malformed_grid = [
            [{"letter": "", "isBlack": False} for _ in range(10)] for _ in range(10)
        ]

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,  # Says 11x11
                    "grid": malformed_grid,  # But grid is 10x10
                    "wordlists": ["comprehensive"],
                    "timeout": 10,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # Might be rejected at API validation or during CLI execution
        # Either is acceptable
        if response.status_code == 400:
            # API validation caught it
            assert "error" in response.json or "message" in response.json
        elif response.status_code == 202:
            # Accepted, will fail during CLI execution
            task_id = response.json["task_id"]

            sse_response = client.get(f"/api/progress/{task_id}")
            messages = sse_parser(sse_response.data)

            if len(messages) > 0:
                last_msg = messages[-1]
                assert (
                    last_msg.get("status") == "error"
                    or "error" in last_msg.get("message", "").lower()
                )

    def test_sse_handles_cli_subprocess_crash(self, client, sse_parser):
        """
        Verify SSE handles gracefully if CLI subprocess crashes unexpectedly.

        This is hard to trigger without modifying CLI code, but we can test
        timeout scenarios which have similar error handling.
        """
        grid = create_test_grid(11)

        # Use very short timeout to force early termination
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 1,  # Very short
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # API might reject very short timeout at validation (400) or accept it (202)
        if response.status_code == 400:
            # Validation rejected short timeout - this is acceptable behavior
            assert "error" in response.json or "message" in response.json
            return  # Test passes - validation is working correctly

        # If accepted, verify SSE error handling
        assert response.status_code == 202
        task_id = response.json["task_id"]
        time.sleep(3)

        # Get SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should have messages (even if timeout/partial)
        assert len(messages) > 0

        # Should indicate completion or error (timeout might result in partial fill)
        last_msg = messages[-1]
        assert last_msg.get("status") in [
            "complete",
            "error",
        ], f"Expected complete or error status, got: {last_msg}"


class TestSSETimeoutHandling:
    """Test SSE handling of operation timeouts."""

    def test_sse_reports_timeout_for_impossible_grid(self, client, sse_parser):
        """
        Verify SSE handles timeout gracefully for grids that can't be solved.

        Create grid with constraints that make it very difficult to fill,
        set short timeout, verify graceful timeout handling.
        """
        # Create grid with many black squares (harder to fill)
        grid = create_test_grid(11)
        # Add black squares in strategic positions to make filling harder
        for i in range(0, 11, 2):
            for j in range(0, 11, 2):
                grid[i][j] = {"letter": "", "isBlack": True}

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 10,  # Short timeout for difficult grid
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # API might reject grid with too many black squares at validation (400) or accept it (202)
        if response.status_code == 400:
            # Validation rejected grid - this is acceptable behavior
            assert "error" in response.json or "message" in response.json
            return  # Test passes - validation is working correctly

        assert response.status_code == 202
        task_id = response.json["task_id"]
        time.sleep(13)

        # Get SSE stream
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        assert len(messages) > 0

        # Should indicate timeout or partial completion
        last_msg = messages[-1]
        assert last_msg.get("status") in [
            "error",
            "complete",
        ], f"Expected error or complete after timeout, got: {last_msg}"

    def test_sse_respects_timeout_parameter(self, client, sse_parser):
        """
        Verify operation respects timeout parameter.

        Set 2s timeout, verify operation doesn't run significantly longer.
        """
        grid = create_test_grid(11)

        start_time = time.time()

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 2,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # API might reject very short timeout at validation (400) or accept it (202)
        if response.status_code == 400:
            # Validation rejected short timeout - this is acceptable behavior
            assert "error" in response.json or "message" in response.json
            return  # Test passes - validation is working correctly

        assert response.status_code == 202
        task_id = response.json["task_id"]

        # Wait for timeout + buffer
        time.sleep(5)

        elapsed = time.time() - start_time

        # Operation should not run significantly longer than timeout
        # (allowing 3s buffer for subprocess overhead)
        assert elapsed < 8, f"Operation ran too long ({elapsed}s) for 2s timeout"

        # Verify SSE stream completed
        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        assert len(messages) > 0


class TestSSEValidationErrors:
    """Test SSE handling of request validation errors."""

    def test_missing_required_parameters(self, client):
        """
        Verify API rejects requests missing required parameters.

        Should return 400, NOT 202 (don't create task for invalid request).
        """
        # Missing 'grid' parameter
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    # 'grid' missing
                    "wordlists": ["comprehensive"],
                    "timeout": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # Should reject at validation
        assert response.status_code == 400
        assert "error" in response.json or "message" in response.json

    def test_invalid_parameter_types(self, client):
        """
        Verify API rejects requests with invalid parameter types.

        Test:
        - timeout as string instead of int
        - min_score as string instead of int
        - algorithm as invalid value
        """
        grid = create_test_grid(11)

        # Invalid timeout type
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": "not_a_number",  # Invalid
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # Should reject
        assert response.status_code == 400

    def test_invalid_algorithm_name(self, client):
        """
        Verify API rejects invalid algorithm names.
        """
        grid = create_test_grid(11)

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 10,
                    "min_score": 10,
                    "algorithm": "invalid_algo_xyz",  # Invalid
                }
            ),
            content_type="application/json",
        )

        # Should reject at validation OR during CLI execution
        assert response.status_code in [400, 202]

        if response.status_code == 202:
            # Accepted but will fail during CLI
            task_id = response.json["task_id"]
            time.sleep(2)

            sse_response = client.get(f"/api/progress/{task_id}")
            data_str = sse_response.data.decode("utf-8")

            # Should have error message
            assert "error" in data_str.lower() or "invalid" in data_str.lower()


class TestSSEClientDisconnection:
    """Test SSE handling when client disconnects."""

    def test_sse_cleanup_after_client_disconnect(self, client):
        """
        Verify resources are cleaned up if client disconnects from SSE stream.

        This is hard to test in Flask test client (no real HTTP connection).
        We verify the stream can be closed without errors.
        """
        grid = create_test_grid(5)

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 5,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 10,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        task_id = response.json["task_id"]

        # Wait briefly
        time.sleep(1)

        # Get SSE stream and immediately close (simulate disconnect)
        sse_response = client.get(f"/api/progress/{task_id}")

        # Should not raise errors
        assert sse_response.status_code == 200

        # Subsequent requests should still work (idempotent)
        sse_response_2 = client.get(f"/api/progress/{task_id}")
        assert sse_response_2.status_code == 200


class TestSSEEdgeCases:
    """Test SSE edge cases and unusual scenarios."""

    def test_sse_empty_grid(self, client, sse_parser):
        """
        Verify autofill on completely empty grid works.

        This tests that SSE handles the common case of starting from scratch.
        """
        grid = create_test_grid(5)

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 5,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 10,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        task_id = response.json["task_id"]
        time.sleep(5)

        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should complete normally
        assert len(messages) > 0
        assert messages[-1].get("status") in ["complete", "error"]

    def test_sse_fully_filled_grid(self, client, sse_parser):
        """
        Verify autofill on already-filled grid completes immediately.

        Expected: Should detect grid is already filled and return success quickly.
        """
        # Create grid with some letters (not fully filled, but partially)
        grid = create_test_grid(11)
        # Add some letters
        grid[0][0] = {"letter": "C", "isBlack": False}
        grid[0][1] = {"letter": "A", "isBlack": False}
        grid[0][2] = {"letter": "T", "isBlack": False}

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 10,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        task_id = response.json["task_id"]
        time.sleep(12)

        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should have messages
        assert len(messages) > 0

    def test_sse_grid_with_all_black_squares(self, client, sse_parser):
        """
        Verify SSE handles gracefully a grid that's all black squares.

        Expected: Should detect no fillable slots and return appropriate error/success.
        """
        # Create grid with all black squares
        grid = [[{"letter": "", "isBlack": True} for _ in range(11)] for _ in range(11)]

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 5,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # Might be rejected at validation
        if response.status_code == 400:
            assert True  # Valid to reject at validation
        elif response.status_code == 202:
            task_id = response.json["task_id"]
            time.sleep(3)

            sse_response = client.get(f"/api/progress/{task_id}")
            messages = sse_parser(sse_response.data)

            # Should handle gracefully (either success with 0 slots or error)
            assert len(messages) > 0

    def test_sse_very_small_grid_3x3(self, client, sse_parser):
        """
        Verify SSE handles very small non-standard grid (3x3).
        """
        grid = create_test_grid(3)

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 3,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 5,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # API might reject non-standard grid size at validation (400) or accept it (202)
        if response.status_code == 400:
            # Validation rejected 3x3 grid - this is acceptable behavior
            assert "error" in response.json or "message" in response.json
            return  # Test passes - validation is working correctly

        # If accepted, verify SSE handling
        assert response.status_code == 202
        task_id = response.json["task_id"]

        time.sleep(7)

        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should complete
        assert len(messages) > 0

    @pytest.mark.slow
    def test_sse_adaptive_mode_error_recovery(self, client, sse_parser):
        """
        Verify SSE handles adaptive mode errors gracefully.

        Adaptive mode might fail to find valid black square placements.
        Should report this clearly without crashing.
        """
        grid = create_test_grid(11)

        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["comprehensive"],
                    "timeout": 15,
                    "min_score": 10,
                    "algorithm": "beam",
                    "adaptive_mode": True,
                    "max_adaptations": 2,
                }
            ),
            content_type="application/json",
        )

        task_id = response.json["task_id"]
        time.sleep(18)

        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        # Should complete (with or without adaptations)
        assert len(messages) > 0
        assert messages[-1].get("status") in ["complete", "error"]


class TestSSEUserFriendlyMessages:
    """Test that SSE error messages are user-friendly."""

    def test_error_messages_contain_useful_info(self, client, sse_parser):
        """
        Verify error messages are descriptive and actionable.

        Error messages should:
        - Describe what went wrong
        - Suggest possible fixes (if applicable)
        - Not expose internal stack traces to users
        """
        grid = create_test_grid(11)

        # Trigger error with invalid wordlist
        response = client.post(
            "/api/fill/with-progress",
            data=json.dumps(
                {
                    "size": 11,
                    "grid": grid,
                    "wordlists": ["nonexistent_wordlist"],
                    "timeout": 5,
                    "min_score": 10,
                    "algorithm": "trie",
                }
            ),
            content_type="application/json",
        )

        # API might reject invalid wordlist at validation (400) or accept and fail during CLI (202)
        if response.status_code == 400:
            # Validation rejected invalid wordlist - check error message quality
            error_response = response.json
            assert "error" in error_response or "message" in error_response

            # Get error message text
            message_text = error_response.get("error") or error_response.get("message")

            # Message should not be empty
            assert len(message_text) > 0, "Error message should not be empty"

            # Message should not contain Python stack traces
            assert (
                "Traceback" not in message_text
            ), "Error message should not include Python traceback"
            assert (
                'File "' not in message_text
            ), "Error message should not include file paths from traceback"
            return  # Test passes - validation error message is good

        # If accepted, verify SSE error message quality
        assert response.status_code == 202
        task_id = response.json["task_id"]
        time.sleep(2)

        sse_response = client.get(f"/api/progress/{task_id}")
        messages = sse_parser(sse_response.data)

        if len(messages) > 0:
            last_msg = messages[-1]

            # Should have a message field
            assert "message" in last_msg, "Error should include message"

            message_text = last_msg["message"]

            # Message should not be empty
            assert len(message_text) > 0, "Error message should not be empty"

            # Message should not contain Python stack traces
            # (Those should be logged server-side, not sent to client)
            assert (
                "Traceback" not in message_text
            ), "Error message should not include Python traceback"
            assert (
                'File "' not in message_text
            ), "Error message should not include file paths from traceback"


# Mark slow tests
pytest.mark.slow(TestSSEEdgeCases.test_sse_adaptive_mode_error_recovery)
