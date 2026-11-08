/**
 * #102: Verify words and Clean grid check against the word lists ticked in Autofill, and the
 * selection outlives the Autofill panel. Real App and real AutofillPanel; the API client is spied.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const DEFAULT = ['comprehensive'];
const WITH_DEMO = ['comprehensive', 'custom/demo_words'];

let store;
let verifySpy;
let cleanSpy;

beforeEach(() => {
  store = new Map();
  global.localStorage.getItem.mockImplementation((k) => (store.has(k) ? store.get(k) : null));
  global.localStorage.setItem.mockImplementation((k, v) => { store.set(k, String(v)); });
  global.localStorage.removeItem.mockImplementation((k) => { store.delete(k); });
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({
    wordlists: [
      { key: 'comprehensive', name: 'Comprehensive Dictionary', category: 'core' },
      { key: 'custom/demo_words', name: 'Demo Words', category: 'custom' },
    ],
  });
  verifySpy = vi.spyOn(api, 'verifyWords').mockResolvedValue({ results: [], invalid_words: [], all_valid: true });
  cleanSpy = vi.spyOn(api, 'cleanGrid').mockImplementation(async ({ grid }) => ({
    grid, removed_count: 0, message: 'Nothing to clean',
  }));
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  vi.restoreAllMocks();
});

async function setup() {
  const user = userEvent.setup();
  const { container } = render(<App />, { wrapper: ToastProvider });
  await waitFor(() => expect(cells(container)).toHaveLength(225));
  await waitFor(() => expect(screen.getByRole('button', { name: /verify words/i })).toBeEnabled());
  await waitFor(() => expect(screen.getByRole('button', { name: /clean grid/i })).toBeEnabled());
  return user;
}
const openTool = (user, name) => user.click(screen.getByRole('button', { name: new RegExp(`^${name}$`) }));
const verify = (user) => user.click(screen.getByRole('button', { name: /verify words/i }));
const clean = (user) => user.click(screen.getByRole('button', { name: /clean grid/i }));
const tick = async (user, label) => user.click(await screen.findByLabelText(label));

describe('Verify and Clean use the word lists ticked in Autofill (#102)', () => {
  it('Verify sends the lists ticked in Autofill', async () => {
    const user = await setup();
    await openTool(user, 'Autofill');
    await tick(user, 'Demo Words');
    await verify(user);
    await waitFor(() => expect(verifySpy).toHaveBeenCalledTimes(1));
    expect(verifySpy.mock.calls[0][0].wordlists).toEqual(WITH_DEMO);
  });

  it('Clean sends the lists ticked in Autofill', async () => {
    const user = await setup();
    await openTool(user, 'Autofill');
    await tick(user, 'Demo Words');
    await clean(user);
    await waitFor(() => expect(cleanSpy).toHaveBeenCalledTimes(1));
    expect(cleanSpy.mock.calls[0][0].wordlists).toEqual(WITH_DEMO);
  });

  it('the selection survives closing the Autofill tool: Verify still sends it and the box is still ticked on reopen', async () => {
    const user = await setup();
    await openTool(user, 'Autofill');
    await tick(user, 'Demo Words');
    await openTool(user, 'Search');
    await verify(user);
    await waitFor(() => expect(verifySpy).toHaveBeenCalledTimes(1));
    expect(verifySpy.mock.calls[0][0].wordlists).toEqual(WITH_DEMO);
    await openTool(user, 'Autofill');
    expect(await screen.findByLabelText('Demo Words')).toBeChecked();
  });

  it('regression pin (passes before the fix): with no Autofill interaction both send the default list', async () => {
    const user = await setup();
    await verify(user);
    await clean(user);
    await waitFor(() => expect(cleanSpy).toHaveBeenCalledTimes(1));
    expect(verifySpy.mock.calls[0][0].wordlists).toEqual(DEFAULT);
    expect(cleanSpy.mock.calls[0][0].wordlists).toEqual(DEFAULT);
  });

  it('regression pin (passes before the fix): with nothing ticked both fall back to the default list, never []', async () => {
    const user = await setup();
    await openTool(user, 'Autofill');
    await user.click(await screen.findByLabelText('Comprehensive Dictionary'));
    expect(screen.getByLabelText('Comprehensive Dictionary')).not.toBeChecked();
    await verify(user);
    await clean(user);
    await waitFor(() => expect(cleanSpy).toHaveBeenCalledTimes(1));
    expect(verifySpy.mock.calls[0][0].wordlists).toEqual(DEFAULT);
    expect(cleanSpy.mock.calls[0][0].wordlists).toEqual(DEFAULT);
  });
});

describe('a word-list change cancels what an earlier Verify or Clean would have applied (#102)', () => {
  const idx = (r, c) => r * 15 + c;
  const focusEl = (c) => c.querySelector('.xw-grid-focus');
  const letters = (c) => Array.from(c.querySelectorAll('text.xw-cell-letter')).map((t) => t.textContent);
  const flaggedLetters = (c) =>
    Array.from(c.querySelectorAll('text.xw-cell-letter')).filter((t) => t.getAttribute('fill') === 'var(--danger)');
  const deferred = () => {
    let resolve;
    const promise = new Promise((res) => { resolve = res; });
    return { promise, resolve };
  };
  const typeAt = async (user, container, r, c, ch) => {
    await act(async () => { await user.click(cells(container)[idx(r, c)]); });
    fireEvent.keyDown(focusEl(container), { key: ch });
  };
  const typeCat = async (user, container) => {
    await typeAt(user, container, 0, 0, 'c');
    await typeAt(user, container, 0, 1, 'a');
    await typeAt(user, container, 0, 2, 't');
  };
  // setup() does not hand back the container, so the typed-grid fixture boots its own render.
  async function boot() {
    const user = userEvent.setup();
    const { container } = render(<App />, { wrapper: ToastProvider });
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await waitFor(() => expect(screen.getByRole('button', { name: /clean grid/i })).toBeEnabled());
    await typeCat(user, container);
    await waitFor(() => expect(letters(container)).toEqual(['C', 'A', 'T']));
    return { user, container };
  }
  const blankingResponse = ({ grid }) => ({
    grid: grid.map((row) => row.map((x) => ({ ...x, letter: '' }))),
    removed_count: 3,
    message: 'Removed 3 letters',
  });
  const flaggingResponse = {
    invalid_words: [{ word: 'CAT', status: 'invalid', cells: [[0, 0], [0, 1], [0, 2]] }],
    invalid_count: 1,
    total_checked: 3,
  };
  const settle = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });

  it('deleting a list in Lists drops it from the selection, so the next Verify sends the default list', async () => {
    const user = await setup();
    await openTool(user, 'Autofill');
    await tick(user, 'Demo Words');
    let deleted = false;
    api.getWordlists.mockImplementation(async () => ({
      wordlists: [
        { key: 'comprehensive', name: 'Comprehensive Dictionary', category: 'core' },
        ...(deleted ? [] : [{ key: 'custom/demo_words', name: 'Demo Words', category: 'custom' }]),
      ],
      categories: {},
      tags: {},
    }));
    vi.spyOn(api, 'getWordlist').mockResolvedValue({
      metadata: { name: 'Demo Words', category: 'custom', description: '' },
      words: ['CAT'],
    });
    vi.spyOn(api, 'deleteWordlist').mockImplementation(async () => { deleted = true; return {}; });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    await openTool(user, 'Lists');
    await user.click(await screen.findByText('Demo Words'));
    await user.click(await screen.findByRole('button', { name: /^delete$/i }));
    await waitFor(() => expect(api.deleteWordlist).toHaveBeenCalledWith('custom/demo_words'));
    await verify(user);
    await waitFor(() => expect(verifySpy).toHaveBeenCalledTimes(1));
    expect(verifySpy.mock.calls[0][0].wordlists).toEqual(DEFAULT);
  });

  it('a Clean response that lands after the lists changed opens no confirm and leaves the letters', async () => {
    const { user, container } = await boot();
    await openTool(user, 'Autofill');
    const d = deferred();
    cleanSpy.mockReturnValueOnce(d.promise);
    await clean(user);
    await waitFor(() => expect(cleanSpy).toHaveBeenCalledTimes(1));
    await tick(user, 'Demo Words');
    d.resolve(blankingResponse(cleanSpy.mock.calls[0][0]));
    await settle();
    expect(screen.queryByText(/Clean will remove/)).toBeNull();
    expect(letters(container)).toEqual(['C', 'A', 'T']);
  });

  it('an open Clean confirm is dismissed when the lists change, and applies nothing', async () => {
    const { user, container } = await boot();
    await openTool(user, 'Autofill');
    cleanSpy.mockImplementationOnce(async (arg) => blankingResponse(arg));
    await clean(user);
    expect(await screen.findByText(/Clean will remove 3 letters/)).toBeInTheDocument();
    await tick(user, 'Demo Words');
    await settle();
    expect(screen.queryByText(/Clean will remove/)).toBeNull();
    expect(letters(container)).toEqual(['C', 'A', 'T']);
  });

  it('a Verify response that lands after the lists changed flags no cell and shows no toast', async () => {
    const { user, container } = await boot();
    await openTool(user, 'Autofill');
    const d = deferred();
    verifySpy.mockReturnValueOnce(d.promise);
    await verify(user);
    await waitFor(() => expect(verifySpy).toHaveBeenCalledTimes(1));
    await tick(user, 'Demo Words');
    d.resolve(flaggingResponse);
    await settle();
    expect(flaggedLetters(container)).toHaveLength(0);
    expect(screen.queryByText(/words flagged/)).toBeNull();
  });

  it('regression pin (passes before the fix): ticking then unticking the same list is not a change, so the Clean confirm still opens', async () => {
    const { user } = await boot();
    await openTool(user, 'Autofill');
    const d = deferred();
    cleanSpy.mockReturnValueOnce(d.promise);
    await clean(user);
    await waitFor(() => expect(cleanSpy).toHaveBeenCalledTimes(1));
    await tick(user, 'Demo Words');
    await tick(user, 'Demo Words');
    expect(screen.getByLabelText('Demo Words')).not.toBeChecked();
    d.resolve(blankingResponse(cleanSpy.mock.calls[0][0]));
    // Control: the fixture does blank, so this confirm is the proof that the "no confirm" rows are not vacuous.
    expect(await screen.findByText(/Clean will remove 3 letters/)).toBeInTheDocument();
  });
});
