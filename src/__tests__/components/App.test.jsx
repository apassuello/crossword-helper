/**
 * Tests for App-level grid import behavior.
 *
 * Regression coverage: importing a grid of a DIFFERENT size used to be wiped
 * because the `useEffect(() => initializeGrid(gridSize), [gridSize])` re-fired
 * on the size change and replaced the imported grid with an empty one.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../App';
import { ToastProvider } from '../../components/bench/Toast';
import { localNumber } from '../../hooks/useNumbering';
import storage from '../../lib/storage';
import { api } from '../../api/client';
import { contentSigOf } from '../../App';

// Probes for the New grid rows (novice-readiness spec 0.2.7 §3.2). Each wraps the
// real module and only records or overrides what a test needs: distinguishable
// document ids, the props App hands the Grid panel, and the autofill machine's
// state/discardRun (so a live run can be simulated without a backend).
const probe = vi.hoisted(() => ({
  mintCalls: 0,
  panelProps: null,
  autofillArgs: null,
  autofillOverride: null,
  saveArgs: null,
}));

vi.mock('../../lib/docId', () => ({
  mintDocId: () => `doc-${++probe.mintCalls}`,
}));

vi.mock('../../components/bench/GridPanel', async (importOriginal) => {
  const actual = await importOriginal();
  const Real = actual.default;
  return {
    ...actual,
    default: (props) => {
      probe.panelProps = props;
      return <Real {...props} />;
    },
  };
});

// Records the `isDirty` App hands the save machine, so a test can assert the dirty flag
// itself rather than only the label the machine derives from it.
vi.mock('../../hooks/useSaveMachine', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useSaveMachine: (args) => {
      probe.saveArgs = args;
      return actual.useSaveMachine(args);
    },
  };
});

vi.mock('../../hooks/useAutofillMachine', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useAutofillMachine: (args) => {
      probe.autofillArgs = args;
      const real = actual.useAutofillMachine(args);
      return probe.autofillOverride ? { ...real, ...probe.autofillOverride } : real;
    },
  };
});

// Bench's App consumes the ToastProvider context (useToasts), so it must be
// rendered inside the provider exactly as main.jsx mounts it. Main's version of
// App did not use toasts and rendered bare; the assertions below are unchanged.
const renderApp = () => render(<App />, { wrapper: ToastProvider });

// Bench's CrosswordGrid renders an SVG, not a div grid: one transparent hit rect
// per cell, black squares as a rect filled with var(--ink) (grid lines use
// `stroke`, not `fill`, so they do not match), and letters as text.xw-cell-letter.
// Main's assertions are unchanged — only the selectors are re-expressed.
const cells = (container) => container.querySelectorAll('rect[fill="transparent"]');
const blackCells = (container) => container.querySelectorAll('rect[fill="var(--ink)"]');
const letters = (container) =>
  Array.from(container.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);

// Mock react-hot-toast to avoid timers/portals in jsdom
vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  }),
  Toaster: () => null,
}));

const importGridViaPaste = async (user, container, gridJson) => {
  // Go to Import tab
  await user.click(screen.getByRole('button', { name: /^import$/i }));

  // Use the Paste JSON method
  await user.click(screen.getByRole('button', { name: /paste json/i }));

  const textarea = screen.getByLabelText(/paste json data/i);
  fireEvent.change(textarea, { target: { value: JSON.stringify(gridJson) } });

  await user.click(screen.getByRole('button', { name: /validate json/i }));

  await waitFor(() => {
    expect(screen.getByRole('button', { name: /import grid/i })).toBeInTheDocument();
  });

  await user.click(screen.getByRole('button', { name: /import grid/i }));
};

describe('App grid import', () => {
  beforeEach(() => {
    // The global localStorage mock returns undefined by default; the real API
    // returns null for missing keys.
    global.localStorage.getItem.mockReturnValue(null);
  });

  it('keeps letters and black squares when importing a smaller (5x5) grid into a 15x15 session (regression)', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();

    // Default 15x15 grid renders 225 cells
    await waitFor(() => {
      expect(cells(container)).toHaveLength(225);
    });

    const gridJson = {
      size: 5,
      grid: [
        ['C', 'A', 'T', '#', '.'],
        ['.', '.', '.', '.', '.'],
        ['#', '.', '.', '.', '#'],
        ['.', '.', '.', '.', '.'],
        ['.', '#', '.', '.', 'Z'],
      ],
    };

    await importGridViaPaste(user, container, gridJson);

    // ImportPanel defers the actual import by 300ms, then App switches to edit view
    await waitFor(() => {
      expect(cells(container)).toHaveLength(25);
    }, { timeout: 3000 });

    // Letters survived (previously wiped by grid re-initialization on size change)
    expect(letters(container)).toHaveLength(4);
    expect(letters(container)).toEqual(expect.arrayContaining(['C', 'A', 'T', 'Z']));

    // Black squares survived too (rendered with the dark fill)
    expect(blackCells(container)).toHaveLength(4);
  });

  it('same-size (15x15) import still works and keeps its letters', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();

    await waitFor(() => {
      expect(cells(container)).toHaveLength(225);
    });

    // Build a 15x15 grid with a few letters and a black square
    const grid = Array.from({ length: 15 }, () => Array(15).fill('.'));
    grid[0][0] = 'H';
    grid[0][1] = 'I';
    grid[7][7] = '#';

    await importGridViaPaste(user, container, { size: 15, grid });

    await waitFor(() => {
      expect(letters(container)).toEqual(expect.arrayContaining(['H', 'I']));
    }, { timeout: 3000 });

    expect(cells(container)).toHaveLength(225);
    expect(blackCells(container)).toHaveLength(1);
  });
});

// novice-readiness spec 0.2.7 §3.1 (#53, #50): hidden rail controls.
describe('App tool rail', () => {
  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
  });

  it('renders no Clues tool and no Heatmap toggle', async () => {
    const { container } = renderApp();
    await waitFor(() => {
      expect(cells(container)).toHaveLength(225);
    });
    expect(screen.getByText('Symmetry')).toBeInTheDocument();
    expect(screen.queryByText('Clues')).toBeNull();
    expect(screen.queryByText('Heatmap')).toBeNull();
  });
});

// novice-readiness spec 0.2.7 §3.3 (G7): black-square guard through the UI, and
// the always-visible key hint line.
describe('App black squares and hint line (§3.3)', () => {
  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
  });

  const SIZE = 15;
  const idx = (r, c) => r * SIZE + c;
  const focusEl = (container) => container.querySelector('.xw-grid-focus');

  it('refuses a theme-locked cell and its mirror partner, but toggles an unlocked one', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(SIZE * SIZE));
    const baseline = blackCells(container).length;
    const A = [2, 3];
    const partner = [SIZE - 1 - A[0], SIZE - 1 - A[1]];

    // Lock A with Ctrl+L.
    await user.click(cells(container)[idx(...A)]);
    fireEvent.keyDown(focusEl(container), { key: 'l', ctrlKey: true });

    // Space on the locked cell: refused.
    fireEvent.keyDown(focusEl(container), { key: ' ' });
    expect(blackCells(container)).toHaveLength(baseline);

    // Space on the locked cell's mirror partner: refused, no partial write.
    await user.click(cells(container)[idx(...partner)]);
    fireEvent.keyDown(focusEl(container), { key: ' ' });
    expect(blackCells(container)).toHaveLength(baseline);

    // Control: an unrelated cell still toggles (cell and its partner: +2).
    await user.click(cells(container)[idx(5, 6)]);
    fireEvent.keyDown(focusEl(container), { key: ' ' });
    expect(blackCells(container)).toHaveLength(baseline + 2);
  });

  // novice-readiness spec 0.2.7 §3.3: the Black square button acts like Space,
  // symmetry included. Checks WHICH cells are black, not only how many.
  const blackSet = (container) => {
    const all = Array.from(container.querySelectorAll('rect[fill="var(--ink)"]'));
    return all.map((el) => [Number(el.getAttribute('x')), Number(el.getAttribute('y'))]);
  };

  it('Black square button blackens the cell and its mirror; with symmetry off only the cell', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(SIZE * SIZE));
    const before = blackSet(container);
    // Black fills are inset by half a stroke width; floor aligns them with the hit rects.
    const key = ([x, y]) => `${Math.floor(x)},${Math.floor(y)}`;
    const beforeKeys = new Set(before.map(key));
    const posOf = (i) => {
      const r = cells(container)[i];
      return key([Number(r.getAttribute('x')), Number(r.getAttribute('y'))]);
    };
    const A = idx(2, 3);
    const M = idx(SIZE - 1 - 2, SIZE - 1 - 3);
    const newlyBlack = () =>
      blackSet(container).map(key).filter((k) => !beforeKeys.has(k)).sort();

    // Symmetry on (default): cell and mirror.
    await user.click(cells(container)[A]);
    await user.click(screen.getByRole('button', { name: 'Black square' }));
    expect(newlyBlack()).toEqual([posOf(A), posOf(M)].sort());

    // Undo, then turn symmetry off and toggle another cell: only that cell.
    await user.click(screen.getByRole('button', { name: 'Black square' }));
    expect(newlyBlack()).toEqual([]);
    await user.click(screen.getByText('Symmetry'));
    const B = idx(5, 6);
    await user.click(cells(container)[B]);
    await user.click(screen.getByRole('button', { name: 'Black square' }));
    expect(newlyBlack()).toEqual([posOf(B)]);
  });

  it('shows the key hint under the grid in more than one tool', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(SIZE * SIZE));
    const hint = () => container.querySelector('p.xw-grid-hint');
    expect(hint()).not.toBeNull();
    expect(hint().textContent).toMatch(/^Type letters · Arrows move/);
    await user.click(screen.getByRole('button', { name: /^import$/i }));
    expect(hint()).not.toBeNull();
    expect(container.querySelectorAll('p.xw-grid-hint')).toHaveLength(1);
  });
});

// novice-readiness spec 0.2.7 §3.2 (#55): New grid, end to end through App.
describe('App New grid (§3.2)', () => {
  const SIZE = 15;
  const idx = (r, c) => r * SIZE + c;
  const focusEl = (container) => container.querySelector('.xw-grid-focus');
  const sizeBtn = (label) => screen.getByRole('button', { name: label });
  const docIdNow = () => probe.autofillArgs.docId;
  const flat = () => probe.panelProps.grid.flat();

  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
    probe.autofillOverride = null;
    probe.panelProps = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const typeLetter = async (user, container, r, c, ch) => {
    await user.click(cells(container)[idx(r, c)]);
    fireEvent.keyDown(focusEl(container), { key: ch });
  };

  it('15x15 with letters: 21x21 + Replace gives a blank 21x21 with a new docId and clean flags', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 3, 3, 'A');
    expect(letters(container)).toEqual(['A']);
    const idBefore = docIdNow();
    const mintsBefore = probe.mintCalls;

    await user.click(sizeBtn('21\u00d721'));
    await user.click(screen.getByRole('button', { name: 'Replace' }));

    await waitFor(() => expect(cells(container)).toHaveLength(441));
    expect(letters(container)).toEqual([]);
    expect(docIdNow()).not.toBe(idBefore);
    expect(flat()).toHaveLength(441);
    for (const cell of flat()) {
      expect(cell.isError).toBe(false);
      expect(cell.isBlocked).toBe(false);
      expect(cell.isAutofilled).toBe(false);
      expect(cell.isThemeLocked).toBe(false);
    }
    // skipNextInitRef: the size change must not run initializeGrid a second time.
    expect(probe.mintCalls - mintsBefore).toBe(1);
  });

  it('Cancel leaves the grid and docId unchanged', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 3, 3, 'A');
    const idBefore = docIdNow();
    const mintsBefore = probe.mintCalls;

    await user.click(sizeBtn('15\u00d715'));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(letters(container)).toEqual(['A']);
    expect(cells(container)).toHaveLength(225);
    expect(docIdNow()).toBe(idBefore);
    expect(probe.mintCalls).toBe(mintsBefore);
  });

  it('a blank grid: choosing 11x11 asks nothing and gives an 11x11 grid', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    const mintsBefore = probe.mintCalls;

    await user.click(sizeBtn('11\u00d711'));

    expect(screen.queryByRole('group')).toBeNull();
    await waitFor(() => expect(cells(container)).toHaveLength(121));
    expect(probe.mintCalls - mintsBefore).toBe(1);
  });

  it('same size, letters only: the blank grid is numbered as localNumber numbers it', async () => {
    // The mount's server reconcile (150 ms debounce, then /api/number) is still in flight
    // when a fast test reaches New grid. A New grid over the same size and black layout does
    // not change the structural signature, so that reconcile is not superseded and, landing
    // after New grid, rewrites every number from the response (the MSW handler answers with
    // `numbered`, not `numbering`, so that is every number -> null). Let it land first, so
    // the numbers asserted below are the ones New grid itself applied.
    const numberGrid = vi.spyOn(api, 'numberGrid');
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await waitFor(() => expect(numberGrid).toHaveBeenCalled());
    await act(async () => {
      await numberGrid.mock.results[0].value;
    });
    await typeLetter(user, container, 3, 3, 'A');
    const idBefore = docIdNow();
    const mintsBefore = probe.mintCalls;

    await user.click(sizeBtn('15\u00d715'));
    await user.click(screen.getByRole('button', { name: 'Replace' }));

    await waitFor(() => expect(letters(container)).toEqual([]));
    await waitFor(() => expect(probe.panelProps.grid[0][0].number).toBe(1));
    expect(docIdNow()).not.toBe(idBefore);
    expect(probe.mintCalls - mintsBefore).toBe(1);
    const expected = localNumber(probe.panelProps.grid).grid;
    expect(probe.panelProps.grid[0][0].number).toBe(1);
    expect(probe.panelProps.grid.map((row) => row.map((x) => x.number))).toEqual(
      expected.map((row) => row.map((x) => x.number))
    );
    expect(container.querySelectorAll('.xw-cell-number').length).toBeGreaterThan(0);
  });

  it('resets the selected cell and turns symmetry back on', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await user.click(screen.getByText('Symmetry'));
    await user.click(cells(container)[idx(2, 2)]);
    await typeLetter(user, container, 3, 3, 'A');
    expect(probe.panelProps.symmetryEnabled).toBe(false);
    expect(probe.panelProps.selectedCell).not.toBeNull();

    await user.click(sizeBtn('15\u00d715'));
    await user.click(screen.getByRole('button', { name: 'Replace' }));

    await waitFor(() => expect(letters(container)).toEqual([]));
    expect(probe.panelProps.symmetryEnabled).toBe(true);
    expect(probe.panelProps.selectedCell).toBeNull();
  });

  it('discards the retained run exactly once', async () => {
    const user = userEvent.setup();
    const discardRun = vi.fn();
    probe.autofillOverride = { discardRun };
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));

    await user.click(sizeBtn('11\u00d711'));

    expect(discardRun).toHaveBeenCalledTimes(1);
  });

  it('while a run is live the size buttons are disabled and createNewGrid is a no-op', async () => {
    const user = userEvent.setup();
    const discardRun = vi.fn();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 3, 3, 'A');
    const idBefore = docIdNow();
    const mintsBefore = probe.mintCalls;

    probe.autofillOverride = { state: 'running', discardRun };
    await user.click(screen.getByText('Symmetry')); // any re-render picks up the override
    await user.click(screen.getByText('Symmetry'));

    for (const label of ['11\u00d711', '15\u00d715', '21\u00d721']) {
      expect(sizeBtn(label)).toBeDisabled();
    }
    act(() => probe.panelProps.onNewGrid(11));

    expect(cells(container)).toHaveLength(225);
    expect(letters(container)).toEqual(['A']);
    expect(docIdNow()).toBe(idBefore);
    expect(probe.mintCalls).toBe(mintsBefore);
    expect(discardRun).not.toHaveBeenCalled();
  });
});

describe('App save wiring (§3.4)', () => {
  const SIZE = 15;
  const idx = (r, c) => r * SIZE + c;
  const focusEl = (container) => container.querySelector('.xw-grid-focus');
  const docIdNow = () => probe.autofillArgs.docId;
  const saveBtn = () => screen.getByRole('button', { name: /save grid/i });
  const nameInput = () => screen.findByRole('textbox');
  const result = (over = {}) => ({ savedAt: '2026-10-24T10:00:00.000Z', id: 'doc-1', name: 'n', forked: false, ...over });

  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
    probe.autofillOverride = null;
    probe.panelProps = null;
    vi.spyOn(storage, 'list').mockResolvedValue([]);
    vi.spyOn(storage, 'save').mockResolvedValue(result());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  const typeLetter = async (user, container, r, c, ch) => {
    await user.click(cells(container)[idx(r, c)]);
    fireEvent.keyDown(focusEl(container), { key: ch });
  };

  // A live run whose Start snapshot is the blank grid while the live grid carries an "A".
  const startLiveRunWithMergedLetter = async (user, container) => {
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    const snapshot = structuredClone(probe.panelProps.grid);
    await typeLetter(user, container, 3, 3, 'A');
    expect(letters(container)).toEqual(['A']);
    probe.autofillOverride = { state: 'running', startSnapshot: snapshot };
    await user.click(screen.getByText('Symmetry')); // re-render picks up the override
    await user.click(screen.getByText('Symmetry'));
    return snapshot;
  };

  it('Save on a new document opens a prompt prefilled with the default name', async () => {
    const user = userEvent.setup();
    renderApp();
    await waitFor(() => expect(probe.panelProps).not.toBeNull());
    await user.click(saveBtn());
    expect((await nameInput()).value).toMatch(/^15\u00d715 \d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
    expect(storage.save).not.toHaveBeenCalled();
  });

  it('Save with a stored entry for docId prefills its name', async () => {
    const user = userEvent.setup();
    renderApp();
    await waitFor(() => expect(probe.panelProps).not.toBeNull());
    storage.list.mockResolvedValue([{ id: docIdNow(), name: 'Mine' }]);
    await user.click(saveBtn());
    expect(await nameInput()).toHaveValue('Mine');
  });

  it('shows no prompt (so no wrong prefill) while list() is pending', async () => {
    const user = userEvent.setup();
    let release;
    storage.list.mockReturnValue(new Promise((r) => (release = r)));
    renderApp();
    await waitFor(() => expect(probe.panelProps).not.toBeNull());
    await user.click(saveBtn());
    expect(screen.queryByRole('textbox')).toBeNull();
    await act(async () => release([{ id: docIdNow(), name: 'Mine' }]));
    expect(await nameInput()).toHaveValue('Mine');
  });

  it('confirming a name calls saveNamed through storage.save and closes the prompt', async () => {
    const user = userEvent.setup();
    renderApp();
    await waitFor(() => expect(probe.panelProps).not.toBeNull());
    await user.click(saveBtn());
    const input = await nameInput();
    fireEvent.change(input, { target: { value: 'Puzzle 1' } });
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(storage.save.mock.calls[0][1]).toMatchObject({ name: 'Puzzle 1' });
    await waitFor(() => expect(screen.queryByRole('textbox')).toBeNull());
  });

  it('a failed save keeps the prompt open', async () => {
    const user = userEvent.setup();
    storage.save.mockRejectedValue(new Error('quota'));
    renderApp();
    await waitFor(() => expect(probe.panelProps).not.toBeNull());
    await user.click(saveBtn());
    await nameInput();
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    await act(async () => {});
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it("a different entry's name asks, and Replace saves with replaceEntryId", async () => {
    const user = userEvent.setup();
    storage.list.mockResolvedValue([{ id: 'x', name: 'Other' }]);
    renderApp();
    await waitFor(() => expect(probe.panelProps).not.toBeNull());
    await user.click(saveBtn());
    fireEvent.change(await nameInput(), { target: { value: 'Other' } });
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(screen.getByText('Replace the saved grid named "Other"?')).toBeInTheDocument();
    expect(storage.save).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(storage.save.mock.calls[0][1]).toMatchObject({ name: 'Other', replaceEntryId: 'x' });
  });

  it('the document\'s own current name is not a collision', async () => {
    const user = userEvent.setup();
    renderApp();
    await waitFor(() => expect(probe.panelProps).not.toBeNull());
    storage.list.mockResolvedValue([{ id: docIdNow(), name: 'Mine' }]);
    await user.click(saveBtn());
    await nameInput();
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(screen.queryByText(/Replace the saved grid/)).toBeNull();
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
  });

  it('autosave never opens the prompt', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 3, 3, 'A');
    await act(async () => vi.advanceTimersByTime(30000));
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(storage.list).not.toHaveBeenCalled();
    expect(screen.queryByRole('textbox')).toBeNull();
  });

  it('a fork result makes the returned id the docId', async () => {
    const user = userEvent.setup();
    storage.save.mockResolvedValue(result({ forked: true, id: 'forked-id' }));
    renderApp();
    await waitFor(() => expect(probe.panelProps).not.toBeNull());
    await user.click(saveBtn());
    await nameInput();
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(docIdNow()).toBe('forked-id'));
  });

  it('S2: autosave during a live run writes the Start snapshot, not the live grid', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { container } = renderApp();
    await startLiveRunWithMergedLetter(user, container);
    await act(async () => vi.advanceTimersByTime(30000));
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    const written = storage.save.mock.calls[0][0];
    expect(written.grid.flat().map((c) => c.letter).filter(Boolean)).toEqual([]);
    expect(written.grid[3][3].letter).toBe('');
  });

  it('S2: Save during a live run writes the Start snapshot', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await startLiveRunWithMergedLetter(user, container);
    await user.click(saveBtn());
    await nameInput();
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(storage.save.mock.calls[0][0].grid[3][3].letter).toBe('');
    expect(storage.save.mock.calls[0][1]).toMatchObject({ name: expect.any(String) });
  });

  it('S2: after a save during a run, savedSig is the snapshot signature (live merges stay clean, the run ending reads unsaved)', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    const snapshot = await startLiveRunWithMergedLetter(user, container);
    await user.click(saveBtn());
    await nameInput();
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(screen.getByText(/saved locally/)).toBeInTheDocument());
    // sanity: the signature the snapshot carries differs from the live grid's
    expect(contentSigOf(SIZE, snapshot)).not.toBe(contentSigOf(SIZE, probe.panelProps.grid));
    // the run ends at the live (merged) grid: storage holds the Start grid, so it is unsaved
    probe.autofillOverride = null;
    await user.click(screen.getByText('Symmetry'));
    await user.click(screen.getByText('Symmetry'));
    await waitFor(() => expect(screen.getByText('unsaved changes')).toBeInTheDocument());
  });

  // novice-readiness spec 0.2.7 §3.4 (S2): savedSig is the signature of the document the
  // machine WROTE, however the live grid moved between the write and its `saved` status.
  describe('a save whose write lands after the grid moved on', () => {
    const deferSave = () => {
      let resolve;
      storage.save.mockImplementation(() => new Promise((r) => (resolve = r)));
      return () => resolve(result());
    };
    const confirmSave = async (user) => {
      await user.click(saveBtn());
      await nameInput();
      await user.click(screen.getByRole('button', { name: 'Save' }));
      await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    };

    it('an edit between the write and `saved` leaves the document dirty', async () => {
      const user = userEvent.setup();
      const { container } = renderApp();
      await waitFor(() => expect(cells(container)).toHaveLength(225));
      await typeLetter(user, container, 3, 3, 'A');
      const release = deferSave();
      await confirmSave(user);
      await typeLetter(user, container, 4, 4, 'B');
      await act(async () => release());
      await waitFor(() => expect(screen.getByText('unsaved changes')).toBeInTheDocument());
      expect(screen.queryByText(/saved locally/)).toBeNull();
      expect(probe.saveArgs.isDirty).toBe(true);
    });

    it('the run ending between the write and `saved` leaves the document dirty', async () => {
      const user = userEvent.setup();
      const { container } = renderApp();
      await startLiveRunWithMergedLetter(user, container);
      const release = deferSave();
      await confirmSave(user);
      probe.autofillOverride = null; // the run ends with the merged grid
      await user.click(screen.getByText('Symmetry'));
      await user.click(screen.getByText('Symmetry'));
      await act(async () => release());
      await waitFor(() => expect(screen.getByText('unsaved changes')).toBeInTheDocument());
      expect(screen.queryByText(/saved locally/)).toBeNull();
      expect(probe.saveArgs.isDirty).toBe(true);
    });
  });
});
