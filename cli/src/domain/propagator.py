"""
Propagator: dataclasses, initial masks, and arc consistency to a fixed point.

DomainState holds a SlotModel alongside two views derived from one `fixed`
tuple: word_masks, one eligibility mask per slot (None for a fixed slot),
and cell_letters, an alphabet bitmask per cell combining the locked-in fixed
letters with the per-position AND of every open slot's own mask.
initial_state (spec 2026-09-09-c3-propagator, section 7 steps 1-2's first
half) builds both from scratch -- no cross-slot arc-consistency pass and no
not-equals removal.

refine/_refine/propagate (section 7 steps 3, 4, 6, 7) revise those masks to
a fixed point over model.crossings: refine runs from an existing
DomainState with the natural queue, _refine is the private seam that takes
an explicit arc sequence so a confluence test can permute it (decision 13),
and propagate is initial_state followed by refine. Both not_equals phases
(step 2's fixed-word removal and step 5's singleton rule) are Task 3's --
every entry point here accepts the flag and is a no-op while it is False.

Revision and Result are the propagation-record shapes refine/_refine/
propagate build so every C3 task shares one vocabulary.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Sequence, Union

import numpy as np
from src.domain.letter_bitset import LetterBitsetIndex
from src.domain.slot_model import SlotModel, pattern

# int is a constant policy; a callable is applied as min_score(length). Written in
# the typing.Union form rather than `int | Callable[...]`: this is a module-level
# alias, a runtime expression that `from __future__ import annotations` does not
# defer, and the `|` form raises TypeError on Python 3.9.
MinScore = Union[int, Callable[[int], int]]


@dataclass
class DomainState:
    model: SlotModel
    word_masks: list[np.ndarray | None]  # parallel to slots; None for a fixed slot
    cell_letters: np.ndarray  # uint64, len size*size; alphabet bitmask per cell
    fixed: tuple[str, ...]


@dataclass(frozen=True)
class Revision:
    source_crossing: int  # crossing index, or -1 for the not-equals rule
    source_slot: int  # the slot whose domain caused the removal
    slot: int  # the slot revised
    removed: np.ndarray  # uint64 mask of the word ids removed


@dataclass(frozen=True)
class Result:
    state: DomainState
    wiped: tuple[int, ...]  # open slots with an empty mask at the fixed point, by id
    revisions: tuple[Revision, ...]


def initial_state(
    model: SlotModel,
    index: LetterBitsetIndex,
    fixed: tuple[str, ...],
    min_score: MinScore = 0,
) -> DomainState:
    """
    Build the unpropagated DomainState for (model, fixed).

    A slot is open iff pattern(model, slot.id, fixed) contains a wildcard,
    fixed otherwise (spec section 3). Every open slot gets
    index.mask(pattern, policy(slot.length)), where policy is min_score
    itself when it is an int and min_score(slot.length) when callable --
    LetterBitsetIndex.mask only accepts a plain int, so a callable is
    resolved here, once per open slot, before the call. Every fixed slot
    gets None.

    cell_letters starts from fixed alone: 0 for a black or unslotted cell
    regardless of what fixed holds there (decision 15 -- a defect cell
    carries no legal letters), the single alphabet bit of fixed[cell] (or 0
    if that letter is outside index.alphabet) for a fixed, slotted cell,
    and the full alphabet mask for a slotted, unfilled one. It is then
    narrowed, per open slot and cell position, by the letters that slot's
    own mask actually admits there -- so an open slot with an empty mask
    zeroes every one of its cells, and this narrowing already reflects in
    the unpropagated masks above, before any cross-slot propagation runs.
    """
    word_masks: list[np.ndarray | None] = []
    for slot in model.slots:
        slot_pattern = pattern(model, slot.id, fixed)
        if "?" not in slot_pattern:
            word_masks.append(None)
            continue
        policy = min_score(slot.length) if callable(min_score) else min_score
        word_masks.append(index.mask(slot_pattern, policy))

    cell_letters = _cell_letters(model, index, fixed, word_masks)

    return DomainState(model=model, word_masks=word_masks, cell_letters=cell_letters, fixed=fixed)


def _cell_letters(
    model: SlotModel,
    index: LetterBitsetIndex,
    fixed: tuple[str, ...],
    word_masks: list[np.ndarray | None],
) -> np.ndarray:
    """
    Spec section 7 step 7's rule -- a pure function of (model, fixed,
    word_masks), so initial_state and refine's fixed point both recompute
    cell_letters through this one function rather than each carrying their
    own copy of the precedence rule.

    Precedence per cell (decision 15): a black or unslotted cell is 0
    regardless of what fixed holds there (a grid defect has no legal
    letter); otherwise a fixed cell is the single bit of its letter, or 0
    if that letter is outside index.alphabet; otherwise (a slotted, unfilled
    cell) it starts as every alphabet bit. Then for every open slot and
    position, cell_letters is ANDed down by that slot's own word_mask's
    letters_at -- which is where an empty mask (a wipeout) zeroes every one
    of its cells.
    """
    num_cells = model.size * model.size
    full_mask = (1 << len(index.alphabet)) - 1
    defect_cells = set(model.blacks) | set(model.unslotted)

    cell_letters = np.zeros(num_cells, dtype=np.uint64)
    for cell in range(num_cells):
        if cell in defect_cells:
            continue  # stays 0 -- unslotted/black wins over any fixed letter there
        letter = fixed[cell]
        if letter:
            bit = index.letter_index.get(letter)
            cell_letters[cell] = np.uint64(1 << bit) if bit is not None else np.uint64(0)
        else:
            cell_letters[cell] = np.uint64(full_mask)

    for slot, word_mask in zip(model.slots, word_masks):
        if word_mask is None:
            continue
        for position, cell in enumerate(slot.cells):
            cell_letters[cell] &= np.uint64(index.letters_at(slot.length, position, word_mask))

    return cell_letters


def _open_arc_queue(model: SlotModel, word_masks: list[np.ndarray | None]) -> list[int]:
    """The natural queue (decision 13): indices into model.crossings, in that
    order, of every crossing whose two slots are both open."""
    return [
        idx
        for idx, crossing in enumerate(model.crossings)
        if word_masks[crossing.across_id] is not None and word_masks[crossing.down_id] is not None
    ]


def _crossings_by_slot(model: SlotModel) -> dict[int, list[tuple[int, int]]]:
    """slot id -> [(crossing index, the slot on the other side of it), ...],
    each slot's list in model.crossings order."""
    by_slot: dict[int, list[tuple[int, int]]] = {slot.id: [] for slot in model.slots}
    for idx, crossing in enumerate(model.crossings):
        by_slot[crossing.across_id].append((idx, crossing.down_id))
        by_slot[crossing.down_id].append((idx, crossing.across_id))
    return by_slot


