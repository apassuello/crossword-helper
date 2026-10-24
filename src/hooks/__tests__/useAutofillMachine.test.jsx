/**
 * Tests for useAutofillMachine (Task 11A) — the F3 autofill lifecycle hook.
 *
 * Follows the useNumbering/useSaveMachine hook-test convention: `api` methods
 * are mocked via `vi.spyOn`, and SSE is driven through the global
 * `MockEventSource` already installed by setupTests.js (see
 * `src/__tests__/setupTests.js`) — `api.openProgress` is NOT mocked, it runs
 * for real against the mocked global `EventSource`, so `global.EventSource
 * .sendMessage(...)` / `.sendError(...)` broadcast to whatever instance the
 * hook opened.
 *
 * No fake timers: this hook has no internal timers (unlike useNumbering's
 * debounce), just promise microtasks from api.startFill/api.cancelFill. The
 * `flush()` helper below drains those between `act()` calls.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { useState } from 'react';
import { renderHook, act } from '@testing-library/react';
import { useAutofillMachine, mergeGridPreserveThemeLocked, LIVE_STATES } from '../useAutofillMachine';
import { api } from '../../api/client';
import { toCliStrings } from '../../api/gridCodec';
import { gridFromRows } from './gridFixtures';

/** Flush a couple of promise microtask turns inside act() (no timer advance). */
const flush = () =>
  act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });

const WHITE_4 = ['....', '....', '....', '....'];

