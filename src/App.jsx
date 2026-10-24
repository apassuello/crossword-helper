import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
// react-hot-toast's <Toaster> is intentionally KEPT: ThemeWordsPanel
// still calls toast.* directly. App's own toasts were
// migrated to the bench ToastProvider (pushToast); the default `toast` import is gone.
import { Toaster } from 'react-hot-toast';
import { api } from './api/client';
import { useHealth } from './hooks/useHealth';
import { usePersistentState } from './hooks/usePersistentState';
import { useSaveMachine } from './hooks/useSaveMachine';
import { useAutofillMachine, LIVE_STATES } from './hooks/useAutofillMachine';
import { useToasts } from './components/bench/Toast';
import { allSlots } from './hooks/useGridGeometry';
import { useNumbering, localNumber } from './hooks/useNumbering';
import { mintDocId } from './lib/docId';
import storage from './lib/storage';
import { toSavedGrid } from './api/gridCodec';
import {
  writeLetter,
  writeToggleBlack,
  writeToggleThemeLock,
  writePatternWord,
  writeAppliedTheme,
  writeImportedGrid,
  writeCleanedGrid,
  canToggleBlack,
} from './lib/gridEdits';
import { TopBar } from './components/bench/TopBar';
import SaveNamePrompt from './components/bench/SaveNamePrompt';
import { ToolRail } from './components/bench/ToolRail';
import CrosswordGrid from './components/bench/CrosswordGrid';
import GridHintLine from './components/bench/GridHintLine';
import GridPanel from './components/bench/GridPanel';
import PatternMatcher from './components/PatternMatcher';
import AutofillPanel from './components/bench/AutofillPanel';
import ExportPanel from './components/ExportPanel';
import ImportPanel from './components/ImportPanel';
import WordListPanel from './components/WordListPanel';
import ThemeWordsPanel from './components/ThemeWordsPanel';
import './styles/App.scss';

// Which lists decide whether an entry is "valid". Verify paints cells red from
// this, and Clean clears exactly those cells — so both calls MUST pass the same
// selection. They used to disagree (verify sent this list, clean sent nothing
// and got every installed list merged), which left red cells sitting on the
// grid after a clean reported success.
const VALIDATION_WORDLISTS = ['comprehensive'];

// Signature of user-authored grid content, for the save machine's dirty
// tracking. Deliberately array-shaped and limited to durable authored fields:
// it EXCLUDES `number` (derived by auto-renumbering, would spuriously mark
// dirty), the transient isError/isHighlighted flags, and `symmetryEnabled` —
// symmetry is a VIEW construction aid (a VIEW toggle), persisted on its
// own key via usePersistentState, so toggling it stays silent as it did before
// the save machine (it still rides along in the saved `doc`). Called in every
// place that establishes or compares dirtiness so the strings are byte-identical.
// `isAutofilled` is authored provenance and is part of the signature (absent counts
// as false); `isBlocked` is runtime-only and is not.
export function contentSigOf(size, grid) {
  return JSON.stringify({
    size,
    cells: grid
      ? grid.map((row) =>
          row.map((c) => [c.letter, c.isBlack, c.isThemeLocked, c.isAutofilled === true])
        )
      : null,
  });
}

