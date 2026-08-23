/**
 * useHealth — top-bar health-dot data source (Task 6).
 *
 * Polls `GET /api/health` (via `api.health()`, the only fetch-capable module)
 * immediately on mount and then every 30s (fixed cadence, no backoff — spec
 * 07 §3.3 / 08 §5). Reports `{online, degraded}` for the red top-bar health
 * dot, one of the four error-surfacing surfaces (spec 08 §4): inline-below-
 * field, red toast, orange autofill-error card, and this dot.
 *
 * `api.health()` resolves with the parsed body even on HTTP 503 — degraded
 * is data, not an exception — and only throws (ApiError{code:'NETWORK'})
 * when the fetch itself fails. The online/degraded verdict is therefore
 * derived from `body.status`, not from response.ok/status.
 */

import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

const POLL_INTERVAL_MS = 30000;

function verdictFor(status) {
  if (status === 'healthy') return { online: true, degraded: false };
  if (status === 'degraded') return { online: true, degraded: true };
  // Any other/missing status (unparseable body, unexpected 500, ...) — a
  // healthy backend always returns one of the two statuses above, so
  // anything else means we can't trust it: red dot.
  return { online: false, degraded: false };
}

/**
 * @returns {{online: boolean, degraded: boolean}}
 */
export function useHealth() {
  const [state, setState] = useState({ online: false, degraded: false });
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    function poll() {
      api
        .health()
        .then((body) => {
          if (!mountedRef.current) return;
          setState(verdictFor(body.status));
        })
        .catch(() => {
          if (!mountedRef.current) return;
          setState({ online: false, degraded: false });
        });
    }

    poll();
    const id = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      mountedRef.current = false;
      clearInterval(id);
    };
  }, []);

  return state;
}

export default useHealth;
