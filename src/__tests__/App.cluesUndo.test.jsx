/**
 * Task 8 (clue-authoring spec 0.1.4, Decision 5 and sections 4.3, 5.4, 6.2 "Undo" and the Panel
 * row "a tool switch commits a draft"): clue edits are undo steps. Real App, rail, top bar, save
 * machine and Clues panel; storage and the API are spied. A clue is written the way a user writes
 * it: open the Clues tool from the rail, type into a row's input, leave the field.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { api } from '../api/client';
import storage from '../lib/storage';
import {
  Q15,
  DIRTY,
  cells,
  letters,
  focusEl,
  entryOf,
  staleAndOrphanEntry,
  spyApp,
  waitForBlank15,
  rail,
  openClues,
  openTool,
  clueInputs,
  typeDraft,
  writeClue,
  leave,
  undoBtn,
  redoBtn,
} from './appClues';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

beforeEach(() => spyApp());
afterEach(() => {
  vi.restoreAllMocks();
});

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitForBlank15(view.container);
  return { user, ...view };
};

describe('one commit is one step (spec 6.2 "Undo"; mutation: the snapshot signature reverts to the grid signature)', () => {
  it('one changed commit is exactly one undo step, and one undo restores the previous text', async () => {
    const { user } = await boot();
    expect(undoBtn()).toBeDisabled();
    await openClues(user);
    const first = clueInputs()[0];
    await writeClue(user, first, 'Alpha');
    expect(first).toHaveValue('Alpha');
    expect(undoBtn()).not.toBeDisabled();
    await user.click(undoBtn());
    expect(clueInputs()[0]).toHaveValue('');
    // exactly one step: the history is empty again
    expect(undoBtn()).toBeDisabled();
    expect(redoBtn()).not.toBeDisabled();
  });

  it('a second changed commit is a second step: one undo restores the first text', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await writeClue(user, clueInputs()[0], 'Beta');
    expect(clueInputs()[0]).toHaveValue('Beta');
    await user.click(undoBtn());
    expect(clueInputs()[0]).toHaveValue('Alpha');
    expect(undoBtn()).not.toBeDisabled();
    await user.click(undoBtn());
    expect(clueInputs()[0]).toHaveValue('');
    expect(undoBtn()).toBeDisabled();
  });

  it('a commit that changes nothing is no step', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await writeClue(user, clueInputs()[0], 'Alpha'); // the same text
    await writeClue(user, clueInputs()[0], '  Alpha  '); // the same text once trimmed
    await writeClue(user, clueInputs()[1], '   '); // whitespace on an entry with no clue
    // the history holds the one step of the first commit, not four
    await user.click(undoBtn());
    expect(clueInputs()[0]).toHaveValue('');
    expect(undoBtn()).toBeDisabled();
  });

  it('typing five characters then leaving is one step', async () => {
    const { user } = await boot();
    await openClues(user);
    const input = clueInputs()[3];
    await user.click(input);
    await user.type(input, 'Hello');
    expect(undoBtn()).toBeDisabled(); // keystrokes are not steps
    await leave(input);
    expect(clueInputs()[3]).toHaveValue('Hello');
    await user.click(undoBtn());
    expect(clueInputs()[3]).toHaveValue('');
    expect(undoBtn()).toBeDisabled();
  });

  it('undo restores the text and redo reapplies it', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await user.click(undoBtn());
    expect(clueInputs()[0]).toHaveValue('');
    await user.click(redoBtn());
    expect(clueInputs()[0]).toHaveValue('Alpha');
    expect(redoBtn()).toBeDisabled();
    expect(undoBtn()).not.toBeDisabled();
  });

  it('Cmd+Z on the document undoes a commit', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    fireEvent.keyDown(document.body, { key: 'z', metaKey: true });
    expect(clueInputs()[0]).toHaveValue('');
  });

  it('removing a clue (an empty draft) is one step: undo brings the text back', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await writeClue(user, clueInputs()[0], '');
    expect(clueInputs()[0]).toHaveValue('');
    await user.click(undoBtn());
    expect(clueInputs()[0]).toHaveValue('Alpha');
  });

  it('a clue commit and a letter typed in the grid are two steps, each undone on its own', async () => {
    const { user, container } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await user.click(cells(container)[5 * 15 + 5]);
    fireEvent.keyDown(focusEl(container), { key: 'Q' });
    expect(letters(container)).toEqual(['Q']);
    await user.click(undoBtn()); // the letter
    expect(letters(container)).toEqual([]);
    expect(clueInputs()[0]).toHaveValue('Alpha');
    await user.click(undoBtn()); // the clue
    expect(clueInputs()[0]).toHaveValue('');
    expect(undoBtn()).toBeDisabled();
  });
});

describe('Keep and Delete are one step each (spec 4.3)', () => {
  const bootStale = async () => {
    storage.load.mockResolvedValue(staleAndOrphanEntry());
    const view = await boot();
    await screen.findByText(/^Restored "Stale"/);
    await openClues(view.user);
    return view;
  };

  it('Keep is one step: undo makes the row stale again', async () => {
    const { user } = await bootStale();
    expect(screen.getByRole('button', { name: 'Keep' })).toBeInTheDocument();
    expect(undoBtn()).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Keep' }));
    expect(screen.queryByRole('button', { name: 'Keep' })).toBeNull();
    expect(undoBtn()).not.toBeDisabled();
    await user.click(undoBtn());
    expect(screen.getByRole('button', { name: 'Keep' })).toBeInTheDocument();
    expect(undoBtn()).toBeDisabled();
  });

  it('Delete is one step: undo brings the orphan back', async () => {
    const { user } = await bootStale();
    expect(screen.getByText('Old orphan clue')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    expect(screen.queryByText('Old orphan clue')).toBeNull();
    expect(undoBtn()).not.toBeDisabled();
    await user.click(undoBtn());
    expect(screen.getByText('Old orphan clue')).toBeInTheDocument();
    expect(undoBtn()).toBeDisabled();
  });
});

describe('Undo with a draft open (spec 4.3)', () => {
  it('clicking Undo commits the draft, then undoes it: the field shows the old text, redo reapplies the trimmed text', async () => {
    const { user } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'one'); // a step, so that Undo is enabled
    await typeDraft(user, clueInputs()[0], '  two  '); // an open draft
    expect(undoBtn()).not.toBeDisabled();
    await user.click(undoBtn());
    // the draft was committed (one -> two) and that commit undone: not one -> '' (the draft ignored)
    expect(clueInputs()[0]).toHaveValue('one');
    expect(undoBtn()).not.toBeDisabled();
    await user.click(redoBtn());
    expect(clueInputs()[0]).toHaveValue('two');
    expect(redoBtn()).toBeDisabled();
  });
});

describe('a tool switch commits a draft (spec 5.4, 6.2 Panel)', () => {
  it('switching away from Clues with a draft open commits it as one step', async () => {
    const { user } = await boot();
    await openClues(user);
    const input = clueInputs()[2];
    await user.click(input);
    await user.type(input, 'Pending');
    expect(undoBtn()).toBeDisabled();
    // a bare click event moves no focus, so no blur: the panel's unmount is what commits
    fireEvent.click(rail('Grid'));
    await waitFor(() => expect(clueInputs()).toHaveLength(0));
    await waitFor(() => expect(undoBtn()).not.toBeDisabled());
    expect(screen.getByText(DIRTY)).toBeInTheDocument();
    await openClues(user);
    expect(clueInputs()[2]).toHaveValue('Pending');
    await user.click(undoBtn());
    expect(clueInputs()[2]).toHaveValue('');
    expect(undoBtn()).toBeDisabled(); // exactly one step
  });

  it('switching with a draft open by clicking the rail with a real pointer commits it once', async () => {
    const { user } = await boot();
    await openClues(user);
    const input = clueInputs()[2];
    await user.click(input);
    await user.type(input, 'Pending');
    await openTool(user, 'Export');
    await openClues(user);
    expect(clueInputs()[2]).toHaveValue('Pending');
    await user.click(undoBtn());
    expect(clueInputs()[2]).toHaveValue('');
    expect(undoBtn()).toBeDisabled();
  });
});

describe('a clue-only undo leaves an open Clean confirm open (spec 4.3; consumer table: pendingClean keeps the grid signature)', () => {
  const cleaned = () => ({
    grid: Array.from({ length: 15 }, () => Array(15).fill('.')),
    removed_count: 1,
    valid_count: 0,
    cleared_cells: [[0, 0]],
    message: 'Removed 1 invalid word',
  });

  it('undoing the clue commit keeps the confirm; undoing the letter then dismisses it', async () => {
    vi.spyOn(api, 'cleanGrid').mockResolvedValue(cleaned());
    const { user, container } = await boot();
    await user.click(cells(container)[0]);
    fireEvent.keyDown(focusEl(container), { key: 'B' });
    expect(letters(container)).toEqual(['B']);
    await openClues(user);
    await writeClue(user, clueInputs()[1], 'Alpha');

    await user.click(screen.getByText('Clean grid'));
    const confirm = await screen.findByRole('button', { name: 'Clean' });
    expect(confirm).toBeInTheDocument();

    await user.click(undoBtn()); // the clue commit: not a grid change
    expect(clueInputs()[1]).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Clean' })).toBeInTheDocument();
    expect(letters(container)).toEqual(['B']);

    await user.click(undoBtn()); // the letter: a grid change, so the confirm goes
    expect(letters(container)).toEqual([]);
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Clean' })).toBeNull());
  });
});

describe('undo back to the saved content leaves the document clean (spec 6.2 "Undo")', () => {
  it('a commit makes the document dirty and undoing it clears the unsaved label', async () => {
    const { user } = await boot();
    await openClues(user);
    expect(screen.queryByText(DIRTY)).toBeNull();
    await writeClue(user, clueInputs()[0], 'Alpha');
    expect(screen.getByText(DIRTY)).toBeInTheDocument();
    await user.click(undoBtn());
    expect(screen.queryByText(DIRTY)).toBeNull();
    await user.click(redoBtn());
    expect(screen.getByText(DIRTY)).toBeInTheDocument();
  });

  it('a restored document with a clue: edit the clue then undo, and the document is clean again', async () => {
    storage.load.mockResolvedValue(
      entryOf('R', 'Restored', 15, {}, { clues: { '0,0,across': { text: 'Kept', answer: Q15 } } })
    );
    const { user } = await boot();
    await screen.findByText(/^Restored "Restored"/);
    await openClues(user);
    expect(clueInputs()[0]).toHaveValue('Kept');
    expect(screen.queryByText(DIRTY)).toBeNull();
    await writeClue(user, clueInputs()[0], 'Changed');
    expect(screen.getByText(DIRTY)).toBeInTheDocument();
    await user.click(undoBtn());
    expect(clueInputs()[0]).toHaveValue('Kept');
    expect(screen.queryByText(DIRTY)).toBeNull();
  });
});
