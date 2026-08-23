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
