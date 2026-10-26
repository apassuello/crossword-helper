/**
 * Issue #91 (novice-readiness spec 0.2.21 section 3.6): with the Theme panel open, a
 * rail click on another tool closes the panel by the same path as its x and shows that
 * tool. Theme and the VIEW toggles leave it open. A close this way stops a running
 * Apply All exactly as the x does (section 3.8, 0.2.19).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import toast from 'react-hot-toast';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import storage from '../lib/storage';
import { api } from '../api/client';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  }),
  Toaster: () => null,
}));

// Inspector panels are markers: this file pins which one is shown, not what it does.
vi.mock('../components/bench/GridPanel', () => ({ default: () => <div data-testid="inspector-edit" /> }));
vi.mock('../components/PatternMatcher', () => ({ default: () => <div data-testid="inspector-search" /> }));
vi.mock('../components/bench/AutofillPanel', () => ({ default: () => <div data-testid="inspector-autofill" /> }));
vi.mock('../components/WordListPanel', () => ({ default: () => <div data-testid="inspector-lists" /> }));
vi.mock('../components/ImportPanel', () => ({ default: () => <div data-testid="inspector-import" /> }));
vi.mock('../components/ExportPanel', () => ({ default: () => <div data-testid="inspector-export" /> }));

const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const letters = (c) => Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);
const railBtn = (name) => screen.getByRole('button', { name: new RegExp(`^${name}$`) });
const themePanel = () => document.querySelector('.theme-words-panel');

beforeEach(() => {
  vi.clearAllMocks();
  global.localStorage.getItem.mockReturnValue(null);
  vi.spyOn(storage, 'list').mockResolvedValue([]);
});
afterEach(() => vi.restoreAllMocks());

async function openTheme(user) {
  const view = render(<App />, { wrapper: ToastProvider });
  await waitFor(() => expect(cells(view.container)).toHaveLength(225));
  await user.click(railBtn('Theme'));
  await waitFor(() => expect(themePanel()).not.toBeNull());
  return view;
}

describe('rail click while the Theme panel is open (#91, spec 0.2.21 section 3.6)', () => {
  it.each([
    ['Grid', 'edit'],
    ['Search', 'search'],
    ['Autofill', 'autofill'],
    ['Lists', 'lists'],
    ['Import', 'import'],
    ['Export', 'export'],
  ])('%s closes the panel, shows that tool and highlights it', async (label, id) => {
    const user = userEvent.setup();
    await openTheme(user);
    await user.click(railBtn(label));
    expect(themePanel()).toBeNull();
    expect(screen.getByTestId(`inspector-${id}`)).toBeInTheDocument();
    expect(railBtn(label)).toHaveClass('on');
    expect(railBtn('Theme')).not.toHaveClass('on');
  });

  it('a click on Theme while it is open leaves it open', async () => {
    const user = userEvent.setup();
    await openTheme(user);
    await user.click(railBtn('Theme'));
    expect(themePanel()).not.toBeNull();
    expect(railBtn('Theme')).toHaveClass('on');
  });

  it('the Symmetry VIEW toggle is not a tool and leaves it open', async () => {
    const user = userEvent.setup();
    await openTheme(user);
    await user.click(railBtn('Symmetry'));
    expect(themePanel()).not.toBeNull();
    expect(railBtn('Theme')).toHaveClass('on');
  });
});

describe('closing the Theme panel mid Apply All stops the run, whichever way it is closed (0.2.19)', () => {
  const words = ['ALPHA', 'BETA', 'GAMMA'];
  const blank = (g) => g.map((r) => r.map((c) => ({ ...c })));
  const suggestions = words.map((w, i) => ({
    word: w,
    length: w.length,
    suggestions: [{ word: w, row: i * 2, col: 0, direction: 'across', score: 90, reasoning: 'ok' }],
  }));

  it.each([
    ['the x button', () => fireEvent.click(document.querySelector('.close-btn'))],
    ['a rail click on Grid', () => fireEvent.click(railBtn('Grid'))],
  ])('closed by %s', async (_name, close) => {
    const user = userEvent.setup();
    vi.spyOn(api, 'themeUpload').mockResolvedValue({
      words,
      count: words.length,
      validation: { valid: true, errors: [], warnings: [] },
    });
    vi.spyOn(api, 'themeSuggestPlacements').mockResolvedValue({ suggestions });
    let resolveSecond;
    const applied = [];
    vi.spyOn(api, 'themeApplyPlacement')
      .mockImplementationOnce(async (req) => {
        applied.push(1);
        return { grid: blank(req.grid) };
      })
      .mockImplementationOnce((req) => {
        applied.push(2);
        // the reply that lands after the close writes a Q no other path writes
        const late = blank(req.grid);
        late[10][10] = { ...late[10][10], letter: 'Q', isThemeLocked: true };
        return new Promise((res) => (resolveSecond = () => res({ grid: late })));
      })
      .mockImplementation(async (req) => {
        applied.push(3);
        return { grid: blank(req.grid) };
      });

    const { container } = await openTheme(user);
    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: { files: [new File([words.join('\n')], 'theme.txt', { type: 'text/plain' })] },
    });
    await waitFor(() => expect(document.querySelectorAll('.apply-btn').length).toBe(3));
    await act(async () => {
      screen.getByRole('button', { name: /apply all best placements/i }).click();
    });
    await waitFor(() => expect(applied).toEqual([1, 2]));

    act(() => close());
    expect(themePanel()).toBeNull();
    await act(async () => {
      resolveSecond();
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(applied).toEqual([1, 2]); // word 3 is never sent
    const applyAll = (c) => c[1] && c[1].id === 'apply-all';
    expect(toast.success.mock.calls.filter(applyAll)).toHaveLength(0);
    expect(toast.error.mock.calls.filter(applyAll)).toHaveLength(0);
    expect(toast.dismiss.mock.calls.filter((c) => c[0] === 'apply-all')).toHaveLength(1);
    expect(letters(container)).not.toContain('Q'); // the reply that landed after the close is dropped
  });
});
