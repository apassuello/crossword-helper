/**
 * useUndoHistory (novice-readiness spec 0.2.11 §3.9 (U1)): React wiring over the pure
 * `lib/history`. History is recorded at the App's user-action handlers, never inside `setGrid`,
 * because autofill, numbering and Verify write through it too.
 *
 * `record(before)` and `commitBatch()` do not compare at call time: a handler's `setGrid` is a
 * functional update that has not rendered yet. They park the "before" content and the step is
 * decided in an effect after the next render, by comparing that content with
 * the rendered grid's content (never a reference compare: `writeLetter` always returns a new grid).
 *
 * A batch (Apply All) is one step: `beginBatch()` takes the "before" content; every `record`
 * while it is open is folded into it; `undo`/`redo` do nothing; `commitBatch()` decides the one
 * step; `clear()` ends the batch without recording it.
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

export function useUndoHistory({ grid, gridSize, setGrid, editingPausedRef }) {
  const [, setVersion] = useState(0);
  const bump = () => setVersion((v) => v + 1);

  const historyRef = useRef(emptyHistory());
  const gridRef = useRef(grid);
  const gridSizeRef = useRef(gridSize);
  gridRef.current = grid;
  gridSizeRef.current = gridSize;
  const batchRef = useRef(null); // { before } while an Apply All batch is open
  const pendingRef = useRef(null); // the "before" content whose step is decided after the next render

  const record = useCallback((before) => {
    if (batchRef.current || !before) return; // folded into the open batch
    pendingRef.current = snapshotContent(before, gridSizeRef.current);
    bump();
  }, []);

  const beginBatch = useCallback(() => {
    if (batchRef.current || !gridRef.current) return;
    batchRef.current = { before: snapshotContent(gridRef.current, gridSizeRef.current) };
  }, []);

  const commitBatch = useCallback(() => {
    if (!batchRef.current) return;
    pendingRef.current = batchRef.current.before;
    batchRef.current = null;
    bump(); // an effect after the next render sees every write the batch queued
  }, []);

  const clear = useCallback(() => {
    batchRef.current = null;
    pendingRef.current = null;
    historyRef.current = emptyHistory();
    bump();
  }, []);

  useEffect(() => {
    const before = pendingRef.current;
    if (!before || !grid) return;
    pendingRef.current = null;
    if (before.size !== gridSize) return;
    // `snapshotContent` holds exactly the fields `contentSigOf` (App.jsx) reads, so equal JSON is an
    // equal content signature; App is not imported here because it imports this module.
    if (JSON.stringify(before) === JSON.stringify(snapshotContent(grid, gridSize))) return;
    historyRef.current = pushStep(historyRef.current, before);
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
  };
}

export default useUndoHistory;
