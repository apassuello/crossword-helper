// novice-readiness spec 0.2.7 §3.2: the Grid panel hosts the grid-level controls.
// It holds the "Black square" toggle (§3.3 (G7)), "New grid" (§3.2 (#55)) and "Open saved"
// (§3.4), whose Delete asks first (PD-6-G20).
import { useState } from 'react';
import { canToggleBlack, gridHasContent } from '../../lib/gridEdits';
import storage from '../../lib/storage';
import InlineConfirm from './InlineConfirm';
import SavedGridsList from './SavedGridsList';

const REPLACE_MESSAGE = 'Replace the current grid? Unsaved changes are lost.';

export const NEW_GRID_SIZES = [11, 15, 21];

export default function GridPanel({
  grid,
  selectedCell,
  symmetryEnabled,
  editingPaused,
  onToggleBlack,
  onNewGrid,
  onOpenBegin,
  onOpenSaved,
  onDeleted,
}) {
  // The one open confirm: { kind: 'new', size } | { kind: 'open', entry } | { kind: 'delete',
  // entry } | null. A single slot, so opening one closes any other (novice-readiness spec
  // 0.2.7 §3.4 (PD-6-G20)); local, so it is dropped when the panel unmounts.
  const [pending, setPending] = useState(null);
  const [saved, setSaved] = useState(null); // entries from storage.list() | null (list hidden)
  const refreshSaved = () => storage.list().then(setSaved);
  // novice-readiness spec 0.2.8 §3.4 (Q1, Greptile #77 GridPanel.jsx:88): Open reads the entry
  // again by id when the user confirms it, not from the list snapshot. An entry that has gone
  // away shows the refreshed list and nothing is adopted. The read is `ordered`: it waits in the
  // lock queue behind this tab's pending saves, so Open shows what they wrote and the save
  // machine's known savedAt is the stored one (Phase 6R re-review N1). So a confirmed Open can
  // wait, and novice-readiness spec 0.2.10 §3.4 (An Open that waits) applies: App's
  // `onOpenBegin` token is taken at the confirm, before the read, and handed back with the
  // entry so App drops the Open if New grid or import replaced the document meanwhile.
  // Closing the panel does not cancel it: the user asked to open it, and the request stands (an
  // empty grid skips the confirm, so "confirm" here includes that click).
  const openEntry = (entry) => {
    const token = onOpenBegin?.();
    return storage.list({ ordered: true }).then((entries) => {
      const fresh = entries.find((e) => e.id === entry.id);
      if (fresh) onOpenSaved(fresh, token);
      else setSaved(entries);
    });
  };
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
              if (gridHasContent(grid)) setPending({ kind: 'new', size });
              else onNewGrid(size);
            }}
          >
            {`${size}\u00d7${size}`}
          </button>
        ))}
      </div>
      <h4 className="xw-grid-panel-sub">Saved grids</h4>
      <div className="xw-grid-panel-actions">
        <button
          type="button"
          className="xw-ghost-btn"
          disabled={editingPaused}
          onClick={refreshSaved}
        >
          Open saved
        </button>
      </div>
      {pending && !editingPaused && (
        <InlineConfirm
          message={
            pending.kind === 'delete' ? `Delete "${pending.entry.name}"?` : REPLACE_MESSAGE
          }
          confirmLabel={pending.kind === 'delete' ? 'Delete' : 'Replace'}
          onConfirm={() => {
            const current = pending;
            setPending(null);
            if (current.kind === 'new') onNewGrid(current.size);
            else if (current.kind === 'open') openEntry(current.entry);
            else {
              // novice-readiness spec 0.2.8 §3.4 (Q1): App learns which id went, so it can mark
              // the open document unsaved when it was that one. A failed remove changes
              // nothing but the refreshed list.
              const id = current.entry.id;
              storage
                .remove(id)
                .then(() => onDeleted?.(id))
                .then(refreshSaved)
                .catch(refreshSaved);
            }
          }}
          onCancel={() => setPending(null)}
        />
      )}
      {saved && (
        <SavedGridsList
          entries={saved}
          disabled={editingPaused}
          onOpen={(entry) => {
            if (gridHasContent(grid)) setPending({ kind: 'open', entry });
            else openEntry(entry);
          }}
          onDelete={(id) => setPending({ kind: 'delete', entry: saved.find((e) => e.id === id) })}
        />
      )}
    </div>
  );
}
