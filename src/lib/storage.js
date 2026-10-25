/**
 * storage — async persistence transport for the save machine.
 * novice-readiness spec 0.2.8 §3.4 (M1, M2, S4, G3).
 *
 * The save machine (useSaveMachine) must reach persistence ONLY through these
 * functions — never `localStorage` directly — so that M2 can swap the
 * transport to `POST /api/grid/save` WITHOUT touching the machine. All are
 * genuinely async (they return real Promises) for exactly that reason.
 *
 * Saved grids are a JSON array under SAVE_KEY, newest first; an entry is the
 * save document plus `name` and `savedAt`, keyed by `doc.id`.
 *
 * Failure contract (the machine depends on it):
 *   - save() REJECTS if a write throws (quota / serialize) → drives the
 *     machine's error path (toast + retry).
 *   - list() and load() NEVER reject: a missing or corrupt array blob, or a
 *     throwing getItem, resolves `[]` / `null` so a bad save can't crash boot.
 *   - remove() rewrites the array; an unknown id resolves and changes nothing.
 *
 * Legacy migration (novice-readiness spec 0.2.7 §3.4, PD-6-G1): a blob under
 * LEGACY_SAVE_KEY is merged into the array as the entry `Saved grid`, and the
 * legacy key is removed only AFTER the array write succeeded. Its id is
 * `legacy-<savedAt>`, so a migration interrupted before the removal upserts the
 * same entry next time instead of duplicating it.
 */

import { mintDocId } from './docId';

/** Saved grids: a JSON array, newest first. */
export const SAVE_KEY = 'crossword_saved_grids';

/** LEGACY single-blob key (pre-6.5 saves). Keep this literal in exactly one place. */
export const LEGACY_SAVE_KEY = 'crossword_saved_grid';

const LEGACY_NAME = 'Saved grid';
const EPOCH_ISO = '1970-01-01T00:00:00.000Z';

const pad = (n) => String(n).padStart(2, '0');

