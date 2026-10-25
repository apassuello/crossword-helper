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

describe('N1: reopening the open document\'s own entry while its autosave waits for the lock', () => {
  it('Open reads behind the queued save: it shows what storage holds, the label leaves "saving", the next edit does not fork', async () => {
    store.set(SAVE_KEY, JSON.stringify([entryOf('G', 'Gee', { '1,1': { letter: 'F' } })]));
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    const { container } = renderApp();
    await waitFor(() => expect(letters(container)).toEqual(['F']));
    await typeLetter(user, container, 3, 3, 'A'); // dirty
    await advance(30000); // the autosave fires; its lock request is queued
    expect(pending).toHaveLength(1);

    await act(async () => { await user.click(screen.getByRole('button', { name: 'Open saved' })); });
    await screen.findByText('Gee');
    await act(async () => {
      await user.click(within(screen.getByText('Gee').closest('li')).getByRole('button', { name: 'Open' }));
    });
    // The grid has content, so Open asks first; confirming re-reads the entry.
    await act(async () => {
      await user.click(screen.getByRole('button', { name: 'Replace' }));
    });
    await act(async () => { await grant(); });
    await act(async () => { await grant(); });

    // (i) the grid shows the entry as storage holds it, (ii) the label left "saving…"
    expect(stored().map((e) => e.id)).toEqual(['G']);
    expect(letters(container).sort()).toEqual(['A', 'F']);
    expect(screen.queryByText('saving…')).toBeNull();
    expect(screen.queryByText('unsaved changes')).toBeNull();

    // (iii) + (iv) the tab's known savedAt is storage's: the next edit saves in place
    await typeLetter(user, container, 5, 5, 'B');
    await advance(30000);
    await act(async () => { await grant(); });
    expect(stored().map((e) => e.name)).toEqual(['Gee']);
    expect(letters(container).sort()).toEqual(['A', 'B', 'F']);
  });
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

// novice-readiness spec 0.2.10 §3.4 (An Open that waits): a confirmed Open behind a held lock is
// dropped only if New grid or import replaced the document since the confirm.
describe('An Open that waits for the lock', () => {
  const imported5 = () =>
    Array.from({ length: 5 }, () => Array.from({ length: 5 }, () => ({ letter: 'X', isBlack: false })));
  const setup = async (entries) => {
    store.set(SAVE_KEY, JSON.stringify(entries));
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    const view = renderApp();
    await waitFor(() => expect(letters(view.container).length).toBeGreaterThan(0));
    await act(async () => { await user.click(screen.getByRole('button', { name: 'Open saved' })); });
    return { user, ...view };
  };
  const confirmOpen = async (user, name) => {
    await screen.findByText(name);
    await act(async () => {
      await user.click(within(screen.getByText(name).closest('li')).getByRole('button', { name: 'Open' }));
    });
    await act(async () => { await user.click(screen.getByRole('button', { name: 'Replace' })); });
  };

  it('(i) an import since the confirm drops the Open', async () => {
    const { user, container } = await setup([entryOf('G', 'Gee', { '1,1': { letter: 'F' } })]);
    await confirmOpen(user, 'Gee');
    expect(pending).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: /^import$/i }));
    await act(async () => { captured.importPanel.onImport({ grid: imported5(), size: 5 }); });
    await act(async () => { await grant(); });
    expect(cells(container)).toHaveLength(25);
    expect(letters(container).every((l) => l === 'X')).toBe(true);
  });

  it('(ii) New grid since the confirm drops the Open', async () => {
    const { user, container } = await setup([entryOf('G', 'Gee', { '1,1': { letter: 'F' } })]);
    await confirmOpen(user, 'Gee');
    expect(pending).toHaveLength(1);
    await act(async () => { await user.click(screen.getByRole('button', { name: '11×11' })); });
    await act(async () => { await user.click(screen.getByRole('button', { name: 'Replace' })); });
    await act(async () => { await grant(); });
    expect(cells(container)).toHaveLength(121);
    expect(letters(container)).toEqual([]);
  });

  it('(iii) control: an Open of the own entry behind a queued autosave adopts', async () => {
    const { user, container } = await setup([entryOf('G', 'Gee', { '1,1': { letter: 'F' } })]);
    await typeLetter(user, container, 3, 3, 'A');
    await advance(30000);
    expect(pending).toHaveLength(1);
    await confirmOpen(user, 'Gee');
    await act(async () => { await grant(); });
    await act(async () => { await grant(); });
    expect(letters(container).sort()).toEqual(['A', 'F']);
  });

  it('(iv) control: Open A then Open B while the lock is held leaves B open', async () => {
    const { user, container } = await setup([
      entryOf('A', 'Aye', { '1,1': { letter: 'P' } }),
      entryOf('B', 'Bee', { '2,2': { letter: 'Q' } }),
    ]);
    await confirmOpen(user, 'Aye');
    await confirmOpen(user, 'Bee');
    expect(pending).toHaveLength(2);
    await act(async () => { await grant(); });
    expect(letters(container)).toEqual(['Q']);
  });

  it('(v) control: a save fork during the wait does not cancel the Open', async () => {
    const { user, container } = await setup([entryOf('G', 'Gee', { '1,1': { letter: 'F' } })]);
    await typeLetter(user, container, 3, 3, 'A');
    await advance(30000);
    expect(pending).toHaveLength(1);
    await confirmOpen(user, 'Gee');
    expect(pending).toHaveLength(2);
    // another tab saved G since this tab last knew it, so the queued save forks
    store.set(SAVE_KEY, JSON.stringify([{ ...entryOf('G', 'Gee', { '1,1': { letter: 'F' } }), savedAt: '2026-10-22T10:00:00.000Z' }]));
    await act(async () => { await grant(); });
    expect(stored().length).toBe(2); // the fork happened
    expect(letters(container)).toEqual(['F']);
  });
});
