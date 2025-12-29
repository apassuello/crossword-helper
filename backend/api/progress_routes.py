"""
Progress tracking routes for real-time updates via Server-Sent Events (SSE).

Provides SSE endpoints for streaming progress updates during long-running operations
like pattern search, autofill, and export.
"""

from flask import Blueprint, Response, request, jsonify
import json
import queue
import threading
import time
from typing import Dict, Any
import uuid

progress_api = Blueprint('progress_api', __name__)

# Global progress trackers (task_id -> queue)
progress_queues: Dict[str, queue.Queue] = {}
progress_queues_lock = threading.Lock()


def create_progress_tracker() -> str:
    """
    Create a new progress tracker and return its ID.

    Returns:
        Task ID (UUID)
    """
    task_id = str(uuid.uuid4())

    with progress_queues_lock:
        progress_queues[task_id] = queue.Queue()

    return task_id


def send_progress(task_id: str, progress: int, message: str, status: str = 'running', data: Dict[str, Any] = None):
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

    event = {
        'progress': progress,
        'message': message,
        'status': status,
        'timestamp': time.time()
    }

    # Include result data if provided
    if data:
        event['data'] = data

    try:
        progress_queues[task_id].put(event, block=False)
    except queue.Full:
        pass  # Drop events if queue is full


def cleanup_progress_tracker(task_id: str):
    """
    Remove a progress tracker.

    Args:
        task_id: Task ID
    """
    with progress_queues_lock:
        if task_id in progress_queues:
            del progress_queues[task_id]


@progress_api.route('/progress/<task_id>', methods=['GET'])
def stream_progress(task_id: str):
    """
    Stream progress updates via Server-Sent Events.

    Args:
        task_id: Task ID to stream progress for

    Returns:
        SSE stream of progress events
    """
    if task_id not in progress_queues:
        return jsonify({'error': 'Task not found'}), 404

    def generate():
        """Generate SSE events from progress queue."""
        task_queue = progress_queues.get(task_id)
        if not task_queue:
            return

        try:
            while True:
                try:
                    # Wait for next event (with timeout)
                    event = task_queue.get(timeout=30)

                    # Send SSE event
                    yield f"data: {json.dumps(event)}\n\n"

                    # If complete or error, stop streaming
                    if event.get('status') in ['complete', 'error']:
                        break

                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"

        finally:
            # Clean up when client disconnects
            cleanup_progress_tracker(task_id)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
            'Connection': 'keep-alive'
        }
    )


@progress_api.route('/progress/start', methods=['POST'])
def start_progress_tracking():
    """
    Create a new progress tracker.

    Returns:
        JSON with task_id
    """
    task_id = create_progress_tracker()
    return jsonify({'task_id': task_id}), 200


@progress_api.route('/progress/<task_id>/update', methods=['POST'])
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
        return jsonify({'error': 'Request body required'}), 400

    send_progress(
        task_id,
        data.get('progress', 0),
        data.get('message', 'Processing...'),
        data.get('status', 'running')
    )

    return jsonify({'success': True}), 200
