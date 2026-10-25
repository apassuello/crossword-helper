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
import storage, { SAVE_KEY } from '../../lib/storage';

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

// What storage.save was handed, with its function-form arguments (resolved inside the lock
// by the real storage) resolved at call time, as the lock would: [doc, opts] per call.
let saveCalls;

const recordSave = (doc, opts) =>
  saveCalls.push([
    typeof doc === 'function' ? doc() : doc,
    typeof opts === 'function' ? opts() : opts,
  ]);

/** storage.save answers `value` (resolved or rejected, once or always) and still records its call. */
function saveImpl(kind, once, value) {
  const impl = (doc, opts) => {
    recordSave(doc, opts);
    return kind === 'resolve' ? Promise.resolve(value) : Promise.reject(value);
  };
  return once ? storage.save.mockImplementationOnce(impl) : storage.save.mockImplementation(impl);
}

beforeEach(() => {
  vi.useFakeTimers();
  saveCalls = [];
  // Default: saves succeed, stamping the current (fake) clock so the saved
  // freshness label can age deterministically.
  vi.spyOn(storage, 'save').mockImplementation((doc, opts) => {
    recordSave(doc, opts);
    return Promise.resolve({ savedAt: new Date().toISOString() });
  });
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
    saveImpl('reject', false, new Error('offline'));
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
    expect(saveCalls.at(-1)[0]).toEqual(expect.objectContaining({ v: 3 }));
    expect(saveCalls.at(-1)[1]).toBeTruthy();
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
      const [, opts] = saveCalls[0];
      expect(opts).toEqual({ expectedSavedAt: null });
      expect('name' in opts).toBe(false);
    });

    it('T2: after adoptSavedAt("T1") autosave sends expectedSavedAt "T1"', async () => {
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      act(() => result.current.adoptSavedAt('T1'));
      await tick30();
      expect(saveCalls[0][1]).toEqual({ expectedSavedAt: 'T1' });
    });

    it('adoptSavedAt does not change status', () => {
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      act(() => result.current.adoptSavedAt('T1'));
      expect(result.current.status).toBe('dirty');
    });

    it('a successful save records its savedAt as the next expectedSavedAt', async () => {
      saveImpl('resolve', false, { savedAt: 'S1', id: 'a', name: 'n', forked: false });
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      await tick30();
      await act(async () => {
        await result.current.save();
      });
      expect(saveCalls[1][1]).toEqual({ expectedSavedAt: 'S1' });
    });

    it('T3: a failed autosave keeps the retry toast, label and +30s re-arm', async () => {
      saveImpl('reject', false, new Error('x'));
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
      expect(saveCalls[0][1].name).toBe('Puzzle');
      expect(result.current.status).toBe('saved');
    });

    it('T5: saveNamed forwards replaceEntryId', async () => {
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      await act(async () => {
        await result.current.saveNamed('Puzzle', { replaceEntryId: 'b' });
      });
      expect(saveCalls[0][1].replaceEntryId).toBe('b');
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
      saveImpl('reject', false, new Error('quota'));
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
      saveImpl('reject', true, new Error('quota'));
      const { result } = renderMachine({ doc: { id: 'a' }, isDirty: true });
      await act(async () => {
        await result.current.saveNamed('Puzzle');
      });
      expect(storage.save).toHaveBeenCalledTimes(1);
      await tick30();
      expect(storage.save).toHaveBeenCalledTimes(2);
      expect('name' in saveCalls[1][1]).toBe(false);
      expect(result.current.status).toBe('saved');
      expect(screen.queryByText(RETRY)).toBeNull();
    });

    it('T9: a forked result calls onForked once and the next save uses its savedAt', async () => {
      const onForked = vi.fn();
      saveImpl('resolve', true, {
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
      expect(saveCalls[1][1]).toEqual({ expectedSavedAt: 'T9' });
    });

    it('a forked saveNamed also calls onForked and resolves true', async () => {
      const onForked = vi.fn();
      saveImpl('resolve', true, {
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
      expect(saveCalls[0][1]).toEqual({ expectedSavedAt: 'T5' });
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
      expect(onSaved.mock.calls[0][0]).toBe(saveCalls[0][0]);
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
      saveImpl('resolve', false, { savedAt: 's', id: 'n', name: 'X (copy)', forked: true });
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

// novice-readiness spec 0.2.8 §3.4 (Q1, Q3): forget() and the pagehide save.
describe('useSaveMachine forget() (§3.4 Q1)', () => {
  it('reads "unsaved changes" and arms nothing; the next real edit arms the autosave', async () => {
    const { result, rerender } = renderMachine({ doc: { id: 'a' }, isDirty: false });
    expect(result.current.savedLabel).toBe('');
    act(() => result.current.forget());
    expect(result.current.savedLabel).toBe('unsaved changes');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(storage.save).not.toHaveBeenCalled();

    rerender({ doc: { id: 'a' }, isDirty: true });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(storage.save).toHaveBeenCalledTimes(1);
  });

  it('clears an autosave already pending', async () => {
    const { result, rerender } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true });
    act(() => result.current.forget());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(storage.save).not.toHaveBeenCalled();
    expect(result.current.savedLabel).toBe('unsaved changes');

    // Already dirty when forgotten, so there is no clean->dirty edge: the next change to
    // `doc` must arm the autosave itself (spec 0.2.9 §3.4 (Q1)).
    rerender({ doc: { id: 'a', n: 2 }, isDirty: true });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(storage.save).toHaveBeenCalledTimes(1);
  });

  it('leaves saved state to a later save: from saved it reads unsaved, a real edit re-saves', async () => {
    const { result, rerender } = renderMachine({ doc: { id: 'a' }, isDirty: true });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    rerender({ doc: { id: 'a' }, isDirty: false });
    expect(result.current.status).toBe('saved');
    act(() => result.current.forget());
    expect(result.current.savedLabel).toBe('unsaved changes');
    rerender({ doc: { id: 'a' }, isDirty: true });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    expect(storage.save).toHaveBeenCalledTimes(2);
  });
});

describe('useSaveMachine pagehide (§3.4 Q3)', () => {
  beforeEach(() => {
    // The pagehide path writes through the synchronous entry point, never storage.save.
    vi.spyOn(storage, 'saveSync').mockImplementation(() => ({ savedAt: new Date().toISOString() }));
  });
  const pagehide = () => act(async () => {
    window.dispatchEvent(new Event('pagehide'));
    await Promise.resolve();
  });

  it('a dirty document is saved at once and the pending timer is cleared', async () => {
    renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true });
    expect(storage.saveSync).not.toHaveBeenCalled();
    await pagehide();
    expect(storage.saveSync).toHaveBeenCalledTimes(1);
    expect(storage.saveSync.mock.calls[0][0]).toEqual({ id: 'a', n: 1 });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });
    expect(storage.saveSync).toHaveBeenCalledTimes(1);
  });

  it('saves the latest doc, not the one at mount', async () => {
    const { rerender } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true });
    rerender({ doc: { id: 'a', n: 2 }, isDirty: true });
    await pagehide();
    expect(storage.saveSync.mock.calls[0][0]).toEqual({ id: 'a', n: 2 });
  });

  it('a clean document writes nothing', async () => {
    renderMachine({ doc: { id: 'a' }, isDirty: false });
    await pagehide();
    expect(storage.saveSync).not.toHaveBeenCalled();
  });

  it('a failed write shows no toast', async () => {
    storage.saveSync.mockImplementation(() => {
      throw new Error('quota');
    });
    renderMachine({ doc: { id: 'a' }, isDirty: true });
    await pagehide();
    await flush();
    expect(storage.saveSync).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('the listener is removed on unmount', async () => {
    const { unmount } = renderMachine({ doc: { id: 'a' }, isDirty: true });
    unmount();
    await pagehide();
    expect(storage.saveSync).not.toHaveBeenCalled();
  });

  it('writes synchronously within the event dispatch, through saveSync and never storage.save', () => {
    renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true });
    act(() => {
      window.dispatchEvent(new Event('pagehide'));
      // no await: the write must already have happened (spec 0.2.9 §3.4)
      expect(storage.saveSync).toHaveBeenCalledTimes(1);
    });
    expect(storage.save).not.toHaveBeenCalled();
  });
});

