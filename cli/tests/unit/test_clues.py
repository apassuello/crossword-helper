"""Unit tests for the clue map: validation, key order, status and carry.

Spec: docs/superpowers/specs/2026-10-31-clue-authoring-design.md, sections 3.1,
3.2, 3.4, 6.1 (Validation, Status), 6.3 and 8. The status cases are read from
tests/fixtures/clue_status_cases.json, which the frontend tests read as well.
"""

import json
from pathlib import Path

import pytest
from src.core.clues import (
    CluesError,
    carry_clues,
    clue_key_sort,
    clue_statuses,
    validate_clues,
)
from src.core.grid import Grid

# cli/tests/unit/test_clues.py -> repository root is three parents up.
FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "clue_status_cases.json"

# Spec 3.4 reasons, appended to: Invalid clue "<key>": <reason>.
KEY_REASON = 'key must be "row,col,across" or "row,col,down" inside the grid'
SHAPE_REASON = "must have text and answer strings"
WHITESPACE_REASON = "text must not start or end with whitespace"
LENGTH_REASON = "text must be 1 to 200 characters"
ANSWER_REASON = "answer must be 2 or more of A-Z or ?"


def msg(key, reason):
    return f'Invalid clue "{key}": {reason}.'


def clue(text="Flower", answer="ROSE"):
    return {"text": text, "answer": answer}


def rejected(clues, size=15):
    """Return the CluesError message for a map the validator must refuse."""
    with pytest.raises(CluesError) as excinfo:
        validate_clues(clues, size)
    return str(excinfo.value)


def load_cases():
    with open(FIXTURE_PATH, encoding="utf-8") as handle:
        return json.load(handle)["cases"]


def grid_from_rows(rows):
    # A 4x4 is non-standard, so strict_size=False; without it every row would
    # fail for the wrong reason, including the 2-letter RO row of spec 6.3.
    return Grid.from_dict({"size": 4, "grid": rows}, strict_size=False)


class TestCluesError:
    def test_is_a_value_error(self):
        assert issubclass(CluesError, ValueError)


class TestValidateRule1:
    @pytest.mark.parametrize("bad", [None, [], [clue()], "clues", 3, True])
    def test_non_object_rejected(self, bad):
        assert rejected(bad) == "Invalid clues: must be an object."

    def test_empty_object_valid(self):
        assert validate_clues({}, 15) is None

    def test_valid_map_returns_none(self):
        assert validate_clues({"0,0,across": clue(), "2,0,down": clue("Up", "AB")}, 15) is None


class TestValidateRule2Keys:
    @pytest.mark.parametrize(
        "key",
        [
            "00,0,across",  # leading zero in row
            "0,00,across",  # leading zero in column
            "0,0,Across",  # case matters
            "0,0,sideways",
            "0,0",
            "0,0,across,",
            " 0,0,across",
            "0, 0,across",
            "-1,0,across",
            "a,0,across",
            "",
            "0,0,across\n",  # `$` would match before a trailing newline
            "1\u0660,0,across",  # Arabic-Indic zero after a 1: \d would accept it
            "15,0,across",  # row == size, outside the grid
            "0,15,down",  # column == size
            "99,99,down",
        ],
    )
    def test_bad_key_rejected_with_exact_message(self, key):
        assert rejected({key: clue()}, 15) == msg(key, KEY_REASON)

    def test_bound_is_the_size_argument(self):
        assert validate_clues({"14,14,down": clue()}, 15) is None
        assert rejected({"14,14,down": clue()}, 11) == msg("14,14,down", KEY_REASON)

    def test_last_row_and_column_accepted(self):
        assert validate_clues({"0,14,down": clue(), "14,0,across": clue()}, 15) is None

    def test_key_errors_reported_in_code_point_order(self):
        # Inserted in the reverse of code-point order: "9,9,down" > "10,0,across"
        # > "0,0,Across" ('1' < '9' and '0' < '1'). Every key is bad.
        clues = {"9,9,down": clue(), "10,0,across": clue(), "0,0,Across": clue()}
        assert rejected(clues, 4) == msg("0,0,Across", KEY_REASON)

    def test_code_point_order_is_not_key_order(self):
        # Key order would reach "2,0,down" first; code-point order reaches
        # "10,0,across" first. Both are outside a 2x2 grid.
        clues = {"2,0,down": clue(), "10,0,across": clue()}
        assert rejected(clues, 2) == msg("10,0,across", KEY_REASON)

    def test_over_long_row_fails_rule_2(self):
        # Matches the key regex, but int() on >4300 digits raises a plain
        # ValueError (Python 3.11+); the spec answer is the rule-2 CluesError.
        key = "1" * 5000 + ",0,across"
        assert rejected({key: clue()}, 15) == msg(key, KEY_REASON)

    def test_over_long_column_fails_rule_2(self):
        key = "0," + "1" * 5000 + ",down"
        assert rejected({key: clue()}, 15) == msg(key, KEY_REASON)

    def test_every_key_checked_before_any_value(self):
        # "0,0,across" has a bad value but sorts first; the bad key still wins.
        clues = {"0,0,across": {"text": "", "answer": "x"}, "99,0,down": clue()}
        assert rejected(clues, 15) == msg("99,0,down", KEY_REASON)


