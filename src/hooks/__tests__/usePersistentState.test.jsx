/**
 * Tests for usePersistentState — the lazy-init-from-localStorage state hook
 * that both the dark-mode and symmetry toggles use.
 *
 * NOTE: setupTests.js replaces global.localStorage with a no-op vi.fn() mock
 * (getItem returns undefined, setItem stores nothing). We back that mock with a
 * real in-memory Map here so persistence is genuinely exercised — otherwise
 * assertions pass trivially against a dead stub.
 *
 * The load-bearing test is `does not clobber a stored value on mount`: it is the
 * regression guard for the bug this hook exists to prevent (default clobbering
 * the stored value before it is read). Reverting the hook to a
 * `useState(default) + read-on-mount effect` shape must fail that test.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePersistentState } from '../usePersistentState';

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
  localStorage.clear.mockImplementation(() => {
    store.clear();
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('usePersistentState', () => {
  it('lazy-initializes from a stored value (JSON default codec)', () => {
    localStorage.setItem('k', JSON.stringify({ a: 1 }));
    const { result } = renderHook(() => usePersistentState('k', { a: 0 }));
    expect(result.current[0]).toEqual({ a: 1 });
  });

  it('falls back to the default when the key is absent, and persists it', () => {
    const { result } = renderHook(() => usePersistentState('k', 7));
    expect(result.current[0]).toBe(7);
    // Mount effect writes the default so the key now exists.
    expect(localStorage.getItem('k')).toBe(JSON.stringify(7));
  });

  it('does NOT clobber a stored value on mount (the mount-race regression guard)', () => {
    // Stored 'false', default 'true' — the old two-effect shape wrote the
    // default over this before reading it. The hook must preserve 'false'.
    localStorage.setItem('sym', JSON.stringify(false));
    const { result } = renderHook(() => usePersistentState('sym', true));

    // Value reflects storage, not the default...
    expect(result.current[0]).toBe(false);
    // ...and after the mount persist effect runs, storage still says false.
    expect(localStorage.getItem('sym')).toBe(JSON.stringify(false));
  });

  it('persists on setValue', () => {
    const { result } = renderHook(() => usePersistentState('k', 1));
    act(() => {
      result.current[1](42);
    });
    expect(result.current[0]).toBe(42);
    expect(localStorage.getItem('k')).toBe(JSON.stringify(42));
  });

  it('supports the setter-function form', () => {
    localStorage.setItem('n', JSON.stringify(10));
    const { result } = renderHook(() => usePersistentState('n', 0));
    act(() => {
      result.current[1]((prev) => prev + 5);
    });
    expect(result.current[0]).toBe(15);
    expect(localStorage.getItem('n')).toBe(JSON.stringify(15));
  });

  it('honors a custom parse/serialize codec (dark-mode style boolean<->string)', () => {
    localStorage.setItem('xw_theme', 'dark');
    const codec = { parse: (v) => v === 'dark', serialize: (v) => (v ? 'dark' : 'light') };
    const { result } = renderHook(() => usePersistentState('xw_theme', false, codec));

    expect(result.current[0]).toBe(true); // 'dark' parsed to boolean true
    act(() => {
      result.current[1](false);
    });
    expect(localStorage.getItem('xw_theme')).toBe('light'); // serialized back to string
  });

  it('falls back to default when the stored value is unparseable, without throwing', () => {
    localStorage.setItem('k', '{not json');
    const { result } = renderHook(() => usePersistentState('k', 'fallback'));
    expect(result.current[0]).toBe('fallback');
  });

  it('does not throw when a persist write fails (quota)', () => {
    // Make the backing setItem reject writes to simulate a full quota.
    localStorage.setItem.mockImplementation(() => {
      throw new DOMException('QuotaExceededError');
    });
    const { result } = renderHook(() => usePersistentState('k', 1));
    expect(() => {
      act(() => {
        result.current[1](2);
      });
    }).not.toThrow();
    expect(result.current[0]).toBe(2);
  });
});