def _enqueue_other_crossings(
    slot_crossings: dict[int, list[tuple[int, int]]],
    masks: list[np.ndarray | None],
    slot_id: int,
    exclude_crossing: int,
    pending: "deque[int]",
) -> None:
    """Enqueue every crossing of slot_id other than the one just processed,
    skipping any whose other slot is fixed -- that arc was never in the open-
    open set to begin with (spec section 7 step 4)."""
    for crossing_idx, other_slot in slot_crossings[slot_id]:
        if crossing_idx == exclude_crossing:
            continue
        if masks[other_slot] is not None:
            pending.append(crossing_idx)


def refine(state: DomainState, index: LetterBitsetIndex, min_score: MinScore = 0, not_equals: bool = True) -> Result:
    """
    Run the arc-consistency fixed point (spec section 7 steps 3-7) from an
    existing DomainState, rather than from (model, fixed) the way propagate
    does.

    The initial queue is the natural one -- model.crossings' own order,
    filtered to the crossings whose two slots are both open (spec section 7
    step 3) -- built here and handed to the private _refine seam (decision
    13), which takes it as an explicit argument so a confluence test can
    permute it while refine itself always passes this one order.

    Does not mutate state or any array it holds; see _refine.
    """
    queue = _open_arc_queue(state.model, state.word_masks)
    return _refine(state, index, min_score, not_equals, queue)


