// Document identity for the save machine. A document id is minted when a grid
// is born (app start, New grid, import) and never changes on an edit, so the
// save machine can tell "a new document" from "the same document, edited".
//
// A module-level counter cannot do this job: it restarts at 1 on every load.

let fallbackSeq = 0;

/** A fresh, non-empty, process-unique document id. */
export function mintDocId() {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === 'function') {
    return c.randomUUID();
  }
  // No crypto: time + a per-session sequence + randomness. The sequence makes
  // two ids minted in the same millisecond differ; the time and random parts
  // keep ids from different sessions apart.
  fallbackSeq += 1;
  const rand = Math.random().toString(36).slice(2, 10);
  return `doc-${Date.now().toString(36)}-${fallbackSeq.toString(36)}-${rand}`;
}
