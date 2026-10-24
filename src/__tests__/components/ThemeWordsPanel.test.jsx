/**
 * Tests for ThemeWordsPanel - theme word management
 * Tests file upload, placement suggestions, conflict detection, apply placements
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import React, { useState } from 'react';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import toast from 'react-hot-toast';
import ThemeWordsPanel, { SUGGESTION_REFETCH_DEBOUNCE_MS } from '../../components/ThemeWordsPanel';
import { api } from '../../api/client';
import { createEmptyGrid, emptyGrid15x15 } from '../fixtures/gridFixtures';
import { http, HttpResponse } from 'msw';
import { mockApiEndpoint, server } from '../fixtures/apiMocks';

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  }),
}));

const BOUNDARY_CONFLICT =
  'Boundary black square at (7, 4) requires a symmetric black square at (7, 10), ' +
  'which is occupied by this word — placement would break grid symmetry';

describe('ThemeWordsPanel Component', () => {
  const defaultProps = {
    grid: emptyGrid15x15,
    gridSize: 15,
    onApplyPlacement: vi.fn(),
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders file upload button', () => {
    render(<ThemeWordsPanel {...defaultProps} />);
    expect(screen.getByRole('button', { name: /choose file/i })).toBeInTheDocument();
  });

  it('validates uploaded theme words', async () => {
    const user = userEvent.setup();

    // Mock the upload endpoint to return valid words with required validation field
    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY', 'CELEBRATION'],
      count: 2,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
      },
    });

    // Mock suggest-placements to return empty (auto-called after upload)
    mockApiEndpoint('post', '/theme/suggest-placements', {
      suggestions: [],
    });

    render(<ThemeWordsPanel {...defaultProps} />);

    const file = new File(['BIRTHDAY\nCELEBRATION'], 'theme.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]');

    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByText('BIRTHDAY')).toBeInTheDocument();
      expect(screen.getByText('CELEBRATION')).toBeInTheDocument();
    });
  });

  it('shows placement suggestions after upload', async () => {
    const user = userEvent.setup();

    // Mock upload endpoint
    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY'],
      count: 1,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
      },
    });

    // Mock suggest-placements to return suggestions
    mockApiEndpoint('post', '/theme/suggest-placements', {
      suggestions: [
        {
          word: 'BIRTHDAY',
          length: 8,
          suggestions: [
            {
              word: 'BIRTHDAY',
              row: 0,
              col: 0,
              direction: 'across',
              score: 90,
              reasoning: 'Good placement',
            },
          ],
        },
      ],
    });

    render(<ThemeWordsPanel {...defaultProps} />);

    const file = new File(['BIRTHDAY'], 'theme.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]');
    await user.upload(input, file);

    await waitFor(() => {
      // Placement Suggestions section appears
      expect(screen.getByText('Placement Suggestions')).toBeInTheDocument();
    });
  });

  it('shows apply button for each placement suggestion', async () => {
    const user = userEvent.setup();

    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY'],
      count: 1,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
      },
    });

    mockApiEndpoint('post', '/theme/suggest-placements', {
      suggestions: [
        {
          word: 'BIRTHDAY',
          length: 8,
          suggestions: [
            {
              word: 'BIRTHDAY',
              row: 0,
              col: 0,
              direction: 'across',
              score: 90,
              reasoning: 'Good placement',
            },
          ],
        },
      ],
    });

    render(<ThemeWordsPanel {...defaultProps} />);

    const file = new File(['BIRTHDAY'], 'theme.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]');
    await user.upload(input, file);

    await waitFor(() => {
      // There may be multiple apply buttons (one per suggestion)
      const applyButtons = screen.getAllByRole('button', { name: /apply this placement/i });
      expect(applyButtons.length).toBeGreaterThan(0);
    });
  });

  it('RED-1: synthesised code must not reach the user on an empty-body 500', async () => {
    const user = userEvent.setup();

    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY'],
      count: 1,
      validation: { valid: true, errors: [], warnings: [] },
    });

    // Empty body -> ApiError.message is '' -> must fall through to the
    // component's own fallback text, never the synthesised 'HTTP_500' code.
    mockApiEndpoint('post', '/theme/suggest-placements', {}, 500);

    render(<ThemeWordsPanel {...defaultProps} />);

    const file = new File(['BIRTHDAY'], 'theme.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]');
    await user.upload(input, file);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to analyze placements');
    });
  });

  it('RED-2: apply-placement conflict text must reach the user', async () => {
    const user = userEvent.setup();

    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY'],
      count: 1,
      validation: { valid: true, errors: [], warnings: [] },
    });

    mockApiEndpoint('post', '/theme/suggest-placements', {
      suggestions: [
        {
          word: 'BIRTHDAY',
          length: 8,
          suggestions: [
            {
              word: 'BIRTHDAY',
              row: 0,
              col: 0,
              direction: 'across',
              score: 90,
              reasoning: 'Good placement',
            },
          ],
        },
      ],
    });

    render(<ThemeWordsPanel {...defaultProps} />);

    const file = new File(['BIRTHDAY'], 'theme.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]');
    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /apply this placement/i })).toBeInTheDocument();
    });

    // Override the default 200 apply-placement handler for this test only.
    mockApiEndpoint(
      'post',
      '/theme/apply-placement',
      { error: 'Placement conflicts detected', conflicts: [BOUNDARY_CONFLICT], applied: false },
      400
    );

    await user.click(screen.getByRole('button', { name: /apply this placement/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('symmetric black square'));
    });
  });

  it('does not gate on extension: a .dict file is read and uploaded', async () => {
    const user = userEvent.setup();
    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY'],
      count: 1,
      validation: { valid: true, errors: [], warnings: [] },
    });
    mockApiEndpoint('post', '/theme/suggest-placements', { suggestions: [] });
    render(<ThemeWordsPanel {...defaultProps} />);
    const input = document.querySelector('input[type="file"]');
    expect(input.hasAttribute('accept')).toBe(false);
    await user.upload(input, new File(['BIRTHDAY'], 'theme.dict'), { applyAccept: false });
    expect(toast.error).not.toHaveBeenCalledWith(expect.stringMatching(/\.txt/));
    await waitFor(() => expect(screen.getByText('BIRTHDAY')).toBeInTheDocument());
  });
});

describe('ThemeWordsPanel while editingPaused (Task 4.4, D1)', () => {
  const showSuggestions = async (extraProps) => {
    const user = userEvent.setup();
    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY'],
      count: 1,
      validation: { valid: true, errors: [], warnings: [] },
    });
    mockApiEndpoint('post', '/theme/suggest-placements', {
      suggestions: [
        {
          word: 'BIRTHDAY',
          length: 8,
          suggestions: [
            { word: 'BIRTHDAY', row: 0, col: 0, direction: 'across', score: 90, reasoning: 'Good placement' },
            { word: 'BIRTHDAY', row: 2, col: 0, direction: 'across', score: 80, reasoning: 'Also fine' },
          ],
        },
      ],
    });
    render(
      <ThemeWordsPanel
        grid={emptyGrid15x15}
        gridSize={15}
        onApplyPlacement={vi.fn()}
        onClose={vi.fn()}
        {...extraProps}
      />
    );
    const input = document.querySelector('input[type="file"]');
    await user.upload(input, new File(['BIRTHDAY'], 'theme.txt', { type: 'text/plain' }));
    await waitFor(() => expect(document.querySelectorAll('.apply-btn').length).toBe(2));
  };

  it('control: not paused, apply buttons and Apply All are enabled', async () => {
    await showSuggestions({});
    document.querySelectorAll('.apply-btn').forEach((b) => expect(b).not.toBeDisabled());
    expect(screen.getByRole('button', { name: /apply all best placements/i })).not.toBeDisabled();
  });

  it('paused: every .apply-btn and the Apply All button are disabled', async () => {
    await showSuggestions({ editingPaused: true });
    const buttons = document.querySelectorAll('.apply-btn');
    expect(buttons.length).toBe(2);
    buttons.forEach((b) => expect(b).toBeDisabled());
    expect(screen.getByRole('button', { name: /apply all best placements/i })).toBeDisabled();
  });
});

/**
 * novice-readiness spec 0.2.7 §3.8 (TH2b): suggestions refresh when the grid changes.
 * Plan defaults PD-6-G13 (400 ms debounce), PD-6-G14 (the panel's toast),
 * PD-6-G15 (suspended while Apply All runs), PD-6-G16 (a refetch is silent).
 */
