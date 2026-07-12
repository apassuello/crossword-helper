// CrosswordGrid — the Constructor's Bench crossword grid (SVG).
// Ported from the design bundle prototype (grid.jsx). Renders cells, numbering,
// focus/highlight states, theme locks, error underlines, and constraint heatmap shading.
// All visual tokens read from CSS variables so light/dark/accent tweaks flow through.
//
// FULLY CONTROLLED: no internal grid state. The parent owns grid + focus + direction.
//
// Keyboard model (Task 5 fix): the prototype re-attached its keydown listener on every
// state change. Here the listener is attached exactly ONCE (empty-deps effect) and reads
// live state/handlers through a ref that is refreshed every render. The key-dispatch
// switch is lifted into the PURE, exported `dispatchGridKey` so it is unit-testable
// without mounting.

import React, { useRef, useMemo, useEffect } from 'react';
import { useGridGeometry } from '../../hooks/useGridGeometry';

// Numeric SVG geometry — DISTINCT from the CSS var(--cell-px). Kept in sync with
// tokens.css (--cell-px: 38px) so cell-relative font sizing lines up.
const CELL_PX = 38;
const PAD = 12;

/**
 * Compute the next/previous word-start when Tab / Shift+Tab is pressed.
 * Cycle is the concatenation [...across, ...down]: after the last across slot it
 * switches to the first down slot, and after the last down slot it wraps to the first
 * across slot (direction switch is the intended new behavior). Falls back to the first
 * (forward) / last (backward) slot when the focus cell is not itself a word cell.
 *
 * @returns {{row:number, col:number, dir:'across'|'down'}|null}
 */
function nextWordStart(slots, focus, dir, forward) {
  const combined = [
    ...slots.across.map((slot) => ({ slot, dir: 'across' })),
    ...slots.down.map((slot) => ({ slot, dir: 'down' })),
  ];
  if (combined.length === 0) return null;

  let curIdx = combined.findIndex(
    (entry) =>
      entry.dir === dir &&
      entry.slot.cells.some(([r, c]) => r === focus.row && c === focus.col)
  );
  if (curIdx === -1) curIdx = forward ? -1 : combined.length;

  const nextIdx = forward
    ? (curIdx + 1) % combined.length
    : (curIdx - 1 + combined.length) % combined.length;

  const entry = combined[nextIdx];
  const [sr, sc] = entry.slot.cells[0];
  return { row: sr, col: sc, dir: entry.dir };
}

/**
 * PURE key dispatch. Given a minimal key descriptor and grid state, return the intended
 * actions — no side effects, no React. Actions are applied by `applyGridKeyActions`.
 *
 * @param {{key:string, shiftKey?:boolean, ctrlKey?:boolean, metaKey?:boolean}} key
 * @param {{grid, size, focus, selectedDir, slots}} state
 * @returns {{preventDefault:boolean, actions:Array<object>}}
 */
