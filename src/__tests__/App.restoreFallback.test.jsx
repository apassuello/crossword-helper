/**
 * #84: restore adopts the newest entry that can be adopted, not just the newest. Real App and
 * real storage over the setup file's localStorage mock; `storage.load` is not spied.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';
import { SAVE_KEY } from '../lib/storage';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const renderApp = () => render(<App />, { wrapper: ToastProvider });
const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const letters = (c) => Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);
const focusEl = (c) => c.querySelector('.xw-grid-focus');
const S0 = '2026-10-22T09:30:00.000Z';
const cellsOf = (size, edits = {}) =>
  Array.from({ length: size }, (_, r) =>
    Array.from({ length: size }, (_, c) => ({
      letter: '', isBlack: false, isThemeLocked: false, number: null, isError: false,
      isAutofilled: false, ...(edits[`${r},${c}`] || {}),
    }))
  );
const entryOf = (id, name, edits = {}) => ({
  id, name, savedAt: S0, size: 15, grid: cellsOf(15, edits), numbering: {}, symmetryEnabled: true,
});
const badEntry = () => ({ id: 'bad', name: 'Broken', grid: null, size: 15, savedAt: S0 });
const advance = (ms) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });

let store;
const stored = () => JSON.parse(store.get(SAVE_KEY) ?? '[]');

beforeEach(() => {
  store = new Map();
  global.localStorage.getItem.mockImplementation((k) => (store.has(k) ? store.get(k) : null));
  global.localStorage.setItem.mockImplementation((k, v) => { store.set(k, String(v)); });
  global.localStorage.removeItem.mockImplementation((k) => { store.delete(k); });
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({ wordlists: [{ key: 'comprehensive', name: 'Comprehensive' }] });
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('restore when the newest saved entry cannot be adopted (#84)', () => {
  it('restores the next adoptable entry, with its banner, letter and document id', async () => {
    store.set(SAVE_KEY, JSON.stringify([badEntry(), entryOf('good', 'Older', { '1,1': { letter: 'F' } })]));
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    const { container } = renderApp();
    await screen.findByText(/Restored "Older"/);
    expect(letters(container)).toEqual(['F']);

    // docId is 'good': the next edit autosaves in place rather than forking a new entry
    await user.click(cells(container)[3 * 15 + 3]);
    fireEvent.keyDown(focusEl(container), { key: 'A' });
    await advance(30000);
    await waitFor(() => expect(stored().find((e) => e.id === 'good')?.grid[3][3].letter).toBe('A'));
    expect(stored().map((e) => e.id).sort()).toEqual(['bad', 'good']);
  });

  it('regression pin (passes before the fix): when no entry is adoptable there is no banner and the grid stays blank', async () => {
    store.set(SAVE_KEY, JSON.stringify([badEntry()]));
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await advance(100);
    expect(screen.queryByText(/Restored/)).toBeNull();
    expect(letters(container)).toEqual([]);

    // a minted document id: the first edit's autosave creates a new entry, never writes into 'bad'
    await user.click(cells(container)[3 * 15 + 3]);
    fireEvent.keyDown(focusEl(container), { key: 'A' });
    await advance(30000);
    await waitFor(() => expect(stored()).toHaveLength(2));
    expect(stored().find((e) => e.id === 'bad').grid).toBeNull();
  });
});
