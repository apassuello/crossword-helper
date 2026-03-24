"""
Beam state representation for crossword autofill.

This module contains the BeamState dataclass which represents one partial
solution in the beam search algorithm.
"""

from typing import Dict, Set, Tuple, List
from dataclasses import dataclass, field
from ...core.grid import Grid


@dataclass
class BeamState:
    """
    Represents one partial solution in the beam.

    Immutable snapshot of a crossword solution state with metadata for scoring.

    Invariants:
    - 0 ≤ slots_filled ≤ total_slots
    - length(used_words) == slots_filled
    - 0.0 ≤ score ≤ 100.0
    - All words in used_words exist in grid
    """

    grid: Grid  # Current grid state
    slots_filled: int  # Number of slots filled so far
    total_slots: int  # Total slots in grid
    score: float  # Quality score (0.0-100.0)
    used_words: Set[str] = field(
        default_factory=set
    )  # Words placed (prevent duplicates)
    slot_assignments: Dict[Tuple[int, int, str], str] = field(
        default_factory=dict
    )  # slot → word
    domains: Dict[Tuple[int, int, str], List[str]] = field(
        default_factory=dict
    )  # slot → candidate words
    domain_reductions: Dict[Tuple[int, int, str], List] = field(
        default_factory=dict
    )  # slot → MAC reductions

    def completion_rate(self) -> float:
        """Return fraction of slots filled (0.0-1.0)"""
        return self.slots_filled / self.total_slots if self.total_slots > 0 else 0.0

    def clone(self) -> "BeamState":
        """
        Create deep copy of this state.

        Postconditions:
        - Returned state is independent (modifications don't affect original)
        - Grid is cloned (not reference)
        - used_words is copied (not reference)
        - domains and domain_reductions are copied (not reference)
        """
        return BeamState(
            grid=self.grid.clone(),  # CRITICAL: deep copy
            slots_filled=self.slots_filled,
            total_slots=self.total_slots,
            score=self.score,
            used_words=self.used_words.copy(),  # CRITICAL: copy set
            slot_assignments=self.slot_assignments.copy(),
            domains={
                k: v.copy() if isinstance(v, list) else v
                for k, v in self.domains.items()
            },
            domain_reductions=self.domain_reductions.copy(),
        )

    def __eq__(self, other: "BeamState") -> bool:
        """
        Check equality (for testing).

        Two states are equal if they have same grid contents and used words.
        """
        if not isinstance(other, BeamState):
            return False

        # Check grid equality by comparing cells content
        # Grid doesn't have __eq__, so compare cells directly
        import numpy as np

        grids_equal = np.array_equal(self.grid.cells, other.grid.cells)

        return grids_equal and self.used_words == other.used_words

    def __hash__(self) -> int:
        """
        Compute hash (for using in sets/dicts).

        Based on grid contents and used words only.
        """
        # Use frozenset for used_words since sets aren't hashable
        return hash((tuple(self.grid.cells.flatten()), frozenset(self.used_words)))
