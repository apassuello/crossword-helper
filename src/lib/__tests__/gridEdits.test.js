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
  canToggleBlack,
  gridHasContent,
  applyVerifyErrors,
  planClean,
  clearAllErrors,
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

// novice-readiness spec 0.2.7 §3.5 (#62, G6): the normative table, row 0 of a 5x5.
// `.` empty, `#` black, `X*` theme-locked holding X, any other letter a user letter.
describe('writePatternWord protects cells (§3.5 #62, G6)', () => {
  const parse = (text) => {
    const over = {};
    const re = /#|[A-Z]\*|[A-Z]|\./g;
    let m;
    let c = 0;
    while ((m = re.exec(text))) {
      const t = m[0];
      if (t === '#') over[`0,${c}`] = { isBlack: true };
      else if (t.endsWith('*')) over[`0,${c}`] = { letter: t[0], isThemeLocked: true };
      else if (t !== '.') over[`0,${c}`] = { letter: t };
      c += 1;
    }
    return over;
  };
  // Render row 0 back to the table's notation. A black cell that holds a letter shows
  // it (`#T`), so a write into a black square cannot hide behind the `#`.
  const show = (g) =>
    g[0]
      .map((x) =>
        x.isBlack
          ? '#' + x.letter
          : (x.letter || '.') + (x.isThemeLocked ? '*' : '')
      )
      .join('');
  const across = (row, col) => ({ row, col, direction: 'across' });

  it.each([
    [0, 'CAT', '.....', 'CAT..'],
    [0, 'CAT', '..#..', 'CA#..'],
    // A word longer than the slot: the walk must END at the black square, not skip it.
    [0, 'CATER', '..#..', 'CA#..'],
    [0, 'CAT', '.X*..', 'CX*T..'],
    [3, 'CAT', '.....', '...CA'],
    [0, 'CAT', 'Z....', 'CAT..'],
  ])('start col %i, %s: %s -> %s', (col, word, before, after) => {
    const g = freeze(mk(5, parse(before)));
    expect(show(writePatternWord(g, across(0, col), word))).toBe(after);
  });

  it('a first-cell black square writes nothing and returns the input grid itself', () => {
    const g = freeze(mk(5, parse('#....')));
    const out = writePatternWord(g, across(0, 0), 'CAT');
    expect(out).toBe(g);
    expect(show(out)).toBe('#....');
  });

  it('a theme-locked cell is skipped (kept as the same object) and the walk continues past it', () => {
    const g = freeze(mk(5, parse('.X*..')));
    const out = writePatternWord(g, across(0, 0), 'CAT');
    expect(out[0][1]).toBe(g[0][1]);
    expect(out[0][2].letter).toBe('T');
    expect(out[0][0].letter).toBe('C');
  });

  it('an autofilled same-letter cell is rewritten as a new object with isAutofilled false', () => {
    const g = freeze(mk(5, { '0,0': { letter: 'C', isAutofilled: true } }));
    const out = writePatternWord(g, across(0, 0), 'CAT');
    expect(show(out)).toBe('CAT..');
    expect(out[0][0]).not.toBe(g[0][0]);
    expect(out[0][0].isAutofilled).toBe(false);
  });

  it('down: stops at the black square in column 0', () => {
    const g = freeze(
      mk(5, { '0,0': {}, '2,0': { isBlack: true } })
    );
    const out = writePatternWord(g, { row: 0, col: 0, direction: 'down' }, 'CATER');
    expect(out.map((r) => (r[0].isBlack ? '#' : r[0].letter || '.') + (r[0].isBlack ? r[0].letter : ''))).toEqual([
      'C', 'A', '#', '.', '.',
    ]);
  });

  it('down: skips a theme-locked cell and writes past it', () => {
    const g = freeze(mk(5, { '1,0': { letter: 'X', isThemeLocked: true } }));
    const out = writePatternWord(g, { row: 0, col: 0, direction: 'down' }, 'CAT');
    expect(out.map((r) => r[0].letter)).toEqual(['C', 'X', 'T', '', '']);
  });

  it('G6: the input grid deep-equals its pre-call snapshot, isAutofilled included', () => {
    const g = freeze(
      mk(5, {
        '0,0': { letter: 'C', isAutofilled: true },
        '0,1': { letter: 'X', isThemeLocked: true, isAutofilled: true },
        '0,3': { isBlack: true },
      })
    );
    const snapshot = JSON.parse(JSON.stringify(g));
    const out = writePatternWord(g, across(0, 0), 'CAT');
    expect(out).not.toBe(g);
    expect(JSON.parse(JSON.stringify(g))).toEqual(snapshot);
    expect(g[0][0].isAutofilled).toBe(true);
  });
});

