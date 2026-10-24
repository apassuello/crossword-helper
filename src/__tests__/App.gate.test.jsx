/**
 * Task 4.4: the D1 writer gate (novice-readiness spec 0.2.6 section 2.3).
 * While an autofill run is live (machine state `submitting` or `running`) no
 * grid writer runs except the machine's own onGridUpdate.
 *
 * Every "unchanged" assertion here has a control proving the path is live:
 * the same input DOES write when no run is live, `health` is online so
 * Verify/Clean are not disabled for being offline, and verifyWords/cleanGrid
 * WERE called before Start so the post-await check is what blocks the write.
 *
 * CrosswordGrid, TopBar, PatternMatcher, ThemeWordsPanel and ImportPanel are wrapped
 * (real component rendered) only to capture the handler props App passes, so
 * the App-level write-time early returns can be called directly, past the
 * controls that are already disabled.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  }),
  Toaster: () => null,
}));

const captured = vi.hoisted(() => ({}));

vi.mock('../components/bench/CrosswordGrid', async () => {
  const actual = await vi.importActual('../components/bench/CrosswordGrid');
  const R = await import('react');
  const Wrapped = (props) => {
    captured.grid = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: Wrapped };
});
vi.mock('../components/bench/TopBar', async () => {
  const actual = await vi.importActual('../components/bench/TopBar');
  const R = await import('react');
  const Wrapped = (props) => {
    captured.topbar = props;
    return R.createElement(actual.TopBar, props);
  };
  return { ...actual, TopBar: Wrapped };
});
vi.mock('../components/PatternMatcher', async () => {
  const actual = await vi.importActual('../components/PatternMatcher');
  const R = await import('react');
  const Wrapped = (props) => {
    captured.pattern = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: Wrapped };
});
vi.mock('../components/ThemeWordsPanel', async () => {
  const actual = await vi.importActual('../components/ThemeWordsPanel');
  const R = await import('react');
  const Wrapped = (props) => {
    captured.theme = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: Wrapped };
});
vi.mock('../components/ImportPanel', async () => {
  const actual = await vi.importActual('../components/ImportPanel');
  const R = await import('react');
  const Wrapped = (props) => {
    captured.importPanel = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: Wrapped };
});

const STATUS = 'Editing is paused while autofill runs.';
const renderApp = () => render(<App />, { wrapper: ToastProvider });
const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const blackCount = (c) => c.querySelectorAll('rect[fill="var(--ink)"]').length;
const lockCount = (c) => c.querySelectorAll('path[fill="var(--accent)"]').length;
const underlines = (c) => c.querySelectorAll('line[stroke="var(--danger)"]').length;
const letters = (c) =>
  Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const flush = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });

let startFillD;

beforeEach(() => {
  global.localStorage.getItem.mockReturnValue(null);
  for (const k of Object.keys(captured)) delete captured[k];
  startFillD = deferred();
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({ wordlists: [] });
  vi.spyOn(api, 'startFill').mockImplementation(() => startFillD.promise);
});
afterEach(() => {
  vi.restoreAllMocks();
});

const boot = async () => {
  const user = userEvent.setup();
  const view = renderApp();
  await waitFor(() => expect(cells(view.container)).toHaveLength(225));
  await waitFor(() =>
    expect(screen.getByText('Verify words').closest('button')).not.toBeDisabled()
  );
  return { user, ...view };
};

const startAutofill = async (user) => {
  await user.click(screen.getByRole('button', { name: /^autofill$/i }));
  await user.click(await screen.findByRole('button', { name: /start autofill/i }));
  await waitFor(() => expect(screen.getByText(STATUS)).toBeInTheDocument());
  expect(api.startFill).toHaveBeenCalledTimes(1);
};

const focusCell = async (user, container, i) => {
  await user.click(cells(container)[i]);
};

describe('App D1 gate: keyboard and pointer writers', () => {
  it('control (no run live): a letter, Space, Ctrl+L and Shift+click each write', async () => {
    const { user, container } = await boot();
    expect(screen.queryByText(STATUS)).not.toBeInTheDocument();

    await focusCell(user, container, 0);
    await user.keyboard('B');
    expect(letters(container)).toEqual(['B']);

    await focusCell(user, container, 20);
    await user.keyboard('{Control>}l{/Control}');
    expect(lockCount(container)).toBe(1);

    expect(blackCount(container)).toBe(0);
    await focusCell(user, container, 40);
    await user.keyboard(' ');
    const afterSpace = blackCount(container);
    expect(afterSpace).toBeGreaterThan(0);

    fireEvent.click(cells(container)[100], { shiftKey: true });
    expect(blackCount(container)).toBeGreaterThan(afterSpace);
  });

  it('submitting: status shown, a typed letter writes nothing', async () => {
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    await user.keyboard('B');
    expect(letters(container)).toEqual(['B']);

    await startAutofill(user);
    expect(container.querySelector('.xw-grid-wrap [role="status"]').textContent).toBe(STATUS);

    await focusCell(user, container, 5);
    await user.keyboard('C');
    expect(letters(container)).toEqual(['B']);
  });

  it('submitting: Ctrl+L, Space and Shift+click leave the grid unchanged', async () => {
    const { user, container } = await boot();
    await startAutofill(user);

    await focusCell(user, container, 20);
    await user.keyboard('{Control>}l{/Control}');
    await user.keyboard(' ');
    await user.keyboard('.');
    fireEvent.click(cells(container)[100], { shiftKey: true });
    fireEvent.click(cells(container)[101], { altKey: true });
    fireEvent.contextMenu(cells(container)[102]);
    expect(blackCount(container)).toBe(0);
    expect(lockCount(container)).toBe(0);
    expect(letters(container)).toEqual([]);
  });

  it('terminal state (startFill rejects): status gone and typing writes again', async () => {
    const { user, container } = await boot();
    await startAutofill(user);

    await act(async () => {
      startFillD.reject(Object.assign(new Error('boom'), { code: 'X' }));
    });
    await waitFor(() => expect(screen.queryByText(STATUS)).not.toBeInTheDocument());

    await focusCell(user, container, 0);
    await user.keyboard('D');
    expect(letters(container)).toEqual(['D']);
  });
});

describe('App D1 gate: async Verify and Clean', () => {
  const invalid = {
    invalid_words: [{ word: 'BA', cells: [[0, 0], [0, 1]], status: 'invalid' }],
    invalid_count: 1,
    total_checked: 1,
    wordlist_size: 10,
  };

  it('control: with no run live, Verify paints the underline and toasts', async () => {
    const d = deferred();
    vi.spyOn(api, 'verifyWords').mockImplementation(() => d.promise);
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    await user.keyboard('BA');

    await user.click(screen.getByText('Verify words'));
    expect(api.verifyWords).toHaveBeenCalledTimes(1);
    await act(async () => d.resolve(invalid));
    await waitFor(() => expect(underlines(container)).toBe(2));
    expect(screen.getByText(/words flagged/)).toBeInTheDocument();
  });

  it('Verify resolving after Start: no cell gains isError, no result toast', async () => {
    const d = deferred();
    vi.spyOn(api, 'verifyWords').mockImplementation(() => d.promise);
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    await user.keyboard('BA');

    await user.click(screen.getByText('Verify words'));
    expect(api.verifyWords).toHaveBeenCalledTimes(1);
    await startAutofill(user);
    expect(screen.getByText('Verify words').closest('button')).toBeDisabled();

    await act(async () => d.resolve(invalid));
    await flush();
    expect(underlines(container)).toBe(0);
    expect(screen.queryByText(/words flagged/)).not.toBeInTheDocument();
    expect(screen.queryByText(/words valid/)).not.toBeInTheDocument();
  });

  const cleaned = () => ({
    grid: Array.from({ length: 15 }, () => Array(15).fill('.')),
    removed_count: 1,
    valid_count: 0,
    cleared_cells: [[0, 0]],
    message: 'Removed 1 invalid word',
  });

  it('control: with no run live, Clean asks, then removes the letter and toasts', async () => {
    const d = deferred();
    vi.spyOn(api, 'cleanGrid').mockImplementation(() => d.promise);
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    await user.keyboard('B');
    expect(letters(container)).toEqual(['B']);

    await user.click(screen.getByText('Clean grid'));
    expect(api.cleanGrid).toHaveBeenCalledTimes(1);
    await act(async () => d.resolve(cleaned()));
    // novice-readiness spec 0.2.7 §3.5 (G5): Clean asks before it blanks; accepting writes.
    await user.click(await screen.findByRole('button', { name: 'Clean' }));
    await waitFor(() => expect(letters(container)).toEqual([]));
    expect(screen.getByText('Removed 1 invalid word')).toBeInTheDocument();
  });

  it('Clean resolving after Start (removed_count 1): no letter removed, no toast', async () => {
    const d = deferred();
    vi.spyOn(api, 'cleanGrid').mockImplementation(() => d.promise);
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    await user.keyboard('B');

    await user.click(screen.getByText('Clean grid'));
    expect(api.cleanGrid).toHaveBeenCalledTimes(1);
    await startAutofill(user);
    expect(screen.getByText('Clean grid').closest('button')).toBeDisabled();

    await act(async () => d.resolve(cleaned()));
    await flush();
    expect(letters(container)).toEqual(['B']);
    expect(screen.queryByText('Removed 1 invalid word')).not.toBeInTheDocument();
  });

  // The N === 0 path writes clearAllErrors and toasts directly, so only the post-await D1
  // check stops it (the removed_count 1 row above is also stopped by the dismissal effect).
  it('Clean resolving after Start with nothing to remove: red cells stay red, no toast', async () => {
    const verifyD = deferred();
    vi.spyOn(api, 'verifyWords').mockImplementation(() => verifyD.promise);
    const d = deferred();
    vi.spyOn(api, 'cleanGrid').mockImplementation(() => d.promise);
    const { user, container } = await boot();
    await act(async () => {
      await focusCell(user, container, 0);
      await user.keyboard('BA');
    });
    await act(async () => {
      await user.click(screen.getByText('Verify words'));
    });
    await act(async () => verifyD.resolve(invalid));
    await waitFor(() => expect(underlines(container)).toBe(2));

    await act(async () => {
      await user.click(screen.getByText('Clean grid'));
    });
    expect(api.cleanGrid).toHaveBeenCalledTimes(1);
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /^autofill$/i }));
    });
    const startBtn = await screen.findByRole('button', { name: /start autofill/i });
    await act(async () => {
      await user.click(startBtn);
    });
    await waitFor(() => expect(screen.getByText(STATUS)).toBeInTheDocument());
    expect(underlines(container)).toBe(2);

    const keepsBA = Array.from({ length: 15 }, (_, r) =>
      Array.from({ length: 15 }, (_, c) => ({
        letter: r === 0 ? 'BA'[c] || '' : '',
        isBlack: false,
      }))
    );
    await act(async () =>
      d.resolve({ grid: keepsBA, removed_count: 0, valid_count: 1, cleared_cells: 0, message: 'x' })
    );
    await flush();
    expect(underlines(container)).toBe(2);
    expect(screen.queryByText(/Grid is clean/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Nothing removed/)).not.toBeInTheDocument();
  });

  it('Verify and Clean make no request when a run is already live (pre-request return)', async () => {
    vi.spyOn(api, 'verifyWords').mockResolvedValue(invalid);
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleaned());
    const { user } = await boot();
    await startAutofill(user);
    // The buttons are disabled, so the pre-request return is reachable only through the
    // handlers themselves, captured from the TopBar props.
    await act(async () => {
      await captured.topbar.onVerify();
      await captured.topbar.onClean();
    });
    expect(api.verifyWords).not.toHaveBeenCalled();
    expect(api.cleanGrid).not.toHaveBeenCalled();
  });
});

describe('App D1 gate: handlers called directly while a run is live', () => {
  const call = (fn, ...args) => act(async () => { fn(...args); });

  it('control: with no run live, the direct calls write', async () => {
    const { user, container } = await boot();
    await call(captured.grid.onSetLetter, 0, 0, 'Z');
    expect(letters(container)).toEqual(['Z']);
    await call(captured.grid.onToggleLock, 3, 3);
    expect(lockCount(container)).toBe(1);
    await call(captured.grid.onToggleBlack, 6, 6);
    expect(blackCount(container)).toBeGreaterThan(0);
    void user;
  });

  it('setLetter, toggleBlackSquare and toggleThemeLock return before any state change', async () => {
    const { user, container } = await boot();
    await startAutofill(user);
    await call(captured.grid.onSetLetter, 0, 0, 'Z');
    await call(captured.grid.onToggleLock, 3, 3);
    await call(captured.grid.onToggleBlack, 6, 6);
    expect(letters(container)).toEqual([]);
    expect(lockCount(container)).toBe(0);
    expect(blackCount(container)).toBe(0);
  });

  it('handlePatternSelect writes nothing while live and writes when not (control)', async () => {
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    await user.click(screen.getByRole('button', { name: /^search$/i }));
    await waitFor(() => expect(captured.pattern).toBeDefined());
    await call(captured.pattern.onSelectWord, 'CAT');
    expect(letters(container)).toEqual(['C', 'A', 'T']);

    await startAutofill(user);
    await user.click(screen.getByRole('button', { name: /^search$/i }));
    await focusCell(user, container, 30);
    await waitFor(() => expect(captured.pattern).toBeDefined());
    await call(captured.pattern.onSelectWord, 'DOG');
    expect(letters(container)).toEqual(['C', 'A', 'T']);
  });

  it('handleThemeWordApplied writes nothing and toasts nothing while live', async () => {
    const { user, container } = await boot();
    const filled = () => {
      const g = captured.grid.grid.map((row) => row.map((c) => ({ ...c })));
      g[2][0] = { ...g[2][0], letter: 'Q', isThemeLocked: true };
      return g;
    };
    await user.click(screen.getByRole('button', { name: /^theme$/i }));
    // Task 6.16: the callback takes the sent grid and the docId the request was sent under.
    const ctx = () => ({ sentGrid: captured.grid.grid, docId: captured.theme.docId });
    let returned;
    await act(async () => {
      returned = captured.theme.onApplyPlacement(filled(), { word: 'QUX' }, ctx());
    });
    expect(returned).toBe(true);
    expect(letters(container)).toEqual(['Q']);
    expect(screen.getByText('Applied "QUX" to grid!')).toBeInTheDocument();

    await startAutofill(user);
    const g2 = captured.grid.grid.map((row) => row.map((c) => ({ ...c })));
    g2[4][0] = { ...g2[4][0], letter: 'W', isThemeLocked: true };
    await act(async () => {
      returned = captured.theme.onApplyPlacement(g2, { word: 'WEE' }, ctx());
    });
    expect(returned).toBe(false);
    expect(letters(container)).toEqual(['Q']);
    expect(screen.queryByText('Applied "WEE" to grid!')).not.toBeInTheDocument();
  });

  it('handleGridImport changes nothing while live (size, grid, symmetry)', async () => {
    const { user, container } = await boot();
    await startAutofill(user);
    const imported = Array.from({ length: 5 }, () =>
      Array.from({ length: 5 }, () => ({ letter: 'X', isBlack: false }))
    );
    await user.click(screen.getByRole('button', { name: /^import$/i }));
    await call(captured.importPanel.onImport, { grid: imported, size: 5 });
    expect(cells(container)).toHaveLength(225);
    expect(letters(container)).toEqual([]);
  });
});

describe('App D1 gate: Import Grid button', () => {
  const pasteAndValidate = async (user) => {
    await user.click(screen.getByRole('button', { name: /^import$/i }));
    await user.click(screen.getByRole('button', { name: /paste json/i }));
    const grid = Array.from({ length: 5 }, () => Array(5).fill('.'));
    grid[0][0] = 'C';
    fireEvent.change(screen.getByLabelText(/paste json data/i), {
      target: { value: JSON.stringify({ size: 5, grid }) },
    });
    await user.click(screen.getByRole('button', { name: /validate json/i }));
    return screen.findByRole('button', { name: /import grid/i });
  };

  it('control: with no run live the Import Grid button is enabled', async () => {
    const { user } = await boot();
    const btn = await pasteAndValidate(user);
    expect(btn).not.toBeDisabled();
  });

  it('submitting: Import Grid is disabled and the grid is unchanged', async () => {
    const { user, container } = await boot();
    await startAutofill(user);
    const btn = await pasteAndValidate(user);
    expect(btn).toBeDisabled();
    await user.click(btn);
    await flush();
    expect(cells(container)).toHaveLength(225);
    expect(letters(container)).toEqual([]);
  });
});
