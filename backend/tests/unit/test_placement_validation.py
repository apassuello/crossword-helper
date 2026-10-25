"""
Unit tests for backend.core.placement_validation (issue #15).

This module is the single implementation of the applier's conflict check —
cell/intersection conflicts and 180-degree rotational-symmetry boundary-black
conflicts. Both the apply-placement route and ThemePlacer.suggest_placements
call it; these tests pin the contract they both depend on.
"""

import copy

from backend.core.placement_validation import apply_checked_placement, check_placement, validate_placement


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


class TestApplyCheckedPlacement:
    """The one write step shared by the apply route and the joint-plan search."""

    def test_string_and_dict_formats_get_the_same_result(self):
        placement = {"word": "HELLO", "row": 2, "col": 3, "direction": "across"}
        strings = [["." for _ in range(11)] for _ in range(11)]
        dicts = _empty_grid(11)
        c1, b1 = apply_checked_placement(strings, placement)
        c2, b2 = apply_checked_placement(dicts, placement)
        assert c1 == c2 == []
        assert b1 == b2 == [[2, 2], [2, 8], [8, 8], [8, 2]]
        assert strings[2][2] == "#" and strings[8][8] == "#"
        assert dicts[2][2] == {"letter": "", "isBlack": True}
        for g in (strings, dicts):
            assert [g[2][3 + i]["letter"] for i in range(5)] == list("HELLO")
            assert all(g[2][3 + i]["isThemeLocked"] for i in range(5))

    def test_conflict_leaves_grid_untouched(self):
        grid = _empty_grid(15)
        grid[7][6] = {"letter": "Z", "isBlack": False}
        before = copy.deepcopy(grid)
        conflicts, added = apply_checked_placement(grid, {"word": "HELLO", "row": 7, "col": 5, "direction": "across"})
        assert conflicts and added == []
        assert grid == before

    def test_does_not_mutate_cell_objects_so_row_copies_are_safe(self):
        grid = _empty_grid(11)
        trial = [row[:] for row in grid]
        before = copy.deepcopy(grid)
        apply_checked_placement(trial, {"word": "HELLO", "row": 2, "col": 3, "direction": "across"})
        assert grid == before
