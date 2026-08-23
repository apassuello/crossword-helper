"""
Integration tests for two bugs in `run_cli_with_progress`
(backend/api/routes.py):

- #22: the stderr pump (routes.py:301-305) reads on the calling thread with
  a plain `readline()` loop. `readline()` returns "" only at OS-level EOF,
  which on a child's stderr pipe only happens when the child exits. A child
  that hangs without writing to or closing stderr blocks the loop forever,
  so `process.communicate(timeout=timeout)` at routes.py:335 is unreachable
  and `timeout` is inert.
- #21 sub-item 1: `register_process(task_id, process)` (routes.py:295) has no
  matching removal on the normal-completion path -- only `cleanup_process`
  (the cancel route's job) ever pops the registry -- so a completed fill
  leaves a dead Popen in `running_processes` forever.

Both need a REAL subprocess: the #22 bug is OS-level pipe blocking, which no
mock reproduces (see backend/tests/unit/test_routes.py's own docstring: "All
CLI adapter calls are mocked" -- that file is the wrong place for this).

This file is deliberately UNMARKED (no @pytest.mark.slow). pytest.ini sets
`addopts = -m "not slow"`, and the only job that opts back into `slow` is
`pause-resume-seam`, against four explicitly named files that do not include
this one -- a slow marker here would run nowhere (CONTRIBUTING.md sec. 3).
Living directly under backend/tests/integration means the ordinary `test`
job's explicit `pytest backend/tests/integration ...` path arg collects it.
"""

import sys
import threading
import uuid
from pathlib import Path

import pytest

from backend.api import progress_routes, routes
from backend.api.progress_routes import running_processes, running_processes_lock

# Generous slack over the harness timeout below -- not tight enough to be
# load-flaky, but tight enough that a real hang (join never returning until
# the child's own exit) fails deterministically rather than after minutes.
JOIN_BOUND_SECONDS = 10
HARNESS_TIMEOUT_SECONDS = 1


def _hang_forever_cmd_args():
    """A synthetic child with NO deadline of its own. If the child
    self-terminated within any bound, buggy and fixed code would converge
    on the same terminal state and the test would pass either way -- there
    must be nothing here for the child to time out on, so the only thing
    that can stop it is the harness's own `timeout` argument."""
    return ["-c", "import time; time.sleep(3600)"]


@pytest.fixture
def python_as_cli(monkeypatch):
    """Point cli_adapter.cli_path at the real interpreter so cmd_args can
    spawn arbitrary child processes via `python -c ...`, and guarantee
    whatever process ends up registered under the yielded task_id is killed
    at teardown -- even if the code under test never returns. Without this,
    a RED run (join times out, thread still alive) abandons a live
    `sleep 3600` process on the machine.
    """
    monkeypatch.setattr(routes.cli_adapter, "cli_path", Path(sys.executable))
    task_id = f"test-sse-fill-timeout-{uuid.uuid4()}"
    yield task_id
    with running_processes_lock:
        process = running_processes.pop(task_id, None)
    if process is not None and process.poll() is None:
        process.kill()
        process.wait(timeout=5)


