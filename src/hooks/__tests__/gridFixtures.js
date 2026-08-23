/**
 * Shared test fixture: build a canonical grid from row strings.
 * '#' = black, '.' = empty white, any other char = filled letter.
 * Used by useGridGeometry.test.jsx and useNumbering.test.jsx so both suites
 * build grids identically without importing each other's non-exported helpers.
 */
export function gridFromRows(rows) {
  return rows.map((row) =>
    row.split('').map((ch) => ({
      letter: ch === '#' || ch === '.' ? '' : ch,
      isBlack: ch === '#',
      number: null,
      isError: false,
      isHighlighted: false,
      isThemeLocked: false,
    }))
  );
}
