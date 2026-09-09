"""
Propagator state: dataclasses and the unpropagated-mask half of arc setup.

DomainState holds a SlotModel alongside two views derived from one `fixed`
tuple: word_masks, one eligibility mask per slot (None for a fixed slot),
and cell_letters, an alphabet bitmask per cell combining the locked-in fixed
letters with the per-position AND of every open slot's own mask.
initial_state (spec 2026-09-09-c3-propagator, section 7 steps 1-2's first
half) builds both from scratch -- no cross-slot arc-consistency pass and no
not-equals removal; both belong to propagate (Tasks 2 and 3).

Revision and Result are the propagation-record shapes propagate and
not_equals build so every C3 task shares one vocabulary; this module only
defines them -- constructing one is Tasks 2/3's job, not initial_state's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Union

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

    return DomainState(model=model, word_masks=word_masks, cell_letters=cell_letters, fixed=fixed)
