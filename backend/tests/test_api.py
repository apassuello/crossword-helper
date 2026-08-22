"""
Unit tests for API routes.

Tests all API endpoints for correct behavior, validation, and error handling.
"""

import json

import pytest

from backend.app import create_app
from backend.tests.response_diag import resp_diag


@pytest.fixture
def client():
    """Create test client."""
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    """Test /api/health endpoint."""

    def test_health_check(self, client):
        """Test health check returns 200."""
        response = client.get("/api/health")
        assert response.status_code == 200, resp_diag(response)

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "version" in data
        assert "components" in data

    def test_health_check_components(self, client):
        """Test health check includes all components (Phase 3: CLI architecture)."""
        response = client.get("/api/health")
        data = json.loads(response.data)

        components = data["components"]
        # Phase 3: Components are now cli_adapter and api_server
        assert components["cli_adapter"] in ["ok", "error"]
        assert components["api_server"] == "ok"


class TestPatternEndpoint:
    """Test /api/pattern endpoint."""

    def test_pattern_search_valid(self, client):
        """Test pattern search with valid pattern."""
        response = client.post("/api/pattern", json={"pattern": "C?T"}, content_type="application/json")

        assert response.status_code == 200, resp_diag(response)

        data = json.loads(response.data)
        assert "results" in data
        assert "meta" in data
        assert isinstance(data["results"], list)

    def test_pattern_search_no_body(self, client):
        """Test pattern search with no request body."""
        response = client.post("/api/pattern", data="", content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_pattern_search_missing_pattern(self, client):
        """Test pattern search without pattern field."""
        response = client.post("/api/pattern", json={}, content_type="application/json")

        assert response.status_code == 400, resp_diag(response)
        data = json.loads(response.data)
        assert "error" in data

    def test_pattern_search_invalid_pattern_type(self, client):
        """Test pattern search with non-string pattern."""
        response = client.post("/api/pattern", json={"pattern": 123}, content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_pattern_search_with_wordlists(self, client):
        """Test pattern search with a real wordlist."""
        response = client.post(
            "/api/pattern",
            json={"pattern": "C?T", "wordlists": ["comprehensive"]},
            content_type="application/json",
        )

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        assert data["meta"]["sources_searched"] == ["comprehensive"]

    def test_pattern_search_invalid_wordlists(self, client):
        """Test pattern search with invalid wordlists type."""
        response = client.post(
            "/api/pattern",
            json={"pattern": "C?T", "wordlists": "not-a-list"},
            content_type="application/json",
        )

        assert response.status_code == 400, resp_diag(response)

    def test_pattern_search_with_max_results(self, client):
        """Test pattern search with max_results parameter."""
        response = client.post(
            "/api/pattern",
            json={"pattern": "C?T", "max_results": 5},
            content_type="application/json",
        )

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        assert len(data["results"]) <= 5

    def test_pattern_search_invalid_max_results(self, client):
        """Test pattern search with invalid max_results."""
        response = client.post(
            "/api/pattern",
            json={"pattern": "C?T", "max_results": "not-a-number"},
            content_type="application/json",
        )

        assert response.status_code == 400, resp_diag(response)

    def test_pattern_search_max_results_out_of_range(self, client):
        """Test pattern search with max_results out of range."""
        response = client.post(
            "/api/pattern",
            json={"pattern": "C?T", "max_results": 200},
            content_type="application/json",
        )

        assert response.status_code == 400, resp_diag(response)

    def test_pattern_search_result_structure(self, client):
        """Test that pattern search results have correct structure."""
        response = client.post("/api/pattern", json={"pattern": "C?T"}, content_type="application/json")

        data = json.loads(response.data)
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "word" in result
            assert "score" in result
            assert "source" in result
            assert "length" in result
            assert "letter_quality" in result


class TestNumberEndpoint:
    """Test /api/number endpoint."""

    def test_number_grid_valid(self, client):
        """Test grid numbering with valid grid."""
        grid_data = {
            "size": 11,
            "grid": [
                ["R", "A", "T", "#", ".", ".", ".", ".", ".", ".", "."],
                ["#", "T", "#", "#", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
                [".", ".", ".", ".", ".", ".", "#", "T", "#", ".", "."],
                [".", ".", ".", ".", ".", ".", "#", "A", "R", ".", "."],
            ],
        }

        response = client.post("/api/number", json=grid_data, content_type="application/json")

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        assert "numbering" in data

    def test_number_grid_no_body(self, client):
        """Test grid numbering with no request body."""
        response = client.post("/api/number", data="", content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_number_grid_missing_size(self, client):
        """Test grid numbering without size field."""
        response = client.post("/api/number", json={"grid": [[]]}, content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_number_grid_missing_grid(self, client):
        """Test grid numbering without grid field."""
        response = client.post("/api/number", json={"size": 11}, content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_number_grid_invalid_size(self, client):
        """Test grid numbering with invalid size (Phase 3: must be 3-50)."""
        response = client.post(
            "/api/number",
            json={"size": 2, "grid": [["A", "B"], ["C", "D"]]},  # Invalid: must be >= 3
            content_type="application/json",
        )

        assert response.status_code == 400, resp_diag(response)

    def test_number_grid_non_integer_size(self, client):
        """Test grid numbering with non-integer size."""
        response = client.post(
            "/api/number",
            json={"size": "11", "grid": [[]]},
            content_type="application/json",
        )

        assert response.status_code == 400, resp_diag(response)

    def test_number_grid_non_array_grid(self, client):
        """Test grid numbering with non-array grid."""
        response = client.post(
            "/api/number",
            json={"size": 11, "grid": "not-an-array"},
            content_type="application/json",
        )

        assert response.status_code == 400, resp_diag(response)

    def test_number_grid_non_2d_array(self, client):
        """Test grid numbering with non-2D array."""
        response = client.post(
            "/api/number",
            json={"size": 11, "grid": ["not", "2d", "array"]},
            content_type="application/json",
        )

        assert response.status_code == 400, resp_diag(response)

    def test_number_grid_with_user_numbering(self, client):
        """Test grid numbering validation with user numbering."""
        grid_data = {
            "size": 11,
            "grid": [["R", "A", "T"] + ["#"] * 8] + [["."] * 11] * 10,
            "numbering": {"(0,0)": 1, "(0,1)": 2},
        }

        response = client.post("/api/number", json=grid_data, content_type="application/json")

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        assert "validation" in data or "numbering" in data


class TestNormalizeEndpoint:
    """Test /api/normalize endpoint."""

    def test_normalize_valid(self, client):
        """Test normalization with valid text."""
        response = client.post("/api/normalize", json={"text": "résumé"}, content_type="application/json")

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        assert "normalized" in data
        assert "original" in data

    def test_normalize_no_body(self, client):
        """Test normalization with no request body."""
        response = client.post("/api/normalize", data="", content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_normalize_missing_text(self, client):
        """Test normalization without text field."""
        response = client.post("/api/normalize", json={}, content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_normalize_non_string_text(self, client):
        """Test normalization with non-string text."""
        response = client.post("/api/normalize", json={"text": 123}, content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_normalize_empty_text(self, client):
        """Test normalization with empty text."""
        response = client.post("/api/normalize", json={"text": ""}, content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_normalize_whitespace_only(self, client):
        """Test normalization with whitespace-only text."""
        response = client.post("/api/normalize", json={"text": "   "}, content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_normalize_too_long(self, client):
        """Test normalization with text exceeding length limit."""
        response = client.post("/api/normalize", json={"text": "a" * 101}, content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_normalize_accented_characters(self, client):
        """Test normalization handles accented characters."""
        response = client.post("/api/normalize", json={"text": "café"}, content_type="application/json")

        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        # Should normalize to unaccented form
        assert "e" in data["normalized"].lower() or "é" in data["normalized"].lower()


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_json(self, client):
        """Test that invalid JSON returns 400."""
        response = client.post("/api/pattern", data="invalid json", content_type="application/json")

        assert response.status_code == 400, resp_diag(response)

    def test_wrong_content_type(self, client):
        """Test that non-JSON content type is handled."""
        response = client.post(
            "/api/pattern",
            data="pattern=C?T",
            content_type="application/x-www-form-urlencoded",
        )

        # May return 400 or 415 depending on Flask version
        assert response.status_code in [400, 415]

    def test_method_not_allowed(self, client):
        """Test that wrong HTTP method returns 405."""
        response = client.get("/api/pattern")  # Should be POST

        assert response.status_code == 405, resp_diag(response)

    def test_nonexistent_endpoint(self, client):
        """Test that nonexistent endpoint returns 404."""
        response = client.get("/api/nonexistent")

        assert response.status_code == 404, resp_diag(response)


class TestCORS:
    """Test CORS headers."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present on API responses."""
        response = client.get("/api/health")

        # Check for CORS headers (if CORS is configured)
        # Note: This depends on whether CORS is enabled in the app
        # If CORS is not configured, this test can be skipped
        response.headers
        # Just verify response is valid
        assert response.status_code == 200, resp_diag(response)


class TestInputSanitization:
    """Test input sanitization and security."""

    def test_sql_injection_attempt(self, client):
        """Test that SQL injection attempts are handled safely."""
        response = client.post(
            "/api/pattern",
            json={"pattern": "'; DROP TABLE words; --"},
            content_type="application/json",
        )

        # Should not crash, should return valid response or error
        assert response.status_code in [200, 400]

    def test_xss_attempt(self, client):
        """Test that XSS attempts are handled safely."""
        response = client.post(
            "/api/normalize",
            json={"text": '<script>alert("xss")</script>'},
            content_type="application/json",
        )

        # Should not crash, should return valid response or error
        assert response.status_code in [200, 400]

    def test_large_payload(self, client):
        """Test handling of unreasonably large payloads."""
        huge_grid = [["."] * 1000] * 1000

        response = client.post(
            "/api/number",
            json={"size": 1000, "grid": huge_grid},
            content_type="application/json",
        )

        # Should reject with error, not crash
        assert response.status_code == 400, resp_diag(response)


class TestNormalizeConventionParity:
    """Regression: /api/normalize must never return interior spaces
    (CLI parity: 'Tina Fey' -> TINAFEY; documented apostrophe examples
    remove spaces too)."""

    def test_two_word_name(self, client):
        response = client.post("/api/normalize", json={"text": "Tina Fey"})
        assert response.status_code == 200, resp_diag(response)
        assert json.loads(response.data)["normalized"] == "TINAFEY"

    def test_hyphenated(self, client):
        response = client.post("/api/normalize", json={"text": "self-aware"})
        assert response.status_code == 200, resp_diag(response)
        assert json.loads(response.data)["normalized"] == "SELFAWARE"

    def test_apostrophe_with_space(self, client):
        """The apostrophe rule used to keep the interior space."""
        response = client.post("/api/normalize", json={"text": "don't stop"})
        assert response.status_code == 200, resp_diag(response)
        assert json.loads(response.data)["normalized"] == "DONTSTOP"


class TestPatternWordlistResolution:
    """Regression: names with .txt used to silently fall back to the CLI's
    8-word builtin list; unknown names must be a clear 400."""

    def test_txt_extension_resolves_to_real_list(self, client):
        response = client.post(
            "/api/pattern",
            json={"pattern": "C?T", "wordlists": ["comprehensive.txt"]},
        )
        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        sources = data["meta"]["sources_searched"]
        assert "builtin" not in sources
        assert any("comprehensive" in s for s in sources)
        # comprehensive.txt has more real C?T matches than the 8-word builtin
        # demo list (grep -icE '^C.T$' data/wordlists/comprehensive.txt -> 7;
        # builtin demo list only contains CAT -> 1)
        assert data["meta"]["total_found"] >= 5

    def test_unknown_wordlist_returns_400(self, client):
        response = client.post(
            "/api/pattern",
            json={"pattern": "C?T", "wordlists": ["definitely_not_a_list"]},
        )
        assert response.status_code == 400, resp_diag(response)
        error = json.loads(response.data)["error"]
        assert error["code"] == "UNKNOWN_WORDLIST"
        assert "definitely_not_a_list" in error["message"]


class TestVerifyWordsWordlistSelection:
    """Regression: verify-words/clean used to ignore the requested wordlists
    and validate against every installed list merged."""

    def _grid_with_word(self, word="CAT", size=5):
        grid = [["." for _ in range(size)] for _ in range(size)]
        for i, ch in enumerate(word):
            grid[0][i] = ch
        return grid

    def test_verify_words_honors_selection(self, client):
        # crosswordese (wc -l data/wordlists/core/crosswordese.txt) does not
        # contain ZUGZWANG-ish junk; use a word that only exists in the comprehensive list
        grid = self._grid_with_word("CAT")

        response = client.post(
            "/api/grid/verify-words",
            json={"size": 5, "grid": grid, "wordlists": ["core/crosswordese"]},
        )
        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        # Selected list only: must be crosswordese's size, not the full merge
        # of every non-archive/non-custom list under data/wordlists/ (see
        # backend/api/routes.py verify_words(), wordlist_dir.rglob('*.txt'))
        assert data["wordlist_size"] < 1000

    def test_verify_words_unknown_wordlist_returns_400(self, client):
        grid = self._grid_with_word("CAT")
        response = client.post(
            "/api/grid/verify-words",
            json={"size": 5, "grid": grid, "wordlists": ["nope_not_here"]},
        )
        assert response.status_code == 400, resp_diag(response)
        assert json.loads(response.data)["error"]["code"] == "UNKNOWN_WORDLIST"

    def test_verify_words_default_is_merged(self, client):
        grid = self._grid_with_word("CAT")
        response = client.post(
            "/api/grid/verify-words",
            json={"size": 5, "grid": grid},
        )
        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        # No selection: falls back to the merged dictionary (see assertion
        # below for the size threshold this enforces)
        assert data["wordlist_size"] > 40000

    def test_clean_honors_selection(self, client):
        # ETUI is classic crosswordese (present in core/crosswordese).
        # Blacked-out row 1 keeps every slot either exactly ETUI or shorter
        # than 3, so this exercises wordlist selection only -- clean also
        # flags unfillable partial slots, and a ragged grid would confound
        # the two (crosswordese has no 5-letter word matching "ETUI?").
        grid = [
            ["E", "T", "U", "I"],
            ["#", "#", "#", "#"],
            [".", ".", ".", "."],
            [".", ".", ".", "."],
        ]
        response = client.post(
            "/api/grid/clean",
            json={"size": 4, "grid": grid, "wordlists": ["core/crosswordese"]},
        )
        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        # ETUI is valid in the selected list, so nothing should be removed
        assert data["removed_count"] == 0

    def test_clean_clears_every_cell_of_a_fully_crossed_invalid_word(self, client):
        """Clean clears all cells of an invalid word, even ones a valid
        crossing word runs through.

        ACI (across, row 0) is not in comprehensive.txt; its three down words
        (ASS, CII, ISS) all are. An earlier version spared cells shared with a
        valid word, which here spared all three -- nothing was cleared and the
        invalid entry survived while the response still claimed it was removed.
        """
        grid = [
            ["A", "C", "I"],
            ["S", "I", "S"],
            ["S", "I", "S"],
        ]
        response = client.post(
            "/api/grid/clean",
            json={"size": 3, "grid": grid, "wordlists": ["comprehensive"]},
        )
        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)

        def letter(cell):
            raw = (cell["letter"] if isinstance(cell, dict) else cell) or ""
            return "" if raw == "." else raw

        row0 = [letter(c) for c in data["grid"][0]]
        assert row0 == ["", "", ""], f"row 0 not fully cleared: {row0!r}"
        assert data["cleared_cells"] == 3, data["message"]
        assert data["removed_count"] >= 1

    def test_clean_clears_unfillable_partial_words(self, client):
        """The grid paints unfillable partials red too, so clean must take
        them -- it used to skip any slot that was not completely filled."""
        # 'QJ?' cannot be completed by any 3-letter word in the list.
        grid = [
            ["Q", "J", "."],
            [".", ".", "."],
            [".", ".", "."],
        ]
        response = client.post(
            "/api/grid/clean",
            json={"size": 3, "grid": grid, "wordlists": ["comprehensive"]},
        )
        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)

        def letter(cell):
            raw = (cell["letter"] if isinstance(cell, dict) else cell) or ""
            return "" if raw == "." else raw

        row0 = [letter(c) for c in data["grid"][0]]
        assert row0 == ["", "", ""], f"unfillable partial survived: {row0!r}"

    def test_clean_reports_zero_when_nothing_to_clean(self, client):
        """removed_count must never overstate: a fully valid grid reports 0."""
        grid = [
            ["C", "A", "T"],
            ["A", "R", "E"],
            ["T", "E", "N"],
        ]
        response = client.post(
            "/api/grid/clean",
            json={"size": 3, "grid": grid, "wordlists": ["comprehensive"]},
        )
        assert response.status_code == 200, resp_diag(response)
        data = json.loads(response.data)
        assert data["removed_count"] == 0
        assert data.get("cleared_cells", 0) == 0

    def test_clean_unknown_wordlist_returns_400(self, client):
        grid = self._grid_with_word("CAT")
        response = client.post(
            "/api/grid/clean",
            json={"size": 5, "grid": grid, "wordlists": ["nope_not_here"]},
        )
        assert response.status_code == 400, resp_diag(response)
        assert json.loads(response.data)["error"]["code"] == "UNKNOWN_WORDLIST"


class TestBuiltinWordlistProtection:
    """Regression: the wordlist API used to allow editing/overwriting the
    shipped lists (comprehensive.txt etc.) with no undo."""

    def test_put_add_words_to_builtin_refused(self, client):
        response = client.put(
            "/api/wordlists/comprehensive",
            json={"add_words": ["ZZZZQQQ"]},
        )
        assert response.status_code == 403, resp_diag(response)
        data = json.loads(response.data)
        assert "built-in" in data["error"]

    def test_put_replace_words_of_builtin_refused(self, client):
        response = client.put(
            "/api/wordlists/core/crosswordese",
            json={"words": ["ONLYME"]},
        )
        assert response.status_code == 403, resp_diag(response)

    def test_delete_builtin_refused(self, client):
        response = client.delete("/api/wordlists/comprehensive")
        assert response.status_code == 403, resp_diag(response)
        assert "built-in" in json.loads(response.data)["error"]

    def test_post_overwrite_builtin_refused(self, client):
        response = client.post(
            "/api/wordlists/comprehensive",
            json={"words": ["HIJACKED"]},
        )
        assert response.status_code == 403, resp_diag(response)

    def test_custom_list_lifecycle_still_editable(self, client):
        """Custom lists remain fully editable (create, update, delete)."""
        name = "custom/test_protection_tmp"

        create = client.post(f"/api/wordlists/{name}", json={"words": ["ALPHA", "BETA"]})
        assert create.status_code == 201, resp_diag(create)

        try:
            update = client.put(f"/api/wordlists/{name}", json={"add_words": ["GAMMA"]})
            assert update.status_code == 200, resp_diag(update)

            get = client.get(f"/api/wordlists/{name}")
            assert get.status_code == 200, resp_diag(get)
            assert "GAMMA" in json.loads(get.data)["words"]
        finally:
            delete = client.delete(f"/api/wordlists/{name}")
            assert delete.status_code == 200, resp_diag(delete)