const CLI_FULL_4 = [
  ['A', 'B', 'C', 'D'],
  ['E', 'F', 'G', 'H'],
  ['I', 'J', 'K', 'L'],
  ['M', 'N', 'O', 'P'],
];

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useAutofillMachine', () => {
  it('1. start() -> submitting -> (202) -> running, EventSource opened with the right taskId', async () => {
    const grid = gridFromRows(WHITE_4);
    const startFill = vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-1' });
    const openProgress = vi.spyOn(api, 'openProgress');
    const onGridUpdate = vi.fn();

    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, onGridUpdate })
    );

    act(() => {
      result.current.start({
        algorithm: 'hybrid',
        timeout: 60,
        minScore: 30,
        wordlists: ['comprehensive'],
      });
    });

    expect(result.current.state).toBe('submitting');
    expect(result.current.message).toBe('Starting autofill…');
    expect(result.current.progress).toBe(0);

    // Binding request-shape contract (brief's mapping table).
    expect(startFill).toHaveBeenCalledWith({
      size: 4,
      grid: toCliStrings(grid),
      wordlists: ['comprehensive'],
      timeout: 60,
      min_score: 30,
      algorithm: 'hybrid',
      theme_entries: {},
      locked_cells: [],
      adaptive_mode: undefined,
      max_adaptations: undefined,
      partial_fill: undefined,
      cleanup: undefined,
      resumeTaskId: undefined,
    });

    await flush();

    expect(result.current.state).toBe('running');
    expect(result.current.taskId).toBe('task-1');
    expect(openProgress).toHaveBeenCalledWith(
      'task-1',
      expect.objectContaining({ onEvent: expect.any(Function), onError: expect.any(Function) })
    );
  });

  it('2. running progress events update {progress, message}', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-2' });
    const grid = gridFromRows(WHITE_4);
    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, onGridUpdate: vi.fn() })
    );

    act(() => {
      result.current.start({});
    });
    await flush();

    act(() => {
      global.EventSource.sendMessage({ status: 'running', progress: 42, message: 'Filling grid…' });
    });

    expect(result.current.state).toBe('running');
    expect(result.current.progress).toBe(42);
    expect(result.current.message).toBe('Filling grid…');
  });

  it('3. complete + grid + success:true -> done, onGridUpdate final merge, success message', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-3' });
    const onGridUpdate = vi.fn();
    const grid = gridFromRows(WHITE_4);
    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, onGridUpdate })
    );

    act(() => {
      result.current.start({});
    });
    await flush();

    const cliGrid = [
      ['A', 'B', 'C', 'D'],
      ['E', 'F', 'G', 'H'],
      ['I', 'J', 'K', 'L'],
      ['M', 'N', 'O', 'P'],
    ];
    act(() => {
      global.EventSource.sendMessage({
        status: 'complete',
        data: { grid: cliGrid, success: true, slots_filled: 8, total_slots: 8 },
      });
    });

    expect(result.current.state).toBe('done');
    expect(result.current.message).toBe('Successfully filled 8/8 slots!');
    // Call 1 is Start's clear-red write; call 2 is the final merge.
    expect(onGridUpdate).toHaveBeenCalledTimes(2);
    const updater = onGridUpdate.mock.calls[1][0];
    const nextGrid = updater(grid);
    expect(nextGrid[0][0].letter).toBe('A');
    expect(nextGrid[3][3].letter).toBe('P');
  });

  it('4. complete + grid + success:false, partial fill -> done, "Partial: ..." message', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-4' });
    const onGridUpdate = vi.fn();
    const grid = gridFromRows(WHITE_4);
    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, onGridUpdate })
    );

    act(() => {
      result.current.start({});
    });
    await flush();

    const cliGrid = [
      ['A', 'B', '.', '.'],
      ['.', '.', '.', '.'],
      ['.', '.', '.', '.'],
      ['.', '.', '.', '.'],
    ];
    act(() => {
      global.EventSource.sendMessage({
        status: 'complete',
        data: {
          grid: cliGrid,
          success: false,
          slots_filled: 5,
          total_slots: 8,
          fill_percentage: 62,
          suggestions: [{ message: 'try a different wordlist' }],
        },
      });
    });

    expect(result.current.state).toBe('done');
    // Spec 0.2.6 section 2.3: `Partial: X/Y slots (P%)` exactly, no suggestion suffix.
    expect(result.current.message).toBe('Partial: 5/8 slots (62%)');
    // Start's clear-red write + the restore of the Start snapshot.
    expect(onGridUpdate).toHaveBeenCalledTimes(2);
    const restored = onGridUpdate.mock.calls[1][0](grid);
    expect(restored).toEqual(result.current.startSnapshot);
  });

  // 4b/4c guard main's fix, dropped when the inline App.jsx block was ported to
  // this hook: success:false with EVERY slot filled must not be reported as a
  // "Partial" fill with a lower-the-min-score suggestion. The CLI returns
  // success:false whenever entries are flagged problematic, even at 100% fill.
  it('4b. complete + success:false but all slots filled -> done, review message not "Partial"', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-4b' });
    const onGridUpdate = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate })
    );

    act(() => {
      result.current.start({});
    });
    await flush();

    act(() => {
      global.EventSource.sendMessage({
        status: 'complete',
        data: {
          grid: CLI_FULL_4,
          success: false,
          slots_filled: 8,
          total_slots: 8,
          fill_percentage: 100,
          problematic_slots_count: 2,
          suggestions: [{ message: 'try lowering the minimum score' }],
        },
      });
    });

    expect(result.current.state).toBe('done');
    expect(result.current.progress).toBe(100);
    expect(result.current.message).toBe(
      'Filled 8/8 slots — 2 entries may be invalid (use Verify Words to check)'
    );
    expect(result.current.message).not.toContain('Partial');
    expect(result.current.message).not.toContain('minimum score');
  });

  it('4c. complete + success:false, all slots filled, no problematic count -> review message', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-4c' });
    const onGridUpdate = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate })
    );

    act(() => {
      result.current.start({});
    });
    await flush();

    act(() => {
      global.EventSource.sendMessage({
        status: 'complete',
        data: {
          grid: CLI_FULL_4,
          success: false,
          slots_filled: 8,
          total_slots: 8,
          fill_percentage: 100,
        },
      });
    });

    expect(result.current.state).toBe('done');
    expect(result.current.message).toBe(
      'Filled 8/8 slots — some entries may need review (use Verify Words to check)'
    );
  });

  it('5. complete with NO data.data.grid -> failed, errorCard "No solution found"', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-5' });
    const onGridUpdate = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate })
    );

    act(() => {
      result.current.start({});
    });
    await flush();

    act(() => {
      global.EventSource.sendMessage({ status: 'complete' });
    });

    expect(result.current.state).toBe('failed');
    expect(result.current.errorCard).toEqual({ message: 'No solution found' });
    // Start's clear-red write + the restore of the Start snapshot; no merge without a result grid.
    expect(onGridUpdate).toHaveBeenCalledTimes(2);
    expect(onGridUpdate.mock.calls[1][0](gridFromRows(WHITE_4))).toEqual(result.current.startSnapshot);
  });

  it('6. error event -> failed + errorCard content from data.message', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-6' });
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate: vi.fn() })
    );

    act(() => {
      result.current.start({});
    });
    await flush();

    act(() => {
      global.EventSource.sendMessage({ status: 'error', message: 'Solver crashed' });
    });

    expect(result.current.state).toBe('failed');
    expect(result.current.errorCard).toEqual({ message: 'Solver crashed' });
  });

  it('6b. error event restores the Start snapshot (Start clear-red write + one restore)', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-6b' });
    const onGridUpdate = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate })
    );
    act(() => {
      result.current.start({});
    });
    await flush();
    act(() => {
      global.EventSource.sendMessage({ status: 'error', message: 'Solver crashed' });
    });
    expect(onGridUpdate).toHaveBeenCalledTimes(2);
    expect(onGridUpdate.mock.calls[1][0](gridFromRows(WHITE_4))).toEqual(result.current.startSnapshot);
  });

  it('7. cancel() -> api.cancelFill called + stream closed + cancelled', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-7' });
    const cancelFill = vi.spyOn(api, 'cancelFill').mockResolvedValue({});
    const closeSpy = vi.spyOn(global.EventSource.prototype, 'close');
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate: vi.fn() })
    );

    act(() => {
      result.current.start({});
    });
    await flush();
    expect(result.current.state).toBe('running');

    act(() => {
      result.current.cancel();
    });

    expect(result.current.state).toBe('cancelled');
    expect(result.current.message).toBe('Cancelled by user');
    expect(cancelFill).toHaveBeenCalledWith('task-7');
    expect(closeSpy).toHaveBeenCalled();
  });

  it('8. SSE status:"paused" -> paused (taskId retained), stream closed, no toast call', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-8' });
    const closeSpy = vi.spyOn(global.EventSource.prototype, 'close');
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate: vi.fn() })
    );

    act(() => {
      result.current.start({});
    });
    await flush();

    act(() => {
      global.EventSource.sendMessage({
        status: 'paused',
        progress: 55,
        message: 'Autofill paused - state saved',
      });
    });

    expect(result.current.state).toBe('paused');
    expect(result.current.taskId).toBe('task-8'); // retained, unlike done/failed/cancelled
    expect(closeSpy).toHaveBeenCalled();
    // The hook has no toast dependency at all — nothing to spy on; this is a
    // design property (no import of a toast module), not a runtime assertion.
  });

  it('9. reset() from each of done/failed/cancelled/paused -> idle, all fields cleared', async () => {
    async function toState(targetState) {
      vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'tid' });
      vi.spyOn(api, 'cancelFill').mockResolvedValue({});
      const { result } = renderHook(() =>
        useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate: vi.fn() })
      );
      act(() => {
        result.current.start({});
      });
      await flush();

      if (targetState === 'done') {
        act(() => {
          global.EventSource.sendMessage({
            status: 'complete',
            data: {
              grid: [
                ['A', '.', '.', '.'],
                ['.', '.', '.', '.'],
                ['.', '.', '.', '.'],
                ['.', '.', '.', '.'],
              ],
              success: true,
              slots_filled: 1,
              total_slots: 1,
            },
          });
        });
      } else if (targetState === 'failed') {
        act(() => {
          global.EventSource.sendMessage({ status: 'error', message: 'boom' });
        });
      } else if (targetState === 'cancelled') {
        act(() => {
          result.current.cancel();
        });
      } else if (targetState === 'paused') {
        act(() => {
          global.EventSource.sendMessage({ status: 'paused', progress: 10 });
        });
      }
      expect(result.current.state).toBe(targetState);

      act(() => {
        result.current.reset();
      });

      expect(result.current.state).toBe('idle');
      expect(result.current.taskId).toBeNull();
      expect(result.current.progress).toBe(0);
      expect(result.current.message).toBe('');
      expect(result.current.errorCard).toBeNull();

      vi.restoreAllMocks();
    }

    await toState('done');
    await toState('failed');
    await toState('cancelled');
    await toState('paused');
  });

  it('10. stray onEvent/onerror AFTER cancel()/reset() is a no-op (ref-discipline state-guard)', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-10' });
    vi.spyOn(api, 'cancelFill').mockResolvedValue({});
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate: vi.fn() })
    );

    act(() => {
      result.current.start({});
    });
    await flush();
    expect(result.current.state).toBe('running');

    act(() => {
      result.current.cancel();
    });
    expect(result.current.state).toBe('cancelled');

    // Stray EventSource onerror arrives after cancel() — must NOT flip to 'failed'.
    act(() => {
      global.EventSource.sendError();
    });
    expect(result.current.state).toBe('cancelled');

    // Stray SSE 'error' status event also must NOT flip to 'failed'.
    act(() => {
      global.EventSource.sendMessage({ status: 'error', message: 'late error' });
    });
    expect(result.current.state).toBe('cancelled');
    expect(result.current.errorCard).toBeNull();

    act(() => {
      result.current.reset();
    });
    expect(result.current.state).toBe('idle');

    // Stray event after reset() must also be a no-op.
    act(() => {
      global.EventSource.sendError();
    });
    expect(result.current.state).toBe('idle');
    act(() => {
      global.EventSource.sendMessage({ status: 'error', message: 'late again' });
    });
    expect(result.current.state).toBe('idle');
  });

  it('11. unmount while running closes the EventSource', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-11' });
    const closeSpy = vi.spyOn(global.EventSource.prototype, 'close');
    const { result, unmount } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate: vi.fn() })
    );

    act(() => {
      result.current.start({});
    });
    await flush();
    expect(result.current.state).toBe('running');

    unmount();

    expect(closeSpy).toHaveBeenCalled();
  });

  it('12. onGridUpdate merge never overwrites isThemeLocked cells (running-preview + done-final)', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-12' });
    const onGridUpdate = vi.fn();
    const grid = gridFromRows(WHITE_4);
    grid[0][0] = { ...grid[0][0], letter: 'Z', isThemeLocked: true };

    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, onGridUpdate })
    );

    act(() => {
      result.current.start({});
    });
    await flush();

    // Running-preview path: server tries to overwrite (0,0) with 'X'.
    const cliGridRunning = [
      ['X', '.', '.', '.'],
      ['.', '.', '.', '.'],
      ['.', '.', '.', '.'],
      ['.', '.', '.', '.'],
    ];
    act(() => {
      global.EventSource.sendMessage({
        status: 'running',
        progress: 20,
        data: { grid: cliGridRunning },
      });
    });
    let updater = onGridUpdate.mock.calls.at(-1)[0];
    let merged = updater(grid);
    expect(merged[0][0].letter).toBe('Z');
    expect(merged[0][0].isThemeLocked).toBe(true);

    // Done-final path: server tries to overwrite (0,0) with 'Y'.
    const cliGridDone = [
      ['Y', 'B', 'C', 'D'],
      ['E', 'F', 'G', 'H'],
      ['I', 'J', 'K', 'L'],
      ['M', 'N', 'O', 'P'],
    ];
    act(() => {
      global.EventSource.sendMessage({
        status: 'complete',
        data: { grid: cliGridDone, success: true, slots_filled: 16, total_slots: 16 },
      });
    });
    updater = onGridUpdate.mock.calls.at(-1)[0];
    merged = updater(grid);
    expect(merged[0][0].letter).toBe('Z'); // still theme-locked, still preserved
    expect(merged[1][1].letter).toBe('F'); // non-locked cells DO get the server fill
  });

  // Bonus (not in the brief's numbered list, added per advisor review): the
  // grid/gridSize ref-discipline claim itself — start() must read the LATEST
  // grid via ref, never a grid closed over at an earlier render.
  it('13. start() reads the latest grid via ref, not a stale closure from an earlier render', async () => {
    const startFill = vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-13' });
    const gridA = gridFromRows(WHITE_4);
    const gridB = gridFromRows(['AAAA', '....', '....', '....']);

    const { result, rerender } = renderHook(
      (props) => useAutofillMachine(props),
      { initialProps: { grid: gridA, gridSize: 4, onGridUpdate: vi.fn() } }
    );

    // Grid changes (e.g. a letter typed) AFTER mount, BEFORE start() fires.
    rerender({ grid: gridB, gridSize: 4, onGridUpdate: vi.fn() });

    act(() => {
      result.current.start({});
    });

    expect(startFill).toHaveBeenCalledWith(
      expect.objectContaining({ grid: toCliStrings(gridB) })
    );

    await flush(); // drain the pending startFill resolution inside act()
  });

  it('14. start() while submitting/running/paused is a no-op (re-entrancy guard, F3 fix)', async () => {
    const startFill = vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-14' });
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, onGridUpdate: vi.fn() })
    );

    // -- submitting: a second start() before the first resolves is a no-op.
    act(() => {
      result.current.start({});
    });
    expect(result.current.state).toBe('submitting');

    act(() => {
      result.current.start({});
    });
    expect(startFill).toHaveBeenCalledTimes(1);
    expect(result.current.state).toBe('submitting');

    await flush();
    expect(result.current.state).toBe('running');
    expect(result.current.taskId).toBe('task-14');

    // -- running: start() is a no-op, does not touch state/taskId.
    act(() => {
      result.current.start({});
    });
    expect(startFill).toHaveBeenCalledTimes(1);
    expect(result.current.state).toBe('running');
    expect(result.current.taskId).toBe('task-14');

    // -- paused: start() is a no-op too (guard is now idle-only, not just
    // submitting/running) — allowing it here would null the taskId and
    // orphan the paused backend state file.
    act(() => {
      global.EventSource.sendMessage({ status: 'paused', progress: 10 });
    });
    expect(result.current.state).toBe('paused');

    act(() => {
      result.current.start({});
    });
    expect(startFill).toHaveBeenCalledTimes(1);
    expect(result.current.state).toBe('paused');
    expect(result.current.taskId).toBe('task-14');
  });

  it('15. start() forwards themeList verbatim to api.startFill (owner-restored field, additive whitelist entry)', async () => {
    const startFill = vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 'task-15' });
    const grid = gridFromRows(WHITE_4);
    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, onGridUpdate: vi.fn() })
    );

    act(() => {
      result.current.start({ wordlists: ['comprehensive', 'custom/my_theme'], themeList: 'custom/my_theme' });
    });

    expect(startFill).toHaveBeenCalledWith(
      expect.objectContaining({ themeList: 'custom/my_theme' })
    );

    await flush();
  });
});

