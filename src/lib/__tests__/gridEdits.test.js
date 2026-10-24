/**
 * Tests for the pure grid writers (novice-readiness spec 0.2.6 §3.7 (S5), §2.3).
 * Common rule: a written cell is a NEW object with isAutofilled:false and
 * isBlocked:false (same letter included); an unwritten cell is the input's own
 * object; inputs are never mutated; no write returns the input grid itself.
 */
import { describe, it, expect } from 'vitest';
import { makeCell } from '../../api/gridCodec';
import {
  writeLetter,
  writeToggleBlack,
  writeToggleThemeLock,
  writePatternWord,
  writeAppliedTheme,
  writeImportedGrid,
  writeCleanedGrid,
} from '../gridEdits';

const cell = (over = {}) => ({ ...makeCell(), ...over });
const mk = (size, over = {}) =>
  Array.from({ length: size }, (_, r) =>
    Array.from({ length: size }, (_, c) => cell(over[`${r},${c}`] || {}))
  );
// Freeze the grid and every cell: a mutating helper throws (ESM strict mode).
const freeze = (g) => {
  g.forEach((row) => {
    row.forEach((x) => Object.freeze(x));
    Object.freeze(row);
  });
  return Object.freeze(g);
};
const flags = (x) => ({ letter: x.letter, a: x.isAutofilled, b: x.isBlocked });

describe('writeLetter', () => {
  it('writes an uppercased letter into an empty cell', () => {
    const g = freeze(mk(3));
    const out = writeLetter(g, 0, 0, 'a');
    expect(flags(out[0][0])).toEqual({ letter: 'A', a: false, b: false });
    expect(out[0][0]).not.toBe(g[0][0]);
  });

  it('same letter on an autofilled cell still clears isAutofilled', () => {
    const g = freeze(mk(3, { '0,0': { letter: 'B', isAutofilled: true } }));
    const out = writeLetter(g, 0, 0, 'B');
    expect(flags(out[0][0])).toEqual({ letter: 'B', a: false, b: false });
    expect(out[0][0]).not.toBe(g[0][0]);
  });

  it('clears red on the edited cell only', () => {
    const g = freeze(
      mk(3, {
        '0,0': { letter: 'B', isAutofilled: true, isBlocked: true },
        '0,1': { isBlocked: true },
      })
    );
    const out = writeLetter(g, 0, 0, 'C');
    expect(flags(out[0][0])).toEqual({ letter: 'C', a: false, b: false });
    expect(out[0][1]).toBe(g[0][1]);
    expect(out[0][1].isBlocked).toBe(true);
    expect(out).not.toBe(g);
  });

  it('erasing (empty letter) is a user write too', () => {
    const g = freeze(mk(3, { '0,0': { letter: 'B', isAutofilled: true } }));
    const out = writeLetter(g, 0, 0, '');
    expect(flags(out[0][0])).toEqual({ letter: '', a: false, b: false });
  });

  it('a black cell is not written: returns the input grid', () => {
    const g = freeze(mk(3, { '0,0': { isBlack: true } }));
    expect(writeLetter(g, 0, 0, 'A')).toBe(g);
  });
});

describe('writeToggleBlack', () => {
  it('with symmetry writes the cell and its partner, both new, flags cleared', () => {
    const g5 = freeze(
      mk(5, {
        '0,1': { letter: 'A', isAutofilled: true, isBlocked: true },
        '4,3': { letter: 'B', isAutofilled: true },
      })
    );
    const out = writeToggleBlack(g5, 0, 1, true);
    for (const [r, c] of [[0, 1], [4, 3]]) {
      expect(out[r][c]).not.toBe(g5[r][c]);
      expect(out[r][c]).toMatchObject({
        isBlack: true,
        letter: '',
        isAutofilled: false,
        isBlocked: false,
      });
    }
    expect(out[2][2]).toBe(g5[2][2]);
  });

  it('without symmetry the partner keeps its object', () => {
    const g5 = freeze(mk(5, { '4,3': { letter: 'B', isAutofilled: true } }));
    const out = writeToggleBlack(g5, 0, 1, false);
    expect(out[4][3]).toBe(g5[4][3]);
    expect(out[0][1].isBlack).toBe(true);
  });

  it('un-blacking writes isBlack false, keeps the empty letter, with the partner', () => {
    const g5 = freeze(
      mk(5, { '0,1': { isBlack: true }, '4,3': { isBlack: true } })
    );
    const out = writeToggleBlack(g5, 0, 1, true);
    expect(out[0][1]).toMatchObject({ isBlack: false, letter: '', isAutofilled: false });
    expect(out[4][3]).toMatchObject({ isBlack: false, letter: '', isAutofilled: false });
  });

  it('the centre cell is its own partner and still toggles', () => {
    // Centre cell is its own partner: toggling twice must not throw or lose structure.
    const g5 = freeze(mk(5));
    const out = writeToggleBlack(g5, 2, 2, true);
    expect(out[2][2].isBlack).toBe(true);
  });
});

describe('writeToggleThemeLock', () => {
  it('flips only isThemeLocked, clears the flags, leaves every other cell', () => {
    const g = freeze(
      mk(3, { '0,0': { letter: 'A', isAutofilled: true, isBlocked: true } })
    );
    const out = writeToggleThemeLock(g, 0, 0);
    expect(out[0][0]).not.toBe(g[0][0]);
    expect(out[0][0]).toMatchObject({
      letter: 'A',
      isThemeLocked: true,
      isAutofilled: false,
      isBlocked: false,
    });
    out.forEach((row, r) =>
      row.forEach((x, c) => {
        if (r !== 0 || c !== 0) expect(x).toBe(g[r][c]);
      })
    );
  });

  it('a black cell is not written: returns the input grid', () => {
    const g = freeze(mk(3, { '1,1': { isBlack: true } }));
    expect(writeToggleThemeLock(g, 1, 1)).toBe(g);
  });
});

