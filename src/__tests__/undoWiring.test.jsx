/**
 * U.2 (novice-readiness spec 0.2.11 section 3.9): every user edit is one undo step, wired at the
 * App handlers. There is no Undo control until U.3, so a wrapper around `useUndoHistory` exposes
 * the hook's return value (`captured.h`), and the child components are wrapped only to capture
 * the handler props App hands them, as App.gate.test.jsx does.
 *
 * Tests that call `captured.h` need the new `hooks/useUndoHistory` module, so before the
 * implementation they fail at that import, not at their own assertion.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';
import storage from '../lib/storage';
import { makeGrid, toSavedGrid } from '../api/gridCodec';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const captured = vi.hoisted(() => ({}));

vi.mock('../hooks/useUndoHistory', async () => {
  const actual = await vi.importActual('../hooks/useUndoHistory');
  return {
    ...actual,
    useUndoHistory: (...args) => {
      const h = actual.useUndoHistory(...args);
      captured.h = h;
      return h;
    },
  };
});

// vi.mock is hoisted and needs literal factories, so each wrapper is spelled out.
vi.mock('../components/bench/CrosswordGrid', async () => {
  const actual = await vi.importActual('../components/bench/CrosswordGrid');
  const R = await import('react');
  const W = (props) => {
    if (props) captured.grid = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: W };
});
vi.mock('../components/PatternMatcher', async () => {
  const actual = await vi.importActual('../components/PatternMatcher');
  const R = await import('react');
  const W = (props) => {
    if (props) captured.pattern = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: W };
});
vi.mock('../components/ThemeWordsPanel', async () => {
  const actual = await vi.importActual('../components/ThemeWordsPanel');
  const R = await import('react');
  const W = (props) => {
    if (props) captured.theme = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: W };
});
vi.mock('../components/ImportPanel', async () => {
  const actual = await vi.importActual('../components/ImportPanel');
  const R = await import('react');
  const W = (props) => {
    if (props) captured.importPanel = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: W };
});
vi.mock('../components/bench/GridPanel', async () => {
  const actual = await vi.importActual('../components/bench/GridPanel');
  const R = await import('react');
  const W = (props) => {
    if (props) captured.gridPanel = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: W };
});

const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const blacks = (c) => c.querySelectorAll('rect[fill="var(--ink)"]').length;
const locks = (c) => c.querySelectorAll('path[fill="var(--accent)"]').length;
const underlines = (c) => c.querySelectorAll('line[stroke="var(--danger)"]').length;
const letters = (c) => Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);
const focusEl = (c) => c.querySelector('.xw-grid-focus');
const blankCli = () => Array.from({ length: 15 }, () => Array(15).fill('.'));
const flush = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });
const deferred = () => {
  let resolve;
  const promise = new Promise((res) => { resolve = res; });
  return { promise, resolve };
};

let handlers;
beforeEach(() => {
  global.localStorage.getItem.mockReturnValue(null);
  for (const k of Object.keys(captured)) delete captured[k];
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({ wordlists: [{ key: 'comprehensive', name: 'Comprehensive' }] });
  vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't1', ceiling_seconds: 300 });
  vi.spyOn(api, 'openProgress').mockImplementation((id, h) => { handlers = h; return { close() {} }; });
  vi.spyOn(storage, 'load').mockResolvedValue(null);
  vi.spyOn(storage, 'list').mockResolvedValue([]);
  vi.spyOn(storage, 'save').mockResolvedValue({ savedAt: 'x', id: 'x', name: 'n', forked: false });
});
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitFor(() => expect(cells(view.container)).toHaveLength(225));
  await waitFor(() => expect(screen.getByText('Verify words').closest('button')).not.toBeDisabled());
  return { user, ...view };
};
const focusCell = (user, container, i) => user.click(cells(container)[i]);
const type = (container, key) => fireEvent.keyDown(focusEl(container), { key });
const undo = () => act(() => captured.h.undo());
const redo = () => act(() => captured.h.redo());

const replyWith = (grid, word, row) =>
  grid.map((r, ri) =>
    r.map((cell, ci) =>
      ri === row && ci < word.length ? { ...cell, letter: word[ci], isThemeLocked: true } : cell
    )
  );

describe('one step per user action', () => {
  it('typing a letter is one step; Backspace is another; undo and redo walk them', async () => {
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    type(container, 'A'); // focus advances to the next cell
    await focusCell(user, container, 0);
    type(container, 'Backspace');
    expect(letters(container)).toEqual([]);
    undo();
    expect(letters(container)).toEqual(['A']);
    undo();
    expect(letters(container)).toEqual([]);
    expect(captured.h.canUndo).toBe(false);
    redo();
    expect(letters(container)).toEqual(['A']);
  });

  it('retyping the same letter over a typed letter adds no step', async () => {
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    type(container, 'A');
    await focusCell(user, container, 0);
    type(container, 'A');
    undo();
    expect(letters(container)).toEqual([]);
    expect(captured.h.canUndo).toBe(false);
  });

  it('a black-square toggle and its mirror are one step', async () => {
    const { container } = await boot();
    act(() => captured.grid.onToggleBlack(0, 0));
    expect(blacks(container)).toBe(2);
    undo();
    expect(blacks(container)).toBe(0);
    expect(captured.h.canUndo).toBe(false);
  });

  it('a theme-lock toggle is one step', async () => {
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    type(container, 'A');
    act(() => captured.grid.onToggleLock(0, 0));
    expect(locks(container)).toBe(1);
    undo();
    expect(locks(container)).toBe(0);
    expect(letters(container)).toEqual(['A']);
  });

  it('placing a Search result is one step', async () => {
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    await user.click(screen.getByRole('button', { name: /^search$/i }));
    await waitFor(() => expect(captured.pattern).toBeTruthy());
    act(() => captured.pattern.onSelectWord('CAT'));
    expect(letters(container)).toEqual(['C', 'A', 'T']);
    undo();
    expect(letters(container)).toEqual([]);
    expect(captured.h.canUndo).toBe(false);
  });

  it('accepting Clean is one step', async () => {
    vi.spyOn(api, 'cleanGrid').mockResolvedValue({
      grid: blankCli(), removed_count: 1, valid_count: 0, cleared_cells: [[0, 0]], message: 'Removed 1',
    });
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    type(container, 'B');
    await user.click(screen.getByText('Clean grid'));
    await user.click(await screen.findByRole('button', { name: 'Clean' }));
    await waitFor(() => expect(letters(container)).toEqual([]));
    undo();
    expect(letters(container)).toEqual(['B']);
  });
});

describe('Apply This Placement and Apply All', () => {
  const openTheme = async (user) => {
    const view = await boot();
    await view.user.click(screen.getByRole('button', { name: /^Theme$/ }));
    await waitFor(() => expect(captured.theme).toBeTruthy());
    return view;
  };

  it('Apply This Placement is one step', async () => {
    const { user, container } = await openTheme();
    const { grid, docId, onApplyPlacement } = captured.theme;
    await act(async () => {
      onApplyPlacement(replyWith(grid, 'CAT', 0), { word: 'CAT' }, { sentGrid: grid, docId });
    });
    expect(letters(container)).toEqual(['C', 'A', 'T']);
    undo();
    expect(letters(container)).toEqual([]);
    expect(captured.h.canUndo).toBe(false);
  });

  it('Apply All of three words is one step', async () => {
    const { container } = await openTheme();
    const { grid, docId } = captured.theme;
    const words = ['CAT', 'DOG', 'EMU'];
    let token;
    await act(async () => {
      token = captured.theme.onBatchBegin();
    });
    let sent = grid;
    for (let i = 0; i < 3; i++) {
      const reply = replyWith(sent, words[i], i * 2);
      await act(async () => {
        captured.theme.onApplyPlacement(reply, { word: words[i] }, { sentGrid: sent, docId });
      });
      sent = reply;
    }
    await act(async () => {
      captured.theme.onBatchEnd(token);
    });
    expect(letters(container)).toEqual(['C', 'A', 'T', 'D', 'O', 'G', 'E', 'M', 'U']);
    undo();
    expect(letters(container)).toEqual([]);
    expect(captured.h.canUndo).toBe(false);
    redo();
    expect(letters(container)).toHaveLength(9);
  });

  it('a batch that ends early (a dropped reply) still closes, and records what it did apply', async () => {
    const { container } = await openTheme();
    const { grid, docId } = captured.theme;
    let token;
    await act(async () => {
      token = captured.theme.onBatchBegin();
    });
    await act(async () => {
      captured.theme.onApplyPlacement(replyWith(grid, 'CAT', 0), { word: 'CAT' }, { sentGrid: grid, docId });
    });
    await act(async () => captured.theme.onBatchEnd(token));
    expect(captured.h.canUndo).toBe(true);
    undo();
    expect(letters(container)).toEqual([]);
  });

  it('a batch whose every reply was dropped records no step', async () => {
    await openTheme();
    const { grid } = captured.theme;
    let token;
    await act(async () => {
      token = captured.theme.onBatchBegin();
    });
    await act(async () => {
      captured.theme.onApplyPlacement(replyWith(grid, 'CAT', 0), { word: 'CAT' }, { sentGrid: grid, docId: 'another-doc' });
    });
    await act(async () => captured.theme.onBatchEnd(token));
    expect(captured.h.canUndo).toBe(false);
  });

  it('during a batch a user edit is folded into it and Undo does nothing', async () => {
    const { user, container } = await openTheme();
    const { grid, docId } = captured.theme;
    let token;
    await act(async () => {
      token = captured.theme.onBatchBegin();
    });
    await act(async () => {
      captured.theme.onApplyPlacement(replyWith(grid, 'CAT', 0), { word: 'CAT' }, { sentGrid: grid, docId });
    });
    await focusCell(user, container, 5 * 15);
    type(container, 'Q');
    undo();
    expect(letters(container).sort()).toEqual(['A', 'C', 'Q', 'T']);
    await act(async () => captured.theme.onBatchEnd(token));
    undo();
    expect(letters(container)).toEqual([]);
    expect(captured.h.canUndo).toBe(false);
  });

  it('PR #90 Greptile P2: the Undo and Redo buttons are disabled while a batch is open, enabled after', async () => {
    const { user, container } = await openTheme();
    const { grid, docId } = captured.theme;
    await act(async () => {
      captured.theme.onApplyPlacement(replyWith(grid, 'CAT', 0), { word: 'CAT' }, { sentGrid: grid, docId });
    });
    const undoBtn = () => screen.getByText('Undo').closest('button');
    expect(undoBtn()).not.toBeDisabled();
    let token;
    await act(async () => {
      token = captured.theme.onBatchBegin();
    });
    expect(undoBtn()).toBeDisabled();
    expect(screen.getByText('Redo').closest('button')).toBeDisabled();
    await act(async () => captured.theme.onBatchEnd(token));
    expect(undoBtn()).not.toBeDisabled();
  });
});

describe('autofill commit points', () => {
  const startRun = async (user, container) => {
    await user.click(screen.getByRole('button', { name: /^autofill$/i }));
    await user.click(await screen.findByRole('button', { name: /start autofill/i }));
    await waitFor(() => expect(handlers).toBeTruthy());
  };

  it('a successful run is one step restoring the Start snapshot, merges and progress record nothing', async () => {
    const { user, container } = await boot();
    await focusCell(user, container, 3 * 15 + 3);
    type(container, 'A');
    await startRun(user, container);
    const g = blankCli(); g[3][3] = 'A'; g[0][0] = 'B';
    act(() => handlers.onEvent({ status: 'running', progress: 10, data: { grid: g } }));
    const final = g.map((r) => r.slice()); final[0][1] = 'C';
    act(() => handlers.onEvent({ status: 'complete', data: { success: true, grid: final, slots_filled: 3, total_slots: 3 } }));
    await waitFor(() => expect(screen.getByText('Successfully filled 3/3 slots!')).toBeInTheDocument());
    expect(letters(container).sort()).toEqual(['A', 'B', 'C']);
    undo();
    expect(letters(container)).toEqual(['A']); // the Start snapshot
    undo();
    expect(letters(container)).toEqual([]); // the typed A, the only other step
    expect(captured.h.canUndo).toBe(false);
  });

  it('a run whose outcome restores the Start snapshot records nothing', async () => {
    const { user, container } = await boot();
    await focusCell(user, container, 3 * 15 + 3);
    type(container, 'A');
    await startRun(user, container);
    const g = blankCli(); g[3][3] = 'A'; g[0][0] = 'B';
    act(() => handlers.onEvent({ status: 'running', progress: 10, data: { grid: g } }));
    act(() => handlers.onEvent({ status: 'error', message: 'boom' }));
    expect(screen.getByText('boom')).toBeInTheDocument();
    expect(letters(container)).toEqual(['A']);
    undo(); // the typed A is the only step
    expect(letters(container)).toEqual([]);
    expect(captured.h.canUndo).toBe(false);
  });

  it('Keep partial fill after a typed letter is one step whose snapshot is the grid as clicked', async () => {
    const { user, container } = await boot();
    await focusCell(user, container, 3 * 15 + 3);
    type(container, 'A');
    await startRun(user, container);
    const g = blankCli(); g[3][3] = 'A'; g[0][0] = 'B';
    act(() => handlers.onEvent({ status: 'complete', data: { success: false, grid: g, slots_filled: 1, total_slots: 2, fill_percentage: 50 } }));
    const keep = await screen.findByRole('button', { name: /keep partial fill/i });
    await focusCell(user, container, 10 * 15 + 10); // after the run: editing is live again
    type(container, 'Q');
    await user.click(keep);
    expect(letters(container).sort()).toEqual(['A', 'B', 'Q']);
    undo();
    expect(letters(container).sort()).toEqual(['A', 'Q']); // as clicked, not the Start snapshot
    undo();
    expect(letters(container).sort()).toEqual(['A']);
  });
});

describe('not recorded', () => {
  it('Verify marks are not a step', async () => {
    vi.spyOn(api, 'verifyWords').mockResolvedValue({
      invalid_words: [{ word: 'B', cells: [[0, 0]], status: 'invalid' }],
      invalid_count: 1, total_checked: 1, wordlist_size: 10,
    });
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    type(container, 'B');
    await user.click(screen.getByText('Verify words'));
    await waitFor(() => expect(underlines(container)).toBe(1));
    undo(); // the typed B is the only step
    expect(letters(container)).toEqual([]);
    expect(underlines(container)).toBe(0); // restore clears isError
    expect(captured.h.canUndo).toBe(false);
  });
});

describe('history ends with the document', () => {
  const typed = async () => {
    const view = await boot();
    await focusCell(view.user, view.container, 0);
    type(view.container, 'A');
    type(view.container, 'B');
    undo(); // one step on each stack
    expect(captured.h.canUndo).toBe(true);
    expect(captured.h.canRedo).toBe(true);
    return view;
  };

  it('New grid clears both stacks', async () => {
    const { container } = await typed();
    act(() => captured.gridPanel.onNewGrid(15));
    expect(letters(container)).toEqual([]);
    expect(captured.h.canUndo).toBe(false);
    expect(captured.h.canRedo).toBe(false);
  });

  it('New grid at another size clears both stacks', async () => {
    await typed();
    act(() => captured.gridPanel.onNewGrid(11));
    await waitFor(() => expect(captured.grid.grid).toHaveLength(11));
    expect(captured.h.canUndo).toBe(false);
    expect(captured.h.canRedo).toBe(false);
  });

  it('Import clears both stacks', async () => {
    const { user } = await typed();
    await user.click(screen.getByRole('button', { name: /^import$/i }));
    await waitFor(() => expect(captured.importPanel).toBeTruthy());
    act(() => captured.importPanel.onImport({ grid: makeGrid(15), size: 15 }));
    expect(captured.h.canUndo).toBe(false);
    expect(captured.h.canRedo).toBe(false);
  });

  it('Open saved clears both stacks', async () => {
    await typed();
    const grid = toSavedGrid(makeGrid(15));
    grid[0][0].letter = 'Z';
    const entry = { id: 'e1', name: 'n', size: 15, grid, savedAt: '2026-10-25T10:00:00.000Z' };
    act(() => captured.gridPanel.onOpenSaved(entry, captured.gridPanel.onOpenBegin()));
    await waitFor(() => expect(letters(document.body)).toContain('Z'));
    expect(captured.h.canUndo).toBe(false);
    expect(captured.h.canRedo).toBe(false);
  });

  it('a save fork keeps both stacks', async () => {
    storage.save.mockResolvedValue({ savedAt: '2026-10-25T10:00:00.000Z', id: 'forked-id', name: 'n', forked: true });
    const { user } = await typed();
    await user.click(screen.getByRole('button', { name: /save grid/i }));
    await screen.findByRole('textbox');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(storage.save).toHaveBeenCalled());
    await flush();
    expect(captured.h.canUndo).toBe(true);
  });
});

describe('gating, async responses and the saved state', () => {
  it('undo and redo do nothing while a run is live', async () => {
    vi.spyOn(api, 'startFill').mockImplementation(() => new Promise(() => {}));
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    type(container, 'A');
    undo();
    expect(letters(container)).toEqual([]);
    type(container, 'B');
    await user.click(screen.getByRole('button', { name: /^autofill$/i }));
    await user.click(await screen.findByRole('button', { name: /start autofill/i }));
    await waitFor(() => expect(screen.getByText('Editing is paused while autofill runs.')).toBeInTheDocument());
    undo();
    redo();
    expect(letters(container)).toEqual(['B']);
    expect(captured.h.canUndo).toBe(true);
  });

  it('undo while Verify is pending: the response lands on the current grid', async () => {
    const d = deferred();
    vi.spyOn(api, 'verifyWords').mockImplementation(() => d.promise);
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    await user.keyboard('BA');
    await user.click(screen.getByText('Verify words'));
    undo(); // removes the A
    expect(letters(container)).toEqual(['B']);
    await act(async () =>
      d.resolve({
        invalid_words: [{ word: 'B', cells: [[0, 0]], status: 'invalid' }],
        invalid_count: 1, total_checked: 1, wordlist_size: 10,
      })
    );
    await waitFor(() => expect(underlines(container)).toBe(1));
    expect(letters(container)).toEqual(['B']); // the undo was not reverted
    expect(captured.h.canRedo).toBe(true);
  });

  it('undo with a Clean confirm open dismisses the confirm', async () => {
    vi.spyOn(api, 'cleanGrid').mockResolvedValue({
      grid: blankCli(), removed_count: 1, valid_count: 0, cleared_cells: [[0, 0]], message: 'Removed 1',
    });
    const { user, container } = await boot();
    await focusCell(user, container, 0);
    type(container, 'B');
    await user.click(screen.getByText('Clean grid'));
    await screen.findByRole('button', { name: 'Clean' });
    undo();
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Clean' })).toBeNull());
    expect(letters(container)).toEqual([]);
  });

  it('undo back to the saved content shows the saved state and cancels the armed autosave', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const view = render(<App />, { wrapper: ToastProvider });
    await waitFor(() => expect(cells(view.container)).toHaveLength(225));
    await focusCell(user, view.container, 0);
    type(view.container, 'A');
    expect(screen.getByText('unsaved changes')).toBeInTheDocument();
    undo();
    expect(letters(view.container)).toEqual([]);
    expect(screen.queryByText('unsaved changes')).toBeNull();
    await act(async () => vi.advanceTimersByTime(60000));
    expect(storage.save).not.toHaveBeenCalled();
  });
});
