/**
 * Tests for storage (Task 7, Step 1) — the async persistence transport the
 * save machine reaches through. Spec 06 §3 (reconciled — see Task 7).
 *
 * The repo's setupTests.js replaces `global.localStorage` with a bag of
 * `vi.fn()` mocks (NOT jsdom's real Storage), so we can't spy on
 * `Storage.prototype` here. Instead we back those mocks with a real Map so
 * save→load round-trips actually persist, and override a single mock when a
 * test needs a quota/serialize failure.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { save, load, SAVE_KEY } from '../storage';

let store;

beforeEach(() => {
  store = new Map();
  localStorage.getItem.mockImplementation((k) => (store.has(k) ? store.get(k) : null));
  localStorage.setItem.mockImplementation((k, v) => {
    store.set(k, String(v));
  });
  localStorage.removeItem.mockImplementation((k) => {
    store.delete(k);
  });
});

describe('storage', () => {
  it('SAVE_KEY is the legacy key so pre-Task-7 saves still load', () => {
    expect(SAVE_KEY).toBe('crossword_saved_grid');
  });

  it('save() returns a real Promise', () => {
    const p = save({ id: 'g1', size: 5 });
    expect(typeof p.then).toBe('function');
    return p; // let it settle
  });

  it('save() round-trips through load() with the doc payload intact', async () => {
    const doc = { id: 'g1', size: 15, grid: [[{ letter: 'A' }]], symmetryEnabled: true };
    const { savedAt } = await save(doc);
    const loaded = await load();
    expect(loaded).toMatchObject(doc);
    expect(loaded.savedAt).toBe(savedAt);
  });

  it('save() stamps an ISO savedAt and returns it', async () => {
    const { savedAt } = await save({ id: 'g1' });
    // ISO 8601, e.g. 2026-07-13T13:00:00.000Z
    expect(savedAt).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
    expect(new Date(savedAt).toISOString()).toBe(savedAt);
  });

  it('save() writes the legacy blob under the exact key "crossword_saved_grid"', async () => {
    await save({ id: 'g1', size: 15 });
    expect(localStorage.setItem).toHaveBeenCalledWith(
      'crossword_saved_grid',
      expect.any(String)
    );
    const raw = store.get('crossword_saved_grid');
    expect(JSON.parse(raw)).toMatchObject({ id: 'g1', size: 15 });
  });

  it('save() REJECTS when setItem throws (quota / serialize failure)', async () => {
    const boom = new Error('QuotaExceededError');
    localStorage.setItem.mockImplementation(() => {
      throw boom;
    });
    await expect(save({ id: 'g1' })).rejects.toBe(boom);
  });

  it('load() returns a real Promise', () => {
    const p = load();
    expect(typeof p.then).toBe('function');
    return p;
  });

  it('load() resolves null when the key is absent (never throws)', async () => {
    await expect(load()).resolves.toBeNull();
  });

  it('load() resolves null for a corrupt blob rather than throwing (boot must not crash)', async () => {
    store.set(SAVE_KEY, '{ this is not valid json');
    await expect(load()).resolves.toBeNull();
  });

  it('load() returns a legacy blob that predates savedAt', async () => {
    // Simulate App.jsx's old handleSaveGrid shape (no savedAt field).
    const legacy = { size: 15, grid: [], numbering: {}, symmetryEnabled: false, timestamp: 'x' };
    store.set(SAVE_KEY, JSON.stringify(legacy));
    await expect(load()).resolves.toEqual(legacy);
  });
});
