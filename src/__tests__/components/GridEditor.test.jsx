/**
 * Tests for GridEditor - interactive crossword grid (SVG-based)
 * Tests cell selection, letter entry, keyboard navigation, black squares, theme locking
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GridEditor from '../../components/GridEditor';
import { emptyGrid11x11, gridWithBlackSquares } from '../fixtures/gridFixtures';

describe('GridEditor Component', () => {
  const defaultProps = {
    grid: emptyGrid11x11,
    gridSize: 11,
    selectedCell: { row: 0, col: 0, direction: 'across' },
    onSelectCell: vi.fn(),
    onToggleBlack: vi.fn(),
    onSetLetter: vi.fn(),
    onToggleThemeLock: vi.fn(),
    validationErrors: [],
    numbering: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders grid with correct number of cells', () => {
    const { container } = render(<GridEditor {...defaultProps} />);
    const cells = container.querySelectorAll('.grid-cell');
    expect(cells.length).toBe(11 * 11);
  });

  it('handles cell click selection', async () => {
    const onSelectCell = vi.fn();
    const { container } = render(
      <GridEditor {...defaultProps} onSelectCell={onSelectCell} />
    );

    const cells = container.querySelectorAll('.grid-cell');
    // fireEvent.click works better for SVG elements than userEvent
    fireEvent.click(cells[5]);

    expect(onSelectCell).toHaveBeenCalled();
  });

  it('allows typing letters via hidden input', async () => {
    const user = userEvent.setup();
    const onSetLetter = vi.fn();
    const { container } = render(
      <GridEditor {...defaultProps} onSetLetter={onSetLetter} />
    );

    // Click a cell to focus it
    const cells = container.querySelectorAll('.grid-cell');
    fireEvent.click(cells[0]);

    // Type into the hidden input
    const hiddenInput = container.querySelector('.hidden-input');
    fireEvent.keyDown(hiddenInput, { key: 'C' });

    expect(onSetLetter).toHaveBeenCalledWith(0, 0, 'C');
  });

  it('toggles black squares on Shift+Click', () => {
    const onToggleBlack = vi.fn();
    const { container } = render(
      <GridEditor {...defaultProps} onToggleBlack={onToggleBlack} />
    );

    const cells = container.querySelectorAll('.grid-cell');
    fireEvent.click(cells[0], { shiftKey: true });

    expect(onToggleBlack).toHaveBeenCalledWith(0, 0);
  });

  it('displays black squares correctly', () => {
    const { container } = render(
      <GridEditor {...defaultProps} grid={gridWithBlackSquares} gridSize={15} />
    );

    // Black cells get fill="#333"
    const allCells = container.querySelectorAll('.grid-cell');
    const blackCells = Array.from(allCells).filter(
      cell => cell.getAttribute('fill') === '#333'
    );
    expect(blackCells.length).toBeGreaterThan(0);
  });

  it('supports keyboard navigation with arrow keys', () => {
    const { container } = render(<GridEditor {...defaultProps} />);

    // Click first cell to set focusedCell
    const cells = container.querySelectorAll('.grid-cell');
    fireEvent.click(cells[0]);

    // Navigate via hidden input keyDown
    const hiddenInput = container.querySelector('.hidden-input');
    fireEvent.keyDown(hiddenInput, { key: 'ArrowRight' });

    // The component updates internal focusedCell state (col: 1)
    // We can verify by pressing a letter and checking the coordinates
    fireEvent.keyDown(hiddenInput, { key: 'A' });
    expect(defaultProps.onSetLetter).toHaveBeenCalledWith(0, 1, 'A');
  });

  it('handles Backspace to clear cell', () => {
    const onSetLetter = vi.fn();
    const { container } = render(
      <GridEditor {...defaultProps} onSetLetter={onSetLetter} />
    );

    // Click a cell to focus it
    const cells = container.querySelectorAll('.grid-cell');
    fireEvent.click(cells[0]);

    // Press Backspace on hidden input
    const hiddenInput = container.querySelector('.hidden-input');
    fireEvent.keyDown(hiddenInput, { key: 'Backspace' });

    expect(onSetLetter).toHaveBeenCalledWith(0, 0, '');
  });
});