describe('writeAppliedTheme', () => {
  it('a newly theme-locked cell is written and loses autofill', () => {
    const prev = freeze(mk(3, { '0,0': { letter: 'A', isAutofilled: true } }));
    const upd = freeze(
      mk(3, { '0,0': { letter: 'A', isThemeLocked: true, isAutofilled: true } })
    );
    const out = writeAppliedTheme(prev, upd, prev);
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
    const out = writeAppliedTheme(prev, upd, prev);
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
    const out = writeAppliedTheme(prev, upd, prev);
    expect(out[2][2]).toBe(prev[2][2]);
    expect(out[2][2].isAutofilled).toBe(true);
    expect(out[0][0]).not.toBe(prev[0][0]);
  });
});

// novice-readiness spec 0.2.8 §3.8 (F4, F1b, PD-6-G12): the merge is against the grid
// the request was built from, not the live grid.
describe('writeAppliedTheme against the sent grid', () => {
  const placed = { '0,0': { letter: 'C', isThemeLocked: true }, '0,1': { letter: 'A', isThemeLocked: true } };

  it('keeps a letter typed after the request was sent (F4)', () => {
    const sent = freeze(mk(5));
    const reply = freeze(mk(5, placed));
    const live = freeze(mk(5, { '2,2': { letter: 'Q' } }));
    const out = writeAppliedTheme(live, reply, sent);
    expect(out[2][2].letter).toBe('Q');
    expect(out[0][0]).toMatchObject({ letter: 'C', isThemeLocked: true });
    expect(out[0][1]).toMatchObject({ letter: 'A', isThemeLocked: true });
  });

  it('keeps a black square toggled after the request was sent', () => {
    const sent = freeze(mk(5));
    const reply = freeze(mk(5, placed));
    const live = freeze(mk(5, { '4,4': { isBlack: true } }));
    const out = writeAppliedTheme(live, reply, sent);
    expect(out[4][4].isBlack).toBe(true);
  });

  it("keeps the user's edit inside the reply's own cell (chained Apply All)", () => {
    const sent = freeze(mk(5, { '0,0': { letter: 'C', isThemeLocked: true } }));
    const reply = freeze(
      mk(5, { '0,0': { letter: 'C', isThemeLocked: true }, '1,0': { letter: 'A', isThemeLocked: true } })
    );
    // the user overwrote (1,0) with X while word 1 was being applied
    const live = freeze(
      mk(5, { '0,0': { letter: 'C', isThemeLocked: true }, '1,0': { letter: 'X' } })
    );
    const out = writeAppliedTheme(live, reply, sent);
    expect(out[1][0].letter).toBe('X');
    expect(out[1][0]).toBe(live[1][0]);
  });

  it('does not throw and returns the live grid when sizes differ (F1b)', () => {
    const reply = freeze(mk(3, { '0,0': { letter: 'A', isThemeLocked: true } }));
    const sent = freeze(mk(3));
    const live = freeze(mk(5));
    let out;
    expect(() => {
      out = writeAppliedTheme(live, reply, sent);
    }).not.toThrow();
    expect(out).toBe(live);
    const bigLive = freeze(mk(7));
    expect(writeAppliedTheme(bigLive, mk(5), mk(5))).toBe(bigLive);
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

// novice-readiness spec 0.2.7 §3.5 (G5, S1): Clean writes only the planned blanks.
describe('writeCleanedGrid', () => {
  it('blanks only the listed cells; every other cell keeps its own object and isError (PD-4A)', () => {
    const prev = freeze(
      mk(3, {
        '0,0': { letter: 'C', isError: true },
        '0,1': { letter: 'A', isAutofilled: true, isBlocked: true, isError: true },
        '0,2': { letter: 'T', isAutofilled: true, isBlocked: true, isError: true },
        '1,1': { letter: 'R', isError: true },
      })
    );
    const cleaned = mk(3, { '0,0': { letter: 'C' } });
    const out = writeCleanedGrid(prev, cleaned, [[0, 2]]);
    expect(out[0][2]).toMatchObject({
      letter: '',
      isError: false,
      isAutofilled: false,
      isBlocked: false,
    });
    expect(out[0][2]).not.toBe(prev[0][2]);
    for (const [r, c] of [[0, 0], [0, 1], [1, 1], [2, 2]]) {
      expect(out[r][c]).toBe(prev[r][c]);
    }
    expect(out[0][1].isError).toBe(true);
  });

  it('isBlack never changes: the response isBlack is not applied', () => {
    const prev = freeze(mk(3, { '1,1': { letter: 'Z' } }));
    const cleaned = mk(3, { '1,1': { isBlack: true }, '0,0': { isBlack: true } });
    const out = writeCleanedGrid(prev, cleaned, [[1, 1]]);
    expect(out[1][1]).toMatchObject({ letter: '', isBlack: false });
    expect(out[0][0]).toBe(prev[0][0]);
    expect(out[0][0].isBlack).toBe(false);
  });
});

describe('applyVerifyErrors', () => {
  it('changes only isError, by key; the input is unchanged', () => {
    const prev = freeze(
      mk(2, {
        '0,0': { isError: true },
        '1,1': { letter: 'Q' },
      })
    );
    const out = applyVerifyErrors(prev, new Set(['0,1']));
    expect(out[0][0].isError).toBe(false);
    expect(out[0][1].isError).toBe(true);
    expect(out[1][1].letter).toBe('Q');
    expect(prev[0][0].isError).toBe(true);
    expect(prev[0][1].isError).toBe(false);
    expect(out).not.toBe(prev);
  });
});

describe('clearAllErrors', () => {
  it('sets isError false everywhere and touches no letter', () => {
    const prev = freeze(
      mk(2, { '0,0': { letter: 'A', isError: true }, '1,1': { letter: 'B', isError: true } })
    );
    const out = clearAllErrors(prev);
    expect(out.flat().every((x) => x.isError === false)).toBe(true);
    expect(out[0][0].letter).toBe('A');
    expect(out[1][1].letter).toBe('B');
    expect(prev[0][0].isError).toBe(true);
  });
});

// novice-readiness spec 0.2.7 §3.5 (G5, S1): which letters Clean may blank.
describe('planClean', () => {
  const sent = [['C', 'A', 'T'], ['', '', ''], ['', '', '']];
  const cleaned = [['C', '', ''], ['', '', ''], ['', '', '']];
  const TL = { isThemeLocked: true };
  const row0 = (over = {}) =>
    mk(3, {
      '0,0': { letter: 'C', ...(over['0,0'] || {}) },
      '0,1': { letter: 'A', ...(over['0,1'] || {}) },
      '0,2': { letter: 'T', ...(over['0,2'] || {}) },
    });

  it('no locks: both removed letters', () => {
    expect(planClean(row0(), sent, cleaned).blanks).toEqual([[0, 1], [0, 2]]);
  });

  it('a theme-locked cell is never in blanks', () => {
    expect(planClean(row0({ '0,1': TL }), sent, cleaned).blanks).toEqual([[0, 2]]);
  });

  it('every removed cell locked: no blanks', () => {
    expect(planClean(row0({ '0,1': TL, '0,2': TL }), sent, cleaned).blanks).toEqual([]);
  });

  it('a letter typed after the request (Q) is not blanked', () => {
    expect(planClean(row0({ '0,1': { letter: 'Q' } }), sent, cleaned).blanks).toEqual([[0, 2]]);
  });

  it('a letter the server kept is not blanked', () => {
    const keeps = [['C', 'A', ''], ['', '', ''], ['', '', '']];
    expect(planClean(row0(), sent, keeps).blanks).toEqual([[0, 2]]);
  });

  it('a cell that was empty when sent is not blanked', () => {
    const sentGap = [['C', '', 'T'], ['', '', ''], ['', '', '']];
    expect(planClean(row0(), sentGap, cleaned).blanks).toEqual([[0, 2]]);
  });

  it('a cell black now is not blanked', () => {
    expect(planClean(row0({ '0,1': { isBlack: true } }), sent, cleaned).blanks).toEqual([[0, 2]]);
  });
});

// novice-readiness spec 0.2.7 §3.3 (G7): the shared black-square guard.
describe('canToggleBlack', () => {
  const TL = { isThemeLocked: true };
  const lockedAt = (...coords) =>
    mk(5, Object.fromEntries(coords.map(([r, c]) => [`${r},${c}`, TL])));

  it.each([
    ['no locks, symmetry on', [], 1, 1, true, true],
    ['selected cell locked, symmetry on', [[1, 1]], 1, 1, true, false],
    ['selected cell locked, symmetry off', [[1, 1]], 1, 1, false, false],
    ['partner locked, symmetry on', [[3, 3]], 1, 1, true, false],
    ['partner locked, symmetry off', [[3, 3]], 1, 1, false, true],
    ['centre cell locked (its own partner), symmetry on', [[2, 2]], 2, 2, true, false],
    ['unrelated cell locked, symmetry on', [[0, 0]], 1, 1, true, true],
  ])('%s', (_label, locks, r, c, sym, expected) => {
    expect(canToggleBlack(lockedAt(...locks), r, c, sym)).toBe(expected);
  });

  it('is false out of range', () => {
    expect(canToggleBlack(mk(5), 5, 0, true)).toBe(false);
    expect(canToggleBlack(mk(5), 0, -1, false)).toBe(false);
  });
});

// novice-readiness spec 0.2.7 §3.2 (#55): does New grid need a confirm?
describe('gridHasContent', () => {
  it('is false for a null grid', () => {
    expect(gridHasContent(null)).toBe(false);
  });

  it('is false for an all-empty white grid, even with theme-locked cells', () => {
    expect(gridHasContent(mk(3, { '1,1': { isThemeLocked: true } }))).toBe(false);
  });

  it('is true with one letter', () => {
    expect(gridHasContent(mk(3, { '2,0': { letter: 'A' } }))).toBe(true);
  });

  it('is true with one black square and no letters', () => {
    expect(gridHasContent(mk(3, { '0,2': { isBlack: true } }))).toBe(true);
  });
});