export function dispatchGridKey(key, state) {
  const { grid, size, focus, selectedDir, slots } = state;
  const actions = [];
  const result = { preventDefault: false, actions };

  if (!focus) return result;
  const { row, col } = focus;
  const cell = grid[row] && grid[row][col];
  if (!cell) return result;

  const k = key.key;
  const ctrl = !!key.ctrlKey;
  const meta = !!key.metaKey;
  const shift = !!key.shiftKey;

  // Ctrl/Cmd+L — toggle theme lock
  if ((ctrl || meta) && k.toLowerCase() === 'l') {
    result.preventDefault = true;
    actions.push({ type: 'toggleLock', row, col });
    return result;
  }

  // Arrow keys — move focus and align direction with motion
  if (k.startsWith('Arrow')) {
    result.preventDefault = true;
    let nr = row;
    let nc = col;
    let desired = selectedDir;
    if (k === 'ArrowUp') {
      if (row > 0) nr = row - 1;
      desired = 'down';
    } else if (k === 'ArrowDown') {
      if (row < size - 1) nr = row + 1;
      desired = 'down';
    } else if (k === 'ArrowLeft') {
      if (col > 0) nc = col - 1;
      desired = 'across';
    } else if (k === 'ArrowRight') {
      if (col < size - 1) nc = col + 1;
      desired = 'across';
    }
    if (nr !== row || nc !== col) actions.push({ type: 'moveFocus', row: nr, col: nc });
    if (desired !== selectedDir) actions.push({ type: 'rotateDir' });
    return result;
  }

  // Space / period — toggle black (never on locked cells)
  if (k === ' ' || k === '.') {
    result.preventDefault = true;
    if (!cell.isThemeLocked) actions.push({ type: 'toggleBlack', row, col });
    return result;
  }

  // Enter — rotate direction (prototype behavior)
  if (k === 'Enter') {
    result.preventDefault = true;
    actions.push({ type: 'rotateDir' });
    return result;
  }

  // Tab / Shift+Tab — next / previous word start (regression guard for GridEditor's
  // moveToNextWord; extended to switch direction across↔down at the list boundary)
  if (k === 'Tab') {
    result.preventDefault = true;
    const next = nextWordStart(slots, focus, selectedDir, !shift);
    if (next) {
      actions.push({ type: 'moveFocus', row: next.row, col: next.col });
      if (next.dir !== selectedDir) actions.push({ type: 'rotateDir' });
    }
    return result;
  }

  // Backspace / Delete — clear letter, or step back on empty Backspace
  if (k === 'Backspace' || k === 'Delete') {
    result.preventDefault = true;
    if (cell.isThemeLocked) return result;
    if (cell.letter) {
      actions.push({ type: 'setLetter', row, col, ch: '' });
    } else if (k === 'Backspace') {
      if (selectedDir === 'across' && col > 0) actions.push({ type: 'moveFocus', row, col: col - 1 });
      else if (selectedDir === 'down' && row > 0) actions.push({ type: 'moveFocus', row: row - 1, col });
    }
    return result;
  }

  // Letters — set + advance in selectedDir (blocked on black/locked cells)
  if (/^[A-Za-z]$/.test(k) && !meta && !ctrl) {
    result.preventDefault = true;
    if (cell.isThemeLocked || cell.isBlack) return result;
    actions.push({ type: 'setLetter', row, col, ch: k.toUpperCase() });
    if (selectedDir === 'across' && col < size - 1) actions.push({ type: 'moveFocus', row, col: col + 1 });
    else if (selectedDir === 'down' && row < size - 1) actions.push({ type: 'moveFocus', row: row + 1, col });
    return result;
  }

  return result;
}

/** Apply the pure dispatch actions to the controlled callbacks. */
function applyGridKeyActions(actions, h) {
  for (const a of actions) {
    switch (a.type) {
      case 'moveFocus':
        h.onMoveFocus(a.row, a.col);
        break;
      case 'setLetter':
        h.onSetLetter(a.row, a.col, a.ch);
        break;
      case 'toggleBlack':
        h.onToggleBlack(a.row, a.col);
        break;
      case 'toggleLock':
        h.onToggleLock(a.row, a.col);
        break;
      case 'rotateDir':
        h.onRotateDir();
        break;
      default:
        break;
    }
  }
}

