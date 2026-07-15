import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
// react-hot-toast's <Toaster> is intentionally KEPT: AutofillPanel, ThemeWordsPanel,
// and BlackSquareSuggestions still call toast.* directly. App's own toasts were
// migrated to the bench ToastProvider (pushToast); the default `toast` import is gone.
import { Toaster } from 'react-hot-toast';
import { api } from './api/client';
import { useHealth } from './hooks/useHealth';
import { usePersistentState } from './hooks/usePersistentState';
import { useSaveMachine } from './hooks/useSaveMachine';
import { useToasts } from './components/bench/Toast';
import { allSlots } from './hooks/useGridGeometry';
import { useNumbering } from './hooks/useNumbering';
import { TopBar } from './components/bench/TopBar';
import { ToolRail } from './components/bench/ToolRail';
import CrosswordGrid from './components/bench/CrosswordGrid';
import PatternMatcher from './components/PatternMatcher';
import AutofillPanel from './components/AutofillPanel';
import ExportPanel from './components/ExportPanel';
import ImportPanel from './components/ImportPanel';
import WordListPanel from './components/WordListPanel';
import ThemeWordsPanel from './components/ThemeWordsPanel';
import './styles/App.scss';

// Signature of user-authored grid content, for the save machine's dirty
// tracking. Deliberately array-shaped and limited to durable authored fields:
// it EXCLUDES `number` (derived by auto-renumbering, would spuriously mark
// dirty), the transient isError/isHighlighted flags, and `symmetryEnabled` —
// symmetry is a VIEW construction aid (grouped with Heatmap), persisted on its
// own key via usePersistentState, so toggling it stays silent as it did before
// the save machine (it still rides along in the saved `doc`). Called in every
// place that establishes or compares dirtiness so the strings are byte-identical.
function contentSigOf(size, grid) {
  return JSON.stringify({
    size,
    cells: grid ? grid.map((row) => row.map((c) => [c.letter, c.isBlack, c.isThemeLocked])) : null,
  });
}

