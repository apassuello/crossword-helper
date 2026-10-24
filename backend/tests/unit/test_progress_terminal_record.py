"""
Task 3.5 -- the tracker keeps its terminal event for 60 s and `generate()` re-sends it
(novice-readiness spec 0.2.5 section 2.4, #41).

Before this, `generate()`'s `finally:` removed the tracker, so a second subscriber or a
reconnect after the first one consumed the terminal event got a 404 or hung. Cases tr1-tr8
are the spec's normative rows; the extra tests pin what the criteria imply.

Streams are driven by iterating `stream_progress`'s response generator directly inside a
request context (the test client would eagerly pull the first chunk and break ordering).
"""

import json
import subprocess

import pytest

from backend.api import progress_routes as pr


@pytest.fixture
def app():
    from backend.app import create_app

    return create_app(testing=True)


@pytest.fixture(autouse=True)
def fast_queue(monkeypatch):
    monkeypatch.setattr(pr, "QUEUE_TIMEOUT_SECONDS", 0.1)


@pytest.fixture
def task_id():
    tid = pr.create_progress_tracker()
    yield tid
    pr.cleanup_progress_tracker(tid)


def _subscribe(app, tid):
    """Return the SSE generator for `tid` (lazy: nothing runs until next())."""
    with app.test_request_context(f"/api/progress/{tid}"):
        resp = pr.stream_progress(tid)
    assert not isinstance(resp, tuple), f"expected a stream, got {resp[0].get_json()}"
    return iter(resp.response)


def _data(frame):
    assert frame.startswith("data: "), frame
    return json.loads(frame[len("data: ") :])


def _drain(gen, limit=5):
    """Frames until the generator ends, failing rather than hanging past `limit` frames."""
    frames = []
    for frame in gen:
        frames.append(frame)
        assert len(frames) <= limit, f"stream did not end: {frames}"
    return frames


def test_tr1_second_subscriber_gets_the_recorded_complete(app, task_id):
    a = _subscribe(app, task_id)
    assert next(a) == ": heartbeat\n\n"  # A is connected before the terminal event exists
    pr.send_progress(task_id, 100, "done", "complete", {"grid": "G"})
    a_frames = _drain(a)
    assert [_data(f)["status"] for f in a_frames] == ["complete"]
    assert pr.progress_queues[task_id].empty()  # A consumed the queue copy; only the record is left

    b_frames = _drain(_subscribe(app, task_id))

    assert len(b_frames) == 1
    assert _data(b_frames[0]) == _data(a_frames[0])
    assert _data(b_frames[0])["data"] == {"grid": "G"}


def test_tr2_subscriber_that_lost_the_queue_race_gets_the_record_on_timeout(app, task_id):
    a, b = _subscribe(app, task_id), _subscribe(app, task_id)
    assert next(a) == ": heartbeat\n\n"  # both connected and waiting, no terminal yet
    assert next(b) == ": heartbeat\n\n"

    pr.send_progress(task_id, 100, "done", "complete")
    a_frames = _drain(a)  # A takes the one queued copy
    assert [_data(f)["status"] for f in a_frames] == ["complete"]

    b_frames = _drain(b)  # B's get() times out (0.1 s), finds the record, ends

    assert [_data(f)["status"] for f in b_frames] == ["complete"]


def test_tr3_disconnect_mid_run_keeps_the_tracker(app, task_id):
    gen = _subscribe(app, task_id)
    assert next(gen) == ": heartbeat\n\n"
    gen.close()  # client goes away; generate() has no finally, so nothing is cleaned up

    assert task_id in pr.progress_queues
    assert app.test_client().get(f"/api/progress/{task_id}").status_code == 200


def test_tr4_tracker_kept_at_exactly_the_retention_boundary(task_id):
    pr.send_progress(task_id, 100, "done", "complete")
    t0 = pr.terminal_events[task_id][1]

    removed = pr.sweep_expired_trackers(now=t0 + 60)

    assert task_id not in removed  # other tests' retained trackers may be swept; ours must not be
    assert task_id in pr.progress_queues


def test_tr5_tracker_swept_just_past_retention(app, task_id):
    pr.send_progress(task_id, 100, "done", "complete")
    t0 = pr.terminal_events[task_id][1]

    removed = pr.sweep_expired_trackers(now=t0 + 60.001)

    assert task_id in removed
    assert task_id not in pr.progress_queues
    assert task_id not in pr.max_progress_per_task
    assert task_id not in pr.terminal_events
    assert app.test_client().get(f"/api/progress/{task_id}").status_code == 404


