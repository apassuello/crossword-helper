"""
Integration tests for wordlist metadata feature.

This test suite ensures that wordlist metadata is correctly structured and returned:
- All wordlists have required metadata fields (especially 'name')
- API endpoints return complete metadata
- Custom/uploaded wordlists get proper metadata
- Metadata persistence works correctly

Created: 2025-12-28
Purpose: Regression protection for wordlist metadata (commit 9976d3b)
         "Fix: Custom wordlists missing name field in API response"
"""

import pytest
from pathlib import Path
import tempfile
import json


class TestWordlistMetadataStructure:
    """Unit tests for wordlist metadata structure and completeness."""

    def test_all_wordlists_have_name_field(self):
        """Verify all wordlists in metadata.json have 'name' field (regression test for 9976d3b)."""
        from backend.data.wordlist_manager import WordListManager

        manager = WordListManager()
        metadata = manager._metadata

        missing_name = []
        for key, info in metadata['wordlists'].items():
            if 'name' not in info:
                missing_name.append(key)

        assert len(missing_name) == 0, \
            f"These wordlists are missing 'name' field: {missing_name}"

    def test_all_wordlists_have_required_fields(self):
        """Verify all wordlists have required metadata fields."""
        from backend.data.wordlist_manager import WordListManager

        manager = WordListManager()
        metadata = manager._metadata

        required_fields = ['name', 'category', 'description', 'tags']

        for key, info in metadata['wordlists'].items():
            for field in required_fields:
                assert field in info, \
                    f"Wordlist '{key}' missing required field '{field}'"

    def test_custom_wordlists_have_name_field(self):
        """Specifically verify custom wordlists have 'name' field (regression test)."""
        from backend.data.wordlist_manager import WordListManager

        manager = WordListManager()
        metadata = manager._metadata

        custom_wordlists = {
            key: info for key, info in metadata['wordlists'].items()
            if info.get('category') == 'custom'
        }

        assert len(custom_wordlists) > 0, "No custom wordlists found for testing"

        for key, info in custom_wordlists.items():
            assert 'name' in info, \
                f"Custom wordlist '{key}' missing 'name' field (bug regression!)"
            assert isinstance(info['name'], str), \
                f"Custom wordlist '{key}' has non-string 'name' field"
            assert len(info['name']) > 0, \
                f"Custom wordlist '{key}' has empty 'name' field"

    def test_get_wordlist_info_includes_name(self):
        """Verify get_wordlist_info() returns 'name' field for all wordlists."""
        from backend.data.wordlist_manager import WordListManager

        manager = WordListManager()
        all_wordlists = [wl['key'] for wl in manager.list_all()]

        for wordlist_key in all_wordlists[:5]:  # Test first 5 to keep test fast
            info = manager.get_wordlist_info(wordlist_key)

            assert 'name' in info, \
                f"get_wordlist_info('{wordlist_key}') missing 'name' field"
            assert 'key' in info, \
                f"get_wordlist_info('{wordlist_key}') missing 'key' field"
            assert info['key'] == wordlist_key, \
                f"get_wordlist_info('{wordlist_key}') returned wrong key"

    def test_wordlist_name_is_human_readable(self):
        """Verify wordlist names are human-readable, not just keys."""
        from backend.data.wordlist_manager import WordListManager

        manager = WordListManager()
        metadata = manager._metadata

        for key, info in metadata['wordlists'].items():
            name = info.get('name', '')

            # Name should be different from key (more readable)
            # e.g., "core/common_3_letter" -> "Common 3-Letter Words"
            assert name != key, \
                f"Wordlist '{key}' has name identical to key (should be human-readable)"

            # Name should not contain underscores (should use spaces)
            assert '_' not in name, \
                f"Wordlist '{key}' name contains underscores: '{name}' (should use spaces)"