describe('writePatternWord', () => {
  const g4 = () =>
    freeze(
      mk(4, {
        '0,1': { letter: 'A', isAutofilled: true },
        '0,2': { letter: 'X', isAutofilled: true, isBlocked: true },
      })
    );

  it('writes each letter along the direction as user writes, without mutating', () => {
    const g = g4();
    const out = writePatternWord(g, { row: 0, col: 0, direction: 'across' }, 'CAT');
    expect([0, 1, 2].map((c) => flags(out[0][c]))).toEqual([
      { letter: 'C', a: false, b: false },
      { letter: 'A', a: false, b: false },
      { letter: 'T', a: false, b: false },
    ]);
    [0, 1, 2].forEach((c) => expect(out[0][c]).not.toBe(g[0][c]));
    expect(out[0][3]).toBe(g[0][3]);
    expect(g[0][1].isAutofilled).toBe(true);
    expect(g[0][2].letter).toBe('X');
  });

  it('writes down a column', () => {
    const g = g4();
    const out = writePatternWord(g, { row: 1, col: 3, direction: 'down' }, 'AB');
    expect(out[1][3].letter).toBe('A');
    expect(out[2][3].letter).toBe('B');
    expect(out[3][3]).toBe(g[3][3]);
  });

  it('clips at the grid edge: writes (0,2) and (0,3) only', () => {
    const g = g4();
    const out = writePatternWord(g, { row: 0, col: 2, direction: 'across' }, 'CAT');
    expect(out[0][2].letter).toBe('C');
    expect(out[0][3].letter).toBe('A');
    expect(out[0][0]).toBe(g[0][0]);
    expect(out[0][1]).toBe(g[0][1]);
    expect(out[1][2]).toBe(g[1][2]);
  });
});

describe('writeAppliedTheme', () => {
  it('a newly theme-locked cell is written and loses autofill', () => {
    const prev = freeze(mk(3, { '0,0': { letter: 'A', isAutofilled: true } }));
    const upd = freeze(
      mk(3, { '0,0': { letter: 'A', isThemeLocked: true, isAutofilled: true } })
    );
    const out = writeAppliedTheme(prev, upd);
    expect(out[0][0]).not.toBe(prev[0][0]);
    expect(out[0][0]).toMatchObject({
      isThemeLocked: true,
      isAutofilled: false,
      isBlocked: false,
    });
  });

  it('a blacked cell given as a bare {letter, isBlack} is made canonical', () => {
    const prev = freeze(mk(3, { '1,1': { letter: 'Z', isAutofilled: true } }));
    const upd = mk(3);
    upd[1][1] = { letter: '', isBlack: true };
    freeze(upd);
    const out = writeAppliedTheme(prev, upd);
    expect(out[1][1]).toEqual({ ...makeCell(), isBlack: true });
  });

  it('an unchanged cell stays prev\'s object and keeps isAutofilled', () => {
    const prev = freeze(
      mk(3, { '2,2': { letter: 'Q', isAutofilled: true }, '0,0': { letter: 'A' } })
    );
    const upd = freeze(
      mk(3, {
        '2,2': { letter: 'Q', isAutofilled: false },
        '0,0': { letter: 'A', isThemeLocked: true },
      })
    );
    const out = writeAppliedTheme(prev, upd);
    expect(out[2][2]).toBe(prev[2][2]);
    expect(out[2][2].isAutofilled).toBe(true);
    expect(out[0][0]).not.toBe(prev[0][0]);
  });
});

describe('writeImportedGrid', () => {
  it('every imported letter counts as typed; canonical fields filled', () => {
    const src = freeze([[{ letter: 'A', isAutofilled: true, isBlocked: true }]]);
    const out = writeImportedGrid(src);
    expect(out[0][0]).toMatchObject({
      letter: 'A',
      isAutofilled: false,
      isThemeLocked: false,
      isBlocked: false,
    });
    expect(out[0][0]).not.toBe(src[0][0]);
  });
});

describe('writeCleanedGrid', () => {
  it('writes only cells Clean changes; a surviving autofilled letter stays autofilled (PD-4A)', () => {
    const prev = freeze(
      mk(2, {
        '0,0': { letter: 'Q', isAutofilled: true, isBlocked: true },
        '0,1': { letter: 'A', isAutofilled: true, isBlocked: true },
        '1,0': { letter: 'R', isError: true },
      })
    );
    const cleaned = [
      [{ letter: '', isBlack: false }, { letter: 'A', isBlack: false }],
      [{ letter: 'R', isBlack: false }, { letter: '', isBlack: false }],
    ];
    const out = writeCleanedGrid(prev, cleaned);
    expect(flags(out[0][0])).toEqual({ letter: '', a: false, b: false });
    expect(out[0][0]).not.toBe(prev[0][0]);
    expect(out[0][1]).toMatchObject({ letter: 'A', isAutofilled: true, isBlocked: true });
    expect(out[0][1].isError).toBe(false);
  });

  it('a cell turned black is written; isError clears on every cell', () => {
    const prev = freeze(mk(2, { '1,1': { letter: 'Z', isAutofilled: true, isError: true } }));
    const cleaned = [
      [{ letter: '', isBlack: false }, { letter: '', isBlack: false }],
      [{ letter: '', isBlack: false }, { letter: '', isBlack: true }],
    ];
    const out = writeCleanedGrid(prev, cleaned);
    expect(out[1][1]).toMatchObject({ isBlack: true, letter: '', isAutofilled: false, isError: false });
  });
});