describe('ThemeWordsPanel refetch on grid change (Task 6.13, TH2b)', () => {
  const STALE_MSG = 'Suggestions updated for the changed grid.';
  const WORDS = ['BIRTHDAY'];

  const listFor = (words, reasoning = 'Good placement') =>
    words.map((w, i) => ({
      word: w,
      length: w.length,
      suggestions: [
        { word: w, row: i * 2, col: 0, direction: 'across', score: 90, reasoning },
      ],
    }));

  const gridWith = (edit) => {
    const g = createEmptyGrid(15);
    if (edit) edit(g);
    return g;
  };

  const deferred = () => {
    let resolve;
    let reject;
    const promise = new Promise((res, rej) => {
      resolve = res;
      reject = rej;
    });
    return { promise, resolve, reject };
  };

  let suggestSpy;
  let applySpy;
  let onApply;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(api, 'themeUpload').mockResolvedValue({
      words: WORDS,
      count: WORDS.length,
      validation: { valid: true, errors: [], warnings: [] },
    });
    suggestSpy = vi
      .spyOn(api, 'themeSuggestPlacements')
      .mockResolvedValue({ suggestions: listFor(WORDS, 'First list') });
    applySpy = vi.spyOn(api, 'themeApplyPlacement').mockResolvedValue({ grid: gridWith() });
    onApply = vi.fn();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // Upload with real timers (FileReader), then switch to fake timers for the debounce.
  // fireEvent + waitFor (not user.upload): the FileReader callback then lands inside
  // waitFor's act handling, so the new tests add no `not wrapped in act` warnings.
  const uploadFile = (words) => {
    const input = document.querySelector('input[type="file"]');
    fireEvent.change(input, {
      target: { files: [new File([words.join('\n')], 'theme.txt', { type: 'text/plain' })] },
    });
  };

  const showList = async (ui, words = WORDS) => {
    const utils = render(ui);
    uploadFile(words);
    await waitFor(() => expect(document.querySelectorAll('.apply-btn').length).toBeGreaterThan(0));
    vi.useFakeTimers();
    return utils;
  };

  const panel = (grid, extra = {}) => (
    <ThemeWordsPanel
      grid={grid}
      gridSize={15}
      onApplyPlacement={onApply}
      onClose={vi.fn()}
      {...extra}
    />
  );

  const advance = (ms) =>
    act(async () => {
      await vi.advanceTimersByTimeAsync(ms);
    });

  const flush = () =>
    act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

  const base = gridWith();
  const letterChanged = (letter) => gridWith((g) => { g[0][0].letter = letter; });

  it('exports the debounce constant at the planning default', () => {
    expect(SUGGESTION_REFETCH_DEBOUNCE_MS).toBe(400);
  });

  it('upload auto-analyze records its signature: no further call without a grid change', async () => {
    await showList(panel(base));
    expect(suggestSpy).toHaveBeenCalledTimes(1);
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS * 5);
    expect(suggestSpy).toHaveBeenCalledTimes(1);
  });

  it('a letter change refetches once for the same words and replaces the list', async () => {
    const { rerender } = await showList(panel(base));
    suggestSpy.mockResolvedValueOnce({ suggestions: listFor(WORDS, 'Second list') });
    expect(screen.getByText('First list')).toBeInTheDocument();

    rerender(panel(letterChanged('X')));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS);

    expect(suggestSpy).toHaveBeenCalledTimes(2);
    const args = suggestSpy.mock.calls[1][0];
    expect(args.themeWords).toEqual(WORDS);
    expect(args.existingGrid[0][0]).toBe('X');
    expect(screen.getByText('Second list')).toBeInTheDocument();
    expect(screen.queryByText('First list')).not.toBeInTheDocument();
  });

  it('two changes inside one debounce window produce one refetch', async () => {
    const { rerender } = await showList(panel(base));
    rerender(panel(letterChanged('X')));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS - 100);
    rerender(panel(letterChanged('Y')));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS - 100);
    expect(suggestSpy).toHaveBeenCalledTimes(1);
    await advance(100);
    expect(suggestSpy).toHaveBeenCalledTimes(2);
    expect(suggestSpy.mock.calls[1][0].existingGrid[0][0]).toBe('Y');
  });

  it('a black square added refetches once', async () => {
    const { rerender } = await showList(panel(base));
    rerender(panel(gridWith((g) => { g[3][3].isBlack = true; })));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS);
    expect(suggestSpy).toHaveBeenCalledTimes(2);
    expect(suggestSpy.mock.calls[1][0].existingGrid[3][3]).toBe('#');
  });

  it('only isError / number / isThemeLocked / isHighlighted / isAutofilled changes do not refetch', async () => {
    const { rerender } = await showList(panel(base));
    rerender(
      panel(
        gridWith((g) => {
          g[0][0].isError = true;
          g[0][1].number = 7;
          g[0][2].isThemeLocked = true;
          g[0][3].isHighlighted = true;
          g[0][4].isAutofilled = true;
        })
      )
    );
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS * 5);
    expect(suggestSpy).toHaveBeenCalledTimes(1);
  });

  it('a response for an older request is dropped once a newer request has started', async () => {
    const { rerender } = await showList(panel(base));
    const d2 = deferred();
    const d3 = deferred();
    suggestSpy.mockReturnValueOnce(d2.promise).mockReturnValueOnce(d3.promise);

    rerender(panel(letterChanged('X')));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS);
    rerender(panel(letterChanged('Y')));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS);
    expect(suggestSpy).toHaveBeenCalledTimes(3);

    d2.resolve({ suggestions: listFor(WORDS, 'Stale list') });
    await flush();
    expect(screen.queryByText('Stale list')).not.toBeInTheDocument();

    d3.resolve({ suggestions: listFor(WORDS, 'Fresh list') });
    await flush();
    expect(screen.getByText('Fresh list')).toBeInTheDocument();
    expect(screen.queryByText('Stale list')).not.toBeInTheDocument();
  });

  it('a grid change before any suggestions load fetches nothing', async () => {
    const { rerender } = render(panel(base));
    vi.useFakeTimers();
    rerender(panel(letterChanged('X')));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS * 3);
    expect(suggestSpy).not.toHaveBeenCalled();
  });

  it('a grid change after a failed analyze fetches nothing', async () => {
    suggestSpy.mockRejectedValueOnce(new Error('boom'));
    const { rerender } = render(panel(base));
    uploadFile(WORDS);
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('boom'));
    vi.useFakeTimers();
    rerender(panel(letterChanged('X')));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS * 3);
    expect(suggestSpy).toHaveBeenCalledTimes(1);
  });

  it('the refetch is silent: no "Found placement suggestions" toast for it', async () => {
    const { rerender } = await showList(panel(base));
    expect(toast.success).toHaveBeenCalledWith('Found placement suggestions for 1 words!');
    toast.success.mockClear();
    rerender(panel(letterChanged('X')));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS);
    expect(suggestSpy).toHaveBeenCalledTimes(2);
    expect(toast.success).not.toHaveBeenCalled();
  });

  it('a failed refetch toasts the error, keeps the old list, and leaves it superseded', async () => {
    const { rerender } = await showList(panel(base));
    suggestSpy.mockRejectedValueOnce(new Error('refetch down'));
    rerender(panel(letterChanged('X')));
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS);
    expect(toast.error).toHaveBeenCalledWith('refetch down');
    expect(screen.getByText('First list')).toBeInTheDocument();

    await act(async () => {
      screen.getByRole('button', { name: /apply this placement/i }).click();
    });
    await flush();
    expect(applySpy).not.toHaveBeenCalled();
    expect(onApply).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(STALE_MSG);
  });

  it('grid changed, debounce pending: Apply This Placement is a no-op with the toast', async () => {
    const { rerender } = await showList(panel(base));
    rerender(panel(letterChanged('X')));
    // no timer advance: the debounce is still pending
    await act(async () => {
      screen.getByRole('button', { name: /apply this placement/i }).click();
    });
    await flush();
    expect(applySpy).not.toHaveBeenCalled();
    expect(onApply).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(STALE_MSG);
  });

  it('grid changed, debounce pending: Apply All Best Placements is a no-op with the toast', async () => {
    const { rerender } = await showList(panel(base));
    rerender(panel(letterChanged('X')));
    await act(async () => {
      screen.getByRole('button', { name: /apply all best placements/i }).click();
    });
    await flush();
    expect(applySpy).not.toHaveBeenCalled();
    expect(onApply).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(STALE_MSG);
  });

  it('grid unchanged: Apply This Placement applies as today', async () => {
    await showList(panel(base));
    await act(async () => {
      screen.getByRole('button', { name: /apply this placement/i }).click();
    });
    await flush();
    expect(applySpy).toHaveBeenCalledTimes(1);
    expect(onApply).toHaveBeenCalledTimes(1);
    expect(toast).not.toHaveBeenCalledWith(STALE_MSG);
  });

  it('Apply All: no refetch while it runs; exactly one after it ends', async () => {
    const words = ['ONE', 'TWO', 'THREE'];
    suggestSpy.mockReset();
    suggestSpy.mockResolvedValueOnce({ suggestions: listFor(words, 'First list') });
    api.themeUpload.mockResolvedValue({
      words,
      count: 3,
      validation: { valid: true, errors: [], warnings: [] },
    });
    const gridAfter = (n) => gridWith((g) => { for (let i = 0; i < n; i++) g[i][0].letter = 'A'; });
    const third = deferred();
    applySpy.mockReset();
    applySpy
      .mockResolvedValueOnce({ grid: gridAfter(1) })
      .mockResolvedValueOnce({ grid: gridAfter(2) })
      .mockReturnValueOnce(third.promise);

    const Host = () => {
      const [g, setG] = useState(base);
      return panel(g, {
        onApplyPlacement: (next) => {
          onApply(next);
          setG(next);
        },
      });
    };
    await showList(<Host />, words);
    expect(suggestSpy).toHaveBeenCalledTimes(1);
    suggestSpy.mockResolvedValue({ suggestions: listFor(words, 'Second list') });

    await act(async () => {
      screen.getByRole('button', { name: /apply all best placements/i }).click();
    });
    await flush();
    expect(onApply).toHaveBeenCalledTimes(2); // the grid prop changed twice, third apply in flight
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS * 3);
    expect(suggestSpy).toHaveBeenCalledTimes(1);

    third.resolve({ grid: gridAfter(3) });
    await flush();
    expect(onApply).toHaveBeenCalledTimes(3);
    await advance(SUGGESTION_REFETCH_DEBOUNCE_MS * 3);
    expect(suggestSpy).toHaveBeenCalledTimes(2);
    expect(screen.getAllByText('Second list')).toHaveLength(3);
    expect(screen.queryByText('First list')).not.toBeInTheDocument();
  });
});

