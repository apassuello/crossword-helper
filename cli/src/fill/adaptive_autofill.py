"""
Adaptive autofill wrapper that automatically detects stuck situations
and applies strategic black square placements to resolve them.

This wrapper monitors autofill progress and intervenes when:
- Thrashing is detected (same slots repeatedly tried)
- No progress after N iterations
- Specific slots consistently fail to fill
"""

import logging
from typing import Dict, List, Optional

from ..core.grid import Grid
from .autofill import Autofill

# Import backend suggester if available
try:
    import os
    import sys

    # Add backend to path
    backend_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from backend.core.black_square_suggester import BlackSquareSuggester

    SUGGESTER_AVAILABLE = True
except ImportError:
    SUGGESTER_AVAILABLE = False
    logging.warning("BlackSquareSuggester not available, adaptive mode disabled")


logger = logging.getLogger(__name__)


class AdaptiveAutofill:
    """
    Adaptive autofill that automatically places black squares when stuck.

    Detection Strategy:
    - Monitor backtrack count per slot
    - If a slot is backtracked > threshold, it's problematic
    - Pause, suggest black square for that slot
    - Apply best suggestion, resume

    Limits:
    - Max 3 adaptations per autofill session
    - Only adapt slots with length >= 6
    - Maintain grid quality (word count in range)
    """

    def __init__(
        self,
        grid: Grid,
        wordlists: List,
        options: Dict,
        progress_reporter=None,
        base_autofill=None,
    ):
        """
        Initialize adaptive autofill.

        Args:
            grid: Crossword grid
            wordlists: List of word list objects
            options: Autofill options (min_score, timeout, etc.)
            progress_reporter: Optional progress reporter for SSE
            base_autofill: Pre-created autofill instance (BeamSearch, Hybrid, etc.)
                          If provided, this instance will be reused instead of creating new one
        """
        self.grid = grid
        self.wordlists = wordlists
        self.options = options
        self.progress_reporter = progress_reporter
        self.base_autofill = base_autofill  # Store for reuse

        # Adaptive behavior settings
        self.max_adaptations = options.get("max_adaptations", 3)
        self.adaptation_threshold = options.get("adaptation_threshold", 100)  # Backtracks before adapting
        self.min_slot_length = 6  # Don't suggest black squares for short slots

        # Tracking
        self.adaptation_count = 0
        self.adaptations_applied = []  # List of (slot, suggestion) tuples
        self.slot_backtrack_counts = {}  # slot_key -> backtrack count

        # Suggester
        if SUGGESTER_AVAILABLE:
            self.suggester = BlackSquareSuggester(grid.size)
        else:
            self.suggester = None

        # Use base autofill if provided, otherwise create new one
        if base_autofill:
            self.autofill = base_autofill
            # Hook into autofill's backtrack callback
            if hasattr(self.autofill, "on_backtrack"):
                self.autofill.on_backtrack = self._on_backtrack
        else:
            self.autofill = None
            self._create_autofill()

    def _create_autofill(self):
        """Create or recreate autofill instance with current grid."""
        # If we have a base autofill (BeamSearch, Hybrid, etc.), reuse it
        if self.base_autofill:
            # Just update the grid on the existing instance
            self.base_autofill.grid = self.grid
            self.autofill = self.base_autofill
        else:
            # Create new standard autofill
            self.autofill = Autofill(
                grid=self.grid,
                wordlists=self.wordlists,
                min_score=self.options.get("min_score", 30),
                timeout=self.options.get("timeout", 300),
                progress_reporter=self.progress_reporter,
                theme_entries=self.options.get("theme_entries", {}),
            )

        # Hook into autofill's backtrack callback
        if hasattr(self.autofill, "on_backtrack"):
            self.autofill.on_backtrack = self._on_backtrack

    def _on_backtrack(self, slot_key: str):
        """
        Called by autofill whenever it backtracks from a slot.

        Track which slots are causing the most backtracks.
        """
        if slot_key not in self.slot_backtrack_counts:
            self.slot_backtrack_counts[slot_key] = 0
        self.slot_backtrack_counts[slot_key] += 1

        # Check if this slot exceeds threshold
        if self.slot_backtrack_counts[slot_key] >= self.adaptation_threshold:
            logger.info(f"Slot {slot_key} exceeded backtrack threshold ({self.slot_backtrack_counts[slot_key]} backtracks)")
            # Mark for adaptation
            self.slot_backtrack_counts[slot_key] = -1  # Prevent repeated triggers

    def fill(self, timeout: int = 300) -> Dict:
        """
        Run adaptive autofill with automatic black square placement.

        Args:
            timeout: Maximum time in seconds for autofill

        Returns:
            Same result format as standard Autofill.fill()
        """
        if not SUGGESTER_AVAILABLE:
            # Fallback to standard autofill
            logger.warning("Adaptive mode disabled, running standard autofill")
            return self.autofill.fill(timeout=timeout)

        # Report adaptive mode enabled
        if self.progress_reporter:
            self.progress_reporter.update(
                0,
                f"Adaptive autofill enabled (max {self.max_adaptations} adaptations)",
                "running",
            )

        # Main autofill loop
        attempt = 0
        while attempt <= self.max_adaptations:
            logger.info(f"Autofill attempt {attempt + 1}/{self.max_adaptations + 1}")

            # Run autofill (returns FillResult dataclass)
            result = self.autofill.fill(timeout=timeout)

            # If successful, return immediately
            if result.success:
                # Add adaptation info to FillResult
                if self.adaptation_count > 0:
                    result.adaptations_applied = self.adaptation_count
                    result.message = f"Success with {self.adaptation_count} adaptive black square(s)"
                return result

            # If we've exhausted adaptations, return partial result
            if attempt >= self.max_adaptations:
                logger.info(f"Max adaptations ({self.max_adaptations}) reached, returning partial result")
                result.adaptations_applied = self.adaptation_count
                result.message = f"Partial fill after {self.adaptation_count} adaptations"
                return result

            # Try to adapt the grid
            adapted = self._try_adapt()

            if adapted:
                # Adaptation successful, try again
                attempt += 1
                self.adaptation_count += 1

                # Reset slot tracking
                self.slot_backtrack_counts = {}

                # Recreate autofill with adapted grid
                self._create_autofill()

                # Report adaptation
                if self.progress_reporter:
                    # Calculate progress percentage from fill result
                    progress = int((result.slots_filled / result.total_slots) * 100) if result.total_slots > 0 else 0
                    self.progress_reporter.update(
                        progress,
                        f"Applied adaptive black square #{self.adaptation_count}, retrying...",
                        "running",
                    )
            else:
                # Can't adapt, return partial result
                logger.info("Cannot adapt further, returning partial result")
                result.adaptations_applied = self.adaptation_count
                return result

        # Should not reach here
        result.adaptations_applied = self.adaptation_count
        return result

    def _try_adapt(self) -> bool:
        """
        Try to adapt the grid by placing a strategic black square.

        Returns:
            True if adaptation was applied, False otherwise
        """
        # Find the most problematic slot
        problematic_slot = self._find_problematic_slot()

        if not problematic_slot:
            logger.info("No problematic slot found for adaptation")
            return False

        logger.info(f"Found problematic slot: {problematic_slot}")

        # Get black square suggestions for this slot
        suggestions = self.suggester.suggest_placements(
            grid=self.grid.to_dict()["grid"],
            problematic_slot=problematic_slot,
            max_suggestions=3,
        )

        if not suggestions or len(suggestions) == 0:
            logger.info("No valid black square suggestions for problematic slot")
            return False

        # Apply the best suggestion (highest score)
        best = suggestions[0]
        logger.info(f"Applying black square at ({best['row']}, {best['col']}) with score {best['score']}")

        # Apply to grid
        self._apply_black_square(best)

        # Track adaptation
        self.adaptations_applied.append((problematic_slot, best))

        # Report adaptation
        if self.progress_reporter:
            self.progress_reporter.update(
                0,
                f"Adaptation #{self.adaptation_count + 1}: Added black square at "
                f"({best['row']}, {best['col']}) - {best['reasoning'][:50]}...",
                "running",
                {
                    "adaptation": {
                        "count": self.adaptation_count + 1,
                        "position": (best["row"], best["col"]),
                        "reasoning": best["reasoning"],
                    }
                },
            )

        return True

    def _find_problematic_slot(self) -> Optional[Dict]:
        """
        Find the most problematic slot to target for black square placement.

        Strategy:
        - Look for slots with high backtrack counts (marked with -1)
        - Prioritize longer slots (harder to fill)
        - Only consider slots with length >= min_slot_length

        Returns:
            Slot dict with keys: row, col, direction, length, pattern
            Or None if no problematic slot found
        """
        # Find slots marked as problematic (backtrack count = -1)
        problematic_keys = [key for key, count in self.slot_backtrack_counts.items() if count == -1]

        if not problematic_keys:
            # No explicitly problematic slots, find the most constrained empty slot
            return self._find_most_constrained_slot()

        # Parse slot keys and get full slot info
        slots = []
        for key in problematic_keys:
            slot_info = self._get_slot_info(key)
            if slot_info and slot_info["length"] >= self.min_slot_length:
                slots.append(slot_info)

        if not slots:
            return None

        # Return longest slot (most likely to benefit from splitting)
        slots.sort(key=lambda s: s["length"], reverse=True)
        return slots[0]

    def _find_most_constrained_slot(self) -> Optional[Dict]:
        """
        Find the most constrained empty slot in the grid.

        Returns:
            Slot dict or None
        """
        slots = []
        grid_dict = self.grid.to_dict()["grid"]

        # Scan grid for empty slots
        for row in range(self.grid.size):
            for col in range(self.grid.size):
                if grid_dict[row][col] == "#":
                    continue

                # Check if start of across word
                if col == 0 or grid_dict[row][col - 1] == "#":
                    slot = self._extract_slot(row, col, "across", grid_dict)
                    if slot and slot["length"] >= self.min_slot_length and "?" in slot["pattern"]:
                        slots.append(slot)

                # Check if start of down word
                if row == 0 or grid_dict[row - 1][col] == "#":
                    slot = self._extract_slot(row, col, "down", grid_dict)
                    if slot and slot["length"] >= self.min_slot_length and "?" in slot["pattern"]:
                        slots.append(slot)

        if not slots:
            return None

        # Return longest slot
        slots.sort(key=lambda s: s["length"], reverse=True)
        return slots[0]

    def _get_slot_info(self, slot_key: str) -> Optional[Dict]:
        """
        Get full slot info from slot key.

        Args:
            slot_key: Format "row,col,direction"

        Returns:
            Slot dict or None
        """
        try:
            parts = slot_key.strip("()").split(",")
            row = int(parts[0])
            col = int(parts[1])
            direction = parts[2]

            grid_dict = self.grid.to_dict()["grid"]
            return self._extract_slot(row, col, direction, grid_dict)
        except (ValueError, IndexError):
            logger.warning(f"Invalid slot key: {slot_key}")
            return None

    def _extract_slot(self, row: int, col: int, direction: str, grid: List[List]) -> Optional[Dict]:
        """
        Extract slot info from grid.

        Returns:
            Dict with keys: row, col, direction, length, pattern, candidate_count
        """
        pattern = ""

        if direction == "across":
            c = col
            while c < len(grid[row]) and grid[row][c] != "#":
                letter = grid[row][c]
                pattern += letter if letter not in [".", ""] else "?"
                c += 1
        else:  # down
            r = row
            while r < len(grid) and grid[r][col] != "#":
                letter = grid[r][col]
                pattern += letter if letter not in [".", ""] else "?"
                r += 1

        if len(pattern) < 3:
            return None

        return {
            "row": row,
            "col": col,
            "direction": direction,
            "length": len(pattern),
            "pattern": pattern,
            "candidate_count": 0,  # Will be calculated by suggester
        }

    def _apply_black_square(self, suggestion: Dict):
        """
        Apply a black square suggestion to the grid.

        Args:
            suggestion: Suggestion dict from BlackSquareSuggester
        """
        # Apply primary black square (with symmetry handled automatically by Grid class)
        self.grid.set_black_square(
            suggestion["row"],
            suggestion["col"],
            enforce_symmetry=True,  # Grid class will handle symmetric position
        )

        sym_row = suggestion["symmetric_position"]["row"]
        sym_col = suggestion["symmetric_position"]["col"]

        logger.info(f"Applied black squares at ({suggestion['row']}, {suggestion['col']}) and ({sym_row}, {sym_col})")
