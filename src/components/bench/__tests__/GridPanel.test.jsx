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
  const onNewGrid = vi.fn();
  const props = {
    grid: makeGrid(),
    gridSize: SIZE,
    selectedCell: sel(1, 1),
    symmetryEnabled: true,
    editingPaused: false,
    onToggleBlack,
    onNewGrid,
    ...over,
  };
  render(<GridPanel {...props} />);
  return { onToggleBlack, onNewGrid, button: screen.getByRole('button', { name: 'Black square' }) };
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

// novice-readiness spec 0.2.7 §3.2 (#55): New grid with an in-panel confirm.
describe('GridPanel New grid (§3.2)', () => {
  const withContent = () => makeGrid({ '0,0': { letter: 'A' } });
  const sizeBtn = (label) => screen.getByRole('button', { name: label });

  it('offers exactly 11×11, 15×15 and 21×21 (× is U+00D7)', () => {
    setup();
    for (const label of ['11\u00d711', '15\u00d715', '21\u00d721']) {
      expect(sizeBtn(label)).toBeInTheDocument();
    }
  });

  it('on a grid with no letter and no black square, calls onNewGrid(size) with no confirm', async () => {
    const { onNewGrid } = setup();
    await userEvent.setup().click(sizeBtn('11\u00d711'));
    expect(onNewGrid).toHaveBeenCalledTimes(1);
    expect(onNewGrid).toHaveBeenCalledWith(11);
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('on a grid with a letter, shows the confirm and does not call onNewGrid yet', async () => {
    const { onNewGrid } = setup({ grid: withContent() });
    await userEvent.setup().click(sizeBtn('21\u00d721'));
    expect(onNewGrid).not.toHaveBeenCalled();
    expect(screen.getByRole('group')).toHaveTextContent(
      'Replace the current grid? Unsaved changes are lost.'
    );
  });

  it('a black square alone also needs the confirm', async () => {
    const { onNewGrid } = setup({ grid: makeGrid({ '2,2': { isBlack: true } }) });
    await userEvent.setup().click(sizeBtn('15\u00d715'));
    expect(onNewGrid).not.toHaveBeenCalled();
    expect(screen.getByRole('group')).toBeInTheDocument();
  });

  it('Replace calls onNewGrid with the chosen size and closes the confirm', async () => {
    const user = userEvent.setup();
    const { onNewGrid } = setup({ grid: withContent() });
    await user.click(sizeBtn('21\u00d721'));
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    expect(onNewGrid).toHaveBeenCalledTimes(1);
    expect(onNewGrid).toHaveBeenCalledWith(21);
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('Cancel closes the confirm and changes nothing', async () => {
    const user = userEvent.setup();
    const { onNewGrid } = setup({ grid: withContent() });
    await user.click(sizeBtn('15\u00d715'));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onNewGrid).not.toHaveBeenCalled();
    expect(screen.queryByRole('group')).toBeNull();
  });

  it('disables all three size buttons while editing is paused', () => {
    setup({ editingPaused: true });
    for (const label of ['11\u00d711', '15\u00d715', '21\u00d721']) {
      expect(sizeBtn(label)).toBeDisabled();
    }
  });

  it('drops an open confirm when the panel unmounts', async () => {
    const user = userEvent.setup();
    const props = {
      grid: withContent(),
      gridSize: SIZE,
      selectedCell: null,
      symmetryEnabled: true,
      editingPaused: false,
      onToggleBlack: vi.fn(),
      onNewGrid: vi.fn(),
    };
    const { unmount } = render(<GridPanel {...props} />);
    await user.click(sizeBtn('15\u00d715'));
    expect(screen.getByRole('group')).toBeInTheDocument();
    unmount();
    render(<GridPanel {...props} />);
    expect(screen.queryByRole('group')).toBeNull();
  });
});
