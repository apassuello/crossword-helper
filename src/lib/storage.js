/**
 * storage — async persistence transport for the save machine.
 * novice-readiness spec 0.2.7 §3.4 (M1, S4, G3).
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
 *   - list() and load() NEVER reject: a missing or corrupt array blob resolves
 *     `[]` / `null` so a bad save can't crash boot.
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

function readArray() {
  const raw = localStorage.getItem(SAVE_KEY);
  if (raw == null) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
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
  if (entries.some((e) => e && e.id === legacy.id)) {
    // Interrupted earlier: the entry is already in the array; only the removal is left.
    return { entries, pending: true, needsWrite: false };
  }
  const at = entries.findIndex((e) => !e || typeof e.savedAt !== 'string' || e.savedAt < legacy.savedAt);
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
 * All saved grids, newest first. Never rejects.
 * @returns {Promise<object[]>}
 */
export function list() {
  return Promise.resolve().then(() => {
    try {
      const { entries, pending, needsWrite } = readState();
      if (pending) {
        if (needsWrite) localStorage.setItem(SAVE_KEY, JSON.stringify(entries));
        dropLegacyKey();
      }
      return entries;
    } catch {
      // A failed migration write leaves the legacy key in place; list() never rejects.
      return readArray();
    }
  });
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
 * a new entry `<name> (copy)` is written under a fresh id instead (S4, P16).
 * @param {object} doc  serializable grid document carrying a stable `id`
 * @param {{name?: string, expectedSavedAt?: string|null, replaceEntryId?: string}} [opts]
 * @returns {Promise<{savedAt: string, id: string, name: string, forked: boolean}>}
 *   rejects if a write throws
 */
export function save(doc, opts = {}) {
  return Promise.resolve().then(() => {
    const now = new Date();
    const savedAt = now.toISOString();
    const { entries, pending } = readState();
    const stored = entries.find((e) => e && e.id === doc.id);

    let id = doc.id;
    let name;
    let forked = false;
    if (typeof opts.expectedSavedAt === 'string' && stored && stored.savedAt !== opts.expectedSavedAt) {
      forked = true;
      id = mintDocId();
      name = `${stored.name} (copy)`;
    } else {
      name = opts.name ?? stored?.name ?? defaultName(doc.size, now);
    }

    const rest = entries.filter((e) => e && e.id !== id && e.id !== opts.replaceEntryId);
    // A throw here (quota exceeded, unserializable value) rejects the returned
    // promise — intentional; the machine's error path relies on it. The legacy
    // key is then left in place.
    localStorage.setItem(SAVE_KEY, JSON.stringify([{ ...doc, id, name, savedAt }, ...rest]));
    if (pending) dropLegacyKey();
    return { savedAt, id, name, forked };
  });
}

/**
 * Delete the entry with `id`. An unknown id resolves and changes nothing.
 * @returns {Promise<void>}
 */
export function remove(id) {
  return Promise.resolve().then(() => {
    const { entries, pending } = readState();
    const rest = entries.filter((e) => e && e.id !== id);
    if (rest.length === entries.length && !pending) return;
    localStorage.setItem(SAVE_KEY, JSON.stringify(rest));
    if (pending) dropLegacyKey();
  });
}

export default { list, load, save, remove, defaultName, formatStamp, SAVE_KEY, LEGACY_SAVE_KEY };
