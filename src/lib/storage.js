/**
 * storage — async persistence transport for the save machine (Task 7, Step 1).
 * Spec 06 §3 (reconciled — see Task 7).
 *
 * The save machine (useSaveMachine) must reach persistence ONLY through these
 * two functions — never `localStorage` directly — so that M2 can swap the
 * transport to `POST /api/grid/save` WITHOUT touching the machine. Both are
 * genuinely async (they return real Promises) for exactly that reason: today
 * they wrap localStorage, tomorrow they wrap fetch, and the machine's
 * await-shape stays identical.
 *
 * Failure contract (the machine depends on it):
 *   - save() REJECTS if the write throws (quota / serialize) → drives the
 *     machine's error path (toast + retry).
 *   - load() NEVER rejects: a missing OR corrupt blob resolves `null` so a bad
 *     save can't crash boot.
 */

// LEGACY key — pre-Task-7 saves (App.jsx handleSaveGrid) live here and must
// still load. Keep this literal in exactly one place.
export const SAVE_KEY = 'crossword_saved_grid';

/**
 * Persist `doc` (stamped with a fresh ISO `savedAt`) to storage.
 * @param {object} doc  serializable grid document carrying a stable `id`
 * @returns {Promise<{savedAt: string}>}  rejects if the write throws
 */
export function save(doc) {
  return Promise.resolve().then(() => {
    const savedAt = new Date().toISOString();
    // A throw here (quota exceeded, unserializable value) rejects the
    // returned promise — intentional; the machine's error path relies on it.
    localStorage.setItem(SAVE_KEY, JSON.stringify({ ...doc, savedAt }));
    return { savedAt };
  });
}

/**
 * Load the persisted document, or `null` if there is none / it is corrupt.
 * @returns {Promise<object|null>}  resolves null on absent/corrupt; never rejects
 */
export function load() {
  return Promise.resolve().then(() => {
    const raw = localStorage.getItem(SAVE_KEY);
    if (raw == null) return null;
    try {
      return JSON.parse(raw);
    } catch {
      // Corrupt blob: swallow to null so a bad save can't crash boot.
      return null;
    }
  });
}

export default { save, load, SAVE_KEY };
