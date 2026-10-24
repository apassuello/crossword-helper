/**
 * Tests for storage — the async persistence transport the save machine reaches
 * through; saved grids are a newest-first list (novice-readiness spec 0.2.7
 * §3.4).
 *
 * The repo's setupTests.js replaces `global.localStorage` with a bag of
 * `vi.fn()` mocks (NOT jsdom's real Storage), so we back those mocks with a real
 * Map so round-trips persist, and override a single mock when a test needs a
 * quota failure.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import storage, {
  save,
  load,
  list,
  remove,
  defaultName,
  formatStamp,
  SAVE_KEY,
  LEGACY_SAVE_KEY,
} from '../storage';

let store;
const T = (n) => new Date(Date.UTC(2026, 9, 1, 10, 0, n)).toISOString();
const g = [[{ letter: 'A' }]];
const readArray = () => JSON.parse(store.get(SAVE_KEY));

beforeEach(() => {
  store = new Map();
  localStorage.getItem.mockImplementation((k) => (store.has(k) ? store.get(k) : null));
  localStorage.setItem.mockImplementation((k, v) => {
    store.set(k, String(v));
  });
  localStorage.removeItem.mockImplementation((k) => {
    store.delete(k);
  });
  vi.useFakeTimers();
  vi.setSystemTime(new Date(2026, 9, 23, 14, 5, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

describe('storage keys', () => {
  it('SAVE_KEY is the array key and LEGACY_SAVE_KEY the pre-6.5 single blob', () => {
    expect(SAVE_KEY).toBe('crossword_saved_grids');
    expect(LEGACY_SAVE_KEY).toBe('crossword_saved_grid');
  });

  it('the default export carries the whole API', () => {
    expect(Object.keys(storage).sort()).toEqual(
      ['LEGACY_SAVE_KEY', 'SAVE_KEY', 'defaultName', 'formatStamp', 'list', 'load', 'remove', 'save'].sort()
    );
  });
});

describe('names', () => {
  it('formatStamp is YYYY-MM-DD HH:MM in local time', () => {
    expect(formatStamp(new Date(2026, 9, 3, 4, 5))).toBe('2026-10-03 04:05');
  });

  it('defaultName joins size, U+00D7 and the stamp', () => {
    const name = defaultName(15, new Date(2026, 9, 23, 14, 5));
    expect(name).toBe('15×15 2026-10-23 14:05');
    expect(name.codePointAt(2)).toBe(0x00d7);
  });
});

describe('list / load', () => {
  it('returns real Promises', () => {
    expect(typeof list().then).toBe('function');
    expect(typeof load().then).toBe('function');
  });

  it('empty storage: list() is [] and load() is null', async () => {
    await expect(list()).resolves.toEqual([]);
    await expect(load()).resolves.toBeNull();
  });

  it('corrupt array blob: list() is [] and load() is null, no throw', async () => {
    store.set(SAVE_KEY, '{ this is not valid json');
    await expect(list()).resolves.toEqual([]);
    await expect(load()).resolves.toBeNull();
  });

  it('a non-array blob reads as empty', async () => {
    store.set(SAVE_KEY, '{"id":"a"}');
    await expect(list()).resolves.toEqual([]);
  });

  it('list() is newest first and load() is the newest', async () => {
    vi.setSystemTime(new Date(Date.UTC(2026, 9, 1, 10, 0, 1)));
    await save({ id: 'a', size: 5, grid: g });
    vi.setSystemTime(new Date(Date.UTC(2026, 9, 1, 10, 0, 2)));
    await save({ id: 'b', size: 5, grid: g });
    expect((await list()).map((e) => e.id)).toEqual(['b', 'a']);
    expect((await load()).id).toBe('b');
  });
});

describe('save', () => {
  it('returns a real Promise', () => {
    const p = save({ id: 'g1', size: 5 });
    expect(typeof p.then).toBe('function');
    return p;
  });

  it('creates an entry under the default name and resolves its identity', async () => {
    const res = await save({ id: 'a', size: 15, grid: g });
    expect(res).toEqual({
      savedAt: new Date().toISOString(),
      id: 'a',
      name: `15×15 ${formatStamp(new Date())}`,
      forked: false,
    });
    const entries = await list();
    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({ id: 'a', size: 15, name: res.name, savedAt: res.savedAt });
  });

  it('writes a JSON array under the array key and not the legacy key', async () => {
    await save({ id: 'a', size: 15, grid: g, symmetryEnabled: true });
    expect(localStorage.setItem).toHaveBeenCalledWith(SAVE_KEY, expect.any(String));
    expect(readArray()[0]).toMatchObject({ id: 'a', size: 15, symmetryEnabled: true });
    expect(store.has(LEGACY_SAVE_KEY)).toBe(false);
  });

  it('upserts: keeps the stored name, refreshes savedAt, moves to front', async () => {
    vi.setSystemTime(new Date(Date.UTC(2026, 9, 1, 10, 0, 1)));
    await save({ id: 'a', size: 5, grid: g }, { name: 'Mine' });
    vi.setSystemTime(new Date(Date.UTC(2026, 9, 1, 10, 0, 2)));
    await save({ id: 'b', size: 5, grid: g });
    vi.setSystemTime(new Date(Date.UTC(2026, 9, 1, 10, 0, 3)));
    await save({ id: 'a', size: 5, grid: g, name: 'ignored' });
    const entries = await list();
    expect(entries.map((e) => e.id)).toEqual(['a', 'b']);
    expect(entries[0].name).toBe('Mine');
    expect(entries[0].savedAt).toBe(T(3));
  });

  it('opts.name renames the entry', async () => {
    await save({ id: 'a', size: 5, grid: g });
    await save({ id: 'a', size: 5, grid: g }, { name: 'Puzzle 1' });
    const entries = await list();
    expect(entries).toHaveLength(1);
    expect(entries[0].name).toBe('Puzzle 1');
  });

  it('replaceEntryId removes that entry in the same write', async () => {
    await save({ id: 'a', size: 5, grid: g });
    await save({ id: 'b', size: 5, grid: g });
    localStorage.setItem.mockClear();
    await save({ id: 'a', size: 5, grid: g }, { name: 'Other', replaceEntryId: 'b' });
    const entries = await list();
    expect(entries.map((e) => [e.id, e.name])).toEqual([['a', 'Other']]);
    expect(localStorage.setItem).toHaveBeenCalledTimes(1);
  });

  it('REJECTS when setItem throws (quota / serialize failure)', async () => {
    const boom = new Error('QuotaExceededError');
    localStorage.setItem.mockImplementation(() => {
      throw boom;
    });
    await expect(save({ id: 'g1', size: 5 })).rejects.toBe(boom);
  });
});

describe('remove', () => {
  it('removes the entry; an unknown id resolves and changes nothing', async () => {
    await save({ id: 'a', size: 5, grid: g });
    await remove('a');
    await expect(list()).resolves.toEqual([]);
    await save({ id: 'b', size: 5, grid: g });
    const before = store.get(SAVE_KEY);
    await expect(remove('zzz')).resolves.toBeUndefined();
    expect(store.get(SAVE_KEY)).toBe(before);
  });
});

describe('fork on a stale expectedSavedAt (S4)', () => {
  beforeEach(async () => {
    vi.setSystemTime(new Date(Date.UTC(2026, 9, 1, 10, 0, 1)));
    await save({ id: 'a', size: 5, grid: g }, { name: 'Mine' });
  });

  it('a mismatch writes a new entry named "<name> (copy)" and leaves the stored one alone', async () => {
    const stored = (await list())[0];
    vi.setSystemTime(new Date(Date.UTC(2026, 9, 1, 10, 0, 5)));
    const res = await save({ id: 'a', size: 5, grid: g }, { expectedSavedAt: T(0) });
    expect(res.forked).toBe(true);
    expect(res.id).not.toBe('a');
    expect(typeof res.id).toBe('string');
    expect(res.name).toBe('Mine (copy)');
    const entries = await list();
    expect(entries).toHaveLength(2);
    expect(entries.find((e) => e.id === 'a')).toEqual(stored);
    expect(entries.find((e) => e.id === res.id)).toMatchObject({ name: 'Mine (copy)' });
  });

  it('a matching expectedSavedAt saves normally', async () => {
    const res = await save({ id: 'a', size: 5, grid: g }, { expectedSavedAt: T(1) });
    expect(res.forked).toBe(false);
    expect(res.id).toBe('a');
    expect(await list()).toHaveLength(1);
  });

  it('no stored entry for the id (deleted elsewhere) saves normally', async () => {
    const res = await save({ id: 'zz', size: 5, grid: g }, { expectedSavedAt: T(1) });
    expect(res.forked).toBe(false);
    expect(res.id).toBe('zz');
    expect(await list()).toHaveLength(2);
  });

  it('expectedSavedAt null skips the check', async () => {
    const res = await save({ id: 'a', size: 5, grid: g }, { expectedSavedAt: null });
    expect(res.forked).toBe(false);
  });
});

describe('legacy migration (§3.4, PD-6-G1)', () => {
  const blob = (extra) =>
    JSON.stringify({ id: 2, size: 5, grid: [[{ letter: 'Q' }]], ...extra });

  it('migrates the blob as "Saved grid", keeping its savedAt, then removes the legacy key', async () => {
    store.set(LEGACY_SAVE_KEY, blob({ savedAt: T(0) }));
    const entries = await list();
    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({ name: 'Saved grid', savedAt: T(0), size: 5 });
    expect(typeof entries[0].id).toBe('string');
    expect(localStorage.removeItem).toHaveBeenCalledWith(LEGACY_SAVE_KEY);
    expect(store.has(LEGACY_SAVE_KEY)).toBe(false);
    expect(await list()).toHaveLength(1);
  });

  it('id and savedAt: the blob savedAt wins when it is a string', async () => {
    store.set(LEGACY_SAVE_KEY, blob({ savedAt: T(0), timestamp: T(9) }));
    const [e] = await list();
    expect(e.savedAt).toBe(T(0));
    expect(e.id).toBe(`legacy-${T(0)}`);
  });

  it('id and savedAt: falls back to a string timestamp (the pre-save-machine shape)', async () => {
    store.set(LEGACY_SAVE_KEY, blob({ timestamp: '2026-09-01T08:00:00.000Z' }));
    const [e] = await list();
    expect(e.savedAt).toBe('2026-09-01T08:00:00.000Z');
    expect(e.id).toBe('legacy-2026-09-01T08:00:00.000Z');
  });

  it('id and savedAt: falls back to the epoch when neither is a string', async () => {
    store.set(LEGACY_SAVE_KEY, blob({ savedAt: 5, timestamp: null }));
    const [e] = await list();
    expect(e.savedAt).toBe('1970-01-01T00:00:00.000Z');
    expect(e.id).toBe('legacy-1970-01-01T00:00:00.000Z');
  });

  it('a corrupt legacy blob is not migrated, not removed, and does not throw', async () => {
    store.set(LEGACY_SAVE_KEY, '{ nope');
    await expect(list()).resolves.toEqual([]);
    expect(store.get(LEGACY_SAVE_KEY)).toBe('{ nope');
    expect(localStorage.removeItem).not.toHaveBeenCalled();
  });

  it('is idempotent when the legacy key removal fails once', async () => {
    store.set(LEGACY_SAVE_KEY, blob({ savedAt: T(0) }));
    localStorage.removeItem.mockImplementationOnce(() => {
      throw new Error('removeItem failed');
    });
    await list().catch(() => undefined);
    expect(store.has(LEGACY_SAVE_KEY)).toBe(true);
    const second = await list();
    expect(second).toHaveLength(1);
    expect(readArray()).toHaveLength(1);
    expect(store.has(LEGACY_SAVE_KEY)).toBe(false);
  });

  it('save() migrates in the same write and merges with the new entry', async () => {
    store.set(LEGACY_SAVE_KEY, blob({ savedAt: T(0) }));
    await save({ id: 'a', size: 5, grid: g });
    expect(readArray().map((e) => e.id)).toEqual(['a', `legacy-${T(0)}`]);
    expect(store.has(LEGACY_SAVE_KEY)).toBe(false);
  });

  it('save() whose array write fails rejects and leaves the legacy key in place', async () => {
    store.set(LEGACY_SAVE_KEY, blob({ savedAt: T(0) }));
    localStorage.setItem.mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    await expect(save({ id: 'a', size: 5, grid: g })).rejects.toThrow('QuotaExceededError');
    expect(store.has(LEGACY_SAVE_KEY)).toBe(true);
    expect(localStorage.removeItem).not.toHaveBeenCalled();
  });

  it('list() whose array write fails keeps the legacy key and does not reject', async () => {
    store.set(LEGACY_SAVE_KEY, blob({ savedAt: T(0) }));
    localStorage.setItem.mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    await expect(list()).resolves.toBeInstanceOf(Array);
    expect(store.has(LEGACY_SAVE_KEY)).toBe(true);
  });
});
