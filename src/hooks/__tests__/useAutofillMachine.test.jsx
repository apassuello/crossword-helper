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
import { useAutofillMachine } from '../useAutofillMachine';
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
    expect(onGridUpdate).toHaveBeenCalledTimes(1);
    const updater = onGridUpdate.mock.calls[0][0];
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
    expect(onGridUpdate).toHaveBeenCalledTimes(1);
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
    expect(onGridUpdate).not.toHaveBeenCalled();
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
