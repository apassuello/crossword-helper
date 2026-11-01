/**
 * Task 8 (clue-authoring spec 0.1.4, section 4.4 "Gating during an autofill run" and 6.2
 * "Gating"): Commit, Keep and Delete join the D1 writer list, and each returns early when the
 * check fails at write time. "A handler called anyway writes nothing."
 *
 * The Clues panel is replaced here by a recording stub (the way App.test.jsx records GridPanel's
 * props), so the three handlers App hands it can be called directly, past the controls that are
 * disabled. The stub stays out of the files that drive the real panel.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import storage from '../lib/storage';
import {
  Q15,
  DIRTY,
  staleAndOrphanEntry,
  spyApp,
  waitForBlank15,
  openClues,
  openTool,
  undoBtn,
} from './appClues';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const captured = vi.hoisted(() => ({}));
vi.mock('../components/CluesPanel', () => ({
  default: (props) => {
    if (props) captured.panel = props;
    return null;
  },
}));

const STATUS = 'Editing is paused while autofill runs.';
let startFillD;
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

beforeEach(() => {
  for (const k of Object.keys(captured)) delete captured[k];
  startFillD = deferred();
  spyApp({ startFill: () => startFillD.promise });
  storage.load.mockResolvedValue(staleAndOrphanEntry());
});
afterEach(() => {
  vi.restoreAllMocks();
});

const STALE = '0,0,across';
const ORPHAN = '3,3,down';
const FRESH = '1,0,across';
const initialClues = () => staleAndOrphanEntry().clues;

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitForBlank15(view.container);
  await screen.findByText(/^Restored "Stale"/);
  return { user, ...view };
};
const startRun = async (user) => {
  await openTool(user, 'Autofill');
  await user.click(await screen.findByRole('button', { name: /start autofill/i }));
  await waitFor(() => expect(screen.getByText(STATUS)).toBeInTheDocument());
};
const endRun = async () => {
  await act(async () => {
    startFillD.reject(Object.assign(new Error('boom'), { code: 'X' }));
  });
  await waitFor(() => expect(screen.queryByText(STATUS)).toBeNull());
};

const HANDLERS = ['onCommit', 'onKeep', 'onDelete'];
const callWith = (handlers, name) => {
  const calls = {
    onCommit: () => handlers.onCommit(FRESH, 'Fresh clue'),
    onKeep: () => handlers.onKeep(STALE),
    onDelete: () => handlers.onDelete(ORPHAN),
  };
  let out;
  act(() => {
    out = calls[name]();
  });
  return out;
};

describe('control: with no run live each handler writes and records one step', () => {
  it('onCommit writes the trimmed text with the entry pattern as answer', async () => {
    const { user } = await boot();
    await openClues(user);
    expect(captured.panel.clues).toEqual(initialClues());
    const res = callWith(captured.panel, 'onCommit');
    expect(res).toEqual({ error: null });
    expect(captured.panel.clues[FRESH]).toEqual({ text: 'Fresh clue', answer: Q15 });
    expect(undoBtn()).not.toBeDisabled();
    expect(screen.getByText(DIRTY)).toBeInTheDocument();
  });

  it('onKeep sets the answer to the current pattern', async () => {
    const { user } = await boot();
    await openClues(user);
    callWith(captured.panel, 'onKeep');
    expect(captured.panel.clues[STALE]).toEqual({ text: 'Old stale clue', answer: Q15 });
    expect(undoBtn()).not.toBeDisabled();
  });

  it('onDelete removes the clue', async () => {
    const { user } = await boot();
    await openClues(user);
    callWith(captured.panel, 'onDelete');
    expect(captured.panel.clues[ORPHAN]).toBeUndefined();
    expect(Object.keys(captured.panel.clues)).toEqual([STALE]);
    expect(undoBtn()).not.toBeDisabled();
  });
});

describe('a handler called while a run is live writes nothing (spec 4.4)', () => {
  const VARIANTS = [
    ['captured before the run started (a stale closure)', 'before'],
    ['captured while the run is live', 'during'],
  ];

  for (const name of HANDLERS) {
    for (const [label, when] of VARIANTS) {
      it(`${name}, ${label}: no change, no step, and onCommit answers { error: null }`, async () => {
        const { user } = await boot();
        let handlers;
        if (when === 'before') {
          await openClues(user);
          handlers = { ...captured.panel };
        }
        await startRun(user);
        if (when === 'during') {
          await openClues(user);
          handlers = { ...captured.panel };
          expect(captured.panel.editingPaused).toBe(true);
        }

        const res = callWith(handlers, name);
        if (name === 'onCommit') expect(res).toEqual({ error: null });

        await endRun();
        await openClues(user);
        expect(captured.panel.clues).toEqual(initialClues());
        expect(undoBtn()).toBeDisabled(); // no step was recorded
        expect(screen.queryByText(DIRTY)).toBeNull();
      });
    }
  }

  it('the panel is told the run is live', async () => {
    const { user } = await boot();
    await openClues(user);
    expect(captured.panel.editingPaused).toBe(false);
    await startRun(user);
    await openClues(user);
    expect(captured.panel.editingPaused).toBe(true);
  });
});