/** Grid with per-cell overrides: edits = { 'r,c': {...cellFields} }. */
function gridWith(rows, edits) {
  const g = gridFromRows(rows);
  for (const [k, v] of Object.entries(edits)) {
    const [r, c] = k.split(',').map(Number);
    g[r][c] = { ...g[r][c], ...v };
  }
  return g;
}

describe('useAutofillMachine Task 5.2: Start, snapshot, lock list, document id, running branch', () => {
  it('S1. start snapshots a red-free copy, sends locked_cells, clears red on the grid, calls onStart once, in order', async () => {
    const grid = gridWith(WHITE_4, {
      '0,0': { letter: 'A', isBlocked: true },
      '0,1': { letter: 'B', isAutofilled: true },
    });
    const startFill = vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-s1' });
    const onGridUpdate = vi.fn();
    const onStart = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, docId: 'doc-1', onGridUpdate, onStart, onToast: vi.fn() })
    );
    expect(result.current.startSnapshot).toBeNull();

    act(() => {
      result.current.start({}, 'doc-1');
    });

    expect(startFill).toHaveBeenCalledWith(expect.objectContaining({ locked_cells: [[0, 0]] }));
    const snap = result.current.startSnapshot;
    expect(snap).not.toBeNull();
    expect(snap[0][0].isBlocked).toBe(false);
    expect(snap[0][0]).not.toBe(grid[0][0]); // a full copy, every cell a new object
    expect(grid[0][0].isBlocked).toBe(true); // the input is untouched
    expect(startFill.mock.calls[0][0].grid).toEqual(toCliStrings(snap));

    expect(onGridUpdate).toHaveBeenCalledTimes(1);
    const cleared = onGridUpdate.mock.calls[0][0](grid);
    expect(cleared[0][0].isBlocked).toBe(false);
    expect(cleared[0][0].letter).toBe('A');

    expect(onStart).toHaveBeenCalledTimes(1);
    // Order: clear red, then onStart (token bump), then the request.
    expect(onGridUpdate.mock.invocationCallOrder[0]).toBeLessThan(onStart.mock.invocationCallOrder[0]);
    expect(onStart.mock.invocationCallOrder[0]).toBeLessThan(startFill.mock.invocationCallOrder[0]);

    await flush();
  });

  it('S2. every letter autofilled -> locked_cells is present and []', async () => {
    const edits = {};
    for (let r = 0; r < 4; r++) {
      for (let c = 0; c < 4; c++) edits[`${r},${c}`] = { letter: 'X', isAutofilled: true };
    }
    const grid = gridWith(WHITE_4, edits);
    const startFill = vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-s2' });
    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, docId: 'd', onGridUpdate: vi.fn(), onStart: vi.fn(), onToast: vi.fn() })
    );
    act(() => {
      result.current.start({}, 'd');
    });
    const req = startFill.mock.calls[0][0];
    expect(Object.prototype.hasOwnProperty.call(req, 'locked_cells')).toBe(true);
    expect(req.locked_cells).toEqual([]);
    await flush();
  });

  it('S3. start while submitting makes no second request and no second onStart', async () => {
    const startFill = vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-s3' });
    const onStart = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({
        grid: gridFromRows(WHITE_4), gridSize: 4, docId: 'd', onGridUpdate: vi.fn(), onStart, onToast: vi.fn(),
      })
    );
    act(() => {
      result.current.start({}, 'd');
    });
    act(() => {
      result.current.start({}, 'd');
    });
    expect(result.current.state).toBe('submitting');
    expect(startFill).toHaveBeenCalledTimes(1);
    expect(onStart).toHaveBeenCalledTimes(1);
    await flush();
  });

  it('S4. same document id: a running event with data.grid applies the merge', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-s4' });
    const grid = gridFromRows(WHITE_4);
    const onGridUpdate = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, docId: 'doc-1', onGridUpdate, onStart: vi.fn(), onToast: vi.fn() })
    );
    act(() => {
      result.current.start({}, 'doc-1');
    });
    await flush();
    onGridUpdate.mockClear();

    act(() => {
      global.EventSource.sendMessage({ status: 'running', progress: 10, data: { grid: CLI_FULL_4 } });
    });
    expect(onGridUpdate).toHaveBeenCalledTimes(1);
    expect(onGridUpdate.mock.calls[0][0](grid)).toEqual(mergeGridPreserveThemeLocked(grid, CLI_FULL_4));
  });

  it('S5. docId changed after Start: running merge, C4 red-mark and complete merge are all dropped', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-s5' });
    const grid = gridFromRows(WHITE_4);
    const onGridUpdate = vi.fn();
    const onToast = vi.fn();
    const { result, rerender } = renderHook((props) => useAutofillMachine(props), {
      initialProps: { grid, gridSize: 4, docId: 'doc-1', onGridUpdate, onStart: vi.fn(), onToast },
    });
    act(() => {
      result.current.start({}, 'doc-1');
    });
    await flush();
    rerender({ grid, gridSize: 4, docId: 'doc-2', onGridUpdate, onStart: vi.fn(), onToast });
    onGridUpdate.mockClear();

    act(() => {
      global.EventSource.sendMessage({ status: 'running', progress: 10, data: { grid: CLI_FULL_4 } });
    });
    expect(onGridUpdate).not.toHaveBeenCalled();

    act(() => {
      global.EventSource.sendMessage({
        status: 'running',
        progress: 20,
        data: { off_list_cells: [[2, 0]], warning: 'Typed words not in the selected word lists: QZX' },
      });
    });
    expect(onGridUpdate).not.toHaveBeenCalled();

    act(() => {
      global.EventSource.sendMessage({
        status: 'complete',
        data: { grid: CLI_FULL_4, success: true, slots_filled: 8, total_slots: 8 },
      });
    });
    expect(onGridUpdate).not.toHaveBeenCalled();
  });

  it('S6. C4 running event marks the off-list cells red, toasts the warning, run continues', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-s6' });
    const grid = gridFromRows(WHITE_4);
    const onGridUpdate = vi.fn();
    const onToast = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, docId: 'd', onGridUpdate, onStart: vi.fn(), onToast })
    );
    act(() => {
      result.current.start({}, 'd');
    });
    await flush();
    onGridUpdate.mockClear();

    const warning = 'Typed words not in the selected word lists: QZX';
    act(() => {
      global.EventSource.sendMessage({
        status: 'running',
        progress: 5,
        data: { off_list_cells: [[2, 0], [2, 1]], warning },
      });
    });
    expect(onGridUpdate).toHaveBeenCalledTimes(1);
    const marked = onGridUpdate.mock.calls[0][0](grid);
    expect(marked[2][0].isBlocked).toBe(true);
    expect(marked[2][1].isBlocked).toBe(true);
    expect(marked[2][2].isBlocked).toBeFalsy();
    expect(onToast).toHaveBeenCalledTimes(1);
    expect(onToast).toHaveBeenCalledWith({ kind: 'info', message: warning });
    expect(result.current.state).toBe('running');
  });

  it('S7. an empty off_list_cells list neither marks nor toasts', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-s7' });
    const onGridUpdate = vi.fn();
    const onToast = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, docId: 'd', onGridUpdate, onStart: vi.fn(), onToast })
    );
    act(() => {
      result.current.start({}, 'd');
    });
    await flush();
    onGridUpdate.mockClear();
    act(() => {
      global.EventSource.sendMessage({
        status: 'running',
        progress: 5,
        data: { off_list_cells: [], warning: 'w' },
      });
    });
    expect(onGridUpdate).not.toHaveBeenCalled();
    expect(onToast).not.toHaveBeenCalled();
  });

  it('S8. a C4 event without a warning marks red but does not toast', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-s8' });
    const onGridUpdate = vi.fn();
    const onToast = vi.fn();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid: gridFromRows(WHITE_4), gridSize: 4, docId: 'd', onGridUpdate, onStart: vi.fn(), onToast })
    );
    act(() => {
      result.current.start({}, 'd');
    });
    await flush();
    onGridUpdate.mockClear();
    act(() => {
      global.EventSource.sendMessage({ status: 'running', progress: 5, data: { off_list_cells: [[1, 1]] } });
    });
    expect(onGridUpdate).toHaveBeenCalledTimes(1);
    expect(onToast).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Task 5.3: terminal outcomes, restore, red cells, the Keep offers.
