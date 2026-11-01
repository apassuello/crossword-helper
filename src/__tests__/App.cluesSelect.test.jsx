/**
 * Task 8, fix cycle 1, M1 (clue-authoring spec 0.1.4, section 5.2 "selecting a row selects its
 * entry"): the panel's `onSelect(row, col, direction)` reaches App's selection with the direction,
 * so a Down row's number selects the Down entry, not the Across one that starts at the same square.
 * Real App, rail and Clues panel; the selected row is the one carrying the `on` class.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { spyApp, waitForBlank15, openClues, clueInputs } from './appClues';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

beforeEach(() => spyApp());
afterEach(() => {
  vi.restoreAllMocks();
});

const rowEl = (input) => input.closest('.xw-clue-row');
const numberBtn = (input) => rowEl(input).querySelector('button.xw-clue-num');

describe('the panel selects its entry with the right direction (M1)', () => {
  it('clicking the number of the first Down row selects that Down row, not the Across row at (0,0)', async () => {
    const user = userEvent.setup();
    const view = render(<App />, { wrapper: ToastProvider });
    await waitForBlank15(view.container);
    await openClues(user);
    expect(clueInputs()).toHaveLength(30);
    const across = clueInputs()[0]; // 1 Across, starts at (0,0)
    const down = clueInputs()[15]; // 1 Down, starts at (0,0) too

    await user.click(numberBtn(down));
    expect(rowEl(down)).toHaveClass('on');
    expect(rowEl(across)).not.toHaveClass('on');

    await user.click(numberBtn(across));
    expect(rowEl(across)).toHaveClass('on');
    expect(rowEl(down)).not.toHaveClass('on');
  });
});
