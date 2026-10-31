"""Clue map: validation, key order, derived status and carry.

Implements Decision 2 (clue-authoring spec 0.1.4, section 1): a clue belongs
to its entry's start cell and direction and records the letters it was
written for, so changed letters make it stale and a destroyed entry makes it
orphaned.

Implements Decision 6 (clue-authoring spec 0.1.4, section 1): the CLI owns the
clue model, its validation and the authoritative status. The rules are spec
sections 3.1, 3.2 and 3.4.
"""

import re
from typing import Any, Dict, Tuple

from .grid import Grid

# Spec 3.1: the Unicode White_Space set, written out. str.strip() is not used:
# it also strips U+001C-U+001F, which this set excludes.
_WHITESPACE = frozenset(
    [chr(c) for c in range(0x09, 0x0E)]
    + [" ", "\u0085", " ", " "]
    + [chr(c) for c in range(0x2000, 0x200B)]
    + [" ", " ", " ", " ", "　"]
)

# [0-9], not \d: \d matches other Unicode digits. fullmatch, not `$`: `$`
# matches before a trailing newline.
_KEY_RE = re.compile(r"(0|[1-9][0-9]*),(0|[1-9][0-9]*),(across|down)")
_ANSWER_RE = re.compile(r"[A-Z?]{2,}")

_MAX_TEXT = 200


class CluesError(ValueError):
    """A clue map failed validation; str(e) is the exact spec 3.4 message."""


def _invalid(key: str, reason: str) -> CluesError:
    return CluesError('Invalid clue "{}": {}.'.format(key, reason))


def _below(digits: str, size: int) -> bool:
    """True if the canonical decimal string `digits` is < size.

    Compares lengths first so int() never sees an over-long string: Python 3.11+
    (and 3.9.14+/3.10.7+) raise ValueError past 4300 digits, older 3.9 does not.
    """
    return size > 0 and len(digits) <= len(str(size)) and int(digits) < size


def clue_key_sort(key: str) -> Tuple[int, int, int]:
    """Sort key for a valid clue key: row, column, then across before down."""
    row, col, direction = key.split(",")
    return (int(row), int(col), 0 if direction == "across" else 1)


def validate_clues(clues: object, size: int) -> None:
    """Validate a clue map against spec 3.4; raise CluesError on the first failure."""
    if not isinstance(clues, dict):
        raise CluesError("Invalid clues: must be an object.")

    key_reason = 'key must be "row,col,across" or "row,col,down" inside the grid'
    for key in sorted(clues):
        match = _KEY_RE.fullmatch(key) if isinstance(key, str) else None
        if match is None or not (_below(match.group(1), size) and _below(match.group(2), size)):
            raise _invalid(str(key), key_reason)

    for key in sorted(clues, key=clue_key_sort):
        value = clues[key]
        if not isinstance(value, dict) or not isinstance(value.get("text"), str) or not isinstance(value.get("answer"), str):
            raise _invalid(key, "must have text and answer strings")
        text = value["text"]
        if text and (text[0] in _WHITESPACE or text[-1] in _WHITESPACE):
            raise _invalid(key, "text must not start or end with whitespace")
        if not 1 <= len(text) <= _MAX_TEXT:
            raise _invalid(key, "text must be 1 to 200 characters")
        if _ANSWER_RE.fullmatch(value["answer"]) is None:
            raise _invalid(key, "answer must be 2 or more of A-Z or ?")


def clue_statuses(grid: Grid, clues: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """Status (ok, stale, orphaned) of each clue key; `clues` must be validated.

    Entries come from get_word_slots(min_length=2) with `.` read as `?`
    (spec 3.2). get_clue_positions is not used: it hides 2-letter entries.
    """
    entries = {(s["row"], s["col"], s["direction"]): s["pattern"].replace(".", "?") for s in grid.get_word_slots(min_length=2)}
    statuses = {}
    for key, clue in clues.items():
        row, col, direction = key.split(",")
        pattern = entries.get((int(row), int(col), direction))
        if pattern is None:
            statuses[key] = "orphaned"
        elif pattern != clue["answer"]:
            statuses[key] = "stale"
        else:
            statuses[key] = "ok"
    return statuses


def carry_clues(source: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
    """Copy `clues` from source to target when source has the key; return target."""
    if "clues" in source:
        target["clues"] = source["clues"]
    return target
