"""
Progress tracking routes for real-time updates via Server-Sent Events (SSE).

Provides SSE endpoints for streaming progress updates during long-running operations
like pattern search, autofill, and export.
"""

import json
import queue
import subprocess
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from flask import Blueprint, Response, jsonify, request

progress_api = Blueprint("progress_api", __name__)

# Global progress trackers (task_id -> queue)
progress_queues: Dict[str, queue.Queue] = {}
progress_queues_lock = threading.Lock()

# Track maximum progress per task for monotonicity enforcement
max_progress_per_task: Dict[str, int] = {}

# Terminal-event record (novice-readiness spec 0.2.5 section 2.4, #41). `progress_queues`
# is a single-consumer queue, so a second subscriber (or a reconnect) cannot read what the
# first one consumed. The first terminal event is therefore kept here, with its enqueue
# time, and re-sent by `generate()`. A tracker whose terminal event is older than
# TRACKER_RETENTION_SECONDS is swept lazily (no timer thread: P3, PD-3-SWEEP).
TERMINAL_STATUSES = ("complete", "error", "paused")
TRACKER_RETENTION_SECONDS = 60
QUEUE_TIMEOUT_SECONDS = 30
terminal_events: Dict[str, Tuple[Dict[str, Any], float]] = {}  # task_id -> (event, enqueue time)


def get_terminal_event(task_id: str) -> Optional[Dict[str, Any]]:
    """Return the recorded terminal event for a task, or None."""
    with progress_queues_lock:
        record = terminal_events.get(task_id)
    return record[0] if record else None


def _remove_tracker_locked(task_id: str) -> None:
    """Drop every per-task record. Caller must hold `progress_queues_lock`."""
    progress_queues.pop(task_id, None)
    max_progress_per_task.pop(task_id, None)
    terminal_events.pop(task_id, None)


def sweep_expired_trackers(now: Optional[float] = None) -> List[str]:
    """
    Remove every tracker whose terminal event was enqueued more than
    TRACKER_RETENTION_SECONDS before `now` (default `time.time()`).

    A tracker with no terminal event is never removed. Returns the removed ids.
    """
    if now is None:
        now = time.time()
    with progress_queues_lock:
        expired = [tid for tid, (_, enqueued) in terminal_events.items() if now - enqueued > TRACKER_RETENTION_SECONDS]
        for tid in expired:
            _remove_tracker_locked(tid)
    return expired


# Track running subprocesses for cleanup
running_processes: Dict[str, "subprocess.Popen"] = {}
running_processes_lock = threading.Lock()
# Cancels that arrived after the 202 but before the child registered (novice-readiness
# spec 0.2.5 section 2.4 (C7), "Early Cancel"). Guarded by `running_processes_lock`.
pending_cancels: Set[str] = set()


def create_progress_tracker() -> str:
    """
    Create a new progress tracker and return its ID.

    Returns:
        Task ID (UUID)
    """
    task_id = str(uuid.uuid4())

    with progress_queues_lock:
        progress_queues[task_id] = queue.Queue()
        max_progress_per_task[task_id] = 0  # Initialize max progress tracking

    return task_id


def send_progress(
    task_id: str,
    progress: int,
    message: str,
    status: str = "running",
    data: Dict[str, Any] = None,
):
    """
    Send a progress update for a task.

    Args:
        task_id: Task ID
        progress: Progress percentage (0-100)
        message: Progress message
        status: Status ('running', 'complete', 'error')
        data: Optional result data (e.g., filled grid)
    """
    if task_id not in progress_queues:
        return

    # Enforce monotonicity: progress should never decrease during backtracking
    # This handles scenarios where beam search backtracks and reduces filled slots
    with progress_queues_lock:
        if status == "running":
            current_max = max_progress_per_task.get(task_id, 0)
            progress = max(progress, current_max)
            max_progress_per_task[task_id] = progress
        elif status == "complete":
            # Always allow completion at 100%
            progress = 100
            max_progress_per_task[task_id] = 100

    event = {
        "progress": progress,
        "message": message,
        "status": status,
        "timestamp": time.time(),
    }

    # Include result data if provided
    if data:
        event["data"] = data

    # Record under the same lock that guards the tracker maps, so a concurrent
    # cleanup/sweep cannot leave a record behind for a removed tracker. Only the FIRST
    # terminal event is kept: a stream ends at the first one it meets (DD4b: paused, then
    # a trailing complete sentinel, replays as paused). novice-readiness spec 0.2.5 s2.4 (#41).
    if status in TERMINAL_STATUSES:
        with progress_queues_lock:
            if task_id in progress_queues:
                terminal_events.setdefault(task_id, (event, event["timestamp"]))

    try:
        progress_queues[task_id].put(event, block=False)
    except queue.Full:
        pass  # Drop events if queue is full


def cleanup_progress_tracker(task_id: str):
    """Remove a progress tracker (does NOT kill subprocess — that's handled by cancel/timeout)."""
    with progress_queues_lock:
        _remove_tracker_locked(task_id)


