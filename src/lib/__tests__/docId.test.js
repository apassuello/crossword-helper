import { describe, it, expect, vi, afterEach } from 'vitest';
import { mintDocId } from '../docId';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('mintDocId', () => {
  it('returns what crypto.randomUUID returned, one fresh value per call', () => {
    const uuids = ['uuid-one', 'uuid-two'];
    const randomUUID = vi.fn(() => uuids.shift());
    vi.stubGlobal('crypto', { randomUUID });

    const a = mintDocId();
    const b = mintDocId();

    expect(randomUUID).toHaveBeenCalledTimes(2);
    expect(a).toBe('uuid-one');
    expect(b).toBe('uuid-two');
    expect(a).not.toBe(b);
  });

  it('falls back to unique non-empty strings when randomUUID is undefined', () => {
    vi.stubGlobal('crypto', { randomUUID: undefined });

    const ids = Array.from({ length: 50 }, () => mintDocId());

    ids.forEach((id) => {
      expect(typeof id).toBe('string');
      expect(id.length).toBeGreaterThan(0);
    });
    expect(new Set(ids).size).toBe(50);
  });

  it('falls back when there is no crypto object at all', () => {
    vi.stubGlobal('crypto', undefined);

    const a = mintDocId();
    const b = mintDocId();

    expect(typeof a).toBe('string');
    expect(a.length).toBeGreaterThan(0);
    expect(a).not.toBe(b);
  });

  it('falls back when randomUUID is present but not a function', () => {
    vi.stubGlobal('crypto', { randomUUID: 'nope' });

    const a = mintDocId();
    const b = mintDocId();

    expect(a.length).toBeGreaterThan(0);
    expect(a).not.toBe(b);
  });

  it('fallback ids stay unique even with the clock and Math.random frozen', () => {
    vi.stubGlobal('crypto', undefined);
    vi.spyOn(Date, 'now').mockReturnValue(1_700_000_000_000);
    vi.spyOn(Math, 'random').mockReturnValue(0.5);

    const ids = Array.from({ length: 20 }, () => mintDocId());

    expect(new Set(ids).size).toBe(20);
  });
});