function App() {
  const [gridSize, setGridSize] = useState(15);
  const [grid, setGrid] = useState(null);
  const [selectedCell, setSelectedCell] = useState(null);
  const [currentTool, setCurrentTool] = useState('edit'); // edit, search, autofill, lists, import, export
  const [showThemePanel, setShowThemePanel] = useState(false);
  // Black-square symmetry toggle, persisted (JSON boolean). usePersistentState
  // lazy-inits from storage, so a stored `false` survives reload (previously a
  // mount-race reset it to true on every load).
  const [symmetryEnabled, setSymmetryEnabled] = usePersistentState('crossword_symmetry_enabled', true);
  // Save machine (Task 7). `docId` is the doc's stable identity: minted at app
  // start and re-minted when a whole new grid is created (init/resize/import),
  // never on an edit, so the machine's F10 reset fires for "new grid" but not
  // for typing. It is a minted id, not a counter: a counter restarts on every
  // load and so cannot key a save.
  // `savedSig` is the content signature considered clean (set on fresh grids and
  // after a successful save); dirtiness is `contentSig !== savedSig`.
  const [docId, setDocId] = useState(mintDocId);
  const [savedSig, setSavedSig] = useState(null);
  // UI dark mode (Task 6), persisted as 'dark'/'light'. usePersistentState owns
  // the lazy-init + persistence (see its mount-race note); the effect below only
  // applies the theme to the document.
  const [dark, setDark] = usePersistentState('xw_theme', false, {
    parse: (v) => v === 'dark',
    serialize: (v) => (v ? 'dark' : 'light'),
  });

  const health = useHealth();
  const { pushToast } = useToasts();

  // Autofill lifecycle (Task 11, F3). Owns start/SSE-progress/done/failed/
  // cancelled/paused; App only threads grid/gridSize in and applies the
  // machine's grid updates back via onGridUpdate. Must precede `useNumbering`
  // below, which gates on `autofill.state`.
  // `invalidateNumberingRef` lets onStart reach useNumbering's `invalidate` although the
  // hook is called after this one (see above); it is filled in right after useNumbering.
  const invalidateNumberingRef = useRef(() => {});
  const autofill = useAutofillMachine({
    grid,
    gridSize,
    docId,
    onGridUpdate: (updater) => setGrid(updater),
    onStart: () => invalidateNumberingRef.current(),
    onToast: pushToast,
  });

  // D1 (novice-readiness spec 0.2.6 section 2.3): while a run is live no grid writer
  // runs except the machine's own onGridUpdate. `editingPaused` drives the disabled
  // controls at render time; `editingPausedRef` is the same value read by the write
  // handlers and by async handlers after their `await`, refreshed every render.
  const editingPaused = LIVE_STATES.has(autofill.state);
  const editingPausedRef = useRef(false);
  editingPausedRef.current = editingPaused;

  // Server-authoritative numbering + validation (Task 8, F2). Replaces the former
  // client-only word-start numbering pass and the validation stub: fires on
  // STRUCTURAL edits only (size / black-square layout — never letter edits),
  // renumbers server-wins after an optimistic local paint, and surfaces advisory
  // `violations`. `unverified` is true while an optimistic pass awaits reconcile.
  // Must precede `doc` below (which reads `numbering`).
  // `enabled` mutes numbering while an autofill run is submitting/running (Task
  // 11C): adaptive-mode autofill adds black squares mid-fill via onGridUpdate,
  // and each addition is a structural edit that would otherwise churn numbering/
  // violations against a grid that's deliberately incomplete mid-run. Flipping
  // back to enabled on completion re-fires against the grid as it stands then
  // (useNumbering's own [sig, enabled] dep array handles the catch-up).
  const { numbering, violations, unverified, invalidate } = useNumbering({
    grid,
    gridSize,
    setGrid,
    pushToast,
    enabled: !editingPaused,
  });
  invalidateNumberingRef.current = invalidate;

  // Save machine wiring (Task 7). `doc` is the full serializable grid document
  // (saved verbatim); `isDirty` is derived by comparing the current content
  // signature to the last-clean one.
  // novice-readiness spec 0.2.7 §3.4 (S2): while a run is live, the Save button and
  // autosave write the Start snapshot, so a reload mid-run restores the grid as it was
  // at Start. `savedGrid` is that grid (the live grid only when no snapshot exists,
  // which Phase 5 does not allow while live); `contentSig` is computed from the same
  // grid, so merges during the run do not flip `isDirty`. `liveSig` is the live grid's
  // own signature, kept for the live-grid consumers (Tasks 6.8 and 6.11).
  const savedGrid = editingPaused && autofill.startSnapshot ? autofill.startSnapshot : grid;
  const liveSig = useMemo(() => contentSigOf(gridSize, grid), [gridSize, grid]);
  const contentSig = useMemo(
    () => (savedGrid === grid ? liveSig : contentSigOf(gridSize, savedGrid)),
    [gridSize, savedGrid, grid, liveSig]
  );
  const isDirty = grid != null && contentSig !== savedSig;
  const doc = useMemo(
    () => ({ id: docId, size: gridSize, grid: toSavedGrid(savedGrid), numbering, symmetryEnabled }),
    [docId, gridSize, savedGrid, numbering, symmetryEnabled]
  );
  // A fork replaces the document id (S4). Must never throw: the machine calls it inside
  // its success handler, where a throw would make saveNamed reject.
  const onForked = useCallback((info) => setDocId(info.id), []);
  const {
    savedLabel,
    saveNamed,
    status: saveStatus,
  } = useSaveMachine({ doc, isDirty, onForked });

  // When a save lands, snapshot the content that was WRITTEN as clean: `contentSig` is
  // computed from the same grid `doc` carries (the Start snapshot during a run), so a
  // save during a run records the snapshot's signature, never the live grid's. Keyed on
  // saveStatus ONLY (adding contentSig here would re-mark clean on every edit
  // while 'saved' and dirtiness would never re-trigger) — sig read from a ref.
  const contentSigRef = useRef(contentSig);
  contentSigRef.current = contentSig;
  useEffect(() => {
    if (saveStatus === 'saved') setSavedSig(contentSigRef.current);
  }, [saveStatus]);

  // The Save button opens the name prompt (§3.4 G3); autosave never does. The prompt
  // mounts only once list() has resolved, so it never shows a prefill the user could
  // confirm by accident while the stored name is still unknown.
  const [savePrompt, setSavePrompt] = useState(null); // { initialName, entries, currentId } | null
  const promptRequestRef = useRef(0);
  const openSavePrompt = useCallback(() => {
    const request = ++promptRequestRef.current;
    const currentId = docId;
    storage.list().then((entries) => {
      if (request !== promptRequestRef.current) return;
      const own = entries.find((e) => e.id === currentId);
      setSavePrompt({
        initialName: own ? own.name : storage.defaultName(gridSize, new Date()),
        entries,
        currentId,
      });
    });
  }, [docId, gridSize]);
  const closeSavePrompt = useCallback(() => {
    promptRequestRef.current += 1; // drops a list() still pending
    setSavePrompt(null);
  }, []);
  const confirmSaveName = useCallback(
    async (name, opts) => {
      if (await saveNamed(name, opts)) closeSavePrompt();
    },
    [saveNamed, closeSavePrompt]
  );
  // A different document (New grid, Open saved, a fork) makes an open prompt stale.
  useEffect(() => closeSavePrompt(), [docId, closeSavePrompt]);

  // Set when a grid import changes the grid size, so the size-change effect
  // below does not wipe the freshly imported grid with an empty one. Bench's
  // rewrite of App.jsx dropped main's declaration while both use sites
  // auto-merged in; keeping the guard is a merge acceptance criterion
  // (App.test.jsx:50, :91).
  const skipNextInitRef = useRef(false);

  // Initialize empty grid
  useEffect(() => {
    if (skipNextInitRef.current) {
      skipNextInitRef.current = false;
      return;
    }
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
        isThemeLocked: false,  // Phase 3: Theme entry locking
        isAutofilled: false,
        isBlocked: false
      }))
    );
    // novice-readiness spec 0.2.7 §3.2 (#55): the blank grid is born numbered. useNumbering
    // fires only on a structural-signature change, and a New grid over a grid with the same
    // size and black layout does not change it, so the numbers are applied here rather than
    // left to the hook. The hook's server reconcile still runs on any real structural change.
    const numbered = localNumber(newGrid).grid;
    setGrid(numbered);
    // Numbering is otherwise hook-driven (useNumbering): setting the grid changes the
    // structural signature, which fires the optimistic renumber + server reconcile.
    // A fresh grid is a new document (F10) and is born clean.
    setDocId(mintDocId());
    setSavedSig(contentSigOf(size, numbered));
  };

  // novice-readiness spec 0.2.7 §3.2 (#55): New grid. Built through `initializeGrid` (which
  // mints the new document id and numbers the grid), so there is no second mint. Gated at
  // write time (D1) as well as at the button, because the autofill machine's doc-id guard
  // relies on New grid never running while a run is live.
  const createNewGrid = useCallback((size) => {
    if (editingPausedRef.current) return;
    if (size !== gridSize) {
      // The [gridSize] effect would otherwise initialise a second time.
      skipNextInitRef.current = true;
      setGridSize(size);
    }
    initializeGrid(size);
    autofill.discardRun();
    setSelectedCell(null);
    setSymmetryEnabled(true);
  }, [gridSize, autofill.discardRun]);

  const toggleBlackSquare = useCallback((row, col) => {
    if (editingPausedRef.current) return;
    if (!grid) return;
    // novice-readiness spec 0.2.7 §3.3 (G7): refuse before any write, so
    // neither the cell nor its partner changes.
    if (!canToggleBlack(grid, row, col, symmetryEnabled)) return;

    setGrid(writeToggleBlack(grid, row, col, symmetryEnabled));
    // Structural edit: useNumbering renumbers (server-wins) + revalidates off the
    // black-square layout change. No manual renumber/validate here.
  }, [grid, symmetryEnabled]);

  const toggleThemeLock = useCallback((row, col) => {
    if (editingPausedRef.current) return;
    if (!grid || grid[row][col].isBlack) return;

    setGrid(writeToggleThemeLock(grid, row, col));
  }, [grid]);

  const setLetter = useCallback((row, col, letter) => {
    if (editingPausedRef.current) return;
    if (!grid || grid[row][col].isBlack) return;

    setGrid(writeLetter(grid, row, col, letter));
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
    if (editingPausedRef.current) return;
    if (!selectedCell || !grid) return;

    setGrid(writePatternWord(grid, selectedCell, word));
    // Letter fill — no renumber/validate (structural signature unchanged).
  }, [selectedCell, grid]);

  const handleVerifyWords = useCallback(async () => {
    if (editingPausedRef.current) return;
    if (!grid) return;

    try {
      const { invalid_words, invalid_count, total_checked, wordlist_size } = await api.verifyWords({
        grid: grid.map(row => row.map(cell => ({
          letter: cell.letter || '',
          isBlack: cell.isBlack || false
        }))),
        size: gridSize,
        wordlists: VALIDATION_WORDLISTS
      });

      // D1: a response that lands after Start writes nothing (no grid, no toast).
      if (editingPausedRef.current) return;

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
      pushToast({ kind: 'error', message: 'Failed to verify words: ' + (error.message || error.code) });
    }
  }, [grid, gridSize, pushToast]);

  const handleCleanGrid = useCallback(async () => {
    if (editingPausedRef.current) return;
    if (!grid) return;

    try {
      const { grid: cleanedGrid, removed_count, valid_count, cleared_cells, message } = await api.cleanGrid({
        grid: grid.map(row => row.map(cell => ({
          letter: cell.letter || '',
          isBlack: cell.isBlack || false
        }))),
        size: gridSize,
        wordlists: VALIDATION_WORDLISTS
      });

      // D1: a response that lands after Start writes nothing (no grid, no toast).
      if (editingPausedRef.current) return;

      if (removed_count === 0) {
        pushToast({ kind: 'info', message: 'Grid is clean — all words are valid!' });
        return;
      }

      // Update grid with cleaned result
      setGrid(writeCleanedGrid(grid, cleanedGrid));
      pushToast({ kind: 'info', message });
    } catch (error) {
      console.error('Clean grid failed:', error);
      pushToast({ kind: 'error', message: 'Failed to clean grid: ' + (error.message || error.code) });
    }
  }, [grid, gridSize, pushToast]);

  const handleThemeWordApplied = useCallback((updatedGrid, placement) => {
    if (editingPausedRef.current) return;
    // Update grid with the applied theme word. Renumbering (if the placement
    // changed the structural layout) is handled by useNumbering.
    setGrid((prev) => writeAppliedTheme(prev, updatedGrid));

    pushToast({ kind: 'info', message: `Applied "${placement.word}" to grid!` });
  }, [pushToast]);

  const handleGridImport = useCallback((importedData) => {
    if (editingPausedRef.current) return;
    const { grid: importedGrid, size, symmetryEnabled: importedSymmetry } = importedData;

    // Update grid size if different (skip the re-init effect so the
    // imported grid isn't overwritten by a fresh empty grid)
    if (size !== gridSize) {
      skipNextInitRef.current = true;
      setGridSize(size);
    }

    // Update grid state. Numbering + validation are now hook-driven: setting the
    // imported grid changes the structural signature, so useNumbering renumbers
    // (server-authoritative) and revalidates. The imported `numbering` field is
    // intentionally no longer applied — the server is the source of truth.
    const normalisedGrid = writeImportedGrid(importedGrid);
    setGrid(normalisedGrid);

    // Update symmetry setting if provided
    if (importedSymmetry !== undefined) {
      setSymmetryEnabled(importedSymmetry);
    }

    // A freshly imported grid is a new document (F10) and is born clean.
    setDocId(mintDocId());
    setSavedSig(contentSigOf(size, normalisedGrid));

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
        editingPaused={editingPaused}
        onSave={openSavePrompt}
        savePrompt={
          savePrompt && (
            <SaveNamePrompt
              initialName={savePrompt.initialName}
              entries={savePrompt.entries}
              currentId={savePrompt.currentId}
              onConfirm={confirmSaveName}
              onCancel={closeSavePrompt}
            />
          )
        }
        onToggleTheme={() => setDark((v) => !v)}
        dark={dark}
      />

      <div className="xw-body">
        <ToolRail
          tool={showThemePanel ? 'theme' : currentTool}
          onSelectTool={selectTool}
          viewToggles={{ symmetry: symmetryEnabled }}
          onToggleView={() => setSymmetryEnabled((v) => !v)}
          stats={railStats}
          violations={violations}
          unverified={unverified}
        />

        <main className="xw-canvas">
          {grid ? (
            <>
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
              editingPaused={editingPaused}
            />
            <GridHintLine />
            </>
          ) : (
            <div className="grid-editor-loading">Initializing grid...</div>
          )}
        </main>

        <aside className="xw-inspector-shell">
          {currentTool === 'edit' && (
            <div className="xw-inspector">
              <GridPanel
                grid={grid}
                gridSize={gridSize}
                selectedCell={selectedCell}
                symmetryEnabled={symmetryEnabled}
                editingPaused={editingPaused}
                onToggleBlack={toggleBlackSquare}
                onNewGrid={createNewGrid}
              />
            </div>
          )}

          {currentTool === 'search' && (
            <div className="xw-inspector">
              <PatternMatcher
                selectedCell={selectedCell}
                onSelectWord={handlePatternSelect}
                editingPaused={editingPaused}
              />
            </div>
          )}

          {currentTool === 'autofill' && (
            <div className="xw-inspector">
              <AutofillPanel machine={autofill} grid={grid} docId={docId} />
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
                editingPaused={editingPaused}
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
          editingPaused={editingPaused}
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