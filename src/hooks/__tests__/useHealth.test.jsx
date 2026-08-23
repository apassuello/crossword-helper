/**
 * Tests for useHealth (Task 6) — top-bar health-dot data source.
 *
 * Establishes the fake-timer pattern for this repo: `api.health` is mocked
 * directly (not via MSW) so `vi.advanceTimersByTimeAsync` can flush the
 * promise microtasks between 30s ticks without a fragile MSW+fake-timers dance.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useHealth } from '../useHealth';
import { api, ApiError } from '../../api/client';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('useHealth', () => {
  it('polls api.health once immediately on mount', async () => {
    vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });

    renderHook(() => useHealth());
    expect(api.health).toHaveBeenCalledTimes(1);

    // Flush the resolved promise's state update inside act() so React doesn't warn.
    await act(async () => {
      await Promise.resolve();
    });
  });

  it('reports online, not degraded for a healthy body', async () => {
    vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });

    const { result } = renderHook(() => useHealth());
    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current).toEqual({ online: true, degraded: false });
  });

  it('reports offline, not degraded when the fetch rejects (NETWORK)', async () => {
    const health = vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });

    const { result } = renderHook(() => useHealth());
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current).toEqual({ online: true, degraded: false });
    expect(health).toHaveBeenCalledTimes(1);

    health.mockRejectedValueOnce(new ApiError({ code: 'NETWORK', status: 0 }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(health).toHaveBeenCalledTimes(2);
    expect(result.current).toEqual({ online: false, degraded: false });
  });

  it('reports online + degraded for a 503 degraded body', async () => {
    vi.spyOn(api, 'health').mockResolvedValue({ status: 'degraded' });

    const { result } = renderHook(() => useHealth());
    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current).toEqual({ online: true, degraded: true });
  });

  it('treats an unparseable/unknown body as offline (red dot, not a crash)', async () => {
    const health = vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });

    const { result } = renderHook(() => useHealth());
    await act(async () => {
      await Promise.resolve();
    });
    // Establish a distinct baseline so the next assertion proves a real flip,
    // not a match against the hook's untouched initial state.
    expect(result.current).toEqual({ online: true, degraded: false });
    expect(health).toHaveBeenCalledTimes(1);

    // Second tick: empty body — no `status` key at all (unparseable/empty JSON).
    health.mockResolvedValueOnce({});
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(health).toHaveBeenCalledTimes(2);
    expect(result.current).toEqual({ online: false, degraded: false });

    // Third tick: back to healthy, to prove the dot can recover...
    health.mockResolvedValueOnce({ status: 'healthy' });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(health).toHaveBeenCalledTimes(3);
    expect(result.current).toEqual({ online: true, degraded: false });

    // ...then a fourth tick: an unrecognized (but non-empty) status string
    // must ALSO fall through to offline, not just an absent key.
    health.mockResolvedValueOnce({ status: 'weird' });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(health).toHaveBeenCalledTimes(4);
    expect(result.current).toEqual({ online: false, degraded: false });
  });

  it('is red before the first poll resolves (no optimistic-green boot)', () => {
    // A never-resolving promise: the hook must not have started green.
    vi.spyOn(api, 'health').mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useHealth());

    expect(result.current).toEqual({ online: false, degraded: false });
  });

  it('polls again after 30s, and a later rejection flips online true -> false', async () => {
    const health = vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });

    const { result } = renderHook(() => useHealth());
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current).toEqual({ online: true, degraded: false });
    expect(health).toHaveBeenCalledTimes(1);

    // Second tick still healthy.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(health).toHaveBeenCalledTimes(2);
    expect(result.current).toEqual({ online: true, degraded: false });

    // Third tick: backend drops off the network.
    health.mockRejectedValueOnce(new ApiError({ code: 'NETWORK', status: 0 }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(health).toHaveBeenCalledTimes(3);
    expect(result.current).toEqual({ online: false, degraded: false });
  });

  it('clears the interval on unmount — no further polls, no act warnings', async () => {
    const health = vi.spyOn(api, 'health').mockResolvedValue({ status: 'healthy' });

    const { unmount } = renderHook(() => useHealth());
    await act(async () => {
      await Promise.resolve();
    });
    expect(health).toHaveBeenCalledTimes(1);

    unmount();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(health).toHaveBeenCalledTimes(1);
  });
});
