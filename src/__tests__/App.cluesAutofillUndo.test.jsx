/**
 * Final review fix 1 (clue-authoring spec 0.1.4, section 4.3; novice spec 0.2.25 section 3.9 "What a
 * step holds"): undoing an autofill run must restore the clue map with the grid. The two commit
 * sites of `useAutofillMachine` (`onRunCommitted` on run success, and `keepFill`) reach
 * `recordStep` without the clues, so a step is stored with `{}` and Undo wipes every clue.
 *
 * One row per site, by name. The harness is undoWiring.test.jsx's "autofill commit points" (the
 * real App, `api.openProgress` captured for the SSE handlers) with the Clues panel as a
 * recording stub (as App.cluesWiring.test.jsx does). Undo is the real top-bar button.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';
import { Q15, cells, letters, focusEl, spyApp, waitForBlank15, openClues, undoBtn } from './appClues';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const probe = vi.hoisted(() => ({ panel: null, mounted: false }));
vi.mock('../components/CluesPanel', async () => {
  const R = await import('react');
  return {
    default: (props) => {
      if (props) probe.panel = props;
      R.useEffect(() => {
        probe.mounted = true;
        return () => {
          probe.mounted = false;
        };
      }, []);
      return null;
    },
  };
});

const K1 = '1,0,across';
const A1 = { text: 'One', answer: Q15 };
const A1EDITED = { text: 'One, edited', answer: Q15 };

let handlers;
beforeEach(() => {
  probe.panel = null;
  probe.mounted = false;
  handlers = undefined;
  spyApp({ startFill: () => Promise.resolve({ task_id: 't1', ceiling_seconds: 300 }) });
  api.openProgress.mockImplementation((id, h) => {
    handlers = h;
    return { close() {} };
  });
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const blankCli = () => Array.from({ length: 15 }, () => Array(15).fill('.'));

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitForBlank15(view.container);
  return { user, ...view };
};

/** The clue map the panel holds now. The stub only tracks props while mounted, so reopen it first. */
const cluesNow = async (user) => {
  if (!probe.mounted) await openClues(user);
  return probe.panel.clues;
};

const commitClue = async (user, text = 'One') => {
  if (!probe.mounted) await openClues(user);
  act(() => {
    probe.panel.onCommit(K1, text);
  });
};

const startRun = async (user) => {
  await user.click(screen.getByRole('button', { name: /^autofill$/i }));
  await user.click(await screen.findByRole('button', { name: /start autofill/i }));
  await waitFor(() => expect(handlers).toBeTruthy());
};

describe('undo of an autofill run keeps the clues', () => {
  it('run success: commit a clue, run to success, Undo: grid back and the clue map unchanged', async () => {
    const { user, container } = await boot();
    await user.click(cells(container)[3 * 15 + 3]);
    fireEvent.keyDown(focusEl(container), { key: 'A' });
    await commitClue(user);
    expect(await cluesNow(user)).toEqual({ [K1]: A1 });
    await startRun(user);
    const g = blankCli();
    g[3][3] = 'A';
    g[0][0] = 'B';
    const final = g.map((r) => r.slice());
    final[0][1] = 'C';
    act(() =>
      handlers.onEvent({
        status: 'complete',
        data: { success: true, grid: final, slots_filled: 3, total_slots: 3 },
      })
    );
    await waitFor(() =>
      expect(screen.getByText('Successfully filled 3/3 slots!')).toBeInTheDocument()
    );
    expect(letters(container).sort()).toEqual(['A', 'B', 'C']);

    await user.click(undoBtn()); // the run
    expect(letters(container)).toEqual(['A']);
    expect(await cluesNow(user)).toEqual({ [K1]: A1 });
  });

  it('keepFill: commit a clue, Keep partial fill, Undo: grid back and the clue map unchanged', async () => {
    const { user, container } = await boot();
    await user.click(cells(container)[3 * 15 + 3]);
    fireEvent.keyDown(focusEl(container), { key: 'A' });
    await commitClue(user);
    await startRun(user);
    const g = blankCli();
    g[3][3] = 'A';
    g[0][0] = 'B';
    act(() =>
      handlers.onEvent({
        status: 'complete',
        data: { success: false, grid: g, slots_filled: 1, total_slots: 2, fill_percentage: 50 },
      })
    );
    await user.click(await screen.findByRole('button', { name: /keep partial fill/i }));
    expect(letters(container).sort()).toEqual(['A', 'B']);

    await user.click(undoBtn()); // the Keep
    expect(letters(container)).toEqual(['A']);
    expect(await cluesNow(user)).toEqual({ [K1]: A1 });
  });

  it('keepFill after a clue edit: the step holds the clues as clicked, not as the run started', async () => {
    const { user, container } = await boot();
    await user.click(cells(container)[3 * 15 + 3]);
    fireEvent.keyDown(focusEl(container), { key: 'A' });
    await commitClue(user);
    await startRun(user);
    const g = blankCli();
    g[3][3] = 'A';
    g[0][0] = 'B';
    act(() =>
      handlers.onEvent({
        status: 'complete',
        data: { success: false, grid: g, slots_filled: 1, total_slots: 2, fill_percentage: 50 },
      })
    );
    await screen.findByRole('button', { name: /keep partial fill/i });
    await openClues(user); // the run is over: the panel is live again
    act(() => {
      probe.panel.onCommit(K1, 'One, edited');
    });
    expect(probe.panel.clues).toEqual({ [K1]: A1EDITED });
    await user.click(screen.getByRole('button', { name: /^autofill$/i }));
    await user.click(await screen.findByRole('button', { name: /keep partial fill/i }));
    expect(letters(container).sort()).toEqual(['A', 'B']);

    await user.click(undoBtn()); // the Keep
    expect(letters(container)).toEqual(['A']);
    expect(await cluesNow(user)).toEqual({ [K1]: A1EDITED });
    await user.click(undoBtn()); // the edit
    expect(await cluesNow(user)).toEqual({ [K1]: A1 });
  });

  it('a successful run that changes nothing, with a clue committed, records no step', async () => {
    const { user, container } = await boot();
    await commitClue(user);
    await startRun(user);
    // a run that finds nothing to add: success, and the grid it returns is the Start grid
    act(() =>
      handlers.onEvent({
        status: 'complete',
        data: { success: true, grid: blankCli(), slots_filled: 0, total_slots: 0 },
      })
    );
    await waitFor(() =>
      expect(screen.getByText('Successfully filled 0/0 slots!')).toBeInTheDocument()
    );
    expect(letters(container)).toEqual([]);

    await user.click(undoBtn()); // the clue commit is the only step
    expect(await cluesNow(user)).toEqual({});
    expect(undoBtn()).toBeDisabled();
  });
});
