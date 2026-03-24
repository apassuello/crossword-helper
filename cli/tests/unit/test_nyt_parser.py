"""Unit tests for cli.src.core.nyt_parser module."""

import json

import pytest

from src.core.nyt_parser import (
    NytDataError,
    NytFormatError,
    NytParseError,
    NytParseResult,
    NytWord,
    extract_words,
    load_nyt_file,
    nyt_grid_to_internal,
    parse_clue_string,
    parse_nyt_json,
    verify_extraction,
)
from src.core.numbering import GridNumbering


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_nyt_3x3(
    grid=None,
    gridnums=None,
    clues=None,
    answers=None,
    size=None,
    **overrides,
) -> dict:
    """Build a minimal valid 3x3 NYT data dict.

    Default layout:
        C A T
        . O .
        D O G

    Black squares at (1,0) and (1,2).

    Across words: 1-Across CAT, 3-Across DOG
    Down words:   1-Down CO, 2-Down AOO? -- actually let's keep it simple.

    Numbering:
        1  2  3
        .  -  .
        4  -  5

    1-Across: CAT (row 0, cols 0-2)
    4-Across: DOG (row 2, cols 0-2)
    1-Down:   CO  -- wait, (1,0) is black. Let me reconsider.

    Revised layout (no black squares, simple):
        C A T
        O N E
        B E D

    gridnums: 1 2 3 / 4 0 0 / 5 0 0
    Across: 1=CAT, 4=ONE, 5=BED
    Down: 1=COB, 2=ANE, 3=TED
    """
    if grid is None:
        grid = [
            "C", "A", "T",
            "O", "N", "E",
            "B", "E", "D",
        ]

    if gridnums is None:
        gridnums = [1, 2, 3, 4, 0, 0, 5, 0, 0]

    if clues is None:
        clues = {
            "across": ["1. Feline", "4. Single", "5. Place to sleep"],
            "down": ["1. Corn on the ___", "2. Herb genus", "3. Classic name"],
        }

    if answers is None:
        answers = {
            "across": ["CAT", "ONE", "BED"],
            "down": ["COB", "ANE", "TED"],
        }

    if size is None:
        size = {"rows": 3, "cols": 3}

    data = {
        "size": size,
        "grid": grid,
        "gridnums": gridnums,
        "clues": clues,
        "answers": answers,
    }
    data.update(overrides)
    return data


@pytest.fixture
def nyt_3x3():
    """Minimal valid 3x3 NYT data dict (no black squares)."""
    return _make_nyt_3x3()


@pytest.fixture
def nyt_3x3_file(tmp_path, nyt_3x3):
    """Write the 3x3 fixture to a temp JSON file and return the path."""
    p = tmp_path / "puzzle.json"
    p.write_text(json.dumps(nyt_3x3))
    return str(p)


def _make_nyt_3x3_with_blacks():
    """3x3 with black squares at (1,0) and (1,2).

    Layout:
        C A T
        . O .
        D O G

    Auto-numbering assigns:
        1(0,0) 2(0,1) -(0,2)
        .      -      .
        3(2,0) -      -(2,2)

    (0,2) gets no number: col 2 is last col (no across) and (1,2) is black (no down).
    (2,2) gets no number: col 2 is last col (no across) and (2,2) is last row (no down).

    Across: 1=CAT, 3=DOG
    Down: 2=AOO (col 1, rows 0-2)
    """
    return _make_nyt_3x3(
        grid=["C", "A", "T", ".", "O", ".", "D", "O", "G"],
        gridnums=[1, 2, 0, 0, 0, 0, 3, 0, 0],
        clues={
            "across": ["1. Feline", "3. Canine"],
            "down": ["2. Sound of wonder"],
        },
        answers={
            "across": ["CAT", "DOG"],
            "down": ["AOO"],
        },
    )


# ---------------------------------------------------------------------------
# TestLoadNytFile
# ---------------------------------------------------------------------------