class TestValidateRule3Shape:
    @pytest.mark.parametrize(
        "value",
        [
            None,
            [],
            "Flower",
            5,
            {},
            {"text": "Flower"},
            {"answer": "ROSE"},
            {"text": 5, "answer": "ROSE"},
            {"text": "Flower", "answer": None},
            {"text": None, "answer": "ROSE"},
            {"text": ["Flower"], "answer": "ROSE"},
        ],
    )
    def test_bad_value_rejected_with_exact_message(self, value):
        assert rejected({"0,0,across": value}) == msg("0,0,across", SHAPE_REASON)

    def test_shape_checked_before_text_rules(self):
        # Text is not a string and answer is bad too: rule 3 wins over rule 6.
        value = {"text": 5, "answer": "x"}
        assert rejected({"0,0,across": value}) == msg("0,0,across", SHAPE_REASON)


class TestValidateRule4Whitespace:
    @pytest.mark.parametrize(
        "ws",
        [
            "\u0009",
            "\u000a",
            "\u000b",
            "\u000c",
            "\u000d",
            " ",
            "\u0085",
            "\u00a0",
            "\u1680",
            "\u2000",
            "\u2005",
            "\u200a",
            "\u2028",
            "\u2029",
            "\u202f",
            "\u205f",
            "\u3000",
        ],
    )
    @pytest.mark.parametrize("where", ["leading", "trailing"])
    def test_every_white_space_character_rejected(self, ws, where):
        text = ws + "Flower" if where == "leading" else "Flower" + ws
        assert rejected({"0,0,across": clue(text)}) == msg("0,0,across", WHITESPACE_REASON)

    def test_leading_no_break_space_rejected(self):
        assert rejected({"0,0,across": clue("\u00a0Flower")}) == msg("0,0,across", WHITESPACE_REASON)

    def test_leading_next_line_rejected(self):
        # U+0085 is in the spec set; JS String.prototype.trim keeps it.
        assert rejected({"0,0,across": clue("\u0085Flower")}) == msg("0,0,across", WHITESPACE_REASON)

    @pytest.mark.parametrize("ch", ["\u001c", "\u001d", "\u001e", "\u001f", "\ufeff", "\u200b"])
    def test_non_white_space_edges_accepted(self, ch):
        # str.strip() would strip U+001C-U+001F; the spec set does not include them.
        # U+FEFF and U+200B are not White_Space either.
        assert validate_clues({"0,0,across": clue(ch + "Flower" + ch)}, 15) is None

    def test_interior_whitespace_accepted(self):
        assert validate_clues({"0,0,across": clue("Red\u00a0or white\tflower")}, 15) is None

    def test_whitespace_only_text_fails_rule_4_before_rule_5(self):
        assert rejected({"0,0,across": clue(" ")}) == msg("0,0,across", WHITESPACE_REASON)


class TestValidateRule5Length:
    def test_empty_text_rejected(self):
        assert rejected({"0,0,across": clue("")}) == msg("0,0,across", LENGTH_REASON)

    def test_one_character_accepted(self):
        assert validate_clues({"0,0,across": clue("x")}, 15) is None

    def test_200_code_points_accepted(self):
        assert validate_clues({"0,0,across": clue("a" * 200)}, 15) is None

    def test_201_code_points_rejected(self):
        assert rejected({"0,0,across": clue("a" * 201)}) == msg("0,0,across", LENGTH_REASON)

    def test_200_emoji_accepted_counting_each_as_one(self):
        # 200 code points, but 400 UTF-16 units and 800 UTF-8 bytes.
        assert validate_clues({"0,0,across": clue("\U0001f600" * 200)}, 15) is None

    def test_201_emoji_rejected(self):
        assert rejected({"0,0,across": clue("\U0001f600" * 201)}) == msg("0,0,across", LENGTH_REASON)

    def test_emoji_at_the_boundary_counts_once(self):
        assert validate_clues({"0,0,across": clue("a" * 199 + "\U0001f600")}, 15) is None
        assert rejected({"0,0,across": clue("a" * 200 + "\U0001f600")}) == msg("0,0,across", LENGTH_REASON)


