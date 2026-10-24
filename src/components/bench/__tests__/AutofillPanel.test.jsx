/**
 * Tests for AutofillPanel (Task 11B) — the ported Constructor's Bench autofill panel.
 *
 * Presentational-ish: owns only local UI state for the options form + the
 * wordlist fetch on mount. All lifecycle (start/cancel/reset/progress) comes
 * from `machine`, shaped exactly like `useAutofillMachine()`'s return value
 * (Task 11A) — see `src/hooks/useAutofillMachine.js`. This component does not
 * know about SSE/EventSource/the API client directly except for
 * `api.getWordlists()`.
 *
 * Grid fixtures reuse `gridFromRows` from the hooks test suite (same helper
 * `useGridGeometry.test.jsx` / `useNumbering.test.jsx` / `useAutofillMachine.test.jsx`
 * already share) so slot/empty-count semantics match production exactly.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, act } from '@testing-library/react';
import { readFileSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { AutofillPanel, getThemeEntries } from '../AutofillPanel';
import { api } from '../../../api/client';
import { gridFromRows } from '../../../hooks/__tests__/gridFixtures';

vi.mock('../../../api/client', () => ({
  api: {
    getWordlists: vi.fn(),
  },
}));

/**
 * Flush the mount-time `api.getWordlists()` microtask inside `act()` so its
 * resolution (however uninteresting to a given test) never lands outside
 * React's batching — avoids the "not wrapped in act" warning without every
 * test needing to care about the wordlist fetch.
 */
const flush = () =>
  act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });

const ALL_BLACK_4 = ['####', '####', '####', '####'];
const OPEN_4 = ['....', '....', '....', '....'];

function themedGrid() {
  const grid = gridFromRows(OPEN_4);
  // Theme-locked "ABCD" across row 0 (the whole slot, spec 0.2.7 section 2.3 Theme entries);
  // the rest stays empty/unlocked.
  'ABCD'.split('').forEach((letter, c) => {
    grid[0][c] = { ...grid[0][c], letter, isThemeLocked: true };
  });
  return grid;
}

/** Lock the listed [row, col] cells of `grid` as theme-locked (letters already in the rows). */
function lockCells(grid, cells) {
  cells.forEach(([r, c]) => {
    grid[r][c] = { ...grid[r][c], isThemeLocked: true };
  });
  return grid;
}

function baseMachine(overrides = {}) {
  return {
    state: 'idle',
    taskId: null,
    progress: 0,
    message: '',
    errorCard: null,
    start: vi.fn(),
    cancel: vi.fn(),
    reset: vi.fn(),
    keepFill: vi.fn(),
    offer: null,
    cancelPending: false,
    ...overrides,
  };
}

const WORDLISTS_RESPONSE = {
  wordlists: [
    { key: 'comprehensive', name: 'Comprehensive', category: 'core', word_count: 44000 },
    { key: 'custom/my_theme', name: 'My Theme List', category: 'custom', word_count: 120 },
  ],
};

beforeEach(() => {
  api.getWordlists.mockReset();
  api.getWordlists.mockResolvedValue(WORDLISTS_RESPONSE);
});