describe('ThemeWordsPanel Apply All reports each word\'s real failure (Task 6.14, TH3)', () => {
  const UPLOAD_OK = (words) => ({
    words,
    count: words.length,
    validation: { valid: true, errors: [], warnings: [] },
  });

  // One entry per word; `sugs` overrides the single default suggestion.
  const listFor = (words, overrides = {}) =>
    words.map((w, i) => ({
      word: w,
      length: w.length,
      suggestions: overrides[w] || [
        { word: w, row: i * 2, col: 0, direction: 'across', score: 90, reasoning: 'Good placement' },
      ],
    }));

  const gridWith = (n) => {
    const g = createEmptyGrid(15);
    for (let i = 0; i < n; i++) g[i][0].letter = 'A';
    return g;
  };

  // Real client + real fetch: the apply endpoint answers per word. 'network' makes
  // fetch reject, so the component sees the client's own status-0 ApiError.
  let requested;
  const answerApply = (byWord) => {
    requested = [];
    let applied = 0;
    server.use(
      http.post('/api/theme/apply-placement', async ({ request }) => {
        const body = await request.json();
        const word = body.placement.word;
        requested.push(word);
        const a = byWord[word];
        if (a === 'network') return HttpResponse.error();
        if (a && a.empty) return new HttpResponse(null, { status: a.status });
        if (a) return HttpResponse.json(a.body, { status: a.status });
        applied += 1;
        return HttpResponse.json({ grid: gridWith(applied) });
      })
    );
  };

  const Host = ({ initial }) => {
    const [g, setG] = useState(initial);
    return <ThemeWordsPanel grid={g} gridSize={15} onApplyPlacement={setG} onClose={vi.fn()} />;
  };

  const showList = async (words, overrides) => {
    vi.spyOn(api, 'themeUpload').mockResolvedValue(UPLOAD_OK(words));
    vi.spyOn(api, 'themeSuggestPlacements').mockResolvedValue({
      suggestions: listFor(words, overrides),
    });
    const utils = render(<Host initial={createEmptyGrid(15)} />);
    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: { files: [new File([words.join('\n')], 'theme.txt', { type: 'text/plain' })] },
    });
    await waitFor(() => expect(document.querySelectorAll('.apply-btn').length).toBeGreaterThan(0));
    return utils;
  };

  const clickApplyAll = async () => {
    await act(async () => {
      screen.getByRole('button', { name: /apply all best placements/i }).click();
    });
  };

  // The summary toasts Apply All pushed (it addresses them with { id: 'apply-all' }).
  const summariesNow = (fn) =>
    fn.mock.calls.filter((c) => c[1] && c[1].id === 'apply-all').map((c) => c[0]);
  const summaries = async (fn) => {
    await waitFor(() => expect(summariesNow(fn).length).toBeGreaterThan(0));
    return summariesNow(fn);
  };

  const CONFLICT_400 = {
    status: 400,
    body: { error: 'Placement conflicts detected', conflicts: ['ALPHA at (0,0) overlaps R'] },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('a 400 conflict, a 500 and a network failure give three different reasons; N counts only the one apply', async () => {
    answerApply({
      ALPHA: CONFLICT_400,
      BETA: { status: 500, body: { error: 'boom' } },
      GAMMA: 'network',
    });
    await showList(['ALPHA', 'BETA', 'GAMMA', 'DELTA']);
    await clickApplyAll();
    expect(await summaries(toast.success)).toEqual([
      'Applied 1 theme words successfully! Skipped: ' +
        'ALPHA (skipped due to conflicts: ALPHA at (0,0) overlaps R); ' +
        'BETA (boom); GAMMA (Could not reach the server)',
    ]);
    expect(requested).toEqual(['ALPHA', 'BETA', 'GAMMA', 'DELTA']);
  });

  it('two conflict details read as the first plus (+1 more)', async () => {
    answerApply({
      ALPHA: { status: 400, body: { error: 'Placement conflicts detected', conflicts: ['a', 'b'] } },
    });
    await showList(['ALPHA', 'BETA']);
    await clickApplyAll();
    expect(await summaries(toast.success)).toEqual([
      'Applied 1 theme words successfully! Skipped: ALPHA (skipped due to conflicts: a (+1 more))',
    ]);
  });

  it('all four fail: the error toast keeps all four reasons, including an empty-body 500 as the fallback, never HTTP_500', async () => {
    answerApply({
      ALPHA: CONFLICT_400,
      BETA: { status: 500, body: { error: 'boom' } },
      GAMMA: 'network',
      DELTA: { status: 500, empty: true },
    });
    await showList(['ALPHA', 'BETA', 'GAMMA', 'DELTA']);
    await clickApplyAll();
    expect(await summaries(toast.error)).toEqual([
      'Could not apply any theme words Skipped: ' +
        'ALPHA (skipped due to conflicts: ALPHA at (0,0) overlaps R); ' +
        'BETA (boom); GAMMA (Could not reach the server); DELTA (Failed to apply placement)',
    ]);
    expect(summariesNow(toast.success)).toEqual([]);
  });

  it('words skipped without a request: no suggestions and a WARNING best suggestion give their own reasons', async () => {
    answerApply({});
    await showList(['ONE', 'TWO', 'THREE'], {
      ONE: [],
      TWO: [
        { word: 'TWO', row: 2, col: 0, direction: 'across', score: 50, reasoning: 'WARNING: crosses R' },
      ],
    });
    await clickApplyAll();
    expect(await summaries(toast.success)).toEqual([
      'Applied 1 theme words successfully! Skipped: ' +
        'ONE (no valid placement); TWO (skipped due to conflicts: WARNING: crosses R)',
    ]);
    expect(requested).toEqual(['THREE']);
  });

  it('one placement applied earlier by Apply This Placement is not counted by the Apply All that follows', async () => {
    const words = ['ALPHA', 'BETA'];
    const suggestSpy = vi.spyOn(api, 'themeSuggestPlacements');
    suggestSpy.mockResolvedValueOnce({ suggestions: listFor(words) });
    vi.spyOn(api, 'themeUpload').mockResolvedValue(UPLOAD_OK(words));
    const applySpy = vi
      .spyOn(api, 'themeApplyPlacement')
      .mockResolvedValueOnce({ grid: gridWith(1) })
      .mockResolvedValueOnce({ grid: gridWith(2) });
    render(<Host initial={createEmptyGrid(15)} />);
    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: { files: [new File([words.join('\n')], 'theme.txt', { type: 'text/plain' })] },
    });
    await waitFor(() => expect(document.querySelectorAll('.apply-btn').length).toBe(2));
    vi.useFakeTimers();

    // The single apply changes the grid prop, so the list is superseded (6.13).
    await act(async () => {
      screen.getAllByRole('button', { name: /apply this placement/i })[0].click();
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(applySpy).toHaveBeenCalledTimes(1);

    // The refetched list (BETA only) lands after the debounce; only then does Apply All run.
    suggestSpy.mockResolvedValueOnce({ suggestions: listFor(['BETA']) });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(SUGGESTION_REFETCH_DEBOUNCE_MS);
    });
    expect(suggestSpy).toHaveBeenCalledTimes(2);

    await clickApplyAll();
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(applySpy).toHaveBeenCalledTimes(2);
    // Fake timers are on here, so read the toast calls directly instead of polling.
    expect(summariesNow(toast.success)).toEqual(['Applied 1 theme words successfully!']);
  });
});

