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
 *   useAutofillMachine({ grid, gridSize, docId, onGridUpdate, onStart, onToast })
 *   -> { state, taskId, progress, message, errorCard, offer, startSnapshot,
 *        cancelPending, start, cancel, reset, keepFill, discardRun, adoptForkedDocId }
 *   start(options = {}, docId): `docId` is the document id at Start; it is stored
 *   with the snapshot, and every merge and red-marking write is skipped when the
 *   hook's CURRENT `docId` param differs from it (novice-readiness spec 0.2.6
 *   section 2.3 (M1)). Every unfinished run (a failed or partial fill, a block, cancel,
 *   pause, an error event) goes through ONE routine, `finishRun`, that restores the Start
 *   snapshot, marks red cells on it and sets the Keep offer (spec 0.2.6 section 2.3).
 *   `offer` is `null` whenever the hook's current `docId` differs from Start's.
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
 * event that arrives after a terminal transition (or `reset()`) already moved
 * the machine on is a guaranteed no-op, rather than a race that could flip
 * `cancelled` back to `failed`. `cancel()` itself does not move the machine:
 * it posts cancelFill and the state stays `running` until the 200 (or a
 * terminal event) arrives (novice-readiness spec 0.2.7 §2.4 (C7)).
 *
 * `cancelPending` is React state (a ref change does not re-render, and the panel disables
 * Cancel on it): true from cancel()'s post, and from an early Cancel recorded in `submitting`,
 * until the 200, a rejection, or any transition to a non-live state. `cancelPendingRef` stays
 * for the synchronous guards. The state is true while either the ref or an early Cancel
 * (`earlyCancelRef`, set in `submitting` before the ref is) is pending.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { toCliStrings } from '../api/gridCodec';

// novice-readiness spec 0.2.7 §2.4 (B4, PD-5H): a Start whose 202 has not arrived after this long fails.
export const SUBMIT_TIMEOUT_MS = 30000;
// novice-readiness spec 0.2.7 §2.4 (B4, P4): the watchdog fires this long after the run's own ceiling.
export const WATCHDOG_GRACE_MS = 30000;

const LOST_CONTACT = 'Lost contact with the autofill run.';

/**
 * novice-readiness spec 0.2.7 §2.4 (C7, PD-3-KILL): the route's text for a child killed by a signal. An `error` event with
 * this text while a cancel is pending is the cancel taking effect, not a failure.
 */
export function isKillError(message) {
  return typeof message === 'string' && message.startsWith('CLI Error (code -');
}

const RESETTABLE_STATES = new Set(['done', 'failed', 'cancelled', 'paused']);

// States in which a run owns the grid: no writer but the machine's own onGridUpdate
// may run (novice-readiness spec 0.2.6 section 2.3, D1). App derives `editingPaused` from it.
export const LIVE_STATES = new Set(['submitting', 'running']);

function initialSnapshot() {
  return {
    state: 'idle',
    taskId: null,
    progress: 0,
    message: '',
    errorCard: null,
    offer: null,
    startSnapshot: null,
    cancelPending: false,
  };
}

// Spec 0.2.6 section 2.3 (PD-5C, ruled by the owner 2026-10-24): a blocked run ends `failed`
// (the error card), grid restored, red cells shown. The state value lives here only, so a
// later re-ruling is a one-value change.
const BLOCKED_STATE = 'failed';

// PD-5F: one message; the distinct slot lengths ascending, joined by ", ".
function blockedMessage(d) {
  if (d.reason === 'no_word_of_length') {
    const lengths = [...new Set((d.blocked_slots || []).map((s) => s.length))].sort((a, b) => a - b);
    return `The selected word lists have no words of length ${lengths.join(', ')}.`;
  }
  return 'No word fits the highlighted letters.';
}

// Red cells of a terminal event: blocked, stuck and off-list cells, each [] when absent.
function redCellsOf(d) {
  return [...(d.blocked_cells || []), ...(d.stuck_cells || []), ...(d.off_list_cells || [])];
}

/**
 * Merge a CLI-string result grid into the CURRENT canonical grid
 * (novice-readiness spec 0.2.6 §2.3 (G12), §3.7). A cell is writable iff it is
 * not theme-locked and is either an empty white cell or already autofilled; a
 * user's letter is never changed. Writable cells take the CLI value:
 *   letter -> {letter, isAutofilled: true} (passed through, not uppercased)
 *   '.' / '' -> {letter: '', isAutofilled: false}
 *   '#' -> {isBlack: true, letter: '', isAutofilled: false}
 * A non-writable cell is returned as the same object. `isBlocked` and
 * `isError` are never changed.
 *
 * TODO: `gridCodec.js` is nominally the only CLI-string <-> canonical-grid
 * decoder in the app; this function duplicates a slice of that decoding
 * inline instead of calling into it. Noting it here for whoever eventually
 * consolidates.
 */