// A stateful harness applies every onGridUpdate updater to a real grid, so the
// rows assert the grid the user would see (restore lands first, red on top).
// ---------------------------------------------------------------------------

const CLI_PART_4 = [
  ['.', 'B', '.', '.'],
  ['.', '.', '.', '.'],
  ['.', '.', '.', '.'],
  ['.', '.', '.', '.'],
];
const CLI_USER_AT_00 = [
  ['U', '.', '.', '.'],
  ['.', '.', '.', '.'],
  ['.', '.', '.', '.'],
  ['.', '.', '.', '.'],
];

function userGrid() {
  return gridWith(WHITE_4, { '0,0': { letter: 'U' } });
}

/** Mounts the hook over a real grid state; start({}, 'doc-1') has been called and the run is `running`. */
async function runningMachine({ docId = 'doc-1', grid = userGrid() } = {}) {
  vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-53' });
  vi.spyOn(api, 'cancelFill').mockResolvedValue({});
  const hook = renderHook(
    (props) => {
      const [g, setG] = useState(grid);
      const m = useAutofillMachine({
        grid: g,
        gridSize: 4,
        docId: props.docId,
        onGridUpdate: setG,
        onStart: vi.fn(),
        onToast: vi.fn(),
      });
      return { ...m, grid: g, setGrid: setG };
    },
    { initialProps: { docId } }
  );
  act(() => {
    hook.result.current.start({}, 'doc-1');
  });
  await flush();
  expect(hook.result.current.state).toBe('running');
  return hook;
}

