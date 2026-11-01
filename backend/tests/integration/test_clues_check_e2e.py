"""
Real-subprocess seam tests for POST /api/clues/check (clue-authoring spec 0.1.4,
sections 3.4, 3.5, 3.6 and 6.1 "Seam").

Flask test client -> real CLIAdapter -> real CLI subprocess. Nothing is mocked,
except in the argv contract test, which captures the adapter's argv and feeds
it to the real click parser in-process.

Deliberately UNMARKED (no `slow`): it must run in the default suite.
"""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from backend.core.cli_adapter import CLIAdapter

URL = "/api/clues/check"


@pytest.fixture
def client():
    from backend.app import create_app

    app = create_app(testing=True)
    with app.test_client() as c:
        yield c


def _grid5():
    """5x5 grid with one black square at (2,2); size 5 is non-standard."""
    grid = [["."] * 5 for _ in range(5)]
    grid[2][2] = "#"
    return grid


def _post(client, body):
    return client.post(URL, data=json.dumps(body), content_type="application/json")


def _error(resp):
    err = resp.get_json()["error"]
    return err["code"], err["message"]


def test_argv_contract_real_click_parser_accepts_the_adapters_arguments(tmp_path):
    """Spec 6.1 Seam bullet 1: parse the actual argv, not just --help."""
    from cli.src.cli import cli

    doc = {"size": 5, "grid": _grid5(), "clues": {"0,0,across": {"text": "A clue", "answer": "?????"}}}
    adapter = CLIAdapter()
    ok = ('{"success": true, "statuses": {}}', "", 0)
    with patch.object(CLIAdapter, "_run_command", return_value=ok) as run:
        adapter.clues_check(doc, allow_nonstandard=True)
    argv = list(run.call_args[0][0])

    real = tmp_path / "grid.json"
    real.write_text(json.dumps(doc))
    argv[2] = str(real)

    result = CliRunner().invoke(cli, argv)

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {"success": True, "statuses": {"0,0,across": "ok"}}


def test_statuses_ok_stale_and_orphaned_reach_the_browser(client):
    clues = {
        "0,0,across": {"text": "Fine", "answer": "?????"},
        "1,0,across": {"text": "Changed", "answer": "ABCDE"},
        "2,2,across": {"text": "Gone", "answer": "??"},
    }
    resp = _post(client, {"size": 5, "grid": _grid5(), "clues": clues})
    assert resp.status_code == 200
    assert resp.get_json() == {
        "success": True,
        "statuses": {"0,0,across": "ok", "1,0,across": "stale", "2,2,across": "orphaned"},
    }


def test_rule_four_failure_is_a_400_invalid_clues_with_the_spec_message(client):
    clues = {"0,0,across": {"text": "trailing ", "answer": "?????"}}
    resp = _post(client, {"size": 5, "grid": _grid5(), "clues": clues})
    assert resp.status_code == 400
    assert _error(resp) == (
        "INVALID_CLUES",
        'Invalid clue "0,0,across": text must not start or end with whitespace.',
    )


def test_null_clues_is_a_400_invalid_clues(client):
    resp = _post(client, {"size": 5, "grid": _grid5(), "clues": None})
    assert resp.status_code == 400
    assert _error(resp) == ("INVALID_CLUES", "Invalid clues: must be an object.")


def test_empty_clues_object_is_a_200_with_no_statuses(client):
    resp = _post(client, {"size": 5, "grid": _grid5(), "clues": {}})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "statuses": {}}


def test_missing_clues_key_is_a_200_with_no_statuses(client):
    resp = _post(client, {"size": 5, "grid": _grid5()})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "statuses": {}}


def test_grid_the_cli_cannot_load_is_a_400_invalid_grid_with_the_cli_text(client):
    # validate_grid_request accepts this (size int in 3-50, grid a list of lists);
    # the CLI rejects it at load: `crossword clues check <file> --json-output
    # --allow-nonstandard` prints {"success": false, "error": "Grid must be 5x5, got 1 rows"}
    # (with U+00D7 as the multiplication sign) and exits 1.
    resp = _post(client, {"size": 5, "grid": [["."]], "clues": {}})
    assert resp.status_code == 400
    assert _error(resp) == ("INVALID_GRID", "Grid must be 5×5, got 1 rows")
