/**
 * The one definition of "grid content" (novice-readiness spec 0.2.18 §3.9, "What one step is"
 * and "What a step holds"). App's dirty tracking, the undo history's snapshots and the hook's
 * step decision all compare content through this module, so they cannot disagree.
 *
 * Signature of user-authored grid content, for the save machine's dirty
 * tracking. Deliberately array-shaped and limited to durable authored fields:
 * it EXCLUDES `number` (derived by auto-renumbering, would spuriously mark
 * dirty), the transient isError/isHighlighted flags, and `symmetryEnabled` --
 * symmetry is a VIEW construction aid (a VIEW toggle), persisted on its
 * own key via usePersistentState, so toggling it stays silent as it did before
 * the save machine (it still rides along in the saved `doc`). Called in every
 * place that establishes or compares dirtiness so the strings are byte-identical.
 * `isAutofilled` is authored provenance and is part of the signature (absent counts
 * as false); `isBlocked` is runtime-only and is not.
 *
 * Implements Decision 5 (clue-authoring spec 0.1.4, section 1), section 4.1 "Two signatures":
 * `contentSigOf` is the GRID signature and is unchanged; `docSigOf` is the DOCUMENT signature
 * (grid plus clues, text included) that dirty tracking and undo compare; `statusSigOf` covers the
 * grid plus each clue's key and answer, never its text, so it changes exactly when a clue's
 * status could. An absent clue map behaves as `{}` in all of them.
 */
import { compareClueKeys } from './clues';

export function cellContentOf(c) {
  return [c.letter, c.isBlack, c.isThemeLocked, c.isAutofilled === true];
}

export function contentSigOf(size, grid) {
  return JSON.stringify({
    size,
    cells: grid ? grid.map((row) => row.map(cellContentOf)) : null,
  });
}

/** `[key, text, answer]` triples of `clues`, in `compareClueKeys` order; absent map -> `[]`. */
function clueTriples(clues) {
  return Object.keys(clues || {})
    .sort(compareClueKeys)
    .map((key) => [key, clues[key].text, clues[key].answer]);
}

/** Document signature (spec 4.1): `JSON.stringify({size, cells, clues})`. */
export function docSigOf(size, grid, clues) {
  return JSON.stringify({
    size,
    cells: grid ? grid.map((row) => row.map(cellContentOf)) : null,
    clues: clueTriples(clues),
  });
}

/** Status signature: the grid signature plus each clue's key and answer in key order, no text. */
export function statusSigOf(size, grid, clues) {
  return JSON.stringify({
    grid: contentSigOf(size, grid),
    clues: clueTriples(clues).map(([key, , answer]) => [key, answer]),
  });
}
