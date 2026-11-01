/**
 * Task 8 (clue-authoring spec 0.1.4, Decision 5 and sections 4.2, 4.5, 4.6, 5.4, 5.5, 6.2
 * "Lifecycle", "Confirm", "Gating"): when the clues are replaced, when a replacement asks first,
 * the interim import rule, a draft discarded with its document, and the Clues panel under a live
 * run. Real App, rail, Grid panel, Import panel and Clues panel; storage and the API are spied.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import storage from '../lib/storage';
import {
  Q15,
  DIRTY,
  cells,
  letters,
  entryOf,
  staleAndOrphanEntry,
  spyApp,
  waitForBlank15,
  openClues,
  openTool,
  clueInputs,
  typeDraft,
  writeClue,
  leave,
  undoBtn,
  saveGrid,
  savedDoc,
} from './appClues';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

let startFillD;
const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

beforeEach(() => {
  startFillD = deferred();
  spyApp({ startFill: () => startFillD.promise });
});
afterEach(() => {
  vi.restoreAllMocks();
});

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitForBlank15(view.container);
  return { user, ...view };
};
const rowOf = (name) => screen.getByText(name).closest('li');
const pressOpenSaved = (user) =>
  act(async () => {
    await user.click(screen.getByRole('button', { name: 'Open saved' }));
  });
const REPLACE = () => screen.queryByRole('button', { name: 'Replace' });

/** A blank 15x15 with one committed clue, the Grid tool open. */
const withOneClue = async (user) => {
  await openClues(user);
  await writeClue(user, clueInputs()[0], 'Alpha');
  await openTool(user, 'Grid');
};

describe('New grid and a size change start with no clues (spec 4.2)', () => {
  it.each([
    ['a size change (11x11)', '11×11', 22],
    ['the same size (15x15)', '15×15', 30],
  ])('%s: confirming the replacement leaves every row empty and the history empty', async (_n, label, rows) => {
    const { user } = await boot();
    await withOneClue(user);
    await user.click(screen.getByRole('button', { name: label }));
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    await openClues(user);
    expect(clueInputs()).toHaveLength(rows);
    expect(clueInputs().every((i) => i.value === '')).toBe(true);
    expect(undoBtn()).toBeDisabled();
    expect(screen.queryByText(DIRTY)).toBeNull();
  });

  it('a new grid is saved with an empty clue map', async () => {
    const { user } = await boot();
    await withOneClue(user);
    await user.click(screen.getByRole('button', { name: '11×11' }));
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(savedDoc().clues).toEqual({});
  });
});

describe('the replacement confirm counts clues (spec 4.5; mutation: the replacement predicate ignores clues)', () => {
  it('New grid asks on a white grid with a clue, and replaces nothing until confirmed', async () => {
    const { user, container } = await boot();
    await withOneClue(user);
    await user.click(screen.getByRole('button', { name: '11×11' }));
    expect(REPLACE()).toBeInTheDocument();
    expect(cells(container)).toHaveLength(225);
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(cells(container)).toHaveLength(225);
    await openClues(user);
    expect(clueInputs()[0]).toHaveValue('Alpha');
  });

  it('control: New grid on a white grid with no clue does not ask', async () => {
    const { user, container } = await boot();
    await openTool(user, 'Grid');
    await user.click(screen.getByRole('button', { name: '11×11' }));
    expect(REPLACE()).toBeNull();
    await waitFor(() => expect(cells(container)).toHaveLength(121));
  });

  it('Open saved asks on a white grid with a clue, and reads nothing until confirmed', async () => {
    const { user, container } = await boot();
    await withOneClue(user);
    storage.list.mockResolvedValue([entryOf('G', 'Gee', 15, { '1,1': { letter: 'F' } })]);
    await pressOpenSaved(user);
    await screen.findByText('Gee');
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Open' }));
    expect(REPLACE()).toBeInTheDocument();
    expect(storage.list).not.toHaveBeenCalledWith({ ordered: true });
    expect(letters(container)).toEqual([]);
    await user.click(REPLACE());
    await waitFor(() => expect(letters(container)).toEqual(['F']));
  });

  it('control: Open saved on a white grid with no clue does not ask', async () => {
    const { user, container } = await boot();
    await openTool(user, 'Grid');
    storage.list.mockResolvedValue([entryOf('G', 'Gee', 15, { '1,1': { letter: 'F' } })]);
    await pressOpenSaved(user);
    await screen.findByText('Gee');
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Open' }));
    await waitFor(() => expect(letters(container)).toEqual(['F']));
    expect(REPLACE()).toBeNull();
  });

  it('Import asks on a white grid with a clue (App\'s prop to the Import panel)', async () => {
    const { user, container } = await boot();
    await withOneClue(user);
    await importViaPaste(user, 5, { ask: true });
    expect(cells(container)).toHaveLength(225);
  });
});

// ImportPanel validates a pasted grid in the browser and applies it after a 300 ms timer.
const importViaPaste = async (user, size, { ask }) => {
  const grid = Array.from({ length: size }, () => Array(size).fill('.'));
  await user.click(screen.getByRole('button', { name: /^import$/i }));
  await user.click(screen.getByRole('button', { name: /paste json/i }));
  fireEvent.change(screen.getByLabelText(/paste json data/i), {
    target: { value: JSON.stringify({ size, grid }) },
  });
  await user.click(screen.getByRole('button', { name: /validate json/i }));
  await waitFor(() => {
    expect(screen.getByRole('button', { name: /import grid/i })).toBeInTheDocument();
  });
  await user.click(screen.getByRole('button', { name: /import grid/i }));
  if (ask) {
    expect(await screen.findByRole('button', { name: 'Replace' })).toBeInTheDocument();
  }
};