export function mergeGridPreserveThemeLocked(currentGrid, cliGrid) {
  return currentGrid.map((row, r) =>
    row.map((cell, c) => {
      const writable =
        !cell.isThemeLocked && !cell.isBlack && (cell.letter === '' || cell.isAutofilled);
      if (!writable) return cell;
      const cliCell = cliGrid[r][c];
      if (cliCell === '#') {
        return { ...cell, isBlack: true, letter: '', isAutofilled: false };
      }
      if (cliCell === '.' || cliCell === '') {
        return { ...cell, letter: '', isAutofilled: false };
      }
      return { ...cell, letter: cliCell, isAutofilled: true };
    })
  );
}

/** [row, col] of every white lettered cell that is theme-locked or not autofilled (§2.3 Lock list). */
export function lockedCellsOf(grid) {
  const out = [];
  grid.forEach((row, r) =>
    row.forEach((cell, c) => {
      if (!cell.isBlack && cell.letter !== '' && (cell.isThemeLocked || !cell.isAutofilled)) {
        out.push([r, c]);
      }
    })
  );
  return out;
}

/** Listed [r, c] cells become new objects with isBlocked true; the rest keep their object (§2.3 Red cells). */
export function markBlocked(grid, cells) {
  const keys = new Set(cells.map(([r, c]) => `${r},${c}`));
  return grid.map((row, r) =>
    row.map((cell, c) => (keys.has(`${r},${c}`) ? { ...cell, isBlocked: true } : cell))
  );
}

/** Every cell a new object with isBlocked false. */
export function clearBlocked(grid) {
  return grid.map((row) => row.map((cell) => ({ ...cell, isBlocked: false })));
}

/** True iff no CLI cell is '.' or '' ('#' counts as filled). */
export function resultGridIsFull(cliGrid) {
  return cliGrid.every((row) => row.every((v) => v !== '.' && v !== ''));
}

/** True iff the CLI holds a letter where the snapshot cell is white, empty and not theme-locked (§2.3 table). */
export function fillsAnyCell(snapshotGrid, cliGrid) {
  return snapshotGrid.some((row, r) =>
    row.some((cell, c) => {
      const v = cliGrid[r][c];
      return (
        v !== '#' && v !== '.' && v !== '' && !cell.isBlack && cell.letter === '' && !cell.isThemeLocked
      );
    })
  );
}

/**
 * @param {{grid: object[][], gridSize: number, docId: string, onGridUpdate: (updater: (prevGrid: object[][]) => object[][]) => void, onStart?: () => void, onToast?: (t: {kind: string, message: string}) => void, onRunCommitted?: (before: object[][]) => void}} params
 */
