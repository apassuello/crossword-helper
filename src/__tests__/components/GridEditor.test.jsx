/**
 * Tests for direction-aware typing in the grid editor.
 *
 * Regression coverage: letter entry used to always advance rightward, with no
 * way to type a down word. Typing now follows the selected direction, toggled
 * with Enter, the toolbar button, or clicking the focused cell again.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../App';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  }),
  Toaster: () => null,
}));

// Letters render as <text class="cell-letter"> at x = padding + col*40 + 20,
// y = padding + row*40 + 26 — collect (x, y, letter) to assert positions.
const renderedLetters = (container) =>
  Array.from(container.querySelectorAll('.cell-letter')).map((el) => ({
    x: Number(el.getAttribute('x')),
    y: Number(el.getAttribute('y')),
    letter: el.textContent,
  }));

const setup = async () => {
  const user = userEvent.setup();
  const utils = render(<App />);
  await waitFor(() => {
    expect(utils.container.querySelectorAll('.grid-cell')).toHaveLength(225);
  });
  return { user, ...utils };
};

describe('GridEditor typing direction', () => {
  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
  });

  it('types across by default (letters advance rightward)', async () => {
    const { user, container } = await setup();

    await user.click(container.querySelectorAll('.grid-cell')[0]);
    await user.keyboard('CAT');

    const letters = renderedLetters(container);
    expect(letters.map((l) => l.letter)).toEqual(['C', 'A', 'T']);
    // Same row (same y), advancing columns (increasing x)
    expect(new Set(letters.map((l) => l.y)).size).toBe(1);
    expect(letters[1].x - letters[0].x).toBe(40);
    expect(letters[2].x - letters[1].x).toBe(40);
  });

  it('Enter toggles to down typing (letters advance downward) (regression)', async () => {
    const { user, container } = await setup();

    await user.click(container.querySelectorAll('.grid-cell')[0]);
    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: /typing: down/i })).toBeInTheDocument();

    await user.keyboard('DOG');

    const letters = renderedLetters(container);
    expect(letters.map((l) => l.letter)).toEqual(['D', 'O', 'G']);
    // Same column (same x), advancing rows (increasing y)
    expect(new Set(letters.map((l) => l.x)).size).toBe(1);
    expect(letters[1].y - letters[0].y).toBe(40);
    expect(letters[2].y - letters[1].y).toBe(40);
  });

  it('Backspace moves back along the typing direction', async () => {
    const { user, container } = await setup();

    await user.click(container.querySelectorAll('.grid-cell')[0]);
    await user.keyboard('{Enter}');
    await user.keyboard('DOG');
    // Cursor sits on the empty cell at row 3: the first backspace clears it and
    // moves UP to row 2 (not left), the second clears row 2's G
    await user.keyboard('{Backspace}{Backspace}');

    const letters = renderedLetters(container);
    expect(letters.map((l) => l.letter)).toEqual(['D', 'O']);
    // Cursor is now on row 1's O: same column as D, one row below it
    expect(letters[1].x).toBe(letters[0].x);
    expect(letters[1].y - letters[0].y).toBe(40);
  });

  it('clicking the focused cell again flips the direction', async () => {
    const { user, container } = await setup();

    const firstCell = container.querySelectorAll('.grid-cell')[0];
    await user.click(firstCell);
    expect(screen.getByRole('button', { name: /typing: across/i })).toBeInTheDocument();

    await user.click(firstCell);
    expect(screen.getByRole('button', { name: /typing: down/i })).toBeInTheDocument();

    await user.click(firstCell);
    expect(screen.getByRole('button', { name: /typing: across/i })).toBeInTheDocument();
  });

  it('the toolbar button toggles the direction', async () => {
    const { user, container } = await setup();

    await user.click(screen.getByRole('button', { name: /typing: across/i }));
    expect(screen.getByRole('button', { name: /typing: down/i })).toBeInTheDocument();

    // And typing follows it
    await user.click(container.querySelectorAll('.grid-cell')[0]);
    await user.keyboard('HI');
    const letters = renderedLetters(container);
    expect(new Set(letters.map((l) => l.x)).size).toBe(1);
    expect(letters[1].y - letters[0].y).toBe(40);
  });
});
