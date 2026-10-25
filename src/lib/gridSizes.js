/**
 * The square grid sizes the importer accepts, inclusive. The one home for the range: the
 * ImportPanel size check and App's `isAdoptableEntry` both read it, so a saved import is
 * always restorable and openable (Phase 6R final review I2; novice-readiness plan Task 6.20).
 * New grid offers only 11/15/21 (`NEW_GRID_SIZES`), but an import may be any size in this range.
 */
export const IMPORT_MIN_SIZE = 3;
export const IMPORT_MAX_SIZE = 25;
