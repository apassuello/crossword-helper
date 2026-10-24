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
 * It reaches persistence ONLY through `storage.save(doc, opts)` (never
 * localStorage directly) so M2 can swap the transport to `POST /api/grid/save`
 * without touching this file. `opts` is `{ name?, expectedSavedAt?,
 * replaceEntryId? }`: autosave sends only `expectedSavedAt` (the machine's
 * `knownSavedAt`), `saveNamed` adds `name`/`replaceEntryId`.
 * novice-readiness spec 0.2.7 §3.4 (G3, G4, S4, PD-6-G6): a fork result calls
 * `onForked`, a failed explicit save shows the quota message and re-arms autosave.
 * novice-readiness spec 0.2.7 §3.4 (S2): `onSaved(written)` receives the exact doc
 * object handed to `storage.save`, in the same success handler that sets `saved`, so
 * the parent can record the signature of what was WRITTEN (not of whatever the live
 * grid is by the time `saved` renders) and both updates land in one render. When an
 * `onSaved` is supplied, the parent contract is enforced: if `isDirty` is still true
 * on the render where status is `saved`, the document moved on after the write and
 * the machine goes back to `dirty` with a fresh autosave timer. Both callbacks are
 * guarded: a throw in either never rejects the save or strands status at `saving`.
 * It is driven by two controlled props:
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

const QUOTA_MESSAGE =
  'Could not save: browser storage is full. Delete a saved grid or export this one.';

/**
 * @param {{doc: {id: string}, isDirty: boolean, onForked?: (info: {id: string, name: string}) => void,
 *   onSaved?: (written: object) => void}} params
 * @returns {{status: 'pristine'|'dirty'|'saving'|'saved'|'error', savedLabel: string,
 *   save: () => Promise<void>,
 *   saveNamed: (name: string, opts?: {replaceEntryId?: string}) => Promise<boolean>,
 *   adoptSavedAt: (savedAt: string|null) => void, forget: () => void}}
 */