describe('AutofillPanel (mounted, controlled)', () => {
  it('renders idle state with the options panel, Start disabled when 0 empty slots', async () => {
    const machine = baseMachine();
    const { getByRole, getByText } = render(<AutofillPanel machine={machine} grid={gridFromRows(ALL_BLACK_4)} />);
    await flush();

    expect(getByText('Algorithm')).toBeInTheDocument();
    expect(getByText('Timeout')).toBeInTheDocument();
    expect(getByText(/Min Score/)).toBeInTheDocument();
    expect(getByText('Adaptive mode')).toBeInTheDocument();
    expect(getByText('Partial fill')).toBeInTheDocument();
    expect(getByText('Cleanup invalid words')).toBeInTheDocument();
    expect(getByText('Word Lists')).toBeInTheDocument();

    const startBtn = getByRole('button', { name: /start autofill/i });
    expect(startBtn).toBeDisabled();
  });

  it('Start click passes the docId prop to machine.start as the second argument', async () => {
    const machine = baseMachine();
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} docId="doc-9" />);
    await flush();

    fireEvent.click(getByRole('button', { name: /start autofill/i }));

    expect(machine.start).toHaveBeenCalledTimes(1);
    expect(machine.start).toHaveBeenCalledWith(
      expect.objectContaining({ themeEntries: { '(0,0,across)': 'ABCD' } }),
      'doc-9'
    );
  });

  it('Start click calls machine.start with options + themeEntries merged in', async () => {
    const machine = baseMachine();
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    fireEvent.click(getByRole('button', { name: /start autofill/i }));

    expect(machine.start).toHaveBeenCalledTimes(1);
    const arg = machine.start.mock.calls[0][0];
    expect(arg).toMatchObject({
      algorithm: 'repair',
      timeout: 300,
      minScore: 30,
      wordlists: ['comprehensive'],
      adaptiveMode: false,
      maxAdaptations: 3,
      partialFill: false,
      cleanup: false,
      themeEntries: { '(0,0,across)': 'ABCD' },
    });
  });

  // Guards the "Theme List designation is dropped before the request goes out"
  // defect, which the field-report ledger records as fixed with NO regression
  // test. The designation only earns its keep if it survives all the way into
  // machine.start — useAutofillMachine forwards it verbatim as `themeList`.
  it('designating a custom wordlist as priority theme passes themeList to machine.start', async () => {
    const machine = baseMachine();
    const { getByRole, getByLabelText, getByText } = render(
      <AutofillPanel machine={machine} grid={themedGrid()} />
    );
    await flush();

    // The priority-theme radio only appears once the custom list is selected.
    fireEvent.click(getByLabelText(/My Theme List/i));
    fireEvent.click(getByLabelText(/Priority theme list/i));

    expect(getByText(/Theme List Active:/i)).toBeInTheDocument();

    fireEvent.click(getByRole('button', { name: /start autofill/i }));
    expect(machine.start).toHaveBeenCalledTimes(1);
    expect(machine.start.mock.calls[0][0]).toMatchObject({
      themeList: 'custom/my_theme',
    });
  });

  // Deselecting the wordlist must clear the designation too, or the request
  // carries a themeList pointing at a list it no longer sends.
  it('deselecting the designated wordlist clears themeList', async () => {
    const machine = baseMachine();
    const { getByRole, getByLabelText } = render(
      <AutofillPanel machine={machine} grid={themedGrid()} />
    );
    await flush();

    fireEvent.click(getByLabelText(/My Theme List/i));
    fireEvent.click(getByLabelText(/Priority theme list/i));
    fireEvent.click(getByLabelText(/My Theme List/i));

    fireEvent.click(getByRole('button', { name: /start autofill/i }));
    expect(machine.start.mock.calls[0][0].themeList).toBeNull();
  });

  it('has no preferPersonalWords field in the rendered options or in the machine.start call', async () => {
    const machine = baseMachine();
    const { getByRole, queryByText } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(queryByText(/prefer personal/i)).toBeNull();

    fireEvent.click(getByRole('button', { name: /start autofill/i }));
    const arg = machine.start.mock.calls[0][0];
    expect(arg).not.toHaveProperty('preferPersonalWords');
  });

  it('algorithm select offers exactly repair/hybrid/beam/trie, trie labeled "Classic CSP"', async () => {
    const machine = baseMachine();
    const { container } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    const select = Array.from(container.querySelectorAll('select')).find((s) =>
      Array.from(s.options).some((o) => o.value === 'repair')
    );
    const options = Array.from(select.options);
    expect(options.map((o) => o.value)).toEqual(['repair', 'hybrid', 'beam', 'trie']);
    expect(options.find((o) => o.value === 'trie').textContent).toBe('Classic CSP');
    expect(options.find((o) => o.value === 'csp')).toBeUndefined();
  });

  it('timeout select offers exactly 60/120/300/600/1800 seconds (1/2/5/10/30 min)', async () => {
    const machine = baseMachine();
    const { container } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    const select = Array.from(container.querySelectorAll('select')).find((s) =>
      Array.from(s.options).some((o) => o.value === '300')
    );
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toEqual(['60', '120', '300', '600', '1800']);
  });

  it('running state renders the progress bar at machine.progress% with machine.message, and Cancel calls machine.cancel', async () => {
    const machine = baseMachine({ state: 'running', progress: 42, message: 'Filling grid…' });
    const { container, getByRole, getByText } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByText('Filling grid…')).toBeInTheDocument();
    const fill = container.querySelector('.xw-progress-fill');
    expect(fill).not.toBeNull();
    expect(fill.style.width).toBe('42%');

    fireEvent.click(getByRole('button', { name: /cancel/i }));
    expect(machine.cancel).toHaveBeenCalledTimes(1);
  });

  it('"Suggest Black Square" is present but disabled with the Task-20 title in running state', async () => {
    const machine = baseMachine({ state: 'running', progress: 10, message: 'Working…' });
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    const btn = getByRole('button', { name: /suggest black square/i });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('title', 'lands in Task 20');
  });

  it('"Suggest Black Square" is present but disabled with the Task-20 title in idle state', async () => {
    const machine = baseMachine();
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    const btn = getByRole('button', { name: /suggest black square/i });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('title', 'lands in Task 20');
  });

  it('submitting state shows Cancel and the click calls machine.cancel (spec 0.2.7 section 2.4)', async () => {
    const machine = baseMachine({ state: 'submitting', progress: 0, message: 'Starting autofill…' });
    const { getByRole, getByText } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByText('Starting autofill…')).toBeInTheDocument();
    fireEvent.click(getByRole('button', { name: /cancel/i }));
    expect(machine.cancel).toHaveBeenCalledTimes(1);
  });

  it('running with cancelPending: Cancel is shown and disabled', async () => {
    const machine = baseMachine({ state: 'running', progress: 10, message: 'Working…', cancelPending: true });
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByRole('button', { name: /cancel/i })).toBeDisabled();
  });

  it('submitting with cancelPending: Cancel is shown and disabled', async () => {
    const machine = baseMachine({ state: 'submitting', message: 'Starting autofill…', cancelPending: true });
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByRole('button', { name: /cancel/i })).toBeDisabled();
  });

  it('running without cancelPending: Cancel is enabled', async () => {
    const machine = baseMachine({ state: 'running', progress: 10, message: 'Working…' });
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByRole('button', { name: /cancel/i })).toBeEnabled();
  });

  it('failed state renders machine.errorCard.message and Reset calls machine.reset', async () => {
    const machine = baseMachine({ state: 'failed', errorCard: { message: 'No solution found' } });
    const { getByText, getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByText('No solution found')).toBeInTheDocument();
    fireEvent.click(getByRole('button', { name: /reset/i }));
    expect(machine.reset).toHaveBeenCalledTimes(1);
  });

  it('done state renders the final message and Reset calls machine.reset', async () => {
    const machine = baseMachine({ state: 'done', progress: 100, message: 'Successfully filled 16/16 slots!' });
    const { getByText, getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByText('Successfully filled 16/16 slots!')).toBeInTheDocument();
    fireEvent.click(getByRole('button', { name: /reset/i }));
    expect(machine.reset).toHaveBeenCalledTimes(1);
  });

  it('paused state shows machine.message and Reset, with no Pause/Resume/Discard controls', async () => {
    const machine = baseMachine({ state: 'paused', message: 'Autofill was paused outside the app.' });
    const { getByText, queryByText, getByRole, queryByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByText('Autofill was paused outside the app.')).toBeInTheDocument();
    expect(queryByText(/resume support lands/)).toBeNull();
    expect(queryByRole('button', { name: /pause/i })).toBeNull();
    expect(queryByRole('button', { name: /resume/i })).toBeNull();
    expect(queryByRole('button', { name: /discard/i })).toBeNull();

    fireEvent.click(getByRole('button', { name: /reset/i }));
    expect(machine.reset).toHaveBeenCalledTimes(1);
  });

  it('renders wordlist checkboxes from api.getWordlists() (built-in + custom, labeled sections) and toggling updates the Start payload', async () => {
    const machine = baseMachine();
    const { findByText, getByText, getByRole, getByLabelText } = render(
      <AutofillPanel machine={machine} grid={themedGrid()} />
    );

    await findByText(/Comprehensive/);
    expect(getByText('Built-in')).toBeInTheDocument();
    expect(getByText('Custom')).toBeInTheDocument();
    expect(getByLabelText(/My Theme List/)).toBeInTheDocument();

    fireEvent.click(getByLabelText(/My Theme List/));
    fireEvent.click(getByRole('button', { name: /start autofill/i }));

    const arg = machine.start.mock.calls[0][0];
    expect(arg.wordlists).toEqual(['comprehensive', 'custom/my_theme']);
  });

  it('theme-list radio appears only once its custom wordlist is selected, and designating it forwards themeList through start()', async () => {
    const machine = baseMachine();
    const { findByText, getByText, getByLabelText, getByRole, queryByLabelText } = render(
      <AutofillPanel machine={machine} grid={themedGrid()} />
    );
    await findByText(/My Theme List/);

    // Not selected yet -> no theme-designation radio.
    expect(queryByLabelText('Priority theme list')).toBeNull();

    fireEvent.click(getByLabelText(/My Theme List/));
    expect(getByLabelText('Priority theme list')).toBeInTheDocument();

    fireEvent.click(getByLabelText('Priority theme list'));
    expect(getByText('Theme List Active: My Theme List')).toBeInTheDocument();

    fireEvent.click(getByRole('button', { name: /start autofill/i }));
    const arg = machine.start.mock.calls[0][0];
    expect(arg.themeList).toBe('custom/my_theme');
  });

  it('deselecting the wordlist designated as the theme list clears themeList too', async () => {
    const machine = baseMachine();
    const { findByText, getByLabelText, getByRole } = render(
      <AutofillPanel machine={machine} grid={themedGrid()} />
    );
    await findByText(/My Theme List/);

    fireEvent.click(getByLabelText(/My Theme List/)); // select the custom wordlist
    fireEvent.click(getByLabelText('Priority theme list')); // designate it as theme
    fireEvent.click(getByLabelText(/My Theme List/)); // deselect it again

    fireEvent.click(getByRole('button', { name: /start autofill/i }));
    const arg = machine.start.mock.calls[0][0];
    expect(arg.themeList).toBeNull();
    expect(arg.wordlists).not.toContain('custom/my_theme');
  });

  it('failed state is orange-banded (--warn), a DIFFERENT surface from the red toast; done/cancelled use --good with no band', async () => {
    const failedMachine = baseMachine({ state: 'failed', errorCard: { message: 'No solution found' } });
    const { getByText: getFailedText, container: failedContainer } = render(
      <AutofillPanel machine={failedMachine} grid={themedGrid()} />
    );
    await flush();
    expect(getFailedText('No solution found')).toHaveStyle({ color: 'var(--warn)' });
    const failedPanel = failedContainer.querySelector('.xw-af-progress-panel');
    expect(failedPanel).toHaveClass('xw-af-failed');

    const doneMachine = baseMachine({ state: 'done', message: 'Successfully filled 16/16 slots!' });
    const { getByText: getDoneText, container: doneContainer } = render(
      <AutofillPanel machine={doneMachine} grid={themedGrid()} />
    );
    await flush();
    expect(getDoneText('Successfully filled 16/16 slots!')).toHaveStyle({ color: 'var(--good)' });
    const donePanel = doneContainer.querySelector('.xw-af-progress-panel');
    expect(donePanel).not.toHaveClass('xw-af-failed');
  });

  it('does not import ProgressIndicator (grep-level check)', () => {
    const here = path.dirname(fileURLToPath(import.meta.url));
    const source = readFileSync(path.join(here, '../AutofillPanel.jsx'), 'utf-8');
    const importLines = source.split('\n').filter((line) => /^\s*import\b/.test(line));
    expect(importLines.join('\n')).not.toMatch(/ProgressIndicator/);
  });
});

