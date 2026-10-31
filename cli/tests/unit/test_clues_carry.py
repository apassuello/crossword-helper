"""
Tests that CLI grid file writes carry ``clues`` (clue-authoring spec 0.1.4,
section 3.5 "Grid JSON file, CLI" bullets; section 6.1 "Round trip").

Grid JSON is a CLI <-> web-app contract and ``fill`` writes back to its own
input file in human mode, so a write that drops ``clues`` destroys the user's
clues in place. This module covers the three file writers that are not pause
states: the ``fill`` result write, ``new`` and ``import-nyt``. Pause states and
``resume`` are covered by
``cli/tests/integration/test_clues_pause_resume.py``.

Every command runs as a subprocess, the way ``run_cli`` in
``test_pause_resume_regressions.py`` does, because the contract is about files
the real CLI writes. ``clues`` is compared by equality with the value written
into the input; a map with two keys, one of them orphaned on the filled grid
(no entry of a 3x3 starts at (1,1)), and no status is asserted.
"""

import json
import subprocess
import sys
from pathlib import Path

from cli.tests.unit.test_nyt_parser import _make_nyt_3x3

REPO_ROOT = Path(__file__).resolve().parents[3]
WORDLIST = REPO_ROOT / "data" / "wordlists" / "comprehensive.txt"

CLUES = {
    "0,0,across": {"text": "Feline pet", "answer": "???"},
    "1,1,down": {"text": "Orphaned on any filled 3x3", "answer": "XY"},
}


def run_cli(args, timeout=120):
    """Run a CLI command; return the CompletedProcess."""
    return subprocess.run(
        [sys.executable, "-m", "cli.src.cli", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=timeout,
    )


def write_blank_3x3(path, **extra):
    """A blank 3x3 grid file that `fill -a trie` completes in about a second."""
    doc = {"size": 3, "grid": [["."] * 3 for _ in range(3)]}
    doc.update(extra)
    path.write_text(json.dumps(doc))
    return path


def fill_args(grid_file, *extra):
    return ["fill", str(grid_file), "-w", str(WORDLIST), "-a", "trie", "-t", "60", "--allow-nonstandard", *extra]


def assert_filled(data):
    """The file is the fill's result write, not the untouched input."""
    assert all(cell != "." for row in data["grid"] for cell in row), data["grid"]


# --- fill: result write ------------------------------------------------------


def test_fill_human_mode_keeps_clues_in_place(tmp_path):
    # Spec 6.3 mutation: "fill's result write drops clues" -> this test fails.
    grid_file = write_blank_3x3(tmp_path / "grid.json", clues=CLUES)

    proc = run_cli(fill_args(grid_file))

    assert proc.returncode == 0, proc.stderr[-800:]
    data = json.loads(grid_file.read_text())
    assert_filled(data)
    assert data.get("clues") == CLUES


def test_fill_output_option_writes_the_input_clues(tmp_path):
    grid_file = write_blank_3x3(tmp_path / "grid.json", clues=CLUES)
    out_file = tmp_path / "out.json"

    proc = run_cli(fill_args(grid_file, "-o", str(out_file)))

    assert proc.returncode == 0, proc.stderr[-800:]
    data = json.loads(out_file.read_text())
    assert_filled(data)
    assert data.get("clues") == CLUES


def test_fill_json_output_with_output_option_writes_the_input_clues(tmp_path):
    grid_file = write_blank_3x3(tmp_path / "grid.json", clues=CLUES)
    out_file = tmp_path / "out.json"

    proc = run_cli(fill_args(grid_file, "--json-output", "-o", str(out_file)))

    assert proc.returncode == 0, proc.stderr[-800:]
    data = json.loads(out_file.read_text())
    assert_filled(data)
    assert data.get("clues") == CLUES


def test_fill_json_output_without_output_option_leaves_the_input_untouched(tmp_path):
    # Spec 3.5: with --json-output, fill writes a file only when -o is given.
    grid_file = write_blank_3x3(tmp_path / "grid.json", clues=CLUES)
    before = grid_file.read_text()

    proc = run_cli(fill_args(grid_file, "--json-output"))

    assert proc.returncode == 0, proc.stderr[-800:]
    assert json.loads(proc.stdout.strip().splitlines()[-1])["success"] is True
    assert grid_file.read_text() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["grid.json"]


def test_fill_input_without_clues_writes_no_clues_key(tmp_path):
    grid_file = write_blank_3x3(tmp_path / "grid.json")
    out_file = tmp_path / "out.json"

    proc = run_cli(fill_args(grid_file, "-o", str(out_file)))

    assert proc.returncode == 0, proc.stderr[-800:]
    data = json.loads(out_file.read_text())
    assert_filled(data)
    assert "clues" not in data


def test_fill_human_mode_input_without_clues_writes_no_clues_key(tmp_path):
    grid_file = write_blank_3x3(tmp_path / "grid.json")

    proc = run_cli(fill_args(grid_file))

    assert proc.returncode == 0, proc.stderr[-800:]
    data = json.loads(grid_file.read_text())
    assert_filled(data)
    assert "clues" not in data


# --- new, import-nyt: write no clues -----------------------------------------


def test_new_writes_no_clues_key(tmp_path):
    out_file = tmp_path / "new.json"

    proc = run_cli(["new", "--size", "11", "-o", str(out_file)])

    assert proc.returncode == 0, proc.stderr[-800:]
    data = json.loads(out_file.read_text())
    assert data["size"] == 11
    assert "clues" not in data


def test_import_nyt_writes_no_clues_key_though_the_nyt_file_has_clues(tmp_path):
    # The NYT format has its own top-level "clues" (across/down lists of
    # strings). The imported grid file must not inherit them, empty or filled.
    nyt_file = tmp_path / "puzzle.json"
    nyt_file.write_text(json.dumps(_make_nyt_3x3()))
    assert "clues" in json.loads(nyt_file.read_text())

    for flag, name in ((None, "empty.json"), ("--filled", "filled.json")):
        out_file = tmp_path / name
        args = ["import-nyt", str(nyt_file), "-o", str(out_file)]
        if flag:
            args.append(flag)

        proc = run_cli(args)

        assert proc.returncode == 0, proc.stderr[-800:]
        data = json.loads(out_file.read_text())
        assert data["size"] == 3
        assert "clues" not in data