/** 'YYYY-MM-DD HH:MM' in local time (spec §3.4, PD-6-G2). */
export function formatStamp(date) {
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    ` ${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/** `<size>×<size> <YYYY-MM-DD HH:MM>`; the multiplication sign is U+00D7. */
export function defaultName(size, date) {
  return `${size}×${size} ${formatStamp(date)}`;
}

/** A usable stored entry: a non-null object with a string `id`. The one home for this rule. */
function isEntry(e) {
  return e !== null && typeof e === 'object' && typeof e.id === 'string';
}

function readArray() {
  const raw = localStorage.getItem(SAVE_KEY);
  if (raw == null) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isEntry) : [];
  } catch {
    return [];
  }
}

/** The legacy blob as an entry, or null if absent / corrupt / not an object. */
function readLegacyEntry() {
  const raw = localStorage.getItem(LEGACY_SAVE_KEY);
  if (raw == null) return null;
  let blob;
  try {
    blob = JSON.parse(raw);
  } catch {
    return null;
  }
  if (blob === null || typeof blob !== 'object' || Array.isArray(blob)) return null;
  let savedAt = EPOCH_ISO;
  if (typeof blob.savedAt === 'string') savedAt = blob.savedAt;
  else if (typeof blob.timestamp === 'string') savedAt = blob.timestamp;
  return { ...blob, id: `legacy-${savedAt}`, name: LEGACY_NAME, savedAt };
}

/**
 * Current entries plus any legacy entry merged in. `pending` is true while the
 * legacy key still has to be removed after an array write.
 */
function readState() {
  const entries = readArray();
  const legacy = readLegacyEntry();
  if (!legacy) return { entries, pending: false, needsWrite: false };
  if (entries.some((e) => e.id === legacy.id)) {
    // Interrupted earlier: the entry is already in the array; only the removal is left.
    return { entries, pending: true, needsWrite: false };
  }
  const at = entries.findIndex((e) => typeof e.savedAt !== 'string' || e.savedAt < legacy.savedAt);
  const merged = at === -1 ? [...entries, legacy] : [...entries.slice(0, at), legacy, ...entries.slice(at)];
  return { entries: merged, pending: true, needsWrite: true };
}

function dropLegacyKey() {
  try {
    localStorage.removeItem(LEGACY_SAVE_KEY);
  } catch {
    // The entry is in the array already; the id makes the next pass a no-op upsert.
  }
}

/**
 * Run `fn` (a whole synchronous read-and-write) inside the cross-tab lock
 * `SAVE_KEY` when `navigator.locks` exists, so two tabs' read-modify-writes
 * serialise (novice-readiness spec 0.2.8 §3.4; Greptile #77 storage.js:171).
 * Without it (older browsers, jsdom) the call runs as before and two tabs can
 * still lose each other's entry — a known residual, not closed here.
 */
function withLock(fn) {
  const locks = typeof navigator !== 'undefined' ? navigator.locks : undefined;
  if (locks && typeof locks.request === 'function') return locks.request(SAVE_KEY, fn);
  return Promise.resolve().then(fn);
}

/**
 * The whole read of `list`, run INSIDE the lock: re-read (another tab may have migrated
 * meanwhile) and finish any pending legacy migration.
 */
function readEntriesInLock() {
  const { entries, pending, needsWrite } = readState();
  if (!pending) return entries;
  try {
    if (needsWrite) localStorage.setItem(SAVE_KEY, JSON.stringify(entries));
    dropLegacyKey();
  } catch {
    // Near the quota: keep the legacy key; the merged entries are still readable.
  }
  return entries;
}

/**
 * All saved grids, newest first. Never rejects: any read failure resolves `[]`
 * (novice-readiness spec 0.2.8 §3.4, M1). A legacy migration whose write fails
 * still returns the merged readable entries and keeps the legacy key, so a later
 * read retries it (Greptile #77 storage.js:126).
 * `{ ordered: true }` always reads inside the lock, so the read queues behind this tab's
 * pending saves and sees what they wrote (Open saved of the open document's own entry,
 * Phase 6R re-review N1). Without it a clean read skips the lock.
 * @param {{ordered?: boolean}} [opts]
 * @returns {Promise<object[]>}
 */
export function list({ ordered = false } = {}) {
  return Promise.resolve()
    .then(() => {
      if (ordered) return withLock(readEntriesInLock);
      const first = readState();
      if (!first.pending) return first.entries;
      return withLock(readEntriesInLock);
    })
    .catch(() => []);
}

/**
 * The newest saved grid, or `null` if there is none. Never rejects.
 * @returns {Promise<object|null>}
 */
export function load() {
  return list().then((entries) => entries[0] ?? null);
}

/**
 * Upsert `doc` by `doc.id` (stamped with a fresh ISO `savedAt`) at the front.
 * Name: `opts.name`, else the stored entry's, else the default name. When
 * `opts.expectedSavedAt` is a string and the stored entry's `savedAt` differs,
 * a new entry `<name> (copy)` (the chosen name) is written under a fresh id
 * instead (S4, P16) and `opts.replaceEntryId` is NOT applied, so the other entry
 * survives (novice-readiness spec 0.2.8 §3.4, M2). A save whose entry no longer
 * exists writes it under its own id; it does not fork (Q1). The whole
 * read-and-write runs inside the cross-tab lock when available.
 *
 * `doc` and `opts` may each be a function: it is called INSIDE the lock, immediately before
 * the write, so a caller that waits for the lock reads its `expectedSavedAt` and snapshots
 * its document when the save executes, not when it was requested (spec 0.2.9 §3.4 (S4);
 * Phase 6R review I1).
 * @param {object|(() => object)} doc  serializable grid document carrying a stable `id`
 * @param {{name?: string, expectedSavedAt?: string|null, replaceEntryId?: string}
 *   |(() => object)} [opts]
 * @returns {Promise<{savedAt: string, id: string, name: string, forked: boolean}>}
 *   rejects if a write throws
 */
export function save(doc, opts = {}) {
  return withLock(() => {
    const resolvedDoc = typeof doc === 'function' ? doc() : doc;
    const resolvedOpts = typeof opts === 'function' ? opts() : opts;
    return writeEntry(resolvedDoc, resolvedOpts);
  });
}

/**
 * The synchronous variant for the `pagehide` handler ONLY: the same read, S4 fork rule and
 * write as `save`, but outside `navigator.locks` and completed before it returns (a lock
 * grant needs a round trip a closing page may not survive; the two-tab race on this one
 * path is accepted). novice-readiness spec 0.2.9 §3.4 (Leaving the page). Throws if a
 * write throws.
 * @returns {{savedAt: string, id: string, name: string, forked: boolean}}
 */
export function saveSync(doc, opts = {}) {
  return writeEntry(doc, opts);
}

function writeEntry(doc, opts) {
  const now = new Date();
  const savedAt = now.toISOString();
  const { entries, pending } = readState();
  const stored = entries.find((e) => e.id === doc.id);

  let id = doc.id;
  const name = opts.name ?? stored?.name ?? defaultName(doc.size, now);
  let finalName = name;
  let forked = false;
  if (typeof opts.expectedSavedAt === 'string' && stored && stored.savedAt !== opts.expectedSavedAt) {
    forked = true;
    id = mintDocId();
    finalName = `${name} (copy)`;
  }

  const rest = entries.filter((e) => e.id !== id && (forked || e.id !== opts.replaceEntryId));
  // A throw here (quota exceeded, unserializable value) rejects the returned
  // promise — intentional; the machine's error path relies on it. The legacy
  // key is then left in place.
  localStorage.setItem(SAVE_KEY, JSON.stringify([{ ...doc, id, name: finalName, savedAt }, ...rest]));
  if (pending) dropLegacyKey();
  return { savedAt, id, name: finalName, forked };
}

/**
 * Delete the entry with `id`. An unknown id resolves and changes nothing.
 * Runs inside the cross-tab lock when available.
 * @returns {Promise<void>}
 */
export function remove(id) {
  return withLock(() => {
    const { entries, pending } = readState();
    const rest = entries.filter((e) => e.id !== id);
    if (rest.length === entries.length && !pending) return;
    localStorage.setItem(SAVE_KEY, JSON.stringify(rest));
    if (pending) dropLegacyKey();
  });
}

export default { list, load, save, saveSync, remove, defaultName, formatStamp, SAVE_KEY, LEGACY_SAVE_KEY };