export function useSaveMachine({ doc, isDirty, onForked, onSaved }) {
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
  const onForkedRef = useRef(onForked); // latest fork callback, read at resolve time
  const onSavedRef = useRef(onSaved); // latest saved callback, read at resolve time
  // The savedAt this tab loaded or last wrote (S4). Deliberately NOT reset on a
  // doc.id change: Open saved / restore call setDocId and adoptSavedAt in one
  // handler, and an effect-time reset would overwrite the adopted value. A stale
  // value for a brand-new id is harmless (storage.save finds no entry to compare).
  const knownSavedAtRef = useRef(null);
  // Set by forget(): the stored entry is gone and the pending timer with it. A document that
  // was already dirty has no clean->dirty edge to arm on, so the next change to `doc` does
  // (novice-readiness spec 0.2.9 §3.4 (Q1)).
  const forgottenRef = useRef(false);
  const isDirtyRef = useRef(isDirty); // latest dirtiness, read by the pagehide handler

  docRef.current = doc;
  isDirtyRef.current = isDirty;
  onForkedRef.current = onForked;
  onSavedRef.current = onSaved;

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
      runSaveRef.current({}, false);
    }, AUTOSAVE_MS);
  }

  /**
   * The one write path. `explicit` (saveNamed) differs only in the opts sent,
   * the failure toast, and resolving a boolean; the write, the knownSavedAt
   * update, the fork callback and the status transitions are shared.
   */
  function runSave(extra, explicit, silent = false) {
    clearAutosave(); // this attempt consumes any pending timer
    setStatus('saving');
    const opts = { expectedSavedAt: knownSavedAtRef.current, ...extra };
    const written = docRef.current;
    // The pagehide path (`silent`) writes through the synchronous entry point, outside the
    // Web Lock: the Promise executor runs it before runSave returns, and a throw becomes
    // the rejection (novice-readiness spec 0.2.9 §3.4 (Q3)).
    const write = silent
      ? new Promise((resolve) => resolve(storage.saveSync(written, opts)))
      : storage.save(written, opts);
    return write.then(
      (res) => {
        // The entry is written. Only the in-memory bookkeeping for the CURRENT document is
        // guarded: a save of a document that New grid, Open saved or an import has since
        // replaced must not set the new document's clean signature, its known savedAt, its
        // docId (fork) or its status label (novice-readiness spec 0.2.9 §3.4 (S4), §2.3 (M1)).
        // Reachable since Task 6.19: a Web Lock grant is asynchronous.
        if (written.id !== docRef.current?.id) return true;
        knownSavedAtRef.current = res.savedAt;
        // A throwing callback must not reject the save (the write already happened)
        // nor skip the `saved` transition below.
        if (res.forked) {
          try {
            onForkedRef.current?.({ id: res.id, name: res.name });
          } catch {
            /* guarded: see above */
          }
        }
        try {
          onSavedRef.current?.(written);
        } catch {
          /* guarded: see above */
        }
        if (!mountedRef.current) return true;
        setSavedAt(res.savedAt);
        setStatus('saved');
        return true;
      },
      () => {
        if (!mountedRef.current) return false;
        // A failed save of a replaced document says nothing about the current one: no
        // `offline` label and no retry timer for it (the toast below still reports the loss).
        const current = written.id === docRef.current?.id;
        if (current) setStatus('error');
        // novice-readiness spec 0.2.8 §3.4 (Q3): a pagehide save fails without a toast.
        if (!silent) {
          pushToast({
            kind: 'error',
            message: explicit ? QUOTA_MESSAGE : 'Couldn’t save — will retry.',
          });
        }
        if (current) armAutosave(); // error is a dirty-variant: re-arm the 30s retry
        return false;
      }
    );
  }

  runSaveRef.current = runSave;

  // Stable identity for the TopBar Save button; always runs the latest save.
  // (Autosave path: resolves void, as before.)
  const save = useCallback(() => runSaveRef.current({}, false).then(() => undefined), []);

  // Explicit named save (§3.4 G3/G4): never rejects; true saved, false failed.
  const saveNamed = useCallback((name, opts = {}) => {
    const extra = { name };
    if (opts.replaceEntryId !== undefined) extra.replaceEntryId = opts.replaceEntryId;
    return runSaveRef.current(extra, true);
  }, []);

  const adoptSavedAt = useCallback((at) => {
    knownSavedAtRef.current = at;
  }, []);

  /**
   * novice-readiness spec 0.2.8 §3.4 (Q1): the open document's stored entry was deleted.
   * Clear any pending autosave and read `unsaved changes`, WITHOUT arming and without
   * touching `isDirty`/`savedSig`/the known `savedAt`: the next real edit arms as usual (a clean
   * document flips `isDirty`; a dirty one arms on its next `doc` change, spec 0.2.9 §3.4 (Q1)),
   * and its save recreates the entry under the same id (storage.save).
   */
  const forget = useCallback(() => {
    clearAutosave();
    forgottenRef.current = true;
    setStatus('dirty');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // novice-readiness spec 0.2.8 §3.4 (Q3): leaving the page saves a dirty document at once
  // through the same path as the autosave timer (so a live run writes the Start snapshot,
  // S2). A clean document writes nothing; a failure shows no toast.
  useEffect(() => {
    const onPageHide = () => {
      if (!isDirtyRef.current) return;
      clearAutosave();
      runSaveRef.current({}, false, true);
    };
    window.addEventListener('pagehide', onPageHide);
    return () => window.removeEventListener('pagehide', onPageHide);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Transition driver: keyed on doc identity + dirtiness. Content-only edits
  // (same id, isDirty already true) do NOT re-run this effect, which is exactly
  // what keeps the single autosave timer from being reset per keystroke.
  useEffect(() => {
    const prevId = prevIdRef.current;
    const prevDirty = prevDirtyRef.current;
    prevIdRef.current = doc?.id;
    prevDirtyRef.current = isDirty;
    if (prevId !== doc?.id) forgottenRef.current = false;

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
      forgottenRef.current = false;
      setStatus('dirty');
      armAutosave();
    }
    // dirty→clean without our own save (e.g. parent marking clean after a save)
    // is a no-op: it must not clobber the `saved` state/label.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc?.id, isDirty]);

  // After forget(), a change to `doc` while already dirty arms the autosave (no edge to do it).
  useEffect(() => {
    if (forgottenRef.current && isDirty && timerRef.current === null) {
      forgottenRef.current = false;
      setStatus('dirty');
      armAutosave();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc]);

  // S2: with an onSaved supplied the parent marks the written doc clean in the same
  // batch as `saved`; `isDirty` still true here means an edit landed after the write.
  const hasOnSaved = onSaved !== undefined;
  useEffect(() => {
    if (hasOnSaved && status === 'saved' && isDirty) {
      setStatus('dirty');
      armAutosave();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, isDirty, hasOnSaved]);

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

  return { status, savedLabel, save, saveNamed, adoptSavedAt, forget };
}

export default useSaveMachine;
