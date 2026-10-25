/**
 * Phase 6R re-review N1 / N2: App-level rows for saves queued behind the Web Lock when the
 * document is replaced (Open saved of its own entry, import). Real App, GridPanel, save machine
 * AND real storage; `navigator.locks` is a stub whose grants the test fires by hand, so a
 * request stays queued until `grant()` and the order of grant vs render is the test's.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';
import storage, { SAVE_KEY } from '../lib/storage';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const captured = {};
vi.mock('../components/ImportPanel', async () => {
  const actual = await vi.importActual('../components/ImportPanel');
  const R = await import('react');
  const Wrapped = (props) => {
    if (props) captured.importPanel = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: Wrapped };
});

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
const typeLetter = async (user, container, r, c, ch) => {
  await user.click(cells(container)[r * 15 + c]);
  fireEvent.keyDown(focusEl(container), { key: ch });
};
const advance = (ms) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });
const settle = async () => { for (let i = 0; i < 6; i += 1) await Promise.resolve(); };

let store;
let pending;
const stored = () => JSON.parse(store.get(SAVE_KEY) ?? '[]');
// Grants every queued lock request in order, one at a time, with the promise reactions of each
// running before the next callback (Web Locks: a grant is a task, reactions are microtasks).
const grant = async () => {
  while (pending.length) {
    pending.shift()();
    await settle();
  }
};

beforeEach(() => {
  store = new Map();
  pending = [];
  global.localStorage.getItem.mockImplementation((k) => (store.has(k) ? store.get(k) : null));
  global.localStorage.setItem.mockImplementation((k, v) => { store.set(k, String(v)); });
  global.localStorage.removeItem.mockImplementation((k) => { store.delete(k); });
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: { request: (n, fn) => new Promise((resolve) => pending.push(() => resolve(fn()))) },
  });
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({ wordlists: [{ key: 'comprehensive', name: 'Comprehensive' }] });
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  delete navigator.locks;
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('N2: an import while a save of the old document waits for the lock', () => {
  it('a grant between the import\'s setters and its render leaves the imported grid clean', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await typeLetter(user, container, 3, 3, 'A');
    await advance(30000); // old document's autosave is queued
    expect(pending).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: /^import$/i }));

    const imported = Array.from({ length: 5 }, () =>
      Array.from({ length: 5 }, () => ({ letter: 'X', isBlack: false }))
    );
    // ImportPanel calls onImport from a timer, so React commits its setters in a later task.
    // Inside an async act the render is held until the scope ends, which is the order under
    // test: the grant, and the save's resolution, land before the import's render.
    await act(async () => {
      captured.importPanel.onImport({ grid: imported, size: 5 });
      expect(cells(container)).toHaveLength(225); // not rendered yet
      await grant();
    });

    expect(cells(container)).toHaveLength(25);
    expect(screen.queryByText('unsaved changes')).toBeNull();
    expect(screen.queryByText(/saved locally/)).toBeNull();
  });
});
