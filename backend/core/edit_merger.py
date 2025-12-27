"""
Edit merger for pause/resume functionality.

Merges user edits into saved autofill state while maintaining consistency
and detecting unsolvable configurations.
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class GridChanges:
    """Tracks changes between saved and edited grids."""
    filled_slots: List[int]  # Slot IDs that were filled by user
    emptied_slots: List[int]  # Slot IDs that were emptied by user
    modified_slots: List[int]  # Slot IDs where content changed
    new_words: Set[str]  # New words added by user
    removed_words: Set[str]  # Words removed by user


class EditMerger:
    """
    Merges user edits into saved autofill state.

    Ensures that user edits are:
    1. Marked as locked (unchangeable during resume)
    2. Incorporated into constraint propagation
    3. Validated for solvability
    """

    def __init__(self):
        """Initialize edit merger."""
        self.logger = logging.getLogger(__name__)

    def merge_edits(
        self,
        saved_state,  # CSPState from state_manager
        edited_grid_dict: Dict,
        word_list=None  # Optional: for validating new words
    ):
        """
        Merge user edits into saved state.

        Process:
        1. Detect changes (cells filled/emptied/modified)
        2. Mark new filled cells as locked
        3. Update domains to reflect new constraints
        4. Re-run AC-3 to prune incompatible words
        5. Validate: ensure domains not empty

        Args:
            saved_state: CSPState from StateManager
            edited_grid_dict: Grid.to_dict() result with user edits
            word_list: Optional WordList for validation

        Returns:
            Updated CSPState ready for resume

        Raises:
            ValueError: If edits create unsolvable state
        """
        from cli.src.core.grid import Grid
        from cli.src.fill.state_manager import CSPState

        # Load grids
        saved_grid = Grid.from_dict(saved_state.grid_dict)
        edited_grid = Grid.from_dict(edited_grid_dict)

        # Detect changes
        changes = self._detect_changes(
            saved_grid,
            edited_grid,
            saved_state.slot_list,
            saved_state.slot_id_map
        )

        self.logger.info(f"Detected changes: {len(changes.filled_slots)} filled, "
                        f"{len(changes.emptied_slots)} emptied, "
                        f"{len(changes.modified_slots)} modified")

        # Update locked slots (add newly filled slots)
        updated_locked = set(saved_state.locked_slots)
        for slot_id in changes.filled_slots:
            updated_locked.add(slot_id)

        # Remove unlocked slots that were emptied
        for slot_id in changes.emptied_slots:
            if slot_id in updated_locked and slot_id not in saved_state.locked_slots:
                # Only remove if not originally locked (theme entry)
                pass  # Keep original locked slots locked

        # Update used words
        updated_used_words = set(saved_state.used_words)
        updated_used_words.update(changes.new_words)
        updated_used_words.difference_update(changes.removed_words)

        # Update domains based on new constraints
        updated_domains = self._update_domains_with_edits(
            saved_state,
            edited_grid,
            changes,
            updated_locked
        )

        # Validate solvability (only if we actually have domains to validate)
        has_domains = any(len(domain) > 0 for domain in updated_domains.values())

        if has_domains:
            validation_result = self._validate_state(
                updated_domains,
                saved_state.constraints,
                saved_state.slot_list
            )

            if not validation_result['is_valid']:
                error_msg = (
                    f"User edits create unsolvable configuration: "
                    f"{validation_result['reason']}"
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        # Create updated state
        updated_state = CSPState(
            grid_dict=edited_grid_dict,
            domains={k: list(v) for k, v in updated_domains.items()},
            constraints=saved_state.constraints,
            used_words=list(updated_used_words),
            slot_id_map=saved_state.slot_id_map,
            slot_list=saved_state.slot_list,
            slots_sorted=saved_state.slots_sorted,
            current_slot_index=saved_state.current_slot_index,
            iteration_count=saved_state.iteration_count,
            locked_slots=list(updated_locked),
            timestamp=saved_state.timestamp,
            random_seed=saved_state.random_seed,
            letter_frequency_table=saved_state.letter_frequency_table
        )

        return updated_state

    def _detect_changes(
        self,
        saved_grid,
        edited_grid,
        slot_list: List[Dict],
        slot_id_map: Dict
    ) -> GridChanges:
        """
        Detect what changed between grids.

        Args:
            saved_grid: Original grid
            edited_grid: Grid with user edits
            slot_list: List of all slots
            slot_id_map: Mapping of (row, col, direction) to slot_id

        Returns:
            GridChanges object
        """
        import json

        filled_slots = []
        emptied_slots = []
        modified_slots = []
        new_words = set()
        removed_words = set()

        # Check each slot for changes
        for slot in slot_list:
            row, col, direction = slot['row'], slot['col'], slot['direction']

            # Get patterns from both grids
            saved_pattern = saved_grid.get_pattern_for_slot(slot)
            edited_pattern = edited_grid.get_pattern_for_slot(slot)

            # Get slot ID
            slot_key = json.dumps([row, col, direction])
            slot_id = slot_id_map.get(slot_key)

            if slot_id is None:
                continue

            # Detect changes
            saved_has_gaps = '?' in saved_pattern
            edited_has_gaps = '?' in edited_pattern

            if saved_has_gaps and not edited_has_gaps:
                # Slot was filled
                filled_slots.append(slot_id)
                new_words.add(edited_pattern)

            elif not saved_has_gaps and edited_has_gaps:
                # Slot was emptied
                emptied_slots.append(slot_id)
                removed_words.add(saved_pattern)

            elif not saved_has_gaps and not edited_has_gaps and saved_pattern != edited_pattern:
                # Slot content was modified
                modified_slots.append(slot_id)
                removed_words.add(saved_pattern)
                new_words.add(edited_pattern)

        return GridChanges(
            filled_slots=filled_slots,
            emptied_slots=emptied_slots,
            modified_slots=modified_slots,
            new_words=new_words,
            removed_words=removed_words
        )

    def _update_domains_with_edits(
        self,
        saved_state,
        edited_grid,
        changes: GridChanges,
        locked_slots: Set[int]
    ) -> Dict[int, Set[str]]:
        """
        Update domains based on new constraints from edits.

        Args:
            saved_state: Original CSPState
            edited_grid: Grid with user edits
            changes: Detected changes
            locked_slots: Slots that are now locked

        Returns:
            Updated domains (slot_id -> set of valid words)
        """
        # Start with saved domains (convert lists to sets)
        updated_domains = {
            int(slot_id): set(words)
            for slot_id, words in saved_state.domains.items()
        }

        # For filled/modified slots, set domain to single word
        for slot_id in changes.filled_slots + changes.modified_slots:
            if slot_id in locked_slots:
                slot = saved_state.slot_list[slot_id]
                pattern = edited_grid.get_pattern_for_slot(slot)
                if '?' not in pattern:
                    # Set domain to just this word
                    updated_domains[slot_id] = {pattern}

        # For emptied slots, keep original domain
        # (will be recomputed during AC-3 if needed)

        # Run constraint propagation to update dependent domains
        updated_domains = self._propagate_constraints(
            updated_domains,
            saved_state.constraints,
            edited_grid,
            saved_state.slot_list
        )

        return updated_domains

    def _propagate_constraints(
        self,
        domains: Dict[int, Set[str]],
        constraints: Dict[int, List],
        grid,
        slot_list: List[Dict]
    ) -> Dict[int, Set[str]]:
        """
        Propagate constraints using AC-3 algorithm.

        Prunes domains based on arc consistency.

        Args:
            domains: Current domains
            constraints: Constraint graph
            grid: Current grid state
            slot_list: List of all slots

        Returns:
            Updated domains after constraint propagation
        """
        from collections import deque

        # Initialize queue with all arcs
        queue = deque()
        for slot_id in domains:
            if slot_id in constraints:
                for other_slot, pos1, pos2 in constraints[slot_id]:
                    queue.append((slot_id, other_slot, pos1, pos2))

        # AC-3 algorithm
        while queue:
            slot_id, other_slot, pos1, pos2 = queue.popleft()

            if self._revise(domains, slot_id, other_slot, pos1, pos2):
                # Domain was revised, re-check neighbors
                if slot_id in constraints:
                    for neighbor_slot, n_pos1, n_pos2 in constraints[slot_id]:
                        if neighbor_slot != other_slot:
                            queue.append((neighbor_slot, slot_id, n_pos2, n_pos1))

        return domains

    def _revise(
        self,
        domains: Dict[int, Set[str]],
        slot_id: int,
        other_slot: int,
        pos1: int,
        pos2: int
    ) -> bool:
        """
        Revise domain of slot_id based on constraint with other_slot.

        Args:
            domains: Current domains
            slot_id: Slot to revise
            other_slot: Constraining slot
            pos1: Position in slot_id
            pos2: Position in other_slot

        Returns:
            True if domain was revised, False otherwise
        """
        revised = False

        if slot_id not in domains or other_slot not in domains:
            return False

        words_to_remove = set()

        for word in domains[slot_id]:
            # Check if this word is compatible with any word in other_slot
            compatible = False

            for other_word in domains[other_slot]:
                # Check if letters match at intersection
                if len(word) > pos1 and len(other_word) > pos2:
                    if word[pos1] == other_word[pos2]:
                        compatible = True
                        break

            if not compatible:
                words_to_remove.add(word)
                revised = True

        # Remove incompatible words
        domains[slot_id] -= words_to_remove

        return revised

    def _validate_state(
        self,
        domains: Dict[int, Set[str]],
        constraints: Dict[int, List],
        slot_list: List[Dict]
    ) -> Dict[str, any]:
        """
        Validate that state is still solvable.

        Args:
            domains: Updated domains
            constraints: Constraint graph
            slot_list: List of all slots

        Returns:
            Dictionary with:
            - is_valid: bool
            - reason: str (if not valid)
            - empty_domains: list of slot IDs with empty domains
        """
        empty_domains = []

        for slot_id, domain in domains.items():
            if len(domain) == 0:
                empty_domains.append(slot_id)

        if empty_domains:
            # Get slot info for error message
            slot_info = []
            for slot_id in empty_domains[:3]:  # Show first 3
                if slot_id < len(slot_list):
                    slot = slot_list[slot_id]
                    slot_info.append(
                        f"({slot['row']},{slot['col']}) {slot['direction']}"
                    )

            return {
                'is_valid': False,
                'reason': f"Empty domains for slots: {', '.join(slot_info)}",
                'empty_domains': empty_domains
            }

        return {
            'is_valid': True,
            'reason': None,
            'empty_domains': []
        }

    def get_edit_summary(
        self,
        saved_grid_dict: Dict,
        edited_grid_dict: Dict,
        slot_list: List[Dict],
        slot_id_map: Dict
    ) -> Dict:
        """
        Get summary of edits without full merge.

        Useful for showing user what changes were made.

        Args:
            saved_grid_dict: Original grid
            edited_grid_dict: Edited grid
            slot_list: List of slots
            slot_id_map: Slot ID mapping

        Returns:
            Dictionary with edit summary
        """
        from cli.src.core.grid import Grid

        saved_grid = Grid.from_dict(saved_grid_dict)
        edited_grid = Grid.from_dict(edited_grid_dict)

        changes = self._detect_changes(
            saved_grid,
            edited_grid,
            slot_list,
            slot_id_map
        )

        return {
            'filled_count': len(changes.filled_slots),
            'emptied_count': len(changes.emptied_slots),
            'modified_count': len(changes.modified_slots),
            'new_words': list(changes.new_words),
            'removed_words': list(changes.removed_words)
        }