class TestWordlistAPIMetadata:
    """Integration tests for wordlist API metadata responses."""

    @pytest.fixture
    def app_client(self):
        """Create Flask test client."""
        from backend.app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_list_wordlists_returns_complete_metadata(self, app_client):
        """Test /api/wordlists returns wordlists with complete metadata."""
        response = app_client.get('/api/wordlists')

        assert response.status_code == 200, \
            f"API returned {response.status_code}: {response.data}"

        data = response.get_json()
        assert 'wordlists' in data, "Response missing 'wordlists' field"

        # Verify each wordlist has required fields
        for wl in data['wordlists']:
            assert 'name' in wl, f"Wordlist {wl.get('key')} missing 'name' in API response"
            assert 'key' in wl, f"Wordlist missing 'key' in API response"
            assert 'category' in wl, f"Wordlist {wl.get('key')} missing 'category'"

    def test_get_specific_wordlist_includes_name(self, app_client):
        """Test /api/wordlists/<name> returns metadata with 'name' field."""
        # Get first available wordlist
        list_response = app_client.get('/api/wordlists')
        wordlists = list_response.get_json()['wordlists']

        if len(wordlists) == 0:
            pytest.skip("No wordlists available for testing")

        test_wordlist = wordlists[0]['key']

        # Get specific wordlist
        response = app_client.get(f'/api/wordlists/{test_wordlist}')

        assert response.status_code == 200
        data = response.get_json()

        assert 'metadata' in data, "Response missing 'metadata' field"
        assert 'name' in data['metadata'], \
            f"Wordlist '{test_wordlist}' metadata missing 'name' field in API response"

    def test_custom_wordlists_in_api_have_name(self, app_client):
        """Test custom wordlists returned by API have 'name' field (regression test)."""
        response = app_client.get('/api/wordlists?category=custom')

        assert response.status_code == 200
        data = response.get_json()

        custom_wordlists = data['wordlists']

        if len(custom_wordlists) == 0:
            pytest.skip("No custom wordlists available for testing")

        for wl in custom_wordlists:
            assert 'name' in wl, \
                f"Custom wordlist '{wl.get('key')}' missing 'name' in API response (bug regression!)"
            assert isinstance(wl['name'], str), \
                f"Custom wordlist '{wl.get('key')}' has non-string 'name'"
            assert len(wl['name']) > 0, \
                f"Custom wordlist '{wl.get('key')}' has empty 'name'"

    def test_uploaded_wordlist_gets_name_field(self, app_client):
        """Test that uploading a new wordlist creates proper metadata with 'name' field."""
        # Create unique wordlist name
        import time
        test_name = f"custom/test_upload_{int(time.time())}"

        # Upload wordlist
        upload_data = {
            "words": ["TESTWORD", "ANOTHER", "WORD"],
            "metadata": {
                "name": "Test Upload Wordlist",  # Explicitly set name
                "description": "Test wordlist for metadata testing",
                "tags": ["test", "upload"]
            }
        }

        response = app_client.post(
            f'/api/wordlists/{test_name}',
            json=upload_data,
            content_type='application/json'
        )

        assert response.status_code == 201, \
            f"Upload failed: {response.get_json()}"

        # Verify wordlist has name in API response
        get_response = app_client.get(f'/api/wordlists/{test_name}')
        assert get_response.status_code == 200

        data = get_response.get_json()
        assert 'metadata' in data
        assert 'name' in data['metadata'], \
            "Uploaded wordlist missing 'name' field in metadata"
        assert data['metadata']['name'] == "Test Upload Wordlist", \
            "Uploaded wordlist has wrong name"

        # Cleanup: Delete the test wordlist
        try:
            app_client.delete(f'/api/wordlists/{test_name}')
        except:
            pass  # Cleanup is best-effort

    def test_wordlist_list_includes_display_names(self, app_client):
        """Verify list endpoint returns human-readable names for UI display."""
        response = app_client.get('/api/wordlists')

        assert response.status_code == 200
        data = response.get_json()
        wordlists = data['wordlists']

        # Verify names are human-readable (contain spaces, not underscores)
        for wl in wordlists[:10]:  # Test first 10
            name = wl.get('name', '')
            key = wl.get('key', '')

            # Name should exist and be different from key
            assert name != '', f"Wordlist '{key}' has empty name"
            assert name != key, \
                f"Wordlist '{key}' name is identical to key (not human-readable)"


# Additional test for metadata persistence
class TestWordlistMetadataPersistence:
    """Tests for wordlist metadata file persistence."""

    def test_metadata_json_is_valid_json(self):
        """Verify metadata.json is valid JSON and can be loaded."""
        metadata_path = Path('data/wordlists/metadata.json')

        assert metadata_path.exists(), "metadata.json not found"

        with open(metadata_path) as f:
            metadata = json.load(f)

        assert 'wordlists' in metadata, "metadata.json missing 'wordlists' key"
        assert isinstance(metadata['wordlists'], dict), "'wordlists' is not a dictionary"

    def test_metadata_json_has_no_missing_names(self):
        """Scan metadata.json directly to ensure no wordlists are missing 'name' field."""
        metadata_path = Path('data/wordlists/metadata.json')

        with open(metadata_path) as f:
            metadata = json.load(f)

        missing_names = []
        for key, info in metadata['wordlists'].items():
            if 'name' not in info:
                missing_names.append(key)

        assert len(missing_names) == 0, \
            f"metadata.json has wordlists missing 'name' field: {missing_names}\n" \
            f"This is the bug from commit 9976d3b - all wordlists MUST have 'name' field!"
