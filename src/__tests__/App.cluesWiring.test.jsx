/**
 * Task 8, fix cycle 1 (clue-authoring spec 0.1.4, Decision 5, sections 4.1, 4.3, 3.3 and the
 * Task 8 contract): the App wiring that no earlier test failed without.
 *
 *  - I1: App's `cluesRef` advances after a clue write, so two writes in one tick are two steps.
 *  - I2: `acceptClean` and `handleThemeWordApplied` each pass `cluesRef.current` to `recordStep`.
 *  - I3: `onSaved` builds the clean point from the written document's clues.
 *  - I4: `commitClue` hands the panel's error back through App.
 *
 * The Clues and Theme panels are recording stubs (as in App.cluesGate.test.jsx and
 * App.themeApply.test.jsx), so the handlers App hands them can be called in one `act()`, the way
 * a keyboard never does. Everything else is real.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';
import storage from '../lib/storage';
import { saveArg } from './saveArgs';
import {
  Q15,
  DIRTY,
  cells,
  letters,
  focusEl,
  spyApp,
  waitForBlank15,
  openClues,
  undoBtn,
} from './appClues';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const probe = vi.hoisted(() => ({ panel: null, theme: null }));
vi.mock('../components/CluesPanel', () => ({
  default: (props) => {
    if (props) probe.panel = props;
    return null;
  },
}));
vi.mock('../components/ThemeWordsPanel', () => ({
  default: (props) => {
    if (props) probe.theme = props;
    return <div className="theme-words-panel" />;
  },
  SUGGESTION_REFETCH_DEBOUNCE_MS: 400,
}));

const K1 = '1,0,across';
const K2 = '2,0,across';
const A1 = { text: 'One', answer: Q15 };
const A2 = { text: 'Two', answer: Q15 };

beforeEach(() => {
  probe.panel = null;
  probe.theme = null;
  spyApp();
});
afterEach(() => {
  vi.restoreAllMocks();
});

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitForBlank15(view.container);
  return { user, ...view };
};

describe('I1: two clue writes in one tick are two steps (App cluesRef advances in writeClues)', () => {
  it('both clues are written, and two undos remove them one at a time', async () => {
    const { user } = await boot();
    await openClues(user);
    const { onCommit } = probe.panel;
    act(() => {
      onCommit(K1, 'One');
      onCommit(K2, 'Two');
    });
    expect(probe.panel.clues).toEqual({ [K1]: A1, [K2]: A2 });
    await user.click(undoBtn());
    expect(probe.panel.clues).toEqual({ [K1]: A1 });
    await user.click(undoBtn());
    expect(probe.panel.clues).toEqual({});
    expect(undoBtn()).toBeDisabled();
  });

  it('a Commit and a Delete in one tick: the Delete builds on the Commit', async () => {
    const { user } = await boot();
    await openClues(user);
    const { onCommit, onDelete } = probe.panel;
    act(() => {
      onCommit(K1, 'One');
      onDelete(K1);
    });
    expect(probe.panel.clues).toEqual({});
    await user.click(undoBtn());
    expect(probe.panel.clues).toEqual({ [K1]: A1 });
  });
});

describe('I2: every recordStep site passes the live clues, so undo of a grid change keeps them', () => {
  it('acceptClean: commit a clue, accept a Clean, undo the Clean: the clue is still there', async () => {
    vi.spyOn(api, 'cleanGrid').mockResolvedValue({
      grid: Array.from({ length: 15 }, () => Array(15).fill('.')),
      removed_count: 1,
      valid_count: 0,
      cleared_cells: [[0, 0]],
      message: 'Removed 1 invalid word',
    });
    const { user, container } = await boot();
    await user.click(cells(container)[0]);
    fireEvent.keyDown(focusEl(container), { key: 'B' });
    expect(letters(container)).toEqual(['B']);
    await openClues(user);
    act(() => {
      probe.panel.onCommit(K1, 'One');
    });
    expect(probe.panel.clues).toEqual({ [K1]: A1 });

    await user.click(screen.getByText('Clean grid'));
    await user.click(await screen.findByRole('button', { name: 'Clean' }));
    await waitFor(() => expect(letters(container)).toEqual([]));

    await user.click(undoBtn()); // the Clean
    expect(letters(container)).toEqual(['B']);
    expect(probe.panel.clues).toEqual({ [K1]: A1 });
  });

  it('handleThemeWordApplied: commit a clue, apply a theme word, undo: the clue is still there', async () => {
    const { user, container } = await boot();
    await openClues(user);
    act(() => {
      probe.panel.onCommit(K1, 'One');
    });
    expect(probe.panel.clues).toEqual({ [K1]: A1 });

    await user.click(screen.getByRole('button', { name: /^Theme$/ }));
    await waitFor(() => expect(probe.theme).not.toBeNull());
    const { grid, docId, onApplyPlacement } = probe.theme;
    const reply = grid.map((r, ri) =>
      r.map((cell, ci) =>
        ri === 0 && ci < 3 ? { ...cell, letter: 'CAT'[ci], isThemeLocked: true } : cell
      )
    );
    let applied;
    await act(async () => {
      applied = onApplyPlacement(reply, { word: 'CAT' }, { sentGrid: grid, docId });
    });
    expect(applied).toMatchObject({ applied: true });
    expect(letters(container)).toEqual(['C', 'A', 'T']);

    await user.click(undoBtn()); // the theme word
    expect(letters(container)).toEqual([]);
    expect(probe.panel.clues).toEqual({ [K1]: A1 });
  });
});

describe('I3: onSaved takes the clean point from the clues the save wrote', () => {
  it('a clue committed while the save is in flight leaves the document dirty', async () => {
    const { user } = await boot();
    await openClues(user);
    act(() => {
      probe.panel.onCommit(K1, 'One');
    });
    let release;
    storage.save.mockImplementation((doc, opts) => {
      saveArg([doc, opts], 0); // the document is resolved when the write starts
      saveArg([doc, opts], 1);
      return new Promise((r) => {
        release = () =>
          r({ savedAt: new Date().toISOString(), id: 'saved-id', name: 'n', forked: false });
      });
    });
    // not `saveGrid`: the name prompt stays open until the held write resolves
    await user.click(screen.getByRole('button', { name: /save grid/i }));
    await user.click(await screen.findByRole('button', { name: 'Save' }));
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(saveArg(storage.save.mock.calls[0], 0).clues).toEqual({ [K1]: A1 });

    act(() => {
      probe.panel.onCommit(K2, 'Two');
    });
    expect(probe.panel.clues).toEqual({ [K1]: A1, [K2]: A2 });
    await act(async () => release());

    await waitFor(() => expect(screen.getByText(DIRTY)).toBeInTheDocument());
    expect(screen.queryByText(/saved locally/)).toBeNull();
  });
});

describe('I4: commitClue answers the panel with the error of a refused commit', () => {
  it('a 201-code-point draft returns the exact message, changes no clue and records no step', async () => {
    const { user } = await boot();
    await openClues(user);
    let res;
    act(() => {
      res = probe.panel.onCommit(K1, 'x'.repeat(201));
    });
    expect(res).toEqual({ error: 'At most 200 characters.' });
    expect(probe.panel.clues).toEqual({});
    expect(undoBtn()).toBeDisabled();
    expect(screen.queryByText(DIRTY)).toBeNull();
  });

  it('control: a draft of exactly 200 code points is accepted with { error: null }', async () => {
    const { user } = await boot();
    await openClues(user);
    let res;
    act(() => {
      res = probe.panel.onCommit(K1, 'x'.repeat(200));
    });
    expect(res).toEqual({ error: null });
    expect(probe.panel.clues[K1]).toEqual({ text: 'x'.repeat(200), answer: Q15 });
  });
});
