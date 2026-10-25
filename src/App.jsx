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
import { toSavedGrid, normalizeSavedGrid } from './api/gridCodec';
import {
  writeLetter,
  writeToggleBlack,
  writeToggleThemeLock,
  writePatternWord,
  writeAppliedTheme,
  writeImportedGrid,
  writeCleanedGrid,
  applyVerifyErrors,
  planClean,
  clearAllErrors,
  canToggleBlack,
  gridHasContent,
} from './lib/gridEdits';
import { TopBar } from './components/bench/TopBar';
import SaveNamePrompt from './components/bench/SaveNamePrompt';
import { ToolRail } from './components/bench/ToolRail';
import CrosswordGrid from './components/bench/CrosswordGrid';
import RestoreBanner from './components/bench/RestoreBanner';
import InlineConfirm from './components/bench/InlineConfirm';
import GridHintLine from './components/bench/GridHintLine';
import GridPanel from './components/bench/GridPanel';
import { IMPORT_MIN_SIZE, IMPORT_MAX_SIZE } from './lib/gridSizes';
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

/**
 * A stored entry becomes the live document only if `size` is an integer the importer accepts
 * (`IMPORT_MIN_SIZE`..`IMPORT_MAX_SIZE`: a saved import may be any of them), `grid` is a
 * `size`×`size` array of rows and every cell is a non-null object. Anything else would crash
 * `allSlots` (ragged rows) or `normalizeCell` (a null cell) after the adoption had started.
 * The spec (0.2.8 §3.4, G#77 App.jsx:264) requires the entry to be validated before adoption
 * but names no size rule; the size rule is the plan's, Task 6.20 (amended by Phase 6R I2).
 */
