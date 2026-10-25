import { describe, it, expect } from 'vitest';
import {
  snapshotContent,
  restoreContent,
  emptyHistory,
  pushStep,
  undoStep,
  redoStep,
  canUndo,
  canRedo,
} from '../history';
import { contentSigOf } from '../contentSig';

const cell = (over = {}) => ({
  letter: '',
  isBlack: false,
  isThemeLocked: false,
  isAutofilled: false,
  isError: false,
  isBlocked: false,
  number: null,
  ...over,
});
const mk = (n, f = () => ({})) =>
  Array.from({ length: n }, (_, r) => Array.from({ length: n }, (_, c) => cell(f(r, c))));
const snap = (letter) => snapshotContent(mk(3, (r, c) => (r === 0 && c === 0 ? { letter } : {})), 3);

describe('snapshotContent / restoreContent', () => {
  it('snapshot holds exactly size and the four content fields', () => {
    const s = snapshotContent(mk(3, () => ({ letter: 'A', isError: true, number: 4 })), 3);
    expect(s.size).toBe(3);
    expect(Object.keys(s.cells[0][0]).sort()).toEqual(
      ['isAutofilled', 'isBlack', 'isThemeLocked', 'letter'].sort()
    );
  });

  it('does not alias the source grid', () => {
    const g = mk(3);
    const s = snapshotContent(g, 3);
    g[0][0].letter = 'Z';
    expect(s.cells[0][0].letter).toBe('');
  });

  it('restore clears isError and isBlocked, keeps other fields', () => {
    const h = mk(3, () => ({ letter: 'B', isAutofilled: true, isThemeLocked: true }));
    const g = mk(3, () => ({ isError: true, isBlocked: true, number: 7 }));
    const out = restoreContent(g, snapshotContent(h, 3));
    expect(out[1][1]).toMatchObject({
      letter: 'B',
      isAutofilled: true,
      isThemeLocked: true,
      isError: false,
      isBlocked: false,
      number: 7,
    });
    expect(g[1][1].isError).toBe(true);
    expect(out).not.toBe(g);
  });

  it('contentSigOf round trip across two grids of one size', () => {
    const h = mk(4, (r, c) => ({ letter: (r + c) % 2 ? 'Q' : '', isBlack: r === c, isAutofilled: r === 1, isThemeLocked: c === 2 }));
    const g = mk(4, () => ({ letter: 'X', isError: true }));
    expect(contentSigOf(4, restoreContent(g, snapshotContent(h, 4)))).toBe(contentSigOf(4, h));
  });
});

describe('history stacks', () => {
  it('empty history cannot undo or redo, and both steps return null', () => {
    const h = emptyHistory();
    expect(canUndo(h)).toBe(false);
    expect(canRedo(h)).toBe(false);
    expect(undoStep(h, snap('A'))).toBeNull();
    expect(redoStep(h, snap('A'))).toBeNull();
  });

  it('push, undo and redo round trip exactly', () => {
    const a = snap('A');
    const b = snap('B');
    const h1 = pushStep(emptyHistory(), a);
    expect(canUndo(h1)).toBe(true);
    const u = undoStep(h1, b);
    expect(u.snapshot).toEqual(a);
    expect(canUndo(u.history)).toBe(false);
    expect(canRedo(u.history)).toBe(true);
    const r = redoStep(u.history, a);
    expect(r.snapshot).toEqual(b);
    expect(canRedo(r.history)).toBe(false);
    expect(canUndo(r.history)).toBe(true);
  });

  it('a push clears redo', () => {
    const h1 = pushStep(emptyHistory(), snap('A'));
    const u = undoStep(h1, snap('B'));
    expect(canRedo(u.history)).toBe(true);
    expect(canRedo(pushStep(u.history, snap('C')))).toBe(false);
  });

  it('keeps the latest 100 steps; step 101 drops the oldest', () => {
    let h = emptyHistory();
    for (let i = 0; i < 101; i++) h = pushStep(h, snap(String(i)));
    let cur = snap('cur');
    const seen = [];
    let u;
    while ((u = undoStep(h, cur))) {
      seen.push(u.snapshot.cells[0][0].letter);
      h = u.history;
      cur = u.snapshot;
    }
    expect(seen).toHaveLength(100);
    expect(seen[0]).toBe('100');
    expect(seen[99]).toBe('1');
  });

  it('never mutates its input', () => {
    const h1 = pushStep(emptyHistory(), snap('A'));
    const frozen = JSON.stringify(h1);
    undoStep(h1, snap('B'));
    pushStep(h1, snap('C'));
    redoStep(h1, snap('D'));
    expect(JSON.stringify(h1)).toBe(frozen);
  });
});
