/**
 * Two grid writes in one tick are two undo steps (novice-readiness spec 0.2.18 §3.9, "What one
 * step is"). Both calls go through the same handler props, captured at one render, as two
 * programmatic writes inside one `act()` would; a real keyboard gives each key its own flush.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, waitFor, act } from '@testing-library/react';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';
import storage from '../lib/storage';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

const captured = vi.hoisted(() => ({}));

vi.mock('../hooks/useUndoHistory', async () => {
  const actual = await vi.importActual('../hooks/useUndoHistory');
  return {
    ...actual,
    useUndoHistory: (...args) => {
      const h = actual.useUndoHistory(...args);
      captured.h = h;
      return h;
    },
  };
});
vi.mock('../components/bench/CrosswordGrid', async () => {
  const actual = await vi.importActual('../components/bench/CrosswordGrid');
  const R = await import('react');
  const W = (props) => {
    if (props) captured.grid = props;
    return R.createElement(actual.default, props);
  };
  return { ...actual, default: W };
});

const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const letters = (c) => Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);

beforeEach(() => {
  global.localStorage.getItem.mockReturnValue(null);
  for (const k of Object.keys(captured)) delete captured[k];
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({ wordlists: [{ key: 'comprehensive', name: 'Comprehensive' }] });
  vi.spyOn(storage, 'load').mockResolvedValue(null);
  vi.spyOn(storage, 'list').mockResolvedValue([]);
});
afterEach(() => { vi.restoreAllMocks(); });

describe.each([
  ['plain', React.Fragment],
  ['StrictMode', React.StrictMode],
])('two writes in one tick (%s)', (_name, Root) => {
  it('two setLetter calls in one act are two undo steps, replayed in order by redo', async () => {
    const { container } = render(<Root><App /></Root>, { wrapper: ToastProvider });
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    act(() => {
      captured.grid.onSetLetter(0, 0, 'A');
      captured.grid.onSetLetter(0, 1, 'B');
    });
    expect(letters(container)).toEqual(['A', 'B']);
    act(() => captured.h.undo());
    expect(letters(container)).toEqual(['A']);
    act(() => captured.h.undo());
    expect(letters(container)).toEqual([]);
    expect(captured.h.canUndo).toBe(false);
    act(() => captured.h.redo());
    expect(letters(container)).toEqual(['A']);
    act(() => captured.h.redo());
    expect(letters(container)).toEqual(['A', 'B']);
  });
});
