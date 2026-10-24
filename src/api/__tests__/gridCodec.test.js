import { describe, it, expect } from 'vitest';
import {
  makeCell,
  makeGrid,
  toCliStrings,
  fromCliStrings,
  applyNumbering,
  normalizeCell,
  toSavedGrid,
} from '../gridCodec';

describe('gridCodec', () => {
  describe('makeCell / makeGrid', () => {
    it('makeCell returns the canonical empty cell', () => {
      expect(makeCell()).toEqual({
        letter: '',
        isBlack: false,
        isThemeLocked: false,
        number: null,
        isError: false,
        isAutofilled: false,
        isBlocked: false,
      });
    });

    it('makeGrid builds an size x size grid of fresh canonical cells', () => {
      const g = makeGrid(5);
      expect(g.length).toBe(5);
      expect(g[0].length).toBe(5);
      expect(g[2][3]).toEqual(makeCell());
      // cells are independent references
      g[0][0].letter = 'X';
      expect(g[0][1].letter).toBe('');
    });
  });

  describe('toCliStrings', () => {
    it('maps black -> "#", empty -> ".", letter uppercased', () => {
      const grid = [
        [
          { ...makeCell(), isBlack: true },
          { ...makeCell(), letter: '' },
          { ...makeCell(), letter: 'a' },
        ],
      ];
      expect(toCliStrings(grid)).toEqual([['#', '.', 'A']]);
    });
  });

  describe('fromCliStrings', () => {
    it('maps "#" -> black, "." -> empty, letters uppercased', () => {
      const grid = fromCliStrings([['#', '.', 'b']]);
      expect(grid[0][0].isBlack).toBe(true);
      expect(grid[0][1].isBlack).toBe(false);
      expect(grid[0][1].letter).toBe('');
      expect(grid[0][2].isBlack).toBe(false);
      expect(grid[0][2].letter).toBe('B');
      // produced cells are canonical
      expect(grid[0][1]).toEqual(makeCell());
    });
  });

  describe('canonical <-> CLI-strings round trip', () => {
    it('preserves letters (uppercased) and black squares', () => {
      const grid = [
        [{ ...makeCell(), isBlack: true }, { ...makeCell(), letter: 'c' }],
        [{ ...makeCell(), letter: 'A' }, { ...makeCell() }],
      ];
      const back = fromCliStrings(toCliStrings(grid));
      expect(back[0][0].isBlack).toBe(true);
      expect(back[0][1].letter).toBe('C');
      expect(back[1][0].letter).toBe('A');
      expect(back[1][1].letter).toBe('');
    });
  });

  describe('applyNumbering', () => {
    it('parses real "(r,c)" keys (with optional space), sets numbers, clears stale', () => {
      let grid = makeGrid(3);
      grid[0][0] = { ...grid[0][0], number: 99 }; // stale number
      const map = { '(0,0)': 1, '(0, 2)': 2, '(1,0)': 3 };
      const out = applyNumbering(grid, map);
      expect(out[0][0].number).toBe(1);
      expect(out[0][2].number).toBe(2);
      expect(out[1][0].number).toBe(3);
      // absent from map -> cleared to null
      expect(out[0][1].number).toBe(null);
      expect(out[2][2].number).toBe(null);
    });

    it('is immutable — input grid untouched, new grid returned', () => {
      const grid = makeGrid(2);
      grid[0][0] = { ...grid[0][0], number: 5 };
      const out = applyNumbering(grid, {});
      expect(grid[0][0].number).toBe(5);
      expect(out[0][0].number).toBe(null);
      expect(out).not.toBe(grid);
      expect(out[0]).not.toBe(grid[0]);
    });
  });

  describe('normalizeCell', () => {
    it('normalizeCell({}) deep-equals makeCell()', () => {
      expect(normalizeCell({})).toEqual(makeCell());
    });

    it('keeps supplied fields and defaults the provenance flags to false', () => {
      const out = normalizeCell({ letter: 'A', isThemeLocked: true });
      expect(out.letter).toBe('A');
      expect(out.isThemeLocked).toBe(true);
      expect(out.isAutofilled).toBe(false);
      expect(out.isBlocked).toBe(false);
    });

    it('keeps isAutofilled true but forces isBlocked false', () => {
      const out = normalizeCell({ letter: 'A', isAutofilled: true, isBlocked: true });
      expect(out.isAutofilled).toBe(true);
      expect(out.isBlocked).toBe(false);
    });

    it('treats a non-true isAutofilled ("yes") as false', () => {
      expect(normalizeCell({ letter: 'A', isAutofilled: 'yes' }).isAutofilled).toBe(false);
    });

    it('returns a new object and does not mutate the input', () => {
      const input = { letter: 'A', isBlocked: true };
      const out = normalizeCell(input);
      expect(out).not.toBe(input);
      expect(input).toEqual({ letter: 'A', isBlocked: true });
    });
  });

  describe('toSavedGrid', () => {
    it('strips isBlocked, keeps isAutofilled and other fields', () => {
      const cell = toSavedGrid([
        [{ letter: 'A', isAutofilled: true, isBlocked: true, isBlack: false }],
      ])[0][0];
      expect('isBlocked' in cell).toBe(false);
      expect(cell.isAutofilled).toBe(true);
      expect(cell.letter).toBe('A');
      expect(cell.isBlack).toBe(false);
    });

    it('defaults a missing isAutofilled to false', () => {
      expect(toSavedGrid([[{ letter: 'B' }]])[0][0].isAutofilled).toBe(false);
    });

    it('treats a non-true isAutofilled as false', () => {
      expect(toSavedGrid([[{ isAutofilled: 'yes' }]])[0][0].isAutofilled).toBe(false);
    });

    it('maps null to null', () => {
      expect(toSavedGrid(null)).toBe(null);
    });

    it('returns a new grid and does not mutate the input', () => {
      const grid = [[{ letter: 'A', isAutofilled: true, isBlocked: true }]];
      const out = toSavedGrid(grid);
      expect(out).not.toBe(grid);
      expect(out[0]).not.toBe(grid[0]);
      expect(out[0][0]).not.toBe(grid[0][0]);
      expect(grid[0][0]).toEqual({ letter: 'A', isAutofilled: true, isBlocked: true });
    });
  });
});
