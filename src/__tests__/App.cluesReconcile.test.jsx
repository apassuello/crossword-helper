/**
 * Task 10 (clue-authoring spec 0.1.4, section 5.6 and 6.2 "Reconciliation"): App passes the
 * reconciled statuses to the Clues panel as `displayStatuses`, and `active` is the Clues tool open
 * and no run live. Real App, rail and Clues panel; `api.checkClues` is stubbed; autofill is started
 * the way App.cluesGate.test.jsx does.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import {
  spyApp,
  waitForBlank15,
  openClues,
  openTool,
  clueInputs,
  writeClue,
} from './appClues';
import { deferred, stubCheckClues } from './importExportHelpers';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const RUN_STATUS = 'Editing is paused while autofill runs.';
let stub;
let startFillD;

// Whatever clues a request carries, the server calls stale.
const SAYS_STALE = async ({ clues }) => ({
  success: true,
  statuses: Object.fromEntries(Object.keys(clues).map((k) => [k, 'stale'])),
});

beforeEach(() => {
  startFillD = deferred();
  spyApp({ startFill: () => startFillD.promise });
  stub = stubCheckClues(SAYS_STALE);
});
afterEach(() => {
  stub.restore();
  vi.restoreAllMocks();
});

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitForBlank15(view.container);
  return { user, ...view };
};
const sleep = (ms) =>
  act(async () => {
    await new Promise((resolve) => setTimeout(resolve, ms));
  });
const writtenFor = () => screen.queryByText(/^Written for /);
const keepButtons = () => screen.queryAllByRole('button', { name: 'Keep' });

describe('App shows the reconciled status in the Clues panel (spec 5.6)', () => {
  it('a server reply of stale where the browser says ok shows the stale row (Written for, Keep)', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    // The browser's own status for a clue just written is ok: no stale row yet.
    expect(writtenFor()).toBeNull();
    expect(keepButtons()).toHaveLength(0);

    // 300 ms after the commit changes the status signature the request goes out.
    await waitFor(() => expect(screen.getByText(/^Written for /)).toBeInTheDocument(), {
      timeout: 3000,
    });
    expect(screen.getByText('Written for ' + '·'.repeat(15))).toBeInTheDocument();
    expect(keepButtons()).toHaveLength(1);
    const last = stub.fn.mock.calls[stub.fn.mock.calls.length - 1][0];
    expect(last.size).toBe(15);
    expect(last.clues['0,0,across'].text).toBe('Alpha');
  });
});

describe('the tool gate (spec 5.6: the request is for the open Clues panel)', () => {
  it('with the Clues panel closed and nothing committed, no request goes out', async () => {
    await boot();
    await sleep(600);
    expect(stub.fn.mock.calls.length).toBe(0);
  });
});

describe('gating at the site that computes active (spec 5.6: "while no autofill run is live")', () => {
  it('no request during a run and the browser status shows; ending the run sends exactly one', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await waitFor(() => expect(screen.getByText(/^Written for /)).toBeInTheDocument(), {
      timeout: 3000,
    });

    // Start a run, then open the Clues tool during it.
    await openTool(user, 'Autofill');
    await user.click(await screen.findByRole('button', { name: /start autofill/i }));
    await waitFor(() => expect(screen.getByText(RUN_STATUS)).toBeInTheDocument());
    await openClues(user);
    const before = stub.fn.mock.calls.length;

    // The earlier matching reply does not show: during the run every status is the browser's.
    expect(writtenFor()).toBeNull();
    expect(keepButtons()).toHaveLength(0);
    await sleep(600);
    expect(stub.fn.mock.calls.length).toBe(before);
    expect(writtenFor()).toBeNull();

    // End the run with the panel open: exactly one request.
    await act(async () => {
      startFillD.reject(Object.assign(new Error('boom'), { code: 'X' }));
    });
    await waitFor(() => expect(screen.queryByText(RUN_STATUS)).toBeNull());
    await waitFor(() => expect(stub.fn.mock.calls.length).toBe(before + 1), { timeout: 3000 });
    await sleep(600);
    expect(stub.fn.mock.calls.length).toBe(before + 1);
    await waitFor(() => expect(screen.getByText(/^Written for /)).toBeInTheDocument());
  });
});
