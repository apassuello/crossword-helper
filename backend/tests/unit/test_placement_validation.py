"""
Unit tests for backend.core.placement_validation (issue #15).

This module is the single implementation of the applier's conflict check —
cell/intersection conflicts and 180-degree rotational-symmetry boundary-black
conflicts. Both the apply-placement route and ThemePlacer.suggest_placements
call it; these tests pin the contract they both depend on.
"""

from backend.core.placement_validation import check_placement, validate_placement


def _empty_grid(size=15):
    return [[{"letter": "", "isBlack": False} for _ in range(size)] for _ in range(size)]


class TestValidatePlacement:
    """Unit acceptance test #2 from the task-3 brief."""

    def test_rejects_boundary_twin_conflict_with_exact_message(self):
        """CROSSWORD (9 letters) at (7, 5, across) needs a boundary black at
        (7, 4); its 180-degree twin (7, 10) falls inside the word itself.
        """
        grid = _empty_grid(15)
        placement = {"word": "CROSSWORD", "row": 7, "col": 5, "direction": "across"}

        conflicts = validate_placement(grid, placement)

        assert (
            "Boundary black square at (7, 4) requires a symmetric "
            "black square at (7, 10), which is occupied by this "
            "word — placement would break grid symmetry"
        ) in conflicts

    def test_accepts_centered_placement_and_computes_symmetric_blacks(self):
        """The centered placement of CROSSWORD on row 7 is col 3: it is
        valid, and it needs boundary blacks at (7, 2) and (7, 12) — each is
        the other's 180-degree twin, so no extra twin squares are required.
        """
        grid = _empty_grid(15)
        placement = {"word": "CROSSWORD", "row": 7, "col": 3, "direction": "across"}

        conflicts, boundary_blacks, twin_blacks = check_placement(grid, placement)

        assert conflicts == []
        assert validate_placement(grid, placement) == []
        assert sorted(list(boundary_blacks) + list(twin_blacks)) == [(7, 2), (7, 12)]

    def test_is_read_only(self):
        """A validator that mutates the grid it is checking would corrupt
        every candidate the suggester tests against it.
        """
        grid = _empty_grid(15)
        placement = {"word": "CROSSWORD", "row": 7, "col": 5, "direction": "across"}

        import copy

        before = copy.deepcopy(grid)
        validate_placement(grid, placement)

        assert grid == before
