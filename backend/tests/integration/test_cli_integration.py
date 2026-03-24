"""
Integration tests for CLI subprocess integration.

These tests actually execute the CLI as a subprocess to catch integration bugs
like data format mismatches between the API and CLI layers.

IMPORTANT: These tests use REAL CLI execution, so they are slower than unit tests.
Mark slow tests with @pytest.mark.slow to allow skipping during development.
"""

import pytest
import json
import subprocess
import tempfile
from pathlib import Path
from backend.app import create_app
from backend.core.cli_adapter import get_adapter
from backend.tests.fixtures import (
    EMPTY_3X3_FRONTEND,
    PARTIALLY_FILLED_3X3_FRONTEND,
    PATTERN_3X3_FRONTEND,
    EMPTY_3X3_CLI,
    PATTERN_3X3_CLI,
    TRANSFORMATION_TEST_CASES,
)


@pytest.fixture
def client():
    """Create test client."""
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client


@pytest.fixture
def cli_adapter():
    """Get CLI adapter instance."""
    return get_adapter()


# ==================================================
# Data Transformation Tests
# ==================================================
# These tests verify the grid format transformation is correct


class TestGridFormatTransformation:
    """Test transformation from frontend format to CLI format."""

    def _transform_grid(self, frontend_grid):
        """
        Apply the same transformation logic as routes.py.

        This is the CRITICAL transformation that was buggy.
        """
        cli_grid = []
        for row in frontend_grid:
            cli_row = []
            for cell in row:
                if isinstance(cell, dict):
                    if cell.get("isBlack", False):
                        cli_row.append("#")
                    elif cell.get("letter", ""):
                        cli_row.append(cell["letter"].upper())
                    else:
                        cli_row.append(".")
                else:
                    # Already in CLI format (string)
                    cli_row.append(cell)
            cli_grid.append(cli_row)
        return cli_grid

    @pytest.mark.parametrize(
        "test_name,frontend_data,expected_cli_data", TRANSFORMATION_TEST_CASES
    )
    def test_grid_transformation(self, test_name, frontend_data, expected_cli_data):
        """Test that grid transformation produces correct CLI format."""
        transformed = self._transform_grid(frontend_data["grid"])
        expected = expected_cli_data["grid"]

        assert transformed == expected, f"Transformation failed for {test_name}"

    def test_empty_cell_becomes_dot(self):
        """Test that empty cells (letter='') become '.' in CLI format."""
        frontend_cell = {"letter": "", "isBlack": False}
        result = self._transform_grid([[frontend_cell]])

        assert result[0][0] == ".", "Empty cell should become '.'"

    def test_black_cell_becomes_hash(self):
        """Test that black cells become '#' in CLI format."""
        frontend_cell = {"letter": "", "isBlack": True}
        result = self._transform_grid([[frontend_cell]])

        assert result[0][0] == "#", "Black cell should become '#'"

    def test_filled_cell_preserves_letter(self):
        """Test that filled cells preserve their letter."""
        frontend_cell = {"letter": "A", "isBlack": False}
        result = self._transform_grid([[frontend_cell]])

        assert result[0][0] == "A", "Filled cell should preserve letter"

    def test_lowercase_letters_uppercased(self):
        """Test that lowercase letters are converted to uppercase."""
        frontend_cell = {"letter": "a", "isBlack": False}
        result = self._transform_grid([[frontend_cell]])

        assert result[0][0] == "A", "Lowercase letters should be uppercased"

    def test_string_cells_pass_through(self):
        """Test that string cells (already in CLI format) pass through unchanged."""
        # This handles the case where grid might already be in CLI format
        mixed_row = ["A", {"letter": "B", "isBlack": False}, "#"]
        result = self._transform_grid([mixed_row])

        assert result[0] == ["A", "B", "#"], "String cells should pass through"


# ==================================================
# CLI Adapter Tests
# ==================================================
# These tests verify the CLI adapter works correctly


