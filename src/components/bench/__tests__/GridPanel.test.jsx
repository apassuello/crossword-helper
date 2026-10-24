// novice-readiness spec 0.2.7 §3.3 (G7) / §3.2: the Grid panel's Black square toggle.
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GridPanel from '../GridPanel';

const SIZE = 5;
const makeGrid = (patch = {}) =>
  Array.from({ length: SIZE }, (_, r) =>
    Array.from({ length: SIZE }, (_, c) => ({
      row: r,
      col: c,
      letter: '',
      isBlack: false,
      isThemeLocked: false,
      ...(patch[`${r},${c}`] || {}),
    }))
  );

const sel = (row, col) => ({ row, col, direction: 'across' });

const setup = (over = {}) => {
  const onToggleBlack = vi.fn();
  const props = {
    grid: makeGrid(),
    gridSize: SIZE,
    selectedCell: sel(1, 1),
    symmetryEnabled: true,
    editingPaused: false,
    onToggleBlack,
    ...over,
  };
  render(<GridPanel {...props} />);
  return { onToggleBlack, button: screen.getByRole('button', { name: 'Black square' }) };
};

describe('GridPanel Black square (§3.3)', () => {
  it('is disabled with no selected cell', () => {
    const { button } = setup({ selectedCell: null });
    expect(button).toBeDisabled();
  });

  it('is enabled for an unlocked cell and calls onToggleBlack(1, 1) on click', async () => {
    const { button, onToggleBlack } = setup();
    expect(button).toBeEnabled();
    await userEvent.setup().click(button);
    expect(onToggleBlack).toHaveBeenCalledTimes(1);
    expect(onToggleBlack).toHaveBeenCalledWith(1, 1);
  });

  it('acts on the selected cell, not a fixed one', async () => {
    const { button, onToggleBlack } = setup({ selectedCell: sel(0, 2) });
    await userEvent.setup().click(button);
    expect(onToggleBlack).toHaveBeenCalledWith(0, 2);
  });

  it('is disabled when the selected cell is theme-locked', () => {
    const { button } = setup({ grid: makeGrid({ '1,1': { isThemeLocked: true } }) });
    expect(button).toBeDisabled();
  });

  it('is disabled when the mirror (3,3) is theme-locked and symmetry is on', () => {
    const { button } = setup({ grid: makeGrid({ '3,3': { isThemeLocked: true } }) });
    expect(button).toBeDisabled();
  });

  it('is enabled when the mirror is theme-locked but symmetry is off', () => {
    const { button } = setup({
      grid: makeGrid({ '3,3': { isThemeLocked: true } }),
      symmetryEnabled: false,
    });
    expect(button).toBeEnabled();
  });

  it('is disabled while editing is paused', () => {
    const { button } = setup({ editingPaused: true });
    expect(button).toBeDisabled();
  });

  it('carries aria-pressed for whether the selected cell is black', () => {
    const { button } = setup({ grid: makeGrid({ '1,1': { isBlack: true } }) });
    expect(button).toHaveAttribute('aria-pressed', 'true');
  });

  it('aria-pressed is false for a white cell and for no selection', () => {
    const { button } = setup();
    expect(button).toHaveAttribute('aria-pressed', 'false');
  });
});
