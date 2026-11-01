/**
 * Shared helpers for the App-level clue tests (clue-authoring spec 0.1.4, Task 8). Not a test
 * file: the `App.clues*.test.jsx` files import it. `vi.mock('react-hot-toast')` cannot live here
 * (it is hoisted per test file), so each test file carries its own.
 *
 * The tests drive the real rail, the real Clues panel and the real top bar. Clue state is
 * observed through what the panel shows, the top bar's labels and buttons, and the document
 * handed to `storage.save`; never through App's state.
 */
import { screen, waitFor, act } from '@testing-library/react';
import { vi, expect } from 'vitest';
import { api } from '../api/client';
import storage from '../lib/storage';
import { saveArg } from './saveArgs';

export const PLACEHOLDER = 'Write a clue…';
export const SAVED_AT = '2026-10-22T09:30:00.000Z';
/** The pattern of an entry of 15 empty squares: the answer of a clue committed on a blank 15x15. */
export const Q15 = '?'.repeat(15);

export const cells = (c) => c.querySelectorAll('rect[fill="transparent"]');
export const letters = (c) =>
  Array.from(c.querySelectorAll('.xw-cell-letter')).map((el) => el.textContent);
export const focusEl = (c) => c.querySelector('.xw-grid-focus');

/** A saved entry's cells, `size` x `size`, with per-cell patches keyed "row,col". */
export const cellsOf = (size, edits = {}) =>
  Array.from({ length: size }, (_, r) =>
    Array.from({ length: size }, (_, c) => ({
      letter: '',
      isBlack: false,
      isThemeLocked: false,
      number: null,
      isError: false,
      isAutofilled: false,
      ...(edits[`${r},${c}`] || {}),
    }))
  );

export const entryOf = (id, name, size = 15, edits = {}, over = {}) => ({
  id,
  name,
  savedAt: SAVED_AT,
  size,
  grid: cellsOf(size, edits),
  numbering: {},
  symmetryEnabled: true,
  ...over,
});

/**
 * An entry on a 15x15 with (3,3) black, holding two clues that are not ok:
 * "0,0,across" was written for a first letter of A that the grid does not have (stale), and
 * "3,3,down" starts no entry because its square is black (orphaned).
 */
export const staleAndOrphanEntry = () =>
  entryOf('S', 'Stale', 15, { '3,3': { isBlack: true } }, {
    clues: {
      '0,0,across': { text: 'Old stale clue', answer: `A${'?'.repeat(14)}` },
      '3,3,down': { text: 'Old orphan clue', answer: 'ABC' },
    },
  });

/** The spies every App-level clue test needs, with nothing in storage. */
export function spyApp({ startFill } = {}) {
  global.localStorage.getItem.mockReturnValue(null);
  vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });
  vi.spyOn(api, 'getWordlists').mockResolvedValue({
    wordlists: [{ key: 'comprehensive', name: 'Comprehensive' }],
  });
  vi.spyOn(api, 'startFill').mockImplementation(startFill || (() => new Promise(() => {})));
  vi.spyOn(api, 'openProgress').mockImplementation(() => ({ close() {} }));
  vi.spyOn(storage, 'load').mockResolvedValue(null);
  vi.spyOn(storage, 'list').mockResolvedValue([]);
  vi.spyOn(storage, 'remove').mockResolvedValue(undefined);
  vi.spyOn(storage, 'save').mockImplementation((doc) =>
    Promise.resolve({
      savedAt: new Date().toISOString(),
      id: saveArg([doc], 0).id,
      name: 'n',
      forked: false,
    })
  );
  vi.spyOn(storage, 'saveSync').mockImplementation(() => ({ savedAt: new Date().toISOString() }));
  vi.spyOn(console, 'error').mockImplementation(() => {});
}

export const waitForBlank15 = async (container) => {
  await waitFor(() => expect(cells(container)).toHaveLength(225));
  await waitFor(() =>
    expect(screen.getByText('Verify words').closest('button')).not.toBeDisabled()
  );
};

// ---------- rail and panel ----------

export const rail = (name) => screen.getByRole('button', { name });
export const openTool = (user, name) => user.click(rail(name));
export const openClues = (user) => openTool(user, 'Clues');

/** Every clue input, Across rows first and then Down rows, each in reading order. */
export const clueInputs = () => screen.queryAllByPlaceholderText(PLACEHOLDER);

/** Types `text` into `input`, replacing what it holds, without leaving it: an open draft. */
export const typeDraft = async (user, input, text) => {
  await user.click(input);
  await user.clear(input);
  if (text !== '') await user.type(input, text);
};

/** Leaves the field the way a user does, committing the draft. */
export const leave = (input) =>
  act(() => {
    input.blur();
  });

/** A committed clue: the draft typed, then the field left. */
export const writeClue = async (user, input, text) => {
  await typeDraft(user, input, text);
  await leave(input);
};

// ---------- top bar ----------

export const undoBtn = () => screen.getByRole('button', { name: 'Undo' });
export const redoBtn = () => screen.getByRole('button', { name: 'Redo' });
export const DIRTY = 'unsaved changes';

/** Save grid, accept the prefilled name, wait for the prompt to close. */
export const saveGrid = async (user) => {
  await user.click(screen.getByRole('button', { name: /save grid/i }));
  await user.click(await screen.findByRole('button', { name: 'Save' }));
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Save' })).toBeNull());
};

/** The document handed to the n-th `storage.save` call. */
export const savedDoc = (n = 0) => saveArg(storage.save.mock.calls[n], 0);
