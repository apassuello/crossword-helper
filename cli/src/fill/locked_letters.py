"""
Which input letters ``fill`` locks, and the cell lists that report them.

novice-readiness spec 0.2.4 §2.1 (C12): ``Grid.from_dict`` writes ``Grid.cells``
directly and applies only an explicit ``"locked"`` key, so the CLI decides the
rest here, once, on a fresh run. On ``--resume`` only ``changed_locked_cells`` and
``stuck_cells`` run, with an empty lock set; ``apply_lock_mode`` and ``preflight`` never do.
``preflight`` is also skipped under ``--adaptive`` (spec 0.2.7 §2.1).
"""

from typing import Dict, Iterable, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from ..core.grid import Grid
from ..domain.fillability import assess
from ..domain.letter_bitset import LetterBitsetIndex
from ..domain.slot_model import SlotModel, fixed_from_grid, pattern
from .word_list import WordList


def cell_list(cells: Iterable[Tuple[int, int]]) -> List[List[int]]:
    """Unique ``[row, col]`` pairs, zero-based, sorted row-major (spec §2.1, C11)."""
    return [[int(r), int(c)] for r, c in sorted({(int(r), int(c)) for r, c in cells})]


def apply_lock_mode(grid: Grid, grid_data: Mapping, lock_filled: bool) -> None:
    """
    Set ``grid.locked_cells`` for a fresh run (spec §2.1, C12).

    Call immediately after ``Grid.from_dict``, which has already validated any
    ``"locked"`` key (so an invalid list fails even under ``--no-lock-filled``).

    - ``lock_filled`` and ``"locked"`` in ``grid_data``: keep ``from_dict``'s set.
    - ``lock_filled`` and no key: every cell holding a letter.
    - not ``lock_filled``: no cell, with or without the key.
    """
    if not lock_filled:
        grid.locked_cells = set()
    elif "locked" not in grid_data:
        grid.locked_cells = {
            (row, col)
            for row in range(grid.size)
            for col in range(grid.size)
            if not grid.is_black(row, col) and not grid.is_empty(row, col)
        }


def input_lock_letters(grid: Grid) -> Dict[Tuple[int, int], str]:
    """``{(row, col): letter}`` for every cell in ``grid.locked_cells``."""
    return {(row, col): grid.get_cell(row, col) for row, col in grid.locked_cells}


POSTCONDITION_MESSAGE = "Autofill changed a locked letter; nothing was written."


def changed_locked_cells(grid: Grid, expected: Mapping[Tuple[int, int], str]) -> List[List[int]]:
    """
    Cell list of every ``expected`` cell that no longer holds its letter in ``grid``.

    novice-readiness spec 0.2.4 §2.1 (D3): the end-to-end postcondition. An empty,
    black or differently lettered cell all count as changed.
    """
    return cell_list(
        (row, col) for (row, col), letter in expected.items() if grid.is_black(row, col) or grid.get_cell(row, col) != letter
    )


OFF_LIST_WARNING_PREFIX = "Typed words not in the selected word lists: "


class PreflightResult(NamedTuple):
    """What pre-flight found; ``reason`` is ``None`` when the run may proceed."""

    reason: Optional[str]  # None, "no_word_fits" or "no_word_of_length"
    blocked_cells: List[List[int]]
    blocked_slots: List[Dict[str, object]]  # {"row", "col", "direction", "length", "pattern"}
    off_list_cells: List[List[int]]
    off_list_words: List[str]  # slot-model order
    index: LetterBitsetIndex


def candidate_index(word_list: WordList, extra_words: Iterable[str] = ()) -> LetterBitsetIndex:
    """
    The index over ``word_list`` plus ``extra_words`` (the ``--theme-entries`` words,
    spec 0.2.7 §2.1); ``word_list`` itself is never mutated.

    Shared by ``preflight`` and by ``--adaptive`` runs, which skip pre-flight but
    still need an index for ``stuck_cells`` check (a).
    """
    extras = list(extra_words)
    if extras:
        word_list = WordList([(w.text, w.score) for w in word_list.words])
        word_list.add_words(extras)
    return LetterBitsetIndex.from_word_list(word_list)


