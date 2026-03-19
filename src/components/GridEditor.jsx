import React, { useState, useRef, useEffect } from 'react';
import classNames from 'classnames';
import './GridEditor.scss';

const CELL_SIZE = 40;
const GRID_PADDING = 20;

function GridEditor({
  grid,
  gridSize,
  selectedCell,
  onSelectCell,
  onToggleBlack,
  onSetLetter,
  onToggleThemeLock,
  validationErrors,
  numbering
}) {
  const [hoveredCell, setHoveredCell] = useState(null);
  const [focusedCell, setFocusedCell] = useState(null);
  const inputRef = useRef(null);
  const svgRef = useRef(null);

  useEffect(() => {
    // Focus input when cell is selected
    if (focusedCell && inputRef.current) {
      inputRef.current.focus();
    }
  }, [focusedCell]);

  if (!grid) return <div className="grid-editor-loading">Initializing grid...</div>;

  const handleCellClick = (row, col, e) => {
    e.preventDefault();

    if (e.shiftKey || e.metaKey) {
      // Toggle black square
      onToggleBlack(row, col);
    } else {
      // Select cell for editing
      setFocusedCell({ row, col });
      onSelectCell({ row, col, direction: e.altKey ? 'down' : 'across' });
    }
  };

  const handleCellRightClick = (row, col, e) => {
    e.preventDefault();  // Prevent context menu
    if (onToggleThemeLock) {
      onToggleThemeLock(row, col);
    }
  };

  const handleKeyDown = (e) => {
    if (!focusedCell) return;

    const { row, col } = focusedCell;

    // Ctrl/Cmd+L to toggle theme lock
    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
      e.preventDefault();
      if (onToggleThemeLock) {
        onToggleThemeLock(row, col);
      }
      return;
    }

    if (e.key === 'ArrowUp' && row > 0) {
      setFocusedCell({ row: row - 1, col });
    } else if (e.key === 'ArrowDown' && row < gridSize - 1) {
      setFocusedCell({ row: row + 1, col });
    } else if (e.key === 'ArrowLeft' && col > 0) {
      setFocusedCell({ row, col: col - 1 });
    } else if (e.key === 'ArrowRight' && col < gridSize - 1) {
      setFocusedCell({ row, col: col + 1 });
    } else if (e.key === ' ' || e.key === '.') {
      // Toggle black square - but not on theme-locked cells
      if (grid[row][col].isThemeLocked) {
        e.preventDefault();
        return; // Cannot toggle black on locked cells
      }
      onToggleBlack(row, col);
    } else if (e.key === 'Backspace' || e.key === 'Delete') {
      // Clear cell - but not theme-locked cells
      if (grid[row][col].isThemeLocked) {
        e.preventDefault();
        return; // Cannot clear locked cells
      }
      onSetLetter(row, col, '');
      // Move to previous cell if backspace
      if (e.key === 'Backspace') {
        if (col > 0) {
          setFocusedCell({ row, col: col - 1 });
        } else if (row > 0) {
          setFocusedCell({ row: row - 1, col: gridSize - 1 });
        }
      }
    } else if (/^[A-Za-z]$/.test(e.key)) {
      // Set letter and advance - but not on theme-locked cells
      if (grid[row][col].isThemeLocked) {
        e.preventDefault();
        return; // Cannot edit locked cells
      }
      onSetLetter(row, col, e.key);
      // Auto-advance to next cell
      if (col < gridSize - 1) {
        setFocusedCell({ row, col: col + 1 });
      } else if (row < gridSize - 1) {
        setFocusedCell({ row: row + 1, col: 0 });
      }
    } else if (e.key === 'Tab') {
      e.preventDefault();
      // Move to next word start
      moveToNextWord(row, col, !e.shiftKey);
    }
  };

  const moveToNextWord = (row, col, forward = true) => {
    // Find next numbered cell
    const cells = [];
    for (let r = 0; r < gridSize; r++) {
      for (let c = 0; c < gridSize; c++) {
        if (grid[r][c].number) {
          cells.push({ row: r, col: c, number: grid[r][c].number });
        }
      }
    }

    const currentIndex = cells.findIndex(cell => cell.row === row && cell.col === col);
    if (currentIndex >= 0) {
      const nextIndex = forward
        ? (currentIndex + 1) % cells.length
        : (currentIndex - 1 + cells.length) % cells.length;
      const nextCell = cells[nextIndex];
      setFocusedCell({ row: nextCell.row, col: nextCell.col });
    }
  };

  const getHighlightedCells = () => {
    if (!selectedCell) return new Set();

    const highlighted = new Set();
    const { row, col, direction } = selectedCell;

    if (direction === 'across') {
      // Highlight across word
      for (let c = col; c >= 0 && !grid[row][c].isBlack; c--) {
        highlighted.add(`${row}-${c}`);
      }
      for (let c = col + 1; c < gridSize && !grid[row][c].isBlack; c++) {
        highlighted.add(`${row}-${c}`);
      }
    } else {
      // Highlight down word
      for (let r = row; r >= 0 && !grid[r][col].isBlack; r--) {
        highlighted.add(`${r}-${col}`);
      }
      for (let r = row + 1; r < gridSize && !grid[r][col].isBlack; r++) {
        highlighted.add(`${r}-${col}`);
      }
    }

    return highlighted;
  };

  const highlightedCells = getHighlightedCells();
  const svgWidth = gridSize * CELL_SIZE + 2 * GRID_PADDING;
  const svgHeight = gridSize * CELL_SIZE + 2 * GRID_PADDING;

  return (
    <div className="grid-editor">
      <div className="grid-container" tabIndex={0} onKeyDown={handleKeyDown}>
        <svg
          ref={svgRef}
          width={svgWidth}
          height={svgHeight}
          className="grid-svg"
          onMouseLeave={() => setHoveredCell(null)}
        >
          <defs>
            <pattern id="grid-pattern" patternUnits="userSpaceOnUse" width={CELL_SIZE} height={CELL_SIZE}>
              <rect width={CELL_SIZE} height={CELL_SIZE} fill="white" stroke="#ddd" strokeWidth="1" />
            </pattern>
          </defs>

          {/* Background grid */}
          <rect
            x={GRID_PADDING}
            y={GRID_PADDING}
            width={gridSize * CELL_SIZE}
            height={gridSize * CELL_SIZE}
            fill="url(#grid-pattern)"
            stroke="#999"
            strokeWidth="2"
          />

          {/* Grid cells */}
          {grid.map((row, rowIdx) =>
            row.map((cell, colIdx) => {
              const x = GRID_PADDING + colIdx * CELL_SIZE;
              const y = GRID_PADDING + rowIdx * CELL_SIZE;
              const cellKey = `${rowIdx}-${colIdx}`;
              const isHighlighted = highlightedCells.has(cellKey);
              const isFocused = focusedCell?.row === rowIdx && focusedCell?.col === colIdx;
              const isHovered = hoveredCell?.row === rowIdx && hoveredCell?.col === colIdx;

              return (
                <g key={cellKey}>
                  {/* Cell background */}
                  <rect
                    x={x}
                    y={y}
                    width={CELL_SIZE}
                    height={CELL_SIZE}
                    fill={
                      cell.isBlack ? '#333' :
                      cell.isThemeLocked ? '#e1bee7' :  // Light purple for theme-locked cells
                      isFocused ? '#ffd700' :
                      isHighlighted ? '#e3f2fd' :
                      isHovered ? '#f5f5f5' :
                      'white'
                    }
                    stroke={
                      cell.isThemeLocked ? '#9c27b0' :  // Purple border for theme-locked
                      cell.isError ? '#f44336' :
                      isFocused ? '#ffa500' :
                      '#ddd'
                    }
                    strokeWidth={cell.isThemeLocked || isFocused ? 2 : 1}
                    className="grid-cell"
                    onClick={(e) => handleCellClick(rowIdx, colIdx, e)}
                    onContextMenu={(e) => handleCellRightClick(rowIdx, colIdx, e)}
                    onMouseEnter={() => setHoveredCell({ row: rowIdx, col: colIdx })}
                    style={{ cursor: 'pointer' }}
                  />

                  {/* Cell number */}
                  {cell.number && (
                    <text
                      x={x + 2}
                      y={y + 10}
                      fontSize="10"
                      fill="#666"
                      className="cell-number"
                      pointerEvents="none"
                    >
                      {cell.number}
                    </text>
                  )}

                  {/* Cell letter */}
                  {cell.letter && !cell.isBlack && (
                    <text
                      x={x + CELL_SIZE / 2}
                      y={y + CELL_SIZE / 2 + 6}
                      fontSize="20"
                      fontWeight="500"
                      textAnchor="middle"
                      fill="#000"
                      className="cell-letter"
                      pointerEvents="none"
                    >
                      {cell.letter}
                    </text>
                  )}

                  {/* Theme lock icon */}
                  {cell.isThemeLocked && !cell.isBlack && (
                    <g transform={`translate(${x + CELL_SIZE - 12}, ${y + CELL_SIZE - 12})`} pointerEvents="none">
                      {/* Lock icon (simplified) */}
                      <circle cx="5" cy="6" r="3.5" fill="none" stroke="#7b1fa2" strokeWidth="1.2"/>
                      <rect x="2" y="6" width="6" height="5" rx="1" fill="#7b1fa2"/>
                      <circle cx="5" cy="8" r="0.8" fill="white"/>
                    </g>
                  )}
                </g>
              );
            })
          )}

          {/* Symmetry indicator lines */}
          {hoveredCell && !grid[hoveredCell.row][hoveredCell.col].isBlack && (
            <>
              <line
                x1={GRID_PADDING + hoveredCell.col * CELL_SIZE + CELL_SIZE / 2}
                y1={GRID_PADDING + hoveredCell.row * CELL_SIZE + CELL_SIZE / 2}
                x2={GRID_PADDING + (gridSize - 1 - hoveredCell.col) * CELL_SIZE + CELL_SIZE / 2}
                y2={GRID_PADDING + (gridSize - 1 - hoveredCell.row) * CELL_SIZE + CELL_SIZE / 2}
                stroke="rgba(156, 39, 176, 0.3)"
                strokeWidth="2"
                strokeDasharray="5,5"
                pointerEvents="none"
              />
              <rect
                x={GRID_PADDING + (gridSize - 1 - hoveredCell.col) * CELL_SIZE}
                y={GRID_PADDING + (gridSize - 1 - hoveredCell.row) * CELL_SIZE}
                width={CELL_SIZE}
                height={CELL_SIZE}
                fill="none"
                stroke="rgba(156, 39, 176, 0.5)"
                strokeWidth="2"
                strokeDasharray="3,3"
                pointerEvents="none"
              />
            </>
          )}
        </svg>

        {/* Hidden input for keyboard handling */}
        <input
          ref={inputRef}
          type="text"
          className="hidden-input"
          value=""
          onChange={() => {}}
          onKeyDown={handleKeyDown}
          style={{ position: 'absolute', left: '-9999px' }}
        />
      </div>

      <div className="grid-instructions">
        <h3>Keyboard Shortcuts</h3>
        <ul>
          <li><kbd>Click</kbd> - Select cell</li>
          <li><kbd>Shift+Click</kbd> - Toggle black square</li>
          <li><kbd>A-Z</kbd> - Enter letter</li>
          <li><kbd>Space</kbd> or <kbd>.</kbd> - Toggle black square</li>
          <li><kbd>Arrow Keys</kbd> - Move between cells</li>
          <li><kbd>Tab</kbd> - Jump to next word</li>
          <li><kbd>Backspace</kbd> - Clear and move back</li>
        </ul>
      </div>
    </div>
  );
}

export default GridEditor;