/**
 * Shared helpers for the App-level Task 9 tests (clue-authoring spec 0.1.4, section 3.5 browser import
 * and export). Not a test file: `App.cluesImport*.test.jsx` import it. Builds on `appClues.js`.
 */
import { screen, waitFor, fireEvent, act } from '@testing-library/react';
import { expect } from 'vitest';

/**
 * A grid-file JSON string: `size` x `size` of empty squares, `cells` ("row,col" -> cell string) patched in.
 * The `clues` key is written when `clues !== undefined`, so `null` is a present key and `undefined` is none.
 */
export const fileOf = (size, { clues, cells = {} } = {}) => {
  const grid = Array.from({ length: size }, (_, r) =>
    Array.from({ length: size }, (_, c) => cells[`${r},${c}`] ?? '.')
  );
  return JSON.stringify({ size, grid, ...(clues !== undefined ? { clues } : {}) });
};

/**
 * Drives Import through the real rail and panel: open the tool, paste `text`, validate, press Import Grid.
 * With `ask`, waits for the replacement confirm (it is NOT pressed). Returns with the click done.
 */
export const importFile = async (user, text, { ask = false } = {}) => {
  await user.click(screen.getByRole('button', { name: /^import$/i }));
  await user.click(screen.getByRole('button', { name: /paste json/i }));
  fireEvent.change(screen.getByLabelText(/paste json data/i), { target: { value: text } });
  await user.click(screen.getByRole('button', { name: /validate json/i }));
  await waitFor(() => {
    expect(screen.getByRole('button', { name: /import grid/i })).toBeInTheDocument();
  });
  await user.click(screen.getByRole('button', { name: /import grid/i }));
  if (ask) {
    expect(await screen.findByRole('button', { name: 'Replace' })).toBeInTheDocument();
  }
};

/** Lets real time pass inside `act`, for "nothing else happens" assertions (past ImportPanel's 300 ms timer). */
export const settle = (ms = 900) =>
  act(async () => {
    await new Promise((resolve) => setTimeout(resolve, ms));
  });

/** The text of the Import panel's error box, or undefined. */
export const importError = () => document.querySelector('.error-message')?.textContent;