function CrosswordGrid({
  grid,
  focus,
  selectedDir,
  heatmap = null,
  onFocus,
  onSetLetter,
  onToggleBlack,
  onToggleLock,
  onRotateDir,
  onMoveFocus,
}) {
  const size = grid.length;
  const W = size * CELL_PX + 2 * PAD;
  const containerRef = useRef(null);

  const geometry = useGridGeometry(grid);
  const slots = useMemo(() => geometry.allSlots(), [geometry]);

  // Highlighted word cells based on focus + direction (verbatim from prototype).
  const highlighted = useMemo(() => {
    const set = new Set();
    if (!focus) return set;
    const { row, col } = focus;
    if (!grid[row] || !grid[row][col] || grid[row][col].isBlack) return set;
    if (selectedDir === 'across') {
      for (let c = col; c >= 0 && !grid[row][c].isBlack; c--) set.add(`${row}-${c}`);
      for (let c = col + 1; c < size && !grid[row][c].isBlack; c++) set.add(`${row}-${c}`);
    } else {
      for (let r = row; r >= 0 && !grid[r][col].isBlack; r--) set.add(`${r}-${col}`);
      for (let r = row + 1; r < size && !grid[r][col].isBlack; r++) set.add(`${r}-${col}`);
    }
    return set;
  }, [focus, selectedDir, grid, size]);

  // Live state + handlers, refreshed every render. The keydown listener reads through
  // this ref so it never needs to be re-attached (the prototype's rebind defect).
  const stateRef = useRef();
  stateRef.current = {
    grid,
    size,
    focus,
    selectedDir,
    slots,
    handlers: { onSetLetter, onToggleBlack, onToggleLock, onRotateDir, onMoveFocus },
  };

  // Attach the keydown listener EXACTLY ONCE.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    const handler = (e) => {
      const st = stateRef.current;
      if (!st.focus) return;
      const { preventDefault, actions } = dispatchGridKey(
        { key: e.key, shiftKey: e.shiftKey, ctrlKey: e.ctrlKey, metaKey: e.metaKey },
        st
      );
      if (preventDefault) e.preventDefault();
      applyGridKeyActions(actions, st.handlers);
    };
    el.addEventListener('keydown', handler);
    return () => el.removeEventListener('keydown', handler);
  }, []);

  const handleCellClick = (r, c, e) => {
    if (e.shiftKey || e.altKey) {
      onToggleBlack(r, c);
      return;
    }
    // Clicking the already-focused cell rotates direction.
    if (focus && focus.row === r && focus.col === c) onRotateDir();
    onFocus(r, c);
    containerRef.current?.focus();
  };

  const handleRightClick = (r, c, e) => {
    e.preventDefault();
    onToggleLock(r, c);
  };

  const constraintShade = (r, c) => {
    if (!heatmap) return 0;
    const rowArr = heatmap[r];
    if (!rowArr) return 0;
    const v = rowArr[c];
    if (v == null) return 0;
    return v; // 0..1 tension
  };

  return (
    <div className="xw-grid-wrap">
      <div ref={containerRef} className="xw-grid-focus" tabIndex={0}>
        <svg
          width={W}
          height={W}
          viewBox={`0 0 ${W} ${W}`}
          className="xw-grid-svg"
          role="grid"
          aria-label={`${size} by ${size} crossword grid`}
        >
          <defs>
            <pattern id="paper" width="80" height="80" patternUnits="userSpaceOnUse">
              <rect width="80" height="80" fill="var(--paper)" />
              <circle cx="10" cy="20" r=".4" fill="var(--ink-08)" />
              <circle cx="55" cy="12" r=".3" fill="var(--ink-08)" />
              <circle cx="30" cy="55" r=".35" fill="var(--ink-08)" />
              <circle cx="70" cy="65" r=".3" fill="var(--ink-08)" />
              <circle cx="45" cy="40" r=".25" fill="var(--ink-08)" />
            </pattern>
            <filter id="blacksq-shadow">
              <feGaussianBlur in="SourceAlpha" stdDeviation="1" />
              <feOffset dx="0" dy="0.5" />
              <feComponentTransfer>
                <feFuncA type="linear" slope="0.35" />
              </feComponentTransfer>
              <feMerge>
                <feMergeNode />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* paper ground */}
          <rect x={0} y={0} width={W} height={W} fill="url(#paper)" />

          {/* outer border */}
          <rect
            x={PAD - 0.5}
            y={PAD - 0.5}
            width={size * CELL_PX + 1}
            height={size * CELL_PX + 1}
            fill="none"
            stroke="var(--ink)"
            strokeWidth="2"
          />

          {/* Inner grid lines */}
          {Array.from({ length: size + 1 }).map((_, i) => (
            <React.Fragment key={`gl-${i}`}>
              <line
                x1={PAD}
                y1={PAD + i * CELL_PX}
                x2={PAD + size * CELL_PX}
                y2={PAD + i * CELL_PX}
                stroke="var(--ink)"
                strokeWidth={i === 0 || i === size ? 1.5 : 0.5}
              />
              <line
                x1={PAD + i * CELL_PX}
                y1={PAD}
                x2={PAD + i * CELL_PX}
                y2={PAD + size * CELL_PX}
                stroke="var(--ink)"
                strokeWidth={i === 0 || i === size ? 1.5 : 0.5}
              />
            </React.Fragment>
          ))}

          {/* Cells */}
          {grid.map((row, r) =>
            row.map((cell, c) => {
              const x = PAD + c * CELL_PX;
              const y = PAD + r * CELL_PX;
              const key = `${r}-${c}`;
              const isFocus = focus && focus.row === r && focus.col === c;
              const isHi = highlighted.has(key);
              const tension = heatmap && !cell.isBlack ? constraintShade(r, c) : 0;

              let fill = 'transparent';
              if (cell.isBlack) fill = 'var(--ink)';
              else if (isFocus) fill = 'var(--accent-15)';
              else if (isHi) fill = 'var(--accent-06)';
              else if (tension > 0.6) fill = 'rgba(220, 80, 60, 0.14)';
              else if (tension > 0.3) fill = 'rgba(230, 160, 60, 0.10)';

              return (
                <g key={key}>
                  {fill !== 'transparent' && (
                    <rect
                      x={x + 0.5}
                      y={y + 0.5}
                      width={CELL_PX - 1}
                      height={CELL_PX - 1}
                      fill={fill}
                      filter={cell.isBlack ? 'url(#blacksq-shadow)' : undefined}
                    />
                  )}
                  <rect
                    x={x}
                    y={y}
                    width={CELL_PX}
                    height={CELL_PX}
                    fill="transparent"
                    style={{ cursor: cell.isBlack ? 'crosshair' : 'text' }}
                    onClick={(e) => handleCellClick(r, c, e)}
                    onContextMenu={(e) => handleRightClick(r, c, e)}
                  />
                  {/* Theme lock: tiny folded corner */}
                  {cell.isThemeLocked && !cell.isBlack && (
                    <path
                      d={`M ${x + CELL_PX - 10} ${y + 1} L ${x + CELL_PX - 1} ${y + 1} L ${x + CELL_PX - 1} ${y + 10} Z`}
                      fill="var(--accent)"
                      pointerEvents="none"
                    />
                  )}
                  {/* Number */}
                  {cell.number && (
                    <text x={x + 3} y={y + 10} className="xw-cell-number" pointerEvents="none">
                      {cell.number}
                    </text>
                  )}
                  {/* Letter */}
                  {cell.letter && !cell.isBlack && (
                    <text
                      x={x + CELL_PX / 2}
                      y={y + CELL_PX / 2 + CELL_PX * 0.2}
                      className="xw-cell-letter"
                      textAnchor="middle"
                      pointerEvents="none"
                      fill={cell.isError ? 'var(--danger)' : 'var(--ink)'}
                    >
                      {cell.letter}
                    </text>
                  )}
                  {/* Error underline */}
                  {cell.isError && !cell.isBlack && (
                    <line
                      x1={x + CELL_PX * 0.2}
                      y1={y + CELL_PX - 3}
                      x2={x + CELL_PX * 0.8}
                      y2={y + CELL_PX - 3}
                      stroke="var(--danger)"
                      strokeWidth="1.2"
                      pointerEvents="none"
                    />
                  )}
                  {/* Focus ring */}
                  {isFocus && !cell.isBlack && (
                    <rect
                      x={x + 1}
                      y={y + 1}
                      width={CELL_PX - 2}
                      height={CELL_PX - 2}
                      fill="none"
                      stroke="var(--accent)"
                      strokeWidth="1.5"
                      pointerEvents="none"
                    />
                  )}
                </g>
              );
            })
          )}
        </svg>
      </div>
    </div>
  );
}

export default CrosswordGrid;
