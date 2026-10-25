/**
 * novice-readiness spec 0.2.8 §3.4: deleting the open grid's own entry (Q1), leaving the
 * page (Q3), Open re-reading by id, and restore/Open validation (Greptile #77
 * GridPanel.jsx:88, App.jsx:264). Real App, GridPanel and save machine; storage is spied.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';
import storage from '../lib/storage';
import { saveArg, resolvingSave } from './saveArgs';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const renderApp = () => render(<App />, { wrapper: ToastProvider });
const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const letters = (c) => Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);
const focusEl = (c) => c.querySelector('.xw-grid-focus');
const blankCli = () => Array.from({ length: 15 }, () => Array(15).fill('.'));
const SAVED_AT = '2026-10-22T09:30:00.000Z';
const cellsOf = (size, edits = {}) =>
  Array.from({ length: size }, (_, r) =>
    Array.from({ length: size }, (_, c) => ({
      letter: '', isBlack: false, isThemeLocked: false, number: null, isError: false,
      isAutofilled: false, ...(edits[`${r},${c}`] || {}),
    }))
  );
const entryOf = (id, name, size = 15, edits = {}, over = {}) => ({
  id, name, savedAt: SAVED_AT, size, grid: cellsOf(size, edits), numbering: {},
  symmetryEnabled: true, ...over,
});
const advance = (ms) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });
const typeLetter = async (user, container, r, c, ch) => {
  await user.click(cells(container)[r * 15 + c]);
  fireEvent.keyDown(focusEl(container), { key: ch });
};
const pressOpenSaved = (user) =>
  act(async () => { await user.click(screen.getByRole('button', { name: 'Open saved' })); });
const rowOf = (name) => screen.getByText(name).closest('li');
const confirmDelete = (user) =>
  user.click(within(screen.getByRole('group', { name: /^Delete "/ })).getByRole('button', { name: 'Delete' }));
const pagehide = () => act(async () => { window.dispatchEvent(new Event('pagehide')); await Promise.resolve(); });

let handlers;
beforeEach(() => {
  global.localStorage.getItem.mockReturnValue(null);
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({ wordlists: [{ key: 'comprehensive', name: 'Comprehensive' }] });
  vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't1', ceiling_seconds: 300 });
  vi.spyOn(api, 'openProgress').mockImplementation((id, h) => { handlers = h; return { close() {} }; });
  vi.spyOn(storage, 'load').mockResolvedValue(null);
  vi.spyOn(storage, 'list').mockResolvedValue([]);
  vi.spyOn(storage, 'remove').mockResolvedValue(undefined);
  vi.spyOn(storage, 'save').mockImplementation((doc) =>
    Promise.resolve({ savedAt: new Date().toISOString(), id: saveArg([doc], 0).id, name: 'n', forked: false })
  );
  vi.spyOn(storage, 'saveSync').mockImplementation(() => ({ savedAt: new Date().toISOString() }));
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

describe('Delete the open grid\'s own entry (§3.4 Q1)', () => {
  const openG = async (user, container) => {
    storage.list.mockResolvedValue([entryOf('G', 'Gee', 15, { '1,1': { letter: 'F' } })]);
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await pressOpenSaved(user);
    await screen.findByText('Gee');
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Open' }));
    await waitFor(() => expect(letters(container)).toEqual(['F']));
  };
  const deleteG = async (user) => {
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Delete' }));
    await confirmDelete(user);
    await waitFor(() => expect(storage.remove).toHaveBeenCalledWith('G'));
  };

  it('label leaves "saved locally", nothing is saved within 30 s, a typed letter re-saves under G\'s id', async () => {
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await openG(user, container);
    await typeLetter(user, container, 3, 3, 'A');
    await advance(30000); // autosave: label is saved locally
    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/saved locally/)).toBeInTheDocument();
    storage.save.mockClear();

    storage.list.mockResolvedValue([]);
    await deleteG(user);
    expect(screen.queryByText(/saved locally/)).toBeNull();
    expect(screen.getByText('unsaved changes')).toBeInTheDocument();
    await advance(60000);
    expect(storage.save).not.toHaveBeenCalled();

    await typeLetter(user, container, 5, 5, 'B');
    await advance(30000);
    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(saveArg(storage.save.mock.calls[0], 0).id).toBe('G');
  });

  it('M2: a Symmetry toggle after deleting a dirty open grid arms nothing; the next letter does', async () => {
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await openG(user, container);
    await typeLetter(user, container, 3, 3, 'A'); // dirty, autosave not yet fired
    storage.list.mockResolvedValue([]);
    await deleteG(user);
    expect(screen.getByText('unsaved changes')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Symmetry' })); // a new `doc`, no grid edit
    await advance(90000);
    expect(storage.save).not.toHaveBeenCalled();

    await typeLetter(user, container, 5, 5, 'B');
    await advance(30000);
    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(saveArg(storage.save.mock.calls[0], 0).id).toBe('G');
  });

  it('deleting another entry leaves the open document\'s status alone', async () => {
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await openG(user, container);
    await typeLetter(user, container, 3, 3, 'A');
    await advance(30000);
    storage.list.mockResolvedValue([entryOf('G', 'Gee'), entryOf('H', 'Aitch')]);
    await pressOpenSaved(user);
    await screen.findByText('Aitch');
    await user.click(within(rowOf('Aitch')).getByRole('button', { name: 'Delete' }));
    await confirmDelete(user);
    await waitFor(() => expect(storage.remove).toHaveBeenCalledWith('H'));
    expect(screen.getByText(/saved locally/)).toBeInTheDocument();
  });

  it('a rejected remove is caught: no unhandled rejection, the list is refreshed', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await openG(user, container);
    storage.remove.mockRejectedValue(new Error('boom'));
    const unhandled = vi.fn();
    process.on('unhandledRejection', unhandled);
    const listCalls = storage.list.mock.calls.length;
    await deleteG(user);
    await waitFor(() => expect(storage.list.mock.calls.length).toBeGreaterThan(listCalls));
    await new Promise((r) => setTimeout(r, 20));
    process.off('unhandledRejection', unhandled);
    expect(unhandled).not.toHaveBeenCalled();
    expect(screen.queryByText('unsaved changes')).toBeNull();
  });
});

describe('Open re-reads the entry by id (§3.4 Q1, G#77 GridPanel.jsx:88)', () => {
  it('a list shown, the grid edited and autosaved, then its row opened: the newer letters are kept', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    const stale = entryOf('G', 'Gee', 15, { '1,1': { letter: 'F' } });
    storage.list.mockResolvedValue([stale]);
    await pressOpenSaved(user);
    await screen.findByText('Gee');
    // the entry is rewritten (the autosave of the same grid) after the list was shown
    storage.list.mockResolvedValue([entryOf('G', 'Gee', 15, { '1,1': { letter: 'F' }, '2,2': { letter: 'Z' } })]);
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Open' }));
    await waitFor(() => expect(letters(container).sort()).toEqual(['F', 'Z']));
  });

  it('an entry that has gone away shows the list refreshed and adopts nothing', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    storage.list.mockResolvedValue([entryOf('G', 'Gee', 15, { '1,1': { letter: 'F' } })]);
    await pressOpenSaved(user);
    await screen.findByText('Gee');
    storage.list.mockResolvedValue([]);
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Open' }));
    await waitFor(() => expect(screen.queryByText('Gee')).toBeNull());
    expect(letters(container)).toEqual([]);
  });
});

describe('Restore and Open validate the entry (§3.4, G#77 App.jsx:264)', () => {
  const BAD = [
    ['ragged rows', { grid: [[{}, {}], [{}]] }],
    ['a null cell', () => { const g = cellsOf(15); g[3][3] = null; return { grid: g }; }],
    ['a size above the import range', { size: 26, grid: cellsOf(26) }],
    ['a size below the import range', { size: 2, grid: cellsOf(2) }],
    ['a size that disagrees with the rows', { size: 15, grid: cellsOf(11) }],
    ['one row too many', () => ({ grid: [...cellsOf(15), cellsOf(15)[0]] })],
    ['one row one cell short', () => { const g = cellsOf(15); g[7] = g[7].slice(1); return { grid: g }; }],
    ['a non-object cell', () => { const g = cellsOf(15); g[0][0] = 'A'; return { grid: g }; }],
  ];
  const patch = (p) => (typeof p === 'function' ? p() : p);

  for (const [label, p] of BAD) {
    it(`restore: ${label} gives a blank grid, no banner, no throw`, async () => {
      const unhandled = vi.fn();
      process.on('unhandledRejection', unhandled);
      storage.load.mockResolvedValue(entryOf('B', 'Bad', 15, {}, patch(p)));
      const { container } = renderApp();
      await waitFor(() => expect(cells(container)).toHaveLength(225));
      await act(async () => { await new Promise((r) => setTimeout(r, 50)); });
      process.off('unhandledRejection', unhandled);
      expect(unhandled).not.toHaveBeenCalled();
      expect(cells(container)).toHaveLength(225);
      expect(letters(container)).toEqual([]);
      expect(screen.queryByText(/restored/i)).toBeNull();
    });

    it(`Open: ${label} adopts nothing and says Could not open this saved grid.`, async () => {
      const user = userEvent.setup();
      const { container } = renderApp();
      await waitFor(() => expect(cells(container)).toHaveLength(225));
      storage.list.mockResolvedValue([entryOf('B', 'Bad', 15, {}, patch(p))]);
      await pressOpenSaved(user);
      await screen.findByText('Bad');
      await user.click(within(rowOf('Bad')).getByRole('button', { name: 'Open' }));
      expect(await screen.findByText('Could not open this saved grid.')).toBeInTheDocument();
      expect(cells(container)).toHaveLength(225);
    });
  }

  // I2 (Phase 6R final review): the importer accepts every size 3..25, so a saved import of
  // any of them is a valid entry. Sizes other than 11/15/21 used to be unrestorable.
  for (const size of [3, 13, 21, 25]) {
    it(`restore: a saved ${size}x${size} import restores`, async () => {
      storage.load.mockResolvedValue(entryOf('I', 'Imported', size, { '1,1': { letter: 'F' } }));
      const { container } = renderApp();
      await waitFor(() => expect(cells(container)).toHaveLength(size * size));
      expect(letters(container)).toEqual(['F']);
    });
  }

  it('Open: a saved 13x13 import opens', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    storage.list.mockResolvedValue([entryOf('I', 'Imported', 13, { '1,1': { letter: 'F' } })]);
    await pressOpenSaved(user);
    await screen.findByText('Imported');
    await user.click(within(rowOf('Imported')).getByRole('button', { name: 'Open' }));
    await waitFor(() => expect(cells(container)).toHaveLength(169));
    expect(letters(container)).toEqual(['F']);
    expect(screen.queryByText('Could not open this saved grid.')).toBeNull();
  });

  it('a valid 11x11 entry still restores', async () => {
    storage.load.mockResolvedValue(entryOf('V', 'Valid', 11, { '1,1': { letter: 'F' } }));
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(121));
    expect(letters(container)).toEqual(['F']);
  });
});

describe('pagehide (§3.4 Q3)', () => {
  it('a clean document writes nothing', async () => {
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await pagehide();
    expect(storage.saveSync).not.toHaveBeenCalled();
  });

  it('a dirty document is saved at once', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 3, 3, 'A');
    expect(storage.saveSync).not.toHaveBeenCalled();
    await pagehide();
    expect(storage.saveSync).toHaveBeenCalledTimes(1);
    expect(storage.saveSync.mock.calls[0][0].grid[3][3].letter).toBe('A');
  });

  it('a live run, dirty: pagehide saves the Start snapshot, not the merged grid', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 3, 3, 'A');
    await user.click(screen.getByRole('button', { name: /^autofill$/i }));
    await user.click(await screen.findByRole('button', { name: /start autofill/i }));
    await waitFor(() => expect(handlers).toBeTruthy());
    const g = blankCli(); g[3][3] = 'A'; g[0][0] = 'B';
    act(() => handlers.onEvent({ status: 'running', progress: 10, data: { grid: g } }));
    expect(letters(container).sort()).toEqual(['A', 'B']);
    await pagehide();
    expect(storage.saveSync).toHaveBeenCalledTimes(1);
    const saved = storage.saveSync.mock.calls[0][0].grid;
    expect(saved[3][3].letter).toBe('A');
    expect(saved[0][0].letter).toBe('');
  });
});
