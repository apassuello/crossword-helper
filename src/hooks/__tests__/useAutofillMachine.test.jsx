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
import { renderHook, act } from '@testing-library/react';
import { useAutofillMachine, mergeGridPreserveThemeLocked } from '../useAutofillMachine';
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
    expect(result.current.message).toBe(
      'Partial: 5/8 slots (62%) - try a different wordlist'
    );
    // Start's clear-red write + the final merge.
    expect(onGridUpdate).toHaveBeenCalledTimes(2);
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
          grid: [
            ['A', 'B', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
          ],
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
          grid: [
            ['A', 'B', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
            ['.', '.', '.', '.'],
          ],
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
    // Only Start's clear-red write; no merge without a result grid.
    expect(onGridUpdate).toHaveBeenCalledTimes(1);
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

const CLI_FULL_4 = [
  ['A', 'B', 'C', 'D'],
  ['E', 'F', 'G', 'H'],
  ['I', 'J', 'K', 'L'],
  ['M', 'N', 'O', 'P'],
];

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
