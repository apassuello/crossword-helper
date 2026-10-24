import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';
import storage from '../lib/storage';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const renderApp = () => render(<App />, { wrapper: ToastProvider });
const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const blacks = (c) => c.querySelectorAll('rect[fill="var(--ink)"]').length;
const letters = (c) => Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);
const focusEl = (c) => c.querySelector('.xw-grid-focus');
const blankCli = () => Array.from({ length: 15 }, () => Array(15).fill('.'));
const flush = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });

let handlers;
beforeEach(() => {
  global.localStorage.getItem.mockReturnValue(null);
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({ wordlists: [{ key: 'comprehensive', name: 'Comprehensive' }] });
  vi.spyOn(api, 'startFill').mockResolvedValue({ task_id: 't1', ceiling_seconds: 300 });
  vi.spyOn(api, 'openProgress').mockImplementation((id, h) => { handlers = h; return { close() {} }; });
  vi.spyOn(storage, 'load').mockResolvedValue(null);
  vi.spyOn(storage, 'list').mockResolvedValue([]);
  vi.spyOn(storage, 'save').mockResolvedValue({ savedAt: 'x', id: 'x', name: 'n', forked: false });
});
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

// Types A at (3,3), starts a run, merges a progress grid with B at (0,0) and a black square at (14,14).
async function liveRunWithProgress(user, container, forked) {
  storage.save.mockResolvedValue({ savedAt: '2026-10-24T10:00:00.000Z', id: forked ? 'forked-id' : 'same-id', name: 'n', forked });
  await waitFor(() => expect(cells(container)).toHaveLength(225));
  await user.click(cells(container)[3 * 15 + 3]);
  fireEvent.keyDown(focusEl(container), { key: 'A' });
  await user.click(screen.getByRole('button', { name: /^autofill$/i }));
  await user.click(await screen.findByRole('button', { name: /start autofill/i }));
  await waitFor(() => expect(handlers).toBeTruthy());
  const g = blankCli(); g[3][3] = 'A'; g[0][0] = 'B'; g[14][14] = '#';
  act(() => handlers.onEvent({ status: 'running', progress: 10, data: { grid: g } }));
  expect(letters(container).sort()).toEqual(['A', 'B']);
  return g;
}

const explicitSave = async (user) => {
  await user.click(screen.getByRole('button', { name: /save grid/i }));
  await screen.findByRole('textbox');
  await user.click(screen.getByRole('button', { name: 'Save' }));
  await waitFor(() => expect(storage.save).toHaveBeenCalled());
  await flush();
};

describe('a save fork (docId change) during a live autofill run (novice-readiness spec 0.2.8 §2.3 (F2))', () => {
  for (const forked of [false, true]) {
    const tag = forked ? 'FORK' : 'control, no fork';
    it(`${tag}: error event restores the Start snapshot (spec 2.3 table)`, async () => {
      const user = userEvent.setup();
      const { container } = renderApp();
      await liveRunWithProgress(user, container, forked);
      await explicitSave(user);
      act(() => handlers.onEvent({ status: 'error', message: 'boom' }));
      expect(screen.getByText('boom')).toBeInTheDocument();
      expect(letters(container)).toEqual(['A']);
      expect(blacks(container)).toBe(0);
    });

    it(`${tag}: a progress merge after the fork still applies`, async () => {
      const user = userEvent.setup();
      const { container } = renderApp();
      const g = await liveRunWithProgress(user, container, forked);
      await explicitSave(user);
      const next = g.map((row) => row.slice()); next[0][1] = 'C';
      act(() => handlers.onEvent({ status: 'running', progress: 20, data: { grid: next } }));
      expect(letters(container).sort()).toEqual(['A', 'B', 'C']);
    });

    it(`${tag}: complete success applies the final result`, async () => {
      const user = userEvent.setup();
      const { container } = renderApp();
      const g = await liveRunWithProgress(user, container, forked);
      await explicitSave(user);
      const final = g.map((row) => row.slice()); final[0][1] = 'C';
      act(() => handlers.onEvent({ status: 'complete', data: { success: true, grid: final, slots_filled: 2, total_slots: 2 } }));
      expect(screen.getByText('Successfully filled 2/2 slots!')).toBeInTheDocument();
      expect(letters(container).sort()).toEqual(['A', 'B', 'C']);
    });

    it(`${tag}: a Keep offer survives an autosave that forks after the run ended`, async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      const { container } = renderApp();
      const g = await liveRunWithProgress(user, container, forked);
      act(() => handlers.onEvent({ status: 'complete', data: { success: false, grid: g, slots_filled: 1, total_slots: 2, fill_percentage: 50 } }));
      expect(screen.getByRole('button', { name: /keep partial fill/i })).toBeInTheDocument();
      await act(async () => vi.advanceTimersByTime(30000));
      await waitFor(() => expect(storage.save).toHaveBeenCalled());
      await act(async () => vi.advanceTimersByTime(10));
      expect(screen.getByRole('button', { name: /keep partial fill/i })).toBeInTheDocument();
    });

    it(`${tag}: AUTOSAVE-driven fork mid-run (30 s timer, no click) then error restores`, async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      const { container } = renderApp();
      await liveRunWithProgress(user, container, forked);
      await act(async () => vi.advanceTimersByTime(30000));
      await waitFor(() => expect(storage.save).toHaveBeenCalled());
      await act(async () => vi.advanceTimersByTime(10));
      act(() => handlers.onEvent({ status: 'error', message: 'boom' }));
      expect(letters(container)).toEqual(['A']);
    });
  }
});