// allSlots (src/hooks/useGridGeometry.js) assumes a square grid, so each 1xN / Nx1 case from the
// brief is embedded in a black-padded square grid; the padding adds no slot.
describe('getThemeEntries (spec 0.2.7 section 2.3 Theme entries)', () => {
  it('1x5 row: a full theme-locked slot CAT then a black cell yields CAT, the lone white cell none', () => {
    const grid = lockCells(gridFromRows(['CAT#.', '#####', '#####', '#####', '#####']), [[0, 0], [0, 1], [0, 2]]);
    expect(getThemeEntries(grid)).toEqual({ '(0,0,across)': 'CAT' });
  });

  it('1x5 row: a partial theme-locked run (CAT then empty white cells) yields no entry', () => {
    const grid = lockCells(gridFromRows(['CAT..', '#####', '#####', '#####', '#####']), [[0, 0], [0, 1], [0, 2]]);
    expect(getThemeEntries(grid)).toEqual({});
  });

  it('1x3 row fully theme-locked but with an empty cell yields no entry', () => {
    const grid = lockCells(gridFromRows(['C.T', '###', '###']), [[0, 0], [0, 1], [0, 2]]);
    expect(getThemeEntries(grid)).toEqual({});
  });

  it('3x1 column fully theme-locked DOG yields a down entry', () => {
    const grid = lockCells(gridFromRows(['D##', 'O##', 'G##']), [[0, 0], [1, 0], [2, 0]]);
    expect(getThemeEntries(grid)).toEqual({ '(0,0,down)': 'DOG' });
  });
});