def test_tr6_tracker_without_terminal_event_is_never_swept(task_id):
    pr.send_progress(task_id, 10, "working", "running")

    assert task_id not in pr.sweep_expired_trackers(now=float("inf"))
    assert task_id in pr.progress_queues


def test_tr7_timeout_error_is_recorded(task_id, mocker):
    from backend.api import routes

    class _Hangs:
        pid = 0
        stdout = None
        stderr = type("E", (), {"readline": staticmethod(lambda: "")})()
        returncode = None

        def communicate(self, timeout=None):
            raise subprocess.TimeoutExpired("fill", timeout)

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return -15

        def kill(self):
            pass

        def poll(self):
            return -15

    mocker.patch.object(routes.subprocess, "Popen", return_value=_Hangs())
    mocker.patch.object(routes.cli_adapter, "cli_path", __import__("pathlib").Path("/fake/crossword"))

    routes.run_cli_with_progress(task_id, ["fill"], timeout=1)

    ev = pr.get_terminal_event(task_id)
    assert ev is not None
    assert (ev["status"], ev["message"]) == ("error", "Operation timed out")


def test_tr8_paused_is_recorded_and_resent(app, task_id):
    pr.send_progress(task_id, 40, "Paused", "paused", {"paused": True})
    assert [_data(f)["status"] for f in _drain(_subscribe(app, task_id))] == ["paused"]
    assert pr.get_terminal_event(task_id)["status"] == "paused"

    again = _drain(_subscribe(app, task_id))

    assert [_data(f)["status"] for f in again] == ["paused"]


def test_running_events_are_not_recorded(task_id):
    pr.send_progress(task_id, 10, "working", "running")

    assert pr.get_terminal_event(task_id) is None
    assert task_id not in pr.terminal_events


def test_subscriber_sends_one_terminal_event_not_queue_copy_plus_record(app, task_id):
    pr.send_progress(task_id, 100, "done", "complete")

    frames = _drain(_subscribe(app, task_id))

    assert [_data(f)["status"] for f in frames] == ["complete"]


def test_cleanup_removes_the_terminal_record(task_id):
    pr.send_progress(task_id, 100, "done", "complete")

    pr.cleanup_progress_tracker(task_id)

    assert pr.get_terminal_event(task_id) is None


def test_stream_request_sweeps_expired_trackers_before_the_404_check(app):
    tid = pr.create_progress_tracker()
    pr.send_progress(tid, 100, "done", "complete")
    event, _ = pr.terminal_events[tid]
    pr.terminal_events[tid] = (event, event["timestamp"] - 61)  # recorded 61 s ago

    assert app.test_client().get(f"/api/progress/{tid}").status_code == 404
    assert tid not in pr.progress_queues


def test_queue_timeout_sweeps_expired_trackers(app, task_id):
    gen = _subscribe(app, task_id)  # the request-start sweep has already run
    old = pr.create_progress_tracker()
    pr.send_progress(old, 100, "done", "complete")
    event, _ = pr.terminal_events[old]
    pr.terminal_events[old] = (event, event["timestamp"] - 61)

    assert next(gen) == ": heartbeat\n\n"  # get() times out -> Empty -> sweep

    assert old not in pr.progress_queues


def test_queue_timeout_that_finds_the_record_still_sweeps_expired_trackers(app, task_id):
    gen = _subscribe(app, task_id)
    assert next(gen) == ": heartbeat\n\n"  # no terminal event yet; waiting on the queue
    old = pr.create_progress_tracker()
    pr.send_progress(old, 100, "done", "complete")
    event, _ = pr.terminal_events[old]
    pr.terminal_events[old] = (event, event["timestamp"] - 61)
    pr.send_progress(task_id, 100, "Complete", "complete")
    pr.progress_queues[task_id].get_nowait()  # another subscriber took it; only the record remains

    assert _data(next(gen))["status"] == "complete"  # Empty -> record found -> ends

    assert old not in pr.progress_queues


def test_first_terminal_event_is_the_one_recorded(task_id):
    pr.send_progress(task_id, 40, "Paused", "paused")
    pr.send_progress(task_id, 100, "Complete", "complete")  # trailing sentinel

    assert pr.get_terminal_event(task_id)["status"] == "paused"