// novice-readiness spec 0.2.9 §3.4 (S4), §2.3 (M1): since Task 6.19 a save resolves only
// after its Web Lock is granted, so a click can land between the machine reading `docRef` and
// the resolution. These tests run the REAL storage behind a deferred FIFO lock stub.
describe('useSaveMachine: a save resolution only acts on the document it wrote', () => {
  const S0 = '2026-10-01T10:00:00.000Z';
  const S1 = '2026-10-01T11:00:00.000Z';
  let store;
  const stored = () => JSON.parse(store.get(SAVE_KEY) ?? '[]');
  const seed = (...entries) => store.set(SAVE_KEY, JSON.stringify(entries));
  const entry = (id, savedAt) => ({ id, name: id.toUpperCase(), savedAt, size: 5, grid: [] });
  // Runs every lock request queued so far, in order (timers 1 ms out, FIFO).
  const flushLocks = () =>
    act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
  // Fires the next pending timer only: the autosave timer, leaving its lock request queued.
  const fireAutosave = () =>
    act(async () => {
      await vi.advanceTimersToNextTimerAsync();
    });
  // What the Delete button does: remove through the lock, and once that resolves forget().
  const deleteEntry = (result, id) =>
    storage.remove(id).then(() => act(async () => result.current.forget()));

  beforeEach(() => {
    storage.save.mockRestore(); // the file-level beforeEach mocks it; these tests use the real one
    store = new Map();
    localStorage.getItem.mockImplementation((k) => (store.has(k) ? store.get(k) : null));
    localStorage.setItem.mockImplementation((k, v) => {
      store.set(k, String(v));
    });
    localStorage.removeItem.mockImplementation((k) => {
      store.delete(k);
    });
    Object.defineProperty(navigator, 'locks', {
      configurable: true,
      // Brief's recipe with a 1 ms delay: fake timers turn a 0 ms delay into 1 ms only inside a
      // tick, so a request made from the autosave callback would otherwise queue behind one made
      // outside it and the lock would not be FIFO.
      value: { request: (n, fn) => new Promise((r) => setTimeout(() => r(fn()), 1)) },
    });
  });

  afterEach(() => {
    delete navigator.locks;
  });

  it('control, forward order: autosave, then Delete of the open entry, then flush -> deleted, "unsaved changes"', async () => {
    seed(entry('a', S0));
    const { result } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true });
    act(() => result.current.adoptSavedAt(S0));
    await fireAutosave();
    const deleting = deleteEntry(result, 'a'); // queued behind the save
    await flushLocks();
    await deleting;
    expect(stored().map((e) => e.id)).toEqual([]);
    expect(result.current.savedLabel).toBe('unsaved changes');
  });

  it('pinned as observed, reverse order: Delete queued, then the autosave fires, then flush', async () => {
    seed(entry('a', S0));
    const { result } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true });
    act(() => result.current.adoptSavedAt(S0));
    const deleting = deleteEntry(result, 'a'); // queued first
    act(() => {
      result.current.save(); // the autosave timer's path (runSave), queued second
    });
    await flushLocks();
    await deleting;
    await flushLocks();
    // Observed: the delete lands first, then the save writes the entry back under its own id
    // (spec: "a save whose entry no longer exists writes that entry"), so the label tells
    // the truth about storage.
    expect(stored().map((e) => e.id)).toEqual(['a']);
    expect(result.current.savedLabel).toMatch(/^saved locally/);
  });

  it('autosave of A, New grid (B) before the flush: B keeps its status, savedAt expectation and next save', async () => {
    seed(entry('a', S0), entry('b', S1));
    const onSaved = vi.fn();
    const { result, rerender } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true, onSaved });
    act(() => result.current.adoptSavedAt(S0));
    await fireAutosave();
    // Open saved B: setDocId and adoptSavedAt in one handler.
    rerender({ doc: { id: 'b', n: 1 }, isDirty: false, onSaved });
    act(() => result.current.adoptSavedAt(S1));
    await flushLocks();
    expect(stored().find((e) => e.id === 'a').savedAt).not.toBe(S0); // A's entry IS written
    expect(onSaved).not.toHaveBeenCalled();
    expect(result.current.status).toBe('pristine');
    expect(result.current.savedLabel).toBe('');

    rerender({ doc: { id: 'b', n: 2 }, isDirty: true, onSaved });
    const saving = vi.spyOn(storage, 'save');
    await fireAutosave();
    await flushLocks();
    // The function-form opts are resolved inside the lock; the stored entry shows what they read.
    expect(saving).toHaveBeenCalledTimes(1);
    expect(stored().find((e) => e.id === 'b').savedAt).not.toBe(S1);
    expect(stored().map((e) => e.name)).not.toContain('B (copy)');
  });

  it('autosave of A that will fork, New grid (B) before the flush: onForked is not called', async () => {
    seed(entry('a', S1)); // a second tab moved A's savedAt
    const onForked = vi.fn();
    const { result, rerender } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true, onForked });
    act(() => result.current.adoptSavedAt(S0));
    await fireAutosave();
    rerender({ doc: { id: 'b', n: 1 }, isDirty: false, onForked });
    await flushLocks();
    expect(stored().some((e) => e.name === 'A (copy)')).toBe(true); // the fork was written
    expect(onForked).not.toHaveBeenCalled();
    expect(result.current.status).toBe('pristine');
  });

  it('a failed save of a replaced document leaves the new document\'s status alone', async () => {
    const { result, rerender } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true });
    const failing = vi.spyOn(storage, 'save').mockImplementation(
      () => new Promise((_, reject) => setTimeout(() => reject(new Error('quota')), 1))
    );
    await fireAutosave();
    rerender({ doc: { id: 'b', n: 1 }, isDirty: false });
    await flushLocks();
    expect(failing).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe('pristine');
    expect(result.current.savedLabel).toBe('');
  });

  it('a save of the still-current document acts as before (onSaved, saved, fork callback)', async () => {
    seed(entry('a', S1));
    const onSaved = vi.fn();
    const onForked = vi.fn();
    const { result } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true, onSaved, onForked });
    act(() => result.current.adoptSavedAt(S0));
    await fireAutosave();
    await flushLocks();
    expect(onSaved).toHaveBeenCalledTimes(1);
    expect(onForked).toHaveBeenCalledTimes(1);
  });

  // ---- I1 (Phase 6R final review): two saves of one document queued behind the lock ----
  // A save builds `expectedSavedAt` and snapshots its document when it EXECUTES inside the lock
  // (novice-readiness spec 0.2.9 §3.4 (S4)), so a write that landed first never forks it.
  const flushAllLocks = async () => {
    for (let i = 0; i < 4; i += 1) await flushLocks();
  };

  it('I1: autosave queued on the lock, then a named Save of the same document -> one entry, no fork', async () => {
    seed(entry('a', S0));
    const onForked = vi.fn();
    const { result } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true, onForked });
    act(() => result.current.adoptSavedAt(S0));
    await fireAutosave();
    let named;
    act(() => {
      named = result.current.saveNamed('A');
    });
    await flushAllLocks();
    await expect(named).resolves.toBe(true);
    expect(stored().map((e) => e.name)).toEqual(['A']);
    expect(onForked).not.toHaveBeenCalled();
  });

  it('I1: pagehide (saveSync) while an autosave is queued on the lock, page survives -> no fork', async () => {
    seed(entry('a', S0));
    const onForked = vi.fn();
    const { result } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true, onForked });
    act(() => result.current.adoptSavedAt(S0));
    await fireAutosave(); // queued, not granted
    act(() => {
      window.dispatchEvent(new Event('pagehide')); // saveSync writes at once, outside the lock
    });
    await flushAllLocks();
    expect(stored().map((e) => e.id)).toEqual(['a']);
    expect(onForked).not.toHaveBeenCalled();
  });

  it('I1: a brand-new id with a stale known savedAt: the chosen name lands on the entry, not a copy', async () => {
    const onForked = vi.fn();
    const { result } = renderMachine({ doc: { id: 'b', n: 1 }, isDirty: true, onForked });
    act(() => result.current.adoptSavedAt(S0)); // left over from the previous document
    await fireAutosave();
    let named;
    act(() => {
      named = result.current.saveNamed('Bee');
    });
    await flushAllLocks();
    await named;
    expect(stored().map((e) => e.name)).toEqual(['Bee']);
    expect(onForked).not.toHaveBeenCalled();
  });

  it('I1: a named save keeps its name and replaceEntryId when queued behind an autosave', async () => {
    seed(entry('a', S0), entry('old', S0));
    const { result } = renderMachine({ doc: { id: 'a', n: 1 }, isDirty: true });
    act(() => result.current.adoptSavedAt(S0));
    await fireAutosave();
    act(() => {
      result.current.saveNamed('Renamed', { replaceEntryId: 'old' });
    });
    await flushAllLocks();
    expect(stored().map((e) => e.id).sort()).toEqual(['a']);
    expect(stored()[0].name).toBe('Renamed');
  });
});
