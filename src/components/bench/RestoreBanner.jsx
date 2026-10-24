import React from 'react';
import { formatStamp } from '../../lib/storage';

// novice-readiness spec 0.2.7 §3.4 (PD-6-G2, PD-6-G9): the banner shown above the grid
// after restore-on-load. The stamp is local time in the default name's shape. Presentational:
// App owns when it closes (its ×, any grid edit, or Start blank).
export default function RestoreBanner({ name, savedAt, onStartBlank, onDismiss }) {
  return (
    <div className="xw-restore-banner" role="status">
      <span className="xw-restore-banner-text">
        {`Restored "${name}" (saved ${formatStamp(new Date(savedAt))})`}
      </span>
      <button type="button" className="xw-ghost-btn" onClick={onStartBlank}>
        Start blank
      </button>
      <button type="button" className="xw-icon-btn" aria-label="Dismiss" onClick={onDismiss}>
        {'×'}
      </button>
    </div>
  );
}