/**
 * Task 6.16 (novice-readiness spec 0.2.8 §3.8, PD-6-G12; review F1, F4, Greptile #77):
 * what the panel hands App, when it stops sending, and the request/signature snapshot.
 */
describe('ThemeWordsPanel applies against the grid it sent (Task 6.16)', () => {
  const UPLOAD_OK = (words) => ({
    words,
    count: words.length,
    validation: { valid: true, errors: [], warnings: [] },
  });
  const listFor = (words) =>
    words.map((w, i) => ({
      word: w,
      length: w.length,
      suggestions: [
        { word: w, row: i * 2, col: 0, direction: 'across', score: 90, reasoning: 'Good placement' },
      ],
    }));
  const gridWith = (n) => {
    const g = createEmptyGrid(15);
    for (let i = 0; i < n; i++) g[i][0].letter = 'A';
    return g;
  };
  const upload = (words) =>
    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: { files: [new File([words.join('\n')], 'theme.txt', { type: 'text/plain' })] },
    });
  const flush = () =>
    act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const deferred = () => {
    let resolve;
    const promise = new Promise((res) => {
      resolve = res;
    });
    return { promise, resolve };
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('single Apply hands App the grid it sent and the docId the request was sent under', async () => {
    const words = ['ALPHA'];
    vi.spyOn(api, 'themeUpload').mockResolvedValue(UPLOAD_OK(words));
    vi.spyOn(api, 'themeSuggestPlacements').mockResolvedValue({ suggestions: listFor(words) });
    vi.spyOn(api, 'themeApplyPlacement').mockResolvedValue({ grid: gridWith(1) });
    const onApply = vi.fn();
    const sent = createEmptyGrid(15);
    render(
      <ThemeWordsPanel grid={sent} gridSize={15} docId="doc-1" onApplyPlacement={onApply} onClose={vi.fn()} />
    );
    upload(words);
    await waitFor(() => expect(document.querySelectorAll('.apply-btn').length).toBe(1));
    await act(async () => {
      screen.getByRole('button', { name: /apply this placement/i }).click();
    });
    await waitFor(() => expect(onApply).toHaveBeenCalledTimes(1));
    expect(onApply.mock.calls[0][2].sentGrid).toBe(sent);
    expect(onApply.mock.calls[0][2].docId).toBe('doc-1');
  });

  it('Apply All: each word is sent the previous reply, and that reply is its sentGrid', async () => {
    const words = ['ALPHA', 'BETA'];
    vi.spyOn(api, 'themeUpload').mockResolvedValue(UPLOAD_OK(words));
    vi.spyOn(api, 'themeSuggestPlacements').mockResolvedValue({ suggestions: listFor(words) });
    const r1 = gridWith(1);
    const r2 = gridWith(2);
    vi.spyOn(api, 'themeApplyPlacement')
      .mockResolvedValueOnce({ grid: r1 })
      .mockResolvedValueOnce({ grid: r2 });
    const onApply = vi.fn();
    const sent = createEmptyGrid(15);
    render(
      <ThemeWordsPanel grid={sent} gridSize={15} docId="doc-1" onApplyPlacement={onApply} onClose={vi.fn()} />
    );
    upload(words);
    await waitFor(() => expect(document.querySelectorAll('.apply-btn').length).toBe(2));
    await act(async () => {
      screen.getByRole('button', { name: /apply all best placements/i }).click();
    });
    await waitFor(() => expect(onApply).toHaveBeenCalledTimes(2));
    expect(onApply.mock.calls[0][0]).toBe(r1);
    expect(onApply.mock.calls[0][2].sentGrid).toBe(sent);
    expect(onApply.mock.calls[1][0]).toBe(r2);
    expect(onApply.mock.calls[1][2].sentGrid).toBe(r1);
    expect(onApply.mock.calls[1][2].docId).toBe('doc-1');
  });

  it('Apply All over 3 words: closing the panel after the first reply sends no further request', async () => {
    const words = ['ALPHA', 'BETA', 'GAMMA'];
    vi.spyOn(api, 'themeUpload').mockResolvedValue(UPLOAD_OK(words));
    vi.spyOn(api, 'themeSuggestPlacements').mockResolvedValue({ suggestions: listFor(words) });
    const first = deferred();
    const applySpy = vi
      .spyOn(api, 'themeApplyPlacement')
      .mockImplementationOnce(() => first.promise)
      .mockResolvedValue({ grid: gridWith(2) });
    const { unmount } = render(
      <ThemeWordsPanel
        grid={createEmptyGrid(15)}
        gridSize={15}
        docId="doc-1"
        onApplyPlacement={vi.fn()}
        onClose={vi.fn()}
      />
    );
    upload(words);
    await waitFor(() => expect(document.querySelectorAll('.apply-btn').length).toBe(3));
    await act(async () => {
      screen.getByRole('button', { name: /apply all best placements/i }).click();
    });
    expect(applySpy).toHaveBeenCalledTimes(1);

    unmount(); // the × button
    await act(async () => {
      first.resolve({ grid: gridWith(1) });
    });
    await flush();
    await flush();
    expect(applySpy).toHaveBeenCalledTimes(1);
  });

  it('a grid edit while themeUpload is pending: the list lands superseded and one refetch runs', async () => {
    const words = ['ALPHA'];
    const up = deferred();
    vi.spyOn(api, 'themeUpload').mockReturnValue(up.promise);
    const suggest = vi
      .spyOn(api, 'themeSuggestPlacements')
      .mockResolvedValue({ suggestions: listFor(words) });
    const applySpy = vi.spyOn(api, 'themeApplyPlacement').mockResolvedValue({ grid: gridWith(1) });
    const gridA = createEmptyGrid(15);
    const gridB = createEmptyGrid(15);
    gridB[7][7].letter = 'Q';
    const props = { gridSize: 15, docId: 'doc-1', onApplyPlacement: vi.fn(), onClose: vi.fn() };
    const { rerender } = render(<ThemeWordsPanel grid={gridA} {...props} />);
    upload(words);
    await flush();
    rerender(<ThemeWordsPanel grid={gridB} {...props} />); // edited while themeUpload is pending
    await act(async () => {
      up.resolve(UPLOAD_OK(words));
    });
    await waitFor(() => expect(document.querySelectorAll('.apply-btn').length).toBe(1));
    expect(suggest).toHaveBeenCalledTimes(1);

    await act(async () => {
      screen.getByRole('button', { name: /apply this placement/i }).click();
    });
    await flush();
    expect(toast).toHaveBeenCalledWith('Suggestions updated for the changed grid.');
    expect(applySpy).not.toHaveBeenCalled();

    await act(async () => {
      await sleep(SUGGESTION_REFETCH_DEBOUNCE_MS + 150);
    });
    expect(suggest).toHaveBeenCalledTimes(2);
    expect(suggest.mock.calls[1][0].existingGrid[7][7]).toBe('Q');
  });
});