class TestSSEFillTimeoutEnforced:
    """Issue #22."""

    def test_hung_child_is_killed_within_harness_timeout(self, python_as_cli, monkeypatch):
        task_id = python_as_cli

        # #21 sub-item 1 (fixed in this same change) means the registry
        # entry is gone from running_processes by the time
        # run_cli_with_progress returns, even on this timeout path -- so
        # capture the process handle directly via a wrapped
        # register_process instead of reading it back out of the registry
        # afterward. `run_cli_with_progress` re-imports `register_process`
        # from this module by name on every call (routes.py, inline `from
        # .progress_routes import register_process`), so patching the
        # attribute here is what it picks up.
        captured = {}
        original_register = progress_routes.register_process

        def capturing_register(tid, proc):
            captured["process"] = proc
            return original_register(tid, proc)

        monkeypatch.setattr(progress_routes, "register_process", capturing_register)

        sent_calls = []
        # routes.py:15 binds `send_progress` at import time, so the patch
        # target must be the already-bound name in routes, not the source
        # module (backend.api.progress_routes) -- patching the source there
        # would not affect this reference.
        monkeypatch.setattr(routes, "send_progress", lambda *a, **k: sent_calls.append(a))

        thread = threading.Thread(
            target=routes.run_cli_with_progress,
            args=(task_id, _hang_forever_cmd_args(), HARNESS_TIMEOUT_SECONDS),
            daemon=True,
        )
        thread.start()
        thread.join(timeout=JOIN_BOUND_SECONDS)

        # RED (pre-fix): the stderr readline() loop never sees EOF because
        # the child never writes to or closes stderr, so this join times
        # out and the thread is still alive after JOIN_BOUND_SECONDS.
        # GREEN (post-fix): communicate(timeout=1) fires TimeoutExpired,
        # the child is terminated/killed, and the thread returns in ~1s.
        assert thread.is_alive() is False, (
            f"run_cli_with_progress did not return within {JOIN_BOUND_SECONDS}s "
            f"of a {HARNESS_TIMEOUT_SECONDS}s harness timeout -- the stderr "
            "pump is still blocking the calling thread (issue #22)"
        )

        process = captured.get("process")
        assert process is not None, "process was never registered"
        assert process.poll() is not None, "child was not reaped after the harness timeout fired"

        # Assert the *effect* of the TimeoutExpired handler firing (a
        # terminal "error" status sent), not merely that the function
        # returned -- returning could also mean it happened to finish for
        # an unrelated reason.
        terminal_error_calls = [c for c in sent_calls if len(c) >= 4 and c[3] == "error"]
        assert terminal_error_calls, f"expected a terminal 'error' send_progress call, got: {sent_calls}"


class TestRunningProcessesCleanup:
    """Issue #21 sub-item 1."""

    def test_registry_entry_removed_after_normal_completion(self, python_as_cli, monkeypatch):
        task_id = python_as_cli
        monkeypatch.setattr(routes, "send_progress", lambda *a, **k: None)

        # A quick, well-behaved child: exits immediately with returncode 0.
        routes.run_cli_with_progress(task_id, ["-c", "pass"], timeout=10)

        with running_processes_lock:
            still_registered = task_id in running_processes
        assert not still_registered, (
            "running_processes still holds the task after normal completion -- "
            "cleanup_process(task_id) is missing from run_cli_with_progress's "
            "finally block (issue #21 sub-item 1)"
        )


class TestNoProgressEventLoss:
    """A fix for #22 must not silently drop stderr progress events.

    `communicate()` drains stderr internally as well as stdout. Racing it
    against a dedicated `_pump_stderr` thread on the same pipe was verified
    (a standalone probe, 5 runs) to lose 2-3 of 20 progress lines per run to
    whichever reader won the race -- a line that lands in `communicate()`'s
    own buffer is never JSON-parsed and never reaches `send_progress`. That
    is a real regression: today, before any fix, there is exactly one
    reader on the pipe and nothing is lost.

    This test is the discriminator between the two ways #22 could be fixed:
    a `communicate(timeout=...)`-based design passes the two tests above
    but fails this one; a `process.wait(timeout=...)` design with a
    dedicated stdout-reader thread (so `wait()` never touches either pipe)
    passes all three.
    """

    def test_all_stderr_progress_lines_reach_send_progress(self, python_as_cli, monkeypatch):
        task_id = python_as_cli
        n_lines = 20

        sent_calls = []
        monkeypatch.setattr(routes, "send_progress", lambda *a, **k: sent_calls.append(a))

        # A well-behaved child that emits N distinct, individually-identifiable
        # progress events on stderr, then exits -- old-style '%' formatting
        # inside the child's own source avoids any ambiguity with this
        # (outer) string's own substitution.
        child_code = (
            "import sys, time, json\n"
            "for i in range(N_LINES):\n"
            "    print(json.dumps({'type': 'progress', 'progress': i, "
            "'message': 'line-%d' % i, 'status': 'running'}), file=sys.stderr, flush=True)\n"
            "    time.sleep(0.02)\n"
        ).replace("N_LINES", str(n_lines))

        routes.run_cli_with_progress(task_id, ["-c", child_code], timeout=10)

        seen_indices = set()
        for args in sent_calls:
            if len(args) >= 3 and isinstance(args[2], str) and args[2].startswith("line-"):
                seen_indices.add(int(args[2].split("-", 1)[1]))

        missing = sorted(set(range(n_lines)) - seen_indices)
        assert not missing, (
            f"lost {len(missing)}/{n_lines} stderr progress events to a reader race "
            f"-- missing indices {missing}. The #22 fix must not call communicate() "
            "on a pipe _pump_stderr also reads."
        )
