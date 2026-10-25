/**
 * useUndoHistory (novice-readiness spec 0.2.18 §3.9 (U1)): React wiring over the pure
 * `lib/history`. History is recorded at the App's user-action handlers, never inside `setGrid`,
 * because autofill, numbering and Verify write through it too.
 *
 * `record(before)` and `commitBatch()` do not compare at call time: a handler's `setGrid` is a
 * functional update that has not rendered yet. They queue the "before" content and the steps are
 * decided in an effect after the next render: each queued "before" is compared with the next
 * queued one (the content after its edit), the last with the rendered grid's content (never a
 * reference compare: `writeLetter` always returns a new grid). Two edits before one render are
 * therefore two steps, provided the second `record` was handed the grid the first edit produced
 * (App's `editGrid` does that); two identical "before"s collapse into one step.
 *
 * A batch (Apply All) is one step: `beginBatch()` takes the "before" content and returns a token
 * (a monotonically increasing id); every `record` while it is open is folded into it;
 * `undo`/`redo` do nothing; `commitBatch(token)` decides the one step, and only for the batch that
 * token opened. A missing, stale or cleared token is ignored, so a slow run cannot close a later
 * run's batch (PR #90 Greptile P1). `clear()` ends the batch without recording it, which makes
 * every token issued before it stale.
 *
 * `beginBatch()` over a batch that is still open first commits that orphan, then opens a new one.
 * That holds because only a closed panel's in-flight run can leave a batch open: the Apply All
 * button is disabled while `applyingAll` and only one panel mounts, so a second `beginBatch`
 * can only come from a remounted panel while the old run is still waiting on a request.
 * `batchOpen` exposes the open state so the Undo and Redo buttons grey while it lasts (PR #90
 * Greptile P2).
 *
 * Undo and redo are grid writers under D1 and return early while `editingPausedRef.current`.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  snapshotContent,
  restoreContent,
  emptyHistory,
  pushStep,
  undoStep,
  redoStep,
  canUndo as historyCanUndo,
  canRedo as historyCanRedo,
} from '../lib/history';
import { contentSigOf } from '../lib/contentSig';

export function useUndoHistory({ grid, gridSize, setGrid, editingPausedRef }) {
  const [, setVersion] = useState(0);
  const bump = () => setVersion((v) => v + 1);

  const historyRef = useRef(emptyHistory());
  const gridRef = useRef(grid);
  const gridSizeRef = useRef(gridSize);
  gridRef.current = grid;
  gridSizeRef.current = gridSize;
  const batchRef = useRef(null); // { before, token } while an Apply All batch is open
  const tokenSeqRef = useRef(0); // last batch token issued
  const pendingRef = useRef([]); // queued "before" snapshots, decided after the next render

  const record = useCallback((before) => {
    if (batchRef.current || !before) return; // folded into the open batch
    pendingRef.current.push(snapshotContent(before, gridSizeRef.current));
    bump();
  }, []);

  const beginBatch = useCallback(() => {
    if (!gridRef.current) return undefined;
    if (batchRef.current) pendingRef.current.push(batchRef.current.before); // commit the orphan
    const token = ++tokenSeqRef.current;
    batchRef.current = { before: snapshotContent(gridRef.current, gridSizeRef.current), token };
    bump(); // batchOpen is read from the ref at render
    return token;
  }, []);

  const commitBatch = useCallback((token) => {
    if (!batchRef.current || token !== batchRef.current.token) return;
    pendingRef.current.push(batchRef.current.before);
    batchRef.current = null;
    bump(); // an effect after the next render sees every write the batch queued
  }, []);

  const clear = useCallback(() => {
    batchRef.current = null;
    pendingRef.current = [];
    historyRef.current = emptyHistory();
    bump();
  }, []);

  useEffect(() => {
    const queue = pendingRef.current;
    if (queue.length === 0 || !grid) return;
    pendingRef.current = [];
    const renderedSig = contentSigOf(gridSize, grid);
    let next = historyRef.current;
    queue.forEach((before, i) => {
      if (before.size !== gridSize) return;
      const afterSig = i + 1 < queue.length ? queue[i + 1].sig : renderedSig;
      if (before.sig !== afterSig) next = pushStep(next, before);
    });
    if (next === historyRef.current) return;
    historyRef.current = next;
    bump();
  });

  const undo = useCallback(() => {
    if (editingPausedRef.current || batchRef.current || !gridRef.current) return;
    const out = undoStep(historyRef.current, snapshotContent(gridRef.current, gridSizeRef.current));
    if (!out || out.snapshot.size !== gridSizeRef.current) return;
    historyRef.current = out.history;
    setGrid((prev) => restoreContent(prev, out.snapshot));
    bump();
  }, [editingPausedRef, setGrid]);

  const redo = useCallback(() => {
    if (editingPausedRef.current || batchRef.current || !gridRef.current) return;
    const out = redoStep(historyRef.current, snapshotContent(gridRef.current, gridSizeRef.current));
    if (!out || out.snapshot.size !== gridSizeRef.current) return;
    historyRef.current = out.history;
    setGrid((prev) => restoreContent(prev, out.snapshot));
    bump();
  }, [editingPausedRef, setGrid]);

  return {
    record,
    beginBatch,
    commitBatch,
    undo,
    redo,
    clear,
    canUndo: historyCanUndo(historyRef.current),
    canRedo: historyCanRedo(historyRef.current),
    batchOpen: batchRef.current !== null,
  };
}

export default useUndoHistory;
