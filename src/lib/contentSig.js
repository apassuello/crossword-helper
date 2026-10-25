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
 */

export function cellContentOf(c) {
  return [c.letter, c.isBlack, c.isThemeLocked, c.isAutofilled === true];
}

export function contentSigOf(size, grid) {
  return JSON.stringify({
    size,
    cells: grid ? grid.map((row) => row.map(cellContentOf)) : null,
  });
}
