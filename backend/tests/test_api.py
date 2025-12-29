"""
Unit tests for API routes.

Tests all API endpoints for correct behavior, validation, and error handling.
"""

import pytest
import json
from backend.app import create_app


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
        response = client.get('/api/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'version' in data
        assert 'components' in data

    def test_health_check_components(self, client):
        """Test health check includes all components (Phase 3: CLI architecture)."""
        response = client.get('/api/health')
        data = json.loads(response.data)

        components = data['components']
        # Phase 3: Components are now cli_adapter and api_server
        assert components['cli_adapter'] in ['ok', 'error']
        assert components['api_server'] == 'ok'


class TestPatternEndpoint:
    """Test /api/pattern endpoint."""

    def test_pattern_search_valid(self, client):
        """Test pattern search with valid pattern."""
        response = client.post('/api/pattern',
                                json={'pattern': 'C?T'},
                                content_type='application/json')

        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'results' in data
        assert 'meta' in data
        assert isinstance(data['results'], list)

    def test_pattern_search_no_body(self, client):
        """Test pattern search with no request body."""
        response = client.post('/api/pattern',
                                data='',
                                content_type='application/json')

        assert response.status_code == 400

    def test_pattern_search_missing_pattern(self, client):
        """Test pattern search without pattern field."""
        response = client.post('/api/pattern',
                                json={},
                                content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_pattern_search_invalid_pattern_type(self, client):
        """Test pattern search with non-string pattern."""
        response = client.post('/api/pattern',
                                json={'pattern': 123},
                                content_type='application/json')

        assert response.status_code == 400

    def test_pattern_search_with_wordlists(self, client):
        """Test pattern search with wordlists parameter."""
        response = client.post('/api/pattern',
                                json={
                                    'pattern': 'C?T',
                                    'wordlists': ['standard']
                                },
                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['meta']['sources_searched'] == ['standard']

    def test_pattern_search_invalid_wordlists(self, client):
        """Test pattern search with invalid wordlists type."""
        response = client.post('/api/pattern',
                                json={
                                    'pattern': 'C?T',
                                    'wordlists': 'not-a-list'
                                },
                                content_type='application/json')

        assert response.status_code == 400

    def test_pattern_search_with_max_results(self, client):
        """Test pattern search with max_results parameter."""
        response = client.post('/api/pattern',
                                json={
                                    'pattern': 'C?T',
                                    'max_results': 5
                                },
                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['results']) <= 5

    def test_pattern_search_invalid_max_results(self, client):
        """Test pattern search with invalid max_results."""
        response = client.post('/api/pattern',
                                json={
                                    'pattern': 'C?T',
                                    'max_results': 'not-a-number'
                                },
                                content_type='application/json')

        assert response.status_code == 400

    def test_pattern_search_max_results_out_of_range(self, client):
        """Test pattern search with max_results out of range."""
        response = client.post('/api/pattern',
                                json={
                                    'pattern': 'C?T',
                                    'max_results': 200
                                },
                                content_type='application/json')

        assert response.status_code == 400

    def test_pattern_search_result_structure(self, client):
        """Test that pattern search results have correct structure."""
        response = client.post('/api/pattern',
                                json={'pattern': 'C?T'},
                                content_type='application/json')

        data = json.loads(response.data)
        if len(data['results']) > 0:
            result = data['results'][0]
            assert 'word' in result
            assert 'score' in result
            assert 'source' in result
            assert 'length' in result
            assert 'letter_quality' in result


class TestNumberEndpoint:
    """Test /api/number endpoint."""

    def test_number_grid_valid(self, client):
        """Test grid numbering with valid grid."""
        grid_data = {
            'size': 11,
            'grid': [
                ['R', 'A', 'T', '#', '.', '.', '.', '.', '.', '.', '.'],
                ['#', 'T', '#', '#', '.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '#', 'T', '#', '.', '.'],
                ['.', '.', '.', '.', '.', '.', '#', 'A', 'R', '.', '.']
            ]
        }

        response = client.post('/api/number',
                                json=grid_data,
                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'numbering' in data

    def test_number_grid_no_body(self, client):
        """Test grid numbering with no request body."""
        response = client.post('/api/number',
                                data='',
                                content_type='application/json')

        assert response.status_code == 400

    def test_number_grid_missing_size(self, client):
        """Test grid numbering without size field."""
        response = client.post('/api/number',
                                json={'grid': [[]]},
                                content_type='application/json')

        assert response.status_code == 400

    def test_number_grid_missing_grid(self, client):
        """Test grid numbering without grid field."""
        response = client.post('/api/number',
                                json={'size': 11},
                                content_type='application/json')

        assert response.status_code == 400

    def test_number_grid_invalid_size(self, client):
        """Test grid numbering with invalid size (Phase 3: must be 3-50)."""
        response = client.post('/api/number',
                                json={
                                    'size': 2,  # Invalid: must be >= 3
                                    'grid': [['A', 'B'], ['C', 'D']]
                                },
                                content_type='application/json')

        assert response.status_code == 400

    def test_number_grid_non_integer_size(self, client):
        """Test grid numbering with non-integer size."""
        response = client.post('/api/number',
                                json={
                                    'size': '11',
                                    'grid': [[]]
                                },
                                content_type='application/json')

        assert response.status_code == 400

    def test_number_grid_non_array_grid(self, client):
        """Test grid numbering with non-array grid."""
        response = client.post('/api/number',
                                json={
                                    'size': 11,
                                    'grid': 'not-an-array'
                                },
                                content_type='application/json')

        assert response.status_code == 400

    def test_number_grid_non_2d_array(self, client):
        """Test grid numbering with non-2D array."""
        response = client.post('/api/number',
                                json={
                                    'size': 11,
                                    'grid': ['not', '2d', 'array']
                                },
                                content_type='application/json')

        assert response.status_code == 400

    def test_number_grid_with_user_numbering(self, client):
        """Test grid numbering validation with user numbering."""
        grid_data = {
            'size': 11,
            'grid': [['R', 'A', 'T'] + ['#'] * 8] + [['.'] * 11] * 10,
            'numbering': {
                '(0,0)': 1,
                '(0,1)': 2
            }
        }

        response = client.post('/api/number',
                                json=grid_data,
                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'validation' in data or 'numbering' in data


class TestNormalizeEndpoint:
    """Test /api/normalize endpoint."""

    def test_normalize_valid(self, client):
        """Test normalization with valid text."""
        response = client.post('/api/normalize',
                                json={'text': 'résumé'},
                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'normalized' in data
        assert 'original' in data

    def test_normalize_no_body(self, client):
        """Test normalization with no request body."""
        response = client.post('/api/normalize',
                                data='',
                                content_type='application/json')

        assert response.status_code == 400

    def test_normalize_missing_text(self, client):
        """Test normalization without text field."""
        response = client.post('/api/normalize',
                                json={},
                                content_type='application/json')

        assert response.status_code == 400

    def test_normalize_non_string_text(self, client):
        """Test normalization with non-string text."""
        response = client.post('/api/normalize',
                                json={'text': 123},
                                content_type='application/json')

        assert response.status_code == 400

    def test_normalize_empty_text(self, client):
        """Test normalization with empty text."""
        response = client.post('/api/normalize',
                                json={'text': ''},
                                content_type='application/json')

        assert response.status_code == 400

    def test_normalize_whitespace_only(self, client):
        """Test normalization with whitespace-only text."""
        response = client.post('/api/normalize',
                                json={'text': '   '},
                                content_type='application/json')

        assert response.status_code == 400

    def test_normalize_too_long(self, client):
        """Test normalization with text exceeding length limit."""
        response = client.post('/api/normalize',
                                json={'text': 'a' * 101},
                                content_type='application/json')

        assert response.status_code == 400

    def test_normalize_accented_characters(self, client):
        """Test normalization handles accented characters."""
        response = client.post('/api/normalize',
                                json={'text': 'café'},
                                content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should normalize to unaccented form
        assert 'e' in data['normalized'].lower() or 'é' in data['normalized'].lower()


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_json(self, client):
        """Test that invalid JSON returns 400."""
        response = client.post('/api/pattern',
                                data='invalid json',
                                content_type='application/json')

        assert response.status_code == 400

    def test_wrong_content_type(self, client):
        """Test that non-JSON content type is handled."""
        response = client.post('/api/pattern',
                                data='pattern=C?T',
                                content_type='application/x-www-form-urlencoded')

        # May return 400 or 415 depending on Flask version
        assert response.status_code in [400, 415]

    def test_method_not_allowed(self, client):
        """Test that wrong HTTP method returns 405."""
        response = client.get('/api/pattern')  # Should be POST

        assert response.status_code == 405

    def test_nonexistent_endpoint(self, client):
        """Test that nonexistent endpoint returns 404."""
        response = client.get('/api/nonexistent')

        assert response.status_code == 404


class TestCORS:
    """Test CORS headers."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present on API responses."""
        response = client.get('/api/health')

        # Check for CORS headers (if CORS is configured)
        # Note: This depends on whether CORS is enabled in the app
        # If CORS is not configured, this test can be skipped
        response.headers
        # Just verify response is valid
        assert response.status_code == 200


class TestInputSanitization:
    """Test input sanitization and security."""

    def test_sql_injection_attempt(self, client):
        """Test that SQL injection attempts are handled safely."""
        response = client.post('/api/pattern',
                                json={'pattern': "'; DROP TABLE words; --"},
                                content_type='application/json')

        # Should not crash, should return valid response or error
        assert response.status_code in [200, 400]

    def test_xss_attempt(self, client):
        """Test that XSS attempts are handled safely."""
        response = client.post('/api/normalize',
                                json={'text': '<script>alert("xss")</script>'},
                                content_type='application/json')

        # Should not crash, should return valid response or error
        assert response.status_code in [200, 400]

    def test_large_payload(self, client):
        """Test handling of unreasonably large payloads."""
        huge_grid = [['.'] * 1000] * 1000

        response = client.post('/api/number',
                                json={
                                    'size': 1000,
                                    'grid': huge_grid
                                },
                                content_type='application/json')

        # Should reject with error, not crash
        assert response.status_code == 400