function App() {
  const [gridSize, setGridSize] = useState(15);
  const [grid, setGrid] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);
  const [autofillProgress, setAutofillProgress] = useState(null);
  const [currentTool, setCurrentTool] = useState('edit'); // edit, search, autofill, clues, lists, import, export
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [showThemePanel, setShowThemePanel] = useState(false);
  // Black-square symmetry toggle, persisted (JSON boolean). usePersistentState
  // lazy-inits from storage, so a stored `false` survives reload (previously a
  // mount-race reset it to true on every load).
  const [symmetryEnabled, setSymmetryEnabled] = usePersistentState('crossword_symmetry_enabled', true);
  const [heatmapOn, setHeatmapOn] = useState(false); // ToolRail VIEW heatmap on-state (real data is Task 22)
  // Save machine (Task 7). `gridId` is the doc's stable identity: it changes
  // only when a whole new grid is created (init/resize/import), never on an
  // edit, so the machine's F10 reset fires for "new grid" but not for typing.
  // `savedSig` is the content signature considered clean (set on fresh grids and
  // after a successful save); dirtiness is `contentSig !== savedSig`.
  const [gridId, setGridId] = useState(1);
  const [savedSig, setSavedSig] = useState(null);
  // UI dark mode (Task 6), persisted as 'dark'/'light'. usePersistentState owns
  // the lazy-init + persistence (see its mount-race note); the effect below only
  // applies the theme to the document.
  const [dark, setDark] = usePersistentState('xw_theme', false, {
    parse: (v) => v === 'dark',
    serialize: (v) => (v ? 'dark' : 'light'),
  });
  const eventSourceRef = React.useRef(null);

  const health = useHealth();
  const { pushToast } = useToasts();

  // Server-authoritative numbering + validation (Task 8, F2). Replaces the former
  // client-only word-start numbering pass and the validation stub: fires on
  // STRUCTURAL edits only (size / black-square layout — never letter edits),
  // renumbers server-wins after an optimistic local paint, and surfaces advisory
  // `violations`. `unverified` is true while an optimistic pass awaits reconcile.
  // Must precede `doc` below (which reads `numbering`).
  const { numbering, violations, unverified } = useNumbering({ grid, gridSize, setGrid, pushToast });

  // Save machine wiring (Task 7). `doc` is the full serializable grid document
  // (saved verbatim); `isDirty` is derived by comparing the current content
  // signature to the last-clean one.
  const contentSig = useMemo(() => contentSigOf(gridSize, grid), [gridSize, grid]);
  const isDirty = grid != null && contentSig !== savedSig;
  const doc = useMemo(
    () => ({ id: gridId, size: gridSize, grid, numbering, symmetryEnabled }),
    [gridId, gridSize, grid, numbering, symmetryEnabled]
  );
  const { savedLabel, save: saveDoc, status: saveStatus } = useSaveMachine({ doc, isDirty });

  // When a save lands, snapshot the current content as clean. Keyed on
  // saveStatus ONLY (adding contentSig here would re-mark clean on every edit
  // while 'saved' and dirtiness would never re-trigger) — sig read from a ref.
  const contentSigRef = useRef(contentSig);
  contentSigRef.current = contentSig;
  useEffect(() => {
    if (saveStatus === 'saved') setSavedSig(contentSigRef.current);
  }, [saveStatus]);

  // Initialize empty grid
  useEffect(() => {
    initializeGrid(gridSize);
  }, [gridSize]);

  // Apply the UI theme to the document whenever it changes (Task 6). Persistence
  // is owned by usePersistentState above; TopBar is a controlled toggle and
  // never touches document/storage.
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  }, [dark]);

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
    // Numbering is now hook-driven (useNumbering): setting the grid changes the
    // structural signature, which fires the optimistic renumber + server reconcile.
    // A fresh grid is a new document (F10) and is born clean.
    setGridId((n) => n + 1);
    setSavedSig(contentSigOf(size, newGrid));
  };

  const toggleBlackSquare = useCallback((row, col) => {
    if (!grid) return;

    const newGrid = [...grid.map(row => [...row])];
    const cell = newGrid[row][col];
    cell.isBlack = !cell.isBlack;
    cell.letter = cell.isBlack ? '' : cell.letter;

    // Apply symmetry only if enabled
    if (symmetryEnabled) {
      const symRow = gridSize - 1 - row;
      const symCol = gridSize - 1 - col;
      newGrid[symRow][symCol].isBlack = cell.isBlack;
      newGrid[symRow][symCol].letter = cell.isBlack ? '' : newGrid[symRow][symCol].letter;
    }

    setGrid(newGrid);
    // Structural edit: useNumbering renumbers (server-wins) + revalidates off the
    // black-square layout change. No manual renumber/validate here.
  }, [grid, gridSize, symmetryEnabled]);

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
    // Letter edit — never renumbers/revalidates (plan Global Constraint 3).
  }, [grid]);

  // Controlled-grid focus/direction handlers (CrosswordGrid, Task 5).
  // selectedCell {row,col,direction} maps to focus {row,col} + selectedDir=direction.
  // Arrow keys and Tab-with-switch each dispatch BOTH onMoveFocus and onRotateDir in one
  // event, and both mutate selectedCell — use functional updates so neither clobbers the
  // other under React batching.
  const handleGridFocus = useCallback((row, col) => {
    setSelectedCell(prev => ({ row, col, direction: prev?.direction || 'across' }));
  }, []);

  const handleGridMoveFocus = useCallback((row, col) => {
    setSelectedCell(prev => ({ row, col, direction: prev?.direction || 'across' }));
  }, []);

  const handleGridRotateDir = useCallback(() => {
    setSelectedCell(prev => {
      const base = prev || { row: 0, col: 0, direction: 'across' };
      return { ...base, direction: base.direction === 'across' ? 'down' : 'across' };
    });
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
    // Letter fill — no renumber/validate (structural signature unchanged).
  }, [selectedCell, grid, gridSize]);

  const handleAutofill = useCallback(async (options = {}) => {
    setAutofillProgress({ status: 'running', progress: 0, message: 'Starting autofill...' });

    try {
      // Start autofill with progress tracking
      const { task_id } = await api.startFill({
        size: gridSize,
        grid: grid.map(row => row.map(cell =>
          cell.isBlack ? '#' : (cell.letter || '.')
        )),
        wordlists: options.wordlists || ['comprehensive'],
        timeout: options.timeout || 300,
        min_score: options.minScore ?? 50,
        algorithm: options.algorithm || 'repair',
        theme_entries: options.theme_entries || {},
        adaptive_mode: options.adaptiveMode || false,
        max_adaptations: options.maxAdaptations || 3,
        partial_fill: options.partialFill || false,
        cleanup: options.cleanup || false
      });

      setCurrentTaskId(task_id);

      // Connect to SSE for progress updates
      const progress = api.openProgress(task_id, {
        onEvent: (data) => {
          try {
            setAutofillProgress({
              status: data.status || 'running',
              progress: data.progress || 0,
              message: data.message || 'Processing...'
            });

            // Apply incremental grid updates if present
            if (data.data && data.data.grid && data.status === 'running') {
              // Create deep copy with new objects (not shallow copy)
              setGrid(prevGrid => prevGrid.map((row, r) =>
                row.map((cell, c) => {
                  // Never overwrite theme-locked cells
                  if (cell.isThemeLocked) return cell;
                  const cliCell = data.data.grid[r][c];
                  if (cliCell === '#') {
                    return { ...cell, isBlack: true };
                  } else if (cliCell === '.' || cliCell === '') {
                    return { ...cell, letter: '' };
                  } else {
                    return { ...cell, letter: cliCell };
                  }
                })
              ));
            }

            // When complete, update grid with results from event data
            if (data.status === 'complete') {
              eventSourceRef.current?.close();
              eventSourceRef.current = null;
              setCurrentTaskId(null);

              // Check if result grid is included in the event
              if (data.data && data.data.grid) {
                // Update grid with filled results (full or partial) - create deep copy with new objects
                setGrid(prevGrid => prevGrid.map((row, r) =>
                  row.map((cell, c) => {
                    // Never overwrite theme-locked cells
                    if (cell.isThemeLocked) return cell;
                    const cliCell = data.data.grid[r][c];
                    if (cliCell === '#') {
                      return { ...cell, isBlack: true };
                    } else if (cliCell === '.' || cliCell === '') {
                      return { ...cell, letter: '' };
                    } else {
                      return { ...cell, letter: cliCell };
                    }
                  })
                ));

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
              eventSourceRef.current?.close();
              eventSourceRef.current = null;
              setAutofillProgress({
                status: 'paused',
                progress: data.progress || 0,
                message: data.message || 'Autofill paused - state saved'
              });
              // currentTaskId is kept for future pause operations
              pushToast({ kind: 'info', message: 'Autofill paused successfully! You can resume later.' });
            } else if (data.status === 'error') {
              eventSourceRef.current?.close();
              eventSourceRef.current = null;
              setCurrentTaskId(null);
              setAutofillProgress({ status: 'error', progress: 0, message: data.message || 'Autofill failed' });
            }
          } catch (error) {
            console.error('Failed to parse SSE event:', error);
          }
        },
        onError: (error) => {
          console.error('SSE error:', error);
          eventSourceRef.current?.close();
          eventSourceRef.current = null;
          setCurrentTaskId(null);
          setAutofillProgress({ status: 'error', progress: 0, message: 'Connection error' });
        },
      });
      eventSourceRef.current = progress;

    } catch (error) {
      setAutofillProgress({ status: 'error', progress: 0, message: error.message });
    }
  }, [grid, gridSize, pushToast]);

  const handleCancelAutofill = useCallback(() => {
    // Capture task ID before clearing state
    const taskId = currentTaskId;

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

    // Call backend to cancel the task
    if (taskId) {
      api.cancelFill(taskId).catch(err => {
        console.warn('Failed to cancel autofill task:', err);
      });
    }
  }, [currentTaskId, autofillProgress]);

  const handleResetAutofill = useCallback(() => {
    // Close SSE connection if active
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Clear all autofill state
    setAutofillProgress(null);
    setCurrentTaskId(null);

    // Clear localStorage autofill state
    localStorage.removeItem('current_autofill_task');
    localStorage.removeItem('paused_autofill_task');

    pushToast({ kind: 'info', message: 'Autofill state reset - ready to start fresh!' });
  }, [pushToast]);

  const handleVerifyWords = useCallback(async () => {
    if (!grid) return;

    try {
      const { invalid_words, invalid_count, total_checked, wordlist_size } = await api.verifyWords({
        grid: grid.map(row => row.map(cell => ({
          letter: cell.letter || '',
          isBlack: cell.isBlack || false
        }))),
        size: gridSize,
        wordlists: ['comprehensive']
      });

      // Build set of cells that belong to invalid words
      const errorCells = new Set();
      invalid_words.forEach(({ cells }) => {
        cells.forEach(([r, c]) => errorCells.add(`${r},${c}`));
      });

      // Update grid: set isError on invalid cells, clear on valid ones
      const newGrid = grid.map((row, r) =>
        row.map((cell, c) => ({
          ...cell,
          isError: errorCells.has(`${r},${c}`)
        }))
      );
      setGrid(newGrid);

      if (invalid_count === 0) {
        pushToast({ kind: 'info', message: `All ${total_checked} words valid!` });
      } else {
        const invalid = invalid_words.filter(w => w.status === 'invalid');
        const unfillable = invalid_words.filter(w => w.status === 'unfillable');
        const parts = [];
        if (invalid.length > 0) {
          parts.push(`${invalid.length} invalid: ${invalid.map(w => w.word).join(', ')}`);
        }
        if (unfillable.length > 0) {
          parts.push(`${unfillable.length} unfillable: ${unfillable.map(w => w.word.replace(/\?/g, '_')).join(', ')}`);
        }
        pushToast({
          kind: 'error',
          message: `${invalid_count} of ${total_checked} words flagged — ${parts.join('; ')}`,
        });
      }
    } catch (error) {
      console.error('Verify words failed:', error);
      pushToast({ kind: 'error', message: 'Failed to verify words: ' + error.message });
    }
  }, [grid, gridSize, pushToast]);

  const handleCleanGrid = useCallback(async () => {
    if (!grid) return;

    try {
      const { grid: cleanedGrid, removed_count, valid_count, cleared_cells, message } = await api.cleanGrid({
        grid: grid.map(row => row.map(cell => ({
          letter: cell.letter || '',
          isBlack: cell.isBlack || false
        }))),
        size: gridSize
      });

      if (removed_count === 0) {
        pushToast({ kind: 'info', message: 'Grid is clean — all words are valid!' });
        return;
      }

      // Update grid with cleaned result
      const newGrid = grid.map((row, r) =>
        row.map((cell, c) => {
          const cleanedCell = cleanedGrid[r][c];
          const letter = typeof cleanedCell === 'object'
            ? (cleanedCell.letter || '')
            : (cleanedCell === '#' ? '' : (cleanedCell === '.' ? '' : cleanedCell));
          const isBlack = typeof cleanedCell === 'object'
            ? cleanedCell.isBlack
            : cleanedCell === '#';
          return {
            ...cell,
            letter: isBlack ? '' : letter,
            isBlack,
            isError: false
          };
        })
      );
      setGrid(newGrid);
      pushToast({ kind: 'info', message });
    } catch (error) {
      console.error('Clean grid failed:', error);
      pushToast({ kind: 'error', message: 'Failed to clean grid: ' + error.message });
    }
  }, [grid, gridSize, pushToast]);

  const handleThemeWordApplied = useCallback((updatedGrid, placement) => {
    // Update grid with the applied theme word. Renumbering (if the placement
    // changed the structural layout) is handled by useNumbering.
    setGrid(updatedGrid);

    pushToast({ kind: 'info', message: `Applied "${placement.word}" to grid!` });
  }, [pushToast]);

  const handleGridImport = useCallback((importedData) => {
    const { grid: importedGrid, size, symmetryEnabled: importedSymmetry } = importedData;

    // Update grid size if different
    if (size !== gridSize) {
      setGridSize(size);
    }

    // Update grid state. Numbering + validation are now hook-driven: setting the
    // imported grid changes the structural signature, so useNumbering renumbers
    // (server-authoritative) and revalidates. The imported `numbering` field is
    // intentionally no longer applied — the server is the source of truth.
    setGrid(importedGrid);

    // Update symmetry setting if provided
    if (importedSymmetry !== undefined) {
      setSymmetryEnabled(importedSymmetry);
    }

    // A freshly imported grid is a new document (F10) and is born clean.
    setGridId((n) => n + 1);
    setSavedSig(contentSigOf(size, importedGrid));

    // Switch to edit tool to show the imported grid
    setCurrentTool('edit');
  }, [gridSize]);

  // Theme is an OVERLAY special-case, not a currentTool — it opens ThemeWordsPanel
  // rather than swapping the inspector. Every other rail id maps 1:1 to an inspector.
  const selectTool = (id) =>
    id === 'theme' ? setShowThemePanel(true) : setCurrentTool(id);

  // ToolRail GRID stats (module-level calculateGridStats) + word count (geometry).
  // Both are null-guarded so an uninitialized grid renders zeros, not a crash.
  const gridStats = grid ? calculateGridStats(grid) : null;
  let wordCount = 0;
  if (grid) {
    const slots = allSlots(grid);
    wordCount = slots.across.length + slots.down.length;
  }
  const railStats = gridStats
    ? {
        total: gridStats.totalCells,
        black: gridStats.blackSquares,
        blackPct: gridStats.blackSquarePercent,
        fillPct: gridStats.fillPercent,
        words: wordCount,
      }
    : { total: 0, black: 0, blackPct: 0, fillPct: 0, words: 0 };

  return (
    <div className="xw-app">
      {/* react-hot-toast surface — KEPT: Autofill/Theme/BlackSquare panels still call
          toast.* directly. App's own toasts use the bench ToastProvider (pushToast). */}
      <Toaster
        position="top-right"
        toastOptions={{
          success: {
            duration: 3000,
            style: { background: '#4caf50', color: '#fff' },
          },
          error: {
            duration: 4000,
            style: { background: '#f44336', color: '#fff' },
          },
        }}
      />

      <TopBar
        status={health}
        savedLabel={savedLabel}
        onVerify={handleVerifyWords}
        onClean={handleCleanGrid}
        onSave={saveDoc}
        onToggleTheme={() => setDark((v) => !v)}
        dark={dark}
      />

      <div className="xw-body">
        <ToolRail
          tool={showThemePanel ? 'theme' : currentTool}
          onSelectTool={selectTool}
          viewToggles={{ symmetry: symmetryEnabled, heatmap: heatmapOn }}
          onToggleView={(which) =>
            which === 'symmetry'
              ? setSymmetryEnabled((v) => !v)
              : setHeatmapOn((v) => !v)
          }
          stats={railStats}
          violations={violations}
          unverified={unverified}
        />

        <main className="xw-canvas">
          {grid ? (
            <CrosswordGrid
              grid={grid}
              focus={selectedCell ? { row: selectedCell.row, col: selectedCell.col } : null}
              selectedDir={selectedCell?.direction || 'across'}
              heatmap={null}
              onFocus={handleGridFocus}
              onMoveFocus={handleGridMoveFocus}
              onRotateDir={handleGridRotateDir}
              onSetLetter={setLetter}
              onToggleBlack={toggleBlackSquare}
              onToggleLock={toggleThemeLock}
            />
          ) : (
            <div className="grid-editor-loading">Initializing grid...</div>
          )}
        </main>

        <aside className="xw-inspector-shell">
          {currentTool === 'edit' && (
            <div className="xw-inspector-empty">
              <div className="xw-empty-mark">▦</div>
              <div className="xw-empty-title">Grid editor</div>
              <div className="xw-empty-sub">
                Select a cell to search, or pick a tool from the rail.
              </div>
            </div>
          )}

          {currentTool === 'search' && (
            <div className="xw-inspector">
              <PatternMatcher
                selectedCell={selectedCell}
                onSelectWord={handlePatternSelect}
              />
            </div>
          )}

          {currentTool === 'autofill' && (
            <div className="xw-inspector">
              <AutofillPanel
                onStartAutofill={handleAutofill}
                onCancelAutofill={handleCancelAutofill}
                onResetAutofill={handleResetAutofill}
                progress={autofillProgress}
                grid={grid}
                currentTaskId={currentTaskId}
              />
            </div>
          )}

          {currentTool === 'clues' && (
            <div className="xw-inspector-empty">
              <div className="xw-empty-mark">§</div>
              <div className="xw-empty-title">Clue list</div>
              <div className="xw-empty-sub">Arrives in a later task.</div>
            </div>
          )}

          {currentTool === 'lists' && (
            <div className="xw-inspector">
              <WordListPanel />
            </div>
          )}

          {currentTool === 'import' && (
            <div className="xw-inspector">
              <ImportPanel
                onImport={handleGridImport}
                currentGridSize={gridSize}
              />
            </div>
          )}

          {currentTool === 'export' && (
            <div className="xw-inspector">
              <ExportPanel
                grid={grid}
                gridSize={gridSize}
                numbering={numbering}
              />
            </div>
          )}
        </aside>
      </div>

      {/* Theme Words Panel — overlay (position:fixed), toggled independently of currentTool */}
      {showThemePanel && (
        <ThemeWordsPanel
          grid={grid}
          gridSize={gridSize}
          onApplyPlacement={handleThemeWordApplied}
          onClose={() => setShowThemePanel(false)}
        />
      )}
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