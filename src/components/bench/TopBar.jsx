// TopBar — Constructor's Bench top bar (brand mark, health status, verify/save
// actions, theme toggle).
// Ported from the design bundle prototype (panels.jsx:46-85).
//
// Presentational / fully controlled — parent (App, U3) owns all state: health
// polling (useHealth), save-state derivation, and dark-mode persistence. No
// useState/useEffect, no timers, no document/localStorage access here — this
// component only calls onToggleTheme; U3 owns the dark-mode effect + persistence.
//
// Prop reconciliation vs. the bundle's { onVerify, onSave, onToggleDark, dark,
// savedAt, status{kind,label} } (see plan Task 6 brief):
//   - status: the useHealth verdict { online, degraded } — TopBar derives the
//     health-dot kind ('err'/'warn'/'ok') and label ('offline'/'degraded'/'online')
//     from it, replacing the bundle's pre-derived {kind,label} pair.
//   - The Verify button is disabled when !status.online (spec 07 §3.3 — offline
//     disables Verify), with a title explaining why. Save is never disabled offline.
//   - savedLabel: a parent-supplied display string, rendered verbatim — replaces
//     the bundle's savedAt timestamp prop (U4's save machine derives the string).
//   - onToggleTheme / dark: renamed from the bundle's onToggleDark.

import React from 'react';

export function TopBar({ status, savedLabel, onVerify, onSave, onClean, onToggleTheme, dark }) {
  const offline = !status.online;
  const kind = offline ? 'err' : status.degraded ? 'warn' : 'ok';
  const label = offline ? 'offline' : status.degraded ? 'degraded' : 'online';

  return (
    <header className="xw-topbar">
      <div className="xw-brand">
        <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
          <rect x="1" y="1" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <rect x="1" y="1" width="6" height="6" fill="currentColor" />
          <rect x="15" y="15" width="6" height="6" fill="currentColor" />
          <line x1="1" y1="8" x2="21" y2="8" stroke="currentColor" strokeWidth=".6" />
          <line x1="1" y1="15" x2="21" y2="15" stroke="currentColor" strokeWidth=".6" />
          <line x1="8" y1="1" x2="8" y2="21" stroke="currentColor" strokeWidth=".6" />
          <line x1="15" y1="1" x2="15" y2="21" stroke="currentColor" strokeWidth=".6" />
        </svg>
        <div className="xw-brand-text">
          <span className="xw-brand-name">Crossword Helper</span>
          <span className="xw-brand-sub">— the constructor's bench</span>
          <span className="xw-pill">v2.0 · advanced</span>
        </div>
      </div>

      <div className="xw-topbar-right">
        <span className="xw-status" data-kind={kind}>
          <span className="xw-status-dot" />
          {label}
        </span>
        <div className="xw-topbar-divider" />
        <button
          className="xw-icon-btn"
          onClick={onVerify}
          disabled={offline}
          title={offline ? 'Backend offline' : 'Verify words against wordlists'}
        >
          <svg width="14" height="14" viewBox="0 0 16 16">
            <path d="M3 8 L7 12 L13 4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>Verify words</span>
        </button>
        {/* Verify+Clean are transitional here until Task 10's 06§2 verify/clean machine. */}
        <button
          className="xw-icon-btn"
          onClick={onClean}
          disabled={offline}
          title={offline ? 'Backend offline' : 'Clean grid of invalid entries'}
        >
          <svg width="14" height="14" viewBox="0 0 16 16">
            <path d="M3 3 L13 13 M13 3 L3 13" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
          <span>Clean grid</span>
        </button>
        <button className="xw-primary-btn xw-primary-btn-sm" onClick={onSave}>
          <svg width="12" height="12" viewBox="0 0 16 16">
            <path d="M3 3 v10 h10 V6 l-3-3 z M6 3 v3 h5 M6 10 h4" fill="none" stroke="currentColor" strokeWidth="1.4" />
          </svg>
          <span>Save grid</span>
        </button>
        {savedLabel && <span className="xw-saved-meta">{savedLabel}</span>}
        <div className="xw-topbar-divider" />
        <button className="xw-mode-btn" onClick={onToggleTheme} title="Toggle theme">
          {dark ? '◐' : '◑'}
        </button>
      </div>
    </header>
  );
}
