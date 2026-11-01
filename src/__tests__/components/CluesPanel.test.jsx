/**
 * Tests for CluesPanel (clue-authoring spec 0.1.4, sections 5.2-5.5 and 6.2 "Panel").
 *
 * The panel is presentational with its own draft state. App-like behaviour (the committed text
 * changing after a commit) is exercised through a small stateful Harness defined below.
 * The component is loaded dynamically per test so each test fails on its own at RED.
 */

import React, { useRef, useState } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { fromCliStrings, applyNumbering } from '../../api/gridCodec';
import { slotAt } from '../../hooks/useGridGeometry';
import {
  clueStatuses,
  applyCommit,
  applyKeep,
  applyDelete,
  parseClueKey,
  CLUE_TOO_LONG,
} from '../../lib/clues';

const PLACEHOLDER = 'Write a clue…';
const DOT = '·';
const DASH = '–';

async function loadPanel() {
  const mod = await import(/* @vite-ignore */ ['..', '..', 'components', 'CluesPanel'].join('/'));
  return mod.default;
}

// ---------- fixtures ----------

// 3x3 all white, numbered the usual way.
const WHITE3_NUMBERS = { '(0,0)': 1, '(0,1)': 2, '(0,2)': 3, '(1,0)': 4, '(2,0)': 5 };
const white3 = (rows = [['.', '.', '.'], ['.', '.', '.'], ['.', '.', '.']]) => fromCliStrings(rows);
const white3Numbered = (rows) => applyNumbering(white3(rows), WHITE3_NUMBERS);

// Black centre: across entries start (0,0) and (2,0); down entries start (0,0) and (0,2).
const RING_NUMBERS = { '(0,0)': 1, '(0,2)': 2, '(2,0)': 3 };
const ringRows = [['A', 'B', 'C'], ['.', '#', '.'], ['D', 'E', 'F']];
const ring = () => applyNumbering(fromCliStrings(ringRows), RING_NUMBERS);

// ---------- helpers ----------

/** Deepest elements whose whole text content equals `text` (does not pin markup). */
function textOf(text) {
  const norm = (s) => s.replace(/\s+/g, ' ').trim();
  return screen.queryAllByText((_, el) => {
    if (norm(el.textContent) !== text) return false;
    return !Array.from(el.children).some((ch) => norm(ch.textContent) === text);
  });
}
const hasText = (text) => textOf(text).length > 0;

const inputs = () => screen.queryAllByPlaceholderText(PLACEHOLDER);
const rowOf = (input) => input.closest('.xw-clue-row');
const onRows = (container) => Array.from(container.querySelectorAll('.xw-clue-row.on'));

/** The number buttons showing `label`, in document order. */
function numberButtons(label) {
  return screen
    .queryAllByText(String(label))
    .map((el) => el.closest('button'))
    .filter(Boolean);
}

/** The read-only text of an orphan, whether rendered as text or as a read-only field. */
function orphanText(text) {
  return screen.queryByText(text) || screen.queryByDisplayValue(text);
}

function Harness({ Panel, grid, initial = {}, spies = {}, ...rest }) {
  const [clues, setClues] = useState(initial);
  const ref = useRef(initial);
  const write = (next) => {
    ref.current = next;
    setClues(next);
  };
  return (
    <Panel
      grid={grid}
      clues={clues}
      displayStatuses={clueStatuses(grid, clues)}
      selectedCell={null}
      editingPaused={false}
      onSelect={() => {}}
      {...rest}
      onCommit={(key, draft) => {
        if (spies.onCommit) spies.onCommit(key, draft);
        const { row, col, dir } = parseClueKey(key);
        const res = applyCommit(ref.current, key, draft, slotAt(grid, row, col, dir).pattern);
        if (!res.error) write(res.clues);
        return { error: res.error };
      }}
      onKeep={(key) => {
        if (spies.onKeep) spies.onKeep(key);
        const { row, col, dir } = parseClueKey(key);
        write(applyKeep(ref.current, key, slotAt(grid, row, col, dir).pattern));
      }}
      onDelete={(key) => {
        if (spies.onDelete) spies.onDelete(key);
        write(applyDelete(ref.current, key));
      }}
    />
  );
}

