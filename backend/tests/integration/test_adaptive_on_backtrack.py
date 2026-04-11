"""
Integration test verifying the on_backtrack callback is wired end-to-end.

Before the fix, AdaptiveAutofill registered self._on_backtrack on the
Autofill instance, but Autofill._backtrack / _backtrack_with_mac never
invoked the callback. The adaptive feature worked only via a fallback
(_find_most_constrained_slot) that doesn't use backtrack counts.

After the fix, on_backtrack is called at every backtrack point, feeding
slot_backtrack_counts so _find_problematic_slot works via the primary
(more precise) code path.
"""

from cli.src.core.grid import Grid
from cli.src.fill.adaptive_autofill import AdaptiveAutofill
from cli.src.fill.autofill import Autofill
from cli.src.fill.word_list import WordList


class TestAdaptiveOnBacktrackIntegration:
    """Verify that AdaptiveAutofill._on_backtrack is actually invoked
    by Autofill during a real fill run, populating slot_backtrack_counts."""

    def test_slot_backtrack_counts_populated(self):
        """Verify slot_backtrack_counts is non-empty after a constrained fill."""
        grid = Grid(11)
        # Create a grid with many crossing 3-letter slots by placing
        # black square rows/cols at positions 3 and 7.
        for r in range(11):
            grid.set_black_square(r, 3)
            grid.set_black_square(r, 7)
        for c in range(11):
            grid.set_black_square(3, c)
            grid.set_black_square(7, c)
        # This creates 54 crossing 3-letter slots — enough to force backtracking
        # with a limited word list.

        words = [
            "CAT",
            "CUP",
            "COB",
            "COT",
            "CUT",
            "BAT",
            "BUS",
            "BOW",
            "BOX",
            "BED",
            "RAT",
            "RUG",
            "ROD",
            "RIB",
            "RIM",
            "ACE",
            "ARC",
            "APE",
            "ATE",
            "AWE",
            "OAR",
            "OAK",
            "OAT",
            "OWL",
            "OWE",
            "UMP",
            "URN",
            "USE",
            "TEN",
            "TOP",
            "TON",
            "TAP",
            "TUB",
            "PEA",
            "PIG",
            "PIN",
            "POT",
            "PUN",
            "BIG",
            "BIT",
            "BOG",
            "BUN",
            "BUT",
            "DIG",
            "DIM",
            "DIP",
            "DOG",
            "DUG",
            "FIG",
            "FIN",
            "FIT",
            "FOG",
            "FUN",
            "GIG",
            "GIN",
            "GUM",
            "GUN",
            "GUT",
            "HIT",
            "HOG",
            "HOP",
            "HUG",
            "HUM",
        ]
        wl = WordList(words)

        adaptive = AdaptiveAutofill(
            grid=grid,
            wordlists=wl,
            options={"min_score": 0, "timeout": 5, "max_adaptations": 0},
            base_autofill=Autofill(grid, wl, timeout=5),
        )

        # Before fill, counts should be empty
        assert len(adaptive.slot_backtrack_counts) == 0

        # Run fill — it will likely fail (tiny word list) but that's OK,
        # what matters is that backtrack counts were recorded.
        adaptive.fill(timeout=5)

        # After fill, the on_backtrack callback should have populated counts
        assert len(adaptive.slot_backtrack_counts) > 0, (
            "slot_backtrack_counts was never populated — on_backtrack is not " "being called by Autofill during backtracking"
        )

    def test_on_backtrack_hook_is_set(self):
        """Verify AdaptiveAutofill sets on_backtrack on its inner Autofill."""
        grid = Grid(11)
        words = ["CAT", "BAT"]
        wl = WordList(words)

        adaptive = AdaptiveAutofill(
            grid=grid,
            wordlists=wl,
            options={"timeout": 1},
            base_autofill=Autofill(grid, wl, timeout=1),
        )

        # The hook should be set during __init__ → _create_autofill
        assert adaptive.autofill.on_backtrack is not None
        assert adaptive.autofill.on_backtrack == adaptive._on_backtrack