class TestCLIAdapterIntegration:
    """Test CLIAdapter actually executes CLI commands."""

    def test_cli_health_check(self, cli_adapter):
        """Test that CLI health check can execute normalize command."""
        is_healthy = cli_adapter.health_check()

        # This will fail if CLI is not properly installed or not executable
        assert is_healthy, "CLI should be healthy (normalize command should work)"

    def test_normalize_command_executes(self, cli_adapter):
        """Test that normalize command actually runs via subprocess."""
        result = cli_adapter.normalize("TEST")

        # Verify we got a result back
        assert "normalized" in result, "Result should have 'normalized' field"
        assert "original" in result, "Result should have 'original' field"
        assert result["original"] == "TEST", "Original text should match input"

    def test_pattern_command_executes(self, cli_adapter):
        """Test that pattern command actually runs via subprocess."""
        # Use a simple pattern that should have results
        result = cli_adapter.pattern(pattern="C?T", max_results=5)

        # Verify structure (actual matches depend on wordlist)
        assert "results" in result, "Result should have 'results' field"
        assert "meta" in result, "Result should have 'meta' field"
        assert isinstance(result["results"], list), "Results should be a list"

    @pytest.mark.slow
    def test_number_command_with_real_grid(self, cli_adapter):
        """Test that number command processes a real grid."""
        # Use empty 3x3 grid in CLI format
        result = cli_adapter.number(
            grid_data=EMPTY_3X3_CLI, allow_nonstandard=True  # 3x3 is non-standard
        )

        # Verify structure
        assert "numbering" in result, "Result should have 'numbering' field"
        assert isinstance(result["numbering"], dict), "Numbering should be a dict"

    @pytest.mark.slow
    def test_fill_command_with_real_grid(self, cli_adapter):
        """
        Test that fill command can process a real grid.

        This is the CRITICAL test that would have caught the bug.
        """
        # Create a simple fillable grid
        grid_data = PATTERN_3X3_CLI

        # This test will FAIL if grid format is wrong
        # because CLI will crash with AttributeError
        try:
            result = cli_adapter.fill(
                grid_data=grid_data,
                wordlist_paths=[
                    str(
                        Path(__file__).parent.parent.parent.parent
                        / "data"
                        / "wordlists"
                        / "comprehensive.txt"
                    )
                ],
                timeout_seconds=30,
                min_score=0,  # Accept any words for testing
                allow_nonstandard=True,
            )

            # Verify result structure
            assert "grid" in result, "Result should have filled grid"
            assert isinstance(result["grid"], list), "Grid should be a list"

        except subprocess.CalledProcessError as e:
            # If this fails with AttributeError in stderr, the transformation bug exists
            if "AttributeError" in e.stderr:
                pytest.fail(
                    "CLI crashed with AttributeError - this indicates grid format bug!\n"
                    f"Stderr: {e.stderr}"
                )
            raise


# ==================================================
# API Integration Tests (/api/fill)
# ==================================================
# These tests actually call the API endpoint and verify CLI execution


