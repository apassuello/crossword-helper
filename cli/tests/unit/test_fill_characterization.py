"""Characterization of `fill` on pre-placed UNLOCKED letters and beam on a locked off-list word.

novice-readiness spec 0.2.4 §2.3 and §2.1 (Task 2.11). Observations only: every test pins
what the CLI did when observed (2026-10-23, HEAD 49df7dc); none asserts desired behaviour.
No product code is exercised except through the real subprocess:

    python -m cli.src.cli fill <grid> -w <list> --allow-nonstandard --json-output \
        --timeout <10|30> --algorithm <alg> -o <out>

Run: pytest cli/tests/unit/test_fill_characterization.py -v
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# L6: a 3x3 word square, rows CAT/ORE/WED, columns COW/ARE/TED.
L6 = "CAT;50\nORE;50\nWED;50\nCOW;50\nARE;50\nTED;50\n"
# L5: completes CAB with OLE/DEE across and COD/ALE/BEE down.
L5 = "COD;50\nALE;50\nBEE;50\nOLE;50\nDEE;50\n"


def _fill(tmp_path, grid, words, algorithm, timeout, locked=None):
    wl = tmp_path / "words.txt"
    wl.write_text(words)
    body = {"size": 3, "grid": grid}
    if locked is not None:
        body["locked"] = locked
    gp = tmp_path / "grid.json"
    gp.write_text(json.dumps(body))
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.src.cli",
            "fill",
            str(gp),
            "-w",
            str(wl),
            "--allow-nonstandard",
            "--json-output",
            "--timeout",
            str(timeout),
            "--algorithm",
            algorithm,
            "-o",
            str(tmp_path / "out.json"),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-500:]
    return json.loads(proc.stdout)["grid"]


def _seeded(letter):
    return [[letter, ".", "."], [".", ".", "."], [".", ".", "."]]


def _timeout(algorithm):
    return 30 if algorithm == "hybrid" else 10


@pytest.mark.parametrize("algorithm", ["regex", "trie", "beam", "repair", "hybrid"])
def test_ch1_unlocked_letter_agreeing_with_a_fill_is_kept(tmp_path, algorithm):
    """CH1, observed 2026-10-23: `C` at (0,0), `"locked": []`, list L6 -> (0,0) stays `C`.

    Command: fill <G33 with C at (0,0), locked []> -w <L6> --allow-nonstandard
    --json-output --timeout 10 (30 for hybrid) --algorithm <alg>. The rest of the grid is
    not pinned: beam and hybrid fill the transpose (COW/ARE/TED) and hybrid varies between
    runs between the square and its transpose; (0,0) is `C` in both.
    """
    grid = _fill(tmp_path, _seeded("C"), L6, algorithm, _timeout(algorithm), locked=[])
    assert grid[0][0] == "C"


@pytest.mark.parametrize("algorithm", ["regex", "trie", "beam"])
def test_ch2_unlocked_unfillable_letter_is_kept_and_nothing_else_is_filled(tmp_path, algorithm):
    """CH2, observed 2026-10-23: `Q` at (0,0), `"locked": []`, list L6 -> grid returned unchanged.

    Same command as CH1 with `Q`. regex, trie and beam keep `Q` and leave every other cell `.`.
    """
    grid = _fill(tmp_path, _seeded("Q"), L6, algorithm, _timeout(algorithm), locked=[])
    assert grid == _seeded("Q")


@pytest.mark.parametrize("algorithm", ["repair", "hybrid"])
def test_ch2_unlocked_unfillable_letter_is_replaced_by_repair_and_hybrid(tmp_path, algorithm):
    """CH2, observed 2026-10-23: `Q` at (0,0), `"locked": []`, list L6.

    repair and hybrid CHANGE the unlocked letter: (0,0) ends `C` and the grid is the full
    square CAT/ORE/WED. Same command as CH1 with `Q`. This is the STOP finding of
    spec §2.3 `[?]`.
    """
    grid = _fill(tmp_path, _seeded("Q"), L6, algorithm, _timeout(algorithm), locked=[])
    assert grid == [["C", "A", "T"], ["O", "R", "E"], ["W", "E", "D"]]


def test_ch2b_unlocked_letter_with_a_word_through_it_is_rewritten_by_beam(tmp_path):
    """CH2b, observed 2026-10-24: `O` at (0,0), `"locked": []`, list L6, beam.

    `O` fits ORE but no complete fill of L6 starts with it, so beam rewrites (0,0): row 0
    came back `CAT` and `COW` in two runs, so only "not `O`" and "complete" are pinned.
    This is what CH2's `Q` could not show: beam keeps an unlocked letter only when no word
    passes through that cell. Spec 0.2.6 §2.3 `[NOTE]`.
    """
    grid = _fill(tmp_path, _seeded("O"), L6, "beam", _timeout("beam"), locked=[])
    assert grid[0][0] != "O"
    assert all(cell != "." for row in grid for cell in row)


@pytest.mark.parametrize("algorithm", ["regex", "trie"])
def test_ch2b_control_regex_and_trie_keep_the_same_unlocked_letter(tmp_path, algorithm):
    """CH2b control: the same row under regex/trie keeps `O` and fills nothing, so the
    beam row above discriminates the algorithms rather than passing on any outcome."""
    grid = _fill(tmp_path, _seeded("O"), L6, algorithm, _timeout(algorithm), locked=[])
    assert grid == _seeded("O")


def test_ch3_beam_fills_around_a_locked_off_list_word(tmp_path):
    """CH3, observed 2026-10-23: beam, row 0 `CAB` locked (key absent), list L5.

    Command: fill <G33 row 0 C A B> -w <L5> --allow-nonstandard --json-output --timeout 10
    --algorithm beam. Beam does not reject the placements crossing `CAB`: rows 1-2 are
    OLE/DEE and the downs are COD/ALE/BEE.
    """
    grid = _fill(
        tmp_path,
        [["C", "A", "B"], [".", ".", "."], [".", ".", "."]],
        L5,
        "beam",
        10,
    )
    assert grid == [["C", "A", "B"], ["O", "L", "E"], ["D", "E", "E"]]
