/**
 * gridEdits — pure grid writers (novice-readiness spec 0.2.7 §3.7 (S5); §2.3
 * "Red cells").
 *
 * Common rule: every cell a writer WRITES is a new object with
 * `isAutofilled: false` (the user, not autofill, now owns it — even when the
 * letter is unchanged) and `isBlocked: false` (an edit clears red on the edited
 * cell only). Cells a writer does not write are the input's own objects. No
 * writer mutates its input grid or its cells; a writer that writes nothing
 * returns its input grid (same reference).
 */
import { normalizeCell } from '../api/gridCodec';
import { mirrorOf } from '../hooks/useGridGeometry';

/** A user-written copy of `cell`: `changes` applied, autofill and red cleared. */
function written(cell, changes) {
  return { ...cell, ...changes, isAutofilled: false, isBlocked: false };
}

/** Copy of `grid` with the cells at `updates` ([row, col, newCell]) replaced. */
function withCells(grid, updates) {
  const next = grid.map((row) => [...row]);
  for (const [r, c, cell] of updates) next[r][c] = cell;
  return next;
}

/** Type a letter (or erase with ''). A black cell is not written. */
export function writeLetter(grid, row, col, letter) {
  if (grid[row][col].isBlack) return grid;
  return withCells(grid, [
    [row, col, written(grid[row][col], { letter: letter.toUpperCase() })],
  ]);
}

/**
 * novice-readiness spec 0.2.7 §3.3 (G7): false when the cell, or with symmetry
 * its mirror partner, is theme-locked. Out of range -> false. With symmetry off
 * the partner is never consulted; the centre cell's partner is itself.
 */
export function canToggleBlack(grid, row, col, symmetryEnabled) {
  const at = (r, c) => grid[r] && grid[r][c];
  const cell = at(row, col);
  if (!cell || cell.isThemeLocked) return false;
  if (symmetryEnabled) {
    const [pr, pc] = mirrorOf(row, col, grid.length);
    const partner = at(pr, pc);
    if (!partner || partner.isThemeLocked) return false;
  }
  return true;
}

/**
 * novice-readiness spec 0.2.7 §3.2 (#55): true if any cell has a letter or is
 * black, i.e. replacing the grid would lose work. A null grid -> false.
 */
export function gridHasContent(grid) {
  if (!grid) return false;
  return grid.some((row) => row.some((cell) => cell.letter || cell.isBlack));
}

/** Flip black on (row, col) and, with symmetry, on its 180-degree partner. */
export function writeToggleBlack(grid, row, col, symmetryEnabled) {
  const size = grid.length;
  const isBlack = !grid[row][col].isBlack;
  const toggled = (cell) =>
    written(cell, { isBlack, letter: isBlack ? '' : cell.letter });
  const updates = [[row, col, toggled(grid[row][col])]];
  if (symmetryEnabled) {
    const symRow = size - 1 - row;
    const symCol = size - 1 - col;
    updates.push([symRow, symCol, toggled(grid[symRow][symCol])]);
  }
  return withCells(grid, updates);
}

/** Flip the theme lock on (row, col). A black cell is not written. */
export function writeToggleThemeLock(grid, row, col) {
  const cell = grid[row][col];
  if (cell.isBlack) return grid;
  return withCells(grid, [
    [row, col, written(cell, { isThemeLocked: !cell.isThemeLocked })],
  ]);
}

/**
 * novice-readiness spec 0.2.7 §3.5 (#62, G6): place a Search result. Walks
 * `word[i]` along `selectedCell.direction` from (row, col), stopping at the first
 * black square or the grid edge. A theme-locked cell is skipped (it keeps its
 * content and consumes `word[i]`) and the walk continues past it. Every other
 * cell is written as a new object (the common rule above); the input grid and its
 * cells are never mutated. Nothing written -> the input grid itself.
 */
export function writePatternWord(grid, selectedCell, word) {
  const { row, col, direction } = selectedCell;
  const size = grid.length;
  const updates = [];
  for (let i = 0; i < word.length; i++) {
    const r = direction === 'across' ? row : row + i;
    const c = direction === 'across' ? col + i : col;
    if (r >= size || c >= size) break;
    const cell = grid[r][c];
    if (cell.isBlack) break;
    if (cell.isThemeLocked) continue;
    updates.push([r, c, written(cell, { letter: word[i] })]);
  }
  return updates.length ? withCells(grid, updates) : grid;
}

/**
 * Merge the apply-theme route's grid: a cell is written when `letter`,
 * `isBlack` or `isThemeLocked` differs from `prevGrid`'s; others keep
 * `prevGrid`'s object.
 */
export function writeAppliedTheme(prevGrid, updatedGrid) {
  return prevGrid.map((row, r) =>
    row.map((prev, c) => {
      const upd = updatedGrid[r][c];
      const changed =
        (upd.letter || '') !== (prev.letter || '') ||
        !!upd.isBlack !== !!prev.isBlack ||
        !!upd.isThemeLocked !== !!prev.isThemeLocked;
      return changed ? written(normalizeCell(upd), {}) : prev;
    })
  );
}

/** Imported cells are canonical and every imported letter counts as typed. */
export function writeImportedGrid(importedGrid) {
  return importedGrid.map((row) =>
    row.map((cell) => written(normalizeCell(cell), {}))
  );
}

/**
 * Apply Clean's response (planning default PD-4A): letter/isBlack come from
 * the response and `isError` clears everywhere; only a cell whose letter or
 * isBlack changes is written (autofill and red cleared), the rest keep
 * `isAutofilled`/`isBlocked`.
 */
export function writeCleanedGrid(prevGrid, cleanedGrid) {
  return prevGrid.map((row, r) =>
    row.map((cell, c) => {
      const cleaned = cleanedGrid[r][c];
      const rawLetter =
        typeof cleaned === 'object'
          ? cleaned.letter || ''
          : cleaned === '#' || cleaned === '.'
            ? ''
            : cleaned;
      const isBlack =
        typeof cleaned === 'object' ? cleaned.isBlack : cleaned === '#';
      const letter = isBlack ? '' : rawLetter;
      const changes = { letter, isBlack, isError: false };
      return letter !== cell.letter || isBlack !== cell.isBlack
        ? written(cell, changes)
        : { ...cell, ...changes };
    })
  );
}