class TestLoadNytFile:
    """Tests for load_nyt_file."""

    def test_loads_valid_file(self, nyt_3x3_file, nyt_3x3):
        data = load_nyt_file(nyt_3x3_file)
        assert data["size"] == nyt_3x3["size"]
        assert data["grid"] == nyt_3x3["grid"]

    def test_file_not_found(self, tmp_path):
        with pytest.raises(NytParseError, match="File not found"):
            load_nyt_file(str(tmp_path / "nope.json"))

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json")
        with pytest.raises(NytFormatError, match="Invalid JSON"):
            load_nyt_file(str(p))

    @pytest.mark.parametrize("missing_key", ["size", "grid", "gridnums", "clues", "answers"])
    def test_missing_required_key(self, tmp_path, nyt_3x3, missing_key):
        del nyt_3x3[missing_key]
        p = tmp_path / "missing.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytFormatError, match="Missing required keys"):
            load_nyt_file(str(p))

    def test_size_not_dict(self, tmp_path, nyt_3x3):
        nyt_3x3["size"] = 3
        p = tmp_path / "bad_size.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytFormatError, match="'size' must be dict"):
            load_nyt_file(str(p))

    def test_size_missing_rows(self, tmp_path, nyt_3x3):
        nyt_3x3["size"] = {"cols": 3}
        p = tmp_path / "bad_size.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytFormatError, match="'size' must be dict"):
            load_nyt_file(str(p))

    def test_non_square_grid(self, tmp_path, nyt_3x3):
        nyt_3x3["size"] = {"rows": 3, "cols": 5}
        p = tmp_path / "non_square.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytFormatError, match="Non-square grids not supported"):
            load_nyt_file(str(p))

    def test_grid_length_mismatch(self, tmp_path, nyt_3x3):
        nyt_3x3["grid"] = ["A", "B"]  # too short
        p = tmp_path / "short_grid.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytDataError, match="Grid length"):
            load_nyt_file(str(p))

    def test_grid_not_list(self, tmp_path, nyt_3x3):
        nyt_3x3["grid"] = "not a list"
        p = tmp_path / "bad_grid.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytDataError, match="Grid length"):
            load_nyt_file(str(p))

    def test_gridnums_length_mismatch(self, tmp_path, nyt_3x3):
        nyt_3x3["gridnums"] = [1, 2]
        p = tmp_path / "bad_gridnums.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytDataError, match="gridnums length"):
            load_nyt_file(str(p))

    def test_clues_not_dict(self, tmp_path, nyt_3x3):
        nyt_3x3["clues"] = "bad"
        p = tmp_path / "bad_clues.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytFormatError, match="'clues' must be a dict"):
            load_nyt_file(str(p))

    def test_clues_missing_direction(self, tmp_path, nyt_3x3):
        del nyt_3x3["clues"]["down"]
        p = tmp_path / "no_down.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytFormatError, match="'clues' missing 'down'"):
            load_nyt_file(str(p))

    def test_answers_direction_not_list(self, tmp_path, nyt_3x3):
        nyt_3x3["answers"]["across"] = "not a list"
        p = tmp_path / "bad_answers.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytFormatError, match="'answers.across' must be a list"):
            load_nyt_file(str(p))

    def test_clue_answer_count_mismatch(self, tmp_path, nyt_3x3):
        nyt_3x3["answers"]["across"].append("EXTRA")
        p = tmp_path / "mismatch.json"
        p.write_text(json.dumps(nyt_3x3))
        with pytest.raises(NytDataError, match="across.*3 clues but 4 answers"):
            load_nyt_file(str(p))


# ---------------------------------------------------------------------------
# TestNytGridToInternal
# ---------------------------------------------------------------------------