export function isAdoptableEntry(entry) {
  if (!entry || !Number.isInteger(entry.size)) return false;
  if (entry.size < IMPORT_MIN_SIZE || entry.size > IMPORT_MAX_SIZE) return false;
  const { grid, size } = entry;
  return (
    Array.isArray(grid) &&
    grid.length === size &&
    grid.every(
      (row) =>
        Array.isArray(row) &&
        row.length === size &&
        row.every((cell) => cell !== null && typeof cell === 'object' && !Array.isArray(cell))
    )
  );
}

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
  // novice-readiness spec 0.2.7 §2.3 (S1): Verify and Clean responses land after an await, so
  // they read the grid, document id and live signature as they are NOW, through refs
  // refreshed every render (like `editingPausedRef`), never through the handler's closure.
  const gridRef = useRef(grid);
  gridRef.current = grid;
  const docIdRef = useRef(docId);
  docIdRef.current = docId;
  const liveSigRef = useRef(liveSig);
  liveSigRef.current = liveSig;
  // novice-readiness spec 0.2.7 §3.5 (G5): Clean's pending confirm, { blanks, cleaned, message, sig }.
  const [pendingClean, setPendingClean] = useState(null);
  // Dismissed, applying nothing, when the live signature leaves the one recorded at open (an
  // isError-only change is not a signature change, PD-6-G11) or a run starts (editingPaused).
  useEffect(() => {
    if (pendingClean && (editingPaused || liveSig !== pendingClean.sig)) setPendingClean(null);
  }, [pendingClean, liveSig, editingPaused]);
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
  // A save fork is the same document under a new id: the autofill machine follows it before
  // App's docId changes (novice-readiness spec 0.2.8 §2.3 (F2)).
  const onForked = useCallback(
    (info) => {
      autofill.adoptForkedDocId(docIdRef.current, info.id);
      setDocId(info.id);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [autofill.adoptForkedDocId]
  );
  // novice-readiness spec 0.2.7 §3.4 (S2): the single writer of savedSig after a save. The
  // machine hands back the exact document it wrote (the Start snapshot during a run), so
  // the clean signature is that document's, whatever the live grid did between the write
  // and the `saved` status. If the grid moved on, isDirty stays true and the machine
  // returns to `dirty` (see useSaveMachine).
  const onSaved = useCallback((written) => setSavedSig(contentSigOf(written.size, written.grid)), []);
  const { savedLabel, saveNamed, adoptSavedAt, forget } = useSaveMachine({ doc, isDirty, onForked, onSaved });

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

  // novice-readiness spec 0.2.7 §3.4 (S3, M1, PD-6-G4): restore the newest save on load. The
  // [gridSize] effect above has already initialised a blank grid by the time `load()`
  // resolves (a microtask later), so the restore simply lands after it. Across sizes the
  // skip flag is set before the size change, so that effect does not blank the restored
  // cells; at the same size it is NOT set (a stray `true` would swallow the next legitimate
  // size change). No entry: the blank grid and the docId minted at start stay.
  const gridSizeRef = useRef(gridSize);
  gridSizeRef.current = gridSize;
  const [restoredBanner, setRestoredBanner] = useState(null); // { name, savedAt, sig } | null
  // novice-readiness spec 0.2.7 §3.4 (S3, M1, PD-6-G4): the one place a saved entry becomes
  // the live document, shared by restore-on-load and Open saved. It reads the current size
  // through `gridSizeRef` and applies the S3 skip-flag rule exactly once. An entry that
  // fails `isAdoptableEntry` is adopted by nothing: one console.error, no state change; Open
  // saved reports it (`openSavedEntry`), restore stays silent on a blank grid.
  // `banner` true shows the restore banner for the entry; false dismisses it.
  const adoptSavedEntry = useCallback(
    (entry, { banner }) => {
      if (!isAdoptableEntry(entry)) {
        console.error('Ignoring a saved grid whose cells are malformed:', entry?.id);
        return false;
      }
      const restored = normalizeSavedGrid(entry.grid);
      if (entry.size !== gridSizeRef.current) {
        skipNextInitRef.current = true;
        setGridSize(entry.size);
      }
      setGrid(restored);
      setDocId(entry.id);
      if (typeof entry.symmetryEnabled === 'boolean') setSymmetryEnabled(entry.symmetryEnabled);
      const sig = contentSigOf(entry.size, restored);
      setSavedSig(sig);
      adoptSavedAt(entry.savedAt);
      setSelectedCell(null);
      setRestoredBanner(banner ? { name: entry.name, savedAt: entry.savedAt, sig } : null);
      return true;
    },
    [adoptSavedAt]
  );
  useEffect(() => {
    let cancelled = false;
    storage.load().then((entry) => {
      if (cancelled || !entry) return;
      adoptSavedEntry(entry, { banner: true });
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // The banner closes on any grid edit: the live signature leaves the one recorded at
  // restore. `contentSigOf` excludes `number`, so a numbering reconcile does not close it.
  useEffect(() => {
    if (restoredBanner && liveSig !== restoredBanner.sig) setRestoredBanner(null);
  }, [liveSig, restoredBanner]);

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

  // novice-readiness spec 0.2.7 §3.4 (S3, M1): Open saved. Gated at write time (D1) as well as
  // at the buttons, because the autofill machine's doc-id guard assumes `docId` cannot change
  // mid-run. The shared adoption does the S3 skip-flag rule, the docId and savedAt adoption;
  // only on success does the run get discarded (no retained snapshot or Keep offer) and the
  // restore banner close (adoption with `banner: false` dismisses it).
  const openSavedEntry = useCallback(
    (entry) => {
      if (editingPausedRef.current) return;
      if (adoptSavedEntry(entry, { banner: false })) autofill.discardRun();
      else pushToast({ kind: 'error', message: 'Could not open this saved grid.' });
    },
    [adoptSavedEntry, autofill.discardRun, pushToast]
  );
  // novice-readiness spec 0.2.8 §3.4 (Q1): Delete removed the entry with this id; when it is
  // the open document's, the document is unsaved now (no autosave is armed until an edit).
  const onEntryDeleted = useCallback(
    (id) => {
      if (id === docIdRef.current) forget();
    },
    [forget]
  );

  const toggleBlackSquare = useCallback((row, col) => {
    if (editingPausedRef.current) return;
    if (!grid) return;
    // novice-readiness spec 0.2.7 §3.3 (G7): refuse before any write, so
    // neither the cell nor its partner changes.
    if (!canToggleBlack(grid, row, col, symmetryEnabled)) return;

    setGrid((prev) => writeToggleBlack(prev, row, col, symmetryEnabled));
    // Structural edit: useNumbering renumbers (server-wins) + revalidates off the
    // black-square layout change. No manual renumber/validate here.
  }, [grid, symmetryEnabled]);

  const toggleThemeLock = useCallback((row, col) => {
    if (editingPausedRef.current) return;
    if (!grid || grid[row][col].isBlack) return;

    setGrid((prev) => writeToggleThemeLock(prev, row, col));
  }, [grid]);

  const setLetter = useCallback((row, col, letter) => {
    if (editingPausedRef.current) return;
    if (!grid || grid[row][col].isBlack) return;

    setGrid((prev) => writeLetter(prev, row, col, letter));
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

    setGrid((prev) => writePatternWord(prev, selectedCell, word));
    // Letter fill — no renumber/validate (structural signature unchanged).
  }, [selectedCell, grid]);

  const handleVerifyWords = useCallback(async () => {
    if (editingPausedRef.current) return;
    if (!grid) return;
    const requestDocId = docIdRef.current;

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
      // novice-readiness spec 0.2.7 §2.3 (PD-6-G12): a response for another document writes nothing.
      if (docIdRef.current !== requestDocId) return;

      // Build set of cells that belong to invalid words
      const errorCells = new Set();
      invalid_words.forEach(({ cells }) => {
        cells.forEach(([r, c]) => errorCells.add(`${r},${c}`));
      });

      // novice-readiness spec 0.2.7 §2.3 (S1): only isError changes, on the grid as it is now.
      setGrid(prev => applyVerifyErrors(prev, errorCells));

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
    const requestDocId = docIdRef.current;
    const sent = grid.map(row => row.map(cell => ({
      letter: cell.letter || '',
      isBlack: cell.isBlack || false
    })));

    try {
      const { grid: cleanedGrid, removed_count, message } = await api.cleanGrid({
        grid: sent,
        size: gridSize,
        wordlists: VALIDATION_WORDLISTS
      });

      // D1: a response that lands after Start writes nothing (no grid, no toast).
      if (editingPausedRef.current) return;
      // novice-readiness spec 0.2.7 §2.3 (PD-6-G12): a response for another document writes nothing.
      if (docIdRef.current !== requestDocId) return;

      // The server echoes the cell shape it was sent ({ letter, isBlack }); a string cell
      // ('#', '.', a letter) is normalised once here so nothing below branches on shape.
      const cleaned = cleanedGrid.map(row => row.map(x =>
        typeof x === 'object'
          ? x
          : { letter: x === '#' || x === '.' ? '' : x, isBlack: x === '#' }
      ));
      const sentLetters = sent.map(row => row.map(x => (x.isBlack ? '' : x.letter)));
      const cleanedLetters = cleaned.map(row => row.map(x => (x.isBlack ? '' : x.letter || '')));
      // S1: planned against the grid as it is NOW, not the one the request was built from.
      const { blanks } = planClean(gridRef.current, sentLetters, cleanedLetters);

      if (blanks.length > 0) {
        // novice-readiness spec 0.2.7 §3.5 (G5 step 2, PD-6-G10): ask first; nothing is written yet.
        setPendingClean({ blanks, cleaned, message, sig: liveSigRef.current });
        return;
      }

      // G5 step 3 / #63: nothing to blank, so the red flags clear and the toast says why.
      setGrid(prev => clearAllErrors(prev));
      pushToast({
        kind: 'info',
        message: removed_count === 0
          ? 'Grid is clean — all words are valid!'
          : 'Nothing removed: theme-locked letters are kept.',
      });
    } catch (error) {
      console.error('Clean grid failed:', error);
      pushToast({ kind: 'error', message: 'Failed to clean grid: ' + (error.message || error.code) });
    }
  }, [grid, gridSize, pushToast]);

  const acceptClean = useCallback(() => {
    if (editingPausedRef.current || !pendingClean) return;
    const { blanks, cleaned, message } = pendingClean;
    setPendingClean(null);
    setGrid(prev => writeCleanedGrid(prev, cleaned, blanks));
    pushToast({ kind: 'info', message });
  }, [pendingClean, pushToast]);

  // novice-readiness spec 0.2.8 §3.8 (F1, F4, PD-6-G12): a reply for a replaced document is
  // dropped, as Verify and Clean do; the rest is merged against the grid it was sent from.
  // Returns true when it wrote the grid, false when a gate dropped the reply.
  const handleThemeWordApplied = useCallback((updatedGrid, placement, { sentGrid, docId: requestDocId }) => {
    if (editingPausedRef.current) return false;
    if (requestDocId !== docIdRef.current) return false;
    // Update grid with the applied theme word. Renumbering (if the placement
    // changed the structural layout) is handled by useNumbering.
    setGrid((prev) => writeAppliedTheme(prev, updatedGrid, sentGrid));

    pushToast({ kind: 'info', message: `Applied "${placement.word}" to grid!` });
    return true;
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

    // novice-readiness spec 0.2.8 §3.2 Import (F3): the imported grid is born numbered.
    // ImportPanel builds every cell with `number: null`, and useNumbering fires only on a
    // structural-signature change (size + black layout), which an import over a grid with the
    // same size and layout does not cause. So the numbers are applied here, as New grid does;
    // the hook's server reconcile still runs on any real structural change. The imported
    // `numbering` field is intentionally not applied — numbers are computed from the grid.
    const normalisedGrid = localNumber(writeImportedGrid(importedGrid)).grid;
    setGrid(normalisedGrid);

    // Update symmetry setting if provided
    if (importedSymmetry !== undefined) {
      setSymmetryEnabled(importedSymmetry);
    }

    // A freshly imported grid is a new document (F10) and is born clean.
    setDocId(mintDocId());
    setSavedSig(contentSigOf(size, normalisedGrid));

    // novice-readiness spec 0.2.8 §3.2 Import (M3): clear a finished run's result and
    // "Keep partial fill" offer, as New grid and Open saved do.
    autofill.discardRun();
    setSelectedCell(null);

    // Switch to edit tool to show the imported grid
    setCurrentTool('edit');
  }, [gridSize, autofill.discardRun]);

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
          {restoredBanner && (
            <RestoreBanner
              name={restoredBanner.name}
              savedAt={restoredBanner.savedAt}
              onStartBlank={() => {
                // PD-6-G9: opens the Grid tool, where New grid is; it creates nothing itself.
                setCurrentTool('edit');
                setRestoredBanner(null);
              }}
              onDismiss={() => setRestoredBanner(null)}
            />
          )}
          {pendingClean && (
            <InlineConfirm
              message={`Clean will remove ${pendingClean.blanks.length} letter${pendingClean.blanks.length === 1 ? '' : 's'}`}
              confirmLabel="Clean"
              cancelLabel="Cancel"
              onConfirm={acceptClean}
              onCancel={() => setPendingClean(null)}
            />
          )}
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
                onOpenSaved={openSavedEntry}
                onDeleted={onEntryDeleted}
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
                gridHasContent={gridHasContent(grid)}
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
          docId={docId}
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