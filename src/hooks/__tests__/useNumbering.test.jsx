/**
 * Tests for the numbering module (Task 8B pure helpers + Task 8C hook).
 *
 * localNumber/numberingMapFromGrid/structuralSigOf are PURE (Task 8B) — no
 * rendering. `useNumbering` (Task 8C) is the React hook layered on top: it
 * detects structural edits via structuralSigOf, paints optimistic numbers
 * synchronously, then reconciles server-wins numbering + validation under a
 * shared request token with a 150ms debounce.
 *
 * Hook-test conventions mirror useHealth.test.jsx / useSaveMachine.test.jsx:
 * fake timers, `vi.spyOn(api, ...)`, `renderHook`/`act`, and a deferred-promise
 * helper for the out-of-order cases. `pushToast`/`setGrid` are injected as
 * plain mocks (the hook takes them as params), so no provider wrapper is needed.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { localNumber, structuralSigOf, useNumbering } from '../useNumbering';
import { allSlots } from '../useGridGeometry';
import { api } from '../../api/client';
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

// The linchpin property GC3 + the hook's change-detection both rely on:
// structuralSigOf is invariant to .letter, sensitive to .isBlack.
describe('structuralSigOf', () => {
  it('is identical when grids differ only in .letter', () => {
    const a = gridFromRows(['A#...', '.....', '.....', '.....', '.....']);
    const b = gridFromRows(['Z#...', '.....', '.....', '.....', '.....']);
    expect(structuralSigOf(5, a)).toBe(structuralSigOf(5, b));
  });

  it('differs when grids differ in .isBlack', () => {
    const a = gridFromRows(['A#...', '.....', '.....', '.....', '.....']);
    const c = gridFromRows(['A....', '.....', '.....', '.....', '.....']);
    expect(structuralSigOf(5, a)).not.toBe(structuralSigOf(5, c));
  });
});

// deferred-promise helper (out-of-order + mid-flight tests) — brief convention.
const d = () => {
  let r;
  const p = new Promise((res) => {
    r = res;
  });
  return { p, r };
};

const WHITE_5 = ['.....', '.....', '.....', '.....', '.....'];

describe('useNumbering hook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('1. instant paint: optimistic setGrid is synchronous, api calls wait behind the 150ms debounce', async () => {
    const setGrid = vi.fn();
    const pushToast = vi.fn();
    const numberGrid = vi.spyOn(api, 'numberGrid').mockResolvedValue({ numbering: {} });
    const validateGrid = vi
      .spyOn(api, 'validateGrid')
      .mockResolvedValue({ warnings: [], suggestions: [] });

    const gA = gridFromRows(WHITE_5);
    const { rerender } = renderHook((props) => useNumbering(props), {
      initialProps: { grid: null, gridSize: 5, setGrid, pushToast },
    });
    // Null grid on mount → no fire.
    expect(setGrid).not.toHaveBeenCalled();

    // Structural rerender (null → grid): the sig changes → the effect fires.
    rerender({ grid: gA, gridSize: 5, setGrid, pushToast });

    // Optimistic paint happened synchronously (effect flushed inside act by rerender).
    expect(setGrid).toHaveBeenCalledTimes(1);
    expect(setGrid).toHaveBeenCalledWith(localNumber(gA).grid);
    // ...but the server calls are still parked behind the debounce.
    expect(numberGrid).not.toHaveBeenCalled();
    expect(validateGrid).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });
    expect(numberGrid).toHaveBeenCalledTimes(1);
    expect(validateGrid).toHaveBeenCalledTimes(1);
  });

  it('2. server wins: reconciles to the server numbering, overriding the optimistic pass', async () => {
    const setGrid = vi.fn();
    const pushToast = vi.fn();
    // Optimistic localNumber gives (0,0)->1,(0,1)->2; server disagrees (paren keys).
    const serverNumbering = { '(0,0)': 42, '(0,1)': 7 };
    vi.spyOn(api, 'numberGrid').mockResolvedValue({ numbering: serverNumbering });
    vi.spyOn(api, 'validateGrid').mockResolvedValue({ warnings: [], suggestions: [] });

    const gA = gridFromRows(WHITE_5);
    const { result, rerender } = renderHook((props) => useNumbering(props), {
      initialProps: { grid: null, gridSize: 5, setGrid, pushToast },
    });
    rerender({ grid: gA, gridSize: 5, setGrid, pushToast });

    // Sanity: the optimistic pass and the server disagree.
    expect(localNumber(gA).numbering['0,0']).toBe(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });

    // Exposed numbering is the SERVER's (unparenthesized "row,col" keys).
    expect(result.current.numbering).toEqual({ '0,0': 42, '0,1': 7 });
    expect(result.current.unverified).toBe(false);

    // ...and the reconciled grid setGrid received carries the server numbers.
    const lastGrid = setGrid.mock.calls.at(-1)[0];
    expect(lastGrid[0][0].number).toBe(42);
    expect(lastGrid[0][1].number).toBe(7);
  });

  it('3. out-of-order discard: a late stale resolution never clobbers the newest (token guard is load-bearing)', async () => {
    const setGrid = vi.fn();
    const pushToast = vi.fn();
    const d1 = d();
    const d2 = d();
    const numberGrid = vi
      .spyOn(api, 'numberGrid')
      .mockReturnValueOnce(d1.p)
      .mockReturnValueOnce(d2.p);
    vi.spyOn(api, 'validateGrid').mockResolvedValue({ warnings: [], suggestions: [] });

    const g1 = gridFromRows(WHITE_5);
    const g2 = gridFromRows(['#....', '.....', '.....', '.....', '.....']);
    const { result, rerender } = renderHook((props) => useNumbering(props), {
      initialProps: { grid: null, gridSize: 5, setGrid, pushToast },
    });

    // Edit 1 → debounce → numberGrid #1 (token 1), pending on d1.p.
    rerender({ grid: g1, gridSize: 5, setGrid, pushToast });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });

    // Edit 2 → debounce → numberGrid #2 (token 2), pending on d2.p.
    rerender({ grid: g2, gridSize: 5, setGrid, pushToast });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });
    expect(numberGrid).toHaveBeenCalledTimes(2);

    // Resolve the NEWEST first, then the stale one (reversed vs token order).
    await act(async () => {
      d2.r({ numbering: { '(1,1)': 9 } });
      await Promise.resolve();
    });
    await act(async () => {
      d1.r({ numbering: { '(0,0)': 1 } });
      await Promise.resolve();
    });

    // Final numbering is the SECOND (newest) response; the late first is discarded.
    // Without the token guard, the late d1 resolution would clobber this to {'0,0':1}.
    expect(result.current.numbering).toEqual({ '1,1': 9 });
  });

  it('4. mid-flight keystroke survives reconcile: a letter typed before the server responds is preserved', async () => {
    const setGrid = vi.fn();
    const pushToast = vi.fn();
    const dNum = d();
    const numberGrid = vi.spyOn(api, 'numberGrid').mockReturnValue(dNum.p);
    vi.spyOn(api, 'validateGrid').mockResolvedValue({ warnings: [], suggestions: [] });

    const gStruct = gridFromRows(WHITE_5);
    const { rerender } = renderHook((props) => useNumbering(props), {
      initialProps: { grid: null, gridSize: 5, setGrid, pushToast },
    });

    // Structural edit → debounce → numberGrid called, pending.
    rerender({ grid: gStruct, gridSize: 5, setGrid, pushToast });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });
    expect(numberGrid).toHaveBeenCalledTimes(1);

    // BEFORE the server responds, a letter is typed (letter-only edit, same isBlack layout).
    const gTyped = gridFromRows(['Q....', '.....', '.....', '.....', '.....']);
    rerender({ grid: gTyped, gridSize: 5, setGrid, pushToast });
    // The letter edit must not fire another numbering call (sig unchanged).
    expect(numberGrid).toHaveBeenCalledTimes(1);

    // Server responds now → reconcile applies to gridRef.current (= gTyped).
    await act(async () => {
      dNum.r({ numbering: { '(0,0)': 1 } });
      await Promise.resolve();
    });

    const lastGrid = setGrid.mock.calls.at(-1)[0];
    expect(lastGrid[0][0].letter).toBe('Q'); // typed letter survived the reconcile
    expect(lastGrid[0][0].number).toBe(1); // and the server number was applied
  });

  it('5. letter typing fires neither numberGrid nor validateGrid', async () => {
    const setGrid = vi.fn();
    const pushToast = vi.fn();
    const numberGrid = vi.spyOn(api, 'numberGrid').mockResolvedValue({ numbering: {} });
    const validateGrid = vi
      .spyOn(api, 'validateGrid')
      .mockResolvedValue({ warnings: [], suggestions: [] });

    const gStruct = gridFromRows(WHITE_5);
    const { rerender } = renderHook((props) => useNumbering(props), {
      initialProps: { grid: gStruct, gridSize: 5, setGrid, pushToast },
    });
    // Flush the mount's structural fire, then start from a clean slate.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });
    expect(numberGrid).toHaveBeenCalledTimes(1);
    expect(validateGrid).toHaveBeenCalledTimes(1);
    numberGrid.mockClear();
    validateGrid.mockClear();

    // Letter-only edits (identical isBlack layout).
    rerender({ grid: gridFromRows(['A....', '.....', '.....', '.....', '.....']), gridSize: 5, setGrid, pushToast });
    rerender({ grid: gridFromRows(['AB...', '.....', '.....', '.....', '.....']), gridSize: 5, setGrid, pushToast });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });
    expect(numberGrid).not.toHaveBeenCalled();
    expect(validateGrid).not.toHaveBeenCalled();
  });

  it('6. debounce coalesces N rapid structural edits into exactly one numberGrid call', async () => {
    const setGrid = vi.fn();
    const pushToast = vi.fn();
    const numberGrid = vi.spyOn(api, 'numberGrid').mockResolvedValue({ numbering: {} });
    vi.spyOn(api, 'validateGrid').mockResolvedValue({ warnings: [], suggestions: [] });

    const { rerender } = renderHook((props) => useNumbering(props), {
      initialProps: { grid: null, gridSize: 5, setGrid, pushToast },
    });

    // Three rapid structural edits (distinct isBlack layouts), no time between them.
    rerender({ grid: gridFromRows(['#....', '.....', '.....', '.....', '.....']), gridSize: 5, setGrid, pushToast });
    rerender({ grid: gridFromRows(['##...', '.....', '.....', '.....', '.....']), gridSize: 5, setGrid, pushToast });
    rerender({ grid: gridFromRows(['###..', '.....', '.....', '.....', '.....']), gridSize: 5, setGrid, pushToast });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });
    expect(numberGrid).toHaveBeenCalledTimes(1);
  });

  it('7. failure path: numberGrid rejection keeps the optimistic numbers, sets unverified, pushes an error toast', async () => {
    const setGrid = vi.fn();
    const pushToast = vi.fn();
    vi.spyOn(api, 'numberGrid').mockRejectedValue(new Error('boom'));
    // validateGrid RESOLVES so only the numbering rejection surfaces a toast.
    vi.spyOn(api, 'validateGrid').mockResolvedValue({ warnings: [], suggestions: [] });

    const gA = gridFromRows(WHITE_5);
    const { result, rerender } = renderHook((props) => useNumbering(props), {
      initialProps: { grid: null, gridSize: 5, setGrid, pushToast },
    });
    rerender({ grid: gA, gridSize: 5, setGrid, pushToast });

    // The optimistic paint is the only setGrid so far.
    expect(setGrid).toHaveBeenCalledTimes(1);
    const optimisticGrid = setGrid.mock.calls[0][0];

    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });

    expect(result.current.unverified).toBe(true);
    expect(pushToast).toHaveBeenCalledTimes(1);
    expect(pushToast).toHaveBeenCalledWith(expect.objectContaining({ kind: 'error' }));
    // No reconcile setGrid — the optimistic pass remains the latest grid write.
    expect(setGrid).toHaveBeenCalledTimes(1);
    expect(setGrid.mock.calls[0][0]).toBe(optimisticGrid);
  });
});
