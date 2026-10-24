"""
Lock channel on /api/fill/with-progress (novice-readiness spec 0.2.5 section 2.2).

`locked_cells` in the request body becomes the grid file's `"locked"` key, and
`--lock-filled` is in the argv on every request. Thread is patched, so no real
CLI runs; the grid file is read from argv[1].
"""

import json

import pytest

from backend.tests.response_diag import resp_diag

_UNSET = object()


@pytest.fixture
def client(mocker):
    mock_adapter = mocker.MagicMock()
    mock_adapter.health_check.return_value = True
    mocker.patch("backend.api.routes.get_adapter", return_value=mock_adapter)
    mocker.patch("backend.api.routes.cli_adapter", mock_adapter)
    mocker.patch(
        "backend.api.routes.resolve_wordlist_paths",
        return_value=["/fake/wordlists/comprehensive.txt"],
    )
    from backend.app import create_app

    app = create_app(testing=True)
    with app.test_client() as c:
        yield c


def _body(locked=_UNSET):
    grid = [["."] * 5 for _ in range(5)]
    grid[0][0] = "A"
    body = {"size": 5, "grid": grid}
    if locked is not _UNSET:
        body["locked_cells"] = locked
    return body


def _post(client, body):
    return client.post("/api/fill/with-progress", data=json.dumps(body), content_type="application/json")


@pytest.mark.parametrize("locked", [[[0, 0]], []])
def test_locked_cells_written_to_grid_file_and_flag_passed(client, mocker, locked):
    thread = mocker.patch("backend.api.routes.threading.Thread")

    resp = _post(client, _body(locked))

    assert resp.status_code == 202, resp_diag(resp)
    argv = thread.call_args.kwargs["args"][1]
    with open(argv[1]) as f:
        grid_file = json.load(f)
    assert "locked" in grid_file
    assert grid_file["locked"] == locked
    assert "--lock-filled" in argv


def test_absent_locked_cells_writes_no_key_but_passes_flag(client, mocker):
    thread = mocker.patch("backend.api.routes.threading.Thread")

    resp = _post(client, _body())

    assert resp.status_code == 202, resp_diag(resp)
    argv = thread.call_args.kwargs["args"][1]
    with open(argv[1]) as f:
        grid_file = json.load(f)
    assert "locked" not in grid_file
    assert "--lock-filled" in argv


def test_null_locked_cells_is_400_and_starts_nothing(client, mocker):
    thread = mocker.patch("backend.api.routes.threading.Thread")
    spy = mocker.spy(__import__("tempfile"), "NamedTemporaryFile")

    resp = _post(client, _body(None))

    assert resp.status_code == 400, resp_diag(resp)
    payload = resp.get_json()
    assert payload["error"]["code"] == "INVALID_REQUEST"
    assert "locked_cells" in payload["error"]["message"]
    assert not thread.called
    assert spy.call_count == 0


# --- Ceiling (novice-readiness spec 0.2.5 section 2.2 B4, P7) ---------------


def _ceiling_cases():
    from backend.core.cli_adapter import CLI_STARTUP_BUDGET_SECONDS as B

    return [(60, 60 + B), (_UNSET, 300 + B)]


@pytest.mark.parametrize("timeout,expected_idx", [(60, 0), (_UNSET, 1)])
def test_thread_ceiling_and_ceiling_seconds_use_startup_budget(client, mocker, timeout, expected_idx):
    thread = mocker.patch("backend.api.routes.threading.Thread")
    body = _body()
    if timeout is not _UNSET:
        body["timeout"] = timeout
    expected = _ceiling_cases()[expected_idx][1]

    resp = _post(client, body)

    assert resp.status_code == 202, resp_diag(resp)
    assert thread.call_args.kwargs["args"][2] == expected
    payload = resp.get_json()
    assert payload["ceiling_seconds"] == expected
    assert set(payload) == {"task_id", "progress_url", "ceiling_seconds"}


# --- Exit 3 and CLI error text (novice-readiness spec 0.2.5 section 2.2, B3; PD-3-KILL) ---

BLOCKED_STDOUT = {
    "success": False,
    "blocked": True,
    "reason": "no_word_fits",
    "blocked_slots": [{"row": 0, "col": 0, "direction": "across", "length": 3, "pattern": "QX?"}],
    "blocked_cells": [[0, 0], [0, 1]],
    "off_list_cells": [],
    "stuck_cells": [],
    "grid": [["Q", "X", "."], [".", ".", "."], [".", ".", "."]],
}
LOCKED_MSG = "Autofill changed a locked letter; nothing was written."


class _FakeProcess:
    """A finished child: stderr is empty, stdout and returncode are canned."""

    def __init__(self, stdout, returncode):
        import io

        self.stdout_text = stdout
        self.returncode = returncode
        self.stderr = io.StringIO("")
        self.pid = 0

    def communicate(self, timeout=None):
        return self.stdout_text, ""

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode


def _terminal_event(mocker, stdout, returncode):
    """Run run_cli_with_progress with a canned child; return its terminal send_progress call."""
    from backend.api import routes

    mocker.patch.object(routes.subprocess, "Popen", return_value=_FakeProcess(stdout, returncode))
    sent = []
    mocker.patch.object(routes, "send_progress", lambda *a, **k: sent.append(a))
    mocker.patch.object(routes.cli_adapter, "cli_path", __import__("pathlib").Path("/fake/crossword"))

    routes.run_cli_with_progress("task-x", ["fill"], timeout=5)

    terminals = [c for c in sent if c[3] in ("complete", "error", "paused")]
    assert len(terminals) == 1, sent
    return terminals[0]


def test_e1_exit_3_with_blocked_json_is_complete_with_the_json(mocker):
    call = _terminal_event(mocker, json.dumps(BLOCKED_STDOUT), 3)

    assert call[3] == "complete"
    assert call[4] == BLOCKED_STDOUT


def test_e2_exit_3_unparseable_stdout_is_error(mocker):
    call = _terminal_event(mocker, "not json", 3)

    assert call[3] == "error"
    assert call[2].startswith("CLI Error (code 3)")


def test_e3_exit_3_without_blocked_true_is_error(mocker):
    call = _terminal_event(mocker, '{"success": false}', 3)

    assert call[3] == "error"


def test_e6_exit_1_string_error_is_the_message_verbatim(mocker):
    call = _terminal_event(mocker, json.dumps({"success": False, "error": LOCKED_MSG}), 1)

    assert call[3] == "error"
    assert call[2] == LOCKED_MSG


def test_e7_killed_child_keeps_cli_error_text(mocker):
    call = _terminal_event(mocker, json.dumps({"success": False, "error": LOCKED_MSG}), -9)

    assert call[3] == "error"
    assert call[2].startswith("CLI Error (code -9)")


def test_e8_non_string_error_keeps_cli_error_text(mocker):
    call = _terminal_event(mocker, '{"success": false, "error": 5}', 1)

    assert call[3] == "error"
    assert call[2].startswith("CLI Error (code 1)")


def test_e9_non_json_stdout_keeps_cli_error_text(mocker):
    call = _terminal_event(mocker, "not json", 1)

    assert call[3] == "error"
    assert call[2].startswith("CLI Error (code 1)")