class TestNytGridToInternal:
    """Tests for nyt_grid_to_internal."""

    def test_all_letters(self, nyt_3x3):
        empty, filled, has_rebus = nyt_grid_to_internal(nyt_3x3)
        assert empty.size == 3
        assert filled.size == 3
        assert has_rebus is False

        # Empty grid should have all '.' (no letters)
        for r in range(3):
            for c in range(3):
                assert empty.get_cell(r, c) == "."

        # Filled grid should have uppercase letters
        assert filled.get_cell(0, 0) == "C"
        assert filled.get_cell(0, 1) == "A"
        assert filled.get_cell(0, 2) == "T"
        assert filled.get_cell(2, 2) == "D"

    def test_black_squares(self):
        data = _make_nyt_3x3_with_blacks()
        empty, filled, has_rebus = nyt_grid_to_internal(data)

        # NYT "." -> internal "#"
        assert empty.is_black(1, 0)
        assert empty.is_black(1, 2)
        assert filled.is_black(1, 0)
        assert filled.is_black(1, 2)

        # Non-black cells remain accessible
        assert empty.get_cell(0, 0) == "."
        assert filled.get_cell(0, 0) == "C"
        assert filled.get_cell(1, 1) == "O"

    def test_rebus_cells(self):
        """Rebus cells (multi-letter) take the first letter."""
        data = _make_nyt_3x3(
            grid=["TH", "A", "T", "O", "N", "E", "B", "E", "D"],
        )
        empty, filled, has_rebus = nyt_grid_to_internal(data)

        assert has_rebus is True
        assert filled.get_cell(0, 0) == "T"  # first letter of "TH"
        assert empty.get_cell(0, 0) == "."

    def test_lowercase_uppercased(self):
        data = _make_nyt_3x3(
            grid=["c", "a", "t", "o", "n", "e", "b", "e", "d"],
        )
        _, filled, _ = nyt_grid_to_internal(data)
        assert filled.get_cell(0, 0) == "C"
        assert filled.get_cell(1, 1) == "N"

    def test_all_black(self):
        data = _make_nyt_3x3(
            grid=[".", ".", ".", ".", ".", ".", ".", ".", "."],
        )
        empty, filled, has_rebus = nyt_grid_to_internal(data)
        for r in range(3):
            for c in range(3):
                assert empty.is_black(r, c)
                assert filled.is_black(r, c)
        assert has_rebus is False

    def test_unknown_cell_type(self):
        """Non-alpha single chars (e.g. digits) become '.' in both grids."""
        data = _make_nyt_3x3(
            grid=["1", "A", "T", "O", "N", "E", "B", "E", "D"],
        )
        empty, filled, _ = nyt_grid_to_internal(data)
        # "1" is not alpha, not ".", not multi-char -> fallback '.'
        assert empty.get_cell(0, 0) == "."
        assert filled.get_cell(0, 0) == "."


# ---------------------------------------------------------------------------
# TestParseClueString
# ---------------------------------------------------------------------------


class TestParseClueString:
    """Tests for parse_clue_string."""

    def test_dot_format(self):
        assert parse_clue_string("1. Defrost") == (1, "Defrost")

    def test_paren_format(self):
        assert parse_clue_string("42) Big deal") == (42, "Big deal")

    def test_space_format(self):
        assert parse_clue_string("7 Lucky number") == (7, "Lucky number")

    def test_no_space_after_separator(self):
        assert parse_clue_string("3.Word") == (3, "Word")

    def test_multi_digit_number(self):
        assert parse_clue_string("123. Long clue here") == (123, "Long clue here")

    def test_clue_with_extra_whitespace(self):
        num, text = parse_clue_string("5.   Lots of spaces  ")
        assert num == 5
        assert text == "Lots of spaces"

    def test_fallback_number_no_separator(self):
        """Fallback regex grabs a leading number even without ., ), or space."""
        num, text = parse_clue_string("99SomeClue")
        assert num == 99
        assert text == "SomeClue"

    def test_no_number_raises(self):
        with pytest.raises(NytDataError, match="Cannot parse clue string"):
            parse_clue_string("No number here")

    def test_empty_string_raises(self):
        with pytest.raises(NytDataError, match="Cannot parse clue string"):
            parse_clue_string("")

    def test_clue_text_empty(self):
        num, text = parse_clue_string("1.")
        assert num == 1
        assert text == ""


# ---------------------------------------------------------------------------
# TestExtractWords
# ---------------------------------------------------------------------------


