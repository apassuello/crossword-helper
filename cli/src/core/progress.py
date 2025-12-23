"""
Progress reporting utility for CLI commands.

Outputs progress updates to stderr in JSON format for consumption by web API.
"""

import json
import sys
from typing import Optional


class ProgressReporter:
    """
    Report progress for long-running operations.

    Outputs JSON progress updates to stderr for parsing by web API.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize progress reporter.

        Args:
            enabled: Whether to output progress (disabled for non-JSON output)
        """
        self.enabled = enabled

    def report(self, progress: int, message: str, status: str = 'running', data: dict = None):
        """
        Report progress update.

        Args:
            progress: Progress percentage (0-100)
            message: Progress message
            status: Status ('running', 'complete', 'error')
            data: Optional data payload (e.g., incremental grid updates)
        """
        if not self.enabled:
            return

        event = {
            'type': 'progress',
            'progress': progress,
            'message': message,
            'status': status
        }

        # Include optional data
        if data:
            event['data'] = data

        # Output to stderr as JSON
        print(json.dumps(event), file=sys.stderr, flush=True)

    def start(self, message: str = 'Starting...'):
        """
        Report operation start.

        Args:
            message: Start message
        """
        self.report(0, message, 'running')

    def update(self, progress: int, message: str, status: str = 'running', data: dict = None):
        """
        Report progress update.

        Args:
            progress: Progress percentage (0-100)
            message: Progress message
            status: Status ('running', 'complete', 'error')
            data: Optional data payload (e.g., incremental grid updates)
        """
        self.report(progress, message, status, data)

    def complete(self, message: str = 'Complete'):
        """
        Report successful completion.

        Args:
            message: Completion message
        """
        self.report(100, message, 'complete')

    def error(self, message: str):
        """
        Report error.

        Args:
            message: Error message
        """
        self.report(0, message, 'error')
