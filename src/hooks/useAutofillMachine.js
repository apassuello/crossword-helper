/**
 * useAutofillMachine — the F3 autofill lifecycle hook (Task 11A).
 *
 * Owns the autofill state machine (start -> SSE progress -> done/failed/
 * cancelled/paused) that today lives inline in App.jsx's handleAutofill/
 * handleCancelAutofill/handleResetAutofill (App.jsx:219-400ish). This hook
 * PORTS that logic without redesigning it; App wiring + deletion of the old
 * inline code happens in a later sub-task (11C), not here.
 *
 * Contract (binding — Tasks 16/17/18 extend this hook, they do not rewrite
 * it, per `.superpowers/sdd/task-11A-brief.md`):
 *
 *   useAutofillMachine({ grid, gridSize, onGridUpdate })
 *   -> { state, taskId, progress, message, errorCard, start, cancel, reset }
 *
 * FLAT return (no nested `context`), per the Phase-3 contract in
 * `.superpowers/sdd/phase2-scoping-2026-07-14.md` "Task 11".
 *
 * `state` is exactly one of:
 *   'idle' | 'submitting' | 'running' | 'done' | 'failed' | 'cancelled' | 'paused'
 * There is deliberately NO separate `warning` state: the old inline code's
 * `warning` (partial fill > 0) and `error` (zero-fill complete) branches both
 * collapse into `done`; the message text alone carries the partial-fill
 * nuance ("Partial: X/Y slots (P%)" vs "Successfully filled X/Y slots!").
 *
 * Ref-discipline (the Task 8C / commit 59b4959 lesson applies directly
 * here): `grid`/`gridSize`/`onGridUpdate` are threaded via refs refreshed
 * every render (mirrors useSaveMachine's `docRef` / useNumbering's
 * `gridRef`), so `start()` and in-flight SSE handlers always read the
 * LATEST values, never a stale closure.
 *
 * The state-guard is the same pattern applied to the machine's OWN state:
 * `stateRef` is updated SYNCHRONOUSLY the instant a transition happens
 * (inside `transition()`, before/alongside the React `setState` call) — not
 * only via the eventual re-render. The SSE `onEvent`/`onError` callbacks
 * check `stateRef.current === 'running'` before doing anything, so a stray
 * event that arrives after `cancel()`/`reset()` already moved the machine on
 * is a guaranteed no-op, rather than a race that could flip `cancelled`
 * back to `failed`.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { toCliStrings } from '../api/gridCodec';

const RESETTABLE_STATES = new Set(['done', 'failed', 'cancelled', 'paused']);

function initialSnapshot() {
  return {
    state: 'idle',
    taskId: null,
    progress: 0,
    message: '',
    errorCard: null,
  };
}

/**
 * Map a CLI-string result grid onto the canonical grid, never overwriting a
 * theme-locked cell. Identical logic to today's inline mapping in
 * App.jsx:253-269 — ported verbatim (including the non-uppercased letter
 * passthrough), not redesigned.
 *
 * TODO: `gridCodec.js` is nominally the only CLI-string <-> canonical-grid
 * decoder in the app; this function duplicates a slice of that decoding
 * inline instead of calling into it. Left as-is per the brief (port, don't
 * redesign) — noting it here for whoever eventually consolidates.
 */
function mergeGridPreserveThemeLocked(prevGrid, cliGrid) {
  return prevGrid.map((row, r) =>
    row.map((cell, c) => {
      if (cell.isThemeLocked) return cell;
      const cliCell = cliGrid[r][c];
      if (cliCell === '#') {
        return { ...cell, isBlack: true };
      } else if (cliCell === '.' || cliCell === '') {
        return { ...cell, letter: '' };
      }
      return { ...cell, letter: cliCell };
    })
  );
}

/**
 * @param {{grid: object[][], gridSize: number, onGridUpdate: (updater: (prevGrid: object[][]) => object[][]) => void}} params
 */
