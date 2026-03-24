"""Shared fixtures for integration tests."""

import json
import select
import subprocess
import time
import pytest
from backend.app import create_app


@pytest.fixture
def client():
    """Create Flask test client."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sse_parser():
    """Parse SSE stream bytes into list of JSON message dicts."""
    def parse_sse_stream(data_bytes):
        messages = []
        data_str = data_bytes.decode('utf-8')
        for chunk in data_str.split('\n\n'):
            if not chunk.strip():
                continue
            for line in chunk.split('\n'):
                if line.startswith('data: '):
                    try:
                        messages.append(json.loads(line[6:]))
                    except json.JSONDecodeError:
                        pass
        return messages
    return parse_sse_stream


def create_test_grid(size=11):
    """Create empty grid in frontend format."""
    return [[{"letter": "", "isBlack": False} for _ in range(size)] for _ in range(size)]


def start_fill_task(client, size=5, algorithm="trie", timeout=10, **extra):
    """Start an autofill task and return task_id. Asserts 202."""
    grid = extra.pop("grid", None) or create_test_grid(size)
    request_data = {
        "size": size,
        "grid": grid,
        "wordlists": ["comprehensive"],
        "timeout": timeout,
        "min_score": 10,
        "algorithm": algorithm,
        **extra,
    }
    response = client.post(
        "/api/fill/with-progress",
        data=json.dumps(request_data),
        content_type="application/json",
    )
    assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.data}"
    return response.json["task_id"]


def collect_sse_messages(client, task_id):
    """
    Fetch SSE stream for task_id. Blocks until stream ends (complete/error).
    Returns list of parsed JSON messages.

    NOTE: Flask test client's client.get() on an SSE endpoint blocks
    synchronously until the generator finishes. No sleep needed before calling this.

    Safety: The SSE generator sends heartbeats every 30s if no events arrive.
    If the fill thread crashes without posting complete/error, the generator
    loops forever. In practice the fill runner always posts a terminal event,
    but if a test hangs here, that's the likely cause.
    """
    sse_response = client.get(f"/api/progress/{task_id}")
    messages = []
    data_str = sse_response.data.decode('utf-8')
    for chunk in data_str.split('\n\n'):
        if not chunk.strip():
            continue
        for line in chunk.split('\n'):
            if line.startswith('data: '):
                try:
                    messages.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
    return messages


def run_cli_until_output(cmd, target_text, timeout=10):
    """
    Run a CLI subprocess and return stdout as soon as target_text appears.
    Kills the process immediately after — does NOT wait for fill to complete.

    Args:
        cmd: Command list for subprocess.Popen
        target_text: String to search for in stdout (case-sensitive)
        timeout: Max seconds to wait for target_text to appear

    Returns:
        str: All stdout collected up to and including the matching line

    Raises:
        TimeoutError: If target_text doesn't appear within timeout
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,  # Don't capture stderr — avoids pipe buffer deadlock
        text=True,
    )

    collected = []
    deadline = time.monotonic() + timeout

    try:
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            ready, _, _ = select.select([proc.stdout], [], [], min(remaining, 0.5))
            if ready:
                line = proc.stdout.readline()
                if not line:
                    break  # EOF — process exited
                collected.append(line)
                if target_text in line:
                    return "".join(collected)
            # Also check if process exited
            if proc.poll() is not None:
                remaining_output = proc.stdout.read()
                if remaining_output:
                    collected.append(remaining_output)
                    if target_text in remaining_output:
                        return "".join(collected)
                break
    finally:
        proc.kill()
        proc.wait()

    stdout_so_far = "".join(collected)
    if target_text in stdout_so_far:
        return stdout_so_far
    raise TimeoutError(
        f"'{target_text}' not found in stdout within {timeout}s. "
        f"Got: {stdout_so_far[:500]}"
    )
