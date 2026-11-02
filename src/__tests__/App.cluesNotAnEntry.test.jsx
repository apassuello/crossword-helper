/**
 * Final fix 2 (Greptile P1, PR #116; clue-authoring spec section 3.3, ruled 2026-11-02): Commit
 * and Keep write nothing for a key that is not an entry when they run (no slot of two or more
 * squares starts at its square in its direction). A row that disappears with a draft open loses
 * the draft; a clue already committed at that key stays, orphaned, with Delete.
 *
 * The real CluesPanel is rendered (wrapped, to record the props App hands it) so a row can
 * unmount with its draft open. ThemeWordsPanel is a stub that captures `onApplyPlacement`, which
 * is then called after the Theme tool has closed: a reply that adds a black square.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { Q15, spyApp, waitForBlank15, openClues, clueInputs, writeClue, typeDraft } from './appClues';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));
const probe = vi.hoisted(() => ({ panel: null, theme: null }));
vi.mock('../components/CluesPanel', async (importOriginal) => {
  const Real = (await importOriginal()).default;
  return {
    default: (props) => {
      if (props) probe.panel = props;
      return <Real {...props} />;
    },
  };
});
vi.mock('../components/ThemeWordsPanel', () => ({
  default: (props) => {
    if (props) probe.theme = props;
    return <div className="theme-words-panel" />;
  },
  SUGGESTION_REFETCH_DEBOUNCE_MS: 400,
}));

const K = '1,0,across'; // row 1, a 15-square entry on the blank grid
const A = { text: 'Alpha', answer: Q15 };

beforeEach(() => {
  probe.panel = null;
  probe.theme = null;
  spyApp();
});
afterEach(() => vi.restoreAllMocks());

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitForBlank15(view.container);
  return { user, ...view };
};

/** Opens the Theme tool and keeps its `onApplyPlacement`, as a reply still in flight would. */
const captureTheme = async (user) => {
  await user.click(screen.getByRole('button', { name: /^Theme$/ }));
  await waitFor(() => expect(probe.theme).not.toBeNull());
  return probe.theme;
};

/** Fires the captured reply: CAT in row 0 and one black square at `black`. */
const reply = async (captured, black) => {
  const { grid, docId, onApplyPlacement } = captured;
  const next = grid.map((r, ri) =>
    r.map((cell, ci) => {
      if (ri === 0 && ci < 3) return { ...cell, letter: 'CAT'[ci], isThemeLocked: true };
      if (ri === black[0] && ci === black[1]) return { ...cell, isBlack: true };
      return cell;
    })
  );
  let res;
  await act(async () => {
    res = onApplyPlacement(next, { word: 'CAT' }, { sentGrid: grid, docId, addedBlackSquares: [black] });
  });
  expect(res).toEqual({ applied: true, addedBlackSquares: 1 });
};

describe('Commit and Keep write nothing for a key that is no longer an entry (spec 3.3)', () => {
  it('a committed clue whose row vanishes with a different draft open: the clue stays, unchanged', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[1], 'Alpha');
    expect(probe.panel.clues).toEqual({ [K]: A });
    const captured = await captureTheme(user);
    await openClues(user);
    await typeDraft(user, clueInputs()[1], 'Beta');
    await reply(captured, [1, 1]); // row 1 across is now one square: (1,0)
    expect(probe.panel.clues).toEqual({ [K]: A });
    for (const c of Object.values(probe.panel.clues)) expect(c.answer.length).toBeGreaterThanOrEqual(2);
  });

  it('a new draft whose row vanishes: nothing is written at its key', async () => {
    const { user } = await boot();
    await openClues(user);
    const captured = await captureTheme(user);
    await openClues(user);
    await typeDraft(user, clueInputs()[1], 'Beta');
    await reply(captured, [1, 1]);
    expect(probe.panel.clues).toEqual({});
    expect(Object.keys(probe.panel.clues)).not.toContain(K);
  });

  it('onCommit on a key whose square starts no entry (second square of a down entry) writes nothing', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[1], 'Alpha');
    expect(probe.panel.clues).toEqual({ [K]: A });
    act(() => {
      probe.panel.onCommit('1,0,down', 'Text');
    });
    expect(probe.panel.clues).toEqual({ [K]: A });
  });

  it('onCommit on a key whose square starts no entry (second square of an across entry) writes nothing', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[1], 'Alpha');
    expect(probe.panel.clues).toEqual({ [K]: A });
    act(() => {
      probe.panel.onCommit('1,1,across', 'Text');
    });
    expect(probe.panel.clues).toEqual({ [K]: A });
  });

  it('onKeep on a key that stopped being an entry writes nothing', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[1], 'Alpha');
    const captured = await captureTheme(user);
    await reply(captured, [1, 1]);
    await openClues(user);
    expect(probe.panel.clues).toEqual({ [K]: A });
    act(() => {
      probe.panel.onKeep(K);
    });
    expect(probe.panel.clues).toEqual({ [K]: A });
  });

  it('control: an entry cut to exactly two squares still commits its two-square pattern', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[1], 'Alpha');
    const captured = await captureTheme(user);
    await reply(captured, [1, 2]); // row 1 across is now (1,0),(1,1)
    await openClues(user);
    act(() => {
      probe.panel.onCommit(K, 'Alpha two');
    });
    expect(probe.panel.clues).toEqual({ [K]: { text: 'Alpha two', answer: '??' } });
  });
});
