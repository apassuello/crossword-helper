/**
 * Tests for grid geometry helpers (Task 5).
 * These are PURE functions — slot extents, patterns, symmetry mirror, slot enumeration.
 * No rendering required.
 */

import { describe, it, expect } from 'vitest';
import { slotAt, allSlots, mirrorOf } from '../useGridGeometry';
import { createEmptyGrid } from '../../__tests__/fixtures/gridFixtures';
import { gridFromRows } from './gridFixtures';

describe('mirrorOf', () => {
  it('mirrors the top-left corner to the bottom-right on a 15x15', () => {
    expect(mirrorOf(0, 0, 15)).toEqual([14, 14]);
  });

  it('mirrors an interior cell through the center', () => {
    expect(mirrorOf(3, 5, 15)).toEqual([11, 9]);
  });

  it('center cell maps to itself on odd grids', () => {
    expect(mirrorOf(7, 7, 15)).toEqual([7, 7]);
  });
});

describe('slotAt — extents around black squares', () => {
  // Row 0:  A B # C .   (black at col 2)
  const grid = gridFromRows([
    'AB#C.',
    '.....',
    '#....',
    '.....',
    '.....',
  ]);

  it('across extent stops at a black square (left segment)', () => {
    const slot = slotAt(grid, 0, 0, 'across');
    expect(slot.cells).toEqual([[0, 0], [0, 1]]);
    expect(slot.length).toBe(2);
  });

  it('across extent starting mid-segment finds the same word', () => {
    const slot = slotAt(grid, 0, 1, 'across');
    expect(slot.cells).toEqual([[0, 0], [0, 1]]);
  });

  it('across extent on the right segment stops at grid edge and black', () => {
    const slot = slotAt(grid, 0, 3, 'across');
    expect(slot.cells).toEqual([[0, 3], [0, 4]]);
  });

  it('down extent stops at a black square', () => {
    // Column 0: A . # . .  -> from row 0 the down word is rows 0..1
    const slot = slotAt(grid, 0, 0, 'down');
    expect(slot.cells).toEqual([[0, 0], [1, 0]]);
    expect(slot.length).toBe(2);
  });

  it('returns an empty zero-length slot for a black cell (no throw)', () => {
    const slot = slotAt(grid, 0, 2, 'across');
    expect(slot.cells).toEqual([]);
    expect(slot.length).toBe(0);
  });
});

describe('slotAt — pattern strings', () => {
  const grid = gridFromRows([
    'C.T..',
    '.....',
    '.....',
    '.....',
    '.....',
  ]);

  it('uses ? for empty cells and uppercases letters', () => {
    // row 0 has no black squares, so the across slot spans the whole row
    const slot = slotAt(grid, 0, 0, 'across');
    expect(slot.pattern).toBe('C?T??');
  });

  it('reads the clue number from the slot start cell', () => {
    const g = createEmptyGrid(5);
    g[0][0].number = 1;
    const slot = slotAt(g, 0, 3, 'across');
    // start cell is (0,0) which carries number 1
    expect(slot.number).toBe(1);
  });
});

describe('allSlots — enumeration', () => {
  it('finds one across + one down word on an empty 5x5', () => {
    const g = createEmptyGrid(5);
    const { across, down } = allSlots(g);
    // Each row is one across word, each column one down word
    expect(across.length).toBe(5);
    expect(down.length).toBe(5);
    // First across slot starts at (0,0) and spans the row
    expect(across[0].cells[0]).toEqual([0, 0]);
    expect(across[0].length).toBe(5);
    expect(across[1].cells[0]).toEqual([1, 0]);
    // First down slot starts at (0,0)
    expect(down[0].cells[0]).toEqual([0, 0]);
    expect(down[1].cells[0]).toEqual([0, 1]);
  });

  it('excludes length-1 (isolated) runs from word slots', () => {
    // A single white cell surrounded by black is not a word.
    const grid = gridFromRows([
      '#.#',
      '.#.',
      '#.#',
    ]);
    const { across, down } = allSlots(grid);
    expect(across).toEqual([]);
    expect(down).toEqual([]);
  });
});
