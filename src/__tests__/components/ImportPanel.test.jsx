// novice-readiness spec 0.2.8 §3.2 Import (Q2): the confirm's Replace is the only way to import
// over content, and it is disabled while editing is paused (D1).
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImportPanel from '../../components/ImportPanel';
import { ApiError } from '../../api/client';
import { stubCheckClues, deferred } from '../importExportHelpers';

const json = JSON.stringify({ size: 3, grid: [['C', 'A', 'T'], ['.', '.', '.'], ['.', '.', '.']] });

const openConfirm = async (props) => {
  const user = userEvent.setup();
  const onImport = vi.fn();
  const view = render(<ImportPanel onImport={onImport} currentGridSize={3} gridHasContent {...props} />);
  await user.click(screen.getByRole('button', { name: /paste json/i }));
  fireEvent.change(screen.getByLabelText(/paste json data/i), { target: { value: json } });
  await user.click(screen.getByRole('button', { name: /validate json/i }));
  await user.click(await screen.findByRole('button', { name: /import grid/i }));
  return { user, onImport, view };
};

describe('ImportPanel replace confirm', () => {
  it('Replace imports (control)', async () => {
    const { user, onImport } = await openConfirm();
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    await vi.waitFor(() => expect(onImport).toHaveBeenCalledTimes(1), { timeout: 2000 });
  });

  it('Replace is disabled while editing is paused', async () => {
    const { view, onImport } = await openConfirm();
    view.rerender(
      <ImportPanel onImport={onImport} currentGridSize={3} gridHasContent editingPaused />
    );
    expect(screen.getByRole('button', { name: 'Replace' })).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------------------------
// Task 9 (clue-authoring spec 0.1.4, section 3.5 "Grid JSON file, browser import" and section 6.2
// "Import"). `api.checkClues` is stubbed by assignment: it does not exist at RED, and this block
// installs and removes it so the tests above never see it.
// ---------------------------------------------------------------------------------------------

// A file cell '' is an empty square: it goes to the route as '.', the shape `numberGrid` sends.
const FILE_GRID = [['C', 'A', 'T'], ['', '.', '#'], ['.', '.', '.']];
const SENT_GRID = [['C', 'A', 'T'], ['.', '.', '#'], ['.', '.', '.']];
const MAP = { '0,0,across': { text: 'Feline', answer: 'CAT' } };
const fileJson = (extra = {}) => JSON.stringify({ size: 3, grid: FILE_GRID, ...extra });
const IMPORT_BTN = { name: /import grid/i };
const errorText = () => document.querySelector('.error-message')?.textContent;
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Render, paste `text`, validate; the Import Grid button is on screen when this returns. */
const arrive = async (text, props = {}) => {
  const user = userEvent.setup();
  const onImport = vi.fn();
  const view = render(<ImportPanel onImport={onImport} currentGridSize={3} {...props} />);
  await user.click(screen.getByRole('button', { name: /paste json/i }));
  fireEvent.change(screen.getByLabelText(/paste json data/i), { target: { value: text } });
  await user.click(screen.getByRole('button', { name: /validate json/i }));
  await screen.findByRole('button', IMPORT_BTN);
  return { user, onImport, view };
};
const pressImport = (user) => user.click(screen.getByRole('button', IMPORT_BTN));
const imported = (onImport) =>
  vi.waitFor(() => expect(onImport).toHaveBeenCalledTimes(1), { timeout: 3000 });

describe('ImportPanel clue check (spec 3.5 browser import, 6.2 Import)', () => {
  let stub;
  beforeEach(() => {
    stub = stubCheckClues(async () => ({ success: true, statuses: {} }));
  });
  afterEach(() => stub.restore());

  it('asks the replacement confirm first: Import over content does not call the route; Replace calls it once', async () => {
    const { user } = await arrive(fileJson({ clues: MAP }), { gridHasContent: true });
    await pressImport(user);
    expect(screen.getByRole('button', { name: 'Replace' })).toBeInTheDocument();
    expect(stub.fn).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    await vi.waitFor(() => expect(stub.fn).toHaveBeenCalledTimes(1), { timeout: 3000 });
  });

  it.each([
    ['holds a map', MAP],
    ['holds {}', {}],
    ['holds null', null],
  ])('a file whose `clues` key %s calls the route with exactly {size, grid, clues}', async (_n, clues) => {
    const { user, onImport } = await arrive(fileJson({ clues }));
    await pressImport(user);
    await vi.waitFor(() => expect(stub.fn).toHaveBeenCalledTimes(1), { timeout: 3000 });
    const arg = stub.fn.mock.calls[0][0];
    expect(Object.keys(arg).sort()).toEqual(['clues', 'grid', 'size']);
    expect(arg.size).toBe(3);
    expect(arg.grid).toStrictEqual(SENT_GRID);
    expect(arg.clues).toStrictEqual(clues);
    await imported(onImport);
  });

  it('a file with no `clues` key makes no request, and onImport receives clues of {}', async () => {
    const { user, onImport } = await arrive(fileJson());
    await pressImport(user);
    await imported(onImport);
    expect(stub.fn).not.toHaveBeenCalled();
    expect(onImport.mock.calls[0][0].clues).toStrictEqual({});
  });

  it("a valid reply: onImport receives the file's map, exactly (not the reply's statuses)", async () => {
    stub.fn.mockResolvedValue({ success: true, statuses: { '0,0,across': 'ok' } });
    const { user, onImport } = await arrive(fileJson({ clues: MAP }));
    await pressImport(user);
    await imported(onImport);
    expect(onImport.mock.calls[0][0].clues).toStrictEqual(MAP);
  });

  it('a 400 shows the error message exactly and imports nothing', async () => {
    const message = 'Invalid clue "0,0,across": text must be 1 to 200 characters.';
    stub.fn.mockRejectedValue(new ApiError({ status: 400, code: 'INVALID_CLUES', message }));
    const { user, onImport } = await arrive(fileJson({ clues: MAP }));
    await pressImport(user);
    await vi.waitFor(() => expect(errorText()).toBe(`Error: ${message}`), { timeout: 3000 });
    await pause(600); // past ImportPanel's 300 ms timer
    expect(onImport).not.toHaveBeenCalled();
  });

  it.each([
    ['a network failure', { status: 0, code: 'NETWORK', message: 'Failed to fetch' }, 'Failed to fetch'],
    ['a 500', { status: 500, code: 'INTERNAL_ERROR', message: 'Clue check failed' }, 'Clue check failed'],
  ])('%s refuses with `Could not check the clues: <message>.` and imports nothing', async (_n, init, text) => {
    stub.fn.mockRejectedValue(new ApiError(init));
    const { user, onImport } = await arrive(fileJson({ clues: MAP }));
    await pressImport(user);
    await vi.waitFor(
      () => expect(errorText()).toBe(`Error: Could not check the clues: ${text}.`),
      { timeout: 3000 }
    );
    await pause(600);
    expect(onImport).not.toHaveBeenCalled();
  });

  it.each([
    ['a 400', { status: 400, code: 'INVALID_CLUES', message: 'Invalid clue "0,0,across".' }, 'Error: Invalid clue "0,0,across".'],
    ['a network failure', { status: 0, code: 'NETWORK', message: 'Failed to fetch' }, 'Error: Could not check the clues: Failed to fetch.'],
  ])('after %s the panel can retry: Import Grid is enabled and reads `Import Grid`', async (_n, init, text) => {
    stub.fn.mockRejectedValue(new ApiError(init));
    const { user } = await arrive(fileJson({ clues: MAP }));
    await pressImport(user);
    await vi.waitFor(() => expect(errorText()).toBe(text), { timeout: 3000 });
    const button = screen.getByRole('button', { name: /import grid|importing/i });
    expect(button).toBeEnabled();
    expect(button).toHaveTextContent(/^Import Grid$/);
  });

  it('a retry after a failure clears the old message while the retry\'s check runs', async () => {
    const held = deferred();
    stub.fn.mockRejectedValueOnce(new ApiError({ status: 400, code: 'INVALID_CLUES', message: 'Bad clue.' }));
    stub.fn.mockImplementationOnce(() => held.promise);
    const { user } = await arrive(fileJson({ clues: MAP }));
    await pressImport(user);
    await vi.waitFor(() => expect(errorText()).toBe('Error: Bad clue.'), { timeout: 3000 });
    await vi.waitFor(() => expect(screen.getByRole('button', IMPORT_BTN)).toBeEnabled());
    await pressImport(user);
    await vi.waitFor(() => expect(stub.fn).toHaveBeenCalledTimes(2), { timeout: 3000 });
    expect(errorText()).toBeUndefined();
    held.resolve({ success: true, statuses: {} });
  });

  describe('token: the replacement count at the confirm (spec 3.5 ruling 2026-11-01)', () => {
    it("with a confirm, onImport's token is beginImport's value at Replace, not before and not after", async () => {
      const held = deferred();
      stub.fn.mockImplementation(() => held.promise);
      let current = 5;
      const beginImport = vi.fn(() => current);
      const { user, onImport } = await arrive(fileJson({ clues: MAP }), {
        gridHasContent: true,
        beginImport,
      });
      await pressImport(user); // the confirm opens
      current = 6;
      await user.click(screen.getByRole('button', { name: 'Replace' }));
      await vi.waitFor(() => expect(stub.fn).toHaveBeenCalledTimes(1), { timeout: 3000 });
      current = 7; // the document is replaced while the check waits
      held.resolve({ success: true, statuses: {} });
      await imported(onImport);
      expect(onImport.mock.calls[0][0].token).toBe(6);
    });

    it("with no confirm, onImport's token is beginImport's value at the click, not after", async () => {
      const held = deferred();
      stub.fn.mockImplementation(() => held.promise);
      let current = 5;
      const beginImport = vi.fn(() => current);
      const { user, onImport } = await arrive(fileJson({ clues: MAP }), { beginImport });
      await pressImport(user);
      await vi.waitFor(() => expect(stub.fn).toHaveBeenCalledTimes(1), { timeout: 3000 });
      current = 6;
      held.resolve({ success: true, statuses: {} });
      await imported(onImport);
      expect(onImport.mock.calls[0][0].token).toBe(5);
    });
  });
});
