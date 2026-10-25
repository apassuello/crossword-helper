/**
 * The save machine hands `storage.save` its document and options as functions that the real
 * storage calls inside the Web Lock (Phase 6R review I1). A test double that never calls them
 * reads them here; the machine resolves each once, so the value is the one the lock would see.
 */
export const saveArg = (call, i) => (typeof call[i] === 'function' ? call[i]() : call[i]);

/** A `storage.save` double that answers `result` after resolving its arguments at call time. */
export const resolvingSave = (result) => (doc, opts) => {
  saveArg([doc, opts], 0);
  saveArg([doc, opts], 1);
  return Promise.resolve(result);
};
