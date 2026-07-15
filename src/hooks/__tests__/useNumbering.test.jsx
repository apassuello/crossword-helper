/**
 * Tests for pure numbering helpers (Task 8B).
 * localNumber/numberingMapFromGrid/structuralSigOf are PURE — no rendering,
 * no React hook here (Task 8C wires the hook on top of these exports).
 */

import { describe, it, expect } from 'vitest';
import { localNumber } from '../useNumbering';
import { allSlots } from '../useGridGeometry';
import { gridFromRows } from './gridFixtures';
import { gridWithBlackSquares } from '../../__tests__/fixtures/gridFixtures';

describe('localNumber', () => {
  it('does not mutate its input', () => {
    const grid = gridFromRows(['AB#C.', '.....', '#....', '.....', '.....']);
    const snap = JSON.stringify(grid);
    localNumber(grid);
    expect(JSON.stringify(grid)).toBe(snap);
  });

  it('numbers match the legacy algorithm on a sample 5x5', () => {
    const { numbering } = localNumber(
      gridFromRows(['.....', '.#...', '.....', '...#.', '.....'])
    );
    expect(numbering).toEqual({
      '0,0': 1,
      '0,2': 2,
      '0,3': 3,
      '0,4': 4,
      '1,2': 5,
      '2,0': 6,
      '2,1': 7,
      '3,0': 8,
      '4,0': 9,
    });
  });

  it('agrees with allSlots on every start cell', () => {
    const { numbering } = localNumber(gridWithBlackSquares);
    const { across, down } = allSlots(gridWithBlackSquares);
    for (const s of [...across, ...down]) {
      const [r, c] = s.cells[0];
      expect(numbering[`${r},${c}`]).toBeDefined();
    }
  });
});
