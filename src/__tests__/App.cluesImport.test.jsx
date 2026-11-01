/**
 * Task 9 (clue-authoring spec 0.1.4, section 3.5 "Grid JSON file, browser export" and "browser import",
 * sections 4.1, 6.2 "Import"): a grid file carries `clues`. Import checks them with the CLI route after the
 * replacement confirm, then applies the file's map; export writes the document's clues. Real App, rail,
 * Import, Export and Clues panels; storage and the API are spied. `api.checkClues` is stubbed by assignment
 * (it does not exist at RED).
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App';
import { ToastProvider } from '../components/bench/Toast';
import { ApiError } from '../api/client';
import {
  Q15,
  DIRTY,
  cells,
  letters,
  focusEl,
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
import { fileOf, importFile, settle, importError } from './appCluesImport';
import { stubCheckClues, captureDownloads, readBlob } from './importExportHelpers';
import storage from '../lib/storage';

vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), { success: vi.fn(), error: vi.fn(), loading: vi.fn() }),
  Toaster: () => null,
}));

let stub;
beforeEach(() => {
  spyApp();
  stub = stubCheckClues(async () => ({ success: true, statuses: {} }));
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
const REPLACE = () => screen.getByRole('button', { name: 'Replace' });

const MAP5 = {
  '0,0,across': { text: 'Alpha', answer: '?????' },
  '0,0,down': { text: 'Bravo', answer: '?????' },
};

describe('a valid import applies the file\'s clues (spec 3.5; 6.2 Import "a valid import applies the clues")', () => {
  it('checks {size, grid, clues} with the route, then the Clues panel shows the clues and the saved document carries the map', async () => {
    stub.fn.mockResolvedValue({
      success: true,
      statuses: { '0,0,across': 'ok', '0,0,down': 'ok' },
    });
    const { user, container } = await boot();
    await importFile(user, fileOf(5, { clues: MAP5 }), { ask: false });
    await waitFor(() => expect(cells(container)).toHaveLength(25), { timeout: 3000 });

    expect(stub.fn).toHaveBeenCalledTimes(1);
    expect(stub.fn.mock.calls[0][0]).toStrictEqual({
      size: 5,
      grid: Array.from({ length: 5 }, () => Array(5).fill('.')),
      clues: MAP5,
    });

    await openClues(user);
    expect(clueInputs().map((i) => i.value)).toEqual([
      'Alpha', '', '', '', '', // Across rows
      'Bravo', '', '', '', '', // Down rows
    ]);
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(savedDoc().clues).toStrictEqual(MAP5);
  });

  it('the imported document is born clean with an empty history (spec 4.1: the clean point after import reads the document)', async () => {
    const { user, container } = await boot();
    await importFile(user, fileOf(5, { clues: MAP5 }), { ask: false });
    await waitFor(() => expect(cells(container)).toHaveLength(25), { timeout: 3000 });
    await openClues(user);
    expect(clueInputs()[0]).toHaveValue('Alpha');
    expect(screen.queryByText(DIRTY)).toBeNull();
    expect(undoBtn()).toBeDisabled();
  });
});

describe('a 400 applies nothing (spec 3.5; 6.2 Import "a 400 shows error.message and applies nothing")', () => {
  it('the grid and the clues are unchanged, and the panel shows the message', async () => {
    const message = 'Invalid clue "0,0,across": answer must be 2 or more of A-Z or ?.';
    stub.fn.mockRejectedValue(new ApiError({ status: 400, code: 'INVALID_CLUES', message }));
    const { user, container } = await boot();
    await user.click(cells(container)[0]);
    fireEvent.keyDown(focusEl(container), { key: 'B' });
    expect(letters(container)).toEqual(['B']);
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');

    await importFile(user, fileOf(5, { clues: MAP5 }), { ask: true });
    await user.click(REPLACE());
    await waitFor(() => expect(importError()).toBe(`Error: ${message}`), { timeout: 3000 });
    await settle(); // past the import timer: nothing may land late

    expect(cells(container)).toHaveLength(225);
    expect(letters(container)).toEqual(['B']);
    await openClues(user);
    expect(clueInputs()).toHaveLength(30);
    expect(clueInputs()[0]).toHaveValue('Alpha');
    expect(screen.queryByDisplayValue('Bravo')).toBeNull();
  });
});

describe('an import over a document with clues, from a file with no `clues` key (spec 3.5; Task 8 interim rule, now permanent)', () => {
  it('leaves no clues, and the import makes no request', async () => {
    const { user, container } = await boot();
    await openClues(user);
    await writeClue(user, clueInputs()[0], 'Alpha');
    await openTool(user, 'Grid');
    // Counted with the Clues panel closed: from Task 10 (spec 5.6) an open panel sends its own
    // reconcile requests through the same method, so only the import's window is asserted.
    const before = stub.fn.mock.calls.length;
    await importFile(user, fileOf(5), { ask: true });
    await user.click(REPLACE());
    await waitFor(() => expect(cells(container)).toHaveLength(25), { timeout: 3000 });
    expect(stub.fn.mock.calls.length).toBe(before);
    await openClues(user);
    expect(clueInputs()).toHaveLength(10);
    expect(clueInputs().every((i) => i.value === '')).toBe(true);
    await saveGrid(user);
    await waitFor(() => expect(storage.save).toHaveBeenCalledTimes(1));
    expect(savedDoc().clues).toStrictEqual({});
  });
});

describe('export through the real App carries the document\'s clues (spec 3.5 browser export; pins App\'s `clues` to ExportPanel)', () => {
  it('the downloaded JSON file\'s `clues` equals the committed map', async () => {
    const downloads = captureDownloads();
    try {
      const { user } = await boot();
      await openClues(user);
      await writeClue(user, clueInputs()[0], 'Alpha');
      await openTool(user, 'Export');
      const panel = document.querySelector('.export-panel');
      await user.click(within(panel).getByRole('button', { name: /^export$/i }));
      await waitFor(() => expect(downloads.blobs).toHaveLength(1), { timeout: 3000 });
      const file = JSON.parse(await readBlob(downloads.blobs[0]));
      expect(file.clues).toStrictEqual({ '0,0,across': { text: 'Alpha', answer: Q15 } });
    } finally {
      downloads.restore();
    }
  });
});
