/**
 * Tests for App-level grid import behavior.
 *
 * Regression coverage: importing a grid of a DIFFERENT size used to be wiped
 * because the `useEffect(() => initializeGrid(gridSize), [gridSize])` re-fired
 * on the size change and replaced the imported grid with an empty one.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act, within } from '@testing-library/react';
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

// novice-readiness spec 0.2.7 §3.4 (S3, PD-6-G4, PD-6-G9): restore on load, the banner, and
// restore across sizes. `storage.load` is mocked; everything else is the real App.
describe('App restore on load (§3.4)', () => {
  const idx = (size) => (r, c) => r * size + c;
  const focusEl = (container) => container.querySelector('.xw-grid-focus');
  const docIdNow = () => probe.autofillArgs.docId;
  const SAVED_AT = new Date(2026, 9, 22, 9, 30).toISOString();

  // A saved grid as storage.load hands it back: canonical cells minus isBlocked.
  const savedCells = (size, edits = {}) =>
    Array.from({ length: size }, (_, r) =>
      Array.from({ length: size }, (_, c) => ({
        letter: '',
        isBlack: false,
        isThemeLocked: false,
        number: null,
        isError: false,
        isAutofilled: false,
        ...(edits[`${r},${c}`] || {}),
      }))
    );
  const entryOf = (size, edits, over = {}) => ({
    id: 'saved-id',
    name: 'Mine',
    savedAt: SAVED_AT,
    size,
    grid: savedCells(size, edits),
    numbering: {},
    symmetryEnabled: true,
    ...over,
  });
  const restoreFrom = (entry) => vi.spyOn(storage, 'load').mockResolvedValue(entry);

  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
    probe.autofillOverride = null;
    probe.panelProps = null;
    probe.saveArgs = null;
    vi.spyOn(storage, 'list').mockResolvedValue([]);
    vi.spyOn(storage, 'save').mockResolvedValue({
      savedAt: '2026-10-24T10:00:00.000Z', id: 'saved-id', name: 'Mine', forked: false,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('load -> null: blank 15x15, no banner, the minted docId stays', async () => {
    restoreFrom(null);
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await waitFor(() => expect(storage.load).toHaveBeenCalled());
    await act(async () => {});
    expect(letters(container)).toEqual([]);
    expect(screen.queryByText(/^Restored /)).toBeNull();
    expect(docIdNow()).toMatch(/^doc-\d+$/);
  });

  it('load -> 15x15 entry: letters are back, banner text is local, docId is the entry id, nothing selected', async () => {
    restoreFrom(entryOf(15, { '2,3': { letter: 'Q' } }));
    const { container } = renderApp();
    expect(await screen.findByText('Restored "Mine" (saved 2026-10-22 09:30)')).toBeInTheDocument();
    expect(letters(container)).toEqual(['Q']);
    expect(cells(container)).toHaveLength(225);
    expect(docIdNow()).toBe('saved-id');
    expect(storage.load).toHaveBeenCalledTimes(1);
  });

  it('restore clears the selected cell (PD-6-G4)', async () => {
    let release;
    vi.spyOn(storage, 'load').mockReturnValue(new Promise((r) => (release = r)));
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await user.click(cells(container)[idx(15)(4, 4)]);
    await waitFor(() => expect(probe.panelProps.selectedCell).toMatchObject({ row: 4, col: 4 }));

    await act(async () => release(entryOf(15, { '2,3': { letter: 'Q' } })));

    await screen.findByText(/^Restored "Mine"/);
    expect(probe.panelProps.selectedCell).toBeNull();
  });

  it('load -> 21x21 entry while gridSize is 15: a 21x21 grid WITH the entry letters', async () => {
    restoreFrom(entryOf(21, { '4,5': { letter: 'Z' }, '20,20': { letter: 'K' } }));
    const { container } = renderApp();
    expect(await screen.findByText(/^Restored "Mine"/)).toBeInTheDocument();
    await waitFor(() => expect(cells(container)).toHaveLength(441));
    expect(letters(container)).toEqual(['Z', 'K']);
    expect(docIdNow()).toBe('saved-id');
    // let the [gridSize] effect and any numbering settle; the letters must still be there
    await act(async () => {});
    expect(letters(container)).toEqual(['Z', 'K']);
  });

  it('15x15 restore, then New grid -> 11x11 gives a blank, fresh 11x11 (no stray skip flag)', async () => {
    restoreFrom(entryOf(15, { '2,3': { letter: 'Q' } }));
    const user = userEvent.setup();
    const { container } = renderApp();
    await screen.findByText(/^Restored "Mine"/);
    expect(letters(container)).toEqual(['Q']);

    await user.click(screen.getByRole('button', { name: '11×11' }));
    await user.click(screen.getByRole('button', { name: 'Replace' }));

    await waitFor(() => expect(cells(container)).toHaveLength(121));
    expect(letters(container)).toEqual([]);
    expect(docIdNow()).not.toBe('saved-id');
  });

  it('cells without isAutofilled read false; a saved true stays true', async () => {
    const entry = entryOf(15, { '0,0': { letter: 'A', isAutofilled: true }, '0,1': { letter: 'B' } });
    delete entry.grid[0][1].isAutofilled;
    restoreFrom(entry);
    renderApp();
    await screen.findByText(/^Restored "Mine"/);
    const g = probe.panelProps.grid;
    expect(g[0][0].isAutofilled).toBe(true);
    expect(g[0][1].isAutofilled).toBe(false);
    expect(g.flat().filter((c) => c.isAutofilled)).toHaveLength(1);
  });

  it('the restored grid is born clean: no edits, banner stays, isDirty is false', async () => {
    restoreFrom(entryOf(15, { '2,3': { letter: 'Q' } }));
    renderApp();
    await screen.findByText(/^Restored "Mine"/);
    await act(async () => {});
    expect(probe.saveArgs.isDirty).toBe(false);
    expect(screen.getByText(/^Restored "Mine"/)).toBeInTheDocument();
  });

  it('the first autosave after a restore sends the loaded savedAt as expectedSavedAt', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    restoreFrom(entryOf(15, { '2,3': { letter: 'Q' } }));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { container } = renderApp();
    await screen.findByText(/^Restored "Mine"/);
    await user.click(cells(container)[idx(15)(5, 5)]);
    fireEvent.keyDown(focusEl(container), { key: 'W' });
    await act(async () => {
      vi.advanceTimersByTime(30000);
    });
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(storage.save.mock.calls[0][0].id).toBe('saved-id');
    expect(storage.save.mock.calls[0][1]).toMatchObject({ expectedSavedAt: SAVED_AT });
  });

  it('the dismiss button closes the banner', async () => {
    restoreFrom(entryOf(15, { '2,3': { letter: 'Q' } }));
    const user = userEvent.setup();
    renderApp();
    await screen.findByText(/^Restored "Mine"/);
    await user.click(screen.getByRole('button', { name: 'Dismiss' }));
    expect(screen.queryByText(/^Restored /)).toBeNull();
  });

  it('typing a letter closes the banner', async () => {
    restoreFrom(entryOf(15, { '2,3': { letter: 'Q' } }));
    const user = userEvent.setup();
    const { container } = renderApp();
    await screen.findByText(/^Restored "Mine"/);
    await user.click(cells(container)[idx(15)(5, 5)]);
    expect(screen.getByText(/^Restored "Mine"/)).toBeInTheDocument(); // selecting is not an edit
    fireEvent.keyDown(focusEl(container), { key: 'W' });
    await waitFor(() => expect(screen.queryByText(/^Restored /)).toBeNull());
  });

  it('a numbering reconcile that lands after the restore does not close the banner', async () => {
    // The mount's numbering reconcile (150 ms debounce) lands on the restored grid and
    // rewrites every `number` (the MSW handler answers with `numbered`, so all become null).
    // contentSigOf excludes `number`, so the banner must survive it.
    const numberGrid = vi.spyOn(api, 'numberGrid');
    restoreFrom(entryOf(15, { '2,3': { letter: 'Q' }, '0,0': { number: 99 } }));
    renderApp();
    await screen.findByText(/^Restored "Mine"/);
    expect(probe.panelProps.grid[0][0].number).toBe(99);
    await waitFor(() => expect(numberGrid).toHaveBeenCalled());
    await waitFor(() => expect(probe.panelProps.grid[0][0].number).not.toBe(99));
    await act(async () => {});
    expect(screen.getByText(/^Restored "Mine"/)).toBeInTheDocument();
    expect(probe.saveArgs.isDirty).toBe(false);
  });

  it('Start blank closes the banner and shows the Grid panel with the New grid buttons', async () => {
    restoreFrom(entryOf(15, { '2,3': { letter: 'Q' } }));
    const user = userEvent.setup();
    const { container } = renderApp();
    await screen.findByText(/^Restored "Mine"/);
    await user.click(screen.getByRole('button', { name: /^import$/i })); // leave the Grid tool
    expect(screen.queryByRole('button', { name: '11×11' })).toBeNull();

    await user.click(screen.getByRole('button', { name: 'Start blank' }));

    expect(screen.queryByText(/^Restored /)).toBeNull();
    expect(screen.getByRole('button', { name: '11×11' })).toBeInTheDocument();
    // it does not create a grid by itself (PD-6-G9)
    expect(letters(container)).toEqual(['Q']);
  });
});

// novice-readiness spec 0.2.7 §3.4 (S3, M1, PD-6-G4, PD-6-G20): Open saved. `storage.list` and
// `storage.load` are mocked; the Grid panel, the save machine and the grid are real.
describe('App Open saved (§3.4)', () => {
  const idx = (size) => (r, c) => r * size + c;
  const focusEl = (container) => container.querySelector('.xw-grid-focus');
  const docIdNow = () => probe.autofillArgs.docId;
  const REPLACE = 'Replace the current grid? Unsaved changes are lost.';
  const SAVED_AT = new Date(2026, 9, 22, 9, 30).toISOString();
  const OTHER_AT = new Date(2026, 9, 21, 8, 0).toISOString();

  const savedCells = (size, edits = {}) =>
    Array.from({ length: size }, (_, r) =>
      Array.from({ length: size }, (_, c) => ({
        letter: '',
        isBlack: false,
        isThemeLocked: false,
        number: null,
        isError: false,
        isAutofilled: false,
        ...(edits[`${r},${c}`] || {}),
      }))
    );
  const entryOf = (id, name, size, edits, over = {}) => ({
    id,
    name,
    savedAt: SAVED_AT,
    size,
    grid: savedCells(size, edits),
    numbering: {},
    symmetryEnabled: true,
    ...over,
  });
  const E15 = () => entryOf('e15', 'Fifteen', 15, { '1,1': { letter: 'F' } });
  const E21 = () => entryOf('e21', 'Twenty-one', 21, { '4,5': { letter: 'Z' }, '20,20': { letter: 'K' } });
  const listing = (...entries) => vi.spyOn(storage, 'list').mockResolvedValue(entries);
  const rowOf = (name) => screen.getByText(name).closest('li');
  // list() resolves after the click; flush it inside act so the state update is wrapped.
  const pressOpenSaved = (user) =>
    act(async () => {
      await user.click(screen.getByRole('button', { name: 'Open saved' }));
    });
  const openFromList = async (user, name) => {
    await pressOpenSaved(user);
    await screen.findByText(name);
    await user.click(within(rowOf(name)).getByRole('button', { name: 'Open' }));
  };
  // Let the numbering reconcile that follows a grid change land inside act (150 ms debounce).
  const settle = () => act(async () => new Promise((r) => setTimeout(r, 400)));
  const typeLetter = async (user, container, r, c, ch) => {
    await user.click(cells(container)[idx(15)(r, c)]);
    fireEvent.keyDown(focusEl(container), { key: ch });
  };

  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
    probe.autofillOverride = null;
    probe.panelProps = null;
    probe.saveArgs = null;
    vi.spyOn(storage, 'load').mockResolvedValue(null);
    vi.spyOn(storage, 'list').mockResolvedValue([]);
    vi.spyOn(storage, 'save').mockResolvedValue({
      savedAt: '2026-10-24T10:00:00.000Z', id: 'e15', name: 'Fifteen', forked: false,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('a blank grid opens an entry at once: its letters, its docId, no confirm', async () => {
    listing(E15());
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await openFromList(user, 'Fifteen');
    expect(screen.queryByText(REPLACE)).toBeNull();
    expect(letters(container)).toEqual(['F']);
    expect(docIdNow()).toBe('e15');
  });

  it('a grid with a letter asks first: Cancel leaves grid and docId, Replace opens', async () => {
    listing(E15());
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 3, 3, 'A');
    await settle();
    const idBefore = docIdNow();

    await openFromList(user, 'Fifteen');
    expect(screen.getByText(REPLACE)).toBeInTheDocument();
    expect(letters(container)).toEqual(['A']);
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(letters(container)).toEqual(['A']);
    expect(docIdNow()).toBe(idBefore);

    await user.click(within(rowOf('Fifteen')).getByRole('button', { name: 'Open' }));
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    expect(letters(container)).toEqual(['F']);
    expect(docIdNow()).toBe('e15');
    await settle();
  });

  it('after a same-size restore, Open a 21x21 entry: a 21x21 grid with its letters (S3)', async () => {
    vi.spyOn(storage, 'load').mockResolvedValue(entryOf('r15', 'Restored one', 15, { '2,3': { letter: 'Q' } }));
    listing(E21());
    const user = userEvent.setup();
    const { container } = renderApp();
    await screen.findByText(/^Restored "Restored one"/);
    await settle();
    expect(letters(container)).toEqual(['Q']);

    await openFromList(user, 'Twenty-one');
    await user.click(screen.getByRole('button', { name: 'Replace' }));

    await waitFor(() => expect(cells(container)).toHaveLength(441));
    expect(letters(container)).toEqual(['Z', 'K']);
    await act(async () => {});
    expect(letters(container)).toEqual(['Z', 'K']);
    expect(docIdNow()).toBe('e21');
    await settle();
  });

  it('Open a same-size entry, then New grid -> 11x11 gives a blank 11x11 (no stray skip flag)', async () => {
    listing(E15());
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await settle();
    await openFromList(user, 'Fifteen');
    expect(letters(container)).toEqual(['F']);

    await user.click(screen.getByRole('button', { name: '11×11' }));
    await user.click(screen.getByRole('button', { name: 'Replace' }));

    await waitFor(() => expect(cells(container)).toHaveLength(121));
    expect(letters(container)).toEqual([]);
    expect(docIdNow()).not.toBe('e15');
    await settle();
  });

  it('adopts the entry id and savedAt: the next autosave updates entry e, expecting its savedAt', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    listing(E15());
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await openFromList(user, 'Fifteen');
    await typeLetter(user, container, 5, 5, 'W');
    await act(async () => {
      vi.advanceTimersByTime(30000);
    });
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(storage.save.mock.calls[0][0].id).toBe('e15');
    expect(storage.save.mock.calls[0][1]).toMatchObject({ expectedSavedAt: SAVED_AT });
  });

  it('the opened grid is born clean, selection is cleared and the restore banner is dismissed', async () => {
    vi.spyOn(storage, 'load').mockResolvedValue(entryOf('r15', 'Restored one', 15, {}));
    listing(E15());
    const user = userEvent.setup();
    const { container } = renderApp();
    await screen.findByText(/^Restored "Restored one"/);
    await user.click(cells(container)[idx(15)(4, 4)]);
    await waitFor(() => expect(probe.panelProps.selectedCell).toMatchObject({ row: 4, col: 4 }));

    await openFromList(user, 'Fifteen');

    expect(screen.queryByText(/^Restored /)).toBeNull();
    expect(probe.panelProps.selectedCell).toBeNull();
    await act(async () => {});
    expect(probe.saveArgs.isDirty).toBe(false);
  });

  it('Open discards the retained run exactly once, and loads isAutofilled as saved with isBlocked false', async () => {
    const discardRun = vi.fn();
    probe.autofillOverride = { discardRun };
    listing(
      entryOf('ea', 'Auto', 15, {
        '0,0': { letter: 'A', isAutofilled: true },
        '0,1': { letter: 'B' },
        '0,2': { isBlack: true, isBlocked: true },
      })
    );
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await openFromList(user, 'Auto');
    const g = probe.panelProps.grid;
    expect(discardRun).toHaveBeenCalledTimes(1);
    expect(g[0][0].isAutofilled).toBe(true);
    expect(g[0][1].isAutofilled).toBe(false);
    expect(g.flat().some((c) => c.isBlocked)).toBe(false);
  });

  it('while a run is live the Open saved button and the rows are disabled', async () => {
    listing(E15());
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await pressOpenSaved(user);
    await screen.findByText('Fifteen');

    probe.autofillOverride = { state: 'running' };
    await user.click(screen.getByText('Symmetry')); // any re-render picks up the override
    await user.click(screen.getByText('Symmetry'));

    expect(screen.getByRole('button', { name: 'Open saved' })).toBeDisabled();
    expect(within(rowOf('Fifteen')).getByRole('button', { name: 'Open' })).toBeDisabled();
    expect(within(rowOf('Fifteen')).getByRole('button', { name: 'Delete' })).toBeDisabled();
  });

  it('openSavedEntry called directly while a run is live changes neither grid nor docId (D1)', async () => {
    const discardRun = vi.fn();
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 3, 3, 'A');
    const idBefore = docIdNow();
    probe.autofillOverride = { state: 'running', discardRun };
    await user.click(screen.getByText('Symmetry'));
    await user.click(screen.getByText('Symmetry'));

    act(() => probe.panelProps.onOpenSaved(E21()));

    expect(cells(container)).toHaveLength(225);
    expect(letters(container)).toEqual(['A']);
    expect(docIdNow()).toBe(idBefore);
    expect(discardRun).not.toHaveBeenCalled();
  });

  describe('a malformed entry (grid not an array of arrays) is adopted by nothing', () => {
    // The mount's numbering reconcile (150 ms debounce, then a request) sets state when it
    // lands; let it land inside act so the only console.error left is the guard's own.
    const settle = () => act(async () => new Promise((r) => setTimeout(r, 400)));
    const MALFORMED = [
      ['null grid', { grid: null }],
      ['a flat array', { grid: ['A', 'B'] }],
      ['a missing grid', { grid: undefined }],
    ];

    it.each(MALFORMED)('Open: %s leaves grid, docId and banner unchanged; one console.error', async (_n, over) => {
      vi.spyOn(storage, 'load').mockResolvedValue(entryOf('r15', 'Restored one', 15, { '2,3': { letter: 'Q' } }));
      listing(entryOf('bad', 'Broken', 15, {}, over));
      const err = vi.spyOn(console, 'error').mockImplementation(() => {});
      const user = userEvent.setup();
      const { container } = renderApp();
      await screen.findByText(/^Restored "Restored one"/);
      await settle();

      await pressOpenSaved(user);
      await screen.findByText('Broken');
      await user.click(within(rowOf('Broken')).getByRole('button', { name: 'Open' }));
      await user.click(screen.getByRole('button', { name: 'Replace' }));

      expect(err).toHaveBeenCalledTimes(1);
      expect(letters(container)).toEqual(['Q']);
      expect(docIdNow()).toBe('r15');
      expect(screen.getByText(/^Restored "Restored one"/)).toBeInTheDocument();
    });

    it.each(MALFORMED)('restore: %s leaves the blank grid and minted docId; one console.error', async (_n, over) => {
      vi.spyOn(storage, 'load').mockResolvedValue(entryOf('bad', 'Broken', 15, {}, over));
      const err = vi.spyOn(console, 'error').mockImplementation(() => {});
      const { container } = renderApp();
      await waitFor(() => expect(storage.load).toHaveBeenCalled());
      await act(async () => {});
      expect(err).toHaveBeenCalledTimes(1);
      expect(cells(container)).toHaveLength(225);
      expect(letters(container)).toEqual([]);
      expect(docIdNow()).toMatch(/^doc-\d+$/);
      expect(screen.queryByText(/^Restored /)).toBeNull();
    });
  });
});

// novice-readiness spec 0.2.7 §3.4: a corrupt element in the stored array must not crash Open
// saved. Real `storage.list` over the localStorage mock; only `load` is stubbed (null) so the
// restore-on-load does not adopt the entry before the test opens it.
describe('App Open saved over corrupt stored data (§3.4)', () => {
  const pressOpenSaved = (user) =>
    act(async () => {
      await user.click(screen.getByRole('button', { name: 'Open saved' }));
    });
  const SAVED_AT = new Date(2026, 9, 22, 9, 30).toISOString();
  const cellsOf = (size) =>
    Array.from({ length: size }, (_, r) =>
      Array.from({ length: size }, (_, c) => ({
        letter: r === 1 && c === 1 ? 'F' : '',
        isBlack: false,
        isThemeLocked: false,
        number: null,
        isError: false,
        isAutofilled: false,
      }))
    );
  const valid = { id: 'e15', name: 'Fifteen', savedAt: SAVED_AT, size: 15, grid: cellsOf(15), numbering: {}, symmetryEnabled: true };

  beforeEach(() => {
    probe.autofillOverride = null;
    probe.panelProps = null;
    global.localStorage.getItem.mockImplementation((k) =>
      k === storage.SAVE_KEY ? JSON.stringify([null, valid]) : null
    );
    vi.spyOn(storage, 'load').mockResolvedValue(null);
  });

  afterEach(() => {
    global.localStorage.getItem.mockReset();
    vi.restoreAllMocks();
  });

  it('lists the one valid entry and Open adopts it', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await pressOpenSaved(user);
    await screen.findByText('Fifteen');
    expect(screen.getAllByRole('listitem')).toHaveLength(1);
    await user.click(within(screen.getByRole('listitem')).getByRole('button', { name: 'Open' }));
    expect(letters(container)).toEqual(['F']);
    expect(probe.autofillArgs.docId).toBe('e15');
  });
});

// novice-readiness spec 0.2.7 §3.5 (#62), §6 SR-PLACE: placing a Search result through the UI
// skips a theme-locked cell, stops at a black square, and leaves cells beyond it alone.
describe('App Search placement (§3.5 #62, SR-PLACE)', () => {
  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
  });

  const SIZE = 15;
  const idx = (r, c) => r * SIZE + c;
  const focusEl = (container) => container.querySelector('.xw-grid-focus');
  const shownWords = () =>
    Array.from(document.querySelectorAll('.word-display')).map((el) => el.textContent);

  it('writes C, keeps the locked X, writes A, stops at the black square', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(SIZE * SIZE));

    // Row 0: col 1 holds X and is locked with Ctrl+L; col 3 is black (Space).
    await user.click(cells(container)[idx(0, 1)]);
    fireEvent.keyDown(focusEl(container), { key: 'x' });
    await user.click(cells(container)[idx(0, 1)]);
    fireEvent.keyDown(focusEl(container), { key: 'l', ctrlKey: true });
    await user.click(cells(container)[idx(0, 3)]);
    fireEvent.keyDown(focusEl(container), { key: ' ' });
    expect(letters(container)).toEqual(['X']);
    const blackBefore = blackCells(container).length;
    expect(blackBefore).toBeGreaterThan(0);

    // Select (0,0), open Search, run a search and pick the result.
    await user.click(cells(container)[idx(0, 0)]);
    await user.click(screen.getAllByRole('button', { name: /^search$/i })[0]);
    await user.type(screen.getByPlaceholderText(/enter pattern/i), 'C????');
    const before = global.EventSource.instances.length;
    await user.click(document.querySelector('.search-btn'));
    await waitFor(() => expect(global.EventSource.instances.length).toBe(before + 1));
    await act(async () => {
      global.EventSource.instances[before].onmessage({
        data: JSON.stringify({
          status: 'complete',
          progress: 100,
          message: 'Search complete',
          data: { results: [{ word: 'CRATE', score: 90 }] },
        }),
      });
    });
    await waitFor(() => expect(shownWords()).toEqual(['CRATE']));
    await user.click(document.querySelector('.result-item'));

    // C at col 0; the locked X consumed the R; A at col 2; the black square at col 3
    // stops the walk, so T and E are never written.
    await waitFor(() => expect(letters(container)).toEqual(['C', 'X', 'A']));
    expect(blackCells(container)).toHaveLength(blackBefore);
  });
});

// novice-readiness spec 0.2.7 §3.5 (G5), §2.3 (S1), #63, #73: Verify and Clean apply to the
// grid as it is when the response lands, and Clean asks before it blanks anything.
describe('App Verify and Clean (§3.5 G5, §2.3 S1, #63)', () => {
  const SIZE = 15;
  const idx = (r, c) => r * SIZE + c;
  const focusEl = (container) => container.querySelector('.xw-grid-focus');
  const docIdNow = () => probe.autofillArgs.docId;
  const gridNow = () => probe.panelProps.grid;
  const SERVER_MESSAGE = 'Cleared 2 cells in 1 invalid word';
  const CLEAN_OK = 'Grid is clean — all words are valid!';
  const KEPT = 'Nothing removed: theme-locked letters are kept.';

  const deferred = () => {
    let resolve;
    const promise = new Promise((res) => {
      resolve = res;
    });
    return { promise, resolve };
  };
  // The server echoes the cell shape it was sent: { letter, isBlack } objects.
  const serverGrid = (row0 = '') =>
    Array.from({ length: SIZE }, (_, r) =>
      Array.from({ length: SIZE }, (_, c) => ({
        letter: r === 0 ? row0[c] || '' : '',
        isBlack: false,
      }))
    );
  const cleanResp = (row0, removed) => ({
    grid: serverGrid(row0),
    removed_count: removed,
    valid_count: 0,
    cleared_cells: removed,
    message: SERVER_MESSAGE,
  });
  const flagged = (...cells) => ({
    invalid_words: [{ word: 'CAT', status: 'invalid', cells }],
    invalid_count: 1,
    total_checked: 3,
    wordlist_size: 100,
  });
  // Numbering reconciles asynchronously after typing; it is not part of what Cancel must preserve.
  const unnumbered = (g) => g.map((row) => row.map(({ number, ...rest }) => rest));
  const errorsNow = () => gridNow().flat().filter((x) => x.isError).length;

  // The click's follow-up state updates land after userEvent returns; the act scope covers them.
  const clickCell = (user, container, r, c) =>
    act(async () => {
      await user.click(cells(container)[idx(r, c)]);
    });
  const typeAt = async (user, container, r, c, ch) => {
    await clickCell(user, container, r, c);
    fireEvent.keyDown(focusEl(container), { key: ch });
  };
  const lockAt = async (user, container, r, c) => {
    await clickCell(user, container, r, c);
    fireEvent.keyDown(focusEl(container), { key: 'l', ctrlKey: true });
  };
  const typeCat = async (user, container) => {
    await typeAt(user, container, 0, 0, 'c');
    await typeAt(user, container, 0, 1, 'a');
    await typeAt(user, container, 0, 2, 't');
  };
  const boot = async () => {
    vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
    const user = userEvent.setup();
    let view;
    await act(async () => {
      view = renderApp();
    });
    await waitFor(() => expect(cells(view.container)).toHaveLength(SIZE * SIZE));
    await waitFor(() => expect(screen.getByRole('button', { name: /clean grid/i })).toBeEnabled());
    return { user, ...view };
  };
  // The response's state updates land in microtasks after the click; the act scope covers them.
  const press = (user, name) =>
    act(async () => {
      await user.click(screen.getByRole('button', { name }));
    });
  const clickClean = (user) => press(user, /clean grid/i);
  const clickVerify = (user) => press(user, /verify words/i);
  const land = (d, value) =>
    act(async () => {
      d.resolve(value);
      await d.promise;
    });
  const confirmText = () => screen.queryByRole('group', { name: /^Clean will remove/ });

  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
    probe.autofillOverride = null;
    probe.panelProps = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('Verify: a letter typed while the request was in flight survives, and the flagged cells show isError (#73)', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    const d = deferred();
    vi.spyOn(api, 'verifyWords').mockReturnValue(d.promise);
    await clickVerify(user);
    await typeAt(user, container, 5, 5, 'q');
    await land(d, flagged([0, 0], [0, 1], [0, 2]));
    expect(await screen.findByText(/1 of 3 words flagged/)).toBeInTheDocument();
    expect(gridNow()[5][5].letter).toBe('Q');
    expect([0, 1, 2].map((c) => gridNow()[0][c].isError)).toEqual([true, true, true]);
    expect(errorsNow()).toBe(3);
  });

  it('Verify with nothing flagged keeps its toast', async () => {
    const { user } = await boot();
    vi.spyOn(api, 'verifyWords').mockResolvedValue({
      invalid_words: [],
      invalid_count: 0,
      total_checked: 4,
      wordlist_size: 100,
    });
    await clickVerify(user);
    expect(await screen.findByText('All 4 words valid!')).toBeInTheDocument();
  });

  it('Verify in flight, docId changes: nothing is written, no toast (PD-6-G12)', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    const d = deferred();
    vi.spyOn(api, 'verifyWords').mockReturnValue(d.promise);
    await clickVerify(user);
    const idBefore = docIdNow();
    act(() => probe.panelProps.onNewGrid(SIZE));
    await waitFor(() => expect(docIdNow()).not.toBe(idBefore));
    await land(d, flagged([0, 0], [0, 1], [0, 2]));
    expect(errorsNow()).toBe(0);
    expect(screen.queryByText(/words flagged/)).toBeNull();
  });

  it('Clean, N > 0: the confirm counts the letters, Cancel changes nothing (red cells included) and toasts nothing', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    vi.spyOn(api, 'verifyWords').mockResolvedValue(flagged([0, 0], [0, 1]));
    await clickVerify(user);
    await waitFor(() => expect(errorsNow()).toBe(2));
    const redAt = () =>
      gridNow().flatMap((row, r) => row.flatMap((x, c) => (x.isError ? [`${r},${c}`] : [])));
    const redBefore = redAt();
    const before = unnumbered(structuredClone(gridNow()));
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleanResp('C', 2));
    await clickClean(user);
    expect(await screen.findByText('Clean will remove 2 letters')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(confirmText()).toBeNull();
    expect(redAt()).toEqual(redBefore);
    expect(redBefore).toEqual(['0,0', '0,1']);
    expect(unnumbered(gridNow())).toEqual(before);
    expect(screen.queryByText(SERVER_MESSAGE)).toBeNull();
  });

  it('Clean, N === 1: singular text', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleanResp('CA', 1));
    await clickClean(user);
    expect(await screen.findByText('Clean will remove 1 letter')).toBeInTheDocument();
  });

  it('Clean, N > 0, accept: the letters blank, the locked letter stays, the toast is the server message', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    await lockAt(user, container, 0, 1);
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleanResp('C', 2));
    await clickClean(user);
    expect(await screen.findByText('Clean will remove 1 letter')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Clean' }));
    expect(confirmText()).toBeNull();
    expect(gridNow()[0].slice(0, 3).map((x) => x.letter)).toEqual(['C', 'A', '']);
    expect(gridNow()[0][1].isThemeLocked).toBe(true);
    expect(await screen.findByText(SERVER_MESSAGE)).toBeInTheDocument();
  });

  it('Clean in flight, the user types: only cells still holding the sent letter are offered', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    const d = deferred();
    vi.spyOn(api, 'cleanGrid').mockReturnValue(d.promise);
    await clickClean(user);
    await typeAt(user, container, 0, 1, 'q');
    await land(d, cleanResp('C', 2));
    expect(await screen.findByText('Clean will remove 1 letter')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Clean' }));
    expect(gridNow()[0].slice(0, 3).map((x) => x.letter)).toEqual(['C', 'Q', '']);
  });

  it('Clean, N === 0 and nothing removed (#63): no confirm, the clean toast, and no cell stays red', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    vi.spyOn(api, 'verifyWords').mockResolvedValue(flagged([0, 0], [0, 1], [0, 2]));
    await clickVerify(user);
    await waitFor(() => expect(errorsNow()).toBe(3));
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleanResp('CAT', 0));
    await clickClean(user);
    expect(await screen.findByText(CLEAN_OK)).toBeInTheDocument();
    expect(confirmText()).toBeNull();
    expect(errorsNow()).toBe(0);
  });

  it('Clean, N === 0 with removals the locks prevent: the kept toast, and no cell stays red', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    await lockAt(user, container, 0, 1);
    await lockAt(user, container, 0, 2);
    vi.spyOn(api, 'verifyWords').mockResolvedValue(flagged([0, 0], [0, 1], [0, 2]));
    await clickVerify(user);
    await waitFor(() => expect(errorsNow()).toBe(3));
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleanResp('C', 2));
    await clickClean(user);
    expect(await screen.findByText(KEPT)).toBeInTheDocument();
    expect(confirmText()).toBeNull();
    expect(errorsNow()).toBe(0);
    expect(gridNow()[0].slice(0, 3).map((x) => x.letter)).toEqual(['C', 'A', 'T']);
  });

  it('Clean in flight, docId changes: no confirm, no write, no toast (PD-6-G12)', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    const d = deferred();
    vi.spyOn(api, 'cleanGrid').mockReturnValue(d.promise);
    await clickClean(user);
    const idBefore = docIdNow();
    act(() => probe.panelProps.onNewGrid(SIZE));
    await waitFor(() => expect(docIdNow()).not.toBe(idBefore));
    const fresh = gridNow();
    await land(d, cleanResp('C', 2));
    expect(confirmText()).toBeNull();
    expect(gridNow()).toBe(fresh);
    expect(screen.queryByText(SERVER_MESSAGE)).toBeNull();
    expect(screen.queryByText(CLEAN_OK)).toBeNull();
    expect(screen.queryByText(KEPT)).toBeNull();
  });

  it('an open confirm is dismissed, applying nothing, when the user types', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleanResp('C', 2));
    await clickClean(user);
    await screen.findByText('Clean will remove 2 letters');
    await typeAt(user, container, 8, 8, 'z');
    await waitFor(() => expect(confirmText()).toBeNull());
    expect(gridNow()[0].slice(0, 3).map((x) => x.letter)).toEqual(['C', 'A', 'T']);
    expect(screen.queryByText(SERVER_MESSAGE)).toBeNull();
  });

  it('an isError-only change (Verify landing) does not dismiss an open confirm (PD-6-G11)', async () => {
    const { user, container } = await boot();
    await typeCat(user, container);
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleanResp('C', 2));
    await clickClean(user);
    await screen.findByText('Clean will remove 2 letters');
    vi.spyOn(api, 'verifyWords').mockResolvedValue(flagged([0, 0], [0, 1], [0, 2]));
    await clickVerify(user);
    await waitFor(() => expect(errorsNow()).toBe(3));
    expect(confirmText()).not.toBeNull();
  });

  it('an open confirm is dismissed, applying nothing, when a run starts', async () => {
    const { user, container, rerender } = await boot();
    await typeCat(user, container);
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleanResp('C', 2));
    await clickClean(user);
    await screen.findByText('Clean will remove 2 letters');
    probe.autofillOverride = { state: 'submitting' };
    rerender(<App />);
    await waitFor(() => expect(confirmText()).toBeNull());
    expect(gridNow()[0].slice(0, 3).map((x) => x.letter)).toEqual(['C', 'A', 'T']);
    expect(screen.queryByText(SERVER_MESSAGE)).toBeNull();
  });
});

// novice-readiness spec 0.2.7 §3.6 (TH5): with the Theme panel open, Save stays reachable.
describe('App Theme panel and the top bar (§3.6 TH5)', () => {
  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
    vi.spyOn(storage, 'list').mockResolvedValue([]);
  });

  it('Save grid still opens the name prompt with the panel open, and x closes the panel', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await user.click(screen.getByRole('button', { name: /^Theme$/ }));
    expect(container.querySelector('.theme-words-panel')).not.toBeNull();
    const save = screen.getByRole('button', { name: /save grid/i });
    expect(save).toBeEnabled();
    await user.click(save);
    expect(await screen.findByRole('textbox')).toBeInTheDocument();
    await user.click(container.querySelector('.close-btn'));
    expect(container.querySelector('.theme-words-panel')).toBeNull();
  });
});

// novice-readiness spec 0.2.8 §3.2 Import (F3, M3, Q2): import confirms before replacing a
// grid with content, is born numbered, and clears a finished run.
describe('App import: confirm, numbering, run discard (§3.2)', () => {
  const REPLACE = 'Replace the current grid? Unsaved changes are lost.';
  const numberCount = (container) => container.querySelectorAll('.xw-cell-number').length;
  const settle = () => act(async () => new Promise((r) => setTimeout(r, 400)));
  const blank15 = () => {
    const grid = Array.from({ length: 15 }, () => Array(15).fill('.'));
    grid[0][0] = 'C';
    grid[0][1] = 'A';
    grid[0][2] = 'T';
    return { size: 15, grid };
  };
  // Stops at the "Import Grid" button so a test can press it itself.
  const preparePaste = async (user, gridJson) => {
    await user.click(screen.getByRole('button', { name: /^import$/i }));
    await user.click(screen.getByRole('button', { name: /paste json/i }));
    fireEvent.change(screen.getByLabelText(/paste json data/i), {
      target: { value: JSON.stringify(gridJson) },
    });
    await user.click(screen.getByRole('button', { name: /validate json/i }));
    await screen.findByRole('button', { name: /import grid/i });
  };
  const typeLetter = async (user, container, r, c, ch) => {
    await user.click(cells(container)[r * 15 + c]);
    fireEvent.keyDown(container.querySelector('.xw-grid-focus'), { key: ch });
  };

  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
    probe.autofillOverride = null;
  });

  afterEach(() => {
    probe.autofillOverride = null;
  });

  it('numbers an imported grid with the same size and layout right after the import (F3)', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await waitFor(() => expect(numberCount(container)).toBe(29));
    await settle();

    await importGridViaPaste(user, container, blank15());

    await waitFor(() => expect(letters(container)).toEqual(expect.arrayContaining(['C', 'A', 'T'])), {
      timeout: 3000,
    });
    expect(numberCount(container)).toBe(29);
  });

  it('discards the retained run when a grid is imported (M3)', async () => {
    const user = userEvent.setup();
    const discardRun = vi.fn();
    probe.autofillOverride = { discardRun };
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));

    await importGridViaPaste(user, container, blank15());

    await waitFor(() => expect(letters(container)).toEqual(expect.arrayContaining(['C'])), {
      timeout: 3000,
    });
    expect(discardRun).toHaveBeenCalledTimes(1);
  });

  it('asks before replacing a grid with a letter; Cancel keeps it (Q2)', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 5, 5, 'Q');
    expect(letters(container)).toEqual(['Q']);

    await preparePaste(user, blank15());
    await user.click(screen.getByRole('button', { name: /import grid/i }));

    expect(screen.getByText(REPLACE)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Replace' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    await settle();

    expect(screen.queryByText(REPLACE)).toBeNull();
    expect(letters(container)).toEqual(['Q']);
  });

  it('a second press of Import Grid while the confirm is open does not replace the grid (Q2)', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 5, 5, 'Q');

    await preparePaste(user, blank15());
    await user.click(screen.getByRole('button', { name: /import grid/i }));
    expect(screen.getByText(REPLACE)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /import grid/i }));
    await settle();

    expect(letters(container)).toEqual(['Q']);
    expect(screen.getByText(REPLACE)).toBeInTheDocument();
  });

  it('replaces the grid once Replace is pressed (Q2)', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 5, 5, 'Q');

    await preparePaste(user, blank15());
    await user.click(screen.getByRole('button', { name: /import grid/i }));
    await user.click(screen.getByRole('button', { name: 'Replace' }));

    await waitFor(() => expect(letters(container)).toEqual(['C', 'A', 'T']), { timeout: 3000 });
  });

  it('shows no confirm over an empty grid (Q2)', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));

    await preparePaste(user, blank15());
    await user.click(screen.getByRole('button', { name: /import grid/i }));

    expect(screen.queryByText(REPLACE)).toBeNull();
    await waitFor(() => expect(letters(container)).toEqual(['C', 'A', 'T']), { timeout: 3000 });
  });
});
