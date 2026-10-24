// novice-readiness spec 0.2.7 §3.2: the Grid panel hosts the grid-level controls.
// This task lands the "Black square" toggle (§3.3 (G7)); New grid and Open saved
// are added by later tasks.
import { canToggleBlack } from '../../lib/gridEdits';

export default function GridPanel({
  grid,
  selectedCell,
  symmetryEnabled,
  editingPaused,
  onToggleBlack,
}) {
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
    </div>
  );
}
