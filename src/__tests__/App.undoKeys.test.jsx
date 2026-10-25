/**
 * U.3 (novice-readiness spec 0.2.18 §3.9 "Controls"): Undo and Redo in the top bar, and the
 * document-level keys. Keys are fired on `document` or on a real element, as a browser delivers them.
 */
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

const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
const letters = (c) => Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);
const focusEl = (c) => c.querySelector('.xw-grid-focus');

beforeEach(() => {
  global.localStorage.getItem.mockReturnValue(null);
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({ wordlists: [{ key: 'comprehensive', name: 'Comprehensive' }] });
  vi.spyOn(api, 'startFill').mockImplementation(() => new Promise(() => {}));
  vi.spyOn(api, 'openProgress').mockImplementation(() => ({ close() {} }));
  vi.spyOn(storage, 'load').mockResolvedValue(null);
  vi.spyOn(storage, 'list').mockResolvedValue([]);
  vi.spyOn(storage, 'save').mockResolvedValue({ savedAt: 'x', id: 'x', name: 'n', forked: false });
});
afterEach(() => { vi.restoreAllMocks(); });

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitFor(() => expect(cells(view.container)).toHaveLength(225));
  await waitFor(() => expect(screen.getByText('Verify words').closest('button')).not.toBeDisabled());
  return { user, ...view };
};
// Types AB into the first two cells: two steps.
const typeAB = async (user, container) => {
  await user.click(cells(container)[0]);
  fireEvent.keyDown(focusEl(container), { key: 'A' });
  fireEvent.keyDown(focusEl(container), { key: 'B' });
  expect(letters(container)).toEqual(['A', 'B']);
};
const undoBtn = () => screen.getByRole('button', { name: 'Undo' });
const redoBtn = () => screen.getByRole('button', { name: 'Redo' });

describe('top-bar buttons', () => {
  it('Undo and Redo start disabled; Undo enables after an edit and undoes it; Redo then redoes it', async () => {
    const { user, container } = await boot();
    expect(undoBtn()).toBeDisabled();
    expect(redoBtn()).toBeDisabled();
    await typeAB(user, container);
    expect(undoBtn()).not.toBeDisabled();
    await user.click(undoBtn());
    expect(letters(container)).toEqual(['A']);
    expect(redoBtn()).not.toBeDisabled();
    await user.click(redoBtn());
    expect(letters(container)).toEqual(['A', 'B']);
  });

  it('both are disabled while autofill is live', async () => {
    const { user, container } = await boot();
    await typeAB(user, container);
    await user.click(screen.getByRole('button', { name: /^autofill$/i }));
    await user.click(await screen.findByRole('button', { name: /start autofill/i }));
    await waitFor(() => expect(undoBtn()).toBeDisabled());
    expect(redoBtn()).toBeDisabled();
  });
});

describe('document keys', () => {
  it.each([
    ['Ctrl+Z', { key: 'z', ctrlKey: true }],
    ['Cmd+Z', { key: 'z', metaKey: true }],
  ])('%s on document undoes and prevents the default', async (_n, init) => {
    const { user, container } = await boot();
    await typeAB(user, container);
    const notPrevented = fireEvent.keyDown(document, init);
    expect(notPrevented).toBe(false);
    expect(letters(container)).toEqual(['A']);
  });

  it.each([
    ['Ctrl+Shift+Z', { key: 'Z', ctrlKey: true, shiftKey: true }],
    ['Cmd+Shift+Z', { key: 'Z', metaKey: true, shiftKey: true }],
    ['Ctrl+Y', { key: 'y', ctrlKey: true }],
  ])('%s on document redoes and prevents the default', async (_n, init) => {
    const { user, container } = await boot();
    await typeAB(user, container);
    fireEvent.keyDown(document, { key: 'z', ctrlKey: true });
    expect(letters(container)).toEqual(['A']);
    const notPrevented = fireEvent.keyDown(document, init);
    expect(notPrevented).toBe(false);
    expect(letters(container)).toEqual(['A', 'B']);
  });

  it('Ctrl+Z on the focused grid undoes exactly one step', async () => {
    const { user, container } = await boot();
    await typeAB(user, container);
    fireEvent.keyDown(focusEl(container), { key: 'z', ctrlKey: true });
    expect(letters(container)).toEqual(['A']);
  });

  it('a Z with no modifier is not an undo', async () => {
    const { user, container } = await boot();
    await typeAB(user, container);
    fireEvent.keyDown(document, { key: 'z' });
    expect(letters(container)).toEqual(['A', 'B']);
  });

  it('Ctrl+Z is still handled after a click on a panel button moved focus out of the grid', async () => {
    const { user, container } = await boot();
    await typeAB(user, container);
    await user.click(screen.getByRole('button', { name: /^search$/i }));
    expect(document.activeElement).not.toBe(focusEl(container));
    fireEvent.keyDown(document.activeElement, { key: 'z', ctrlKey: true });
    expect(letters(container)).toEqual(['A']);
  });

  it.each([
    ['input', () => document.createElement('input')],
    ['textarea', () => document.createElement('textarea')],
    ['select', () => document.createElement('select')],
    ['contenteditable', () => {
      const d = document.createElement('div');
      d.setAttribute('contenteditable', 'true');
      return d;
    }],
  ])('is ignored, and not prevented, when the target is a %s', async (_n, make) => {
    const { user, container } = await boot();
    await typeAB(user, container);
    const el = make();
    document.body.appendChild(el);
    const notPrevented = fireEvent.keyDown(el, { key: 'z', ctrlKey: true });
    document.body.removeChild(el);
    expect(notPrevented).toBe(true);
    expect(letters(container)).toEqual(['A', 'B']);
  });

  it('does nothing while autofill is live', async () => {
    const { user, container } = await boot();
    await typeAB(user, container);
    await user.click(screen.getByRole('button', { name: /^autofill$/i }));
    await user.click(await screen.findByRole('button', { name: /start autofill/i }));
    await waitFor(() => expect(undoBtn()).toBeDisabled());
    fireEvent.keyDown(document, { key: 'z', ctrlKey: true });
    expect(letters(container)).toEqual(['A', 'B']);
  });
});
