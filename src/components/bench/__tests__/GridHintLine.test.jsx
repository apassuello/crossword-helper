/**
 * novice-readiness spec 0.2.7 §3.3 (G7): the hint line text, and a test that
 * every key the line names is handled by dispatchGridKey (not the reverse).
 */
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import GridHintLine, { GRID_HINT } from '../GridHintLine';
import { dispatchGridKey } from '../CrosswordGrid';
import { allSlots } from '../../../hooks/useGridGeometry';
import { createEmptyGrid } from '../../../__tests__/fixtures/gridFixtures';

describe('GridHintLine', () => {
  it('GRID_HINT is exactly the §3.3 line', () => {
    expect(GRID_HINT).toBe(
      'Type letters · Arrows move · Space or . black square · Enter switch direction · Tab next word · Backspace clear'
    );
  });

  it('renders GRID_HINT in a p.xw-grid-hint', () => {
    const { container } = render(<GridHintLine />);
    const p = container.querySelector('p.xw-grid-hint');
    expect(p).not.toBeNull();
    expect(p.textContent).toBe(GRID_HINT);
  });
});

describe('every key the hint line names is handled by dispatchGridKey', () => {
  // White, empty, unlocked focus cell with neighbours on every side.
  const grid = createEmptyGrid(5);
  const withLetter = createEmptyGrid(5).map((row) => row.map((c) => ({ ...c })));
  withLetter[2][2].letter = 'Q';
  const st = (g) => ({
    grid: g,
    size: 5,
    focus: { row: 2, col: 2 },
    selectedDir: 'across',
    slots: allSlots(g),
  });
  const press = (key, g = grid) => dispatchGridKey({ key }, st(g));
  const types = (res) => res.actions.map((a) => a.type);

  const rows = {
    'Type letters': () => {
      const res = press('a');
      expect(res.preventDefault).toBe(true);
      expect(res.actions).toContainEqual(
        expect.objectContaining({ type: 'setLetter', ch: 'A' })
      );
    },
    'Arrows move': () => {
      for (const k of ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']) {
        const res = press(k);
        expect(res.preventDefault, k).toBe(true);
        expect(types(res), k).toContain('moveFocus');
      }
    },
    'Space or . black square': () => {
      for (const k of [' ', '.']) {
        expect(types(press(k)), JSON.stringify(k)).toContain('toggleBlack');
      }
    },
    'Enter switch direction': () => {
      expect(types(press('Enter'))).toContain('rotateDir');
    },
    'Tab next word': () => {
      expect(types(press('Tab'))).toContain('moveFocus');
    },
    'Backspace clear': () => {
      expect(press('Backspace', withLetter).actions).toContainEqual(
        expect.objectContaining({ type: 'setLetter', ch: '' })
      );
    },
  };

  const segments = GRID_HINT.split(' · ');

  it('has a row for every hint segment', () => {
    for (const seg of segments) expect(rows, seg).toHaveProperty([seg]);
  });

  it.each(segments)('%s', (seg) => {
    expect(rows[seg], `no handler check for hint segment "${seg}"`).toBeTypeOf('function');
    rows[seg]();
  });
});
