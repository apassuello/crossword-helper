"""
Fillability: propagate to a fixed point and report whether it proves no fill
exists, plus what the fixed point looks like.

assess (spec 2026-09-07-domain-capabilities-design.md, section 8) is
propagate (src.domain.propagator) plus a report: it runs the merged C3
engine to its arc-consistency fixed point and reads FillabilityReport's
fields off the resulting Result/DomainState. refuted is bool(result.wiped)
-- a one-sided guarantee (True proves no fill exists under min_score; False
certifies nothing), never a graduated signal: no threshold, no penalty, no
confidence. domain_sizes mirrors word_masks positionally: -1 for a fixed
slot (word_masks[s] is None), index.count(word_masks[s]) for an open one,
read at the fixed point so a slot the floor or arc consistency empties
shows 0 like any other wiped slot. cell_letters is carried through from
result.state.cell_letters unchanged -- Qxw's assist mode is exactly this
array, decoded.

off_list_fixed (decision 19) is the one field this module computes itself
rather than reading off Result: "this fixed slot's word is not in the
index," decided by index membership alone, independent of min_score -- a
fixed on-list word scoring below the floor is still on-list. It is *not*
computed by calling propagator._fixed_word_removals or reusing its loop:
that function only runs when not_equals=True (propagate's step 2, between
initial_state and refine), so it would silently omit every off-list fixed
slot whenever a caller's propagate ran with not_equals=False -- and
assess's own contract carries no not_equals parameter to guarantee which
way that goes. off_list_fixed must be correct regardless, so this module
walks model.slots itself, mirroring _fixed_word_removals' own per-slot
predicate (pattern(model, slot.id, fixed), then index.mask(text, 0), score
floor 0 always -- never the caller's min_score) but independently, over
`fixed` alone rather than over propagate's own narrowed word_masks.

A fixed slot's text containing a letter outside index.alphabet is off-list,
not an error: index.mask "degrades to an all-zero array... never an
exception" (letter_bitset.py), so its count is 0 and it lands in
off_list_fixed like any other off-list word -- no guard is added here, and
none should be.

Not built: any graduated signal on top of refuted (analyze_constraints'
"critical" threshold and StateEvaluator's penalty ladder go past what any
source licenses), and unslotted_cells (decision 18) -- a white cell in no
entry is a grid-defect label that belongs at the rendering layer, which
holds the model; model.unslotted is already that list, so nothing here
duplicates it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .letter_bitset import LetterBitsetIndex
from .propagator import MinScore, propagate
from .slot_model import SlotModel, pattern


@dataclass(frozen=True, eq=False)  # decision 16's family rule; __eq__ below
class FillabilityReport:
    refuted: bool  # True: no fill exists under min_score. False: not refuted.
    wiped_slots: tuple[int, ...]
    domain_sizes: tuple[int, ...]  # parallel to slots; -1 for a fixed slot
    cell_letters: np.ndarray  # uint64 per cell -- what Qxw's assist mode shows
    off_list_fixed: tuple[int, ...]  # decision 19; fixed slots whose word is not in the index

    def __eq__(self, other: object) -> bool:
        """
        Decision 16 (spec section 7, applied to this struct by section 8):
        the dataclass-generated __eq__ would raise ValueError the moment it
        reached cell_letters, which always holds more than one element (one
        entry per cell). Equal iff refuted, wiped_slots, domain_sizes and
        off_list_fixed all compare == (a bool and three plain tuples, so
        ordinary equality is exact), and cell_letters compares
        np.array_equal. Mirrors Result.__eq__.

        Defining __eq__ in the class body is also what nulls __hash__ here:
        Python sets a class's __hash__ to None whenever __eq__ is defined
        without also defining __hash__, independent of dataclass machinery.
        """
        if not isinstance(other, FillabilityReport):
            return NotImplemented
        if self.refuted != other.refuted:
            return False
        if self.wiped_slots != other.wiped_slots:
            return False
        if self.domain_sizes != other.domain_sizes:
            return False
        if self.off_list_fixed != other.off_list_fixed:
            return False
        return np.array_equal(self.cell_letters, other.cell_letters)


def assess(
    model: SlotModel,
    index: LetterBitsetIndex,
    fixed: tuple[str, ...],
    min_score: MinScore = 0,
) -> FillabilityReport:
    """
    Propagate (model, index, fixed) to a fixed point and report on it.

    refuted/wiped_slots/domain_sizes/cell_letters all read off propagate's
    own Result -- refuted = bool(result.wiped), domain_sizes[s] is -1 for a
    fixed slot (word_masks[s] is None) or index.count(word_masks[s])
    otherwise, cell_letters carried through unchanged. propagate itself
    runs at its own default (not_equals=True): assess's contract carries no
    parameter to vary it. off_list_fixed is computed separately (see module
    docstring) and does not depend on that setting.
    """
    result = propagate(model, index, fixed, min_score=min_score)

    domain_sizes = tuple(-1 if mask is None else index.count(mask) for mask in result.state.word_masks)

    return FillabilityReport(
        refuted=bool(result.wiped),
        wiped_slots=result.wiped,
        domain_sizes=domain_sizes,
        cell_letters=result.state.cell_letters,
        off_list_fixed=_off_list_fixed(model, index, fixed),
    )


def _off_list_fixed(model: SlotModel, index: LetterBitsetIndex, fixed: tuple[str, ...]) -> tuple[int, ...]:
    """
    Every fixed slot whose word is not in the index (decision 19), decided
    at score floor 0 regardless of whatever min_score the caller passed to
    assess -- membership is a fact about the word list, not something a
    score floor should gate (mirrors _fixed_word_removals' own docstring
    rationale).

    A slot is fixed here by the same test initial_state uses: no '?' left
    in pattern(model, slot.id, fixed). This never reads propagate's own
    word_masks or Result -- see module docstring for why not_equals makes
    that the wrong source.

    index.mask never raises on a letter outside index.alphabet -- it
    degrades to an all-zero array, so a fixed slot whose text uses a letter
    no word in the list uses is reported here as off-list, not as an
    error.
    """
    off_list = []
    for slot in model.slots:
        text = pattern(model, slot.id, fixed)
        if "?" in text:
            continue  # open, not fixed
        if index.count(index.mask(text, 0)) == 0:
            off_list.append(slot.id)
    return tuple(off_list)
