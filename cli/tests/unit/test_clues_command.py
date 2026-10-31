"""
Tests for ``crossword clues check`` (clue-authoring spec section 3.6).

Spec section 3.6 gives the command and its replies; section 3.4 gives the
validation messages (copied literally below, never produced by calling the
validator); section 10's 0.1.4 ruling says that without ``--json-output`` the
command prints the same JSON object as with it. So every row runs in both modes
and asserts the same exit code and the same parsed JSON.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.src.cli import cli

MODES = [["--json-output"], []]
MODE_IDS = ["json-output", "no-flag"]

FIXTURE = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "clue_status_cases.json"


def _grid_doc(size=11, rows=None, **extra):
    """Grid file dict. ``rows`` maps row index to a list of cells for that row."""
    grid = [["."] * size for _ in range(size)]
    for r, cells in (rows or {}).items():
        grid[r] = list(cells)
    doc = {"size": size, "grid": grid}
    doc.update(extra)
    return doc


def _check(tmp_path, doc, mode, extra_args=()):
    path = tmp_path / "grid.json"
    path.write_text(json.dumps(doc))
    args = ["clues", "check", str(path), *extra_args, *mode]
    return CliRunner().invoke(cli, args)


def _row(word, size=11):
    return list(word) + ["."] * (size - len(word))


# --- valid clues: exit 0, one status per clue key ----------------------------


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
def test_valid_ok_stale_orphaned_each_reported_for_its_key(tmp_path, mode):
    # Row 0 holds ROSE then seven empties: the across entry at (0,0) is "ROSE???????".
    doc = _grid_doc(
        rows={0: _row("ROSE")},
        clues={
            "0,0,across": {"text": "Flower", "answer": "ROSE???????"},  # equal pattern
            "0,0,down": {"text": "Flower", "answer": "R??????????"},  # equal pattern
            "1,0,across": {"text": "Changed", "answer": "ROSE"},  # length differs
            "0,1,across": {"text": "Gone", "answer": "OSE"},  # no entry starts at (0,1) across
        },
    )
    result = _check(tmp_path, doc, mode)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "success": True,
        "statuses": {
            "0,0,across": "ok",
            "0,0,down": "ok",
            "1,0,across": "stale",
            "0,1,across": "orphaned",
        },
    }


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
def test_valid_statuses_has_exactly_one_entry_per_clue(tmp_path, mode):
    clues = {f"{r},0,across": {"text": f"Clue {r}", "answer": "?" * 11} for r in range(5)}
    result = _check(tmp_path, _grid_doc(clues=clues), mode)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert set(payload["statuses"]) == set(clues)
    assert list(payload["statuses"].values()) == ["ok"] * 5


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
def test_valid_orphan_keyed_inside_grid_is_orphaned_not_an_error(tmp_path, mode):
    # Spec 3.4: "Keys orphaned in the grid are valid; they show as orphaned."
    doc = _grid_doc(clues={"5,5,down": {"text": "Nowhere", "answer": "AB"}})
    result = _check(tmp_path, doc, mode)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "success": True,
        "statuses": {"5,5,down": "orphaned"},
    }


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
def test_valid_stale_when_cell_letter_differs(tmp_path, mode):
    doc = _grid_doc(
        rows={0: _row("RODE")},
        clues={"0,0,across": {"text": "Flower", "answer": "ROSE???????"}},
    )
    result = _check(tmp_path, doc, mode)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "success": True,
        "statuses": {"0,0,across": "stale"},
    }


# --- section 3.4 failures: exit 1, INVALID_CLUES ------------------------------

OK_CLUE = {"text": "Fine", "answer": "AB"}
KEY_REASON = 'key must be "row,col,across" or "row,col,down" inside the grid.'

INVALID_ROWS = [
    pytest.param(None, "Invalid clues: must be an object.", id="rule1-null"),
    pytest.param([], "Invalid clues: must be an object.", id="rule1-array"),
    pytest.param(
        {"1,1": OK_CLUE},
        f'Invalid clue "1,1": {KEY_REASON}',
        id="rule2-malformed-key",
    ),
    pytest.param(
        {"11,0,across": OK_CLUE},
        f'Invalid clue "11,0,across": {KEY_REASON}',
        id="rule2-row-outside-grid",
    ),
    pytest.param(
        {"01,0,across": OK_CLUE},
        f'Invalid clue "01,0,across": {KEY_REASON}',
        id="rule2-leading-zero",
    ),
    pytest.param(
        {"0,0,across": "ROSE"},
        'Invalid clue "0,0,across": must have text and answer strings.',
        id="rule3-value-not-object",
    ),
    pytest.param(
        {"0,0,across": {"text": "Flower"}},
        'Invalid clue "0,0,across": must have text and answer strings.',
        id="rule3-missing-answer",
    ),
    pytest.param(
        {"0,0,across": {"text": " Flower", "answer": "ROSE"}},
        'Invalid clue "0,0,across": text must not start or end with whitespace.',
        id="rule4-leading-space",
    ),
    pytest.param(
        {"0,0,across": {"text": "", "answer": "ROSE"}},
        'Invalid clue "0,0,across": text must be 1 to 200 characters.',
        id="rule5-empty-text",
    ),
    pytest.param(
        {"0,0,across": {"text": "x" * 201, "answer": "ROSE"}},
        'Invalid clue "0,0,across": text must be 1 to 200 characters.',
        id="rule5-201-chars",
    ),
    pytest.param(
        {"0,0,across": {"text": "Flower", "answer": "rose"}},
        'Invalid clue "0,0,across": answer must be 2 or more of A-Z or ?.',
        id="rule6-lowercase-answer",
    ),
    pytest.param(
        {"0,0,across": {"text": "Flower", "answer": "R"}},
        'Invalid clue "0,0,across": answer must be 2 or more of A-Z or ?.',
        id="rule6-one-letter-answer",
    ),
]


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
@pytest.mark.parametrize("clues, message", INVALID_ROWS)
def test_invalid_clues_exit_1_with_invalid_clues_code(tmp_path, mode, clues, message):
    result = _check(tmp_path, _grid_doc(clues=clues), mode)
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout) == {
        "success": False,
        "code": "INVALID_CLUES",
        "error": message,
    }


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
def test_invalid_clues_validated_against_grid_size_not_eleven(tmp_path, mode):
    # "5,0,across" is outside a 4x4 grid but inside an 11x11 one.
    doc = _grid_doc(size=4, clues={"5,0,across": OK_CLUE})
    result = _check(tmp_path, doc, mode, extra_args=["--allow-nonstandard"])
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout) == {
        "success": False,
        "code": "INVALID_CLUES",
        "error": f'Invalid clue "5,0,across": {KEY_REASON}',
    }


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
def test_first_failure_wins_in_key_order(tmp_path, mode):
    # Both clues are bad; rules 3-6 run key by key in key order, so "2,0,down"
    # (before "10,0,across") is the one reported.
    doc = _grid_doc(
        clues={
            "10,0,across": {"text": "Flower", "answer": "r"},
            "2,0,down": {"text": "", "answer": "AB"},
        }
    )
    result = _check(tmp_path, doc, mode)
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["error"] == ('Invalid clue "2,0,down": text must be 1 to 200 characters.')


# --- no clues key ------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
def test_no_clues_key_gives_empty_statuses(tmp_path, mode):
    result = _check(tmp_path, _grid_doc(), mode)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"success": True, "statuses": {}}


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
def test_empty_clues_object_gives_empty_statuses(tmp_path, mode):
    result = _check(tmp_path, _grid_doc(clues={}), mode)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"success": True, "statuses": {}}


# --- unloadable grid ---------------------------------------------------------


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
def test_unloadable_grid_gives_json_error_without_code(tmp_path, mode):
    # 4x4 without --allow-nonstandard: Grid.from_dict(strict_size=True) rejects it.
    doc = _grid_doc(size=4, clues={"0,0,across": OK_CLUE})
    result = _check(tmp_path, doc, mode)
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["success"] is False
    assert isinstance(payload["error"], str) and payload["error"]
    assert "code" not in payload


# --- 4x4 with --allow-nonstandard --------------------------------------------


def _fixture_cases():
    cases = json.loads(FIXTURE.read_text())["cases"]
    return [pytest.param(c, id=f"{i}-{c['status']}-{c['key']}") for i, c in enumerate(cases) if len(c["grid"]) == 4]


def test_fixture_has_four_by_four_cases_covering_every_status():
    statuses = {p.values[0]["status"] for p in _fixture_cases()}
    assert statuses == {"ok", "stale", "orphaned"}


@pytest.mark.parametrize("mode", MODES, ids=MODE_IDS)
@pytest.mark.parametrize("case", _fixture_cases())
def test_nonstandard_4x4_with_flag_returns_fixture_status(tmp_path, mode, case):
    doc = {
        "size": 4,
        "grid": case["grid"],
        "clues": {case["key"]: {"text": "A clue", "answer": case["answer"]}},
    }
    result = _check(tmp_path, doc, mode, extra_args=["--allow-nonstandard"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "success": True,
        "statuses": {case["key"]: case["status"]},
    }
