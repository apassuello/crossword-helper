/**
 * Tests for useSaveMachine (Task 7, Step 2) — the Bench save machine.
 *
 * Follows useHealth's fake-timer pattern: `storage.save`/`storage.load` are
 * mocked directly (not via a real backend) so `vi.advanceTimersByTimeAsync`
 * can flush the save promise's microtasks between 30s ticks. The hook calls
 * the REAL `useToasts()`, so `renderHook` is wrapped in a real `<ToastProvider>`
 * and the error toast is asserted through the DOM (error kind → role="alert").
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, screen } from '@testing-library/react';
import { useSaveMachine } from '../useSaveMachine';
import { ToastProvider } from '../../components/bench/Toast';
import storage from '../../lib/storage';

const wrapper = ({ children }) => <ToastProvider>{children}</ToastProvider>;

/** Render the machine as a controlled component (doc + isDirty are props). */
function renderMachine(initialProps) {
  return renderHook((props) => useSaveMachine(props), { initialProps, wrapper });
}

/** Flush a couple of promise microtask turns inside act() (no timer advance). */
const flush = () =>
  act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });

beforeEach(() => {
  vi.useFakeTimers();
  // Default: saves succeed, stamping the current (fake) clock so the saved
  // freshness label can age deterministically.
  vi.spyOn(storage, 'save').mockImplementation(() =>
    Promise.resolve({ savedAt: new Date().toISOString() })
  );
  vi.spyOn(storage, 'load').mockResolvedValue(null);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe('useSaveMachine', () => {
  // ---- F10 first (the subtle one) --------------------------------------
  it('F10: doc.id change clears the pending autosave — the old doc is never saved', async () => {
    const { result, rerender } = renderMachine({ doc: { id: 'a' }, isDirty: true });
    // Mounted dirty → armed for autosave.
    expect(result.current.status).toBe('dirty');

    // New grid loaded (id changes) and it is clean.
    rerender({ doc: { id: 'b' }, isDirty: false });
    expect(result.current.status).toBe('pristine');

    // The old doc's 30s timer must have been dropped: advancing does not save.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(storage.save).not.toHaveBeenCalled();
  });

  // ---- basic edges -----------------------------------------------------
  it('an edit (isDirty false→true) marks the machine dirty', () => {
    const { result, rerender } = renderMachine({ doc: { id: 'a' }, isDirty: false });
    expect(result.current.status).toBe('pristine');
    expect(result.current.savedLabel).toBe('');

    rerender({ doc: { id: 'a' }, isDirty: true });
    expect(result.current.status).toBe('dirty');
    expect(result.current.savedLabel).toBe('unsaved changes');
  });

  it('autosaves after 30s when dirty (dirty→saving→saved), calling storage.save once', async () => {
    const { result } = renderMachine({ doc: { id: 'a', v: 1 }, isDirty: true });
    expect(result.current.status).toBe('dirty');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe('saved');
  });

  it('does NOT autosave from pristine (no timer armed)', async () => {
    renderMachine({ doc: { id: 'a' }, isDirty: false });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(storage.save).not.toHaveBeenCalled();
  });

  it('on success → saved with savedAt, and the timer is cleared (no re-save at the next 30s)', async () => {
    const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe('saved');
    expect(result.current.savedLabel).toBe('saved locally · just now');

    // A second 30s must NOT trigger another save.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(storage.save).toHaveBeenCalledTimes(1);
  });

  it('on reject → error + red toast, and the retry re-arms so the next 30s saves again', async () => {
    storage.save.mockRejectedValue(new Error('offline'));
    const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe('error');
    expect(result.current.savedLabel).toBe('offline — will retry');

    // pushToast({kind:'error'}) surfaced as a role="alert" toast.
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();

    // Retry timer re-armed: the next 30s attempts the save again.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(storage.save).toHaveBeenCalledTimes(2);
  });

  it('does not reset the timer per keystroke: two content edits within 30s → exactly one save of the latest doc', async () => {
    const { rerender } = renderMachine({ doc: { id: 'x', v: 1 }, isDirty: false });
    // clean → dirty: arms the single timer.
    rerender({ doc: { id: 'x', v: 1 }, isDirty: true });
    // Two more edits (same id, still dirty) — must NOT re-arm the timer.
    rerender({ doc: { id: 'x', v: 2 }, isDirty: true });
    rerender({ doc: { id: 'x', v: 3 }, isDirty: true });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(storage.save).toHaveBeenLastCalledWith(
      expect.objectContaining({ v: 3 }),
      expect.anything()
    );
  });

  it('manual save() goes saving→saved immediately, without waiting 30s', async () => {
    const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
    expect(result.current.status).toBe('dirty');

    act(() => {
      result.current.save();
    });
    expect(result.current.status).toBe('saving');
    expect(result.current.savedLabel).toBe('saving…'); // exact ellipsis glyph

    await flush();
    expect(storage.save).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe('saved');
  });

  it('after saved, isDirty going true again returns to dirty', async () => {
    const { result, rerender } = renderMachine({ doc: { id: 'a' }, isDirty: true });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(result.current.status).toBe('saved');

    // Parent marks the doc clean after the save…
    rerender({ doc: { id: 'a' }, isDirty: false });
    expect(result.current.status).toBe('saved'); // no-op: label preserved

    // …then a fresh edit re-dirties it.
    rerender({ doc: { id: 'a' }, isDirty: true });
    expect(result.current.status).toBe('dirty');
  });

  it('the saved label ages from "just now" to "1m ago" over 60s without a new save', async () => {
    const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(result.current.status).toBe('saved');
    expect(result.current.savedLabel).toBe('saved locally · just now');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(result.current.savedLabel).toBe('saved locally · 1m ago');
    expect(storage.save).toHaveBeenCalledTimes(1); // the tick is not a save
  });

  it('unmount clears the autosave timer — no later save, no act warnings', async () => {
    const { unmount } = renderMachine({ doc: { id: 'a' }, isDirty: true });

    unmount();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(storage.save).not.toHaveBeenCalled();
  });

  // ---- Task 6.6: named save, fork, adopted savedAt (novice-readiness spec 0.2.7 §3.4) ----
  describe('named save, fork and adopted savedAt', () => {
    const QUOTA = 'Could not save: browser storage is full. Delete a saved grid or export this one.';
    const RETRY = 'Couldn’t save — will retry.';

    const tick30 = () =>
      act(async () => {
        await vi.advanceTimersByTimeAsync(30000);
      });

    it('T1: autosave calls storage.save(doc, { expectedSavedAt: null }) with no name', async () => {
      renderMachine({ doc: { id: 'a' }, isDirty: true });
      await tick30();
      expect(storage.save).toHaveBeenCalledTimes(1);
      const [, opts] = storage.save.mock.calls[0];
      expect(opts).toEqual({ expectedSavedAt: null });
      expect('name' in opts).toBe(false);
    });

    it('T2: after adoptSavedAt("T1") autosave sends expectedSavedAt "T1"', async () => {
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      act(() => result.current.adoptSavedAt('T1'));
      await tick30();
      expect(storage.save.mock.calls[0][1]).toEqual({ expectedSavedAt: 'T1' });
    });

    it('adoptSavedAt does not change status', () => {
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      act(() => result.current.adoptSavedAt('T1'));
      expect(result.current.status).toBe('dirty');
    });

    it('a successful save records its savedAt as the next expectedSavedAt', async () => {
      storage.save.mockResolvedValue({ savedAt: 'S1', id: 'a', name: 'n', forked: false });
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      await tick30();
      await act(async () => {
        await result.current.save();
      });
      expect(storage.save.mock.calls[1][1]).toEqual({ expectedSavedAt: 'S1' });
    });

    it('T3: a failed autosave keeps the retry toast, label and +30s re-arm', async () => {
      storage.save.mockRejectedValue(new Error('x'));
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      await tick30();
      expect(screen.getByRole('alert')).toHaveTextContent(RETRY);
      expect(result.current.savedLabel).toBe('offline — will retry');
      await tick30();
      expect(storage.save).toHaveBeenCalledTimes(2);
    });

    it('T4: saveNamed forwards the name, resolves true and goes saved', async () => {
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      let ok;
      await act(async () => {
        ok = await result.current.saveNamed('Puzzle');
      });
      expect(ok).toBe(true);
      expect(storage.save.mock.calls[0][1].name).toBe('Puzzle');
      expect(result.current.status).toBe('saved');
    });

    it('T5: saveNamed forwards replaceEntryId', async () => {
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      await act(async () => {
        await result.current.saveNamed('Puzzle', { replaceEntryId: 'b' });
      });
      expect(storage.save.mock.calls[0][1].replaceEntryId).toBe('b');
    });

    it('saveNamed clears the pending autosave timer (no second save at +30s)', async () => {
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      await act(async () => {
        await result.current.saveNamed('Puzzle');
      });
      await tick30();
      expect(storage.save).toHaveBeenCalledTimes(1);
    });

    it('T6: a rejected saveNamed shows the quota toast only, resolves false, status error', async () => {
      storage.save.mockRejectedValue(new Error('quota'));
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      let ok;
      await act(async () => {
        ok = await result.current.saveNamed('Puzzle');
      });
      expect(ok).toBe(false);
      expect(result.current.status).toBe('error');
      const alerts = screen.getAllByRole('alert');
      expect(alerts).toHaveLength(1);
      expect(alerts[0]).toHaveTextContent(QUOTA);
      expect(screen.queryByText(RETRY)).toBeNull();
    });

    it('PD-6-G6: after a failed explicit save the 30 s autosave re-arm continues, with no second toast', async () => {
      storage.save.mockRejectedValueOnce(new Error('quota'));
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      await act(async () => {
        await result.current.saveNamed('Puzzle');
      });
      expect(storage.save).toHaveBeenCalledTimes(1);
      await tick30();
      expect(storage.save).toHaveBeenCalledTimes(2);
      expect('name' in storage.save.mock.calls[1][1]).toBe(false);
      expect(result.current.status).toBe('saved');
      expect(screen.queryByText(RETRY)).toBeNull();
    });

    it('T9: a forked result calls onForked once and the next save uses its savedAt', async () => {
      const onForked = vi.fn();
      storage.save.mockResolvedValueOnce({
        forked: true,
        id: 'n',
        name: 'X (copy)',
        savedAt: 'T9',
      });
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true, onForked });
      await tick30();
      expect(onForked).toHaveBeenCalledTimes(1);
      expect(onForked).toHaveBeenCalledWith({ id: 'n', name: 'X (copy)' });
      await act(async () => {
        await result.current.save();
      });
      expect(storage.save.mock.calls[1][1]).toEqual({ expectedSavedAt: 'T9' });
    });

    it('a forked saveNamed also calls onForked and resolves true', async () => {
      const onForked = vi.fn();
      storage.save.mockResolvedValueOnce({
        forked: true,
        id: 'n',
        name: 'X (copy)',
        savedAt: 'T9',
      });
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true, onForked });
      let ok;
      await act(async () => {
        ok = await result.current.saveNamed('X');
      });
      expect(ok).toBe(true);
      expect(onForked).toHaveBeenCalledWith({ id: 'n', name: 'X (copy)' });
    });

    it('a doc.id change does not reset an adoptSavedAt made in the same act', async () => {
      const { result, rerender } = renderMachine({ doc: { id: 'a' }, isDirty: false });
      act(() => {
        rerender({ doc: { id: 'b' }, isDirty: false });
        result.current.adoptSavedAt('T5');
      });
      await act(async () => {
        await result.current.save();
      });
      expect(storage.save.mock.calls[0][1]).toEqual({ expectedSavedAt: 'T5' });
    });
  });

  describe('onSaved (novice-readiness spec 0.2.7 §3.4 (S2))', () => {
    it('is called once with the exact doc object handed to storage.save', async () => {
      const onSaved = vi.fn();
      const doc = { id: 'a' };
      const { result } = renderMachine({ doc, isDirty: true, onSaved });
      await act(async () => {
        await result.current.saveNamed('N');
      });
      expect(onSaved).toHaveBeenCalledTimes(1);
      expect(onSaved.mock.calls[0][0]).toBe(storage.save.mock.calls[0][0]);
      expect(onSaved.mock.calls[0][0]).toBe(doc);
    });

    it('a parent that is still dirty after onSaved keeps the machine dirty and re-arms autosave', async () => {
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true, onSaved: vi.fn() });
      await act(async () => {
        await result.current.saveNamed('N');
      });
      expect(result.current.status).toBe('dirty');
      await act(async () => {
        await vi.advanceTimersByTimeAsync(30000);
      });
      expect(storage.save).toHaveBeenCalledTimes(2);
    });

    it('a throwing onSaved cannot make saveNamed reject or leave status at saving', async () => {
      const onSaved = vi.fn(() => {
        throw new Error('boom');
      });
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: false, onSaved });
      let ok;
      await act(async () => {
        ok = await result.current.saveNamed('N');
      });
      expect(ok).toBe(true);
      expect(result.current.status).toBe('saved');
    });

    it('a throwing onForked cannot make saveNamed reject or leave status at saving', async () => {
      storage.save.mockResolvedValue({ savedAt: 's', id: 'n', name: 'X (copy)', forked: true });
      const onForked = vi.fn(() => {
        throw new Error('boom');
      });
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true, onForked });
      let ok;
      await act(async () => {
        ok = await result.current.saveNamed('X');
      });
      expect(ok).toBe(true);
      expect(result.current.status).toBe('saved');
    });
  });
});