const send = (msg) =>
  act(() => {
    global.EventSource.sendMessage(msg);
  });
const complete = (data) => send({ status: 'complete', data });
const lettersOf = (g) => g.map((row) => row.map((c) => c.letter).join(''));
const redOf = (g) => {
  const out = [];
  g.forEach((row, r) => row.forEach((c, k) => c.isBlocked && out.push([r, k])));
  return out;
};

describe('useAutofillMachine Task 5.3: terminal outcomes (spec 0.2.6 section 2.3 table)', () => {
  it('row 1. success merges onto the current grid; the user letter stays; no offer', async () => {
    const { result } = await runningMachine();
    complete({ success: true, grid: CLI_FULL_4, slots_filled: 8, total_slots: 8 });
    expect(result.current.state).toBe('done');
    expect(result.current.message).toBe('Successfully filled 8/8 slots!');
    expect(result.current.offer).toBeNull();
    expect(result.current.grid[0][0].letter).toBe('U');
    expect(result.current.grid[0][0].isAutofilled).toBeFalsy();
    expect(result.current.grid[0][1].letter).toBe('B');
    expect(result.current.grid[0][1].isAutofilled).toBe(true);
  });

  it('row 2. every slot filled, success:false: snapshot restored, keepFill offer, counted message', async () => {
    const { result } = await runningMachine();
    complete({ success: false, grid: CLI_FULL_4, slots_filled: 8, total_slots: 8, problematic_slots_count: 2 });
    expect(result.current.state).toBe('done');
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.offer).toMatchObject({ kind: 'keepFill' });
    expect(result.current.message).toBe(
      'Filled 8/8 slots — 2 entries may be invalid (use Verify Words to check)'
    );
  });

  it('row 2b. as row 2 without problematic_slots_count: the no-count text (PD-5G)', async () => {
    const { result } = await runningMachine();
    complete({ success: false, grid: CLI_FULL_4, slots_filled: 8, total_slots: 8 });
    expect(result.current.offer).toMatchObject({ kind: 'keepFill' });
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.message).toBe(
      'Filled 8/8 slots — some entries may need review (use Verify Words to check)'
    );
  });

  it('row 2c. counts say 8/8 but the grid has empty cells: the grid decides -> partial offer', async () => {
    const { result } = await runningMachine();
    complete({
      success: false, grid: CLI_PART_4, slots_filled: 8, total_slots: 8, fill_percentage: 100,
    });
    expect(result.current.state).toBe('done');
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.offer).toEqual({ kind: 'keepPartialFill', slotsFilled: 8, totalSlots: 8 });
    expect(result.current.message).toBe('Partial: 8/8 slots (100%)');
  });

  it('row 3. partial: snapshot restored, keepPartialFill offer with counts, suggestion suffix dropped', async () => {
    const { result } = await runningMachine();
    complete({
      success: false, grid: CLI_PART_4, slots_filled: 5, total_slots: 8, fill_percentage: 62,
      stuck_cells: [], suggestions: [{ message: 'x' }],
    });
    expect(result.current.state).toBe('done');
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.offer).toEqual({ kind: 'keepPartialFill', slotsFilled: 5, totalSlots: 8 });
    expect(result.current.message).toBe('Partial: 5/8 slots (62%)');
  });

  it('row 4. stuck_cells non-empty: stuck message, those cells red on the restored grid', async () => {
    const { result } = await runningMachine();
    complete({
      success: false, grid: CLI_PART_4, slots_filled: 5, total_slots: 8, fill_percentage: 62,
      stuck_cells: [[0, 0]], suggestions: [{ message: 'x' }],
    });
    expect(result.current.message).toBe('Autofill could not fill around the highlighted letters.');
    expect(result.current.grid[0][0].isBlocked).toBe(true);
    expect(redOf(result.current.grid)).toEqual([[0, 0]]);
    expect(lettersOf(result.current.grid)).toEqual(lettersOf(result.current.startSnapshot));
    expect(result.current.offer).toEqual({ kind: 'keepPartialFill', slotsFilled: 5, totalSlots: 8 });
  });

  it('row 4 (sources). red is the union of blocked_cells, stuck_cells and off_list_cells', async () => {
    const { result } = await runningMachine();
    complete({
      success: false, grid: CLI_PART_4, slots_filled: 5, total_slots: 8, fill_percentage: 62,
      blocked_cells: [[1, 1]], stuck_cells: [[0, 0]], off_list_cells: [[2, 2]],
    });
    expect(redOf(result.current.grid)).toEqual([[0, 0], [1, 1], [2, 2]]);
  });

  it('row 5. blocked no_word_fits: failed + error card, snapshot restored, red cells, no offer (PD-5C)', async () => {
    const { result } = await runningMachine();
    complete({
      success: false, blocked: true, reason: 'no_word_fits', blocked_cells: [[0, 0]],
      blocked_slots: [{ row: 0, col: 0, direction: 'across', length: 4, pattern: 'U???' }],
      off_list_cells: [], stuck_cells: [], grid: CLI_USER_AT_00,
    });
    expect(result.current.state).toBe('failed');
    expect(result.current.errorCard).toEqual({ message: 'No word fits the highlighted letters.' });
    expect(result.current.grid[0][0].isBlocked).toBe(true);
    expect(lettersOf(result.current.grid)).toEqual(lettersOf(result.current.startSnapshot));
    expect(result.current.offer).toBeNull();
  });

  it('row 5 (B3). blocked is checked before success: blocked:true wins over success:true', async () => {
    const { result } = await runningMachine();
    complete({
      success: true, blocked: true, reason: 'no_word_fits', blocked_cells: [[0, 0]],
      blocked_slots: [], grid: CLI_FULL_4, slots_filled: 8, total_slots: 8,
    });
    expect(result.current.state).toBe('failed');
    expect(result.current.errorCard).toEqual({ message: 'No word fits the highlighted letters.' });
    expect(lettersOf(result.current.grid)).toEqual(lettersOf(result.current.startSnapshot));
  });

  it('row 6. blocked no_word_of_length: length message, no red', async () => {
    const { result } = await runningMachine();
    complete({
      success: false, blocked: true, reason: 'no_word_of_length', blocked_cells: [],
      blocked_slots: [{ row: 0, col: 0, direction: 'across', length: 4, pattern: 'U???' }],
      off_list_cells: [], stuck_cells: [], grid: CLI_USER_AT_00,
    });
    expect(result.current.state).toBe('failed');
    expect(result.current.errorCard).toEqual({ message: 'The selected word lists have no words of length 4.' });
    expect(redOf(result.current.grid)).toEqual([]);
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.offer).toBeNull();
  });

  it('row 6 (PD-5F). several lengths: distinct, ascending, joined by ", "', async () => {
    const { result } = await runningMachine();
    const slot = (length) => ({ row: 0, col: 0, direction: 'across', length, pattern: '?' });
    complete({
      success: false, blocked: true, reason: 'no_word_of_length', blocked_cells: [],
      blocked_slots: [slot(5), slot(4), slot(5), slot(10)], grid: CLI_USER_AT_00,
    });
    // Numeric ascending (10 after 5), duplicates removed.
    expect(result.current.errorCard).toEqual({
      message: 'The selected word lists have no words of length 4, 5, 10.',
    });
  });

  it('row 7. complete without a grid: failed, snapshot restored, no offer', async () => {
    const { result } = await runningMachine();
    send({ status: 'running', progress: 5, data: { grid: CLI_PART_4 } });
    send({ status: 'complete' });
    expect(result.current.state).toBe('failed');
    expect(result.current.errorCard).toEqual({ message: 'No solution found' });
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.offer).toBeNull();
  });

  it('row 8. progress grid filled a cell, then cancel: restored, keepPartialFill without counts', async () => {
    const { result } = await runningMachine();
    send({ status: 'running', progress: 5, data: { grid: CLI_PART_4 } });
    expect(result.current.grid[0][1].letter).toBe('B'); // the running merge landed
    act(() => {
      result.current.cancel();
    });
    expect(result.current.state).toBe('cancelled');
    expect(result.current.message).toBe('Cancelled by user');
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.offer).toEqual({ kind: 'keepPartialFill', slotsFilled: null, totalSlots: null });
  });

  it('row 8 (predicate). a progress grid that fills no cell makes no offer', async () => {
    const { result } = await runningMachine();
    send({ status: 'running', progress: 5, data: { grid: CLI_USER_AT_00 } });
    act(() => {
      result.current.cancel();
    });
    expect(result.current.offer).toBeNull();
  });

  it('row 8b. cancelled with no progress grid: restored, no offer', async () => {
    const { result } = await runningMachine();
    act(() => {
      result.current.cancel();
    });
    expect(result.current.state).toBe('cancelled');
    expect(result.current.message).toBe('Cancelled by user');
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.offer).toBeNull();
  });

  it('row 9. paused with data.grid: paused, taskId kept, restored, offer, fixed text', async () => {
    const { result } = await runningMachine();
    send({ status: 'paused', progress: 30, data: { grid: CLI_PART_4 } });
    expect(result.current.state).toBe('paused');
    expect(result.current.taskId).toBe('t-53');
    expect(result.current.message).toBe('Autofill was paused outside the app.');
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.offer).toEqual({ kind: 'keepPartialFill', slotsFilled: null, totalSlots: null });
  });

  it('row 10. error after a progress grid: failed with the error text, restored, offer', async () => {
    const { result } = await runningMachine();
    send({ status: 'running', progress: 5, data: { grid: CLI_PART_4 } });
    send({ status: 'error', message: 'CLI Error (code 1): boom' });
    expect(result.current.state).toBe('failed');
    expect(result.current.errorCard).toEqual({ message: 'CLI Error (code 1): boom' });
    expect(result.current.grid).toEqual(result.current.startSnapshot);
    expect(result.current.offer).toEqual({ kind: 'keepPartialFill', slotsFilled: null, totalSlots: null });
  });

  // Row 11 (lost contact, `Lost contact with the autofill run.`) is driven by Task 5.4's watchdog;
  // its test is written there against this task's shared terminal routine.

  it('row 12. success with off_list_cells: merged, those cells red, user letter intact', async () => {
    const { result } = await runningMachine();
    complete({
      success: true, grid: CLI_FULL_4, slots_filled: 8, total_slots: 8, off_list_cells: [[0, 0]],
    });
    expect(result.current.state).toBe('done');
    expect(result.current.grid[0][0].isBlocked).toBe(true);
    expect(result.current.grid[0][0].letter).toBe('U');
    expect(result.current.grid[0][1].letter).toBe('B');
    expect(result.current.offer).toBeNull();
  });

  it('order. restore and red are ONE updater: red lands on the restored grid', async () => {
    vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't-ord' });
    const onGridUpdate = vi.fn();
    const grid = userGrid();
    const { result } = renderHook(() =>
      useAutofillMachine({ grid, gridSize: 4, docId: 'doc-1', onGridUpdate, onStart: vi.fn(), onToast: vi.fn() })
    );
    act(() => {
      result.current.start({}, 'doc-1');
    });
    await flush();
    onGridUpdate.mockClear();
    complete({
      success: false, grid: CLI_PART_4, slots_filled: 5, total_slots: 8, fill_percentage: 62,
      stuck_cells: [[0, 0]],
    });
    expect(onGridUpdate).toHaveBeenCalledTimes(1);
    // Applied to a grid that has diverged (a merged cell), the single updater still yields snapshot + red.
    const dirty = mergeGridPreserveThemeLocked(grid, CLI_PART_4);
    const out = onGridUpdate.mock.calls[0][0](dirty);
    expect(lettersOf(out)).toEqual(lettersOf(result.current.startSnapshot));
    expect(out[0][0].isBlocked).toBe(true);
  });

  it('PD-5D. docId changed since Start: restore and red are skipped, state still terminal, offer null', async () => {
    const { result, rerender } = await runningMachine();
    rerender({ docId: 'doc-2' });
    const before = result.current.grid;
    complete({
      success: false, grid: CLI_PART_4, slots_filled: 5, total_slots: 8, fill_percentage: 62,
      stuck_cells: [[0, 0]],
    });
    expect(result.current.state).toBe('done');
    expect(result.current.grid).toBe(before);
    expect(result.current.offer).toBeNull();
  });
});