describe('AutofillPanel Start gating and hints (spec 0.2.7 section 2.3 I5, P18)', () => {
  const NO_LISTS = 'Select at least one word list';
  const NO_SLOTS = 'Clear some cells to run autofill again';

  it('Start with defaults sends minScore 30, and the slider shows 30', async () => {
    const machine = baseMachine();
    const { getByRole, getByText } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByText(/Min Score/).textContent).toBe('Min Score: 30');
    fireEvent.click(getByRole('button', { name: /start autofill/i }));
    expect(machine.start.mock.calls[0][0].minScore).toBe(30);
  });

  it('all word lists unticked: Start disabled, the word-list hint shown, the slot hint not', async () => {
    const machine = baseMachine();
    const { getByRole, getByText, queryByText, findByLabelText } = render(
      <AutofillPanel machine={machine} grid={themedGrid()} />
    );
    fireEvent.click(await findByLabelText(/Comprehensive/));

    expect(getByRole('button', { name: /start autofill/i })).toBeDisabled();
    expect(getByText(NO_LISTS)).toBeInTheDocument();
    expect(queryByText(NO_SLOTS)).toBeNull();
  });

  it('with a word list ticked the word-list hint is absent and Start is enabled', async () => {
    const machine = baseMachine();
    const { getByRole, queryByText } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(queryByText(NO_LISTS)).toBeNull();
    expect(getByRole('button', { name: /start autofill/i })).toBeEnabled();
  });

  it('no empty slot: Start disabled, the slot hint shown, the word-list hint not', async () => {
    const machine = baseMachine();
    const { getByRole, getByText, queryByText } = render(
      <AutofillPanel machine={machine} grid={gridFromRows(['ABCD', 'EFGH', 'IJKL', 'MNOP'])} />
    );
    await flush();

    expect(getByRole('button', { name: /start autofill/i })).toBeDisabled();
    expect(getByText(NO_SLOTS)).toBeInTheDocument();
    expect(queryByText(NO_LISTS)).toBeNull();
  });

  it('with an empty slot the slot hint is absent', async () => {
    const machine = baseMachine();
    const { queryByText } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(queryByText(NO_SLOTS)).toBeNull();
  });

  it('both conditions at once show both hints', async () => {
    const machine = baseMachine();
    const { getByText, findByLabelText } = render(
      <AutofillPanel machine={machine} grid={gridFromRows(['ABCD', 'EFGH', 'IJKL', 'MNOP'])} />
    );
    fireEvent.click(await findByLabelText(/Comprehensive/));

    expect(getByText(NO_LISTS)).toBeInTheDocument();
    expect(getByText(NO_SLOTS)).toBeInTheDocument();
  });
});

