"""
Task 19 — real-subprocess pause -> edit -> resume + pattern, through Flask (slow gate).

Zero mocks: real Flask app + real `python -m cli.src.cli fill ...` subprocess. This is
the batch gate proving Tasks 13-15 wire together — the pause-flag-dir + state-dir chain
and the resume-route round-trip — that no mocked unit test can prove.

META-RULE (binding): if this fails, fix Tasks 13-15, NEVER weaken the test. Debug order
when step 3 times out / 404s:
  1. state never appears -> the CLI never paused (Task 13: --task-id / PauseController).
  2. state 404s though the CLI paused -> split dir (Task 15: STATE_DIR == STATE_STORAGE_DIR
     + --state-dir on the argv).
  3. pause 200 but no state -> flag-dir mismatch (Task 15: PAUSE_FLAG_DIR both sides).

Distinct from the in-process `test_e2e_pause_resume.py` (which builds the algorithm
classes directly and never touches Flask). This is the HTTP-through-Flask gate.
"""

import time

import pytest

from backend.core.state_paths import PAUSE_FLAG_DIR
from backend.tests.integration.conftest import create_test_grid
from backend.tests.response_diag import resp_diag

pytestmark = pytest.mark.slow


def _await_state(client, task_id, deadline_s=10):
    """Poll GET /api/fill/state/<task_id> every 0.5s until the first 200; return its
    JSON, else None on timeout. The 10s deadline IS the F11 running.pausing guarantee."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        resp = client.get(f"/api/fill/state/{task_id}")
        if resp.status_code == 200:
            return resp.get_json()
        time.sleep(0.5)
    return None


def _clear_flag(task_id):
    """Best-effort removal of a task's pause flag from the shared flag dir."""
    try:
        (PAUSE_FLAG_DIR / f"crossword_pause_{task_id}.flag").unlink(missing_ok=True)
    except OSError:
        pass


def test_pause_edit_resume_roundtrip(client):
    """Blank 15x15 trie (exact-position CSP): fill -> pause -> saved state -> resume-prepare
    -> resume-fill. Gates the wiring, not fill quality (an all-white 15x15 is unsolvable)."""
    task_id = new_task_id = resp2 = None
    try:
        # 1. Start a real fill (spawns a real CLI subprocess).
        resp = client.post(
            "/api/fill/with-progress",
            json={
                "size": 15,
                "grid": create_test_grid(15),
                "wordlists": ["comprehensive"],
                "algorithm": "trie",
                "timeout": 120,
                "min_score": 10,
            },
        )
        assert resp.status_code == 202, resp_diag(resp)
        task_id = resp.get_json()["task_id"]
        assert task_id

        # 2. Let it get into backtracking, then request pause.
        time.sleep(3)
        p = client.post(f"/api/fill/pause/{task_id}")
        assert p.status_code == 200, resp_diag(p)
        assert p.get_json()["success"] is True

        # 3. Saved state must appear (where the route reads it) within the 10s F11 deadline.
        #    A miss here is a Tasks-13/15 wiring bug, not a test bug (see META-RULE).
        state = _await_state(client, task_id, 10)
        assert state is not None, "no saved state within the 10s F11 deadline — debug Tasks 13/15, not the test"
        assert "grid_preview" in state
        assert state["total_slots"] > 0
        assert state["algorithm"] == "csp"  # envelope state-format tag

        # 4. Resume: merges the (unmodified) edit, mints resume_<hex>, and runs the
        #    resumed fill synchronously (backend/api/pause_resume_routes.py:331-339).
        #    The blank 15x15 is an unsatisfiable position, so exact-position resume
        #    falls back to unwind-and-re-search (#9) and spends the whole timeout
        #    budget before reporting failure. timeout=3 keeps that path exercised
        #    without burning the 300s default. Passing grid_preview verbatim
        #    introduces no new empty domains.
        r = client.post(
            "/api/fill/resume",
            json={"task_id": task_id, "edited_grid": state["grid_preview"], "options": {"timeout": 3}},
        )
        assert r.status_code == 200, resp_diag(r)
        new_task_id = r.get_json()["new_task_id"]
        assert new_task_id.startswith("resume_")

        # 5. Resume-fill through the SSE route (targets the prepared state via resume_task_id).
        resp2 = client.post(
            "/api/fill/with-progress",
            json={
                "size": 15,
                "grid": create_test_grid(15),
                "wordlists": ["comprehensive"],
                "algorithm": "trie",
                "timeout": 120,
                "min_score": 10,
                "resume_task_id": new_task_id,
            },
        )
        assert resp2.status_code == 202, resp_diag(resp2)
        assert resp2.get_json()["task_id"]
    finally:
        # Teardown: stop the orphaned resume subprocess + remove state/flag files from the
        # SHARED dirs so the gate is cheaply re-runnable. Touches no assertion.
        if resp2 is not None and resp2.status_code == 202:
            resume_run_id = resp2.get_json()["task_id"]
            client.post(f"/api/fill/cancel/{resume_run_id}")
            _clear_flag(resume_run_id)
        for tid in (task_id, new_task_id):
            if tid:
                client.delete(f"/api/fill/state/{tid}")
                _clear_flag(tid)


def test_pattern_through_flask(client):
    """Real pattern search through Flask -> CLI subprocess, verbatim CLI JSON."""
    resp = client.post("/api/pattern", json={"pattern": "C?T", "wordlists": ["comprehensive"]})
    assert resp.status_code == 200, resp_diag(resp)
    data = resp.get_json()
    assert data["results"]
    first = data["results"][0]
    assert "word" in first and "source" in first
    assert len(first["word"]) == 3 and first["word"][0] == "C" and first["word"][2] == "T"
