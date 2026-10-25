/**
 * Two edits before one render are two undo steps (novice-readiness spec 0.2.18 §3.9, "What one
 * step is"). Each handler records the grid it saw, then writes with a functional update.
 */
import { describe, it, expect } from 'vitest';
import React, { useState } from 'react';
import { renderHook, act } from '@testing-library/react';
import { useUndoHistory } from '../useUndoHistory';

const blank = () =>
  Array.from({ length: 2 }, () =>
    Array.from({ length: 2 }, () => ({
      letter: '', isBlack: false, isThemeLocked: false, isAutofilled: false,
    }))
  );
const put = (g, r, c, letter) =>
  g.map((row, ri) => row.map((x, ci) => (ri === r && ci === c ? { ...x, letter } : x)));
const letters = (g) => g.map((row) => row.map((c) => c.letter || '.').join('')).join('/');

describe('useUndoHistory: two records before one render', () => {
  it.each([
    ['plain', undefined],
    ['StrictMode', React.StrictMode],
  ])('records two steps, each with its own before (%s)', (_n, wrapper) => {
    const paused = { current: false };
    const hook = renderHook(
      () => {
        const [grid, setGrid] = useState(blank());
        const h = useUndoHistory({ grid, gridSize: 2, setGrid, editingPausedRef: paused });
        return { ...h, grid, setGrid };
      },
      { wrapper }
    );
    const r = () => hook.result.current;
    act(() => {
      // what App does: record the grid it saw, then a functional write; a mirror ref hands the
      // second call the grid the first call produced, so the befores differ.
      const b0 = r().grid;
      r().record(b0);
      r().setGrid((g) => put(g, 0, 0, 'A'));
      r().record(put(b0, 0, 0, 'A'));
      r().setGrid((g) => put(g, 0, 1, 'B'));
    });
    expect(letters(r().grid)).toBe('AB/..');
    act(() => r().undo());
    expect(letters(r().grid)).toBe('A./..');
    act(() => r().undo());
    expect(letters(r().grid)).toBe('../..');
    expect(r().canUndo).toBe(false);
    act(() => r().redo());
    expect(letters(r().grid)).toBe('A./..');
    act(() => r().redo());
    expect(letters(r().grid)).toBe('AB/..');
  });
});
