/**
 * Task 8 (clue-authoring spec 0.1.4, Decision 5 and sections 3.5, 4.1, 4.2, 6.2 "Save" and
 * "Lifecycle"): clues are part of the saved document and of its dirty state. Real App, rail, Grid
 * panel, Clues panel and save machine; storage and the API are spied.
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
  focusEl,
  entryOf,
  spyApp,
  waitForBlank15,
  openClues,
  openTool,
  clueInputs,
  writeClue,
  undoBtn,
  saveGrid,
  savedDoc,
} from './appClues';
import { saveArg } from './saveArgs';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

beforeEach(() => spyApp());
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const renderApp = () => render(<App />, { wrapper: ToastProvider });
const boot = async () => {
  const user = userEvent.setup();
  const view = renderApp();
  await waitForBlank15(view.container);
  return { user, ...view };
};
const advance = (ms) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
const rowOf = (name) => screen.getByText(name).closest('li');
const pressOpenSaved = (user) =>
  act(async () => {
    await user.click(screen.getByRole('button', { name: 'Open saved' }));
  });

describe('dirty state reads the document signature (spec 4.1; mutation: isDirty reads the grid signature)', () => {
  it('a commit makes the document dirty and a save makes it clean', async () => {
    const { user } = await boot();
    await openClues(user);
    expect(screen.queryByText(DIRTY)).toBeNull();
    await writeClue(user, clueInputs()[0], 'Alpha');
    expect(screen.getByText(DIRTY)).toBeInTheDocument();
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText(/^saved locally/)).toBeInTheDocument());
    expect(screen.queryByText(DIRTY)).toBeNull();
  });

  it('after a save, a commit is dirty again and undoing it returns to the saved label', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await saveGrid(user);
    await waitFor(() => expect(screen.getByText(/^saved locally/)).toBeInTheDocument());
    await writeClue(user, clueInputs()[0], 'Beta');
    expect(screen.getByText(DIRTY)).toBeInTheDocument();
    await user.click(undoBtn());
    expect(clueInputs()[0]).toHaveValue('Alpha');
    expect(screen.queryByText(DIRTY)).toBeNull();
    expect(screen.getByText(/^saved locally/)).toBeInTheDocument();
  });

  it('Keep is a change of the document too', async () => {
    storage.load.mockResolvedValue(
      entryOf('K', 'Keep', 15, {}, { clues: { '0,0,across': { text: 'Old', answer: `A${'?'.repeat(14)}` } } })
    );
    const { user } = await boot();
    await screen.findByText(/^Restored "Keep"/);
    await openClues(user);
    expect(screen.queryByText(DIRTY)).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Keep' }));
    expect(screen.getByText(DIRTY)).toBeInTheDocument();
  });
});

describe('the saved document carries clues (spec 3.5)', () => {
  it('Save writes the clue map under `clues`, keyed by entry start and direction, with the entry pattern as answer', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await writeClue(user, clueInputs()[15], '  Bravo  '); // the first Down row, trimmed
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(savedDoc().clues).toEqual({
      '0,0,across': { text: 'Alpha', answer: Q15 },
      '0,0,down': { text: 'Bravo', answer: Q15 },
    });
  });

  it('a document with no clues is saved with an empty map', async () => {
    const { user } = await boot();
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(savedDoc().clues).toEqual({});
  });

  it("a clue's answer is the live pattern of its entry at the commit", async () => {
    const { user, container } = await boot();
    await user.click(cells(container)[0]);
    fireEvent.keyDown(focusEl(container), { key: 'C' });
    fireEvent.keyDown(focusEl(container), { key: 'A' });
    expect(letters(container)).toEqual(['C', 'A']);
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(savedDoc().clues).toEqual({ '0,0,across': { text: 'Alpha', answer: `CA${'?'.repeat(13)}` } });
  });

  it('the pagehide save carries the clues', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await act(async () => {
      window.dispatchEvent(new Event('pagehide'));
      await Promise.resolve();
    });
    expect(storage.saveSync).toHaveBeenCalledTimes(1);
    expect(storage.saveSync.mock.calls[0][0].clues).toEqual({
      '0,0,across': { text: 'Alpha', answer: Q15 },
    });
  });
});

describe('Open restores clues (spec 3.5, 4.2)', () => {
  const withClues = () =>
    entryOf('G', 'Gee', 15, { '1,1': { letter: 'F' } }, {
      clues: { '1,0,across': { text: 'Opened clue', answer: `?F${'?'.repeat(13)}` } },
    });

  it('Open saved shows the entry\'s clues in the panel and saves them back', async () => {
    const { user, container } = await boot();
    storage.list.mockResolvedValue([withClues()]);
    await pressOpenSaved(user);
    await screen.findByText('Gee');
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Open' }));
    await waitFor(() => expect(letters(container)).toEqual(['F']));
    await openClues(user);
    expect(clueInputs()[1]).toHaveValue('Opened clue');
    expect(screen.queryByText(DIRTY)).toBeNull();
    expect(undoBtn()).toBeDisabled(); // history ends with the document
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(savedDoc().clues).toEqual(withClues().clues);
  });

  it('an entry with no `clues` opens with none', async () => {
    const { user, container } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await openTool(user, 'Grid');
    storage.list.mockResolvedValue([entryOf('G', 'Gee', 15, { '1,1': { letter: 'F' } })]);
    await pressOpenSaved(user);
    await screen.findByText('Gee');
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Open' }));
    await user.click(screen.getByRole('button', { name: 'Replace' })); // the document has a clue
    await waitFor(() => expect(letters(container)).toEqual(['F']));
    await openClues(user);
    expect(clueInputs().every((i) => i.value === '')).toBe(true);
  });

  it('restore on load applies the entry\'s clues', async () => {
    storage.load.mockResolvedValue(withClues());
    const { user, container } = await boot();
    await waitFor(() => expect(letters(container)).toEqual(['F']));
    await openClues(user);
    expect(clueInputs()[1]).toHaveValue('Opened clue');
    expect(screen.queryByText(DIRTY)).toBeNull();
  });

  it('an entry whose `clues` is not a map is not adopted', async () => {
    const { user, container } = await boot();
    storage.list.mockResolvedValue([entryOf('B', 'Bad', 15, {}, { clues: [] })]);
    await pressOpenSaved(user);
    await screen.findByText('Bad');
    await user.click(within(rowOf('Bad')).getByRole('button', { name: 'Open' }));
    expect(await screen.findByText('Could not open this saved grid.')).toBeInTheDocument();
    expect(cells(container)).toHaveLength(225);
  });
});

describe('a clue commit closes the restored banner (spec 6.2 "Save")', () => {
  it('the banner is open after restore and closes on a commit', async () => {
    storage.load.mockResolvedValue(
      entryOf('R', 'Rest', 15, {}, { clues: { '0,0,across': { text: 'Kept', answer: Q15 } } })
    );
    const { user } = await boot();
    await screen.findByText(/^Restored "Rest"/);
    await openClues(user);
    // a commit that changes nothing leaves it open
    await writeClue(user, clueInputs()[0], 'Kept');
    expect(screen.getByText(/^Restored "Rest"/)).toBeInTheDocument();
    await writeClue(user, clueInputs()[1], 'Second');
    await waitFor(() => expect(screen.queryByText(/^Restored "Rest"/)).toBeNull());
  });

  it('a commit that only changes the clues closes the banner on a restore with no clues', async () => {
    storage.load.mockResolvedValue(entryOf('R', 'Plain'));
    const { user } = await boot();
    await screen.findByText(/^Restored "Plain"/);
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await waitFor(() => expect(screen.queryByText(/^Restored "Plain"/)).toBeNull());
  });
});

describe('after forget(), a clue commit re-arms autosave (spec 4.1 table, save machine row)', () => {
  it('a document dirty by a letter, its entry deleted, then a clue commit: the autosave fires and saves under the same id', async () => {
    const entry = entryOf('G', 'Gee', 15, { '1,1': { letter: 'F' } });
    storage.list.mockResolvedValue([entry]);
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
    const { container } = renderApp();
    await waitFor(() => expect(cells(container)).toHaveLength(225));
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await pressOpenSaved(user);
    await screen.findByText('Gee');
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Open' }));
    await waitFor(() => expect(letters(container)).toEqual(['F']));
    // dirty by a letter, autosave not yet fired
    await user.click(cells(container)[3 * 15 + 3]);
    fireEvent.keyDown(focusEl(container), { key: 'A' });
    // delete the open document's own entry: forget()
    storage.list.mockResolvedValue([]);
    await user.click(within(rowOf('Gee')).getByRole('button', { name: 'Delete' }));
    await user.click(
      within(screen.getByRole('group', { name: /^Delete "/ })).getByRole('button', { name: 'Delete' })
    );
    await waitFor(() => expect(storage.remove).toHaveBeenCalledWith('G'));
    expect(screen.getByText(DIRTY)).toBeInTheDocument();
    await advance(60000);
    expect(storage.save).not.toHaveBeenCalled(); // forgotten: nothing armed

    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await advance(30000);
    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(saveArg(storage.save.mock.calls[0], 0).id).toBe('G');
    expect(saveArg(storage.save.mock.calls[0], 0).clues).toEqual({
      '0,0,across': { text: 'Alpha', answer: Q15 },
    });
  });
});

describe('a save fork keeps the clues and the history (spec 4.2)', () => {
  it('after a fork the panel still shows the clue and Undo still undoes it', async () => {
    storage.save.mockImplementation((doc) => {
      saveArg([doc], 0);
      return Promise.resolve({
        savedAt: '2026-10-24T10:00:00.000Z',
        id: 'forked-id',
        name: 'n',
        forked: true,
      });
    });
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    // the fork replaced the document id, not the document
    expect(clueInputs()[0]).toHaveValue('Alpha');
    expect(undoBtn()).not.toBeDisabled();
    // the next save is under the new id and still carries the clue
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(2));
    expect(savedDoc(1).id).toBe('forked-id');
    expect(savedDoc(1).clues).toEqual({ '0,0,across': { text: 'Alpha', answer: Q15 } });
    await user.click(undoBtn());
    expect(clueInputs()[0]).toHaveValue('');
  });
});
