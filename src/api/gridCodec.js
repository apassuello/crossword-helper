/**
 * gridCodec — the ONLY place that converts between the three grid cell
 * encodings used across the app (see the plan's "Grid cell encodings"):
 *
 *   1. Frontend canonical: { letter, isBlack, isThemeLocked, number, isError }
 *   2. CLI strings (every backend call): "#" black, "." empty, "A" letter (uppercase)
 *   3. numbering response keys: "(r,c)" strings
 *
 * Letters are uppercased in BOTH directions.
 */

/** Canonical empty cell. */
export function makeCell() {
  return {
    letter: '',
    isBlack: false,
    isThemeLocked: false,
    number: null,
    isError: false,
  };
}

/** size x size grid of fresh (independent) canonical cells. */
export function makeGrid(size) {
  return Array.from({ length: size }, () =>
    Array.from({ length: size }, () => makeCell())
  );
}

/** Canonical grid -> CLI string rows (string[][]). */
export function toCliStrings(grid) {
  return grid.map((row) =>
    row.map((cell) => {
      if (cell.isBlack) return '#';
      if (cell.letter) return String(cell.letter).toUpperCase();
      return '.';
    })
  );
}

/** CLI string rows -> canonical grid. */
export function fromCliStrings(rows) {
  return rows.map((row) =>
    row.map((ch) => {
      const cell = makeCell();
      if (ch === '#') {
        cell.isBlack = true;
      } else if (ch === '.' || ch === '' || ch == null) {
        // empty white cell — nothing to set
      } else {
        cell.letter = String(ch).toUpperCase();
      }
      return cell;
    })
  );
}

const NUMBERING_KEY = /^\((\d+),\s*(\d+)\)$/;

/**
 * Apply a `{"(r,c)": n}` numbering map to a canonical grid.
 * Immutable: returns a new grid. Sets `.number` for mapped cells and clears
 * (`null`) stale numbers on cells absent from the map.
 */
export function applyNumbering(grid, numberingMap) {
  const parsed = new Map();
  for (const [key, n] of Object.entries(numberingMap || {})) {
    const m = NUMBERING_KEY.exec(key);
    if (m) parsed.set(`${m[1]},${m[2]}`, n);
  }
  return grid.map((row, r) =>
    row.map((cell, c) => {
      const k = `${r},${c}`;
      return { ...cell, number: parsed.has(k) ? parsed.get(k) : null };
    })
  );
}
