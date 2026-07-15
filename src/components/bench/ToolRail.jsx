// ToolRail — Constructor's Bench left navigation rail (tool switcher, VIEW
// toggles, GRID stats block).
// Ported from the design bundle prototype (panels.jsx:88-140).
//
// Presentational / fully controlled — parent (App, U3) owns tool selection,
// view-toggle state, and stats derivation. No useState/useEffect.
//
// Prop reconciliation vs. the bundle's { tool, onTool, stats, symmetry,
// onToggleSym, heatmap, onToggleHeatmap } (see plan Task 6 brief):
//   - onSelectTool(id): renamed from the bundle's onTool.
//   - viewToggles: { symmetry, heatmap } replaces the bundle's separate
//     symmetry/heatmap props; onToggleView(which) with which in
//     'symmetry' | 'heatmap' replaces the bundle's two separate
//     onToggleSym/onToggleHeatmap callbacks with a single handler.
//   - Dropped the bundle's dead per-tool `hint` field: keyboard letters
//     (G/S/F/...) were defined but never rendered or wired to a shortcut.
//   - stats: { total, black, blackPct, fillPct, words } — rendered verbatim.

import React from 'react';

const TOOLS = [
  { id: 'edit', label: 'Grid' },
  { id: 'search', label: 'Search' },
  { id: 'autofill', label: 'Autofill' },
  { id: 'clues', label: 'Clues' },
  { id: 'theme', label: 'Theme' },
  { id: 'lists', label: 'Lists' },
  { id: 'import', label: 'Import' },
  { id: 'export', label: 'Export' },
];

const ICONS = {
  edit: (
    <g>
      <rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <line x1="2" y1="6" x2="14" y2="6" stroke="currentColor" strokeWidth=".7" />
      <line x1="6" y1="2" x2="6" y2="14" stroke="currentColor" strokeWidth=".7" />
    </g>
  ),
  search: (
    <g>
      <circle cx="7" cy="7" r="4.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <line x1="10" y1="10" x2="13.5" y2="13.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </g>
  ),
  autofill: (
    <g>
      <path d="M3 8 L7 12 L13 3" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="3" cy="3" r="1" fill="currentColor" />
    </g>
  ),
  clues: (
    <g>
      <line x1="3" y1="4" x2="13" y2="4" stroke="currentColor" strokeWidth="1.4" />
      <line x1="3" y1="8" x2="13" y2="8" stroke="currentColor" strokeWidth="1.4" />
      <line x1="3" y1="12" x2="10" y2="12" stroke="currentColor" strokeWidth="1.4" />
    </g>
  ),
  theme: (
    <g>
      <circle cx="8" cy="8" r="5" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="8" cy="8" r="1.5" fill="currentColor" />
    </g>
  ),
  lists: (
    <g>
      <rect x="2" y="3" width="12" height="2.2" fill="currentColor" />
      <rect x="2" y="6.9" width="12" height="2.2" fill="currentColor" opacity=".6" />
      <rect x="2" y="10.8" width="12" height="2.2" fill="currentColor" opacity=".3" />
    </g>
  ),
  import: (
    <g>
      <path d="M8 2 v8 M5 7 L8 10 L11 7" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="3" y1="13" x2="13" y2="13" stroke="currentColor" strokeWidth="1.4" />
    </g>
  ),
  export: (
    <g>
      <path d="M8 10 v-8 M5 5 L8 2 L11 5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="3" y1="13" x2="13" y2="13" stroke="currentColor" strokeWidth="1.4" />
    </g>
  ),
};

export function ToolRail({ tool, onSelectTool, viewToggles, onToggleView, stats, violations = [], unverified = false }) {
  return (
    <nav className="xw-toolrail">
      <div className="xw-toolrail-top">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            className={`xw-tool-btn ${tool === t.id ? 'on' : ''}`}
            onClick={() => onSelectTool(t.id)}
            title={t.label}
          >
            <svg width="16" height="16" viewBox="0 0 16 16">{ICONS[t.id]}</svg>
            <span>{t.label}</span>
          </button>
        ))}
      </div>
      <div className="xw-toolrail-bottom">
        <div className="xw-rail-section-label">VIEW</div>
        <button
          className={`xw-tool-btn xw-tool-btn-small ${viewToggles.symmetry ? 'on' : ''}`}
          onClick={() => onToggleView('symmetry')}
        >
          <svg width="14" height="14" viewBox="0 0 16 16">
            <circle cx="8" cy="8" r="1.2" fill="currentColor" />
            <rect x="1" y="1" width="4" height="4" fill="currentColor" />
            <rect x="11" y="11" width="4" height="4" fill="currentColor" />
          </svg>
          <span>Symmetry</span>
        </button>
        <button
          className={`xw-tool-btn xw-tool-btn-small ${viewToggles.heatmap ? 'on' : ''}`}
          onClick={() => onToggleView('heatmap')}
        >
          <svg width="14" height="14" viewBox="0 0 16 16">
            <circle cx="8" cy="8" r="6" fill="currentColor" opacity=".3" />
            <circle cx="8" cy="8" r="3.5" fill="currentColor" opacity=".6" />
            <circle cx="8" cy="8" r="1.2" fill="currentColor" />
          </svg>
          <span>Heatmap</span>
        </button>

        <div className="xw-rail-section-label" style={{ marginTop: 14 }}>GRID</div>
        <div className="xw-rail-stat"><span>Total</span><span className="xw-rail-stat-val">{stats.total}</span></div>
        <div className="xw-rail-stat"><span>Black</span><span className="xw-rail-stat-val">{stats.black}<em>·</em>{stats.blackPct}%</span></div>
        <div className="xw-rail-stat"><span>Filled</span><span className="xw-rail-stat-val">{stats.fillPct}%</span></div>
        <div className="xw-rail-stat"><span>Words</span><span className="xw-rail-stat-val">{stats.words}</span></div>

        {/* VIOLATIONS — advisory, live (plan Global Constraint 7): server-sourced
            warnings/suggestions from useNumbering's /api/grid/validate pass. Shown
            only when non-empty; `unverified` (optimistic paint awaiting reconcile)
            tags the label so a stale/in-flight state reads as provisional. */}
        {violations.length > 0 && (
          <>
            <div className="xw-rail-section-label" style={{ marginTop: 14 }}>
              VIOLATIONS{unverified ? ' (unverified)' : ''}
            </div>
            {violations.map((v, i) => (
              <div key={i} className="xw-rail-violation">{v}</div>
            ))}
          </>
        )}
      </div>
    </nav>
  );
}
