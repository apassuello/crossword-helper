"""
Slot geometry over a crossword grid: dataclasses, construction, cell ownership.

SlotModel is a flat, index-based read of a grid's white-cell geometry: which
runs of white cells (of at least min_length) exist, in what order, and which
slot (if any) owns each cell in each direction. Cell indices are
row * size + col throughout -- no (row, col) tuples in any stored field --
so the structure carries only ints, strings and tuples and can be ported to
Rust+WASM later (spec 2026-09-08-c2-slot-model, "Flat and index-based").

Slot order, and therefore Slot.id, follows Grid.enumerate_white_runs' walk
(all across runs in row-major order, then all down runs in column-major
order) filtered to length >= min_length the way Grid.get_word_slots filters
it -- so a slot built here and looked up by id agrees with the grid's own
oracle at every min_length. crossings is always () in this module: Task 2
populates it. fixed_from_grid/pattern (Task 3) and to_dict/from_dict
(Task 4) are later additions to this same file, not built here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

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

        return cls(
            size=size,
            blacks=black_cells,
            slots=tuple(slots),
            crossings=(),
            cell_across=tuple(cell_across),
            cell_down=tuple(cell_down),
            unslotted=unslotted,
        )

    def slot_key(self, slot_id: int) -> tuple[int, int, str]:
        """(row, col, direction) for slot_id -- the key shape Autofill.slot_id_map uses."""
        slot = self.slots[slot_id]
        return (slot.row, slot.col, slot.direction)
