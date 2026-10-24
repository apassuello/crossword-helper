/**
 * Tests for CrosswordGrid (Task 5) — the ported Constructor's Bench SVG grid.
 *
 * Fully controlled: no internal grid state. Interaction tests here REPLACE the old
 * src/__tests__/components/GridEditor.test.jsx interaction tests (GridEditor deleted).
 *
 * The old GridEditor.test.jsx had no heatmap-fetch tests (the constraint fetch lived
 * inside GridEditor.jsx and is dropped — heatmap is now a controlled prop), so there is
 * nothing to describe.skip for Task 22.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import CrosswordGrid, { dispatchGridKey } from '../CrosswordGrid';
import { allSlots } from '../../../hooks/useGridGeometry';
import { createEmptyGrid } from '../../../__tests__/fixtures/gridFixtures';

// Clickable interaction rects are the only rects with fill="transparent"
const hitRects = (container) => container.querySelectorAll('rect[fill="transparent"]');

function baseProps(overrides = {}) {
  return {
    grid: createEmptyGrid(5),
    focus: { row: 0, col: 0 },
    selectedDir: 'across',
    heatmap: null,
    onFocus: vi.fn(),
    onSetLetter: vi.fn(),
    onToggleBlack: vi.fn(),
    onToggleLock: vi.fn(),
    onRotateDir: vi.fn(),
    onMoveFocus: vi.fn(),
    ...overrides,
  };
}

describe('dispatchGridKey (pure key dispatch)', () => {
  const grid = createEmptyGrid(5);
  const state = (over = {}) => ({
    grid,
    size: 5,
    focus: { row: 0, col: 0 },
    selectedDir: 'across',
    slots: allSlots(grid),
    ...over,
  });

  it('typing a letter sets it and advances focus in selectedDir (across)', () => {
    const { actions } = dispatchGridKey({ key: 'c' }, state());
    expect(actions).toContainEqual({ type: 'setLetter', row: 0, col: 0, ch: 'C' });
    expect(actions).toContainEqual({ type: 'moveFocus', row: 0, col: 1 });
  });

  it('typing a letter advances downward when selectedDir is down', () => {
    const { actions } = dispatchGridKey({ key: 'x' }, state({ selectedDir: 'down' }));
    expect(actions).toContainEqual({ type: 'setLetter', row: 0, col: 0, ch: 'X' });
    expect(actions).toContainEqual({ type: 'moveFocus', row: 1, col: 0 });
  });

  it('typing is blocked on a black cell', () => {
    const g = createEmptyGrid(5);
    g[0][0].isBlack = true;
    const { actions } = dispatchGridKey({ key: 'a' }, state({ grid: g }));
    expect(actions.find((a) => a.type === 'setLetter')).toBeUndefined();
  });

  it('typing is blocked on a theme-locked cell', () => {
    const g = createEmptyGrid(5);
    g[0][0].isThemeLocked = true;
    const { actions } = dispatchGridKey({ key: 'a' }, state({ grid: g }));
    expect(actions.find((a) => a.type === 'setLetter')).toBeUndefined();
  });

  it('Space toggles black on an unlocked cell', () => {
    const { actions } = dispatchGridKey({ key: ' ' }, state());
    expect(actions).toContainEqual({ type: 'toggleBlack', row: 0, col: 0 });
  });

  it('Space does not toggle black on a theme-locked cell', () => {
    const g = createEmptyGrid(5);
    g[0][0].isThemeLocked = true;
    const { actions } = dispatchGridKey({ key: ' ' }, state({ grid: g }));
    expect(actions.find((a) => a.type === 'toggleBlack')).toBeUndefined();
  });

  it('Enter rotates direction', () => {
    const { actions } = dispatchGridKey({ key: 'Enter' }, state());
    expect(actions).toContainEqual({ type: 'rotateDir' });
  });

  it('ArrowDown moves focus down AND switches direction to down', () => {
    const { actions } = dispatchGridKey({ key: 'ArrowDown' }, state({ selectedDir: 'across' }));
    expect(actions).toContainEqual({ type: 'moveFocus', row: 1, col: 0 });
    expect(actions).toContainEqual({ type: 'rotateDir' });
  });

  it('Tab jumps to the next across word start (empty grid)', () => {
    const { actions } = dispatchGridKey({ key: 'Tab' }, state());
    // On an empty 5x5, across slots start at (0,0),(1,0),... — next after (0,0) is (1,0)
    expect(actions).toContainEqual({ type: 'moveFocus', row: 1, col: 0 });
    expect(actions.find((a) => a.type === 'rotateDir')).toBeUndefined();
  });

  it('Tab switches to down slots after the last across slot', () => {
    // focus on the last across slot start (4,0); next wraps to first down slot (0,0) as "down"
    const { actions } = dispatchGridKey({ key: 'Tab' }, state({ focus: { row: 4, col: 0 } }));
    expect(actions).toContainEqual({ type: 'moveFocus', row: 0, col: 0 });
    expect(actions).toContainEqual({ type: 'rotateDir' });
  });

  it('Shift+Tab goes to the previous word start', () => {
    const { actions } = dispatchGridKey({ key: 'Tab', shiftKey: true }, state({ focus: { row: 2, col: 0 } }));
    expect(actions).toContainEqual({ type: 'moveFocus', row: 1, col: 0 });
  });

  it('Ctrl+L toggles the theme lock', () => {
    const { actions } = dispatchGridKey({ key: 'l', ctrlKey: true }, state());
    expect(actions).toContainEqual({ type: 'toggleLock', row: 0, col: 0 });
  });

  it('Backspace clears a filled cell', () => {
    const g = createEmptyGrid(5);
    g[0][1].letter = 'A';
    const { actions } = dispatchGridKey({ key: 'Backspace' }, state({ grid: g, focus: { row: 0, col: 1 } }));
    expect(actions).toContainEqual({ type: 'setLetter', row: 0, col: 1, ch: '' });
  });

  it('Backspace on an EMPTY cell steps focus backward without clearing (across->col-1, down->row-1)', () => {
    // Distinct from "Backspace clears a filled cell": here the focused cell has no letter,
    // so Backspace must STEP BACK (moveFocus) rather than emit a setLetter clear.
    const across = dispatchGridKey(
      { key: 'Backspace' },
      state({ focus: { row: 0, col: 2 }, selectedDir: 'across' })
    ).actions;
    expect(across).toContainEqual({ type: 'moveFocus', row: 0, col: 1 });
    expect(across.find((a) => a.type === 'setLetter')).toBeUndefined();

    const down = dispatchGridKey(
      { key: 'Backspace' },
      state({ focus: { row: 2, col: 0 }, selectedDir: 'down' })
    ).actions;
    expect(down).toContainEqual({ type: 'moveFocus', row: 1, col: 0 });
    expect(down.find((a) => a.type === 'setLetter')).toBeUndefined();
  });

  it('preventDefault is true for handled keys and false for unhandled keys', () => {
    // Handled keys must swallow the browser default.
    expect(dispatchGridKey({ key: 'a' }, state()).preventDefault).toBe(true);
    expect(dispatchGridKey({ key: ' ' }, state()).preventDefault).toBe(true);
    expect(dispatchGridKey({ key: 'Tab' }, state()).preventDefault).toBe(true);
    expect(dispatchGridKey({ key: 'ArrowDown' }, state()).preventDefault).toBe(true);
    // Unhandled keys must NOT preventDefault (let the browser handle them).
    expect(dispatchGridKey({ key: 'F1' }, state()).preventDefault).toBe(false);
    expect(dispatchGridKey({ key: 'Escape' }, state()).preventDefault).toBe(false);
  });
});

describe('CrosswordGrid (mounted, controlled)', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders one interaction rect per cell', () => {
    const props = baseProps();
    const { container } = render(<CrosswordGrid {...props} />);
    expect(hitRects(container).length).toBe(25);
  });

  it('click focuses a cell via onFocus(r,c)', () => {
    const props = baseProps({ focus: null });
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.click(hitRects(container)[6]); // (1,1)
    expect(props.onFocus).toHaveBeenCalledWith(1, 1);
  });

  it('Shift+Click toggles a black square', () => {
    const props = baseProps();
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.click(hitRects(container)[0], { shiftKey: true });
    expect(props.onToggleBlack).toHaveBeenCalledWith(0, 0);
  });

  it('right-click toggles the theme lock', () => {
    const props = baseProps();
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.contextMenu(hitRects(container)[0]);
    expect(props.onToggleLock).toHaveBeenCalledWith(0, 0);
  });

  it('typing advances focus in selectedDir', () => {
    const props = baseProps();
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.keyDown(container.querySelector('.xw-grid-focus'), { key: 'C' });
    expect(props.onSetLetter).toHaveBeenCalledWith(0, 0, 'C');
    expect(props.onMoveFocus).toHaveBeenCalledWith(0, 1);
  });

  it('ArrowDown moves focus and rotates direction (both fire in one event)', () => {
    const props = baseProps({ selectedDir: 'across' });
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.keyDown(container.querySelector('.xw-grid-focus'), { key: 'ArrowDown' });
    expect(props.onMoveFocus).toHaveBeenCalledWith(1, 0);
    expect(props.onRotateDir).toHaveBeenCalled();
  });

  it('Tab jumps to the next word start', () => {
    const props = baseProps();
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.keyDown(container.querySelector('.xw-grid-focus'), { key: 'Tab' });
    expect(props.onMoveFocus).toHaveBeenCalledWith(1, 0);
  });

  it('Space toggles black via the onToggleBlack callback', () => {
    const props = baseProps();
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.keyDown(container.querySelector('.xw-grid-focus'), { key: ' ' });
    expect(props.onToggleBlack).toHaveBeenCalledWith(0, 0);
  });

  it('renders black squares with the ink fill', () => {
    const g = createEmptyGrid(5);
    g[2][2].isBlack = true;
    const props = baseProps({ grid: g });
    const { container } = render(<CrosswordGrid {...props} />);
    const black = container.querySelectorAll('rect[fill="var(--ink)"]');
    expect(black.length).toBeGreaterThan(0);
  });

  it('renders heatmap shading on a high-tension, non-focused, non-highlighted cell', () => {
    // focus (0,0) across highlights row 0; pick (2,2) for tension so precedence
    // (black > focus > highlight > tension) leaves the tension fill visible.
    const heatmap = createEmptyGrid(5).map((row) => row.map(() => 0));
    heatmap[2][2] = 0.9;
    const props = baseProps({ heatmap, focus: { row: 0, col: 0 }, selectedDir: 'across' });
    const { container } = render(<CrosswordGrid {...props} />);
    const shaded = container.querySelectorAll('rect[fill="rgba(220, 80, 60, 0.14)"]');
    expect(shaded.length).toBe(1);
  });

  it('does not render heatmap shading when heatmap prop is null', () => {
    const props = baseProps({ heatmap: null });
    const { container } = render(<CrosswordGrid {...props} />);
    const shaded = container.querySelectorAll('rect[fill="rgba(220, 80, 60, 0.14)"]');
    expect(shaded.length).toBe(0);
  });

  it('rebinds to live focus + fresh handlers after rerender (no stale closure, no duplicate listener)', () => {
    // The keydown listener is attached exactly once (empty-deps effect) and reads live
    // state/handlers through stateRef.current. This guards two regressions at once:
    //   - reverting to a one-time stale-closure capture (would target the OLD focus and
    //     call the OLD onSetLetter mock), and
    //   - re-adding grid/state to the effect deps without a clean cleanup (would attach a
    //     duplicate live listener and fire the callback twice).
    const propsA = baseProps({ focus: { row: 0, col: 0 } });
    const { container, rerender } = render(<CrosswordGrid {...propsA} />);

    // Rerender the SAME instance with a DIFFERENT focus AND a fresh set of mock handlers.
    const propsB = baseProps({ focus: { row: 2, col: 3 } });
    rerender(<CrosswordGrid {...propsB} />);

    // Re-query the (same) container node after rerender, then fire exactly ONE keydown.
    fireEvent.keyDown(container.querySelector('.xw-grid-focus'), { key: 'q' });

    // (a) The letter targets the NEW focus cell via the live handler set — not a stale one.
    expect(propsB.onSetLetter).toHaveBeenCalledWith(2, 3, 'Q');
    // (b) Exactly once — a duplicate listener from a deps-reversion would fire it twice.
    expect(propsB.onSetLetter).toHaveBeenCalledTimes(1);
    // A stale mount-time closure would instead have called the OLD handler set.
    expect(propsA.onSetLetter).not.toHaveBeenCalled();
  });
});

describe('CrosswordGrid red (isBlocked) rendering', () => {
  it('renders exactly one data-blocked rect for two blocked cells, one of them black', () => {
    const grid = createEmptyGrid(5);
    grid[1][1] = { ...grid[1][1], isBlocked: true };
    grid[2][2] = { ...grid[2][2], isBlack: true, isBlocked: true };
    const { container } = render(<CrosswordGrid {...baseProps({ grid })} />);
    const reds = container.querySelectorAll('[data-blocked="true"]');
    expect(reds).toHaveLength(1);
    expect(reds[0].getAttribute('fill')).toBe('var(--danger)');
  });

  it('renders none when no cell is blocked', () => {
    const { container } = render(<CrosswordGrid {...baseProps()} />);
    expect(container.querySelectorAll('[data-blocked="true"]')).toHaveLength(0);
  });
});

// Task 4.4 — D1 writer gate (novice-readiness spec 0.2.6 section 2.3).
describe('dispatchGridKey while editingPaused', () => {
  const grid = createEmptyGrid(5);
  const state = (over = {}) => ({
    grid,
    size: 5,
    focus: { row: 1, col: 1 },
    selectedDir: 'across',
    slots: allSlots(grid),
    ...over,
  });
  const PAUSED = { preventDefault: true, actions: [] };

  it.each([
    ['a letter', { key: 'A' }],
    ['Backspace', { key: 'Backspace' }],
    ['Delete', { key: 'Delete' }],
    ['Space', { key: ' ' }],
    ['period', { key: '.' }],
    ['Ctrl+L', { key: 'l', ctrlKey: true }],
    ['Cmd+L', { key: 'L', metaKey: true }],
  ])('%s prevents default and emits no action', (_name, key) => {
    expect(dispatchGridKey(key, state({ editingPaused: true }))).toEqual(PAUSED);
  });

  it('Backspace on a filled cell would write when not paused (control)', () => {
    const g = createEmptyGrid(5);
    g[1][1].letter = 'Q';
    const live = dispatchGridKey({ key: 'Backspace' }, state({ grid: g, slots: allSlots(g) }));
    expect(live.actions).toContainEqual({ type: 'setLetter', row: 1, col: 1, ch: '' });
    expect(
      dispatchGridKey({ key: 'Backspace' }, state({ grid: g, slots: allSlots(g), editingPaused: true }))
    ).toEqual(PAUSED);
  });

  it.each([
    ['ArrowRight', {}],
    ['ArrowDown', {}],
    ['Tab', {}],
    ['Tab', { shiftKey: true }],
    ['Enter', {}],
  ])('%s behaves as today (regression pin)', (k, extra) => {
    const key = { key: k, ...extra };
    const live = dispatchGridKey(key, state({ editingPaused: false }));
    expect(live.actions.length).toBeGreaterThan(0);
    expect(dispatchGridKey(key, state({ editingPaused: true }))).toEqual(live);
  });
});

describe('CrosswordGrid while editingPaused (mounted)', () => {
  beforeEach(() => vi.clearAllMocks());
  const STATUS = 'Editing is paused while autofill runs.';

  it('renders the status text inside .xw-grid-wrap', () => {
    const { container } = render(<CrosswordGrid {...baseProps({ editingPaused: true })} />);
    const status = container.querySelector('.xw-grid-wrap [role="status"]');
    expect(status).not.toBeNull();
    expect(status.textContent).toBe(STATUS);
  });

  it('renders no status element when the prop is absent', () => {
    const { container } = render(<CrosswordGrid {...baseProps()} />);
    expect(container.querySelector('[role="status"]')).toBeNull();
  });

  it('Shift+click calls no onToggleBlack; Alt+click neither', () => {
    const props = baseProps({ editingPaused: true });
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.click(hitRects(container)[0], { shiftKey: true });
    fireEvent.click(hitRects(container)[0], { altKey: true });
    expect(props.onToggleBlack).not.toHaveBeenCalled();
  });

  it('right-click prevents default and calls no onToggleLock', () => {
    const props = baseProps({ editingPaused: true });
    const { container } = render(<CrosswordGrid {...props} />);
    const notCancelled = fireEvent.contextMenu(hitRects(container)[0]);
    expect(notCancelled).toBe(false);
    expect(props.onToggleLock).not.toHaveBeenCalled();
  });

  it('a plain click still focuses', () => {
    const props = baseProps({ editingPaused: true, focus: null });
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.click(hitRects(container)[6]);
    expect(props.onFocus).toHaveBeenCalledWith(1, 1);
  });

  it('typing through the mounted listener calls no onSetLetter', () => {
    const props = baseProps({ editingPaused: true });
    const { container } = render(<CrosswordGrid {...props} />);
    fireEvent.keyDown(container.querySelector('.xw-grid-focus'), { key: 'C' });
    expect(props.onSetLetter).not.toHaveBeenCalled();
    expect(props.onMoveFocus).not.toHaveBeenCalled();
  });
});
