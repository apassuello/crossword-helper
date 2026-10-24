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
