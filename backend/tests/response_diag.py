"""Assertion messages for Flask test-client responses.

A bare `assert response.status_code == 200` fails as `assert 500 == 200`. The body
that would say *why* — the route's error payload, and for a 500 the exception
message — is discarded, and no rerun of the assertion as written recovers it. CI
run 32230539895 lost a subprocess failure the same way; see `_diag` in
cli/tests/integration/test_fill_pause_resume.py for the child-process equivalent.
"""

from typing import Any


def resp_diag(response: Any, limit: int = 800) -> str:
    """Status plus a truncated body for a Flask test response.

    Two things this must never do, since a message expression is evaluated only
    when the assertion is already failing:

    - **Raise.** A raising message replaces the assertion failure with its own
      traceback, which is strictly worse than the bare assert. Hence `get_data`
      rather than `get_json`, which raises on a non-JSON body, and the guard.
    - **Drain an SSE stream.** `get_data()` consumes the response iterable; on a
      `text/event-stream` route backed by a long-running fill that turns a clean
      assertion failure into a hang, so those report status only.

    The guard is on the mimetype, deliberately not on `is_streamed`: Werkzeug's
    test client iterates lazily, so `is_streamed` is True for *every* test
    response including a plain 404, and guarding on it suppressed every body.
    """
    status = getattr(response, "status_code", "?")
    if getattr(response, "mimetype", None) == "text/event-stream":
        return f"HTTP {status} (SSE stream; body deliberately not drained)"
    try:
        body = response.get_data(as_text=True)
    except Exception as exc:  # noqa: BLE001 - diagnostics must never raise
        body = f"<unreadable body: {exc!r}>"
    return f"HTTP {status} body: {body[:limit]}"
