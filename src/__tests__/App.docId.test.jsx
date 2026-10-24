/**
 * Task 4.2: the save document is keyed on a minted docId, and its cells are the
 * saved form (isAutofilled carried, isBlocked absent).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App, { contentSigOf } from '../App';
import { ToastProvider } from '../components/bench/Toast';
import storage from '../lib/storage';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  }),
  Toaster: () => null,
}));

const renderApp = () => render(<App />, { wrapper: ToastProvider });
const cells = (container) => container.querySelectorAll('rect[fill="transparent"]');

const cell = (over = {}) => ({
  letter: 'A',
  isBlack: false,
  isThemeLocked: false,
  number: null,
  isError: false,
  ...over,
});

describe('contentSigOf', () => {
  it('differs when only isAutofilled is flipped', () => {
    expect(contentSigOf(1, [[cell({ isAutofilled: false })]])).not.toBe(
      contentSigOf(1, [[cell({ isAutofilled: true })]])
    );
  });

  it('is identical when only isBlocked is flipped', () => {
    expect(contentSigOf(1, [[cell({ isBlocked: false })]])).toBe(
      contentSigOf(1, [[cell({ isBlocked: true })]])
    );
  });

  it('treats an absent isAutofilled as false', () => {
    expect(contentSigOf(1, [[cell()]])).toBe(contentSigOf(1, [[cell({ isAutofilled: false })]]));
  });

  it('treats a non-true isAutofilled (undefined/null) as false but true as true', () => {
    expect(contentSigOf(1, [[cell({ isAutofilled: null })]])).toBe(contentSigOf(1, [[cell()]]));
    expect(contentSigOf(1, [[cell({ isAutofilled: true })]])).not.toBe(contentSigOf(1, [[cell()]]));
  });

  it('keeps a null grid signature', () => {
    expect(JSON.parse(contentSigOf(3, null))).toEqual({ size: 3, cells: null });
  });
});

describe('App document id and save document', () => {
  let saveSpy;
  beforeEach(() => {
    global.localStorage.getItem.mockReturnValue(null);
    saveSpy = vi.spyOn(storage, 'save').mockResolvedValue({ savedAt: '2026-10-24T00:00:00.000Z' });
  });
  afterEach(() => {
    saveSpy.mockRestore();
  });

  const importViaPaste = async (user, gridJson) => {
    await user.click(screen.getByRole('button', { name: /^import$/i }));
    await user.click(screen.getByRole('button', { name: /paste json/i }));
    fireEvent.change(screen.getByLabelText(/paste json data/i), {
      target: { value: JSON.stringify(gridJson) },
    });
    await user.click(screen.getByRole('button', { name: /validate json/i }));
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /import grid/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /import grid/i }));
  };

  it('a grid import mints a new doc.id: Save before and after carry different non-empty ids', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));

    await user.click(screen.getByRole('button', { name: /save grid/i }));
    await waitFor(() => expect(saveSpy).toHaveBeenCalledTimes(1));

    const grid = Array.from({ length: 5 }, () => Array(5).fill('.'));
    grid[0][0] = 'C';
    await importViaPaste(user, { size: 5, grid });
    await waitFor(() => expect(cells(container)).toHaveLength(25), { timeout: 3000 });

    await user.click(screen.getByRole('button', { name: /save grid/i }));
    await waitFor(() => expect(saveSpy).toHaveBeenCalledTimes(2));

    const first = saveSpy.mock.calls[0][0].id;
    const second = saveSpy.mock.calls[1][0].id;
    expect(typeof first).toBe('string');
    expect(first.length).toBeGreaterThan(0);
    expect(typeof second).toBe('string');
    expect(second.length).toBeGreaterThan(0);
    expect(second).not.toBe(first);
  });

  it('typing does not change doc.id: two Saves around an edit carry the same id', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));

    await user.click(screen.getByRole('button', { name: /save grid/i }));
    await waitFor(() => expect(saveSpy).toHaveBeenCalledTimes(1));

    await user.click(cells(container)[0]);
    await user.keyboard('A');
    await user.click(screen.getByRole('button', { name: /save grid/i }));
    await waitFor(() => expect(saveSpy).toHaveBeenCalledTimes(2));

    expect(saveSpy.mock.calls[1][0].id).toBe(saveSpy.mock.calls[0][0].id);
  });

  it('Save after typing a letter saves cells that carry isAutofilled and no isBlocked key', async () => {
    const user = userEvent.setup();
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));

    await user.click(cells(container)[0]);
    await user.keyboard('A');
    await user.click(screen.getByRole('button', { name: /save grid/i }));
    await waitFor(() => expect(saveSpy).toHaveBeenCalledTimes(1));

    const doc = saveSpy.mock.calls[0][0];
    expect(doc.grid[0][0].letter).toBe('A');
    const all = doc.grid.flat();
    expect(all).toHaveLength(225);
    all.forEach((c) => {
      expect(c).toHaveProperty('isAutofilled', false);
      expect(c).not.toHaveProperty('isBlocked');
    });
  });
});
