/**
 * Pure undo/redo history of grid content snapshots (novice-readiness spec §3.9 (U1),
 * "What a step holds" and "Restoring"). No React; every function returns new values.
 *
 * Coupling: a snapshot holds exactly the fields `contentSigOf` in `App.jsx` reads (size and each
 * cell's letter, isBlack, isThemeLocked, isAutofilled), so restoring a snapshot reproduces the
 * content signature and an undo back to the saved content makes the document clean (§3.9).
 */

export const HISTORY_LIMIT = 100;

export function snapshotContent(grid, gridSize) {
  return {
    size: gridSize,
    cells: grid.map((row) =>
      row.map((c) => ({
        letter: c.letter,
        isBlack: c.isBlack,
        isThemeLocked: c.isThemeLocked,
        isAutofilled: c.isAutofilled === true,
      }))
    ),
  };
}

export function restoreContent(grid, snapshot) {
  return grid.map((row, r) =>
    row.map((c, col) => {
      const s = snapshot.cells[r][col];
      return {
        ...c,
        letter: s.letter,
        isBlack: s.isBlack,
        isThemeLocked: s.isThemeLocked,
        isAutofilled: s.isAutofilled,
        isError: false,
        isBlocked: false,
      };
    })
  );
}

export function emptyHistory() {
  return { undo: [], redo: [] };
}

export function pushStep(history, snapshot) {
  return { undo: [...history.undo, snapshot].slice(-HISTORY_LIMIT), redo: [] };
}

export function undoStep(history, currentSnapshot) {
  if (history.undo.length === 0) return null;
  const snapshot = history.undo[history.undo.length - 1];
  return {
    history: {
      undo: history.undo.slice(0, -1),
      redo: [...history.redo, currentSnapshot].slice(-HISTORY_LIMIT),
    },
    snapshot,
  };
}

export function redoStep(history, currentSnapshot) {
  if (history.redo.length === 0) return null;
  const snapshot = history.redo[history.redo.length - 1];
  return {
    history: {
      undo: [...history.undo, currentSnapshot].slice(-HISTORY_LIMIT),
      redo: history.redo.slice(0, -1),
    },
    snapshot,
  };
}

export const canUndo = (history) => history.undo.length > 0;
export const canRedo = (history) => history.redo.length > 0;
