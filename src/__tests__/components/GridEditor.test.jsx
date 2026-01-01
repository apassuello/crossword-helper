/**
 * Tests for GridEditor - interactive crossword grid
 * Tests cell selection, letter entry, keyboard navigation, black squares, theme locking
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GridEditor from '../../components/GridEditor';
import { emptyGrid11x11, gridWithBlackSquares } from '../fixtures/gridFixtures';

describe('GridEditor Component', () => {
  const defaultProps = {
    grid: emptyGrid11x11,
    onCellChange: vi.fn(),
    onCellSelect: vi.fn(),
    selectedCell: { row: 0, col: 0 },
    size: 11,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders grid with correct size', () => {
    const { container } = render(<GridEditor {...defaultProps} />);
    const cells = container.querySelectorAll('.cell');
    expect(cells.length).toBe(11 * 11);
  });

  it('handles cell click selection', async () => {
    const user = userEvent.setup();
    const onCellSelect = vi.fn();

    render(<GridEditor {...defaultProps} onCellSelect={onCellSelect} />);

    const cells = screen.getAllByRole('gridcell');
    await user.click(cells[5]);

    expect(onCellSelect).toHaveBeenCalled();
  });

  it('allows typing letters in cells', async () => {
    const user = userEvent.setup();
    const onCellChange = vi.fn();

    render(<GridEditor {...defaultProps} onCellChange={onCellChange} />);

    const cells = screen.getAllByRole('gridcell');
    await user.click(cells[0]);
    await user.keyboard('C');

    expect(onCellChange).toHaveBeenCalledWith(0, 0, 'C');
  });

  it('toggles black squares on Shift+Click', async () => {
    const user = userEvent.setup();
    const onCellChange = vi.fn();

    render(<GridEditor {...defaultProps} onCellChange={onCellChange} />);

    const cells = screen.getAllByRole('gridcell');
    await user.click(cells[0], { shiftKey: true });

    expect(onCellChange).toHaveBeenCalledWith(0, 0, expect.objectContaining({
      isBlack: true
    }));
  });

  it('displays black squares correctly', () => {
    const { container } = render(
      <GridEditor {...defaultProps} grid={gridWithBlackSquares} />
    );

    const blackCells = container.querySelectorAll('.cell.black');
    expect(blackCells.length).toBeGreaterThan(0);
  });

  it('supports keyboard navigation with arrow keys', async () => {
    const user = userEvent.setup();
    const onCellSelect = vi.fn();

    render(<GridEditor {...defaultProps} onCellSelect={onCellSelect} />);

    const cells = screen.getAllByRole('gridcell');
    await user.click(cells[0]);

    await user.keyboard('{ArrowRight}');
    expect(onCellSelect).toHaveBeenCalledWith(expect.objectContaining({ col: 1 }));

    await user.keyboard('{ArrowDown}');
    expect(onCellSelect).toHaveBeenCalledWith(expect.objectContaining({ row: 1 }));
  });

  it('handles Backspace to clear cell', async () => {
    const user = userEvent.setup();
    const onCellChange = vi.fn();

    render(<GridEditor {...defaultProps} onCellChange={onCellChange} />);

    const cells = screen.getAllByRole('gridcell');
    await user.click(cells[0]);
    await user.keyboard('{Backspace}');

    expect(onCellChange).toHaveBeenCalledWith(0, 0, '');
  });
});
