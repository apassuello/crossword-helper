/**
 * useSaveMachine — the Bench "save machine" (Task 7, Step 2).
 * Spec 06 §3 (reconciled — see Task 7).
 *
 * A five-state machine that debounces edits into autosaves and surfaces a
 * single derived status label for the TopBar:
 *
 *   pristine → dirty → saving → saved
 *              saving --fail--> error   (dirty-variant; auto-retries)
 *
 * It reaches persistence ONLY through `storage.save` (never localStorage
 * directly) so M2 can swap the transport to `POST /api/grid/save` without
 * touching this file. It is driven by two controlled props:
 *   - `doc`     : the serializable grid document, carrying a stable `id`.
 *   - `isDirty` : parent-owned "there are unsaved changes" flag.
 *
 * Key invariants (mirroring useHealth's timer/cleanup discipline):
 *   - Entering `dirty` arms exactly ONE 30s autosave timer. Further edits
 *     while already dirty (same doc.id, isDirty stays true) keep the SAME
 *     timer — no per-keystroke reset, so a fast typist can't starve autosave.
 *   - `doc.id` changing (F10 "new grid") clears the pending timer and re-derives
 *     state from the new doc's `isDirty`; the previous doc is NEVER saved.
 *   - Labels are derived every render from state, never stored as a string.
 *
 * Parent contract: after a successful save the parent should flip `isDirty`
 * back to false (the doc is now clean); the next edit then flips it true again,
 * which this machine reads as the `saved → dirty` transition.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import storage from '../lib/storage';
import { useToasts } from '../components/bench/Toast';

const AUTOSAVE_MS = 30000;
const SAVED_TICK_MS = 60000;

/** Derive the "saved locally · …" freshness label from a savedAt timestamp. */
function savedFreshnessLabel(savedAt, now) {
  if (!savedAt) return 'saved locally · just now';
  const ageMs = now - new Date(savedAt).getTime();
  if (ageMs < SAVED_TICK_MS) return 'saved locally · just now';
  return `saved locally · ${Math.floor(ageMs / SAVED_TICK_MS)}m ago`;
}

/**
 * @param {{doc: {id: string}, isDirty: boolean}} params
 * @returns {{status: 'pristine'|'dirty'|'saving'|'saved'|'error', savedLabel: string, save: () => Promise<void>}}
 */
export function useSaveMachine({ doc, isDirty }) {
  const { pushToast } = useToasts();

  const [status, setStatus] = useState('pristine');
  const [savedAt, setSavedAt] = useState(null);
  const [tick, setTick] = useState(0); // forces the saved-label to re-derive

  const timerRef = useRef(null); // pending autosave timeout id
  const docRef = useRef(doc); // always the latest doc, read at fire time
  const mountedRef = useRef(true);
  const prevIdRef = useRef(undefined); // previous doc.id (F10 detection)
  const prevDirtyRef = useRef(false); // previous isDirty (edge detection)
  const runSaveRef = useRef(() => {}); // latest runSave, called by timer + button

  docRef.current = doc;

  function clearAutosave() {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  function armAutosave() {
    clearAutosave();
    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      runSaveRef.current();
    }, AUTOSAVE_MS);
  }

  function runSave() {
    clearAutosave(); // this attempt consumes any pending timer
    setStatus('saving');
    return storage.save(docRef.current).then(
      ({ savedAt: at }) => {
        if (!mountedRef.current) return;
        setSavedAt(at);
        setStatus('saved');
      },
      () => {
        if (!mountedRef.current) return;
        setStatus('error');
        pushToast({ kind: 'error', message: 'Couldn’t save — will retry.' });
        armAutosave(); // error is a dirty-variant: re-arm the 30s retry
      }
    );
  }

  runSaveRef.current = runSave;

  // Stable identity for the TopBar Save button; always runs the latest save.
  const save = useCallback(() => runSaveRef.current(), []);

  // Transition driver: keyed on doc identity + dirtiness. Content-only edits
  // (same id, isDirty already true) do NOT re-run this effect, which is exactly
  // what keeps the single autosave timer from being reset per keystroke.
  useEffect(() => {
    const prevId = prevIdRef.current;
    const prevDirty = prevDirtyRef.current;
    prevIdRef.current = doc?.id;
    prevDirtyRef.current = isDirty;

    // F10 — the document identity changed (or first mount). Drop the old doc's
    // pending autosave and re-derive from the new doc's dirtiness.
    if (prevId !== doc?.id) {
      clearAutosave();
      if (isDirty) {
        setStatus('dirty');
        armAutosave();
      } else {
        setStatus('pristine');
      }
      return;
    }

    // Same document: a clean→dirty edge enters `dirty` and arms ONE timer.
    if (!prevDirty && isDirty) {
      setStatus('dirty');
      armAutosave();
    }
    // dirty→clean without our own save (e.g. parent marking clean after a save)
    // is a no-op: it must not clobber the `saved` state/label.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc?.id, isDirty]);

  // While `saved`, tick a 60s heartbeat so "just now" ages into "1m ago"
  // without a new save. Cleaned up on leaving `saved` and on unmount.
  useEffect(() => {
    if (status !== 'saved') return undefined;
    const id = setInterval(() => {
      if (!mountedRef.current) return;
      setTick((t) => t + 1);
    }, SAVED_TICK_MS);
    return () => clearInterval(id);
  }, [status]);

  // Unmount: stop the world — clear the autosave timer, block late saves.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      clearAutosave();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const savedLabel = useMemo(() => {
    switch (status) {
      case 'dirty':
        return 'unsaved changes';
      case 'saving':
        return 'saving…';
      case 'error':
        return 'offline — will retry';
      case 'saved':
        return savedFreshnessLabel(savedAt, Date.now());
      case 'pristine':
      default:
        return '';
    }
    // `tick` is intentionally a dep: it re-derives the aging saved-label.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, savedAt, tick]);

  return { status, savedLabel, save };
}

export default useSaveMachine;
