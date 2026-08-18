"""
Task 15 — backend resume wiring on /api/fill/with-progress.

Covers:
- DD2: every web fill argv carries --task-id + --state-dir + --pause-flag-dir.
- DD3: resume_task_id → --resume <state> when the prepared state exists, else 404.
- DD4: a paused stdout makes run_cli_with_progress emit a terminal `paused` and
       SUPPRESS the spurious `complete` (queue level).
- DD4b: `paused` joins the SSE generator's terminal-break set so the (synchronous)
        stream actually closes on the first paused event (generator level).

Route-spawned subprocess is mocked out (Thread/Popen patched) — no real CLI runs.
"""

import json

import pytest


@pytest.fixture
def client(mocker):
    """Flask test client with the CLI adapter + wordlist resolver mocked out."""
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
        yield c, mock_adapter


def _post_json(client, url, data):
    return client.post(url, data=json.dumps(data), content_type="application/json")


def _point_dirs_at(monkeypatch, tmp_path):
    """Deterministically bind routes.py's dir globals to tmp_path (constants are
    import-time, so setenv-after-import is a trap — patch the bound globals)."""
    import backend.api.routes as routes_mod

    monkeypatch.setattr(routes_mod, "STATE_DIR", tmp_path)
    monkeypatch.setattr(routes_mod, "PAUSE_FLAG_DIR", tmp_path)


# ---------------------------------------------------------------------------
# DD2 / DD3 — argv threading
# ---------------------------------------------------------------------------


def test_fresh_fill_threads_task_id_and_dirs(client, mocker, monkeypatch, tmp_path):
    """(a) A fresh fill argv carries --task-id + both dirs, and no --resume."""
    c, _ = client
    _point_dirs_at(monkeypatch, tmp_path)
    thread = mocker.patch("backend.api.routes.threading.Thread")

    resp = _post_json(c, "/api/fill/with-progress", {"size": 5, "grid": [["."] * 5] * 5})

    assert resp.status_code == 202
    argv = thread.call_args.kwargs["args"][1]
    assert "--task-id" in argv
    assert argv[argv.index("--state-dir") + 1] == str(tmp_path)
    assert argv[argv.index("--pause-flag-dir") + 1] == str(tmp_path)
    assert "--resume" not in argv


def test_resume_task_id_existing_state_adds_resume(client, mocker, monkeypatch, tmp_path):
    """(b) resume_task_id + an existing prepared state file → --resume <path>, still
    on a fresh SSE task-id (so the resumed run stays pausable)."""
    c, _ = client
    _point_dirs_at(monkeypatch, tmp_path)
    (tmp_path / "resume_abc12345.json.gz").write_bytes(b"x")  # route only checks .exists()
    thread = mocker.patch("backend.api.routes.threading.Thread")

    resp = _post_json(
        c,
        "/api/fill/with-progress",
        {"size": 5, "grid": [["."] * 5] * 5, "resume_task_id": "resume_abc12345"},
    )

    assert resp.status_code == 202
    argv = thread.call_args.kwargs["args"][1]
    assert argv[argv.index("--resume") + 1] == str(tmp_path / "resume_abc12345.json.gz")
    assert "--task-id" in argv  # fresh SSE id, distinct from the resume file basename


def test_resume_task_id_missing_state_returns_404(client, mocker, monkeypatch, tmp_path):
    """(c) resume_task_id with no prepared state → 404 TASK_NOT_FOUND (before any temp
    file is written; Thread is never started)."""
    c, _ = client
    _point_dirs_at(monkeypatch, tmp_path)
    thread = mocker.patch("backend.api.routes.threading.Thread")

    resp = _post_json(
        c,
        "/api/fill/with-progress",
        {"size": 5, "grid": [["."] * 5] * 5, "resume_task_id": "resume_missing"},
    )

    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "TASK_NOT_FOUND"
    thread.assert_not_called()


# ---------------------------------------------------------------------------
# DD4 — paused terminal branch (queue level)
# ---------------------------------------------------------------------------


class _FakePopen:
    """Popen double: streams one `paused` progress line on stderr then EOF, and
    returns a paused stdout protocol from communicate() with exit 0."""

    def __init__(self, *args, **kwargs):
        self.pid = 123
        self.returncode = 0
        self.stderr = self
        self._lines = iter(
            [
                json.dumps(
                    {
                        "type": "progress",
                        "progress": 40,
                        "message": "Paused: 4/10 slots filled",
                        "status": "paused",
                        "data": {"state_path": "x", "grid": []},
                    }
                )
                + "\n",
                "",  # EOF
            ]
        )

    def readline(self):
        return next(self._lines, "")

    def communicate(self, timeout=None):
        return (
            json.dumps({"paused": True, "task_id": "t", "slots_filled": 4, "total_slots": 10}),
            "",
        )


def test_paused_stdout_emits_paused_not_complete(mocker):
    """(d) DD4: a paused stdout yields a terminal `paused` event and NO `complete`."""
    mocker.patch("backend.api.routes.subprocess.Popen", _FakePopen)

    from backend.api.progress_routes import create_progress_tracker, progress_queues
    from backend.api.routes import run_cli_with_progress

    task_id = create_progress_tracker()
    run_cli_with_progress(task_id, ["fill", "g.json", "--json-output"])

    events, q = [], progress_queues[task_id]
    while not q.empty():
        events.append(q.get_nowait())
    statuses = [e.get("status") for e in events]

    assert "paused" in statuses
    assert "complete" not in statuses  # spurious complete suppressed


# ---------------------------------------------------------------------------
# DD4b — paused ends the SSE stream (generator level; what (d) cannot see)
# ---------------------------------------------------------------------------


def test_paused_event_terminates_sse_stream(client):
    """(e) DD4b: the generator breaks on the FIRST paused event and never reaches a
    trailing complete sentinel. Pre-fix it would yield paused THEN complete (fails
    fast, no hang — the sentinel guarantees termination either way)."""
    c, _ = client
    from backend.api.progress_routes import create_progress_tracker, send_progress

    task_id = create_progress_tracker()
    send_progress(task_id, 40, "Paused", "paused", {"state_path": "x"})
    send_progress(task_id, 100, "Complete", "complete", {})  # sentinel

    body = c.get(f"/api/progress/{task_id}").get_data(as_text=True)

    assert '"status": "paused"' in body
    assert '"status": "complete"' not in body  # broke on paused first
