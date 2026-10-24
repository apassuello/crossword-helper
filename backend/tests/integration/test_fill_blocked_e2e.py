"""
Real-subprocess seam test for a blocked fill (novice-readiness spec 0.2.5
section 2.2, B3 and C4).

POST /api/fill/with-progress runs the real CLI; the task's SSE queue is read
until a terminal event. E4 pins that a blocked result (exit 3) arrives as
a `complete` event carrying the blocked payload. E4b pins the lock channel:
the route's `"locked"` key is the only thing that stops the CLI treating Q and
X as free (`--lock-filled` alone locks every letter when the key is absent, so
E4 cannot tell). E5 pins that the CLI's off-list ("C4") stderr event crosses
`_pump_stderr` as a `running` event.

Deliberately UNMARKED (no `slow`): it must run in the default suite.
"""

import json
import queue
import time

import pytest

from backend.api import progress_routes

TERMINAL = ("complete", "error", "paused")
L5_LINES = "COD;50\nALE;50\nBEE;50\nOLE;50\nDEE;50\n"


@pytest.fixture
def client():
    from backend.app import create_app

    app = create_app(testing=True)
    with app.test_client() as c:
        yield c


def _events_until_terminal(task_id, limit=120):
    q = progress_routes.progress_queues[task_id]
    events = []
    deadline = time.time() + limit
    while time.time() < deadline:
        try:
            ev = q.get(timeout=1)
        except queue.Empty:
            continue
        events.append(ev)
        if ev.get("status") in TERMINAL:
            return events
    pytest.fail(f"no terminal event within {limit}s; got {events}")


def _post(client, body):
    resp = client.post("/api/fill/with-progress", data=json.dumps(body), content_type="application/json")
    assert resp.status_code == 202, resp.get_data(as_text=True)
    return resp.get_json()["task_id"]


def test_e4_blocked_fill_is_a_complete_event_carrying_the_blocked_result(client):
    grid = [["."] * 5 for _ in range(5)]
    grid[0][0], grid[0][1] = "Q", "X"
    task_id = _post(
        client,
        {"size": 5, "grid": grid, "locked_cells": [[0, 0], [0, 1]], "wordlists": ["comprehensive"]},
    )

    terminal = _events_until_terminal(task_id)[-1]

    assert terminal["status"] == "complete", terminal
    data = terminal["data"]
    assert data["blocked"] is True
    assert data["reason"] == "no_word_fits"
    assert data["blocked_cells"] == [[0, 0], [0, 1]]
    assert data["blocked_slots"] == [{"row": 0, "col": 0, "direction": "across", "length": 5, "pattern": "QX???"}]


def test_e5_off_list_event_crosses_the_stderr_pump_as_running(client, tmp_path, monkeypatch):
    from backend.api import routes

    words = tmp_path / "l5.txt"
    words.write_text(L5_LINES)
    monkeypatch.setattr(routes, "resolve_wordlist_paths_strict", lambda names: ([str(words)], []))
    grid = [["."] * 3 for _ in range(3)]
    grid[0] = ["C", "A", "B"]
    task_id = _post(
        client,
        {
            "size": 3,
            "grid": grid,
            "locked_cells": [[0, 0], [0, 1], [0, 2]],
            "wordlists": ["l5"],
            "algorithm": "repair",
            "timeout": 10,
        },
    )

    events = _events_until_terminal(task_id)

    expected = {"off_list_cells": [[0, 0], [0, 1], [0, 2]], "warning": "Typed words not in the selected word lists: CAB"}
    off_list = [e for e in events[:-1] if e.get("status") == "running" and e.get("data") == expected]
    assert off_list, events


def test_e4b_empty_locked_cells_reaches_the_cli_and_nothing_is_locked(client):
    grid = [["."] * 5 for _ in range(5)]
    grid[0][0], grid[0][1] = "Q", "X"
    task_id = _post(
        client,
        {"size": 5, "grid": grid, "locked_cells": [], "wordlists": ["comprehensive"], "timeout": 10},
    )

    terminal = _events_until_terminal(task_id)[-1]

    assert terminal["status"] == "complete", terminal
    data = terminal["data"]
    assert data["blocked"] is False, data
    assert data["success"] is True, data
    assert data["all_slots_filled"] is True, data
    assert data["grid"][0][:2] != ["Q", "X"], data["grid"]
