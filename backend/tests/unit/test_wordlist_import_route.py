"""
Route tests for POST /api/wordlists/import and POST /api/wordlists/<name>
(spec 2026-10-22-basics-first-design, section 4 and open points O5-O7, O10).

The manager is repointed at a tmp directory, so nothing touches data/wordlists/.
The parse step runs the real CLI through the real adapter (seam rule).
"""

import json

import pytest

from backend.api import wordlist_routes
from backend.app import app
from backend.data.wordlist_manager import WordListManager


@pytest.fixture
def wl_dir(tmp_path, monkeypatch):
    (tmp_path / "metadata.json").write_text(json.dumps({"wordlists": {}, "categories": {}, "tags": {}}, indent=2))
    manager = WordListManager(wordlist_dir=str(tmp_path))
    monkeypatch.setattr(wordlist_routes, "wordlist_manager", manager)
    return tmp_path


@pytest.fixture
def client(wl_dir):
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _files(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*.txt"))


def test_import_stores_canonical_lines_and_keeps_name(client, wl_dir):
    r = client.post("/api/wordlists/import", json={"name": "my_list", "content": "APPLE;50\ngrape,40\n"})
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["name"] == "imports/my_list"
    assert (wl_dir / "imports" / "my_list.txt").read_text().splitlines() == ["APPLE;50", "GRAPE;40"]
    meta = json.loads((wl_dir / "metadata.json").read_text())["wordlists"]["imports/my_list"]
    assert meta["name"] == "My List"
    assert meta["category"] == "imports"


def test_import_empty_content_rejected(client, wl_dir):
    r = client.post("/api/wordlists/import", json={"name": "e", "content": ""})
    assert r.status_code == 400
    assert r.get_json()["error"] == "No valid words found"
    assert r.get_json()["skipped"] == 0
    assert _files(wl_dir) == []


def test_import_all_invalid_rejected_with_reasons(client, wl_dir):
    r = client.post("/api/wordlists/import", json={"name": "bad", "content": "!!\n12\n"})
    assert r.status_code == 400
    body = r.get_json()
    assert body["error"] == "No valid words found"
    assert body["skipped"] == 2
    assert body["reasons"] == {"length outside 3-21": 2}
    assert _files(wl_dir) == []
    assert "imports/bad" not in json.loads((wl_dir / "metadata.json").read_text())["wordlists"]


def test_dry_run_returns_parse_and_stores_nothing(client, wl_dir):
    before = (wl_dir / "metadata.json").read_bytes()
    r = client.post("/api/wordlists/import", json={"name": "dry", "content": "APPLE;50\ngrape,40\n", "dry_run": True})
    assert r.status_code == 200
    body = r.get_json()
    assert body["words"] == [{"word": "APPLE", "score": 50}, {"word": "GRAPE", "score": 40}]
    assert body["skipped"] == []
    assert _files(wl_dir) == []
    assert (wl_dir / "metadata.json").read_bytes() == before


def test_import_merges_existing_metadata(client, wl_dir):
    meta_path = wl_dir / "metadata.json"
    meta_path.write_text(
        json.dumps({"wordlists": {"imports/x": {"name": "Custom Title", "extra": 1}}, "categories": {}, "tags": {}})
    )
    wordlist_routes.wordlist_manager._load_metadata()
    r = client.post("/api/wordlists/import", json={"name": "x", "content": "CAT\n", "metadata": {"description": "d"}})
    assert r.status_code == 201
    entry = json.loads(meta_path.read_text())["wordlists"]["imports/x"]
    assert entry["name"] == "Custom Title"
    assert entry["extra"] == 1
    assert entry["description"] == "d"


def test_get_after_import_leaves_metadata_byte_identical(client, wl_dir):
    client.post("/api/wordlists/import", json={"name": "my_list", "content": "APPLE;50\ngrape,40\n"})
    # simulate a stored entry that lacks `name`, the case that made GET mutate
    meta_path = wl_dir / "metadata.json"
    data = json.loads(meta_path.read_text())
    del data["wordlists"]["imports/my_list"]["name"]
    meta_path.write_text(json.dumps(data, indent=2))
    wordlist_routes.wordlist_manager._load_metadata()
    before = meta_path.read_bytes()
    r = client.get("/api/wordlists/imports/my_list")
    assert r.status_code == 200
    assert r.get_json()["metadata"]["name"] == "My List"
    assert r.get_json()["words"] == ["APPLE", "GRAPE"]
    assert meta_path.read_bytes() == before
    assert "key" not in wordlist_routes.wordlist_manager._metadata["wordlists"]["imports/my_list"]


def test_temp_file_removed(client, monkeypatch):
    seen = []
    real = wordlist_routes.get_adapter().parse_wordlist

    class Spy:
        def parse_wordlist(self, path):
            seen.append(path)
            return real(path)

    monkeypatch.setattr(wordlist_routes, "get_adapter", lambda: Spy())
    client.post("/api/wordlists/import", json={"name": "t", "content": "!!\n"})
    client.post("/api/wordlists/import", json={"name": "t", "content": "CAT\n"})
    import os

    assert len(seen) == 2 and not any(os.path.exists(p) for p in seen)


def test_create_without_category_goes_to_custom_then_put_delete(client, wl_dir):
    r = client.post("/api/wordlists/qa-put", json={"words": ["cat", "dog"]})
    assert r.status_code == 201
    assert (wl_dir / "custom" / "qa-put.txt").exists()
    meta = json.loads((wl_dir / "metadata.json").read_text())["wordlists"]["custom/qa-put"]
    assert meta["category"] == "custom"
    r = client.put("/api/wordlists/custom/qa-put", json={"add_words": ["eel"]})
    assert r.status_code == 200
    r = client.delete("/api/wordlists/custom/qa-put")
    assert r.status_code == 200
    assert "custom/qa-put" not in json.loads((wl_dir / "metadata.json").read_text())["wordlists"]
    assert not (wl_dir / "custom" / "qa-put.txt").exists()


def test_manager_load_strips_score_suffix(tmp_path):
    (tmp_path / "a.txt").write_text("APPLE;50\nGRAPE\n# c\n")
    assert WordListManager(wordlist_dir=str(tmp_path)).load("a") == ["APPLE", "GRAPE"]
