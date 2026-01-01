/**
 * Test fixtures for grid data
 *
 * Provides various grid configurations for testing:
 * - Empty grids (different sizes)
 * - Partially filled grids
 * - Grids with theme words
 * - Grids with black squares
 * - Edge cases
 */

/**
 * Create empty grid of specified size
 */
export function createEmptyGrid(size = 15) {
  return Array(size).fill(null).map(() =>
    Array(size).fill(null).map(() => ({
      letter: '',
      isBlack: false,
      number: null,
      isError: false,
      isHighlighted: false,
      isThemeLocked: false,
    }))
  );
}

/**
 * 11x11 empty grid (standard small size)
 */
export const emptyGrid11x11 = createEmptyGrid(11);

/**
 * 15x15 empty grid (standard medium size)
 */
export const emptyGrid15x15 = createEmptyGrid(15);

/**
 * 21x21 empty grid (standard large size)
 */
export const emptyGrid21x21 = createEmptyGrid(21);

/**
 * Grid with some black squares (symmetric pattern)
 */
export const gridWithBlackSquares = (() => {
  const grid = createEmptyGrid(15);
  // Add symmetric black squares
  grid[0][0].isBlack = true;
  grid[14][14].isBlack = true;
  grid[0][14].isBlack = true;
  grid[14][0].isBlack = true;
  grid[7][7].isBlack = true; // Center
  return grid;
})();

/**
 * Partially filled grid (some letters filled in)
 */
export const partiallyFilledGrid = (() => {
  const grid = createEmptyGrid(15);
  // Fill in top row
  const word = 'CROSSWORD';
  for (let i = 0; i < word.length; i++) {
    grid[0][i].letter = word[i];
  }
  return grid;
})();

/**
 * Grid with theme words (locked)
 */
export const gridWithThemeWords = (() => {
  const grid = createEmptyGrid(15);
  // Theme word "BIRTHDAY" across top
  const theme = 'BIRTHDAY';
  for (let i = 0; i < theme.length; i++) {
    grid[0][i].letter = theme[i];
    grid[0][i].isThemeLocked = true;
  }
  return grid;
})();

/**
 * Grid with validation errors
 */
export const gridWithErrors = (() => {
  const grid = createEmptyGrid(15);
  grid[0][0].isError = true;
  grid[0][1].isError = true;
  return grid;
})();

/**
 * Very small grid (3x3) for edge case testing
 */
export const tinyGrid3x3 = createEmptyGrid(3);

/**
 * Grid with all black squares (invalid)
 */
export const allBlackGrid = (() => {
  const grid = createEmptyGrid(11);
  grid.forEach(row => row.forEach(cell => cell.isBlack = true));
  return grid;
})();

/**
 * Grid in CLI format (for API requests)
 */
export function gridToCliFormat(grid) {
  return grid.map(row =>
    row.map(cell => {
      if (cell.isBlack) return '#';
      if (cell.letter) return cell.letter.toUpperCase();
      return '.';
    })
  );
}

/**
 * Convert CLI format grid to frontend format
 */
export function cliToFrontendFormat(cliGrid) {
  return cliGrid.map(row =>
    row.map(cell => ({
      letter: cell === '#' || cell === '.' ? '' : cell,
      isBlack: cell === '#',
      number: null,
      isError: false,
      isHighlighted: false,
      isThemeLocked: false,
    }))
  );
}

/**
 * Sample completed grid (fully filled)
 */
export const completedGrid = (() => {
  const grid = createEmptyGrid(11);
  // Fill with pattern (not real words, just for testing)
  for (let r = 0; r < 11; r++) {
    for (let c = 0; c < 11; c++) {
      if ((r + c) % 3 === 0) {
        grid[r][c].isBlack = true;
      } else {
        grid[r][c].letter = String.fromCharCode(65 + ((r + c) % 26)); // A-Z
      }
    }
  }
  return grid;
})();

/**
 * Grid with numbered slots (after auto-numbering)
 */
export const numberedGrid = (() => {
  const grid = createEmptyGrid(15);
  let num = 1;
  for (let r = 0; r < 15; r++) {
    for (let c = 0; c < 15; c++) {
      // Number cells that start across or down words
      const isStart = (
        (c === 0 || grid[r][c - 1]?.isBlack) && c < 14 && !grid[r][c + 1]?.isBlack
      ) || (
        (r === 0 || grid[r - 1]?.[c]?.isBlack) && r < 14 && !grid[r + 1]?.[c]?.isBlack
      );

      if (isStart) {
        grid[r][c].number = num++;
      }
    }
  }
  return grid;
})();

export default {
  createEmptyGrid,
  emptyGrid11x11,
  emptyGrid15x15,
  emptyGrid21x21,
  gridWithBlackSquares,
  partiallyFilledGrid,
  gridWithThemeWords,
  gridWithErrors,
  tinyGrid3x3,
  allBlackGrid,
  completedGrid,
  numberedGrid,
  gridToCliFormat,
  cliToFrontendFormat,
};
