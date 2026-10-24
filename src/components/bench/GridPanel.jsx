// novice-readiness spec 0.2.7 §3.2: the Grid panel hosts the grid-level controls.
// It holds the "Black square" toggle (§3.3 (G7)) and "New grid" (§3.2 (#55)); Open
// saved is added by a later task.
import { useState } from 'react';
import { canToggleBlack, gridHasContent } from '../../lib/gridEdits';
import InlineConfirm from './InlineConfirm';

const NEW_GRID_SIZES = [11, 15, 21];

export default function GridPanel({
  grid,
  selectedCell,
  symmetryEnabled,
  editingPaused,
  onToggleBlack,
  onNewGrid,
}) {
  // The size awaiting confirmation; local, so it is dropped when the panel unmounts.
  const [pendingSize, setPendingSize] = useState(null);
  const hasSelection = Boolean(selectedCell) && Boolean(grid);
  const { row, col } = selectedCell || {};
  const allowed =
    hasSelection && canToggleBlack(grid, row, col, symmetryEnabled);
  const disabled = !allowed || editingPaused;
  const pressed = hasSelection ? Boolean(grid[row]?.[col]?.isBlack) : false;

  return (
    <div className="xw-insp-section xw-grid-panel">
      <h3>Grid</h3>
      <div className="xw-grid-panel-actions">
        <button
          type="button"
          className="xw-ghost-btn"
          aria-pressed={pressed}
          disabled={disabled}
          onClick={() => onToggleBlack(row, col)}
        >
          Black square
        </button>
      </div>
      <h4 className="xw-grid-panel-sub">New grid</h4>
      <div className="xw-grid-panel-actions">
        {NEW_GRID_SIZES.map((size) => (
          <button
            key={size}
            type="button"
            className="xw-ghost-btn"
            disabled={editingPaused}
            onClick={() => {
              if (gridHasContent(grid)) setPendingSize(size);
              else onNewGrid(size);
            }}
          >
            {`${size}\u00d7${size}`}
          </button>
        ))}
      </div>
      {pendingSize !== null && !editingPaused && (
        <InlineConfirm
          message="Replace the current grid? Unsaved changes are lost."
          confirmLabel="Replace"
          onConfirm={() => {
            const size = pendingSize;
            setPendingSize(null);
            onNewGrid(size);
          }}
          onCancel={() => setPendingSize(null)}
        />
      )}
    </div>
  );
}
