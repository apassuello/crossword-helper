/**
 * useNumbering — pure numbering helpers (Task 8B).
 *
 * These are the PURE building blocks for server-authoritative numbering
 * (plan Task 8/F2): `localNumber` is the optimistic client-side pass fired
 * immediately on a structural edit for instant paint, before the server's
 * `/api/number` response (always wins on reconcile — see gridCodec.applyNumbering)
 * lands. Task 8C wraps these in an actual React hook that detects structural
 * changes via `structuralSigOf` and drives the optimistic → server-reconcile flow.
 *
 * All functions here are pure/immutable (no input mutation), mirroring
 * gridCodec.applyNumbering's contract.
 *
 * Cell shape (frontend canonical): { letter, isBlack, number, isError, isThemeLocked, ... }
 */

import { allSlots } from './useGridGeometry';

/**
 * Optimistic client-side numbering pass. Builds the set of word-start cells
 * from `allSlots` (across/down slot[0].cells[0]) rather than reimplementing
 * the legacy isStartOfAcrossWord/isStartOfDownWord predicates — this
 * guarantees the numbering agrees with `slotAt(...).number` by construction.
 *
 * Immutable: returns a brand-new grid (new rows, new cell objects); the
 * input `grid` is never mutated.
 *
 * @param {object[][]} grid
 * @returns {{ grid: object[][], numbering: Record<string, number> }}
 *   `numbering` keys are unparenthesized "row,col" strings (see plan Global
 *   Constraint 6 — NOT the server's "(r,c)" form).
 */
export function localNumber(grid) {
  const { across, down } = allSlots(grid);
  const starts = new Set();
  for (const s of [...across, ...down]) {
    const [r, c] = s.cells[0];
    starts.add(`${r},${c}`);
  }

  const numbering = {};
  let currentNumber = 1;

  const newGrid = grid.map((row, r) =>
    row.map((cell, c) => {
      const key = `${r},${c}`;
      if (starts.has(key)) {
        const n = currentNumber++;
        numbering[key] = n;
        return { ...cell, number: n };
      }
      return { ...cell, number: null };
    })
  );

  return { grid: newGrid, numbering };
}

/**
 * Extract a `{"row,col": number}` numbering map from a grid's `.number`
 * fields (e.g. after the server's `/api/number` response has been applied
 * via gridCodec.applyNumbering). Cells with no number are omitted.
 *
 * @param {object[][]} grid
 * @returns {Record<string, number>}
 */
export function numberingMapFromGrid(grid) {
  return Object.fromEntries(
    grid.flatMap((row, r) =>
      row.flatMap((cell, c) =>
        cell.number != null ? [[`${r},${c}`, cell.number]] : []
      )
    )
  );
}

/**
 * Structural signature of a grid: size + isBlack layout ONLY. Mirrors
 * App's `contentSigOf` shape but deliberately excludes `.letter` and every
 * derived field (`.number`, `.isError`, `.isThemeLocked`, ...) — renumbering
 * must fire on black-square/size changes only, never on letter edits
 * (plan Global Constraint 3).
 *
 * @param {number} size
 * @param {object[][]|null} grid
 * @returns {string|null}
 */
export function structuralSigOf(size, grid) {
  if (!grid) return null;
  return JSON.stringify({
    size,
    cells: grid.map((row) => row.map((c) => c.isBlack)),
  });
}