export function useAutofillMachine({ grid, gridSize, docId, onGridUpdate, onStart, onToast, onRunCommitted }) {
  const [snapshot, setSnapshot] = useState(initialSnapshot);

  // Latest props, read at fire time (mirrors useSaveMachine's docRef).
  const gridRef = useRef(grid);
  const gridSizeRef = useRef(gridSize);
  const onGridUpdateRef = useRef(onGridUpdate);
  gridRef.current = grid;
  gridSizeRef.current = gridSize;
  onGridUpdateRef.current = onGridUpdate;
  // The CURRENT document id, compared at event time against the id stored at Start.
  const docIdRef = useRef(docId);
  docIdRef.current = docId;
  const onStartRef = useRef(onStart);
  const onToastRef = useRef(onToast);
  onStartRef.current = onStart;
  onToastRef.current = onToast;
  // Undo wiring (novice-readiness spec 0.2.18 §3.9, "What one step is"): told when a run's result was
  // committed to the grid, with the grid to restore on undo.
  const onRunCommittedRef = useRef(onRunCommitted);
  onRunCommittedRef.current = onRunCommitted;
  const startDocIdRef = useRef(null); // document id at the accepted start()
  const startSnapshotRef = useRef(null); // the red-free Start copy that restore writes back
  const lastGridRef = useRef(null); // last data.grid received on any event of the current run
  const offerRef = useRef(null); // synchronous mirror of the stored offer, for keepFill

  // Synchronous state-guard — see the module doc comment above. Updated the
  // instant a transition happens, never lagging behind React's batched
  // setState, so an in-flight SSE callback always sees the CURRENT state.
  const stateRef = useRef(snapshot.state);
  const taskIdRef = useRef(null);
  const streamRef = useRef(null); // current { close() } from api.openProgress
  const mountedRef = useRef(true);
  // §2.4 (B4): Start time, the submit timer, the watchdog, the run token that ties a late
  // 202 to its own request, and the two cancel flags.
  const startTimeRef = useRef(0);
  const submitTimerRef = useRef(null);
  const watchdogRef = useRef(null);
  const runIdRef = useRef(0);
  const cancelPendingRef = useRef(false); // C7: cancelFill posted, 200 not yet seen
  const earlyCancelRef = useRef(false); // PD-5I: Cancel pressed while `submitting`

  const clearTimers = () => {
    if (submitTimerRef.current !== null) {
      clearTimeout(submitTimerRef.current);
      submitTimerRef.current = null;
    }
    if (watchdogRef.current !== null) {
      clearTimeout(watchdogRef.current);
      watchdogRef.current = null;
    }
  };

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      clearTimers();
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
    if ('offer' in patch) offerRef.current = patch.offer;
    // §2.4 (B4): every transition to a non-live state clears the timers and any cancel flag.
    if ('state' in patch && !LIVE_STATES.has(patch.state)) {
      clearTimers();
      cancelPendingRef.current = false;
      earlyCancelRef.current = false;
      patch = { ...patch, cancelPending: false };
    }
    setSnapshot((prev) => ({ ...prev, ...patch }));
  }, []);

  // novice-readiness spec 0.2.6 section 2.3 (M1): a merge or red-marking write is
  // skipped when the document was replaced since Start.
  const sameDocument = () => docIdRef.current === startDocIdRef.current;

  /**
   * The single terminal routine for an unfinished run (novice-readiness spec 0.2.6 §2.3
   * outcome table; the submit timeout, watchdog, lost stream, cancel and a rejected start all end here). Restore the Start snapshot
   * and mark red cells in ONE updater, so red lands on the restored grid ("Order on a
   * terminal outcome"); both writes are skipped when the document changed since Start
   * (PD-5D). `offer` is the Keep offer or null. For `failed` the text goes in
   * `errorCard.message`, otherwise in `message`.
   */
  const finishRun = useCallback(
    ({ state, text, red = [], offer = null, extra = {} }) => {
      closeStream();
      const snap = startSnapshotRef.current;
      if (snap && sameDocument()) {
        onGridUpdateRef.current(() => markBlocked(snap, red));
      }
      transition({
        state,
        offer,
        ...(state === 'failed' ? { errorCard: { message: text } } : { message: text, errorCard: null }),
        ...extra,
      });
    },
    [transition, closeStream]
  );

  /** Offer for cancelled / paused / error: only if a progress grid filled at least one cell (§2.3 table). */
  const progressOffer = () =>
    lastGridRef.current && startSnapshotRef.current && fillsAnyCell(startSnapshotRef.current, lastGridRef.current)
      ? { kind: 'keepPartialFill', slotsFilled: null, totalSlots: null }
      : null;

  /** Fire-and-forget api.cancelFill: a rejection is swallowed (nothing can act on it). */
  const bestEffortCancel = (taskId) => {
    if (!taskId) return;
    api.cancelFill(taskId).catch((e) => console.warn('Failed to cancel autofill task:', e));
  };

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
          lastGridRef.current = cliGrid;
          if (sameDocument()) {
            onGridUpdateRef.current((prevGrid) => mergeGridPreserveThemeLocked(prevGrid, cliGrid));
          }
        }
        // Case 2 (spec 0.2.6 section 2.3 Red cells, C4): off-list typed words are
        // marked red and the run continues.
        const offList = data.data && data.data.off_list_cells;
        if (Array.isArray(offList) && offList.length > 0 && sameDocument()) {
          onGridUpdateRef.current((prevGrid) => markBlocked(prevGrid, offList));
          if (typeof data.data.warning === 'string' && onToastRef.current) {
            onToastRef.current({ kind: 'info', message: data.data.warning });
          }
        }
        return;
      }

      if (status === 'complete') {
        const d = data.data;
        // Spec 0.2.6 §2.3 (B3): a blocked run arrives as `complete`; check it FIRST, before
        // success or the grid.
        if (d && d.blocked === true) {
          if (d.grid) lastGridRef.current = d.grid;
          finishRun({
            state: BLOCKED_STATE,
            text: blockedMessage(d),
            red: redCellsOf(d),
            extra: { progress: 0, taskId: null },
          });
          return;
        }
        if (d && d.grid) {
          const cliGrid = d.grid;
          lastGridRef.current = cliGrid;
          const red = redCellsOf(d);

          if (d.success) {
            closeStream();
            if (sameDocument()) {
              onGridUpdateRef.current((prevGrid) =>
                markBlocked(mergeGridPreserveThemeLocked(prevGrid, cliGrid), red)
              );
              // One undo step whose snapshot is the Start snapshot (§3.9); no second copy is taken.
              onRunCommittedRef.current?.(startSnapshotRef.current);
            }
            transition({
              state: 'done',
              progress: 100,
              message: `Successfully filled ${d.slots_filled}/${d.total_slots} slots!`,
              errorCard: null,
              offer: null,
              taskId: null,
            });
            return;
          }

          // Spec 0.2.6 §2.3 outcome table. "Every slot filled" is decided by the result grid
          // (no empty white cell), not by the slot counts.
          const fillPct = d.fill_percentage || 0;
          if (resultGridIsFull(cliGrid)) {
            const problematicCount = d.problematic_slots_count || 0;
            // PD-5G: the no-count variant stays beside the counted text.
            const text =
              problematicCount > 0
                ? `Filled ${d.slots_filled}/${d.total_slots} slots — ${problematicCount} entries may be invalid (use Verify Words to check)`
                : `Filled ${d.slots_filled}/${d.total_slots} slots — some entries may need review (use Verify Words to check)`;
            finishRun({
              state: 'done',
              text,
              red,
              offer: { kind: 'keepFill', slotsFilled: null, totalSlots: null },
              extra: { progress: 100, taskId: null },
            });
          } else {
            const stuck = Array.isArray(d.stuck_cells) && d.stuck_cells.length > 0;
            finishRun({
              state: 'done',
              text: stuck
                ? 'Autofill could not fill around the highlighted letters.'
                : `Partial: ${d.slots_filled}/${d.total_slots} slots (${fillPct}%)`,
              red,
              offer: { kind: 'keepPartialFill', slotsFilled: d.slots_filled, totalSlots: d.total_slots },
              extra: { progress: fillPct, taskId: null },
            });
          }
        } else {
          finishRun({ state: 'failed', text: 'No solution found', extra: { progress: 0, taskId: null } });
        }
        return;
      }

      if (status === 'paused') {
        if (data.data && data.data.grid) lastGridRef.current = data.data.grid;
        // taskId intentionally NOT included in the patch — retained.
        finishRun({
          state: 'paused',
          text: 'Autofill was paused outside the app.',
          offer: progressOffer(),
          extra: { progress: data.progress || 0 },
        });
        return;
      }

      if (status === 'error') {
        // §2.4 (C7): with a cancel pending, a kill's error text is the cancel taking effect.
        if (cancelPendingRef.current && isKillError(data.message)) {
          finishRun({
            state: 'cancelled',
            text: 'Cancelled by user',
            offer: progressOffer(),
            extra: { taskId: null },
          });
          return;
        }
        finishRun({
          state: 'failed',
          text: data.message || 'Autofill failed',
          offer: progressOffer(),
          extra: { taskId: null },
        });
      }
    },
    [transition, closeStream, finishRun]
  );

  const handleStreamError = useCallback(() => {
    if (!mountedRef.current) return;
    // Same ref-discipline guard as handleEvent.
    if (stateRef.current !== 'running') return;
    // novice-readiness spec 0.2.7 §2.4 (C8): the stream is gone (EventSource would reconnect, so finishRun closes it); the run
    // may still be alive server-side, so best-effort cancel it.
    bestEffortCancel(taskIdRef.current);
    finishRun({
      state: 'failed',
      text: LOST_CONTACT,
      offer: progressOffer(),
      extra: { taskId: null },
    });
  }, [finishRun]);

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
    (taskId, ceilingSeconds) => {
      closeStream();
      clearTimers(); // the submit timer ends with the 202
      transition({ state: 'running', taskId, errorCard: null });
      // §2.4 (B4, P4): keyed to Start, not to this 202's arrival.
      if (typeof ceilingSeconds === 'number') {
        const delay = Math.max(
          0,
          startTimeRef.current + ceilingSeconds * 1000 + WATCHDOG_GRACE_MS - Date.now()
        );
        watchdogRef.current = setTimeout(() => {
          watchdogRef.current = null;
          if (stateRef.current !== 'running' || taskIdRef.current !== taskId) return;
          bestEffortCancel(taskId);
          finishRun({
            state: 'failed',
            text: LOST_CONTACT,
            offer: progressOffer(),
            extra: { taskId: null },
          });
        }, delay);
      }
      const stream = api.openProgress(taskId, {
        onEvent: handleEvent,
        onError: handleStreamError,
      });
      streamRef.current = stream;
    },
    [closeStream, transition, handleEvent, handleStreamError, finishRun]
  );

  /**
   * novice-readiness spec 0.2.7 §2.4 (C7): Cancel in `running` posts cancelFill and keeps the stream open; the 200 ends the
   * run as `cancelled`, any rejection means the cancel is no longer pending and the machine keeps
   * waiting on the stream (404, PD-5J). In `submitting` it is only recorded (PD-5I): the 202
   * handler replays it once the task id is known.
   */
  const cancel = useCallback(() => {
    if (stateRef.current === 'submitting') {
      earlyCancelRef.current = true;
      setSnapshot((prev) => ({ ...prev, cancelPending: true }));
      return;
    }
    if (stateRef.current !== 'running' || cancelPendingRef.current) return;
    const taskId = taskIdRef.current;
    if (!taskId) return;
    cancelPendingRef.current = true;
    setSnapshot((prev) => ({ ...prev, cancelPending: true }));
    api.cancelFill(taskId).then(
      () => {
        if (!mountedRef.current) return;
        if (stateRef.current !== 'running' || taskIdRef.current !== taskId) return;
        finishRun({
          state: 'cancelled',
          text: 'Cancelled by user',
          offer: progressOffer(),
          extra: { taskId: null },
        });
      },
      (e) => {
        if (taskIdRef.current === taskId) {
          cancelPendingRef.current = false;
          if (mountedRef.current) setSnapshot((prev) => ({ ...prev, cancelPending: false }));
        }
        if (!e || e.status !== 404) console.warn('Failed to cancel autofill task:', e);
      }
    );
  }, [finishRun]);

  const start = useCallback(
    (options = {}, startDocId) => {
      // Re-entrancy guard, gated to `idle` only — the brief's transition
      // table is exhaustive and lists `idle --start()--> submitting` as the
      // only start edge. Notably this also blocks start() from `paused`:
      // allowing it there would null out taskId and silently orphan the
      // paused backend state file, destroying the handle Task 16's resume()
      // needs. Callers reach `idle` from any terminal/paused state via
      // reset() first.
      if (stateRef.current !== 'idle') return;

      closeStream();
      clearTimers();
      cancelPendingRef.current = false;
      earlyCancelRef.current = false;
      const runId = ++runIdRef.current;
      startTimeRef.current = Date.now();

      // The snapshot is a red-free full copy of the grid at Start; the lock list
      // is computed from it. Any retained last grid from a previous run is dropped.
      const startGrid = clearBlocked(gridRef.current);
      startDocIdRef.current = startDocId;
      startSnapshotRef.current = startGrid;
      lastGridRef.current = null;
      transition({
        state: 'submitting',
        taskId: null,
        progress: 0,
        message: 'Starting autofill…',
        errorCard: null,
        offer: null,
        startSnapshot: startGrid,
        cancelPending: false,
      });
      // Start clears all red on the live grid (spec 0.2.6 section 2.3 Red cells).
      onGridUpdateRef.current((prev) => clearBlocked(prev));
      // Bumps useNumbering's token so an in-flight reconcile cannot land mid-run.
      if (onStartRef.current) onStartRef.current();

      // §2.4 (PD-5H): a 202 that never comes ends the run; a 202 arriving later is cancelled.
      submitTimerRef.current = setTimeout(() => {
        submitTimerRef.current = null;
        if (stateRef.current !== 'submitting' || runIdRef.current !== runId) return;
        finishRun({ state: 'failed', text: LOST_CONTACT, extra: { taskId: null } });
      }, SUBMIT_TIMEOUT_MS);

      api
        .startFill({
          size: gridSizeRef.current,
          grid: toCliStrings(startGrid),
          // Always present, [] included (spec 0.2.6 section 2.3 Lock list, M3).
          locked_cells: lockedCellsOf(startGrid),
          wordlists: options.wordlists,
          timeout: options.timeout,
          min_score: options.minScore,
          algorithm: options.algorithm,
          theme_entries: options.themeEntries || {},
          adaptive_mode: options.adaptiveMode,
          max_adaptations: options.maxAdaptations,
          partial_fill: options.partialFill,
          cleanup: options.cleanup,
          // Owner-restored (F3 follow-up): the designated priority-theme
          // custom wordlist. Field name is NOT snake_cased — the backend
          // reads it verbatim as `themeList` (backend/api/routes.py:470).
          themeList: options.themeList,
          resumeTaskId: options.resumeTaskId,
        })
        .then(
          (res) => {
            if (!mountedRef.current) return;
            if (stateRef.current !== 'submitting' || runIdRef.current !== runId) {
              bestEffortCancel(res && res.task_id); // late 202: ignored, its task cancelled
              return;
            }
            const early = earlyCancelRef.current;
            enterRunning(res.task_id, res.ceiling_seconds);
            if (early) cancel(); // PD-5I: replay the recorded Cancel on the now-known task
          },
          (error) => {
            if (!mountedRef.current) return;
            if (stateRef.current !== 'submitting' || runIdRef.current !== runId) return;
            finishRun({
              state: 'failed',
              text: error.message || `Fill failed to start (${error.code})`,
            });
          }
        );
    },
    [closeStream, transition, enterRunning, finishRun, cancel]
  );

  const reset = useCallback(() => {
    if (!RESETTABLE_STATES.has(stateRef.current)) return;
    closeStream(); // defensively close any lingering stream
    // Keeps startSnapshot (and the last grid): only the offer is dropped.
    transition({ state: 'idle', taskId: null, progress: 0, message: '', errorCard: null, offer: null });
  }, [closeStream, transition]);

  /**
   * Apply the last received result or progress grid through the same merge, against the
   * grid as it is now, so letters typed after the run stay (spec 0.2.6 §2.3 "Keep partial
   * fill"). A no-op unless an offer is showing and `forDocId` is the Start document.
   */
  const keepFill = useCallback(
    (forDocId) => {
      if (!offerRef.current || !lastGridRef.current) return;
      if (!sameDocument() || forDocId !== startDocIdRef.current) return;
      const lastGrid = lastGridRef.current;
      // One undo step whose snapshot is the grid as it is when clicked (§3.9): the user may have
      // edited or undone since the run ended.
      onRunCommittedRef.current?.(gridRef.current);
      onGridUpdateRef.current((prev) => mergeGridPreserveThemeLocked(prev, lastGrid));
      transition({ offer: null });
    },
    [transition]
  );

  /**
   * A save fork mints a new id for the SAME document (novice-readiness spec 0.2.8 §2.3 (F2)).
   * Replace the stored Start id only when it is `oldId`; otherwise a no-op, so a replaced
   * document (New grid, Open saved, import) still reads as a different one. App's `setDocId`
   * commits a render later, and `docIdRef` follows the param only at render, so the current-id
   * ref is advanced here too: an event arriving in that window (a terminal `complete` or error
   * included) must read as the same document, not be dropped.
   */
  const adoptForkedDocId = useCallback((oldId, newId) => {
    if (startDocIdRef.current !== oldId) return;
    startDocIdRef.current = newId;
    docIdRef.current = newId;
  }, []);

  /** New grid / Open saved: drop the run's retained snapshot and offer (spec 0.2.6 §3.2). No-op while live. */
  const discardRun = useCallback(() => {
    if (LIVE_STATES.has(stateRef.current)) return;
    closeStream();
    lastGridRef.current = null;
    startSnapshotRef.current = null;
    transition({
      state: 'idle',
      taskId: null,
      progress: 0,
      message: '',
      errorCard: null,
      offer: null,
      startSnapshot: null,
    });
  }, [closeStream, transition]);

  // Offered only while the document id App passes still matches Start's.
  const offer = snapshot.offer && docId === startDocIdRef.current ? snapshot.offer : null;

  return {
    state: snapshot.state,
    taskId: snapshot.taskId,
    progress: snapshot.progress,
    message: snapshot.message,
    errorCard: snapshot.errorCard,
    offer,
    startSnapshot: snapshot.startSnapshot,
    cancelPending: snapshot.cancelPending,
    start,
    cancel,
    reset,
    keepFill,
    discardRun,
    adoptForkedDocId,
  };
}

export default useAutofillMachine;
