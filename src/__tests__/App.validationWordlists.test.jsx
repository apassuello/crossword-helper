/**
 * #102: Verify words and Clean grid check against the word lists ticked in Autofill, and the
 * selection outlives the Autofill panel. Real App and real AutofillPanel; the API client is spied.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