describe('useAutofillMachine Task 5.3: keepFill, reset, discardRun', () => {
  const partial = {
    success: false, grid: CLI_PART_4, slots_filled: 5, total_slots: 8, fill_percentage: 62,
  };

  it('keepFill(docId) merges the last grid onto the current grid and clears the offer; state unchanged', async () => {
    const { result } = await runningMachine();
    complete(partial);
    expect(result.current.grid[0][1].letter).toBe('');
    act(() => {
      result.current.keepFill('doc-1');
    });
    expect(result.current.grid[0][1].letter).toBe('B');
    expect(result.current.grid[0][1].isAutofilled).toBe(true);
    expect(result.current.grid[0][0].letter).toBe('U');
    expect(result.current.offer).toBeNull();
    expect(result.current.state).toBe('done');
  });

  it('keepFill uses the LAST grid received on any event (a paused grid)', async () => {
    const { result } = await runningMachine();
    send({ status: 'running', progress: 1, data: { grid: CLI_USER_AT_00 } });
    send({ status: 'paused', progress: 2, data: { grid: CLI_PART_4 } });
    act(() => {
      result.current.keepFill('doc-1');
    });
    expect(result.current.grid[0][1].letter).toBe('B');
  });

  it('a letter typed into an empty cell after the run survives keepFill', async () => {
    const { result } = await runningMachine();
    complete(partial);
    // The user types 'Q' into (0,1), which the kept grid would fill with 'B'.
    act(() => {
      result.current.setGrid((g) =>
        g.map((row, r) => row.map((c, k) => (r === 0 && k === 1 ? { ...c, letter: 'Q' } : c)))
      );
    });
    act(() => {
      result.current.keepFill('doc-1');
    });
    expect(result.current.grid[0][1].letter).toBe('Q');
    expect(result.current.grid[0][2].letter).toBe(''); // sanity: merge ran, only (0,1) is user-held
    expect(result.current.offer).toBeNull();
  });

  it('docId changed: offer is null and keepFill is a no-op', async () => {
    const { result, rerender } = await runningMachine();
    complete(partial);
    expect(result.current.offer).not.toBeNull();
    rerender({ docId: 'doc-2' });
    expect(result.current.offer).toBeNull();
    const before = result.current.grid;
    act(() => {
      result.current.keepFill('doc-2');
    });
    expect(result.current.grid).toBe(before);
    // And back on the original document the offer returns (derived, not consumed).
    rerender({ docId: 'doc-1' });
    expect(result.current.offer).not.toBeNull();
  });

  it('keepFill with a docId other than the start id is a no-op', async () => {
    const { result } = await runningMachine();
    complete(partial);
    const before = result.current.grid;
    act(() => {
      result.current.keepFill('doc-9');
    });
    expect(result.current.grid).toBe(before);
    expect(result.current.offer).not.toBeNull();
  });

  it('keepFill with no offer showing is a no-op', async () => {
    const { result } = await runningMachine();
    complete({ success: true, grid: CLI_FULL_4, slots_filled: 8, total_slots: 8 });
    const before = result.current.grid;
    act(() => {
      result.current.keepFill('doc-1');
    });
    expect(result.current.grid).toBe(before);
  });

  it('reset(): idle, offer null, startSnapshot kept', async () => {
    const { result } = await runningMachine();
    complete(partial);
    const snap = result.current.startSnapshot;
    act(() => {
      result.current.reset();
    });
    expect(result.current.state).toBe('idle');
    expect(result.current.offer).toBeNull();
    expect(result.current.startSnapshot).toBe(snap);
    expect(snap).not.toBeNull();
  });

  it('discardRun(): idle, offer null, startSnapshot null, and keepFill can no longer apply', async () => {
    const { result } = await runningMachine();
    complete(partial);
    act(() => {
      result.current.discardRun();
    });
    expect(result.current.state).toBe('idle');
    expect(result.current.taskId).toBeNull();
    expect(result.current.progress).toBe(0);
    expect(result.current.message).toBe('');
    expect(result.current.errorCard).toBeNull();
    expect(result.current.offer).toBeNull();
    expect(result.current.startSnapshot).toBeNull();
    const before = result.current.grid;
    act(() => {
      result.current.keepFill('doc-1');
    });
    expect(result.current.grid).toBe(before);
  });

  it('discardRun() while running (or submitting) changes nothing', async () => {
    const { result } = await runningMachine();
    expect(LIVE_STATES.has(result.current.state)).toBe(true);
    const snap = result.current.startSnapshot;
    act(() => {
      result.current.discardRun();
    });
    expect(result.current.state).toBe('running');
    expect(result.current.taskId).toBe('t-53');
    expect(result.current.startSnapshot).toBe(snap);
  });
});
