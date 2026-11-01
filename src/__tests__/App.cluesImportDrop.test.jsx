/**
 * Task 9 (clue-authoring spec 0.1.4, section 3.5 "browser import", ruled 2026-11-01; novice-readiness
 * spec section 3.4 "An Open that waits"): an import waits for the clue check. If New grid or an import
 * replaced the document after the user confirmed it, the import is dropped with no message. Grid edits,
 * closing the panel and a save fork do not cancel it. Real App; `api.checkClues` is held by a deferred and
 * stubbed by assignment (it does not exist at RED).
 *
 * Every test first waits for the held check to be called, so at RED (where nothing calls it) each fails
 * there, on the missing request, and not on a side effect.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import {
  DIRTY,
  cells,
  letters,
  focusEl,
  spyApp,
  waitForBlank15,
  openClues,
  openTool,
  clueInputs,
  undoBtn,
  entryOf,
} from './appClues';
import storage from '../lib/storage';
import { fileOf, importFile, settle } from './appCluesImport';
import { stubCheckClues, deferred, captureDownloads, readBlob } from './importExportHelpers';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

let stub;
let held;
beforeEach(() => {
  spyApp();
  held = deferred();
  stub = stubCheckClues(() => held.promise);
});
afterEach(() => {
  stub.restore();
  vi.restoreAllMocks();
});

const boot = async () => {
  const user = userEvent.setup();
  const view = render(<App />, { wrapper: ToastProvider });
  await waitForBlank15(view.container);
  return { user, ...view };
};

// The import under test: 5x5, a Q in the first square, one clue. The check on it is held.
const FIRST = fileOf(5, {
  cells: { '0,0': 'Q' },
  clues: { '0,0,across': { text: 'Alpha', answer: 'Q????' } },
});
const startFirstImport = async (user) => {
  await importFile(user, FIRST, { ask: false });
  await waitFor(() => expect(stub.fn).toHaveBeenCalledTimes(1), { timeout: 3000 });
};
const releaseFirst = () => held.resolve({ success: true, statuses: { '0,0,across': 'ok' } });

describe('an import that waits is dropped when the document is replaced after its confirm (spec 3.5 ruling 2026-11-01)', () => {
  it('New grid made while the check runs: the document is the new grid, and the import never appears', async () => {
    const { user, container } = await boot();
    await startFirstImport(user);
    await openTool(user, 'Grid');
    await user.click(screen.getByRole('button', { name: '11×11' }));
    await waitFor(() => expect(cells(container)).toHaveLength(121));

    releaseFirst();
    await settle();

    expect(cells(container)).toHaveLength(121);
    expect(letters(container)).toEqual([]);
    await openClues(user);
    expect(clueInputs()).toHaveLength(22);
    expect(clueInputs().every((i) => i.value === '')).toBe(true);
    expect(screen.queryByDisplayValue('Alpha')).toBeNull();
    expect(screen.queryByText(DIRTY)).toBeNull();
    expect(undoBtn()).toBeDisabled();
  });

  it('a second import of a file with no `clues` key: the document is the second import, and the first never appears', async () => {
    const { user, container } = await boot();
    await startFirstImport(user);
    // The first import keeps its panel busy; leaving the tool and coming back gives a fresh Import panel.
    await openTool(user, 'Grid');
    await importFile(user, fileOf(7, { cells: { '1,1': 'Z' } }), { ask: false });
    await waitFor(() => expect(cells(container)).toHaveLength(49), { timeout: 3000 });
    expect(letters(container)).toEqual(['Z']);
    expect(stub.fn).toHaveBeenCalledTimes(1); // the second file has no `clues` key: no request

    releaseFirst();
    await settle();

    expect(cells(container)).toHaveLength(49);
    expect(letters(container)).toEqual(['Z']);
    await openClues(user);
    expect(clueInputs()).toHaveLength(14);
    expect(clueInputs().every((i) => i.value === '')).toBe(true);
    expect(screen.queryByDisplayValue('Alpha')).toBeNull();
  });
});

describe('what does not cancel a waiting import (novice-readiness spec 3.4; clue-authoring spec 3.5)', () => {
  it('a grid edit made while the check runs is replaced when the import applies', async () => {
    const { user, container } = await boot();
    await startFirstImport(user);
    await user.click(cells(container)[3]);
    fireEvent.keyDown(focusEl(container), { key: 'B' });
    expect(letters(container)).toEqual(['B']); // the edit is on the 15x15 grid

    releaseFirst();
    await waitFor(() => expect(cells(container)).toHaveLength(25), { timeout: 3000 });

    expect(letters(container)).toEqual(['Q']);
    await openClues(user);
    expect(clueInputs()[0]).toHaveValue('Alpha');
    expect(screen.queryByText(DIRTY)).toBeNull();
  });

  it('switching tool away from Import while the check runs does not cancel it', async () => {
    const { user, container } = await boot();
    await startFirstImport(user);
    await openTool(user, 'Grid');
    expect(cells(container)).toHaveLength(225);

    releaseFirst();
    await waitFor(() => expect(cells(container)).toHaveLength(25), { timeout: 3000 });

    expect(letters(container)).toEqual(['Q']);
    await openClues(user);
    expect(clueInputs()[0]).toHaveValue('Alpha');
  });
});

describe('a waiting import applies against the size the document has when it lands (spec 3.5 ruling 2026-11-01: an Open does not drop it)', () => {
  it('an Open of another size made while the check runs: the import still applies, and the size matches the grid', async () => {
    const downloads = captureDownloads();
    try {
      const { user, container } = await boot();
      // A 15x15 file into the 15x15 document: same size, so the size comparison is the one that matters.
      await importFile(user, fileOf(15, { cells: { '0,0': 'Q' }, clues: {} }), { ask: false });
      await waitFor(() => expect(stub.fn).toHaveBeenCalledTimes(1), { timeout: 3000 });
      await openTool(user, 'Grid');
      // A blank grid, so Open does not ask: it replaces the document at once with an 11x11.
      storage.list.mockResolvedValue([entryOf('E', 'Eleven', 11)]);
      await user.click(screen.getByRole('button', { name: 'Open saved' }));
      await screen.findByText('Eleven');
      await user.click(
        within(screen.getByText('Eleven').closest('li')).getByRole('button', { name: 'Open' })
      );
      await waitFor(() => expect(cells(container)).toHaveLength(121));

      releaseFirst();
      await waitFor(() => expect(letters(container)).toEqual(['Q']), { timeout: 3000 });
      await settle();

      // The import applied (an Open does not move the replacement count), and the document is consistent.
      expect(cells(container)).toHaveLength(225);
      await openTool(user, 'Export');
      const panel = document.querySelector('.export-panel');
      await user.click(within(panel).getByRole('button', { name: /^export$/i }));
      await waitFor(() => expect(downloads.blobs).toHaveLength(1), { timeout: 3000 });
      const file = JSON.parse(await readBlob(downloads.blobs[0]));
      expect(file.grid).toHaveLength(15);
      expect(file.size).toBe(file.grid.length);
      expect(file.size).toBe(15);
    } finally {
      downloads.restore();
    }
  });
});
