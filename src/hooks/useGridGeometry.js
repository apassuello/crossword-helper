/**
 * useGridGeometry — pure grid geometry (Task 5).
 *
 * Client-side computation policy (plan §"Client-side computation policy"): the GUI MAY
 * compute slot extents, focused-slot pattern strings, and the 180° symmetry mirror.
 * It MUST NOT compute word validity, scores, candidate lists, or fills — none of that
 * lives here. Everything below is derived-view geometry only.
 *
 * All functions are PURE (no React) so they can be unit-tested without mounting. The
 * hook simply memoizes grid-bound versions.
 *
 * Cell shape (frontend canonical): { letter, isBlack, number, isError, isThemeLocked, ... }
 */

import { useMemo } from 'react';

/** 180° rotational symmetry partner of (r, c) on a size×size grid. */
export function mirrorOf(r, c, size) {
  return [size - 1 - r, size - 1 - c];
}

function cellAt(grid, r, c) {
  return grid[r] && grid[r][c];
}

/**
 * The word slot passing through (r, c) in `dir` ('across' | 'down').
 * Extents stop at black squares and grid edges. The pattern uses '?' for empty cells
 * and uppercased letters for filled ones. `number` is the clue number carried by the
 * slot's start cell (null if unnumbered). A black or out-of-range cell yields an empty
 * zero-length slot (never throws).
 *
 * @returns {{cells: number[][], pattern: string, number: number|null, length: number}}
 */
export function slotAt(grid, r, c, dir) {
  const empty = { cells: [], pattern: '', number: null, length: 0 };
  const cell = cellAt(grid, r, c);
  if (!cell || cell.isBlack) return empty;

  const size = grid.length;
  const cells = [];

  if (dir === 'across') {
    let start = c;
    while (start > 0 && !grid[r][start - 1].isBlack) start--;
    let end = c;
    while (end < size - 1 && !grid[r][end + 1].isBlack) end++;
    for (let cc = start; cc <= end; cc++) cells.push([r, cc]);
  } else {
    let start = r;
    while (start > 0 && !grid[start - 1][c].isBlack) start--;
    let end = r;
    while (end < size - 1 && !grid[end + 1][c].isBlack) end++;
    for (let rr = start; rr <= end; rr++) cells.push([rr, c]);
  }

  const pattern = cells
    .map(([rr, cc]) => {
      const letter = grid[rr][cc].letter;
      return letter ? letter.toUpperCase() : '?';
    })
    .join('');

  const [sr, sc] = cells[0];
  const startCell = grid[sr][sc];

  return {
    cells,
    pattern,
    number: startCell.number != null ? startCell.number : null,
    length: cells.length,
  };
}

/**
 * All across and down WORD slots (length ≥ 2), enumerated in reading order.
 * A cell starts an across word when its left neighbor is black/edge and its right
 * neighbor is white; likewise for down words. Isolated (length-1) runs are excluded.
 *
 * @returns {{across: object[], down: object[]}} slots as produced by slotAt
 */
export function allSlots(grid) {
  const size = grid.length;
  const across = [];
  const down = [];

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const cell = grid[r][c];
      if (cell.isBlack) continue;

      const leftEdge = c === 0 || grid[r][c - 1].isBlack;
      const hasRight = c < size - 1 && !grid[r][c + 1].isBlack;
      if (leftEdge && hasRight) across.push(slotAt(grid, r, c, 'across'));

      const topEdge = r === 0 || grid[r - 1][c].isBlack;
      const hasDown = r < size - 1 && !grid[r + 1][c].isBlack;
      if (topEdge && hasDown) down.push(slotAt(grid, r, c, 'down'));
    }
  }

  return { across, down };
}

/**
 * Hook: memoized grid-bound geometry helpers.
 * @param {object[][]} grid
 * @returns {{ slotAt(r,c,dir), allSlots(), mirrorOf(r,c,size) }}
 */
export function useGridGeometry(grid) {
  return useMemo(
    () => ({
      slotAt: (r, c, dir) => slotAt(grid, r, c, dir),
      allSlots: () => allSlots(grid),
      mirrorOf,
    }),
    [grid]
  );
}

export default useGridGeometry;
