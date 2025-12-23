import React, { useState, useCallback, useEffect } from 'react';
import GridEditor from './components/GridEditor';
import PatternMatcher from './components/PatternMatcher';
import ToolPanel from './components/ToolPanel';
import AutofillPanel from './components/AutofillPanel';
import ExportPanel from './components/ExportPanel';
import WordListPanel from './components/WordListPanel';
import './styles/App.scss';

function App() {
  const [gridSize, setGridSize] = useState(15);
  const [grid, setGrid] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);
  const [numbering, setNumbering] = useState({});
  const [validationErrors, setValidationErrors] = useState([]);
  const [autofillProgress, setAutofillProgress] = useState(null);
  const [currentTool, setCurrentTool] = useState('edit'); // edit, pattern, autofill, export, wordlists

  // Initialize empty grid
  useEffect(() => {
    initializeGrid(gridSize);
  }, [gridSize]);

  const initializeGrid = (size) => {
    const newGrid = Array(size).fill(null).map(() =>
      Array(size).fill(null).map(() => ({
        letter: '',
        isBlack: false,
        number: null,
        isError: false,
        isHighlighted: false
      }))
    );
    setGrid(newGrid);
    updateNumbering(newGrid);
  };

  const updateNumbering = useCallback((gridData) => {
    // Calculate numbering based on grid state
    const numbers = {};
    let currentNumber = 1;

    for (let row = 0; row < gridData.length; row++) {
      for (let col = 0; col < gridData[row].length; col++) {
        const cell = gridData[row][col];
        if (cell.isBlack) continue;

        const needsNumber =
          (isStartOfAcrossWord(gridData, row, col) ||
           isStartOfDownWord(gridData, row, col));

        if (needsNumber) {
          numbers[`${row},${col}`] = currentNumber;
          gridData[row][col].number = currentNumber;
          currentNumber++;
        } else {
          gridData[row][col].number = null;
        }
      }
    }

    setNumbering(numbers);
  }, []);

  const isStartOfAcrossWord = (gridData, row, col) => {
    if (col === 0 || gridData[row][col - 1].isBlack) {
      // Check if there's at least one more non-black cell to the right
      return col < gridData[row].length - 1 && !gridData[row][col + 1].isBlack;
    }
    return false;
  };

  const isStartOfDownWord = (gridData, row, col) => {
    if (row === 0 || gridData[row - 1][col].isBlack) {
      // Check if there's at least one more non-black cell below
      return row < gridData.length - 1 && !gridData[row + 1][col].isBlack;
    }
    return false;
  };

  const toggleBlackSquare = useCallback((row, col) => {
    if (!grid) return;

    const newGrid = [...grid.map(row => [...row])];
    const cell = newGrid[row][col];
    cell.isBlack = !cell.isBlack;
    cell.letter = cell.isBlack ? '' : cell.letter;

    // Apply symmetry
    const symRow = gridSize - 1 - row;
    const symCol = gridSize - 1 - col;
    newGrid[symRow][symCol].isBlack = cell.isBlack;
    newGrid[symRow][symCol].letter = cell.isBlack ? '' : newGrid[symRow][symCol].letter;

    setGrid(newGrid);
    updateNumbering(newGrid);
    validateGrid(newGrid);
  }, [grid, gridSize]);

  const setLetter = useCallback((row, col, letter) => {
    if (!grid || grid[row][col].isBlack) return;

    const newGrid = [...grid.map(row => [...row])];
    newGrid[row][col].letter = letter.toUpperCase();
    setGrid(newGrid);
    validateGrid(newGrid);
  }, [grid]);

  const validateGrid = useCallback((gridData) => {
    const errors = [];

    // Check for disconnected regions
    // Check for words shorter than 3 letters
    // Check for unchecked squares
    // etc.

    setValidationErrors(errors);
  }, []);

  const handlePatternSelect = useCallback((word) => {
    // Fill word into grid at selected position
    if (!selectedCell || !grid) return;

    const { row, col, direction } = selectedCell;
    const newGrid = [...grid.map(row => [...row])];

    for (let i = 0; i < word.length; i++) {
      if (direction === 'across') {
        if (col + i < gridSize) {
          newGrid[row][col + i].letter = word[i];
        }
      } else {
        if (row + i < gridSize) {
          newGrid[row + i][col].letter = word[i];
        }
      }
    }

    setGrid(newGrid);
    validateGrid(newGrid);
  }, [selectedCell, grid, gridSize]);

  const handleAutofill = useCallback(async (options = {}) => {
    setAutofillProgress({ status: 'running', progress: 0, message: 'Starting autofill...' });

    try {
      // Start autofill with progress tracking
      const initResponse = await fetch('/api/fill/with-progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          size: gridSize,
          grid: grid.map(row => row.map(cell =>
            cell.isBlack ? '#' : (cell.letter || '.')
          )),
          wordlists: options.wordlists || ['comprehensive'],
          timeout: options.timeout || 300,
          min_score: options.minScore || 30,
          algorithm: options.algorithm || 'regex'
        })
      });

      const { task_id } = await initResponse.json();

      // Connect to SSE for progress updates
      const eventSource = new EventSource(`/api/progress/${task_id}`);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setAutofillProgress({
            status: data.status || 'running',
            progress: data.progress || 0,
            message: data.message || 'Processing...'
          });

          // Apply incremental grid updates if present
          if (data.data && data.data.grid && data.status === 'running') {
            const newGrid = [...grid.map(row => [...row])];
            data.data.grid.forEach((row, r) => {
              row.forEach((cell, c) => {
                if (cell !== '#' && cell !== '.') {
                  newGrid[r][c].letter = cell;
                }
              });
            });
            setGrid(newGrid);
          }

          // When complete, update grid with results from event data
          if (data.status === 'complete') {
            eventSource.close();

            // Check if result grid is included in the event
            if (data.data && data.data.grid) {
              // Update grid with filled results (full or partial)
              const newGrid = [...grid.map(row => [...row])];
              data.data.grid.forEach((row, r) => {
                row.forEach((cell, c) => {
                  if (cell !== '#' && cell !== '.') {
                    newGrid[r][c].letter = cell;
                  }
                });
              });
              setGrid(newGrid);

              // Show appropriate message based on success
              if (data.data.success) {
                setAutofillProgress({
                  status: 'complete',
                  progress: 100,
                  message: `Successfully filled ${data.data.slots_filled}/${data.data.total_slots} slots!`
                });
              } else {
                // Partial fill with suggestions
                const fillPct = data.data.fill_percentage || 0;
                let message = `Partial: ${data.data.slots_filled}/${data.data.total_slots} slots (${fillPct}%)`;

                // Add first suggestion if available
                if (data.data.suggestions && data.data.suggestions.length > 0) {
                  message += ` - ${data.data.suggestions[0].message}`;
                }

                setAutofillProgress({
                  status: fillPct > 0 ? 'warning' : 'error',
                  progress: fillPct,
                  message: message
                });
              }
            } else {
              setAutofillProgress({ status: 'error', progress: 0, message: 'No solution found' });
            }
          } else if (data.status === 'error') {
            eventSource.close();
            setAutofillProgress({ status: 'error', progress: 0, message: data.message || 'Autofill failed' });
          }
        } catch (error) {
          console.error('Failed to parse SSE event:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        eventSource.close();
        setAutofillProgress({ status: 'error', progress: 0, message: 'Connection error' });
      };

    } catch (error) {
      setAutofillProgress({ status: 'error', progress: 0, message: error.message });
    }
  }, [grid, gridSize]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <h1>Crossword Helper</h1>
          <span className="version">v2.0 Advanced</span>
        </div>
        <div className="header-tools">
          <button
            className={`tool-btn ${currentTool === 'edit' ? 'active' : ''}`}
            onClick={() => setCurrentTool('edit')}
          >
            Grid Editor
          </button>
          <button
            className={`tool-btn ${currentTool === 'pattern' ? 'active' : ''}`}
            onClick={() => setCurrentTool('pattern')}
          >
            Pattern Search
          </button>
          <button
            className={`tool-btn ${currentTool === 'autofill' ? 'active' : ''}`}
            onClick={() => setCurrentTool('autofill')}
          >
            Autofill
          </button>
          <button
            className={`tool-btn ${currentTool === 'export' ? 'active' : ''}`}
            onClick={() => setCurrentTool('export')}
          >
            Export
          </button>
          <button
            className={`tool-btn ${currentTool === 'wordlists' ? 'active' : ''}`}
            onClick={() => setCurrentTool('wordlists')}
          >
            Word Lists
          </button>
        </div>
      </header>

      <div className="app-body">
        <div className="main-panel">
          <GridEditor
            grid={grid}
            gridSize={gridSize}
            selectedCell={selectedCell}
            onSelectCell={setSelectedCell}
            onToggleBlack={toggleBlackSquare}
            onSetLetter={setLetter}
            validationErrors={validationErrors}
            numbering={numbering}
          />
        </div>

        <div className="side-panel">
          {currentTool === 'edit' && (
            <ToolPanel
              gridSize={gridSize}
              onSizeChange={setGridSize}
              onClearGrid={() => initializeGrid(gridSize)}
              validationErrors={validationErrors}
              gridStats={grid ? calculateGridStats(grid) : null}
            />
          )}

          {currentTool === 'pattern' && (
            <PatternMatcher
              selectedCell={selectedCell}
              onSelectWord={handlePatternSelect}
            />
          )}

          {currentTool === 'autofill' && (
            <AutofillPanel
              onStartAutofill={handleAutofill}
              progress={autofillProgress}
              grid={grid}
            />
          )}

          {currentTool === 'export' && (
            <ExportPanel
              grid={grid}
              gridSize={gridSize}
              numbering={numbering}
            />
          )}

          {currentTool === 'wordlists' && (
            <WordListPanel />
          )}
        </div>
      </div>
    </div>
  );
}

function calculateGridStats(grid) {
  let blackSquares = 0;
  let filledCells = 0;
  let totalCells = grid.length * grid.length;

  grid.forEach(row => {
    row.forEach(cell => {
      if (cell.isBlack) blackSquares++;
      else if (cell.letter) filledCells++;
    });
  });

  return {
    totalCells,
    blackSquares,
    blackSquarePercent: ((blackSquares / totalCells) * 100).toFixed(1),
    filledCells,
    fillPercent: ((filledCells / (totalCells - blackSquares)) * 100).toFixed(1)
  };
}

export default App;