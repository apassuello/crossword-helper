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
and propagate is initial_state followed by refine. not_equals gates two
rules: step 2's fixed-word removal (propagate only, between initial_state
and refine) and step 5's singleton rule (a phase inside _refine, run only
once the arc queue is empty -- never interleaved into step 4's loop, per
the spec's [NOTE] on why that would break confluence). Both are no-ops
when not_equals is False.

Revision and Result are the propagation-record shapes refine/_refine/
propagate build so every C3 task shares one vocabulary.

crossing_counts (section 7's last primitive) reads an existing DomainState
-- it never calls refine or propagate -- and returns one count per open
crossing of a candidate word at a slot, in model.crossings order. Decision
6 is binding: this is a quantity, not a ranking, so nothing here sorts or
aggregates the tuple it returns.
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


@dataclass(eq=False)
class DomainState:
    model: SlotModel
    word_masks: list[np.ndarray | None]  # parallel to slots; None for a fixed slot
    cell_letters: np.ndarray  # uint64, len size*size; alphabet bitmask per cell
    fixed: tuple[str, ...]

    def __eq__(self, other: object) -> bool:
        """
        Decision 16 (spec 0.1.8, section 7): the dataclass-generated __eq__
        raises ValueError the moment it reaches a field whose array holds
        more than one element -- cell_letters always does (one entry per
        cell), and a wide enough word list makes word_masks do too. Equal
        iff model and fixed compare ==, cell_letters compares
        np.array_equal, and word_masks compares elementwise, pairwise both
        None or np.array_equal. The None case is checked explicitly rather
        than folded into a bare np.array_equal(a, b): that form only
        answers correctly for None by NumPy's incidental coercion of None
        to a 0-d object array, not by contract.

        Defining __eq__ in the class body is also what nulls __hash__ here:
        Python itself sets a class's __hash__ to None whenever __eq__ is
        defined without also defining __hash__, independent of dataclass
        machinery.
        """
        if not isinstance(other, DomainState):
            return NotImplemented
        if self.model != other.model:
            return False
        if self.fixed != other.fixed:
            return False
        if len(self.word_masks) != len(other.word_masks):
            return False
        for mine, theirs in zip(self.word_masks, other.word_masks):
            if (mine is None) != (theirs is None):
                return False
            if mine is not None and not np.array_equal(mine, theirs):
                return False
        return np.array_equal(self.cell_letters, other.cell_letters)


@dataclass(frozen=True, eq=False)
class Revision:
    source_crossing: int  # crossing index, or -1 for the not-equals rule
    source_slot: int  # the slot whose domain caused the removal
    slot: int  # the slot revised
    removed: np.ndarray  # uint64 mask of the word ids removed

    def __eq__(self, other: object) -> bool:
        """
        Decision 16 (spec 0.1.8, section 7): mirrors DomainState.__eq__ for
        the same reason -- the dataclass-generated tuple __eq__ raises
        ValueError once source_crossing, source_slot and slot all compare
        equal and it reaches `removed`, if that mask spans more than one
        uint64 chunk. Equal iff source_crossing, source_slot and slot all
        compare ==, and removed compares np.array_equal.

        Defining __eq__ in the class body is also what nulls __hash__ here
        -- see DomainState.__eq__'s docstring.
        """
        if not isinstance(other, Revision):
            return NotImplemented
        if self.source_crossing != other.source_crossing:
            return False
        if self.source_slot != other.source_slot:
            return False
        if self.slot != other.slot:
            return False
        return np.array_equal(self.removed, other.removed)


@dataclass(frozen=True, eq=False)
class Result:
    state: DomainState
    wiped: tuple[int, ...]  # open slots with an empty mask at the fixed point, by id
    revisions: tuple[Revision, ...]

    def __eq__(self, other: object) -> bool:
        """
        Decision 16 (spec 0.1.8, section 7): mirrors DomainState.__eq__.
        Equal iff state, wiped and revisions all compare == -- state via
        DomainState.__eq__ (decision 16 again, one level down) and
        revisions via plain tuple comparison, which delegates each element
        to Revision.__eq__ above.

        Defining __eq__ in the class body is also what nulls __hash__ here
        -- see DomainState.__eq__'s docstring.
        """
        if not isinstance(other, Result):
            return NotImplemented
        if self.state != other.state:
            return False
        if self.wiped != other.wiped:
            return False
        return self.revisions == other.revisions


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

    min_score (decision 17, spec 0.1.8) is applied here, before anything
    else: every slot whose mask is not None is ANDed with
    index.mask(pattern(state.model, slot.id, state.fixed), policy), policy
    resolved per slot exactly as initial_state resolves it -- min_score
    itself when min_score is an int, min_score(slot.length) when it is
    callable. A fixed slot (mask None) is left alone. The narrowing records
    no Revision: it runs before the fixed-point loop that produces them,
    and Revision.source_crossing has no encoding for a score policy. It is
    idempotent when the floor is unchanged -- arc consistency and this AND
    both only narrow a mask, never widen it -- which is why propagate may
    pass the same min_score through both initial_state and refine without
    double-counting, and a slot the floor empties is reported in wiped like
    any other empty slot.

    The initial queue is the natural one -- model.crossings' own order,
    filtered to the crossings whose two slots are both open (spec section 7
    step 3) -- built from the narrowed masks and handed to the private
    _refine seam (decision 13), which takes it as an explicit argument so a
    confluence test can permute it while refine itself always passes this
    one order.

    not_equals is forwarded to _refine unchanged; it gates step 5's
    singleton-clearing phase there. Step 2's fixed-word removal is not run
    here -- it belongs to propagate, between initial_state and this call.

    Does not mutate state or any array it holds: the narrowing above builds
    a fresh word_masks list (state.word_masks itself is only read, never
    written into), and every open slot's entry in it is a new array from
    index.mask's own AND, never an in-place edit. See _refine for the rest
    of the fixed-point loop's own non-mutation.
    """
    model = state.model
    narrowed_masks: list[np.ndarray | None] = []
    for slot in model.slots:
        mask = state.word_masks[slot.id]
        if mask is None:
            narrowed_masks.append(None)
            continue
        policy = min_score(slot.length) if callable(min_score) else min_score
        narrowed_masks.append(mask & index.mask(pattern(model, slot.id, state.fixed), policy))

    # cell_letters is carried over unchanged rather than recomputed: this
    # DomainState is a transient argument to _refine alone, which never
    # reads state.cell_letters (it recomputes cell_letters fresh from its
    # own local masks list at the end, via _cell_letters) and never returns
    # this object -- so recomputing it here would be pure waste.
    narrowed_state = DomainState(model=model, word_masks=narrowed_masks, cell_letters=state.cell_letters, fixed=state.fixed)

    queue = _open_arc_queue(model, narrowed_masks)
    return _refine(narrowed_state, index, min_score, not_equals, queue)


def _refine(
    state: DomainState,
    index: LetterBitsetIndex,
    min_score: MinScore,
    not_equals: bool,
    queue: Sequence[int],
) -> Result:
    """
    The fixed-point loop (spec section 7 steps 4, 5, 6, 7), taking its
    initial arc sequence as an explicit argument (decision 13) so refine's
    natural order and a test's permuted order run through the identical
    algorithm.

    min_score is accepted here only for signature stability with refine
    (decision 13) -- this function's body never reads it. The caller must
    already have narrowed every open slot's mask by the resolved policy,
    exactly as refine does before building queue (decision 17); _refine
    itself applies no floor of its own.

    Per popped crossing (cell, a, i, b, j): allowed is the intersection of
    what each side's mask admits at the shared cell; each side is narrowed
    to allowed via index.restrict, and a side that changed gets a Revision,
    its new mask stored, and every other crossing of that slot (whose other
    side is open) re-enqueued. An empty mask is not a stop -- its letters_at
    is 0, so restrict on the far side empties in turn, and that cascade is
    exactly the point (spec section 7 step 4).

    Step 5 (not_equals) runs only once this inner queue is fully drained,
    never interleaved into it -- interleaving the singleton rule into step
    4 is non-confluent (spec section 7's [NOTE]): a slot on its way to
    empty may or may not pass through a transient singleton depending on
    queue order, and firing the rule on that transient state makes the
    result depend on order. Collecting singletons only at a genuine
    arc-consistent fixed point removes that transient case, so this
    function alternates two whole phases -- drain the arc queue, then run
    the singleton phase once -- rather than checking for singletons inside
    the loop above. If the phase changes anything, every crossing of every
    slot it touched is re-enqueued and the outer loop returns to draining
    the arc queue (spec section 7 step 5's own "return to step 4"); the
    outer loop stops only once a drain leaves the queue empty and the
    following phase removes nothing (step 6's fixed point, extended by
    not_equals).

    Does not mutate state or any array it holds: masks starts as a shallow
    copy of state.word_masks (untouched slots keep their original array
    reference, which this function never writes into), and every touched
    slot's replacement -- from index.restrict or from the not_equals
    helpers -- is always a new array, never an in-place edit. wiped and
    cell_letters are computed fresh at the end from the local masks list.
    """
    model = state.model
    masks: list[np.ndarray | None] = list(state.word_masks)
    slot_crossings = _crossings_by_slot(model)

    pending: "deque[int]" = deque(queue)
    revisions: list[Revision] = []

    while True:
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

        if not not_equals:
            break

        phase_revisions, changed_slots = _singleton_not_equals_phase(model, index, masks)
        if not phase_revisions:
            break
        revisions.extend(phase_revisions)
        for slot_id in changed_slots:
            _enqueue_other_crossings(slot_crossings, masks, slot_id, -1, pending)  # -1: no real crossing, so exclude nothing

    wiped = tuple(slot.id for slot in model.slots if masks[slot.id] is not None and index.count(masks[slot.id]) == 0)
    cell_letters = _cell_letters(model, index, state.fixed, masks)
    new_state = DomainState(model=model, word_masks=masks, cell_letters=cell_letters, fixed=state.fixed)
    return Result(state=new_state, wiped=wiped, revisions=tuple(revisions))


def _singleton_not_equals_phase(
    model: SlotModel,
    index: LetterBitsetIndex,
    masks: list[np.ndarray | None],
) -> tuple[tuple[Revision, ...], set[int]]:
    """
    Spec section 7 step 5, run once against an arc-consistent set of masks.

    Collects every open slot whose current mask is a singleton -- a
    property of the state handed in, read once up front so a slot this
    call itself empties out cannot retroactively join or leave that set.
    Each collected singleton then clears its one word id from every other
    open slot of the same length: a target slot loses that bit only if it
    was actually present (a real removal, mirroring step 4's own
    if-changed guard), which is what lets two same-length slots holding
    the same singleton clear each other and both end up empty -- neither
    is excluded from being a source merely because it is also a target.

    Mutates masks in place (the caller's local list) but never a mask
    array itself: every replacement is a fresh array from a bitwise op.
    Returns the Revisions produced and the set of slot ids actually
    changed, for the caller to re-enqueue.
    """
    singletons = [
        (slot.id, masks[slot.id]) for slot in model.slots if masks[slot.id] is not None and index.count(masks[slot.id]) == 1
    ]

    revisions: list[Revision] = []
    changed: set[int] = set()
    for source_id, singleton_mask in singletons:
        source_length = model.slots[source_id].length
        for slot in model.slots:
            target_id = slot.id
            if target_id == source_id or slot.length != source_length:
                continue
            target_mask = masks[target_id]
            if target_mask is None:
                continue
            removed = target_mask & singleton_mask
            if not np.any(removed):
                continue
            masks[target_id] = target_mask & ~singleton_mask
            revisions.append(Revision(source_crossing=-1, source_slot=source_id, slot=target_id, removed=removed))
            changed.add(target_id)

    return tuple(revisions), changed


def propagate(
    model: SlotModel,
    index: LetterBitsetIndex,
    fixed: tuple[str, ...],
    min_score: MinScore = 0,
    not_equals: bool = True,
) -> Result:
    """
    Build the unpropagated DomainState for (model, fixed) and run it to the
    arc-consistency fixed point: initial_state, then (if not_equals) step
    2's fixed-word removal, then refine.

    Step 2 belongs here rather than in initial_state or refine: it needs
    the fixed slots' own text, which initial_state already classified as
    fixed by giving them a None mask, but it runs exactly once, before arc
    consistency's queue is even built -- not on every call refine's own
    fixed point might see. A fixed slot whose text is off the index (mask
    count 0) contributes no removal; a same-length open slot that never
    actually held the removed word contributes no Revision either,
    mirroring step 4's own if-changed guard.
    """
    state = initial_state(model, index, fixed, min_score)
    if not_equals:
        masks, step_2_revisions = _fixed_word_removals(model, index, fixed, state.word_masks)
        if step_2_revisions:
            cell_letters = _cell_letters(model, index, fixed, masks)
            state = DomainState(model=model, word_masks=masks, cell_letters=cell_letters, fixed=fixed)
    else:
        step_2_revisions = ()

    result = refine(state, index, min_score=min_score, not_equals=not_equals)
    if step_2_revisions:
        result = Result(state=result.state, wiped=result.wiped, revisions=step_2_revisions + result.revisions)
    return result


def _fixed_word_removals(
    model: SlotModel,
    index: LetterBitsetIndex,
    fixed: tuple[str, ...],
    word_masks: list[np.ndarray | None],
) -> tuple[list[np.ndarray | None], tuple[Revision, ...]]:
    """
    Spec section 7 step 2's not-equals half: every fixed slot whose text is
    in the index removes that word id from every same-length open mask.

    A fixed slot's text is pattern(model, slot.id, fixed) with no wildcard
    left in it, by definition of fixed (spec section 3) -- resolving it
    through index.mask(text, 0) at a score floor of 0 answers "is this
    word in the index at all", independent of whatever min_score policy
    the caller's own masks were built with: the word is already committed
    as this slot's answer, so its presence in the dictionary is a fact
    about the word list, not something a score floor should gate. An
    off-list text (count 0) contributes no removal.

    Returns a fresh word_masks list (word_masks itself is only shallow-
    copied, never written into) and the Revisions produced, one per
    (fixed slot, target slot) pair that actually lost a bit.
    """
    masks = list(word_masks)
    revisions: list[Revision] = []

    for slot in model.slots:
        if masks[slot.id] is not None:
            continue  # open -- not a not-equals source
        text = pattern(model, slot.id, fixed)
        word_mask = index.mask(text, 0)
        if index.count(word_mask) == 0:
            continue  # off-list; nothing to remove

        for target in model.slots:
            if target.id == slot.id or target.length != slot.length:
                continue
            target_mask = masks[target.id]
            if target_mask is None:
                continue
            removed = target_mask & word_mask
            if not np.any(removed):
                continue
            masks[target.id] = target_mask & ~word_mask
            revisions.append(Revision(source_crossing=-1, source_slot=slot.id, slot=target.id, removed=removed))

    return masks, tuple(revisions)


def crossing_counts(state: DomainState, index: LetterBitsetIndex, slot_id: int, word: str) -> tuple[int, ...]:
    """
    Spec section 7's last primitive: for a candidate word at slot_id, one
    count per crossing of slot_id whose other slot is open, walked in
    model.crossings order (section 6 pins that order by .cell).

    Each count is index.count(index.restrict(L_other, pos_other,
    1 << letter_index[word[pos_self]], mask_other)) -- how many words the
    other slot's own current mask would still admit at the shared cell if
    word were placed there. A crossing into a fixed slot is omitted, not
    zero-padded, so the returned tuple can be shorter than slot_id's own
    crossing count. A letter outside index.alphabet has no letter_index
    entry to look up, so that crossing contributes 0 rather than raising.

    Reads state alone -- never calls refine or propagate, and never
    mutates state or anything it holds.

    Decision 6: this is a quantity, not a ranking. No sort, no
    aggregation -- the tuple comes back in crossing order.

    Raises:
        ValueError: if len(word) != model.slots[slot_id].length, checked
            before any crossing is walked.
    """
    model = state.model
    length = model.slots[slot_id].length
    if len(word) != length:
        raise ValueError(f"word {word!r} has length {len(word)}; slot {slot_id} has length {length}")

    counts: list[int] = []
    for crossing in model.crossings:
        if crossing.across_id == slot_id:
            self_pos, other_id, other_pos = crossing.across_pos, crossing.down_id, crossing.down_pos
        elif crossing.down_id == slot_id:
            self_pos, other_id, other_pos = crossing.down_pos, crossing.across_id, crossing.across_pos
        else:
            continue

        mask_other = state.word_masks[other_id]
        if mask_other is None:
            continue  # crossing into a fixed slot: omitted, not zero-padded

        letter_bit = index.letter_index.get(word[self_pos])
        if letter_bit is None:
            counts.append(0)  # out-of-alphabet letter: contributes 0, never raises
            continue

        length_other = model.slots[other_id].length
        restricted = index.restrict(length_other, other_pos, 1 << letter_bit, mask_other)
        counts.append(index.count(restricted))

    return tuple(counts)