class TestExtractWords:
    """Tests for extract_words."""

    def test_extracts_all_words(self, nyt_3x3):
        empty, _, _ = nyt_grid_to_internal(nyt_3x3)
        numbering = GridNumbering.auto_number(empty)
        words = extract_words(nyt_3x3, numbering, empty)

        across = [w for w in words if w.direction == "across"]
        down = [w for w in words if w.direction == "down"]

        assert len(across) == 3
        assert len(down) == 3

        across_by_num = {w.number: w for w in across}
        assert across_by_num[1].answer == "CAT"
        assert across_by_num[1].row == 0
        assert across_by_num[1].col == 0
        assert across_by_num[1].length == 3
        assert across_by_num[1].clue == "Feline"

    def test_word_positions(self, nyt_3x3):
        empty, _, _ = nyt_grid_to_internal(nyt_3x3)
        numbering = GridNumbering.auto_number(empty)
        words = extract_words(nyt_3x3, numbering, empty)

        down_by_num = {w.number: w for w in words if w.direction == "down"}
        # 1-Down starts at (0,0)
        assert down_by_num[1].row == 0
        assert down_by_num[1].col == 0
        assert down_by_num[1].answer == "COB"

    def test_with_black_squares(self):
        data = _make_nyt_3x3_with_blacks()
        empty, _, _ = nyt_grid_to_internal(data)
        numbering = GridNumbering.auto_number(empty)
        words = extract_words(data, numbering, empty)

        across = [w for w in words if w.direction == "across"]
        down = [w for w in words if w.direction == "down"]

        across_answers = {w.answer for w in across}
        assert "CAT" in across_answers
        assert "DOG" in across_answers

        # Down word through col 1: A-O-O
        down_answers = {w.answer for w in down}
        assert "AOO" in down_answers

    def test_skips_unparseable_clues(self, nyt_3x3):
        """Clues that can't be parsed are silently skipped."""
        nyt_3x3["clues"]["across"][1] = "no-number-here"
        empty, _, _ = nyt_grid_to_internal(nyt_3x3)
        numbering = GridNumbering.auto_number(empty)
        words = extract_words(nyt_3x3, numbering, empty)

        across = [w for w in words if w.direction == "across"]
        # One across clue was skipped
        assert len(across) == 2

    def test_skips_unknown_number(self, nyt_3x3):
        """If clue references a number not in numbering, it's skipped."""
        nyt_3x3["clues"]["across"][0] = "999. Ghost clue"
        nyt_3x3["answers"]["across"][0] = "XXX"
        empty, _, _ = nyt_grid_to_internal(nyt_3x3)
        numbering = GridNumbering.auto_number(empty)
        words = extract_words(nyt_3x3, numbering, empty)

        across = [w for w in words if w.direction == "across"]
        nums = {w.number for w in across}
        assert 999 not in nums


# ---------------------------------------------------------------------------
# TestVerifyExtraction — tested indirectly through parse_nyt_json too
# ---------------------------------------------------------------------------


class TestVerifyExtraction:
    """Tests for verify_extraction."""

    def test_successful_verification(self, nyt_3x3):
        empty, _, _ = nyt_grid_to_internal(nyt_3x3)
        numbering = GridNumbering.auto_number(empty)
        words = extract_words(nyt_3x3, numbering, empty)
        result = verify_extraction(nyt_3x3, empty, words, 3)

        assert result.success is True
        assert result.grid_match is True
        assert result.conflicts == []
        assert result.mismatched_cells == []
        assert result.words_placed == result.total_words

    def test_with_black_squares(self):
        data = _make_nyt_3x3_with_blacks()
        empty, _, _ = nyt_grid_to_internal(data)
        numbering = GridNumbering.auto_number(empty)
        words = extract_words(data, numbering, empty)
        result = verify_extraction(data, empty, words, 3)

        assert result.success is True
        assert result.grid_match is True

    def test_detects_conflict_wrong_answer(self, nyt_3x3):
        """If a word's answer doesn't match the grid, verification catches it."""
        empty, _, _ = nyt_grid_to_internal(nyt_3x3)
        numbering = GridNumbering.auto_number(empty)
        words = extract_words(nyt_3x3, numbering, empty)

        # Corrupt an answer to create a crossing conflict
        for w in words:
            if w.number == 1 and w.direction == "across":
                w.answer = "CZT"  # Z conflicts with 2-Down 'A' at (0,1)
                break

        result = verify_extraction(nyt_3x3, empty, words, 3)
        # Grid won't match because reconstructed grid has Z instead of A at (0,1)
        assert result.grid_match is False or len(result.conflicts) > 0
        assert result.success is False

    def test_detects_missing_cells(self, nyt_3x3):
        """If no word covers a cell, it shows up as mismatched."""
        empty, _, _ = nyt_grid_to_internal(nyt_3x3)
        # Pass empty word list -> no cells get filled -> all cells mismatch
        result = verify_extraction(nyt_3x3, empty, [], 3)

        assert result.success is False
        assert result.grid_match is False
        assert len(result.mismatched_cells) == 9  # all cells empty
        assert result.words_placed == 0