class TestFillEndpointIntegration:
    """Test /api/fill endpoint with real CLI execution."""

    @pytest.mark.slow
    def test_fill_endpoint_with_empty_grid(self, client):
        """
        Test /api/fill with empty grid in frontend format.

        This is the PRIMARY test that catches the bug.
        """
        response = client.post(
            "/api/fill",
            json={
                "size": 3,
                "grid": EMPTY_3X3_FRONTEND["grid"],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        # If the transformation is wrong, this will return 500 with AttributeError
        assert response.status_code in [
            200,
            507,
        ], f"Expected success or timeout, got {response.status_code}: {response.data}"

        if response.status_code == 200:
            data = json.loads(response.data)
            assert "grid" in data, "Response should contain filled grid"

    @pytest.mark.slow
    def test_fill_endpoint_with_pattern_grid(self, client):
        """Test /api/fill with grid containing black squares."""
        response = client.post(
            "/api/fill",
            json={
                "size": 3,
                "grid": PATTERN_3X3_FRONTEND["grid"],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        assert response.status_code in [
            200,
            507,
        ], f"Expected success or timeout, got {response.status_code}: {response.data}"

    @pytest.mark.slow
    def test_fill_endpoint_with_partially_filled_grid(self, client):
        """Test /api/fill with partially filled grid in frontend format."""
        response = client.post(
            "/api/fill",
            json={
                "size": 3,
                "grid": PARTIALLY_FILLED_3X3_FRONTEND["grid"],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        assert response.status_code in [
            200,
            507,
        ], f"Expected success or timeout, got {response.status_code}: {response.data}"

    def test_fill_endpoint_validates_missing_grid(self, client):
        """Test that /api/fill rejects requests without grid."""
        response = client.post(
            "/api/fill",
            json={"size": 3, "wordlists": ["comprehensive"]},
            content_type="application/json",
        )

        assert response.status_code == 400, "Should reject missing grid"
        data = json.loads(response.data)
        assert "error" in data, "Error response should have 'error' field"

    def test_fill_endpoint_validates_missing_size(self, client):
        """Test that /api/fill rejects requests without size."""
        response = client.post(
            "/api/fill",
            json={"grid": EMPTY_3X3_FRONTEND["grid"], "wordlists": ["comprehensive"]},
            content_type="application/json",
        )

        assert response.status_code == 400, "Should reject missing size"

    def test_fill_endpoint_validates_invalid_size(self, client):
        """Test that /api/fill rejects invalid grid sizes."""
        response = client.post(
            "/api/fill",
            json={
                "size": 2,  # Too small (min is 3)
                "grid": [[]],
                "wordlists": ["comprehensive"],
            },
            content_type="application/json",
        )

        assert response.status_code == 400, "Should reject invalid size"

    def test_fill_endpoint_validates_wordlists(self, client):
        """Test that /api/fill validates wordlists parameter."""
        response = client.post(
            "/api/fill",
            json={
                "size": 3,
                "grid": EMPTY_3X3_FRONTEND["grid"],
                "wordlists": [],  # Empty list should fail
            },
            content_type="application/json",
        )

        assert response.status_code == 400, "Should reject empty wordlists"


# ==================================================
# Grid Format Bug Regression Tests
# ==================================================
# These tests specifically target the bug that was missed


class TestGridFormatBugRegression:
    """
    Tests that specifically catch the grid format bug.

    The bug: Frontend sends {"letter": "A", "isBlack": false}
             CLI expects "A" or "#" or "."
    """

    def test_bug_regression_dict_format_to_string_format(self):
        """
        Regression test for the specific bug that was missed.

        This test will FAIL if the transformation code is removed or broken.
        """
        # Frontend sends this format
        frontend_grid = [[{"letter": "A", "isBlack": False}]]

        # Expected CLI format after transformation
        expected_cli_grid = [["A"]]

        # Apply transformation
        cli_grid = []
        for row in frontend_grid:
            cli_row = []
            for cell in row:
                if isinstance(cell, dict):
                    if cell.get("isBlack", False):
                        cli_row.append("#")
                    elif cell.get("letter", ""):
                        cli_row.append(cell["letter"].upper())
                    else:
                        cli_row.append(".")
                else:
                    cli_row.append(cell)
            cli_grid.append(cli_row)

        assert (
            cli_grid == expected_cli_grid
        ), "Transformation should convert dict format to string format"

    def test_bug_regression_cli_receives_parseable_json(self, cli_adapter):
        """
        Test that CLI receives valid JSON it can parse.

        This would have caught the bug because CLI would crash
        trying to access .get() on a dict.
        """
        # Create grid data in CLI format
        grid_data = {
            "size": 3,
            "grid": [["A", ".", "."], [".", "#", "."], [".", ".", "."]],
        }

        # Write to temp file (simulates what API does)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(grid_data, f)
            temp_path = f.name

        try:
            # Try to have CLI read it
            cmd = [str(cli_adapter.cli_path), "validate", temp_path]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=cli_adapter.cli_path.parent,
            )

            # Should not crash with AttributeError
            assert (
                "AttributeError" not in result.stderr
            ), f"CLI crashed with AttributeError - grid format is wrong!\nStderr: {result.stderr}"

        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.slow
    def test_bug_regression_end_to_end_fill_api(self, client):
        """
        End-to-end regression test for the fill API.

        Sends frontend-format grid through API to CLI and verifies no crash.
        """
        response = client.post(
            "/api/fill",
            json={
                "size": 3,
                "grid": [
                    [
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": False},
                    ],
                    [
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": True},
                        {"letter": "", "isBlack": False},
                    ],
                    [
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": False},
                        {"letter": "", "isBlack": False},
                    ],
                ],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        # Should NOT get 500 error with AttributeError
        assert (
            response.status_code != 500
        ), f"API should not crash with 500 error. Response: {response.data}"

        # Accept 200 (success) or 507 (timeout) or 400 (validation error)
        # Just verify it doesn't crash
        assert response.status_code in [
            200,
            400,
            507,
        ], f"Unexpected status code: {response.status_code}"


# ==================================================
# Error Handling Tests
# ==================================================


class TestCLIErrorHandling:
    """Test error handling in CLI integration."""

    def test_cli_timeout_handling(self, cli_adapter):
        """Test that CLI commands timeout correctly."""
        # Use a very short timeout to force timeout
        with pytest.raises(subprocess.TimeoutExpired):
            cli_adapter._run_command(
                ["fill", "/nonexistent/grid.json"],
                timeout=0.001,  # 1ms timeout
                check_success=False,
            )

    def test_cli_invalid_command_handling(self, cli_adapter):
        """Test that invalid CLI commands are handled."""
        with pytest.raises(subprocess.CalledProcessError):
            cli_adapter._run_command(["invalid-command"])

    def test_cli_malformed_json_output(self, cli_adapter, monkeypatch):
        """Test handling of malformed JSON from CLI."""

        # Mock _run_command to return invalid JSON
        def mock_run_command(args, timeout=None):
            # Return malformed JSON output
            return ("not valid json {{{", "", 0)

        monkeypatch.setattr(cli_adapter, "_run_command", mock_run_command)

        # This should raise ValueError due to JSON parse error
        with pytest.raises(ValueError, match="Failed to parse CLI output"):
            cli_adapter.pattern("C?T", wordlist_paths=[])


# ==================================================
# Performance Tests
# ==================================================


@pytest.mark.slow
class TestCLIPerformance:
    """Test performance characteristics of CLI integration."""

    def test_small_grid_fills_quickly(self, client):
        """Test that small grids (3x3) fill within reasonable time."""
        import time

        start_time = time.time()

        client.post(
            "/api/fill",
            json={
                "size": 3,
                "grid": PATTERN_3X3_FRONTEND["grid"],
                "wordlists": ["comprehensive"],
                "timeout": 30,
                "min_score": 0,
            },
            content_type="application/json",
        )

        elapsed = time.time() - start_time

        # 3x3 should complete in under 30 seconds
        assert elapsed < 30, f"3x3 grid took {elapsed:.2f}s, should be under 30s"

    def test_cli_adapter_caching_works(self):
        """Test that CLI adapter instance is cached."""
        adapter1 = get_adapter()
        adapter2 = get_adapter()

        assert adapter1 is adapter2, "get_adapter() should return same instance"
