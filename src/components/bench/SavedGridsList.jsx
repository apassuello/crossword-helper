// novice-readiness spec 0.2.7 §3.4: the Open saved list, one row per saved grid (name, size,
// saved time) with Open and Delete. Entries arrive newest first from `storage.list()`;
// `disabled` is `editingPaused` (D1), so no row can act while an autofill run is live.
import { formatStamp } from '../../lib/storage';

export default function SavedGridsList({ entries, disabled, onOpen, onDelete }) {
  return (
    <ul className="xw-saved-list">
      {entries.map((entry) => (
        <li key={entry.id} className="xw-saved-row">
          <span className="xw-saved-name">{entry.name}</span>
          <span className="xw-saved-meta">
            {`${entry.size}×${entry.size}`} {'·'} {formatStamp(new Date(entry.savedAt))}
          </span>
          <span className="xw-saved-actions">
            <button type="button" className="xw-ghost-btn" disabled={disabled} onClick={() => onOpen(entry)}>
              Open
            </button>
            <button type="button" className="xw-ghost-btn" disabled={disabled} onClick={() => onDelete(entry.id)}>
              Delete
            </button>
          </span>
        </li>
      ))}
    </ul>
  );
}
