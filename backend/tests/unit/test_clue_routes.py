"""
Route tests for POST /api/clues/check (clue-authoring spec 0.1.4 section 3.6).

The subprocess layer is mocked at class level (CLIAdapter._run_command), so
the real adapter's JSON handling runs. Every row asserts the status code first.
"""

import json
import subprocess
from unittest.mock import patch

import pytest

from backend.core.cli_adapter import CLIAdapter

URL = "/api/clues/check"
BODY = {"size": 5, "grid": [["."] * 5 for _ in range(5)], "clues": {}}
MARKER = "NOT-JSON-MARKER-7f3a"


@pytest.fixture
def client():
    from backend.app import create_app

    app = create_app(testing=True)
    with app.test_client() as c:
        yield c


def _post(client, body):
    return client.post(URL, data=json.dumps(body), content_type="application/json")


def _error(resp):
    err = resp.get_json()["error"]
    return err["code"], err["message"]


def _patched(stdout, returncode=0):
    return patch.object(CLIAdapter, "_run_command", return_value=(stdout, "", returncode))


def test_success_replies_200_with_the_cli_json(client):
    cli_json = {"success": True, "statuses": {"0,0,across": "stale"}}
    with _patched(json.dumps(cli_json), 0):
        resp = _post(client, BODY)
    assert resp.status_code == 200
    assert resp.get_json() == cli_json


def test_invalid_clues_replies_400_with_the_cli_message(client):
    out = {"success": False, "code": "INVALID_CLUES", "error": "Invalid clues: must be an object."}
    with _patched(json.dumps(out), 1):
        resp = _post(client, BODY)
    assert resp.status_code == 400
    assert _error(resp) == ("INVALID_CLUES", "Invalid clues: must be an object.")


def test_other_cli_failure_replies_400_invalid_grid(client):
    out = {"success": False, "error": "Grid must be 5x5, got 1 rows"}
    with _patched(json.dumps(out), 1):
        resp = _post(client, BODY)
    assert resp.status_code == 400
    assert _error(resp) == ("INVALID_GRID", "Grid must be 5x5, got 1 rows")


def test_body_without_size_replies_400_invalid_grid_and_runs_nothing(client):
    with patch.object(CLIAdapter, "_run_command") as run:
        resp = _post(client, {"grid": BODY["grid"], "clues": {}})
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "INVALID_GRID"
        assert run.call_count == 0


def test_non_json_output_replies_500_with_a_fixed_message_and_no_leak(client):
    with _patched(MARKER, 0):
        resp = _post(client, BODY)
    assert resp.status_code == 500
    assert _error(resp) == ("INTERNAL_ERROR", "Clue check returned unreadable output")
    assert (MARKER in resp.get_data(as_text=True)) is False


def test_empty_stdout_exit_two_replies_500_with_the_same_message(client):
    with _patched("", 2):
        resp = _post(client, BODY)
    assert resp.status_code == 500
    assert _error(resp) == ("INTERNAL_ERROR", "Clue check returned unreadable output")


def test_timeout_replies_504(client):
    with patch.object(CLIAdapter, "_run_command", side_effect=subprocess.TimeoutExpired(cmd="crossword", timeout=1)):
        resp = _post(client, BODY)
    assert resp.status_code == 504
    assert _error(resp) == ("TIMEOUT", "Clue check timed out")


# Same replies as /api/number gives (routes.py number_grid, lines 124-135): read, not guessed.


def test_non_json_content_type_replies_400_invalid_content_type(client):
    resp = client.post(URL, data="x", content_type="text/plain")
    assert resp.status_code == 400
    assert _error(resp) == ("INVALID_CONTENT_TYPE", "Content-Type must be application/json")


def test_malformed_json_replies_400_invalid_json(client):
    resp = client.post(URL, data="{bad", content_type="application/json")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "INVALID_JSON"


def test_empty_body_replies_400_invalid_json(client):
    resp = client.post(URL, data="", content_type="application/json")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "INVALID_JSON"


def test_json_null_body_replies_400_empty_body(client):
    resp = client.post(URL, data="null", content_type="application/json")
    assert resp.status_code == 400
    assert _error(resp) == ("EMPTY_BODY", "Request body cannot be empty")


@pytest.mark.parametrize("size, nonstandard", [(15, False), (11, False), (21, False), (5, True)])
def test_allow_nonstandard_follows_the_number_rule(client, size, nonstandard):
    body = {"size": size, "grid": [["."] * size for _ in range(size)], "clues": {}}
    with patch.object(CLIAdapter, "_run_command", return_value=('{"success": true, "statuses": {}}', "", 0)) as run:
        resp = _post(client, body)
        assert resp.status_code == 200
        argv = run.call_args[0][0]
        assert argv[:2] == ["clues", "check"]
        assert argv[-1:] == (["--allow-nonstandard"] if nonstandard else ["--json-output"])
