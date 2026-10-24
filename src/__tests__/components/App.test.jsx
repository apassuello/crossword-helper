/**
 * Tests for App-level grid import behavior.
 *
 * Regression coverage: importing a grid of a DIFFERENT size used to be wiped
 * because the `useEffect(() => initializeGrid(gridSize), [gridSize])` re-fired
 * on the size change and replaced the imported grid with an empty one.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../App';
import { ToastProvider } from '../../components/bench/Toast';

// Bench's App consumes the ToastProvider context (useToasts), so it must be
// rendered inside the provider exactly as main.jsx mounts it. Main's version of
// App did not use toasts and rendered bare; the assertions below are unchanged.
const renderApp = () => render(<App />, { wrapper: ToastProvider });

// Bench's CrosswordGrid renders an SVG, not a div grid: one transparent hit rect
// per cell, black squares as a rect filled with var(--ink) (grid lines use
// `stroke`, not `fill`, so they do not match), and letters as text.xw-cell-letter.
// Main's assertions are unchanged — only the selectors are re-expressed.
const cells = (container) => container.querySelectorAll('rect[fill="transparent"]');
const blackCells = (container) => container.querySelectorAll('rect[fill="var(--ink)"]');
const letters = (container) =>
  Array.from(container.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);

// Mock react-hot-toast to avoid timers/portals in jsdom
vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  }),
  Toaster: () => null,
}));

const importGridViaPaste = async (user, container, gridJson) => {
  // Go to Import tab
  await user.click(screen.getByRole('button', { name: /^import$/i }));

  // Use the Paste JSON method
  await user.click(screen.getByRole('button', { name: /paste json/i }));

  const textarea = screen.getByLabelText(/paste json data/i);
  fireEvent.change(textarea, { target: { value: JSON.stringify(gridJson) } });

  await user.click(screen.getByRole('button', { name: /validate json/i }));

  await waitFor(() => {
    expect(screen.getByRole('button', { name: /import grid/i })).toBeInTheDocument();
  });

  await user.click(screen.getByRole('button', { name: /import grid/i }));
};

describe('App grid import', () => {
  beforeEach(() => {
    // The global localStorage mock returns undefined by default; the real API
    // returns null for missing keys.
    global.localStorage.getItem.mockReturnValue(null);
  });

  it('keeps letters and black squares when importing a smaller (5x5) grid into a 15x15 session (regression)', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();

    // Default 15x15 grid renders 225 cells
    await waitFor(() => {
      expect(cells(container)).toHaveLength(225);
    });

    const gridJson = {
      size: 5,
      grid: [
        ['C', 'A', 'T', '#', '.'],
        ['.', '.', '.', '.', '.'],
        ['#', '.', '.', '.', '#'],
        ['.', '.', '.', '.', '.'],
        ['.', '#', '.', '.', 'Z'],
      ],
    };

    await importGridViaPaste(user, container, gridJson);

    // ImportPanel defers the actual import by 300ms, then App switches to edit view
    await waitFor(() => {
      expect(cells(container)).toHaveLength(25);
    }, { timeout: 3000 });

    // Letters survived (previously wiped by grid re-initialization on size change)
    expect(letters(container)).toHaveLength(4);
    expect(letters(container)).toEqual(expect.arrayContaining(['C', 'A', 'T', 'Z']));

    // Black squares survived too (rendered with the dark fill)
    expect(blackCells(container)).toHaveLength(4);
  });

  it('same-size (15x15) import still works and keeps its letters', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();

    await waitFor(() => {
      expect(cells(container)).toHaveLength(225);
    });

    // Build a 15x15 grid with a few letters and a black square
    const grid = Array.from({ length: 15 }, () => Array(15).fill('.'));
    grid[0][0] = 'H';
    grid[0][1] = 'I';
    grid[7][7] = '#';

    await importGridViaPaste(user, container, { size: 15, grid });

    await waitFor(() => {
      expect(letters(container)).toEqual(expect.arrayContaining(['H', 'I']));
    }, { timeout: 3000 });

    expect(cells(container)).toHaveLength(225);
    expect(blackCells(container)).toHaveLength(1);
  });
});

// novice-readiness spec 0.2.7 §3.1 (#53, #50): hidden rail controls.
describe('App tool rail', () => {
  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
  });

  it('renders no Clues tool and no Heatmap toggle', async () => {
    const { container } = renderApp();
    await waitFor(() => {
      expect(cells(container)).toHaveLength(225);
    });
    expect(screen.getByText('Symmetry')).toBeInTheDocument();
    expect(screen.queryByText('Clues')).toBeNull();
    expect(screen.queryByText('Heatmap')).toBeNull();
  });
});

// novice-readiness spec 0.2.7 §3.3 (G7): black-square guard through the UI, and
// the always-visible key hint line.
describe('App black squares and hint line (§3.3)', () => {
  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
  });

  const SIZE = 15;
  const idx = (r, c) => r * SIZE + c;
  const focusEl = (container) => container.querySelector('.xw-grid-focus');

  it('refuses a theme-locked cell and its mirror partner, but toggles an unlocked one', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(SIZE * SIZE));
    const baseline = blackCells(container).length;
    const A = [2, 3];
    const partner = [SIZE - 1 - A[0], SIZE - 1 - A[1]];

    // Lock A with Ctrl+L.
    await user.click(cells(container)[idx(...A)]);
    fireEvent.keyDown(focusEl(container), { key: 'l', ctrlKey: true });

    // Space on the locked cell: refused.
    fireEvent.keyDown(focusEl(container), { key: ' ' });
    expect(blackCells(container)).toHaveLength(baseline);

    // Space on the locked cell's mirror partner: refused, no partial write.
    await user.click(cells(container)[idx(...partner)]);
    fireEvent.keyDown(focusEl(container), { key: ' ' });
    expect(blackCells(container)).toHaveLength(baseline);

    // Control: an unrelated cell still toggles (cell and its partner: +2).
    await user.click(cells(container)[idx(5, 6)]);
    fireEvent.keyDown(focusEl(container), { key: ' ' });
    expect(blackCells(container)).toHaveLength(baseline + 2);
  });

  it('shows the key hint under the grid in more than one tool', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(SIZE * SIZE));
    const hint = () => container.querySelector('p.xw-grid-hint');
    expect(hint()).not.toBeNull();
    expect(hint().textContent).toMatch(/^Type letters · Arrows move/);
    await user.click(screen.getByRole('button', { name: /^import$/i }));
    expect(hint()).not.toBeNull();
    expect(container.querySelectorAll('p.xw-grid-hint')).toHaveLength(1);
  });
});
