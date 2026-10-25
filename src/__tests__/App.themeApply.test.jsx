/**
 * Task 6.16 (novice-readiness spec 0.2.8 §3.8, PD-6-G12; review F1, F4): App's
 * theme-apply callback drops a reply for a replaced document and merges the rest
 * against the grid the request was sent from. The panel is a probe that exposes
 * the props App hands it.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import storage from '../lib/storage';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const probe = vi.hoisted(() => ({ props: null }));
vi.mock('../components/ThemeWordsPanel', () => ({
  default: (props) => {
    if (props) probe.props = props;
    return <div className="theme-words-panel" />;
  },
  SUGGESTION_REFETCH_DEBOUNCE_MS: 400,
}));

const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const letters = (c) => Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);
const blacks = (c) => c.querySelectorAll('rect[fill="var(--ink)"]').length;

const replyWith = (grid, word, row = 0) =>
  grid.map((r, ri) =>
    r.map((cell, ci) =>
      ri === row && ci < word.length
        ? { ...cell, letter: word[ci], isThemeLocked: true }
        : cell
    )
  );

beforeEach(() => {
  global.localStorage.getItem.mockReturnValue(null);
  vi.spyOn(storage, 'list').mockResolvedValue([]);
});
afterEach(() => {
  vi.restoreAllMocks();
  probe.props = null;
});

async function openThemePanel(user) {
  const view = render(<App />, { wrapper: ToastProvider });
  await waitFor(() => expect(cells(view.container)).toHaveLength(225));
  await user.click(screen.getByRole('button', { name: /^Theme$/ }));
  await waitFor(() => expect(probe.props).not.toBeNull());
  return view;
}

describe('App handleThemeWordApplied (Task 6.16)', () => {
  it('control: a reply for the current document is merged and toasted', async () => {
    const user = userEvent.setup();
    const { container } = await openThemePanel(user);
    const { grid, docId, onApplyPlacement } = probe.props;
    let result;
    await act(async () => {
      result = onApplyPlacement(replyWith(grid, 'CAT'), { word: 'CAT' }, { sentGrid: grid, docId });
    });
    expect(result).toBe(true);
    expect(letters(container)).toEqual(['C', 'A', 'T']);
    expect(await screen.findByText('Applied "CAT" to grid!')).toBeInTheDocument();
  });

  it('keeps a letter typed after the request was sent (F4)', async () => {
    const user = userEvent.setup();
    const { container } = await openThemePanel(user);
    const { grid, docId, onApplyPlacement } = probe.props; // sent grid: blank
    await user.click(cells(container)[2 * 15 + 2]);
    fireEvent.keyDown(container.querySelector('.xw-grid-focus'), { key: 'Q' });
    await act(async () => {
      onApplyPlacement(replyWith(grid, 'CAT'), { word: 'CAT' }, { sentGrid: grid, docId });
    });
    expect(letters(container).sort()).toEqual(['A', 'C', 'Q', 'T']);
  });

  it('a reply sent before New grid (same size) is dropped: grid unchanged, no toast', async () => {
    const user = userEvent.setup();
    const { container } = await openThemePanel(user);
    const { grid, docId, onApplyPlacement } = probe.props;
    await user.click(screen.getByRole('button', { name: '15×15' }));
    await waitFor(() => expect(probe.props.docId).not.toBe(docId));
    let result;
    await act(async () => {
      result = onApplyPlacement(replyWith(grid, 'CAT'), { word: 'CAT' }, { sentGrid: grid, docId });
    });
    expect(result).toBe(false);
    expect(letters(container)).toEqual([]);
    expect(screen.queryByText('Applied "CAT" to grid!')).toBeNull();
  });

  it('a reply from a smaller document does not throw into a larger live grid', async () => {
    const user = userEvent.setup();
    const { container } = await openThemePanel(user);
    const { grid, onApplyPlacement } = probe.props;
    await user.click(screen.getByRole('button', { name: '21×21' }));
    await waitFor(() => expect(cells(container)).toHaveLength(441));
    // even with a (wrongly) current docId the merge must not throw
    const live = probe.props.docId;
    expect(() =>
      act(() => {
        onApplyPlacement(replyWith(grid, 'CAT'), { word: 'CAT' }, { sentGrid: grid, docId: live });
      })
    ).not.toThrow();
    expect(cells(container)).toHaveLength(441);
    expect(blacks(container)).toBe(0);
    expect(letters(container)).toEqual([]);
  });
});