def preflight(grid: Grid, word_list: WordList, extra_words: Iterable[str] = ()) -> PreflightResult:
    """
    Pre-flight for a fresh, non-adaptive ``fill`` run; never mutates ``grid``
    or ``word_list``.

    novice-readiness spec 0.2.7 §2.1: ``fill`` skips this under ``--resume`` and
    ``--adaptive``. ``extra_words`` are the ``--theme-entries`` words: candidate
    words for this check only, for any slot, not only the one they are keyed to.
    They count for dead-slot detection and for case 2. The index is built from a
    copy of the list plus them; the solver's list is untouched.

    novice-readiness spec 0.2.4 §2.1 (C1, C4, M2, B2): only locked letters
    constrain the fill, so the unlocked ones are cleared on a clone first.

    - dead slot: its pattern has a ``?`` and no word of the lists matches it
      (``min_score=0`` passed explicitly; ``count_matches`` defaults to 30).
      ``report.wiped_slots`` is never used for red cells (C1).
    - length block (``PD-2-PREC``, option (b)): a dead slot whose length has
      no word at all; it goes to B2 whether or not it holds a locked letter.
    - case 1: a dead slot that is not a length block contains a locked cell.
    - B2: dead slots exist but none of that kind holds a locked cell.
    - case 2: every cell of every typed (fixed) word that is not in the lists.
    """
    model = SlotModel.from_grid(grid)
    index = candidate_index(word_list, extra_words)
    cleared = grid.clone()
    cleared.clear_unlocked()
    fixed = fixed_from_grid(cleared)
    report = assess(model, index, fixed, min_score=0)

    size = model.size
    locked = {(int(r), int(c)) for r, c in grid.locked_cells}

    dead = []  # (slot, pattern, is_length_block), slot-model order
    for slot in model.slots:
        slot_pattern = pattern(model, slot.id, fixed)
        if "?" in slot_pattern and index.count_matches(slot_pattern, min_score=0) == 0:
            dead.append((slot, slot_pattern, index.count_matches("?" * slot.length, min_score=0) == 0))

    blocked_slots: List[Dict[str, object]] = [
        {"row": slot.row, "col": slot.col, "direction": slot.direction, "length": slot.length, "pattern": slot_pattern}
        for slot, slot_pattern, _ in dead
    ]
    case_1_cells = [
        (cell // size, cell % size)
        for slot, _, is_length_block in dead
        if not is_length_block
        for cell in slot.cells
        if (cell // size, cell % size) in locked
    ]

    reason: Optional[str] = None
    if case_1_cells:
        reason = "no_word_fits"
    elif dead:
        reason = "no_word_of_length"

    off_list_slots = [model.slots[slot_id] for slot_id in report.off_list_fixed]
    return PreflightResult(
        reason=reason,
        blocked_cells=cell_list(case_1_cells) if reason == "no_word_fits" else [],
        blocked_slots=blocked_slots,
        off_list_cells=cell_list((cell // size, cell % size) for slot in off_list_slots for cell in slot.cells),
        off_list_words=["".join(fixed[cell] for cell in slot.cells) for slot in off_list_slots],
        index=index,
    )


def off_list_warning(words: Sequence[str]) -> str:
    """The case-2 warning text (spec §2.1): the prefix and the words, comma-separated."""
    return OFF_LIST_WARNING_PREFIX + ", ".join(words)


def blocked_text_lines(result: PreflightResult) -> List[str]:
    """
    Text-mode lines of a blocked result (spec §2.1; ``PD-2-OUT``).

    ``no_word_fits``: one line per blocked slot. ``no_word_of_length``: one line
    per distinct slot length, ascending. Not blocked: no lines.
    """
    if result.reason == "no_word_fits":
        return [
            f"Blocked: no word fits {s['pattern']} at {s['row']},{s['col']} {s['direction']}" for s in result.blocked_slots
        ]
    if result.reason == "no_word_of_length":
        lengths = sorted({int(s["length"]) for s in result.blocked_slots})  # type: ignore[call-overload]
        return [f"Blocked: the selected word lists have no words of length {n}" for n in lengths]
    return []


def stuck_cells(
    final_grid: Grid,
    locked: Iterable[Tuple[int, int]],
    problematic_slots: Sequence[Mapping],
    index: Optional[LetterBitsetIndex],
    min_score: int,
) -> List[List[int]]:
    """
    Locked cells the solver could not fill around (novice-readiness spec 0.2.4
    §2.1, C11/C2): the cell list of ``locked`` cells lying in

    (a) a slot of ``final_grid`` with an empty cell whose pattern matches no word
        of ``index`` at ``min_score``, or
    (b) a slot named by a ``problematic_slots`` entry with ``"reason":
        "invalid_word"`` (``IterativeRepair._build_result``'s shape; entries
        without a ``"reason"``, as beam and classic return, contribute nothing).

    ``index`` is ``None`` only on ``--resume``, where the lock set is empty: with no
    locked cell the result is ``[]`` and ``index`` is never touched. A fresh
    ``--adaptive`` run skips pre-flight but passes ``candidate_index(...)``.
    """
    locked_set = {(int(r), int(c)) for r, c in locked}
    if not locked_set:
        return []

    stuck = set()

    model = SlotModel.from_grid(final_grid)
    fixed = fixed_from_grid(final_grid)
    size = model.size
    for slot in model.slots:
        slot_pattern = pattern(model, slot.id, fixed)
        if "?" not in slot_pattern:
            continue
        if index is not None and index.count_matches(slot_pattern, min_score=min_score) == 0:
            stuck.update((cell // size, cell % size) for cell in slot.cells if (cell // size, cell % size) in locked_set)

    for entry in problematic_slots:
        if entry.get("reason") != "invalid_word":
            continue
        row, col, direction = entry["slot"]
        step = (0, 1) if direction == "across" else (1, 0)
        for offset in range(len(entry["pattern"])):
            cell = (row + step[0] * offset, col + step[1] * offset)
            if cell in locked_set:
                stuck.add(cell)

    return cell_list(stuck)
