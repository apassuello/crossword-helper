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
 * novice-readiness spec 0.2.8 §3.8 (F4, F1b): merge the apply-theme route's reply
 * against the grid the request was built from. A cell is written only where the
 * reply differs from `sentGrid` (`letter`, `isBlack` or `isThemeLocked`) **and**
 * the live grid (`prevGrid`) still equals `sentGrid` there; a cell the user changed
 * since the send keeps its live object. Under Apply All `sentGrid` is the chained
 * previous reply, so an edit made during earlier words is kept even inside a later
 * word's own cells. When the three grids are not all the same size the live grid
 * is returned unchanged (never throws).
 */
export function writeAppliedTheme(prevGrid, replyGrid, sentGrid) {
  const size = prevGrid.length;
  if (replyGrid.length !== size || sentGrid.length !== size) return prevGrid;
  const differs = (a, b) =>
    (a.letter || '') !== (b.letter || '') ||
    !!a.isBlack !== !!b.isBlack ||
    !!a.isThemeLocked !== !!b.isThemeLocked;
  return prevGrid.map((row, r) =>
    row.map((live, c) => {
      const reply = replyGrid[r] && replyGrid[r][c];
      const sent = sentGrid[r] && sentGrid[r][c];
      if (!reply || !sent) return live;
      return differs(reply, sent) && !differs(live, sent)
        ? written(normalizeCell(reply), {})
        : live;
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
 * novice-readiness spec 0.2.7 §2.3 (S1): Verify's response as a functional update.
 * A new grid in which only `isError` changes (true for a "row,col" key in
 * `errorKeys`, false elsewhere); letters, locks and provenance are `prev`'s.
 */
export function applyVerifyErrors(prev, errorKeys) {
  return prev.map((row, r) =>
    row.map((cell, c) => ({ ...cell, isError: errorKeys.has(`${r},${c}`) }))
  );
}

/**
 * novice-readiness spec 0.2.7 §3.5 (G5) and §2.3 (S1): the cells Clean may
 * blank, judged against `prev`, the grid as it is when the response lands.
 * `sentLetters` / `cleanedLetters` are string[][] ('' for blank or black). A
 * cell qualifies when the request carried a letter there, the server removed
 * it, `prev` still holds that same letter (a letter typed since is the user's),
 * and the cell is white and not theme-locked.
 */
export function planClean(prev, sentLetters, cleanedLetters) {
  const blanks = [];
  prev.forEach((row, r) =>
    row.forEach((cell, c) => {
      if (
        sentLetters[r][c] &&
        !cleanedLetters[r][c] &&
        !cell.isBlack &&
        !cell.isThemeLocked &&
        cell.letter === sentLetters[r][c]
      ) {
        blanks.push([r, c]);
      }
    })
  );
  return { blanks };
}

/**
 * novice-readiness spec 0.2.7 §3.5 (G5, PD-4A): apply Clean's response. Only
 * the cells in `blanks` (from `planClean`) are written, each as a new object
 * with the server's letter (always '' for a blank), `isError`, `isAutofilled`
 * and `isBlocked` cleared. Every other cell is `prevGrid`'s own object, its
 * `isError` as it was. `isBlack` never changes: `cleanedGrid`'s is not applied.
 */
export function writeCleanedGrid(prevGrid, cleanedGrid, blanks) {
  const updates = blanks.map(([r, c]) => [
    r,
    c,
    written(prevGrid[r][c], {
      letter: cleanedGrid[r][c].letter || '',
      isError: false,
    }),
  ]);
  return updates.length ? withCells(prevGrid, updates) : prevGrid;
}

/** novice-readiness spec 0.2.7 §3.5 (G5 step 3, #63): a new grid with `isError` false everywhere. */
export function clearAllErrors(prev) {
  return prev.map((row) => row.map((cell) => ({ ...cell, isError: false })));
}
