/**
 * Pure grid functions of the autofill merge (Task 5.1).
 * novice-readiness spec 0.2.6 section 2.3 (G12) and section 3.7.
 */
import { describe, it, expect } from 'vitest';
import {
  mergeGridPreserveThemeLocked,
  lockedCellsOf,
  markBlocked,
  clearBlocked,
  resultGridIsFull,
  fillsAnyCell,
} from '../useAutofillMachine';
import { makeCell } from '../../api/gridCodec';

const cell = (over = {}) => ({ ...makeCell(), ...over });
// Merge one current cell against one CLI value, 1x1.
const merge1 = (current, cli) => mergeGridPreserveThemeLocked([[current]], [[cli]])[0][0];

describe('mergeGridPreserveThemeLocked', () => {
  it('empty white, not autofilled + letter -> letter, isAutofilled true', () => {
    const cur = cell();
    const out = merge1(cur, 'A');
    expect(out.letter).toBe('A');
    expect(out.isAutofilled).toBe(true);
  });

  it('passes the CLI letter through without uppercasing', () => {
    expect(merge1(cell(), 'a').letter).toBe('a');
  });

  it('autofilled letter + new letter -> replaced, stays autofilled', () => {
    const out = merge1(cell({ letter: 'B', isAutofilled: true }), 'C');
    expect(out.letter).toBe('C');
    expect(out.isAutofilled).toBe(true);
  });

  it.each(['.', ''])('autofilled letter + %j -> cleared, isAutofilled false', (cli) => {
    const out = merge1(cell({ letter: 'B', isAutofilled: true }), cli);
    expect(out.letter).toBe('');
    expect(out.isAutofilled).toBe(false);
  });

  it.each(['E', '.', '#'])('user letter + %j -> same object', (cli) => {
    const cur = cell({ letter: 'D', isAutofilled: false });
    expect(merge1(cur, cli)).toBe(cur);
  });

  it('theme-locked letter + letter -> same object', () => {
    const cur = cell({ letter: 'F', isThemeLocked: true });
    expect(merge1(cur, 'G')).toBe(cur);
  });

  it('theme-locked empty white + letter -> same object', () => {
    const cur = cell({ isThemeLocked: true });
    expect(merge1(cur, 'G')).toBe(cur);
  });

  it('empty white + "#" -> black, letter empty, not autofilled', () => {
    const out = merge1(cell(), '#');
    expect(out.isBlack).toBe(true);
    expect(out.letter).toBe('');
    expect(out.isAutofilled).toBe(false);
  });

  it('autofilled letter + "#" -> black, letter empty, not autofilled', () => {
    const out = merge1(cell({ letter: 'B', isAutofilled: true }), '#');
    expect(out.isBlack).toBe(true);
    expect(out.letter).toBe('');
    expect(out.isAutofilled).toBe(false);
  });

  it.each(['A', '.'])('black cell + %j -> same object', (cli) => {
    const cur = cell({ isBlack: true });
    expect(merge1(cur, cli)).toBe(cur);
  });

  it('user letter with isBlocked + same letter -> same object, isBlocked kept', () => {
    const cur = cell({ letter: 'D', isBlocked: true });
    const out = merge1(cur, 'D');
    expect(out).toBe(cur);
    expect(out.isBlocked).toBe(true);
  });

  it('never changes isBlocked or isError on a written cell', () => {
    const cur = cell({ letter: 'B', isAutofilled: true, isBlocked: true, isError: true });
    const out = merge1(cur, 'C');
    expect(out.isBlocked).toBe(true);
    expect(out.isError).toBe(true);
  });

  it('is defined against the current grid: returns a new grid, input untouched', () => {
    const cur = [[cell()]];
    const out = mergeGridPreserveThemeLocked(cur, [['A']]);
    expect(out).not.toBe(cur);
    expect(cur[0][0].letter).toBe('');
  });
});

describe('lockedCellsOf', () => {
  const grid3 = () => [
    [cell({ letter: 'A' }), cell({ letter: 'B', isAutofilled: true }), cell({ isThemeLocked: true })],
    [cell({ letter: 'C', isAutofilled: true, isThemeLocked: true }), cell({ isBlack: true, letter: 'Z' }), cell()],
    [cell({ letter: 'D', isBlocked: true }), cell(), cell()],
  ];

  it('lists user letters and theme-locked letters, row-major, excluding the rest', () => {
    expect(lockedCellsOf(grid3())).toEqual([[0, 0], [1, 0], [2, 0]]);
  });

  it('is [] when every letter is autofilled and none theme-locked', () => {
    const g = [[cell({ letter: 'A', isAutofilled: true }), cell({ letter: 'B', isAutofilled: true })]];
    expect(lockedCellsOf(g)).toEqual([]);
  });
});

describe('markBlocked', () => {
  it('listed cells become new objects with isBlocked true; others keep their object', () => {
    const g = [[cell({ letter: 'A' }), cell({ letter: 'B' })], [cell(), cell()]];
    const out = markBlocked(g, [[0, 1], [1, 0]]);
    expect(out[0][1]).not.toBe(g[0][1]);
    expect(out[0][1].isBlocked).toBe(true);
    expect(out[0][1].letter).toBe('B');
    expect(out[1][0]).not.toBe(g[1][0]);
    expect(out[1][0].isBlocked).toBe(true);
    expect(out[0][0]).toBe(g[0][0]);
    expect(out[1][1]).toBe(g[1][1]);
    expect(g[0][1].isBlocked).toBe(false);
  });
});

describe('clearBlocked', () => {
  it('returns a new object for every cell with isBlocked false, other fields unchanged', () => {
    const g = [[cell({ letter: 'A', isBlocked: true }), cell({ isError: true })]];
    const out = clearBlocked(g);
    expect(out[0][0]).not.toBe(g[0][0]);
    expect(out[0][1]).not.toBe(g[0][1]);
    expect(out[0][0]).toEqual({ ...g[0][0], isBlocked: false });
    expect(out[0][1]).toEqual({ ...g[0][1], isBlocked: false });
    expect(g[0][0].isBlocked).toBe(true);
  });
});

describe('resultGridIsFull', () => {
  it('true when no cell is "." or "" ("#" counts as filled)', () => {
    expect(resultGridIsFull([['A', '#'], ['B', 'C']])).toBe(true);
  });
  it('false when a "." is present', () => {
    expect(resultGridIsFull([['A', '.'], ['B', 'C']])).toBe(false);
  });
  it('false when an empty string is present', () => {
    expect(resultGridIsFull([['A', 'B'], ['', 'C']])).toBe(false);
  });
});

describe('fillsAnyCell', () => {
  const snap = () => [[cell({ letter: 'X' }), cell()]];
  it('true when the CLI puts a letter on an empty white snapshot cell', () => {
    expect(fillsAnyCell(snap(), [['X', 'A']])).toBe(true);
  });
  it('false when CLI letters sit only on cells the snapshot already holds', () => {
    expect(fillsAnyCell(snap(), [['Y', '.']])).toBe(false);
  });
  it('false when the CLI only puts "#" on an empty cell', () => {
    expect(fillsAnyCell(snap(), [['X', '#']])).toBe(false);
  });
  it('false when the empty snapshot cell is theme-locked', () => {
    const s = [[cell({ isThemeLocked: true })]];
    expect(fillsAnyCell(s, [['A']])).toBe(false);
  });
  it('false when the empty snapshot cell is black', () => {
    const s = [[cell({ isBlack: true })]];
    expect(fillsAnyCell(s, [['A']])).toBe(false);
  });
});
