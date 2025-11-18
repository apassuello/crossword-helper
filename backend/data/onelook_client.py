"""
OneLook API client for word pattern matching.

This module provides an HTTP client for querying the OneLook dictionary API
to find words matching specific patterns and constraints.
"""

import requests
import logging
from typing import List


class OneLookClient:
    """Client for OneLook dictionary API."""

    BASE_URL = 'https://api.onelook.com/words'

    def __init__(self, timeout: int = 5):
        """
        Initialize OneLook API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def search(self, pattern: str, max_results: int = 100) -> List[str]:
        """
        Search OneLook API for pattern matches.

        Args:
            pattern: Crossword pattern (e.g., '?i?a')
            max_results: Maximum number of results

        Returns:
            List of matching words (uppercase)
            Empty list on error (graceful degradation)
        """
        try:
            response = requests.get(
                self.BASE_URL,
                params={'sp': pattern.lower(), 'max': max_results},
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            words = [entry['word'].upper() for entry in data]

            self.logger.info(f"OneLook found {len(words)} matches for '{pattern}'")
            return words

        except requests.Timeout:
            self.logger.warning(f"OneLook API timeout for pattern '{pattern}'")
            return []

        except requests.RequestException as e:
            self.logger.warning(f"OneLook API error: {e}")
            return []

        except (KeyError, ValueError) as e:
            self.logger.error(f"OneLook response parsing error: {e}")
            return []