class TestValidateRule6Answer:
    @pytest.mark.parametrize(
        "answer",
        ["", "R", "?", "ro", "Ro", "R0", "RO SE", "RO\n", "ROSE ", "RO-SE", "R\u00c9", "\uff32\uff2f"],
    )
    def test_bad_answer_rejected_with_exact_message(self, answer):
        assert rejected({"0,0,across": clue(answer=answer)}) == msg("0,0,across", ANSWER_REASON)

    @pytest.mark.parametrize("answer", ["RO", "ROSE", "RO?E", "??", "?" * 21])
    def test_good_answer_accepted(self, answer):
        assert validate_clues({"0,0,across": clue(answer=answer)}, 15) is None


class TestValidateOrdering:
    def test_value_errors_reported_in_key_order(self):
        # Key order reaches "2,0,down" first; code-point order would reach
        # "10,0,across" first. Both keys are valid for size 15, both values bad.
        clues = {
            "10,0,across": clue(text=""),
            "2,0,down": clue(answer="x"),
        }
        assert rejected(clues) == msg("2,0,down", ANSWER_REASON)

    def test_key_order_puts_across_before_down(self):
        clues = {"1,1,down": clue(text=""), "1,1,across": clue(answer="x")}
        assert rejected(clues) == msg("1,1,across", ANSWER_REASON)

    def test_key_order_is_by_row_then_column(self):
        clues = {"1,10,across": clue(text=""), "1,2,across": clue(answer="x")}
        assert rejected(clues) == msg("1,2,across", ANSWER_REASON)
        clues = {"1,1,across": clue(text=""), "0,14,down": clue(answer="x")}
        assert rejected(clues) == msg("0,14,down", ANSWER_REASON)

    def test_rules_3_to_6_run_key_by_key_not_rule_by_rule(self):
        # The first key has only a rule-6 fault; the second has a rule-3 fault.
        # Rule-by-rule checking would report the second key.
        clues = {"0,0,across": clue(answer="x"), "0,1,across": None}
        assert rejected(clues) == msg("0,0,across", ANSWER_REASON)

    def test_rules_apply_in_order_within_one_value(self):
        # Whitespace fault and answer fault together: rule 4 first.
        assert rejected({"0,0,across": clue(text=" x", answer="x")}) == msg("0,0,across", WHITESPACE_REASON)
        # Too long and answer fault together: rule 5 first.
        assert rejected({"0,0,across": clue(text="a" * 201, answer="x")}) == msg("0,0,across", LENGTH_REASON)

    def test_orphan_key_is_valid(self):
        # No validation against the grid's entries; orphans show as orphaned.
        assert validate_clues({"14,14,across": clue()}, 15) is None


class TestClueKeySort:
    def test_returns_row_col_direction_tuple(self):
        assert clue_key_sort("0,0,across") == (0, 0, 0)
        assert clue_key_sort("0,0,down") == (0, 0, 1)
        assert clue_key_sort("3,12,down") == (3, 12, 1)
        assert clue_key_sort("14,2,across") == (14, 2, 0)

    def test_numeric_not_lexicographic(self):
        assert clue_key_sort("2,0,down") < clue_key_sort("10,0,across")
        assert sorted(["10,0,across", "2,0,down"], key=clue_key_sort) == ["2,0,down", "10,0,across"]

    def test_across_before_down(self):
        assert clue_key_sort("4,4,across") < clue_key_sort("4,4,down")

    def test_row_then_column_then_direction(self):
        keys = ["1,0,across", "0,10,down", "0,2,down", "0,2,across", "0,0,down"]
        assert sorted(keys, key=clue_key_sort) == [
            "0,0,down",
            "0,2,across",
            "0,2,down",
            "0,10,down",
            "1,0,across",
        ]


