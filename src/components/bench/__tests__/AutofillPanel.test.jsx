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
import { AutofillPanel } from '../AutofillPanel';
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
  // Theme-locked "AB" across row 0 (cols 0-1); rest stays empty/unlocked.
  grid[0][0] = { ...grid[0][0], letter: 'A', isThemeLocked: true };
  grid[0][1] = { ...grid[0][1], letter: 'B', isThemeLocked: true };
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
      minScore: 50,
      wordlists: ['comprehensive'],
      adaptiveMode: false,
      maxAdaptations: 3,
      partialFill: false,
      cleanup: false,
      themeEntries: { '(0,0,across)': 'AB' },
    });
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

  it('submitting state has no Cancel button (no cancel/reset edge)', async () => {
    const machine = baseMachine({ state: 'submitting', progress: 0, message: 'Starting autofill…' });
    const { queryByRole, getByText } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByText('Starting autofill…')).toBeInTheDocument();
    expect(queryByRole('button', { name: /cancel/i })).toBeNull();
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

  it('paused state renders the exact stub text and Reset, with no Pause/Resume/Discard controls', async () => {
    const machine = baseMachine({ state: 'paused', message: 'Autofill paused - state saved' });
    const { getByText, getByRole, queryByRole } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);
    await flush();

    expect(getByText('paused — resume support lands with F11')).toBeInTheDocument();
    expect(queryByRole('button', { name: /pause/i })).toBeNull();
    expect(queryByRole('button', { name: /resume/i })).toBeNull();
    expect(queryByRole('button', { name: /discard/i })).toBeNull();

    fireEvent.click(getByRole('button', { name: /reset/i }));
    expect(machine.reset).toHaveBeenCalledTimes(1);
  });

  it('renders wordlist checkboxes from api.getWordlists() (built-in + custom) and toggling updates the Start payload', async () => {
    const machine = baseMachine();
    const { findByText, getByRole, getByLabelText } = render(<AutofillPanel machine={machine} grid={themedGrid()} />);

    await findByText(/Comprehensive/);
    expect(getByLabelText(/My Theme List/)).toBeInTheDocument();

    fireEvent.click(getByLabelText(/My Theme List/));
    fireEvent.click(getByRole('button', { name: /start autofill/i }));

    const arg = machine.start.mock.calls[0][0];
    expect(arg.wordlists).toEqual(['comprehensive', 'custom/my_theme']);
  });

  it('does not import ProgressIndicator or BlackSquareSuggestions (grep-level check)', () => {
    const here = path.dirname(fileURLToPath(import.meta.url));
    const source = readFileSync(path.join(here, '../AutofillPanel.jsx'), 'utf-8');
    const importLines = source.split('\n').filter((line) => /^\s*import\b/.test(line));
    expect(importLines.join('\n')).not.toMatch(/ProgressIndicator/);
    expect(importLines.join('\n')).not.toMatch(/BlackSquareSuggestions/);
  });
});
