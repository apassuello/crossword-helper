"""
Final-review fixes for chore/wordlist-basics (issue #48 area).

I1: word edits keep stored ;N scores.
I3: import/create/update/delete refuse paths outside the word-list directory
    and refuse built-in categories, before anything is written.
Minor: a non-string import `content` is a 400, not a 500.

Every test repoints the manager at a tmp directory (never data/wordlists/).
"""

import json

import pytest

from backend.api import wordlist_routes
from backend.app import app
from backend.data.wordlist_manager import WordListManager


@pytest.fixture
def wl_dir(tmp_path, monkeypatch):
    root = tmp_path / "wl"
    root.mkdir()
    (root / "metadata.json").write_text(json.dumps({"wordlists": {}, "categories": {}, "tags": {}}, indent=2))
    manager = WordListManager(wordlist_dir=str(root))
    monkeypatch.setattr(wordlist_routes, "wordlist_manager", manager)
    return root


@pytest.fixture
def client(wl_dir):
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _everything(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def _lines(root, rel):
    return (root / rel).read_text().splitlines()


# --- I1 ---------------------------------------------------------------------


def test_put_add_words_keeps_stored_scores(client, wl_dir):
    r = client.post("/api/wordlists/import", json={"name": "s", "content": "APPLE;50\ngrape,40\n"})
    assert r.status_code == 201
    r = client.put("/api/wordlists/imports/s", json={"add_words": ["lemon"]})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert _lines(wl_dir, "imports/s.txt") == ["APPLE;50", "GRAPE;40", "LEMON"]


def test_put_remove_words_keeps_other_scores(client, wl_dir):
    client.post("/api/wordlists/import", json={"name": "s", "content": "APPLE;50\ngrape,40\nlemon\n"})
    r = client.put("/api/wordlists/imports/s", json={"remove_words": ["lemon"]})
    assert r.status_code == 200
    assert _lines(wl_dir, "imports/s.txt") == ["APPLE;50", "GRAPE;40"]


def test_put_add_to_missing_list_is_404(client, wl_dir):
    r = client.put("/api/wordlists/imports/nope", json={"add_words": ["cat"]})
    assert r.status_code == 404
    assert _everything(wl_dir) == ["metadata.json"]


def test_put_replace_words_keeps_score_entry_canonical(client, wl_dir):
    client.post("/api/wordlists/import", json={"name": "s", "content": "CAT\n"})
    r = client.put("/api/wordlists/imports/s", json={"words": ["apple;50", " grape ", ""]})
    assert r.status_code == 200
    assert _lines(wl_dir, "imports/s.txt") == ["APPLE;50", "GRAPE"]


def test_manager_bare_entry_does_not_overwrite_scored_line(tmp_path):
    (tmp_path / "y.txt").write_text("CAT;50\n")
    m = WordListManager(wordlist_dir=str(tmp_path))
    m.add_words("y", ["cat", "dog"])
    assert (tmp_path / "y.txt").read_text().splitlines() == ["CAT;50", "DOG"]


def test_manager_scored_entry_replaces_existing_score(tmp_path):
    (tmp_path / "y.txt").write_text("CAT;50\nDOG\n")
    m = WordListManager(wordlist_dir=str(tmp_path))
    m.add_words("y", ["cat;70", "dog;10"])
    assert (tmp_path / "y.txt").read_text().splitlines() == ["CAT;70", "DOG;10"]


# --- I3 ---------------------------------------------------------------------


def test_import_absolute_category_writes_nothing(client, wl_dir, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    r = client.post("/api/wordlists/import", json={"name": "n", "content": "CAT\n", "category": str(outside)})
    assert r.status_code in (400, 403)
    assert "error" in r.get_json()
    assert list(outside.iterdir()) == []
    assert _everything(wl_dir) == ["metadata.json"]


def test_import_dotdot_category_writes_nothing(client, wl_dir, tmp_path):
    r = client.post("/api/wordlists/import", json={"name": "n", "content": "CAT\n", "category": "../.."})
    assert r.status_code in (400, 403)
    assert _everything(tmp_path) == ["wl/metadata.json"]


def test_import_dotdot_name_writes_nothing(client, wl_dir, tmp_path):
    r = client.post("/api/wordlists/import", json={"name": "../escape", "content": "CAT\n"})
    assert r.status_code in (400, 403)
    assert _everything(tmp_path) == ["wl/metadata.json"]


def test_import_absolute_name_writes_nothing(client, wl_dir, tmp_path):
    r = client.post("/api/wordlists/import", json={"name": str(tmp_path / "abs"), "content": "CAT\n"})
    assert r.status_code in (400, 403)
    assert _everything(tmp_path) == ["wl/metadata.json"]


def test_import_into_builtin_category_is_403(client, wl_dir):
    r = client.post("/api/wordlists/import", json={"name": "zz", "content": "CAT\n", "category": "core"})
    assert r.status_code == 403
    assert r.get_json()["builtin"] is True
    assert _everything(wl_dir) == ["metadata.json"]


def test_import_non_string_category_or_name_is_400(client, wl_dir):
    for body in ({"name": 5, "content": "CAT\n"}, {"name": "n", "content": "CAT\n", "category": ["x"]}):
        r = client.post("/api/wordlists/import", json=body)
        assert r.status_code == 400
    assert _everything(wl_dir) == ["metadata.json"]


def test_import_dry_run_with_escaping_path_is_refused_too(client, wl_dir):
    r = client.post("/api/wordlists/import", json={"name": "n", "content": "CAT\n", "category": "..", "dry_run": True})
    assert r.status_code in (400, 403)


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_other_write_routes_refuse_escaping_names(client, wl_dir, tmp_path, method):
    body = {"words": ["cat"], "add_words": ["cat"]}
    call = getattr(client, method)
    r = call("/api/wordlists/custom/../../esc", json=body) if method != "delete" else call("/api/wordlists/custom/../../esc")
    assert r.status_code == 400
    assert _everything(tmp_path) == ["wl/metadata.json"]


def test_create_with_dotdot_segment_writes_nothing(client, wl_dir, tmp_path):
    # Drive the view function directly: the test client may normalise the URL.
    with app.test_request_context(json={"words": ["cat"]}, method="POST"):
        resp, status = wordlist_routes.create_wordlist("custom/../../esc")
    assert status in (400, 403)
    assert _everything(tmp_path) == ["wl/metadata.json"]


# --- Minor: non-string content ---------------------------------------------


@pytest.mark.parametrize("content", [None, 5, ["CAT"], {"a": 1}])
def test_import_non_string_content_is_400(client, wl_dir, content):
    r = client.post("/api/wordlists/import", json={"name": "n", "content": content})
    assert r.status_code == 400
    assert "error" in r.get_json()
    assert _everything(wl_dir) == ["metadata.json"]