class TestClueStatusFixture:
    def test_fixture_holds_the_fourteen_cases(self):
        cases = load_cases()
        assert len(cases) == 14
        assert [c["key"] for c in cases] == ["0,0,across"] * 7 + ["0,0,down"] * 7
        assert [c["status"] for c in cases[:7]] == [c["status"] for c in cases[7:]]

    @pytest.mark.parametrize(
        "case",
        load_cases(),
        ids=lambda c: "{}-{}-{}".format(c["key"], c["answer"], c["status"]),
    )
    def test_status_matches_the_fixture(self, case):
        grid = grid_from_rows(case["grid"])
        clues = {case["key"]: clue(answer=case["answer"])}
        validate_clues(clues, grid.size)
        assert clue_statuses(grid, clues) == {case["key"]: case["status"]}

    @pytest.mark.parametrize("direction", ["across", "down"])
    def test_two_letter_entry_is_visible(self, direction):
        # Mutation (spec 6.3): get_word_slots() at its default min_length=3 hides
        # the 2-letter RO entry, so this row would be `orphaned` instead of `ok`.
        key = "0,0," + direction
        case = next(c for c in load_cases() if c["key"] == key and c["answer"] == "RO")
        status = clue_statuses(grid_from_rows(case["grid"]), {key: clue(answer="RO")})
        assert status[key] == "ok"


class TestClueStatuses:
    ROSE_ROWS = [list("ROSE"), list("...."), list("...."), list("....")]

    def test_empty_map_gives_empty_statuses(self):
        assert clue_statuses(grid_from_rows(self.ROSE_ROWS), {}) == {}

    def test_every_key_gets_a_status(self):
        clues = {
            "0,0,across": clue(answer="ROSE"),
            "0,0,down": clue(answer="RAAA"),
            "3,3,across": clue(answer="AB"),
        }
        statuses = clue_statuses(grid_from_rows(self.ROSE_ROWS), clues)
        assert statuses == {"0,0,across": "ok", "0,0,down": "stale", "3,3,across": "orphaned"}

    def test_empty_square_is_read_as_question_mark(self):
        # The grid pattern is "RO.E"; reading `.` as `?` makes it match "RO?E".
        rows = [list("RO.E"), list("...."), list("...."), list("....")]
        clues = {"0,0,across": clue(answer="RO?E")}
        assert clue_statuses(grid_from_rows(rows), clues) == {"0,0,across": "ok"}

    def test_entry_must_start_at_the_key(self):
        # (0,1) is inside the run that starts at (0,0): no entry starts there.
        clues = {"0,1,across": clue(answer="OSE")}
        assert clue_statuses(grid_from_rows(self.ROSE_ROWS), clues) == {"0,1,across": "orphaned"}

    def test_change_of_length_is_stale(self):
        clues = {"0,0,across": clue(answer="ROS")}
        assert clue_statuses(grid_from_rows(self.ROSE_ROWS), clues) == {"0,0,across": "stale"}

    def test_one_cell_run_starts_no_entry(self):
        rows = [list("R#SE"), list("...."), list("...."), list("....")]
        clues = {"0,0,across": clue(answer="ROSE")}
        assert clue_statuses(grid_from_rows(rows), clues) == {"0,0,across": "orphaned"}


class TestGetWordSlotsPatternForm:
    def test_empty_square_is_a_dot_in_the_pattern(self):
        # Spec 8: the docstring says 'C?T' but get_word_slots joins raw cell
        # values, so an empty square is `.`. Clue status relies on that form.
        grid = grid_from_rows([list("RO.E"), list("...."), list("...."), list("....")])
        slots = grid.get_word_slots(min_length=2)
        across = next(s for s in slots if s["direction"] == "across" and s["row"] == 0 and s["col"] == 0)
        assert across["pattern"] == "RO.E"
        assert across["pattern"][2] == "."
        assert "?" not in across["pattern"]


class TestCarryClues:
    def test_copies_the_clue_map(self):
        source = {"clues": {"0,0,across": clue()}, "size": 15}
        target = {"grid": [["."]]}
        assert carry_clues(source, target) == {"grid": [["."]], "clues": {"0,0,across": clue()}}

    def test_returns_the_target_object(self):
        target = {}
        assert carry_clues({"clues": {}}, target) is target

    def test_empty_map_is_carried(self):
        target = carry_clues({"clues": {}}, {"grid": []})
        assert "clues" in target
        assert target["clues"] == {}

    def test_absent_key_leaves_target_without_it(self):
        target = carry_clues({"size": 15}, {"grid": []})
        assert "clues" not in target
        assert target == {"grid": []}

    def test_any_value_is_carried_unvalidated(self):
        target = carry_clues({"clues": None}, {})
        assert "clues" in target
        assert target["clues"] is None

    def test_other_target_keys_are_kept(self):
        target = carry_clues({"clues": {"0,0,down": clue()}}, {"size": 11, "numbering": {}})
        assert target["size"] == 11
        assert target["numbering"] == {}

    def test_source_is_not_modified(self):
        source = {"clues": {"0,0,across": clue()}, "size": 15}
        carry_clues(source, {})
        assert source == {"clues": {"0,0,across": clue()}, "size": 15}
