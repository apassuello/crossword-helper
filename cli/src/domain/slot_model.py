"""
Slot geometry over a crossword grid: dataclasses, construction, cell ownership.

SlotModel is a flat, index-based read of a grid's white-cell geometry: which
runs of white cells (of at least min_length) exist, in what order, and which
slot (if any) owns each cell in each direction. Cell indices are
row * size + col throughout -- no (row, col) tuples in any stored field --
so the structure carries only ints, strings and tuples and can be ported to
Rust+WASM later (spec 2026-09-07-domain-capabilities-design, section 2,
"Flat and index-based").

Slot order, and therefore Slot.id, follows Grid.enumerate_white_runs' walk
(all across runs in row-major order, then all down runs in column-major
order) filtered to length >= min_length the way Grid.get_word_slots filters
it -- so a slot built here and looked up by id agrees with the grid's own
oracle at every min_length. Crossings are pinned across-first: a Crossing's
across_id always names an "across" slot and down_id a "down" one, regardless
of which slot an oracle names first. fixed_from_grid and pattern (Task 3)
read a Grid's letters into a flat `fixed` tuple and render a slot's pattern
from `model` and `fixed` alone -- pattern never touches a Grid, which is
what lets one model stay constant while fixed changes underneath it.
to_dict/from_dict (Task 4) flatten a model to plain dicts/lists/ints/strings
and rebuild it from that shape, restoring every list-shaped field -- and
each nested Slot.cells -- back to a tuple so dataclass equality holds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.core.cell_types import WILDCARD
from src.core.grid import Grid


@dataclass(frozen=True)
class Slot:
    id: int
    direction: str  # "across" | "down"
    row: int
    col: int
    length: int
    cells: tuple[int, ...]  # cell indices, in reading order


@dataclass(frozen=True)
class Crossing:  # orientation pinned: across first
    cell: int
    across_id: int
    across_pos: int
    down_id: int
    down_pos: int


@dataclass(frozen=True)
class SlotModel:
    size: int
    blacks: tuple[int, ...]  # sorted cell indices
    slots: tuple[Slot, ...]  # index == Slot.id
    crossings: tuple[Crossing, ...]  # sorted by .cell
    cell_across: tuple[int, ...]  # len size*size; slot id or -1
    cell_down: tuple[int, ...]  # len size*size; slot id or -1
    unslotted: tuple[int, ...]  # sorted cell indices

    @classmethod
    def from_grid(cls, grid: Grid, min_length: int = 3) -> "SlotModel":
        """Build a SlotModel from a Grid's size and black cells only -- filled letters have no effect."""
        black_cells = (row * grid.size + col for row, col in grid.get_black_squares())
        return cls.from_blacks(grid.size, black_cells, min_length=min_length)

    @classmethod
    def from_blacks(cls, size: int, blacks: Iterable[int], min_length: int = 3) -> "SlotModel":
        """
        Build a SlotModel from a size and a set of black cell indices.

        blacks may be any Iterable[int], including a one-shot generator;
        duplicates collapse and the stored order is ascending regardless of
        input order.

        Raises:
            ValueError: if a black index falls outside range(size * size).
        """
        num_cells = size * size
        black_set = set()
        for cell in blacks:
            if not (0 <= cell < num_cells):
                raise ValueError(f"black cell index {cell} out of range for a {size}x{size} grid (0..{num_cells - 1})")
            black_set.add(cell)
        black_cells = tuple(sorted(black_set))

        is_black = [False] * num_cells
        for cell in black_cells:
            is_black[cell] = True

        slots: list[Slot] = []
        cell_across = [-1] * num_cells
        cell_down = [-1] * num_cells

        # Across runs: row-major order, matching Grid.enumerate_white_runs.
        for row in range(size):
            col = 0
            while col < size:
                if is_black[row * size + col]:
                    col += 1
                    continue
                start_col = col
                run_cells = []
                while col < size and not is_black[row * size + col]:
                    run_cells.append(row * size + col)
                    col += 1
                if len(run_cells) >= min_length:
                    slot_id = len(slots)
                    slots.append(
                        Slot(
                            id=slot_id,
                            direction="across",
                            row=row,
                            col=start_col,
                            length=len(run_cells),
                            cells=tuple(run_cells),
                        )
                    )
                    for cell in run_cells:
                        cell_across[cell] = slot_id

        # Down runs: column-major order, matching Grid.enumerate_white_runs.
        for col in range(size):
            row = 0
            while row < size:
                if is_black[row * size + col]:
                    row += 1
                    continue
                start_row = row
                run_cells = []
                while row < size and not is_black[row * size + col]:
                    run_cells.append(row * size + col)
                    row += 1
                if len(run_cells) >= min_length:
                    slot_id = len(slots)
                    slots.append(
                        Slot(
                            id=slot_id, direction="down", row=start_row, col=col, length=len(run_cells), cells=tuple(run_cells)
                        )
                    )
                    for cell in run_cells:
                        cell_down[cell] = slot_id

        unslotted = tuple(
            cell for cell in range(num_cells) if not is_black[cell] and cell_across[cell] == -1 and cell_down[cell] == -1
        )

        # Materialise crossings from the slots themselves -- not from cell_across/cell_down --
        # so the agreement assert below compares two independently derived things. An across
        # slot and a down slot share at most one cell (perpendicular runs), found here purely
        # from Slot.cells.
        across_slots = [s for s in slots if s.direction == "across"]
        down_slots_with_sets = [(s, set(s.cells)) for s in slots if s.direction == "down"]

        crossings: list[Crossing] = []
        for across in across_slots:
            for down, down_cell_set in down_slots_with_sets:
                shared = set(across.cells) & down_cell_set
                if not shared:
                    continue
                (cell,) = shared
                crossings.append(
                    Crossing(
                        cell=cell,
                        across_id=across.id,
                        across_pos=across.cells.index(cell),
                        down_id=down.id,
                        down_pos=down.cells.index(cell),
                    )
                )
        crossings.sort(key=lambda c: c.cell)

        # Agreement assert: cell_across/cell_down were built above by marking cells while
        # walking runs -- an independent route from the crossings just built by intersecting
        # slot cell sets. A discrepancy here means the two routes disagree, which should never
        # happen; per spec 6 this is an internal invariant, hence a bare assert.
        for crossing in crossings:
            assert cell_across[crossing.cell] == crossing.across_id
            assert cell_down[crossing.cell] == crossing.down_id
            assert slots[crossing.across_id].cells[crossing.across_pos] == crossing.cell
            assert slots[crossing.down_id].cells[crossing.down_pos] == crossing.cell
        mutually_owned_cells = {i for i in range(num_cells) if cell_across[i] != -1 and cell_down[i] != -1}
        assert {c.cell for c in crossings} == mutually_owned_cells

        return cls(
            size=size,
            blacks=black_cells,
            slots=tuple(slots),
            crossings=tuple(crossings),
            cell_across=tuple(cell_across),
            cell_down=tuple(cell_down),
            unslotted=unslotted,
        )

    def slot_key(self, slot_id: int) -> tuple[int, int, str]:
        """(row, col, direction) for slot_id -- the key shape Autofill.slot_id_map uses."""
        slot = self.slots[slot_id]
        return (slot.row, slot.col, slot.direction)

    def to_dict(self) -> dict:
        """
        Flatten this model into plain, JSON-native containers: dicts, lists,
        ints and strings only -- no tuples, dataclass instances or NumPy
        scalars. Keys are the dataclass field names at every level, per spec
        2026-09-07-domain-capabilities-design section 6. `direction` is carried through as
        its own string ("across"/"down"); every other value is an int.
        """
        return {
            "size": self.size,
            "blacks": list(self.blacks),
            "slots": [
                {
                    "id": slot.id,
                    "direction": slot.direction,
                    "row": slot.row,
                    "col": slot.col,
                    "length": slot.length,
                    "cells": list(slot.cells),
                }
                for slot in self.slots
            ],
            "crossings": [
                {
                    "cell": crossing.cell,
                    "across_id": crossing.across_id,
                    "across_pos": crossing.across_pos,
                    "down_id": crossing.down_id,
                    "down_pos": crossing.down_pos,
                }
                for crossing in self.crossings
            ],
            "cell_across": list(self.cell_across),
            "cell_down": list(self.cell_down),
            "unslotted": list(self.unslotted),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SlotModel":
        """
        Rebuild a SlotModel from to_dict's output (or an equivalent dict,
        such as one that has been through json.dumps/json.loads).

        Every list-shaped field is restored to a tuple, including each
        nested Slot.cells -- dataclass equality treats a list where a tuple
        belongs as unequal even when the elements match. Order is preserved
        exactly as given; this only round-trips correctly because to_dict's
        `slots` and `crossings` already carry the model's pinned order.

        Raises:
            KeyError: if d is missing any of the seven top-level keys.
        """
        return cls(
            size=d["size"],
            blacks=tuple(d["blacks"]),
            slots=tuple(
                Slot(
                    id=slot["id"],
                    direction=slot["direction"],
                    row=slot["row"],
                    col=slot["col"],
                    length=slot["length"],
                    cells=tuple(slot["cells"]),
                )
                for slot in d["slots"]
            ),
            crossings=tuple(
                Crossing(
                    cell=crossing["cell"],
                    across_id=crossing["across_id"],
                    across_pos=crossing["across_pos"],
                    down_id=crossing["down_id"],
                    down_pos=crossing["down_pos"],
                )
                for crossing in d["crossings"]
            ),
            cell_across=tuple(d["cell_across"]),
            cell_down=tuple(d["cell_down"]),
            unslotted=tuple(d["unslotted"]),
        )


def fixed_from_grid(grid: Grid) -> tuple[str, ...]:
    """
    Read a Grid's letter content into a flat, index-based tuple: the content
    half of the geometry/content split the rest of this module depends on.

    A filled white cell gives its letter whether or not it is locked --
    lock provenance is a separate concern (spec
    2026-09-07-domain-capabilities-design, section 6) and plays no part here. A black cell and an empty white cell
    both give "".
    """
    return tuple(
        grid.get_cell(row, col) if grid.has_letter(row, col) else "" for row in range(grid.size) for col in range(grid.size)
    )


def pattern(model: SlotModel, slot_id: int, fixed: tuple[str, ...]) -> str:
    """
    Render slot_id's pattern from model and fixed alone -- never touches a
    Grid, which is what lets one model stay constant while fixed changes
    underneath it.

    Each of the slot's cells, in Slot.cells order, contributes its letter
    from fixed if non-empty, else the wildcard.

    Raises:
        ValueError: if len(fixed) != model.size * model.size.
        IndexError: if slot_id is out of range for model.slots, unguarded --
            a negative slot_id therefore indexes from the end natively.
    """
    expected_length = model.size * model.size
    if len(fixed) != expected_length:
        raise ValueError(f"fixed must have length {expected_length} for a {model.size}x{model.size} grid, got {len(fixed)}")
    slot = model.slots[slot_id]
    return "".join(fixed[cell] if fixed[cell] else WILDCARD for cell in slot.cells)