describe('AutofillPanel Keep offer (spec 0.2.7 section 2.3 table)', () => {
  it('keepPartialFill with counts: label "Keep partial fill (5/8 slots)", click calls keepFill(docId)', async () => {
    const machine = baseMachine({
      state: 'done',
      message: 'Partial: 5/8 slots (62%)',
      offer: { kind: 'keepPartialFill', slotsFilled: 5, totalSlots: 8 },
    });
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} docId="d" />);
    await flush();

    fireEvent.click(getByRole('button', { name: 'Keep partial fill (5/8 slots)' }));
    expect(machine.keepFill).toHaveBeenCalledTimes(1);
    expect(machine.keepFill).toHaveBeenCalledWith('d');
  });

  it('keepPartialFill without counts: label "Keep partial fill"', async () => {
    const machine = baseMachine({
      state: 'cancelled',
      message: 'Cancelled by user',
      offer: { kind: 'keepPartialFill', slotsFilled: null, totalSlots: null },
    });
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} docId="d" />);
    await flush();

    expect(getByRole('button', { name: 'Keep partial fill' })).toBeInTheDocument();
  });

  it('keepFill: label "Keep fill"', async () => {
    const machine = baseMachine({
      state: 'done',
      message: 'Filled 8/8 slots',
      offer: { kind: 'keepFill', slotsFilled: null, totalSlots: null },
    });
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} docId="d" />);
    await flush();

    expect(getByRole('button', { name: 'Keep fill' })).toBeInTheDocument();
  });

  it('failed with an errorCard and an offer: the card, the Keep button, and the click calls keepFill(docId)', async () => {
    const machine = baseMachine({
      state: 'failed',
      errorCard: { message: 'No word fits the highlighted letters.' },
      offer: { kind: 'keepPartialFill', slotsFilled: 5, totalSlots: 8 },
    });
    const { getByRole, getByText } = render(<AutofillPanel machine={machine} grid={themedGrid()} docId="d" />);
    await flush();

    expect(getByText('No word fits the highlighted letters.')).toBeInTheDocument();
    fireEvent.click(getByRole('button', { name: 'Keep partial fill (5/8 slots)' }));
    expect(machine.keepFill).toHaveBeenCalledWith('d');
  });

  it('no offer: no Keep button', async () => {
    const machine = baseMachine({ state: 'done', message: 'Successfully filled 8/8 slots!' });
    const { queryByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} docId="d" />);
    await flush();

    expect(queryByRole('button', { name: /keep/i })).toBeNull();
  });

  it('paused with an offer: the message, the Keep button and Reset', async () => {
    const machine = baseMachine({
      state: 'paused',
      message: 'Autofill was paused outside the app.',
      offer: { kind: 'keepPartialFill', slotsFilled: null, totalSlots: null },
    });
    const { getByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} docId="d" />);
    await flush();

    fireEvent.click(getByRole('button', { name: 'Keep partial fill' }));
    expect(machine.keepFill).toHaveBeenCalledWith('d');
    fireEvent.click(getByRole('button', { name: /reset/i }));
    expect(machine.reset).toHaveBeenCalledTimes(1);
  });
});