function plainProps(grid, clues = {}, extra = {}) {
  return {
    grid,
    clues,
    displayStatuses: clueStatuses(grid, clues),
    selectedCell: null,
    editingPaused: false,
    onCommit: vi.fn(() => ({ error: null })),
    onKeep: vi.fn(),
    onDelete: vi.fn(),
    onSelect: vi.fn(),
    ...extra,
  };
}

describe('CluesPanel', () => {
  let originalScroll;
  beforeEach(() => {
    originalScroll = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = vi.fn();
  });
  afterEach(() => {
    Element.prototype.scrollIntoView = originalScroll;
  });

  // ---------------- header and groups ----------------

  describe('header and groups', () => {
    it('shows the title and the entry counts on a grid with no clues', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(white3())} />);
      expect(hasText('Clues')).toBe(true);
      expect(hasText(`3 across ${DOT} 3 down`)).toBe(true);
      expect(screen.queryByText(/stale/)).toBeNull();
      expect(screen.queryByText(/orphaned/)).toBeNull();
    });

    it('counts entries, not clues, in the header sub-line', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(ring(), { '0,0,across': { text: 'One', answer: 'ABC' } })} />);
      expect(hasText(`2 across ${DOT} 2 down`)).toBe(true);
    });

    it('appends the stale and orphaned counts to the sub-line', async () => {
      const Panel = await loadPanel();
      const grid = white3([['C', 'A', 'T'], ['.', '.', '.'], ['.', '.', '.']]);
      const clues = {
        '0,0,across': { text: 'Feline', answer: 'C?T' }, // stale
        '10,0,across': { text: 'Gone one', answer: 'AB' }, // orphaned
        '2,0,down': { text: 'Gone two', answer: 'C?D' }, // orphaned
      };
      render(<Panel {...plainProps(grid, clues)} />);
      expect(hasText(`3 across ${DOT} 3 down ${DOT} 1 stale ${DOT} 2 orphaned`)).toBe(true);
    });

    it('counts stale and orphaned by the displayed status', async () => {
      const Panel = await loadPanel();
      const grid = white3([['C', 'A', 'T'], ['.', '.', '.'], ['.', '.', '.']]);
      const clues = { '0,0,across': { text: 'Feline', answer: 'CAT' } }; // browser says ok
      render(
        <Panel {...plainProps(grid, clues, { displayStatuses: { '0,0,across': 'stale' } })} />
      );
      expect(hasText(`3 across ${DOT} 3 down ${DOT} 1 stale`)).toBe(true);
    });

    it('heads the groups with the entry counts', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(ring())} />);
      expect(hasText(`Across ${DOT} 2`)).toBe(true);
      expect(hasText(`Down ${DOT} 2`)).toBe(true);
    });

    it('shows the empty-group texts on an all-black grid', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(fromCliStrings([['#', '#', '#'], ['#', '#', '#'], ['#', '#', '#']]))} />);
      expect(hasText('No across words yet.')).toBe(true);
      expect(hasText('No down words yet.')).toBe(true);
      expect(hasText(`Across ${DOT} 0`)).toBe(true);
      expect(hasText(`Down ${DOT} 0`)).toBe(true);
      expect(hasText(`0 across ${DOT} 0 down`)).toBe(true);
      expect(inputs()).toHaveLength(0);
    });

    it('does not show the empty-group texts when entries exist', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(ring())} />);
      expect(screen.queryByText('No across words yet.')).toBeNull();
      expect(screen.queryByText('No down words yet.')).toBeNull();
    });
  });

  // ---------------- rows ----------------

  describe('rows', () => {
    it('shows a dash on every number button before numbering', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(white3())} />);
      const dashes = screen.queryAllByText(DASH).map((el) => el.closest('button'));
      expect(dashes).toHaveLength(6);
      dashes.forEach((b) => expect(b).not.toBeNull());
    });

    it('lists rows in reading order, Across then Down', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(ring())} />);
      const rows = inputs().map(rowOf);
      expect(rows).toHaveLength(4);
      // Across: (0,0) ABC then (2,0) DEF. Down: (0,0) A?D then (0,2) C?F.
      expect(rows[0].textContent).toContain('ABC');
      expect(rows[1].textContent).toContain('DEF');
      expect(rows[2].textContent).toContain(`A${DOT}D`);
      expect(rows[3].textContent).toContain(`C${DOT}F`);
      expect(numberButtons(1)).toHaveLength(2);
      expect(rows[0].contains(numberButtons(1)[0])).toBe(true);
      expect(rows[1].contains(numberButtons(3)[0])).toBe(true);
      expect(rows[2].contains(numberButtons(1)[1])).toBe(true);
      expect(rows[3].contains(numberButtons(2)[0])).toBe(true);
    });

    it('orders rows by row and then column when starts differ in both', async () => {
      const Panel = await loadPanel();
      // Across starts: (0,0) ...., (1,0) ...., (2,2) .. ; the (2,2) start is after (1,0).
      const grid = fromCliStrings([['.', '.', '.', '.'], ['.', '.', '.', '.'], ['#', '#', '.', '.'], ['#', '.', '.', '.']]);
      const numbers = { '(0,0)': 1, '(1,0)': 5, '(2,2)': 9, '(3,1)': 10 };
      render(<Panel {...plainProps(applyNumbering(grid, numbers))} />);
      const rows = inputs().map(rowOf);
      expect(rows).toHaveLength(8); // 4 across, then 4 down
      expect(rows[0].contains(numberButtons(1)[0])).toBe(true);
      expect(rows[1].contains(numberButtons(5)[0])).toBe(true);
      expect(rows[2].contains(numberButtons(9)[0])).toBe(true);
      expect(rows[3].contains(numberButtons(10)[0])).toBe(true);
    });

    it('shows one box per square, a letter or a dot for an empty one', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(white3([['A', '.', 'C'], ['.', '.', '.'], ['.', '.', '.']]))} />);
      const first = rowOf(inputs()[0]);
      expect(first.textContent).toContain(`A${DOT}C`);
      const emptyAcross = rowOf(inputs()[1]);
      expect(emptyAcross.textContent).toContain(`${DOT}${DOT}${DOT}`);
    });

    it('gives every row the placeholder', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(white3())} />);
      expect(screen.getAllByPlaceholderText(PLACEHOLDER)).toHaveLength(6);
    });

    it('shows the committed text in the row input', async () => {
      const Panel = await loadPanel();
      const grid = white3();
      render(<Panel {...plainProps(grid, { '1,0,across': { text: 'Middle', answer: '???' } })} />);
      expect(inputs()[1]).toHaveValue('Middle');
      expect(inputs()[0]).toHaveValue('');
    });
  });

  // ---------------- stale rows and Keep ----------------

  describe('stale rows', () => {
    const grid = () => white3([['C', 'A', 'T'], ['.', '.', '.'], ['.', '.', '.']]);
    const staleClues = { '0,0,across': { text: 'Feline', answer: 'C?T' } };

    it('shows Written for and a Keep button on a stale row', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(grid(), staleClues)} />);
      expect(hasText(`Written for C${DOT}T`)).toBe(true);
      expect(screen.getAllByRole('button', { name: 'Keep' })).toHaveLength(1);
    });

    it('shows neither on an ok row', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(grid(), { '0,0,across': { text: 'Feline', answer: 'CAT' } })} />);
      expect(screen.queryByText(/Written for/)).toBeNull();
      expect(screen.queryByRole('button', { name: 'Keep' })).toBeNull();
    });

    it('calls onKeep with the key', async () => {
      const Panel = await loadPanel();
      const props = plainProps(grid(), staleClues);
      render(<Panel {...props} />);
      await userEvent.setup().click(screen.getByRole('button', { name: 'Keep' }));
      expect(props.onKeep).toHaveBeenCalledTimes(1);
      expect(props.onKeep).toHaveBeenCalledWith('0,0,across');
    });

    it('is no longer stale after Keep, through the harness', async () => {
      const Panel = await loadPanel();
      render(<Harness Panel={Panel} grid={grid()} initial={staleClues} />);
      await userEvent.setup().click(screen.getByRole('button', { name: 'Keep' }));
      expect(screen.queryByRole('button', { name: 'Keep' })).toBeNull();
      expect(screen.queryByText(/Written for/)).toBeNull();
      expect(inputs()[0]).toHaveValue('Feline');
    });

    it('follows the displayed status: no Keep when the display says ok', async () => {
      const Panel = await loadPanel();
      // The browser rule says stale (C?T vs CAT); the displayed status is ok.
      render(
        <Panel {...plainProps(grid(), staleClues, { displayStatuses: { '0,0,across': 'ok' } })} />
      );
      expect(screen.queryByRole('button', { name: 'Keep' })).toBeNull();
      expect(screen.queryByText(/Written for/)).toBeNull();
    });

    it('follows the displayed status: Keep when the display says stale', async () => {
      const Panel = await loadPanel();
      // The browser rule says ok (CAT vs CAT); the displayed status is stale.
      render(
        <Panel
          {...plainProps(grid(), { '0,0,across': { text: 'Feline', answer: 'CAT' } }, {
            displayStatuses: { '0,0,across': 'stale' },
          })}
        />
      );
      expect(screen.getAllByRole('button', { name: 'Keep' })).toHaveLength(1);
    });
  });

  // ---------------- orphans ----------------

  describe('orphans', () => {
    const orphanClues = {
      '10,0,across': { text: 'Alpha text', answer: 'AB' },
      '2,0,down': { text: 'Beta text', answer: 'C?D' },
    };

    it('shows the Orphaned heading and its explanation line', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(white3(), orphanClues)} />);
      expect(hasText(`Orphaned ${DOT} 2`)).toBe(true);
      expect(
        hasText('These entries no longer exist. Copy a clue into an entry, or delete it.')
      ).toBe(true);
    });

    it('lists orphans in key order with answer boxes, text and Delete', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(white3(), orphanClues)} />);
      const beta = orphanText('Beta text');
      const alpha = orphanText('Alpha text');
      expect(beta).not.toBeNull();
      expect(alpha).not.toBeNull();
      const deletes = screen.getAllByRole('button', { name: 'Delete' });
      expect(deletes).toHaveLength(2);
      const before = (a, b) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
      // "2,0,down" sorts before "10,0,across": Beta, its Delete, Alpha, its Delete.
      expect(before(beta, deletes[0])).toBe(true);
      expect(before(deletes[0], alpha)).toBe(true);
      expect(before(alpha, deletes[1])).toBe(true);

      const item = (btn, textEl) => {
        let el = btn.parentElement;
        while (el && !el.contains(textEl)) el = el.parentElement;
        return el;
      };
      expect(item(deletes[0], beta).textContent).toContain(`C${DOT}D`);
      expect(item(deletes[1], alpha).textContent).toContain('AB');
    });

    it('calls onDelete with the key', async () => {
      const Panel = await loadPanel();
      const props = plainProps(white3(), orphanClues);
      render(<Panel {...props} />);
      await userEvent.setup().click(screen.getAllByRole('button', { name: 'Delete' })[0]);
      expect(props.onDelete).toHaveBeenCalledTimes(1);
      expect(props.onDelete).toHaveBeenCalledWith('2,0,down');
    });

    it('removes the orphan after Delete, through the harness', async () => {
      const Panel = await loadPanel();
      render(<Harness Panel={Panel} grid={white3()} initial={orphanClues} />);
      await userEvent.setup().click(screen.getAllByRole('button', { name: 'Delete' })[0]);
      expect(screen.getAllByRole('button', { name: 'Delete' })).toHaveLength(1);
      expect(hasText(`Orphaned ${DOT} 1`)).toBe(true);
      expect(orphanText('Beta text')).toBeNull();
    });

    it('shows no Orphaned heading when there are no orphans', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(white3(), { '0,0,across': { text: 'Fine', answer: '???' } })} />);
      expect(screen.queryByText(/Orphaned/)).toBeNull();
      expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull();
    });

    it('shows Delete by the displayed status, not the browser rule', async () => {
      const Panel = await loadPanel();
      // The browser rule says orphaned (no such entry); the displayed status is ok.
      render(
        <Panel
          {...plainProps(white3(), { '10,0,across': { text: 'Alpha text', answer: 'AB' } }, {
            displayStatuses: { '10,0,across': 'ok' },
          })}
        />
      );
      expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull();
    });

    it('moves a clue between its row and Orphaned as its entry goes and returns', async () => {
      const Panel = await loadPanel();
      const clues = { '0,1,down': { text: 'Moving', answer: '???' } };
      const gridWithEntry = white3();
      const gridWithoutEntry = white3([['.', '#', '.'], ['.', '.', '.'], ['.', '.', '.']]);
      const mk = (grid) => <Panel {...plainProps(grid, clues)} />;

      const { rerender } = render(mk(gridWithEntry));
      expect(screen.getByDisplayValue('Moving')).toHaveAttribute('placeholder', PLACEHOLDER);
      expect(screen.queryByText(/Orphaned/)).toBeNull();
      expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull();

      rerender(mk(gridWithoutEntry));
      expect(hasText(`Orphaned ${DOT} 1`)).toBe(true);
      expect(screen.getAllByRole('button', { name: 'Delete' })).toHaveLength(1);
      expect(orphanText('Moving')).not.toBeNull();

      rerender(mk(gridWithEntry));
      expect(screen.queryByText(/Orphaned/)).toBeNull();
      expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull();
      expect(screen.getByDisplayValue('Moving')).toHaveAttribute('placeholder', PLACEHOLDER);
    });
  });

  // ---------------- drafts and keys ----------------

  describe('drafts and keys', () => {
    it('commits on blur once, with the untrimmed draft', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const props = plainProps(white3());
      render(<Panel {...props} />);
      await user.type(inputs()[0], '  hi  ');
      expect(props.onCommit).not.toHaveBeenCalled();
      await user.click(document.body);
      expect(props.onCommit).toHaveBeenCalledTimes(1);
      expect(props.onCommit).toHaveBeenCalledWith('0,0,across', '  hi  ');
    });

    it('commits on Enter and focuses the next row input', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const spies = { onCommit: vi.fn() };
      render(<Harness Panel={Panel} grid={white3()} spies={spies} />);
      await user.type(inputs()[0], 'first{Enter}');
      expect(spies.onCommit).toHaveBeenCalledWith('0,0,across', 'first');
      expect(inputs()[1]).toHaveFocus();
      expect(inputs()[0]).toHaveValue('first');
    });

    it('passes from the last Across row to the first Down row', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      render(<Harness Panel={Panel} grid={white3()} />);
      // Rows: three Across, then three Down.
      await user.type(inputs()[2], 'last across{Enter}');
      expect(inputs()[3]).toHaveFocus();
    });

    it('keeps focus on Enter in the last row', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      render(<Harness Panel={Panel} grid={white3()} />);
      const last = inputs()[5];
      await user.type(last, 'end{Enter}');
      expect(last).toHaveFocus();
      expect(last).toHaveValue('end');
    });

    it('refuses an Enter over 200 characters: message, draft and focus kept', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      render(<Harness Panel={Panel} grid={white3()} />);
      const input = inputs()[0];
      const long = 'x'.repeat(201);
      await user.click(input);
      fireEvent.change(input, { target: { value: long } });
      await user.keyboard('{Enter}');
      expect(screen.getByText(CLUE_TOO_LONG)).toBeInTheDocument();
      expect(CLUE_TOO_LONG).toBe('At most 200 characters.');
      expect(input).toHaveValue(long);
      expect(input).toHaveFocus();
      await user.keyboard('y');
      expect(screen.queryByText(CLUE_TOO_LONG)).toBeNull();
    });

    it('Escape restores the committed text and keeps focus', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const initial = { '0,0,across': { text: 'Orig', answer: '???' } };
      render(<Harness Panel={Panel} grid={white3()} initial={initial} />);
      const input = inputs()[0];
      await user.type(input, 'zz');
      expect(input).toHaveValue('Origzz');
      await user.keyboard('{Escape}');
      expect(input).toHaveValue('Orig');
      expect(input).toHaveFocus();
    });

    it('Escape discards the draft: a later blur does not commit it', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const props = plainProps(white3(), { '0,0,across': { text: 'Orig', answer: '???' } });
      render(<Panel {...props} />);
      const input = inputs()[0];
      await user.type(input, 'abandoned');
      expect(input).toHaveValue('Origabandoned');
      await user.keyboard('{Escape}');
      expect(input).toHaveValue('Orig');
      await user.click(document.body);
      expect(props.onCommit).not.toHaveBeenCalledWith('0,0,across', 'Origabandoned');
    });

    it('Escape discards the draft: a later unmount does not commit it', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const props = plainProps(white3(), { '0,0,across': { text: 'Orig', answer: '???' } });
      const { unmount } = render(<Panel {...props} />);
      const input = inputs()[0];
      await user.type(input, 'abandoned');
      await user.keyboard('{Escape}');
      expect(input).toHaveValue('Orig');
      unmount();
      expect(props.onCommit).not.toHaveBeenCalledWith('0,0,across', 'Origabandoned');
    });

    it('after Enter, Escape restores the text just committed', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      render(<Harness Panel={Panel} grid={white3()} />);
      await user.type(inputs()[0], 'New{Enter}');
      await user.click(inputs()[0]);
      await user.keyboard('more');
      expect(inputs()[0]).toHaveValue('Newmore');
      await user.keyboard('{Escape}');
      expect(inputs()[0]).toHaveValue('New');
      expect(inputs()[0]).toHaveFocus();
    });

    it('replaces a draft when the committed text changes beneath it', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const grid = white3();
      const first = plainProps(grid, { '0,0,across': { text: 'One', answer: '???' } });
      const { rerender } = render(<Panel {...first} />);
      await user.type(inputs()[0], ' draft');
      expect(inputs()[0]).toHaveValue('One draft');
      rerender(
        <Panel {...plainProps(grid, { '0,0,across': { text: 'Two', answer: '???' } })} />
      );
      expect(inputs()[0]).toHaveValue('Two');
    });

    it('commits a draft once when the panel unmounts', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const props = plainProps(white3());
      const { unmount } = render(<Panel {...props} />);
      await user.type(inputs()[0], 'abc');
      expect(props.onCommit).not.toHaveBeenCalled();
      unmount();
      expect(props.onCommit).toHaveBeenCalledTimes(1);
      expect(props.onCommit).toHaveBeenCalledWith('0,0,across', 'abc');
    });
  });

  // ---------------- selection ----------------

  describe('selection', () => {
    it('selects the entry start and focuses the input on a number click', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const props = plainProps(ring());
      render(<Panel {...props} />);
      await user.click(numberButtons(2)[0]);
      expect(props.onSelect).toHaveBeenCalledWith(0, 2, 'down');
      expect(inputs()[3]).toHaveFocus();

      await user.click(numberButtons(3)[0]);
      expect(props.onSelect).toHaveBeenCalledWith(2, 0, 'across');
      expect(inputs()[1]).toHaveFocus();
    });

    it('selects the entry start when a row input gains focus', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const props = plainProps(ring());
      render(<Panel {...props} />);
      await user.click(inputs()[1]);
      expect(props.onSelect).toHaveBeenCalledWith(2, 0, 'across');
      await user.click(inputs()[3]);
      expect(props.onSelect).toHaveBeenCalledWith(0, 2, 'down');
    });

    it('highlights the row of the grid selection, scrolls it, and leaves focus alone', async () => {
      const Panel = await loadPanel();
      const grid = ring();
      const props = plainProps(grid);
      const ui = (selectedCell) => (
        <>
          <button data-testid="grid-focus">grid</button>
          <Panel {...props} selectedCell={selectedCell} />
        </>
      );
      const { container, rerender } = render(ui(null));
      const outside = screen.getByTestId('grid-focus');
      outside.focus();
      expect(onRows(container)).toHaveLength(0);

      // (0,1) lies inside the across entry that starts at (0,0).
      rerender(ui({ row: 0, col: 1, direction: 'across' }));
      expect(onRows(container)).toEqual([rowOf(inputs()[0])]);
      expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' });
      const scrolled = Element.prototype.scrollIntoView.mock.instances;
      expect(scrolled.some((el) => rowOf(inputs()[0]).contains(el) || el === rowOf(inputs()[0]))).toBe(
        true
      );
      expect(document.activeElement).toBe(outside);

      // (1,2) lies inside the down entry that starts at (0,2).
      rerender(ui({ row: 1, col: 2, direction: 'down' }));
      expect(onRows(container)).toEqual([rowOf(inputs()[3])]);
      expect(document.activeElement).toBe(outside);
    });

    it('highlights no row for a cell with no entry in its direction', async () => {
      const Panel = await loadPanel();
      const props = plainProps(ring());
      const { container, rerender } = render(
        <Panel {...props} selectedCell={{ row: 0, col: 1, direction: 'across' }} />
      );
      expect(onRows(container)).toHaveLength(1);
      // (1,0) is white but its across run is a single square: no entry.
      rerender(<Panel {...props} selectedCell={{ row: 1, col: 0, direction: 'across' }} />);
      expect(onRows(container)).toHaveLength(0);
    });
  });

  // ---------------- editingPaused ----------------

  describe('editingPaused', () => {
    it('disables inputs, Keep and Delete but still selects on a number click', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      const grid = white3Numbered([['C', 'A', 'T'], ['.', '.', '.'], ['.', '.', '.']]);
      const clues = {
        '0,0,across': { text: 'Feline', answer: 'C?T' }, // stale
        '10,0,across': { text: 'Gone', answer: 'AB' }, // orphaned
      };
      const props = plainProps(grid, clues, { editingPaused: true });
      render(<Panel {...props} />);
      inputs().forEach((i) => expect(i).toBeDisabled());
      expect(screen.getByRole('button', { name: 'Keep' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled();

      await user.click(numberButtons(4)[0]);
      expect(props.onSelect).toHaveBeenCalledWith(1, 0, 'across');
    });

    it('leaves inputs, Keep and Delete enabled when not paused', async () => {
      const Panel = await loadPanel();
      const grid = white3Numbered([['C', 'A', 'T'], ['.', '.', '.'], ['.', '.', '.']]);
      const clues = {
        '0,0,across': { text: 'Feline', answer: 'C?T' },
        '10,0,across': { text: 'Gone', answer: 'AB' },
      };
      render(<Panel {...plainProps(grid, clues)} />);
      inputs().forEach((i) => expect(i).toBeEnabled());
      expect(screen.getByRole('button', { name: 'Keep' })).toBeEnabled();
      expect(screen.getByRole('button', { name: 'Delete' })).toBeEnabled();
    });
  });

  // ---------------- pins added after the Task 7 review ----------------

  describe('review pins', () => {
    it('Keep on the second stale row calls onKeep with the second key', async () => {
      const Panel = await loadPanel();
      const grid = white3([['C', 'A', 'T'], ['D', 'O', 'G'], ['.', '.', '.']]);
      const clues = {
        '0,0,across': { text: 'Feline', answer: 'C?T' },
        '1,0,across': { text: 'Hound', answer: 'D?G' },
      };
      const props = plainProps(grid, clues);
      render(<Panel {...props} />);
      const keeps = screen.getAllByRole('button', { name: 'Keep' });
      expect(keeps).toHaveLength(2);
      await userEvent.setup().click(keeps[1]);
      expect(props.onKeep).toHaveBeenCalledTimes(1);
      expect(props.onKeep).toHaveBeenCalledWith('1,0,across');
    });

    it('Delete on the second orphan calls onDelete with the second key in key order', async () => {
      const Panel = await loadPanel();
      const clues = {
        '10,0,across': { text: 'Alpha text', answer: 'AB' },
        '2,0,down': { text: 'Beta text', answer: 'C?D' },
      };
      const props = plainProps(white3(), clues);
      render(<Panel {...props} />);
      const deletes = screen.getAllByRole('button', { name: 'Delete' });
      expect(deletes).toHaveLength(2);
      await userEvent.setup().click(deletes[1]);
      expect(props.onDelete).toHaveBeenCalledTimes(1);
      expect(props.onDelete).toHaveBeenCalledWith('10,0,across');
    });

    it('counts across and down separately in the header and the group headings', async () => {
      const Panel = await loadPanel();
      // Across starts (0,0), (1,0), (2,0); down starts (0,0), (0,1).
      const grid = fromCliStrings([['.', '.', '#'], ['.', '.', '#'], ['.', '.', '#']]);
      render(<Panel {...plainProps(grid)} />);
      expect(hasText(`3 across ${DOT} 2 down`)).toBe(true);
      expect(hasText(`Across ${DOT} 3`)).toBe(true);
      expect(hasText(`Down ${DOT} 2`)).toBe(true);
    });

    it('shows the empty text only for the direction that has no entries', async () => {
      const Panel = await loadPanel();
      // One across entry, no down entry.
      const acrossOnly = fromCliStrings([['.', '.', '.'], ['#', '#', '#'], ['#', '#', '#']]);
      const first = render(<Panel {...plainProps(acrossOnly)} />);
      expect(hasText(`1 across ${DOT} 0 down`)).toBe(true);
      expect(hasText('No down words yet.')).toBe(true);
      expect(screen.queryByText('No across words yet.')).toBeNull();
      first.unmount();

      // One down entry, no across entry.
      const downOnly = fromCliStrings([['.', '#', '#'], ['.', '#', '#'], ['.', '#', '#']]);
      render(<Panel {...plainProps(downOnly)} />);
      expect(hasText(`0 across ${DOT} 1 down`)).toBe(true);
      expect(hasText('No across words yet.')).toBe(true);
      expect(screen.queryByText('No down words yet.')).toBeNull();
    });

    it('counts only the orphans in the Orphaned heading when an ok clue exists', async () => {
      const Panel = await loadPanel();
      const clues = {
        '0,0,across': { text: 'Fine', answer: '???' }, // ok
        '10,0,across': { text: 'Gone', answer: 'AB' }, // orphaned
      };
      render(<Panel {...plainProps(white3(), clues)} />);
      expect(hasText(`Orphaned ${DOT} 1`)).toBe(true);
      expect(screen.queryByText(`Orphaned ${DOT} 2`)).toBeNull();
    });

    it('drops the row of a clue whose entry goes, and brings it back', async () => {
      const Panel = await loadPanel();
      const clues = { '0,1,down': { text: 'Moving', answer: '???' } };
      const gridWithEntry = white3();
      const gridWithoutEntry = white3([['.', '#', '.'], ['.', '.', '.'], ['.', '.', '.']]);
      const mk = (grid) => <Panel {...plainProps(grid, clues)} />;

      const { rerender } = render(mk(gridWithEntry));
      expect(screen.queryByDisplayValue('Moving')).not.toBeNull();

      rerender(mk(gridWithoutEntry));
      expect(screen.queryByDisplayValue('Moving')).toBeNull();
      expect(orphanText('Moving')).not.toBeNull();

      rerender(mk(gridWithEntry));
      expect(screen.queryByDisplayValue('Moving')).not.toBeNull();
    });

    it('Escape clears the refusal message of a refused Enter', async () => {
      const Panel = await loadPanel();
      const user = userEvent.setup();
      render(<Harness Panel={Panel} grid={white3()} />);
      const input = inputs()[0];
      await user.click(input);
      fireEvent.change(input, { target: { value: 'x'.repeat(201) } });
      await user.keyboard('{Enter}');
      expect(screen.getByText(CLUE_TOO_LONG)).toBeInTheDocument();
      await user.keyboard('{Escape}');
      expect(screen.queryByText(CLUE_TOO_LONG)).toBeNull();
      expect(input).toHaveValue('');
    });

    it('draws one box per square, each showing its letter or a dot', async () => {
      const Panel = await loadPanel();
      render(<Panel {...plainProps(white3([['A', '.', 'C'], ['.', '.', '.'], ['.', '.', '.']]))} />);
      const boxes = (row) =>
        Array.from(row.querySelectorAll('.xw-clue-pat-box')).map((b) => b.textContent);
      expect(boxes(rowOf(inputs()[0]))).toEqual(['A', DOT, 'C']);
      expect(boxes(rowOf(inputs()[1]))).toEqual([DOT, DOT, DOT]);
    });
  });
});
