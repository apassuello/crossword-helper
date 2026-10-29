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
            "Boundary black square at (8, 5) requires a symmetric "
            "black square at (8, 11), which is occupied by this "
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


class TestMessagePositionsAreOneBased:
    """#94: the grid labels rows and columns from 1, so every position in a
    conflict message is the zero-based index plus one. Display only."""

    def test_letter_conflict_reports_one_based_position(self):
        grid = _empty_grid(15)
        grid[5][6] = {"letter": "A", "isBlack": False}
        conflicts = validate_placement(grid, {"word": "BC", "row": 5, "col": 6, "direction": "across"})
        assert "Letter conflict at (6, 7): trying to place 'B' but cell already contains 'A'" in conflicts

    def test_black_cell_reports_one_based_position(self):
        grid = _empty_grid(15)
        grid[3][4] = {"letter": "", "isBlack": True}
        conflicts = validate_placement(grid, {"word": "AB", "row": 3, "col": 4, "direction": "across"})
        assert "Cannot place 'A' at (4, 5): cell is black" in conflicts

    def test_out_of_bounds_reports_one_based_position(self):
        grid = _empty_grid(15)
        across = validate_placement(grid, {"word": "ABC", "row": 2, "col": 13, "direction": "across"})
        assert "Position (3, 16) out of bounds" in across
        down = validate_placement(grid, {"word": "ABC", "row": 13, "col": 2, "direction": "down"})
        assert "Position (16, 3) out of bounds" in down

    def test_boundary_twin_letter_reports_one_based_positions(self):
        grid = _empty_grid(15)
        grid[12][12] = {"letter": "Q", "isBlack": False}
        conflicts = validate_placement(grid, {"word": "HELLO", "row": 2, "col": 3, "direction": "across"})
        assert (
            "Boundary black square at (3, 3) requires a symmetric black square at (13, 13), but that cell contains 'Q'"
        ) in conflicts


class TestBoundaryLetterRunsOn:
    """A letter directly before or after a word does not terminate it, unlike a
    black square or the grid edge: the run continues and the real entry is
    longer than the word. Such a placement used to be accepted (and suggested)
    as if the letter were a black square.
    """

    def _grid_with_s(self):
        grid = [["." for _ in range(7)] for _ in range(7)]
        grid[3][3] = "S"
        return grid

    def test_rejects_letter_after_word(self):
        grid = self._grid_with_s()
        conflicts = validate_placement(grid, {"word": "CAT", "row": 3, "col": 0, "direction": "across"})
        assert "Cell (4, 4) next to the word contains 'S': the entry would run on past the word" in conflicts

    def test_rejects_letter_before_word_down(self):
        grid = self._grid_with_s()
        conflicts = validate_placement(grid, {"word": "CAT", "row": 4, "col": 3, "direction": "down"})
        assert "Cell (4, 4) next to the word contains 'S': the entry would run on past the word" in conflicts

    def test_dict_format_letter_is_rejected_too(self):
        grid = _empty_grid(7)
        grid[3][3] = {"letter": "S", "isBlack": False}
        assert validate_placement(grid, {"word": "CAT", "row": 3, "col": 4, "direction": "across"}) != []

    def test_black_square_and_edge_still_terminate(self):
        grid = self._grid_with_s()
        grid[3][3] = "#"
        assert validate_placement(grid, {"word": "CAT", "row": 3, "col": 0, "direction": "across"}) == []
        assert validate_placement(grid, {"word": "CAT", "row": 3, "col": 4, "direction": "across"}) == []

    def test_word_crossing_the_letter_is_still_valid(self):
        grid = self._grid_with_s()
        assert validate_placement(grid, {"word": "ASK", "row": 3, "col": 2, "direction": "across"}) == []


class TestBlackSquareStubs:
    """Blacks a placement adds split the runs they land in. A resulting 1-2 cell
    stub is a conflict only when it holds an existing letter (owner ruling,
    2026-10-29); an empty stub is left for the user to black out.
    """

    PLACEMENT = {"word": "EASTERN", "row": 6, "col": 4, "direction": "across"}

    def test_rejects_stub_cutting_a_filled_crossing_entry(self):
        # EASTERN needs blacks at (6,3) and its twin (8,3), stranding the N at
        # (7,3) as a 1-letter down entry.
        grid = [["." for _ in range(15)] for _ in range(15)]
        grid[7][3] = "N"
        conflicts = validate_placement(grid, self.PLACEMENT)
        assert "Black square at (7, 4) would leave a 1-letter entry at (8, 4)-(8, 4)" in conflicts

    def test_empty_stub_is_allowed(self):
        # Same blacks on an empty grid strand an empty (7,3): allowed.
        grid = [["." for _ in range(15)] for _ in range(15)]
        assert validate_placement(grid, self.PLACEMENT) == []

    def test_suggester_never_strands_an_existing_letter(self):
        from backend.core.theme_placer import ThemePlacer

        grid = [["." for _ in range(15)] for _ in range(15)]
        grid[7][3] = "N"
        results = ThemePlacer(15).suggest_placements(["EASTERN"], existing_grid=grid, max_suggestions_per_word=500)
        placed = {(s["row"], s["col"], s["direction"]) for s in results[0]["suggestions"]}
        assert results[0]["suggestions"]
        assert (6, 4, "across") not in placed
