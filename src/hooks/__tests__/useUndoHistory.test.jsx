/**
 * useUndoHistory (U.2, novice-readiness spec 0.2.11 section 3.9): the React wiring over the pure
 * `lib/history`. A step is recorded only when the content signature differs once the edit has
 * rendered; a batch (Apply All) is one step; undo and redo are D1 writers.
 */
import { describe, it, expect } from 'vitest';
import { useState } from 'react';
import { renderHook, act } from '@testing-library/react';
import { useUndoHistory } from '../useUndoHistory';
import { contentSigOf } from '../../lib/contentSig';

const blank = (n = 3) =>
  Array.from({ length: n }, () =>
    Array.from({ length: n }, () => ({
      letter: '',
      isBlack: false,
      number: null,
      isError: false,
      isHighlighted: false,
      isThemeLocked: false,
      isAutofilled: false,
      isBlocked: false,
    }))
  );

const put = (g, r, c, patch) =>
  g.map((row, ri) => row.map((cell, ci) => (ri === r && ci === c ? { ...cell, ...patch } : cell)));

const letters = (g) => g.map((row) => row.map((c) => c.letter || '.').join('')).join('/');

// beginBatch inside act(), returning its token.
const begin0 = (r) => {
  let t;
  act(() => {
    t = r().beginBatch();
  });
  return t;
};

function setup(initial = blank()) {
  const paused = { current: false };
  const hook = renderHook(() => {
    const [grid, setGrid] = useState(initial);
    const h = useUndoHistory({ grid, gridSize: initial.length, setGrid, editingPausedRef: paused });
    return { ...h, grid, setGrid };
  });
  // One user edit: record the grid before, write the new one, in one batch as a handler does.
  const edit = (fn) =>
    act(() => {
      hook.result.current.record(hook.result.current.grid);
      hook.result.current.setGrid((g) => fn(g));
    });
  return { hook, paused, edit, r: () => hook.result.current };
}

describe('useUndoHistory', () => {
  it('one edit is one step: undo restores the content, redo reapplies it exactly', () => {
    const { edit, r } = setup();
    edit((g) => put(g, 0, 0, { letter: 'A', isThemeLocked: true, isAutofilled: true }));
    const after = contentSigOf(3, r().grid);
    expect(r().canUndo).toBe(true);
    expect(r().canRedo).toBe(false);
    act(() => r().undo());
    expect(letters(r().grid)).toBe('.../.../...');
    expect(r().canUndo).toBe(false);
    expect(r().canRedo).toBe(true);
    act(() => r().redo());
    expect(contentSigOf(3, r().grid)).toBe(after);
  });

  it('an edit that leaves the content signature unchanged records no step, though the grid is a new object', () => {
    const { edit, r } = setup(put(blank(), 0, 0, { letter: 'A' }));
    const before = r().grid;
    edit((g) => put(g, 0, 0, { letter: 'A' }));
    expect(r().grid).not.toBe(before);
    expect(r().canUndo).toBe(false);
  });

  it('the same letter over an autofilled cell is a change', () => {
    const { edit, r } = setup(put(blank(), 0, 0, { letter: 'A', isAutofilled: true }));
    edit((g) => put(g, 0, 0, { letter: 'A', isAutofilled: false }));
    expect(r().canUndo).toBe(true);
    act(() => r().undo());
    expect(r().grid[0][0].isAutofilled).toBe(true);
  });

  it('a new step clears the redo stack', () => {
    const { edit, r } = setup();
    edit((g) => put(g, 0, 0, { letter: 'A' }));
    act(() => r().undo());
    expect(r().canRedo).toBe(true);
    edit((g) => put(g, 1, 1, { letter: 'B' }));
    expect(r().canRedo).toBe(false);
  });

  it('undo and redo clear isError and isBlocked on every cell', () => {
    const { edit, r } = setup();
    edit((g) => put(g, 0, 0, { letter: 'A' }));
    act(() => r().setGrid((g) => put(put(g, 0, 0, { isError: true }), 2, 2, { isBlocked: true })));
    act(() => r().undo());
    expect(r().grid.flat().some((c) => c.isError || c.isBlocked)).toBe(false);
    act(() => r().setGrid((g) => put(g, 1, 1, { isError: true })));
    act(() => r().redo());
    expect(r().grid.flat().some((c) => c.isError || c.isBlocked)).toBe(false);
  });

  it('a batch of three edits is one step', () => {
    const { r } = setup();
    const t = begin0(r);
    for (const [row, ch] of [[0, 'A'], [1, 'B'], [2, 'C']]) {
      act(() => {
        r().record(r().grid); // the per-word record of onApplyPlacement: folded
        r().setGrid((g) => put(g, row, 0, { letter: ch }));
      });
    }
    act(() => r().commitBatch(t));
    expect(letters(r().grid)).toBe('A../B../C..');
    act(() => r().undo());
    expect(letters(r().grid)).toBe('.../.../...');
    expect(r().canUndo).toBe(false);
    act(() => r().redo());
    expect(letters(r().grid)).toBe('A../B../C..');
  });

  it('a batch that changed nothing records no step', () => {
    const { r } = setup();
    const t = begin0(r);
    act(() => r().commitBatch(t));
    expect(r().canUndo).toBe(false);
  });

  it('a batch committed in the same update as its last write still sees that write', () => {
    const { r } = setup();
    const t = begin0(r);
    act(() => {
      r().setGrid((g) => put(g, 0, 0, { letter: 'A' }));
      r().commitBatch(t);
    });
    expect(r().canUndo).toBe(true);
  });

  it('while a batch is open an edit is folded into it and undo and redo do nothing', () => {
    const { edit, r } = setup();
    edit((g) => put(g, 0, 0, { letter: 'A' })); // an earlier step
    const t = begin0(r);
    edit((g) => put(g, 1, 1, { letter: 'B' })); // user edit inside the batch
    act(() => r().undo());
    expect(letters(r().grid)).toBe('A../.B./...');
    act(() => r().commitBatch(t));
    act(() => r().undo()); // one step for the batch, which holds the user edit
    expect(letters(r().grid)).toBe('A../.../...');
    act(() => r().undo());
    expect(letters(r().grid)).toBe('.../.../...');
  });

  it('redo does nothing while a batch is open, with a step waiting on the redo stack', () => {
    const { edit, r } = setup();
    edit((g) => put(g, 0, 0, { letter: 'A' }));
    act(() => r().undo());
    expect(r().canRedo).toBe(true);
    const t = begin0(r);
    act(() => r().redo());
    expect(letters(r().grid)).toBe('.../.../...');
  });

  it('clear() empties both stacks and ends an open batch without recording it', () => {
    const { edit, r } = setup();
    edit((g) => put(g, 0, 0, { letter: 'A' }));
    act(() => r().undo());
    const t = begin0(r);
    act(() => r().setGrid((g) => put(g, 2, 2, { letter: 'Z' })));
    act(() => r().clear());
    act(() => r().commitBatch(t));
    expect(r().canUndo).toBe(false);
    expect(r().canRedo).toBe(false);
  });

  it('undo and redo return early while a run is live (D1)', () => {
    const { edit, paused, r } = setup();
    edit((g) => put(g, 0, 0, { letter: 'A' }));
    paused.current = true;
    act(() => r().undo());
    expect(letters(r().grid)).toBe('A../.../...');
    expect(r().canUndo).toBe(true);
    paused.current = false;
    act(() => r().undo());
    paused.current = true;
    act(() => r().redo());
    expect(letters(r().grid)).toBe('.../.../...');
    expect(r().canRedo).toBe(true);
  });

  it('undo with nothing to undo does nothing', () => {
    const { r } = setup();
    const g = r().grid;
    act(() => r().undo());
    act(() => r().redo());
    expect(r().grid).toBe(g);
  });
});

