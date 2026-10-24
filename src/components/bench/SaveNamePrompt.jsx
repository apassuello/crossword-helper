import React, { useState } from 'react';
import InlineConfirm from './InlineConfirm';

// The name prompt under the TopBar Save button
// (novice-readiness spec 0.2.7 §3.4 (G3)). Confirming renames the document's own
// entry; a name already used by a DIFFERENT entry asks before replacing it
// (PD-6-G8). Match is trimmed and case-sensitive (PD-6-G3); an empty or blank name
// cannot be confirmed (PD-6-G7). Presentational: the parent owns the write and
// decides when the prompt closes.
export default function SaveNamePrompt({ initialName, entries, currentId, onConfirm, onCancel }) {
  const [name, setName] = useState(initialName);
  const [collision, setCollision] = useState(null); // the other entry about to be replaced

  const trimmed = name.trim();

  function submit(e) {
    e?.preventDefault();
    if (!trimmed) return;
    const other = entries.find((x) => x.id !== currentId && x.name === trimmed);
    if (other) {
      setCollision(other);
      return;
    }
    onConfirm(trimmed);
  }

  if (collision) {
    return (
      <div className="xw-save-prompt">
        <InlineConfirm
          message={`Replace the saved grid named "${trimmed}"?`}
          confirmLabel="Replace"
          onConfirm={() => onConfirm(trimmed, { replaceEntryId: collision.id })}
          onCancel={() => setCollision(null)}
        />
      </div>
    );
  }

  return (
    <form
      className="xw-save-prompt"
      onSubmit={submit}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onCancel();
      }}
    >
      <label className="xw-save-prompt-label" htmlFor="xw-save-name">
        Name this grid
      </label>
      <input
        id="xw-save-name"
        className="xw-save-prompt-input"
        type="text"
        value={name}
        autoFocus
        onChange={(e) => setName(e.target.value)}
      />
      <div className="xw-save-prompt-actions">
        <button type="submit" className="xw-primary-btn xw-primary-btn-sm" disabled={!trimmed}>
          Save
        </button>
        <button type="button" className="xw-ghost-btn" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