# ---------------------------------------------------------------------------
# TestParseNytJson — end-to-end through parse_nyt_json
# ---------------------------------------------------------------------------


class TestParseNytJson:
    """Tests for parse_nyt_json (main entry point)."""

    def test_full_parse_with_verification(self, nyt_3x3_file):
        result = parse_nyt_json(nyt_3x3_file, verify=True)

        assert isinstance(result, NytParseResult)
        assert result.size == 3
        assert result.verification is not None
        assert result.verification.success is True
        assert len(result.words) == 6  # 3 across + 3 down

    def test_full_parse_without_verification(self, nyt_3x3_file):
        result = parse_nyt_json(nyt_3x3_file, verify=False)

        assert result.verification is None
        assert result.size == 3
        assert len(result.words) == 6

    def test_metadata_extracted(self, tmp_path):
        data = _make_nyt_3x3(
            title="Monday Puzzle",
            author="Will Shortz",
            editor="Joel Fagliano",
            date="2024-01-15",
            dow="Monday",
        )
        p = tmp_path / "meta.json"
        p.write_text(json.dumps(data))

        result = parse_nyt_json(str(p))
        assert result.metadata["title"] == "Monday Puzzle"
        assert result.metadata["author"] == "Will Shortz"
        assert result.metadata["editor"] == "Joel Fagliano"
        assert result.metadata["date"] == "2024-01-15"
        assert result.metadata["dow"] == "Monday"
        assert result.metadata["has_rebus"] is False

    def test_missing_metadata_defaults_empty(self, nyt_3x3_file):
        result = parse_nyt_json(nyt_3x3_file)
        assert result.metadata["title"] == ""
        assert result.metadata["author"] == ""

    def test_rebus_flagged_in_metadata(self, tmp_path):
        data = _make_nyt_3x3(
            grid=["TH", "A", "T", "O", "N", "E", "B", "E", "D"],
        )
        p = tmp_path / "rebus.json"
        p.write_text(json.dumps(data))

        result = parse_nyt_json(str(p), verify=False)
        assert result.metadata["has_rebus"] is True

    def test_with_black_squares(self, tmp_path):
        data = _make_nyt_3x3_with_blacks()
        p = tmp_path / "blacks.json"
        p.write_text(json.dumps(data))

        result = parse_nyt_json(str(p), verify=True)
        assert result.verification.success is True

        across = [w for w in result.words if w.direction == "across"]
        down = [w for w in result.words if w.direction == "down"]
        assert len(across) == 2
        assert len(down) == 1

    def test_file_not_found_raises(self):
        with pytest.raises(NytParseError):
            parse_nyt_json("/nonexistent/path/puzzle.json")

    def test_invalid_json_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{{{{")
        with pytest.raises(NytFormatError):
            parse_nyt_json(str(p))

    def test_numbering_dict_populated(self, nyt_3x3_file):
        result = parse_nyt_json(nyt_3x3_file)
        # 3x3 all-white grid: cells (0,0), (0,1), (0,2), (1,0), (2,0)
        # should all get numbers
        assert len(result.numbering) > 0
        assert (0, 0) in result.numbering
        assert result.numbering[(0, 0)] == 1

    def test_words_are_nyt_word_objects(self, nyt_3x3_file):
        result = parse_nyt_json(nyt_3x3_file)
        for w in result.words:
            assert isinstance(w, NytWord)
            assert w.direction in ("across", "down")
            assert isinstance(w.number, int)
            assert isinstance(w.answer, str)
            assert isinstance(w.clue, str)
            assert w.length > 0

    def test_empty_grid_has_no_letters(self, nyt_3x3_file):
        result = parse_nyt_json(nyt_3x3_file)
        for r in range(result.size):
            for c in range(result.size):
                cell = result.empty_grid.get_cell(r, c)
                assert cell in (".", "#")

    def test_filled_grid_has_letters(self, nyt_3x3_file):
        result = parse_nyt_json(nyt_3x3_file)
        has_letter = False
        for r in range(result.size):
            for c in range(result.size):
                cell = result.filled_grid.get_cell(r, c)
                if cell not in (".", "#"):
                    has_letter = True
                    assert cell.isalpha() and cell.isupper()
        assert has_letter