export function useAutofillMachine({ grid, gridSize, onGridUpdate }) {
  const [snapshot, setSnapshot] = useState(initialSnapshot);

  // Latest props, read at fire time (mirrors useSaveMachine's docRef).
  const gridRef = useRef(grid);
  const gridSizeRef = useRef(gridSize);
  const onGridUpdateRef = useRef(onGridUpdate);
  gridRef.current = grid;
  gridSizeRef.current = gridSize;
  onGridUpdateRef.current = onGridUpdate;

  // Synchronous state-guard — see the module doc comment above. Updated the
  // instant a transition happens, never lagging behind React's batched
  // setState, so an in-flight SSE callback always sees the CURRENT state.
  const stateRef = useRef(snapshot.state);
  const taskIdRef = useRef(null);
  const streamRef = useRef(null); // current { close() } from api.openProgress
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      // Unmount while running: close the EventSource. The old inline code
      // never did this (App never unmounted the panel) — this is a genuine
      // addition for a proper hook, not a port.
      if (streamRef.current) {
        streamRef.current.close();
        streamRef.current = null;
      }
    };
  }, []);

  const closeStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
  }, []);

  const transition = useCallback((patch) => {
    if ('state' in patch) stateRef.current = patch.state;
    if ('taskId' in patch) taskIdRef.current = patch.taskId;
    setSnapshot((prev) => ({ ...prev, ...patch }));
  }, []);

  const handleEvent = useCallback(
    (data) => {
      if (!mountedRef.current) return;
      // Ref-discipline guard: a stray event after cancel()/reset() already
      // moved the machine off 'running' must be a no-op.
      if (stateRef.current !== 'running') return;

      const status = (data && data.status) || 'running';

      if (status === 'running') {
        transition({
          progress: data.progress || 0,
          message: data.message || 'Processing…',
        });
        if (data.data && data.data.grid) {
          const cliGrid = data.data.grid;
          onGridUpdateRef.current((prevGrid) => mergeGridPreserveThemeLocked(prevGrid, cliGrid));
        }
        return;
      }

      if (status === 'complete') {
        closeStream();
        if (data.data && data.data.grid) {
          const cliGrid = data.data.grid;
          onGridUpdateRef.current((prevGrid) => mergeGridPreserveThemeLocked(prevGrid, cliGrid));

          if (data.data.success) {
            transition({
              state: 'done',
              progress: 100,
              message: `Successfully filled ${data.data.slots_filled}/${data.data.total_slots} slots!`,
              errorCard: null,
              taskId: null,
            });
          } else {
            const fillPct = data.data.fill_percentage || 0;
            let message = `Partial: ${data.data.slots_filled}/${data.data.total_slots} slots (${fillPct}%)`;
            if (data.data.suggestions && data.data.suggestions.length > 0) {
              message += ` - ${data.data.suggestions[0].message}`;
            }
            transition({ state: 'done', progress: fillPct, message, errorCard: null, taskId: null });
          }
        } else {
          transition({
            state: 'failed',
            progress: 0,
            errorCard: { message: 'No solution found' },
            taskId: null,
          });
        }
        return;
      }

      if (status === 'paused') {
        closeStream();
        // taskId intentionally NOT included in the patch — retained.
        transition({
          state: 'paused',
          progress: data.progress || 0,
          message: data.message || 'Autofill paused - state saved',
          errorCard: null,
        });
        return;
      }

      if (status === 'error') {
        closeStream();
        transition({
          state: 'failed',
          errorCard: { message: data.message || 'Autofill failed' },
          taskId: null,
        });
      }
    },
    [transition, closeStream]
  );

  const handleStreamError = useCallback(() => {
    if (!mountedRef.current) return;
    // Same ref-discipline guard as handleEvent.
    if (stateRef.current !== 'running') return;
    closeStream();
    transition({ state: 'failed', errorCard: { message: 'Connection error' }, taskId: null });
  }, [transition, closeStream]);

  /**
   * Enter `running` on `taskId` and open its progress stream. Factored out
   * of `start()` because Task 16's two-step resume re-enters `running` on a
   * DIFFERENT taskId via this identical logic — inlining it in `start()`
   * would force that task to duplicate this or refactor it out later.
   *
   * Structural invariant: ALWAYS close any existing stream FIRST, before
   * opening the new one. This can't be left to callers to remember — the
   * state-guard in `handleEvent`/`handleStreamError` only checks
   * `stateRef.current === 'running'`, not stream identity, so if two live
   * streams ever existed simultaneously, a stale one's events would still
   * pass the guard and get misapplied to the new task. Closing here, inside
   * the single entry point to `running`, makes "at most one live stream"
   * hold structurally rather than merely by caller convention.
   */
  const enterRunning = useCallback(
    (taskId) => {
      closeStream();
      transition({ state: 'running', taskId, errorCard: null });
      const stream = api.openProgress(taskId, {
        onEvent: handleEvent,
        onError: handleStreamError,
      });
      streamRef.current = stream;
    },
    [closeStream, transition, handleEvent, handleStreamError]
  );

  const start = useCallback(
    (options = {}) => {
      // Re-entrancy guard, gated to `idle` only — the brief's transition
      // table is exhaustive and lists `idle --start()--> submitting` as the
      // only start edge. Notably this also blocks start() from `paused`:
      // allowing it there would null out taskId and silently orphan the
      // paused backend state file, destroying the handle Task 16's resume()
      // needs. Callers reach `idle` from any terminal/paused state via
      // reset() first.
      if (stateRef.current !== 'idle') return;

      closeStream();
      transition({
        state: 'submitting',
        taskId: null,
        progress: 0,
        message: 'Starting autofill…',
        errorCard: null,
      });

      api
        .startFill({
          size: gridSizeRef.current,
          grid: toCliStrings(gridRef.current),
          wordlists: options.wordlists,
          timeout: options.timeout,
          min_score: options.minScore,
          algorithm: options.algorithm,
          theme_entries: options.themeEntries || {},
          adaptive_mode: options.adaptiveMode,
          max_adaptations: options.maxAdaptations,
          partial_fill: options.partialFill,
          cleanup: options.cleanup,
          resumeTaskId: options.resumeTaskId,
        })
        .then(
          (res) => {
            if (!mountedRef.current) return;
            enterRunning(res.task_id);
          },
          (error) => {
            if (!mountedRef.current) return;
            transition({ state: 'failed', errorCard: { message: error.message } });
          }
        );
    },
    [closeStream, transition, enterRunning]
  );

  const cancel = useCallback(() => {
    if (stateRef.current !== 'running') return;
    const taskId = taskIdRef.current;
    closeStream();
    transition({ state: 'cancelled', message: 'Cancelled by user', errorCard: null, taskId: null });
    if (taskId) {
      api.cancelFill(taskId).catch((err) => console.warn('Failed to cancel autofill task:', err));
    }
  }, [closeStream, transition]);

  const reset = useCallback(() => {
    if (!RESETTABLE_STATES.has(stateRef.current)) return;
    closeStream(); // defensively close any lingering stream
    transition({ state: 'idle', taskId: null, progress: 0, message: '', errorCard: null });
  }, [closeStream, transition]);

  return {
    state: snapshot.state,
    taskId: snapshot.taskId,
    progress: snapshot.progress,
    message: snapshot.message,
    errorCard: snapshot.errorCard,
    start,
    cancel,
    reset,
  };
}

export default useAutofillMachine;
