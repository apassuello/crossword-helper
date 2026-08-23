/**
 * usePersistentState — a `useState` whose value is lazily initialized from and
 * persisted to `localStorage` under `key`.
 *
 * Motivation (mount-race fix). The naive persistence shape —
 *   `const [v, setV] = useState(DEFAULT)`  +  a `[v]` persist effect  +  a
 *   separate read-on-mount effect — has a silent bug: on first mount React
 * flushes the persist effect (with `v === DEFAULT`) BEFORE the read effect, so
 * the DEFAULT clobbers the stored value before it is ever read. The dark-mode
 * toggle hit exactly this (commit 207595e), and the symmetry toggle carried the
 * same latent twin. Lazy-initializing from storage makes the first render
 * already correct, so the single persist effect's first write is a no-op-
 * equivalent (it writes the same value back) — there is no window to clobber,
 * and no read-on-mount effect is needed.
 *
 * @template T
 * @param {string} key          localStorage key.
 * @param {T} defaultValue      value used when the key is absent or unparseable.
 * @param {{parse?: (raw: string) => T, serialize?: (v: T) => string}} [opts]
 *   Converters between the stored string and the in-memory value.
 *   Defaults: `JSON.parse` / `JSON.stringify`. `parse` is read once (in the
 *   lazy initializer); `serialize` may be an inline function (held in a ref).
 * @returns {[T, React.Dispatch<React.SetStateAction<T>>]} same shape as useState.
 */
import { useEffect, useRef, useState } from 'react';

export function usePersistentState(key, defaultValue, opts = {}) {
  const parse = opts.parse || JSON.parse;
  const serialize = opts.serialize || JSON.stringify;

  // `serialize` runs in the persist effect (which re-runs on value change), so
  // hold it in a ref to keep the effect's deps to [key, value] while still
  // honoring an inline serializer. `parse` only runs once below, so no ref.
  const serializeRef = useRef(serialize);
  serializeRef.current = serialize;

  const [value, setValue] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      // `== null` treats both null (real localStorage's absent-key return) and
      // undefined as "not stored".
      return raw == null ? defaultValue : parse(raw);
    } catch {
      // Absent/unparseable/quota-blocked read — fall back to the default.
      return defaultValue;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, serializeRef.current(value));
    } catch {
      // Persistence is best-effort; a quota/serialize failure must not crash render.
    }
  }, [key, value]);

  return [value, setValue];
}

export default usePersistentState;