def _refine(
    state: DomainState,
    index: LetterBitsetIndex,
    min_score: MinScore,
    not_equals: bool,
    queue: Sequence[int],
) -> Result:
    """
    The fixed-point loop (spec section 7 steps 4, 6, 7), taking its initial
    arc sequence as an explicit argument (decision 13) so refine's natural
    order and a test's permuted order run through the identical algorithm.

    Per popped crossing (cell, a, i, b, j): allowed is the intersection of
    what each side's mask admits at the shared cell; each side is narrowed
    to allowed via index.restrict, and a side that changed gets a Revision,
    its new mask stored, and every other crossing of that slot (whose other
    side is open) re-enqueued. An empty mask is not a stop -- its letters_at
    is 0, so restrict on the far side empties in turn, and that cascade is
    exactly the point (spec section 7 step 4).

    Does not mutate state or any array it holds: masks starts as a shallow
    copy of state.word_masks (untouched slots keep their original array
    reference, which this function never writes into), and every touched
    slot's replacement comes from index.restrict, which always returns a
    new array rather than an in-place edit. wiped and cell_letters are
    computed fresh at the end from the local masks list.

    not_equals is accepted so Task 3 can extend this signature's behaviour
    without changing its shape; step 5's singleton-clearing phase is not
    implemented here -- not_equals=False is the only value this task's
    contract requires, and it is already a no-op by simply never running
    that phase.
    """
    model = state.model
    masks: list[np.ndarray | None] = list(state.word_masks)
    slot_crossings = _crossings_by_slot(model)

    pending: "deque[int]" = deque(queue)
    revisions: list[Revision] = []

    while pending:
        crossing_idx = pending.popleft()
        crossing = model.crossings[crossing_idx]
        a, i, b, j = crossing.across_id, crossing.across_pos, crossing.down_id, crossing.down_pos
        length_a = model.slots[a].length
        length_b = model.slots[b].length
        mask_a = masks[a]
        mask_b = masks[b]

        allowed = index.letters_at(length_a, i, mask_a) & index.letters_at(length_b, j, mask_b)
        new_a = index.restrict(length_a, i, allowed, mask_a)
        new_b = index.restrict(length_b, j, allowed, mask_b)

        if not np.array_equal(new_a, mask_a):
            revisions.append(Revision(source_crossing=crossing_idx, source_slot=b, slot=a, removed=mask_a ^ new_a))
            masks[a] = new_a
            _enqueue_other_crossings(slot_crossings, masks, a, crossing_idx, pending)

        if not np.array_equal(new_b, mask_b):
            revisions.append(Revision(source_crossing=crossing_idx, source_slot=a, slot=b, removed=mask_b ^ new_b))
            masks[b] = new_b
            _enqueue_other_crossings(slot_crossings, masks, b, crossing_idx, pending)

    wiped = tuple(slot.id for slot in model.slots if masks[slot.id] is not None and index.count(masks[slot.id]) == 0)
    cell_letters = _cell_letters(model, index, state.fixed, masks)
    new_state = DomainState(model=model, word_masks=masks, cell_letters=cell_letters, fixed=state.fixed)
    return Result(state=new_state, wiped=wiped, revisions=tuple(revisions))


def propagate(
    model: SlotModel,
    index: LetterBitsetIndex,
    fixed: tuple[str, ...],
    min_score: MinScore = 0,
    not_equals: bool = True,
) -> Result:
    """
    Build the unpropagated DomainState for (model, fixed) and run it to the
    arc-consistency fixed point: initial_state, then refine.

    Step 2's not-equals half -- removing a fixed slot's on-list word from
    every same-length open mask, between initial_state and refine -- is
    Task 3's; it is a no-op while not_equals=False, which is this task's
    entire scope.
    """
    state = initial_state(model, index, fixed, min_score)
    return refine(state, index, min_score=min_score, not_equals=not_equals)
