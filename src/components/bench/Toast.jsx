// Toast — bespoke top-right toast surface (Task 6, U1b).
//
// Spec 08 defines exactly four error surfaces: inline-below-field, this red
// toast (top-right, auto-dismiss ~6s) for generic 4xx/5xx + network failures,
// the orange autofill-error card, and the top-bar health dot (useHealth).
// This is surface #2.
//
// Bespoke — replaces react-hot-toast (migration of App.jsx's existing
// `toast.*` calls happens in a later unit; do not remove the react-hot-toast
// dependency here).
//
// No React portal: a fixed-position stack rendered in place keeps this
// testable via RTL without a portal-aware container.

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

const ToastContext = createContext(null);

const AUTO_DISMISS_MS = 6000;
let nextId = 0;

/**
 * @param {{children: React.ReactNode}} props
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef(new Map());

  // Clear every pending auto-dismiss timer on unmount — otherwise a toast
  // pushed just before unmount leaks a live setTimeout past the provider's
  // lifetime (harmless in practice since setState on an unmounted component
  // is a silent no-op in React 18, but a leaked timer is still a leaked timer).
  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach(clearTimeout);
      timers.clear();
    };
  }, []);

  const dismiss = useCallback((id) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const pushToast = useCallback(
    ({ kind = 'error', message }) => {
      const id = nextId++;
      setToasts((prev) => [...prev, { id, kind, message }]);
      const timer = setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
      timersRef.current.set(id, timer);
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ pushToast }}>
      {children}
      <div className="xw-toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`xw-toast xw-toast-${t.kind}`}>
            <span className="xw-toast-msg">{t.message}</span>
            <button
              type="button"
              className="xw-toast-dismiss"
              aria-label="Dismiss"
              onClick={() => dismiss(t.id)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/**
 * @returns {{pushToast: (toast: {kind?: 'error'|'info', message: string}) => void}}
 */
export function useToasts() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToasts() must be called within a <ToastProvider>');
  }
  return ctx;
}