describe('useUndoHistory batch tokens (PR #90 Greptile P1, P2)', () => {
  const begin = (r) => {
    let t;
    act(() => {
      t = r().beginBatch();
    });
    return t;
  };

  it('(a) a token issued before clear() is stale: it cannot close the batch opened after it', () => {
    const { r } = setup();
    const t1 = begin(r);
    act(() => r().clear());
    const t2 = begin(r);
    act(() => r().commitBatch(t1));
    // still open: a record folds into the batch and undo is blocked
    act(() => {
      r().record(r().grid);
      r().setGrid((g) => put(g, 0, 0, { letter: 'A' }));
    });
    act(() => {
      r().record(r().grid);
      r().setGrid((g) => put(g, 1, 0, { letter: 'B' }));
    });
    expect(r().batchOpen).toBe(true);
    act(() => r().undo());
    expect(letters(r().grid)).toBe('A../B../...');
    act(() => r().commitBatch(t2));
    expect(r().batchOpen).toBe(false);
    act(() => r().undo());
    expect(letters(r().grid)).toBe('.../.../...');
    expect(r().canUndo).toBe(false);
  });

  it('(b) a batch opened over an orphan commits the orphan; the orphan token is then ignored', () => {
    const { r } = setup();
    const t1 = begin(r);
    const t2 = begin(r);
    expect(t2).not.toBe(t1);
    act(() => r().commitBatch(t1));
    expect(r().batchOpen).toBe(true);
    act(() => r().commitBatch(t2));
    expect(r().batchOpen).toBe(false);
  });

  it('(b2) the orphan batch keeps its own step; the new batch is a second one', () => {
    const { r } = setup();
    const t1 = begin(r);
    act(() => r().setGrid((g) => put(g, 0, 0, { letter: 'A' })));
    const t2 = begin(r);
    act(() => r().setGrid((g) => put(g, 1, 0, { letter: 'B' })));
    act(() => r().commitBatch(t1));
    act(() => r().commitBatch(t2));
    act(() => r().undo());
    expect(letters(r().grid)).toBe('A../.../...');
    act(() => r().undo());
    expect(letters(r().grid)).toBe('.../.../...');
  });

  it('a missing token is ignored', () => {
    const { r } = setup();
    begin(r);
    act(() => r().commitBatch());
    expect(r().batchOpen).toBe(true);
  });

  it('(c) batchOpen is true as soon as beginBatch renders, false after the commit', () => {
    const { r } = setup();
    expect(r().batchOpen).toBe(false);
    const t = begin(r);
    expect(r().batchOpen).toBe(true);
    act(() => r().commitBatch(t));
    expect(r().batchOpen).toBe(false);
  });

  it('batchOpen is false after clear()', () => {
    const { r } = setup();
    begin(r);
    act(() => r().clear());
    expect(r().batchOpen).toBe(false);
  });
});