describe('Import applies no clues until Task 9 (controller ruling 2026-11-01; spec 3.5: a file with no `clues` key applies {})', () => {
  it('after writing a clue, an import leaves the document with no clues', async () => {
    const { user, container } = await boot();
    await withOneClue(user);
    await importViaPaste(user, 5, { ask: true });
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    await waitFor(() => expect(cells(container)).toHaveLength(25), { timeout: 3000 });
    await openClues(user);
    expect(clueInputs()).toHaveLength(10);
    expect(clueInputs().every((i) => i.value === '')).toBe(true);
    // the imported document is born clean, with an empty history
    expect(screen.queryByText(DIRTY)).toBeNull();
    expect(undoBtn()).toBeDisabled();
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(savedDoc().clues).toEqual({});
  });

  it('a same-size import over a clue also leaves none', async () => {
    const { user, container } = await boot();
    await withOneClue(user);
    await importViaPaste(user, 15, { ask: true });
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    await waitFor(() => expect(screen.queryByText(/^Import Grid$/)).toBeNull(), { timeout: 3000 });
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    await openClues(user);
    expect(clueInputs().every((i) => i.value === '')).toBe(true);
    expect(screen.queryByText(DIRTY)).toBeNull();
  });
});

describe('a draft is discarded when the document is replaced (spec 5.4; An Open that waits, 4.6)', () => {
  it('a draft open in the Clues panel while a confirmed Open lands never reaches the opened document', async () => {
    const { user, container } = await boot();
    const opened = entryOf('O', 'Opened', 15, { '1,1': { letter: 'F' } }, {
      clues: { '1,0,across': { text: 'Opened clue', answer: `?F${'?'.repeat(13)}` } },
    });
    const held = deferred();
    storage.list.mockImplementation((opts) =>
      opts && opts.ordered ? held.promise : Promise.resolve([opened])
    );
    await withOneClue(user); // the document has a clue, so Open asks
    await pressOpenSaved(user);
    await screen.findByText('Opened');
    await user.click(within(rowOf('Opened')).getByRole('button', { name: 'Open' }));
    await user.click(screen.getByRole('button', { name: 'Replace' }));
    expect(storage.list).toHaveBeenCalledWith({ ordered: true }); // the read is held

    // while it waits: the Clues tool, and a draft that is not committed
    await openClues(user);
    expect(clueInputs()[0]).toHaveValue('Alpha');
    const draftInput = clueInputs()[2];
    await typeDraft(user, draftInput, 'Leaked');
    expect(draftInput).toHaveValue('Leaked');

    // the read lands: the Open replaces the document
    await act(async () => {
      held.resolve([opened]);
    });
    await waitFor(() => expect(letters(container)).toEqual(['F']));
    expect(screen.getByDisplayValue('Opened clue')).toBeInTheDocument();
    expect(screen.queryByDisplayValue('Alpha')).toBeNull();
    // the draft went with the old document
    expect(screen.queryByDisplayValue('Leaked')).toBeNull();

    // and leaving the field now commits nothing into the opened document
    await leave(draftInput);
    expect(screen.queryByDisplayValue('Leaked')).toBeNull();
    expect(screen.queryByText(DIRTY)).toBeNull();
    expect(undoBtn()).toBeDisabled();
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(savedDoc().clues).toEqual(opened.clues);
  });
});

describe('the panel under a live run (spec 5.5, 4.4)', () => {
  it('control: with no run live the inputs, Keep and Delete are enabled', async () => {
    storage.load.mockResolvedValue(staleAndOrphanEntry());
    const { user } = await boot();
    await screen.findByText(/^Restored "Stale"/);
    await openClues(user);
    expect(clueInputs().length).toBeGreaterThan(0);
    expect(clueInputs().every((i) => !i.disabled)).toBe(true);
    expect(screen.getByRole('button', { name: 'Keep' })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: 'Delete' })).not.toBeDisabled();
  });

  it('during a run, every input, Keep and Delete are disabled', async () => {
    storage.load.mockResolvedValue(staleAndOrphanEntry());
    const { user } = await boot();
    await screen.findByText(/^Restored "Stale"/);
    await openTool(user, 'Autofill');
    await user.click(await screen.findByRole('button', { name: /start autofill/i }));
    await waitFor(() =>
      expect(screen.getByText('Editing is paused while autofill runs.')).toBeInTheDocument()
    );
    await openClues(user);
    expect(clueInputs().length).toBeGreaterThan(0);
    expect(clueInputs().every((i) => i.disabled)).toBe(true);
    expect(screen.getByRole('button', { name: 'Keep' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled();
  });

  it('when the run ends the controls are enabled again', async () => {
    storage.load.mockResolvedValue(staleAndOrphanEntry());
    const { user } = await boot();
    await screen.findByText(/^Restored "Stale"/);
    await openTool(user, 'Autofill');
    await user.click(await screen.findByRole('button', { name: /start autofill/i }));
    await waitFor(() =>
      expect(screen.getByText('Editing is paused while autofill runs.')).toBeInTheDocument()
    );
    await openClues(user);
    await act(async () => {
      startFillD.reject(Object.assign(new Error('boom'), { code: 'X' }));
    });
    await waitFor(() => expect(clueInputs().every((i) => !i.disabled)).toBe(true));
    expect(screen.getByRole('button', { name: 'Keep' })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: 'Delete' })).not.toBeDisabled();
  });
});
