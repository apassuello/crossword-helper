import React, { useState, useCallback, useEffect } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import GridEditor from './components/GridEditor';
import PatternMatcher from './components/PatternMatcher';
import ToolPanel from './components/ToolPanel';
import AutofillPanel from './components/AutofillPanel';
import ExportPanel from './components/ExportPanel';
import ImportPanel from './components/ImportPanel';
import WordListPanel from './components/WordListPanel';
import './styles/App.scss';

function App() {
  const [gridSize, setGridSize] = useState(15);
  const [grid, setGrid] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);
  const [numbering, setNumbering] = useState({});
  const [validationErrors, setValidationErrors] = useState([]);
  const [autofillProgress, setAutofillProgress] = useState(null);
  const [currentTool, setCurrentTool] = useState('edit'); // edit, pattern, autofill, import, export, wordlists
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const eventSourceRef = React.useRef(null);

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
        isHighlighted: false,
        isThemeLocked: false  // Phase 3: Theme entry locking
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

  const toggleThemeLock = useCallback((row, col) => {
    if (!grid || grid[row][col].isBlack) return;

    // Create deep copy with new objects
    const newGrid = grid.map((gridRow, r) =>
      gridRow.map((cell, c) => {
        if (r === row && c === col) {
          return { ...cell, isThemeLocked: !cell.isThemeLocked };
        }
        return { ...cell };
      })
    );

    setGrid(newGrid);
  }, [grid]);

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

  const handleSaveGrid = useCallback(() => {
    try {
      const gridData = {
        size: gridSize,
        grid: grid.map(row => row.map(cell => ({
          letter: cell.letter || '',
          isBlack: cell.isBlack || false,
          isThemeLocked: cell.isThemeLocked || false,
          number: cell.number || null
        }))),
        numbering: numbering,
        timestamp: new Date().toISOString()
      };

      localStorage.setItem('crossword_saved_grid', JSON.stringify(gridData));
      toast.success('Grid saved successfully to browser storage!');
    } catch (err) {
      console.error('Failed to save grid:', err);
      toast.error('Failed to save grid: ' + err.message);
    }
  }, [grid, gridSize, numbering]);

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
          algorithm: options.algorithm || 'regex',
          theme_entries: options.theme_entries || {}
        })
      });

      const { task_id } = await initResponse.json();
      setCurrentTaskId(task_id);

      // Connect to SSE for progress updates
      const eventSource = new EventSource(`/api/progress/${task_id}`);
      eventSourceRef.current = eventSource;

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
            // Create deep copy with new objects (not shallow copy)
            const newGrid = grid.map((row, r) =>
              row.map((cell, c) => {
                const cliCell = data.data.grid[r][c];
                if (cliCell === '#') {
                  return { ...cell, isBlack: true };
                } else if (cliCell !== '#' && cliCell !== '.' && cliCell !== '') {
                  return { ...cell, letter: cliCell };
                }
                return { ...cell };
              })
            );
            setGrid(newGrid);
          }

          // When complete, update grid with results from event data
          if (data.status === 'complete') {
            eventSource.close();
            eventSourceRef.current = null;
            setCurrentTaskId(null);

            // Check if result grid is included in the event
            if (data.data && data.data.grid) {
              // Update grid with filled results (full or partial) - create deep copy with new objects
              const newGrid = grid.map((row, r) =>
                row.map((cell, c) => {
                  const cliCell = data.data.grid[r][c];
                  if (cliCell === '#') {
                    return { ...cell, isBlack: true };
                  } else if (cliCell !== '#' && cliCell !== '.' && cliCell !== '') {
                    return { ...cell, letter: cliCell };
                  }
                  return { ...cell };
                })
              );
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
          } else if (data.status === 'paused') {
            // Autofill was paused - close connection and show paused state
            eventSource.close();
            eventSourceRef.current = null;
            setAutofillProgress({
              status: 'paused',
              progress: data.progress || 0,
              message: data.message || 'Autofill paused - state saved'
            });
            // currentTaskId is kept for future pause operations
            toast.success('Autofill paused successfully! You can resume later.');
          } else if (data.status === 'error') {
            eventSource.close();
            eventSourceRef.current = null;
            setCurrentTaskId(null);
            setAutofillProgress({ status: 'error', progress: 0, message: data.message || 'Autofill failed' });
          }
        } catch (error) {
          console.error('Failed to parse SSE event:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        eventSource.close();
        eventSourceRef.current = null;
        setCurrentTaskId(null);
        setAutofillProgress({ status: 'error', progress: 0, message: 'Connection error' });
      };

    } catch (error) {
      setAutofillProgress({ status: 'error', progress: 0, message: error.message });
    }
  }, [grid, gridSize]);

  const handleCancelAutofill = useCallback(() => {
    // Close SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Update progress to cancelled state
    setAutofillProgress({
      status: 'error',
      progress: autofillProgress?.progress || 0,
      message: 'Cancelled by user'
    });

    // Clear task ID
    setCurrentTaskId(null);

    // Optional: Call backend to kill the process (for cleaner cancellation)
    if (currentTaskId) {
      fetch(`/api/cancel/${currentTaskId}`, { method: 'POST' }).catch(err => {
        console.warn('Failed to signal backend cancellation:', err);
      });
    }
  }, [currentTaskId, autofillProgress]);

  const handleGridImport = useCallback((importedData) => {
    const { grid: importedGrid, size, numbering: importedNumbering } = importedData;

    // Update grid size if different
    if (size !== gridSize) {
      setGridSize(size);
    }

    // Update grid state
    setGrid(importedGrid);

    // Update numbering (or recalculate if not provided)
    if (importedNumbering && Object.keys(importedNumbering).length > 0) {
      setNumbering(importedNumbering);
      // Apply numbering to grid cells
      Object.entries(importedNumbering).forEach(([coords, number]) => {
        const [row, col] = coords.split(',').map(Number);
        if (importedGrid[row] && importedGrid[row][col]) {
          importedGrid[row][col].number = number;
        }
      });
    } else {
      // Recalculate numbering if not provided
      updateNumbering(importedGrid);
    }

    // Validate the imported grid
    validateGrid(importedGrid);

    // Switch to edit tool to show the imported grid
    setCurrentTool('edit');
  }, [gridSize, updateNumbering, validateGrid]);

  return (
    <div className="app">
      <Toaster
        position="top-right"
        toastOptions={{
          success: {
            duration: 3000,
            style: {
              background: '#4caf50',
              color: '#fff',
            },
          },
          error: {
            duration: 4000,
            style: {
              background: '#f44336',
              color: '#fff',
            },
          },
        }}
      />
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
            className={`tool-btn ${currentTool === 'import' ? 'active' : ''}`}
            onClick={() => setCurrentTool('import')}
          >
            Import
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
            onToggleThemeLock={toggleThemeLock}
            validationErrors={validationErrors}
            numbering={numbering}
          />
        </div>

        <div className="side-panel">
          {currentTool === 'edit' && (
            <ToolPanel
              gridSize={gridSize}
              onSizeChange={setGridSize}
              onClearGrid={() => {
                if (window.confirm('Clear the entire grid? This cannot be undone.')) {
                  initializeGrid(gridSize);
                }
              }}
              onLoadGrid={() => setCurrentTool('import')}
              onSaveGrid={handleSaveGrid}
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
              onCancelAutofill={handleCancelAutofill}
              progress={autofillProgress}
              grid={grid}
              currentTaskId={currentTaskId}
            />
          )}

          {currentTool === 'import' && (
            <ImportPanel
              onImport={handleGridImport}
              currentGridSize={gridSize}
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