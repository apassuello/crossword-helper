// novice-readiness spec 0.2.7 §3.2 (#55): an in-panel confirm, never a browser dialog.
// Shared by New grid, Open saved, the save-name collision and Clean.
export default function InlineConfirm({
  message,
  confirmLabel,
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  confirmDisabled = false,
}) {
  return (
    <div className="xw-inline-confirm" role="group" aria-label={message}>
      <p className="xw-inline-confirm-msg">{message}</p>
      <div className="xw-inline-confirm-actions">
        <button type="button" className="xw-danger-btn" onClick={onConfirm} disabled={confirmDisabled}>
          {confirmLabel}
        </button>
        <button type="button" className="xw-ghost-btn" onClick={onCancel}>
          {cancelLabel}
        </button>
      </div>
    </div>
  );
}