def _terminate(process) -> None:
    """Terminate-then-kill a subprocess. Takes no lock, so it is safe to call with or without one."""
    try:
        process.terminate()
        process.wait(timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        try:
            process.kill()
        except OSError:
            pass


def register_process(task_id: str, process):
    """
    Register a subprocess for a task (for cleanup on disconnect).

    If a cancel was recorded for this task before it registered, the process is
    terminated here, before returning (novice-readiness spec 0.2.5 section 2.4 (C7)).
    The check and the registration share one critical section with `request_cancel`,
    so whichever of the two takes `running_processes_lock` first, the process ends up
    killed: see `request_cancel`.
    """
    with running_processes_lock:
        running_processes[task_id] = process
        cancelled = task_id in pending_cancels
        pending_cancels.discard(task_id)
    if cancelled:
        _terminate(process)


def request_cancel(task_id: str) -> str:
    """
    Cancel a task: "killed" | "recorded" | "not_running" (spec 0.2.5 section 2.4 (C7)).

    - a live registered process: popped and terminated, "killed";
    - a tracker with no terminal event and no registered process: `task_id` is added to
      `pending_cancels`, "recorded", and `register_process` kills the child on arrival;
    - anything else (no tracker, terminal event recorded, dead process): "not_running".

    Lock order: `running_processes_lock` (outer) then `progress_queues_lock` (inner), and
    only here. Every other path takes at most one of the two (`send_progress`, the sweep,
    `get_terminal_event` and the cleanup helpers take only the queues lock; the process
    helpers only the processes lock), so no path holds the inner lock while waiting for
    the outer one and no cycle can form.

    Atomicity: the registered/not-registered decision and the `pending_cancels` insert
    happen inside one hold of `running_processes_lock`, as do `register_process`'s
    insert and `pending_cancels` check. Either `register_process` ran first (the process
    is in `running_processes`, so this call sees it: "killed"), or this call ran first
    (the id is in `pending_cancels`, so `register_process` sees it and terminates).
    There is no third ordering. The child is terminated after the lock is released; it
    is already unreachable by any other cancel at that point.
    """
    with running_processes_lock:
        process = running_processes.get(task_id)
        if process is not None:
            if process.poll() is not None:
                return "not_running"
            running_processes.pop(task_id, None)
        else:
            with progress_queues_lock:
                has_tracker = task_id in progress_queues
                has_terminal = task_id in terminal_events
            if not has_tracker or has_terminal:
                return "not_running"
            pending_cancels.add(task_id)
            return "recorded"
    _terminate(process)
    return "killed"


def is_process_running(task_id: str) -> bool:
    """Check whether a registered subprocess for this task is still alive."""
    with running_processes_lock:
        process = running_processes.get(task_id)
    return process is not None and process.poll() is None


def cleanup_process(task_id: str) -> bool:
    """
    Terminate subprocess if still running.

    Returns:
        True if a live process was found and terminated, False otherwise.
    """
    with running_processes_lock:
        process = running_processes.pop(task_id, None)
    if process and process.poll() is None:
        _terminate(process)
        return True
    return False


@progress_api.route("/progress/<task_id>", methods=["GET"])
def stream_progress(task_id: str):
    """
    Stream progress updates via Server-Sent Events.

    Args:
        task_id: Task ID to stream progress for

    Returns:
        SSE stream of progress events
    """
    sweep_expired_trackers()
    if task_id not in progress_queues:
        return jsonify({"error": "Task not found"}), 404

    def generate():
        """Generate SSE events from progress queue, ending with one terminal event."""
        task_queue = progress_queues.get(task_id)
        if not task_queue:
            return

        # The queue has one consumer per event, so a terminal event another subscriber
        # already took is only available from the record (#41).
        recorded = get_terminal_event(task_id)
        if recorded is not None:
            yield f"data: {json.dumps(recorded)}\n\n"
            return

        # No cleanup on exit: the tracker outlives its subscribers so a reconnect or a
        # second subscriber still finds it; sweep_expired_trackers retires it.
        while True:
            try:
                # Wait for next event (with timeout)
                event = task_queue.get(timeout=QUEUE_TIMEOUT_SECONDS)

                # Send SSE event
                yield f"data: {json.dumps(event)}\n\n"

                # If complete, error, or paused, stop streaming. DD4b: `paused` is a
                # terminal SSE state (the CLI exits and the stream must close, else
                # the synchronous consumer hangs). Resume opens a fresh task_id stream.
                if event.get("status") in TERMINAL_STATUSES:
                    return

            except queue.Empty:
                # Another subscriber may have taken the terminal event from the queue.
                # Read the record BEFORE sweeping: the sweep may retire this very tracker,
                # and the record must already be in hand to be sent.
                recorded = get_terminal_event(task_id)
                sweep_expired_trackers()
                if recorded is not None:
                    yield f"data: {json.dumps(recorded)}\n\n"
                    return
                # Send heartbeat to keep connection alive
                yield ": heartbeat\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Connection": "keep-alive",
        },
    )


@progress_api.route("/progress/start", methods=["POST"])
def start_progress_tracking():
    """
    Create a new progress tracker.

    Returns:
        JSON with task_id
    """
    task_id = create_progress_tracker()
    return jsonify({"task_id": task_id}), 200


@progress_api.route("/progress/<task_id>/update", methods=["POST"])
def update_progress(task_id: str):
    """
    Manually update progress for a task (for testing).

    Args:
        task_id: Task ID

    Request Body:
        - progress: Progress percentage (0-100)
        - message: Progress message
        - status: Status ('running', 'complete', 'error')

    Returns:
        Success response
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body required"}), 400

    send_progress(
        task_id,
        data.get("progress", 0),
        data.get("message", "Processing..."),
        data.get("status", "running"),
    )

    return jsonify({"success": True}), 200
