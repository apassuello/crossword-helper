/**
 * useClueReconcile (clue-authoring spec 0.1.4, section 5.6 "Status display and reconciliation").
 *
 * Implements Decision 6 (clue-authoring spec 0.1.4, section 1): the CLI owns the authoritative
 * clue status; the browser's `clueStatuses` is for display only until a reply arrives.
 *
 * While `active` (panel open, no autofill run live) a request goes out when `active` becomes true
 * and 300 ms after the status signature last changed. Each request carries the signature it was
 * built from; a reply (or a failure) counts only if that signature is still the current one and
 * the hook is still active, so a reply for an older signature never shows. A clue missing from the
 * reply shows the browser's status. A failure, a moved-on signature, or an inactive hook shows the
 * browser's statuses for every clue, and a failure shows nothing else.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api/client';
import { toCliStrings } from '../api/gridCodec';
import { clueStatuses } from '../lib/clues';
import { statusSigOf } from '../lib/contentSig';

export const RECONCILE_DELAY_MS = 300;

export function useClueReconcile({ grid, gridSize, clues, active }) {
  const sig = grid ? statusSigOf(gridSize, grid, clues) : null;
  const [applied, setApplied] = useState(null); // { sig, statuses } of the last applied reply

  // Latest inputs, read by timers and replies (never through a stale closure).
  const latest = useRef({});
  latest.current = { grid, gridSize, clues, sig, active };
  const wasActive = useRef(false);

  useEffect(() => {
    const opening = active && !wasActive.current;
    wasActive.current = active;
    if (!active || !grid) {
      setApplied(null);
      return undefined;
    }
    let timer = null;
    const send = () => {
      timer = null;
      const cur = latest.current;
      if (!cur.grid) return;
      const requestSig = cur.sig;
      const stillCurrent = () => latest.current.active && latest.current.sig === requestSig;
      api
        .checkClues({ size: cur.gridSize, grid: toCliStrings(cur.grid), clues: cur.clues })
        .then(
          (res) => {
            if (stillCurrent()) setApplied({ sig: requestSig, statuses: (res && res.statuses) || {} });
          },
          () => {
            if (stillCurrent()) setApplied(null);
          }
        );
    };
    if (opening) send();
    else timer = setTimeout(send, RECONCILE_DELAY_MS);
    return () => {
      if (timer !== null) clearTimeout(timer);
    };
  }, [active, sig]); // eslint-disable-line react-hooks/exhaustive-deps

  return useMemo(() => {
    if (!grid) return {};
    const browser = clueStatuses(grid, clues);
    if (!active || !applied || applied.sig !== sig) return browser;
    const out = {};
    for (const key of Object.keys(browser)) {
      out[key] = Object.prototype.hasOwnProperty.call(applied.statuses, key)
        ? applied.statuses[key]
        : browser[key];
    }
    return out;
  }, [grid, clues, active, applied, sig]);
}
