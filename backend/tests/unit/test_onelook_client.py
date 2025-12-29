"""
Unit tests for OneLook API client.

This test suite ensures OneLook API client works correctly:
- Successful pattern searches return uppercase words
- Graceful degradation on timeout/errors (returns empty list)
- Request parameters are correctly formatted
- Response parsing handles edge cases

Created: 2025-12-28
Purpose: Comprehensive testing of OneLook API integration
"""

from unittest.mock import Mock, patch
import requests


class TestOneLookClientSuccess:
    """Tests for successful OneLook API responses."""

    def test_search_returns_uppercase_words(self):
        """Verify search() returns words in uppercase."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient(timeout=5)

        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {'word': 'visa', 'score': 1000},
            {'word': 'vita', 'score': 950},
            {'word': 'diva', 'score': 900}
        ]
        mock_response.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_response):
            results = client.search('?i?a')

        # Verify words are uppercase
        assert results == ['VISA', 'VITA', 'DIVA']
        assert all(word.isupper() for word in results)

    def test_search_sends_lowercase_pattern(self):
        """Verify pattern is sent to API in lowercase."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient()

        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_response) as mock_get:
            client.search('PATTERN')

        # Verify pattern was lowercased in request
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['params']['sp'] == 'pattern'

    def test_search_respects_max_results_parameter(self):
        """Verify max_results parameter is passed to API."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient()

        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_response) as mock_get:
            client.search('test', max_results=50)

        # Verify max parameter sent correctly
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['params']['max'] == 50

    def test_search_uses_correct_timeout(self):
        """Verify timeout parameter is passed to requests.get()."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient(timeout=10)

        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_response) as mock_get:
            client.search('test')

        # Verify timeout passed to requests
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['timeout'] == 10

    def test_search_handles_empty_results(self):
        """Verify empty API response returns empty list."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient()

        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_response):
            results = client.search('xyz')

        assert results == []
        assert isinstance(results, list)


class TestOneLookClientErrorHandling:
    """Tests for OneLook API error handling and graceful degradation."""

    def test_timeout_returns_empty_list(self):
        """Verify timeout returns empty list gracefully (no exception raised)."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient(timeout=1)

        with patch('requests.get', side_effect=requests.Timeout):
            results = client.search('?i?a')

        # Should return empty list, not raise exception
        assert results == []

    def test_request_exception_returns_empty_list(self):
        """Verify network errors return empty list gracefully."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient()

        with patch('requests.get', side_effect=requests.RequestException("Network error")):
            results = client.search('?i?a')

        # Should return empty list, not raise exception
        assert results == []

    def test_http_error_returns_empty_list(self):
        """Verify HTTP errors (404, 500) return empty list gracefully."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient()

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        with patch('requests.get', return_value=mock_response):
            results = client.search('?i?a')

        assert results == []

    def test_malformed_json_returns_empty_list(self):
        """Verify malformed JSON response returns empty list."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient()

        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_response):
            results = client.search('?i?a')

        assert results == []

    def test_missing_word_field_returns_empty_list(self):
        """Verify response missing 'word' field returns empty list."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient()

        # Response with entry missing 'word' field
        mock_response = Mock()
        mock_response.json.return_value = [
            {'score': 1000},  # Missing 'word' field
            {'word': 'test', 'score': 900}
        ]
        mock_response.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_response):
            results = client.search('?i?a')

        # Should gracefully handle KeyError and return empty list
        assert results == []


class TestOneLookClientIntegration:
    """Integration-style tests verifying overall client behavior."""

    def test_client_initializes_with_default_timeout(self):
        """Verify client can be initialized with default timeout."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient()

        assert client.timeout == 5  # Default timeout

    def test_client_initializes_with_custom_timeout(self):
        """Verify client can be initialized with custom timeout."""
        from backend.data.onelook_client import OneLookClient

        client = OneLookClient(timeout=10)

        assert client.timeout == 10

    def test_base_url_is_correct(self):
        """Verify BASE_URL points to OneLook API."""
        from backend.data.onelook_client import OneLookClient

        assert OneLookClient.BASE_URL == 'https://api.onelook.com/words'
