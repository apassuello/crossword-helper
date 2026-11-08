/**
 * One content signature (novice-readiness spec 0.2.18 §3.9, "What one step is" / "What a step
 * holds"): App, the history and the hook all compare grid content through `lib/contentSig`.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { snapshotContent } from '../history';
import { contentSigOf, docSigOf, statusSigOf } from '../contentSig';

const cell = (patch = {}) => ({
  letter: '', isBlack: false, isThemeLocked: false, isAutofilled: false, ...patch,
});
const grid = (patch) => [[cell(patch)]];

describe('contentSigOf', () => {
  it('treats isAutofilled undefined as false', () => {
    const undef = grid();
    delete undef[0][0].isAutofilled;
    expect(contentSigOf(1, undef)).toBe(contentSigOf(1, grid({ isAutofilled: false })));
    expect(contentSigOf(1, undef)).not.toBe(contentSigOf(1, grid({ isAutofilled: true })));
  });

  it('a snapshot of an undefined-isAutofilled grid has the signature of the false grid', () => {
    const undef = grid();
    delete undef[0][0].isAutofilled;
    const a = snapshotContent(undef, 1);
    const b = snapshotContent(grid({ isAutofilled: false }), 1);
    expect(contentSigOf(a.size, a.cells)).toBe(contentSigOf(b.size, b.cells));
    expect(a.sig).toBe(docSigOf(1, grid({ isAutofilled: false }), {}));
  });

  it('App, the history and the hook import it from lib/contentSig and define no copy', () => {
    const read = (p) => fs.readFileSync(path.resolve(__dirname, '../..', p), 'utf8');
    for (const f of ['App.jsx', 'lib/history.js', 'hooks/useUndoHistory.js']) {
      expect(read(f), f).toMatch(/from '(\.\.\/|\.\/)(lib\/)?contentSig'/);
    }
    expect(read('App.jsx')).not.toMatch(/function contentSigOf/);
  });
});

// ---- Task 6: the document signature and the status signature (clue-authoring spec 4.1) ----
const grid2 = (over = {}) =>
  [
    [cell({ letter: 'R' }), cell({ letter: 'O' })],
    [cell(), cell()],
  ].map((row, r) => row.map((c, k) => ({ ...c, ...(over[`${r},${k}`] || {}) })));

const SPEC_SIG =
  '{"size":2,"cells":[[["R",false,false,false],["O",false,false,false]],' +
  '[["",false,false,false],["",false,false,false]]],"clues":[["0,0,across","Flower","RO"]]}';
const SPEC_CLUES = { '0,0,across': { text: 'Flower', answer: 'RO' } };

// Three entries in key order: 0,0,across < 0,0,down < 1,0,across.
const entry = (t, a) => ({ text: t, answer: a });
const KEY_ORDER = ['0,0,across', '0,0,down', '1,0,across'];
const mapOf = (keys) => Object.fromEntries(keys.map((k) => [k, entry(`t ${k}`, 'AB')]));

describe('docSigOf', () => {
  it('is byte-exact for the spec 4.1 example', () => {
    expect(docSigOf(2, grid2(), SPEC_CLUES)).toBe(SPEC_SIG);
  });

  it('gives the same signature with no clue map as with {}', () => {
    expect(docSigOf(2, grid2())).toBe(docSigOf(2, grid2(), {}));
  });

  it('changes when one clue text changes', () => {
    const other = { '0,0,across': { text: 'Bloom', answer: 'RO' } };
    expect(docSigOf(2, grid2(), other)).not.toBe(docSigOf(2, grid2(), SPEC_CLUES));
  });

  it('changes when one clue answer changes', () => {
    const other = { '0,0,across': { text: 'Flower', answer: 'RA' } };
    expect(docSigOf(2, grid2(), other)).not.toBe(docSigOf(2, grid2(), SPEC_CLUES));
  });

  it('changes on a grid edit of one letter', () => {
    const edited = grid2({ '1,1': { letter: 'X' } });
    expect(docSigOf(2, edited, SPEC_CLUES)).not.toBe(docSigOf(2, grid2(), SPEC_CLUES));
  });

  it('is identical for the same entries inserted in another order (6.3)', () => {
    const a = mapOf(['0,0,down', '1,0,across', '0,0,across']);
    const b = mapOf(['1,0,across', '0,0,across', '0,0,down']);
    expect(Object.keys(a)).not.toEqual(KEY_ORDER);
    expect(Object.keys(a)).not.toEqual([...KEY_ORDER].reverse());
    expect(Object.keys(a)).not.toEqual(Object.keys(b));
    expect(docSigOf(2, grid2(), a)).toBe(docSigOf(2, grid2(), b));
  });

  it('lists the triples in compareClueKeys order, not string order', () => {
    const clues = { '10,0,across': entry('ten', 'AB'), '2,0,down': entry('two', 'CD') };
    expect(JSON.parse(docSigOf(2, grid2(), clues)).clues).toEqual([
      ['2,0,down', 'two', 'CD'],
      ['10,0,across', 'ten', 'AB'],
    ]);
  });

  it('keeps the cells exactly as contentSigOf serializes them', () => {
    const g = grid2();
    expect(JSON.parse(docSigOf(2, g, SPEC_CLUES)).cells).toEqual(
      JSON.parse(contentSigOf(2, g)).cells
    );
  });

  it('serializes a null grid as cells: null, exactly as contentSigOf does', () => {
    const cells = JSON.parse(docSigOf(2, null, {})).cells;
    expect(cells).toBe(null);
    expect(cells).toEqual(JSON.parse(contentSigOf(2, null)).cells);
  });
});

describe('contentSigOf is unchanged by clues', () => {
  it('has no clues key on the spec 4.1 grid', () => {
    expect(contentSigOf(2, grid2())).toBe(
      '{"size":2,"cells":[[["R",false,false,false],["O",false,false,false]],' +
        '[["",false,false,false],["",false,false,false]]]}'
    );
  });
});

describe('statusSigOf', () => {
  it('gives the same signature with no clue map as with {}', () => {
    expect(statusSigOf(2, grid2())).toBe(statusSigOf(2, grid2(), {}));
  });

  it('is the same when only one clue text differs', () => {
    const other = { '0,0,across': { text: 'Bloom', answer: 'RO' } };
    expect(statusSigOf(2, grid2(), other)).toBe(statusSigOf(2, grid2(), SPEC_CLUES));
  });

  it('differs when one answer differs', () => {
    const other = { '0,0,across': { text: 'Flower', answer: 'RA' } };
    expect(statusSigOf(2, grid2(), other)).not.toBe(statusSigOf(2, grid2(), SPEC_CLUES));
  });

  it('differs when a key is added', () => {
    const more = { ...SPEC_CLUES, '0,0,down': { text: 'x', answer: 'RA' } };
    expect(statusSigOf(2, grid2(), more)).not.toBe(statusSigOf(2, grid2(), SPEC_CLUES));
  });

  it('differs when the same answers sit under different keys', () => {
    const across = { '0,0,across': { text: 'x', answer: 'RO' } };
    const down = { '0,0,down': { text: 'x', answer: 'RO' } };
    expect(statusSigOf(2, grid2(), across)).not.toBe(statusSigOf(2, grid2(), down));
  });

  it('differs on a grid edit', () => {
    const edited = grid2({ '1,1': { letter: 'X' } });
    expect(statusSigOf(2, edited, SPEC_CLUES)).not.toBe(statusSigOf(2, grid2(), SPEC_CLUES));
  });

  it('is the same for another insertion order', () => {
    const a = mapOf(['0,0,down', '1,0,across', '0,0,across']);
    const b = mapOf(['1,0,across', '0,0,across', '0,0,down']);
    expect(statusSigOf(2, grid2(), a)).toBe(statusSigOf(2, grid2(), b));
  });
});
