"""
Slot intersection utilities for beam search.

This module provides utility functions for checking slot intersections,
finding crossing positions, and managing slot relationships.
"""

from typing import List, Dict, Tuple, Optional
from ....core.grid import Grid


class SlotIntersectionHelper:
    """
    Utility class for slot intersection operations.

    Provides methods to check if slots intersect, find intersection positions,
    and get all slots that cross a given reference slot.
    """

    @staticmethod
    def slots_intersect(slot1: Dict, slot2: Dict) -> bool:
        """
        Check if two slots share at least one cell.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            True if slots intersect, False otherwise
        """
        # Same direction can't intersect
        if slot1["direction"] == slot2["direction"]:
            return False

        # Get cell positions for each slot
        def get_positions(slot):
            positions = []
            if slot["direction"] == "across":
                for i in range(slot["length"]):
                    positions.append((slot["row"], slot["col"] + i))
            else:  # down
                for i in range(slot["length"]):
                    positions.append((slot["row"] + i, slot["col"]))
            return set(positions)

        pos1 = get_positions(slot1)
        pos2 = get_positions(slot2)

        # Check for any common positions
        return bool(pos1 & pos2)

    @staticmethod
    def get_slot_intersection(slot1: Dict, slot2: Dict) -> Optional[Tuple[int, int]]:
        """
        Get intersection positions between two slots.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            (slot1_position, slot2_position) if they intersect, None otherwise
        """
        if slot1["direction"] == slot2["direction"]:
            return None  # Parallel slots don't intersect

        # Get cell coordinates for each slot
        cells1 = set()
        cells2 = set()

        if slot1["direction"] == "across":
            for i in range(slot1["length"]):
                cells1.add((slot1["row"], slot1["col"] + i, i))
        else:  # down
            for i in range(slot1["length"]):
                cells1.add((slot1["row"] + i, slot1["col"], i))

        if slot2["direction"] == "across":
            for i in range(slot2["length"]):
                cells2.add((slot2["row"], slot2["col"] + i, i))
        else:  # down
            for i in range(slot2["length"]):
                cells2.add((slot2["row"] + i, slot2["col"], i))

        # Find intersection
        for r1, c1, pos1 in cells1:
            for r2, c2, pos2 in cells2:
                if r1 == r2 and c1 == c2:
                    return (pos1, pos2)

        return None

    @staticmethod
    def get_crossing_position(slot1: Dict, slot2: Dict) -> Optional[Tuple[int, int]]:
        """
        Get the position where two slots cross.

        Args:
            slot1: First slot
            slot2: Second slot

        Returns:
            (pos_in_slot1, pos_in_slot2) or None if no crossing
        """
        # Slots must be perpendicular to intersect
        if slot1["direction"] == slot2["direction"]:
            return None

        # Determine which is across and which is down
        if slot1["direction"] == "across":
            across_slot = slot1
            down_slot = slot2
            across_is_first = True
        else:
            across_slot = slot2
            down_slot = slot1
            across_is_first = False

        # Calculate intersection point
        across_row = across_slot["row"]
        across_col = across_slot["col"]
        down_row = down_slot["row"]
        down_col = down_slot["col"]

        # Check if they intersect
        if down_col < across_col or down_col >= across_col + across_slot["length"]:
            return None  # Down slot doesn't cross across slot horizontally

        if across_row < down_row or across_row >= down_row + down_slot["length"]:
            return None  # Across slot doesn't cross down slot vertically

        # Calculate positions within each word
        across_pos = down_col - across_col
        down_pos = across_row - down_row

        if across_is_first:
            return (across_pos, down_pos)
        else:
            return (down_pos, across_pos)

    @staticmethod
    def get_slot_crossings(slot: Dict, grid: Grid) -> List[Dict]:
        """
        Get all slots that cross this slot.

        Args:
            slot: Slot dictionary with row, col, direction, length
            grid: Grid containing all slots

        Returns:
            List of crossing slot dictionaries
        """
        crossings = []
        all_slots = grid.get_word_slots()

        for other_slot in all_slots:
            # Skip same slot
            if (
                other_slot["row"] == slot["row"]
                and other_slot["col"] == slot["col"]
                and other_slot["direction"] == slot["direction"]
            ):
                continue

            # Check for intersection
            if slot["direction"] == "across" and other_slot["direction"] == "down":
                # This slot is horizontal, other is vertical
                if (
                    slot["row"] >= other_slot["row"]
                    and slot["row"] < other_slot["row"] + other_slot["length"]
                    and other_slot["col"] >= slot["col"]
                    and other_slot["col"] < slot["col"] + slot["length"]
                ):
                    crossings.append(other_slot)
            elif slot["direction"] == "down" and other_slot["direction"] == "across":
                # This slot is vertical, other is horizontal
                if (
                    slot["col"] >= other_slot["col"]
                    and slot["col"] < other_slot["col"] + other_slot["length"]
                    and other_slot["row"] >= slot["row"]
                    and other_slot["row"] < slot["row"] + slot["length"]
                ):
                    crossings.append(other_slot)

        return crossings

    @staticmethod
    def get_intersecting_slots(
        grid: Grid, reference_slot: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Get slots that intersect with reference_slot.

        Only checks slots that share at least one cell with reference_slot.
        This is much more efficient than checking all slots.

        Args:
            grid: Current grid
            reference_slot: Slot to find intersections for (optional)

        Returns:
            List of slots that intersect with reference_slot, or all empty slots if no reference
        """
        if reference_slot is None:
            # No reference slot - check all slots (fallback)
            return grid.get_empty_slots()

        intersecting = []
        all_slots = grid.get_empty_slots()

        for slot in all_slots:
            # Skip same slot
            if (
                slot["row"] == reference_slot["row"]
                and slot["col"] == reference_slot["col"]
                and slot["direction"] == reference_slot["direction"]
            ):
                continue

            # Check if they intersect
            if SlotIntersectionHelper.slots_intersect(reference_slot, slot):
                intersecting.append(slot)

        return intersecting

    @staticmethod
    def get_slot_by_id(slot_id: Tuple, slots: List[Dict]) -> Optional[Dict]:
        """
        Get slot dictionary by its ID tuple (row, col, direction).

        Args:
            slot_id: Tuple of (row, col, direction)
            slots: List of all slots

        Returns:
            Slot dictionary or None if not found
        """
        row, col, direction = slot_id
        for slot in slots:
            if (
                slot["row"] == row
                and slot["col"] == col
                and slot["direction"] == direction
            ):
                return slot
        return None
