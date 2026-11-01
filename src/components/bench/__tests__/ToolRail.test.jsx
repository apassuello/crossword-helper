/**
 * Tests for ToolRail (Task 6, U2) — the ported Constructor's Bench tool navigation rail.
 *
 * Fully controlled: no internal state. `viewToggles` + `onToggleView(which)` replace the
 * bundle's two separate onToggleSym/onToggleHeatmap callbacks with a single handler
 * (per the plan's public prop API).
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { ToolRail } from '../ToolRail';

// clue-authoring spec 0.1.4 §5.1: the Clues tool sits between Autofill and Theme.
const TOOL_IDS = ['edit', 'search', 'autofill', 'clues', 'theme', 'lists', 'import', 'export'];
const TOOL_LABELS = ['Grid', 'Search', 'Autofill', 'Clues', 'Theme', 'Lists', 'Import', 'Export'];

function baseProps(overrides = {}) {
  return {
    tool: 'edit',
    onSelectTool: vi.fn(),
    viewToggles: { symmetry: false },
    onToggleView: vi.fn(),
    stats: { total: 225, black: 36, blackPct: 16, fillPct: 42, words: 78 },
    ...overrides,
  };
}

describe('ToolRail (mounted, controlled)', () => {
  it('renders every tool and the Symmetry toggle', () => {
    const props = baseProps();
    const { getByText } = render(<ToolRail {...props} />);
    TOOL_LABELS.forEach((label) => {
      expect(getByText(label)).toBeInTheDocument();
    });
    expect(getByText('Symmetry')).toBeInTheDocument();
  });

  // novice-readiness spec 0.2.7 §3.1 (#50): the Heatmap toggle is still not rendered. The Clues
  // tool (#53) is, since clue-authoring spec 0.1.4 §5.1 and §6.2 "Rail".
  it('does not render the Heatmap toggle', () => {
    const props = baseProps();
    const { queryByText } = render(<ToolRail {...props} />);
    expect(queryByText('Heatmap')).toBeNull();
  });

  it('renders the Clues tool', () => {
    const props = baseProps();
    const { getByText } = render(<ToolRail {...props} />);
    expect(getByText('Clues')).toBeInTheDocument();
    expect(getByText('Clues').closest('button')).toHaveAttribute('title', 'Clues');
  });

  // §5.1: "between Autofill and Theme". The tool ids are not rendered, so the order is read by
  // clicking the tool buttons top to bottom and collecting the ids they select.
  it('lists the tools in order, with clues between autofill and theme', () => {
    const props = baseProps();
    const { container } = render(<ToolRail {...props} />);
    const buttons = Array.from(container.querySelectorAll('.xw-toolrail-top button'));
    buttons.forEach((b) => fireEvent.click(b));
    expect(props.onSelectTool.mock.calls.map((c) => c[0])).toEqual(TOOL_IDS);
    expect(props.onSelectTool.mock.calls.map((c) => c[0]).slice(2, 5)).toEqual([
      'autofill',
      'clues',
      'theme',
    ]);
  });

  it('the Clues tool draws an icon', () => {
    const props = baseProps();
    const { getByText } = render(<ToolRail {...props} />);
    const svg = getByText('Clues').closest('button').querySelector('svg');
    expect(svg.children.length).toBeGreaterThan(0);
  });

  it('ignores a heatmap key in viewToggles (still renders no Heatmap)', () => {
    const props = baseProps({ viewToggles: { symmetry: false, heatmap: true } });
    const { queryByText } = render(<ToolRail {...props} />);
    expect(queryByText('Heatmap')).toBeNull();
  });

  TOOL_IDS.forEach((id, i) => {
    it(`clicking ${TOOL_LABELS[i]} calls onSelectTool('${id}')`, () => {
      const props = baseProps();
      const { getByText } = render(<ToolRail {...props} />);
      fireEvent.click(getByText(TOOL_LABELS[i]));
      expect(props.onSelectTool).toHaveBeenCalledWith(id);
    });
  });

  it('the active tool has the "on" class', () => {
    const props = baseProps({ tool: 'theme' });
    const { getByText } = render(<ToolRail {...props} />);
    expect(getByText('Theme').closest('button')).toHaveClass('on');
    expect(getByText('Grid').closest('button')).not.toHaveClass('on');
  });

  it('clicking Symmetry calls onToggleView("symmetry")', () => {
    const props = baseProps();
    const { getByText } = render(<ToolRail {...props} />);
    fireEvent.click(getByText('Symmetry'));
    expect(props.onToggleView).toHaveBeenCalledWith('symmetry');
  });

  it('viewToggles.symmetry:true puts "on" on the Symmetry button', () => {
    const props = baseProps({ viewToggles: { symmetry: true } });
    const { getByText } = render(<ToolRail {...props} />);
    expect(getByText('Symmetry').closest('button')).toHaveClass('on');
  });

  it('renders the GRID stats block (total/black/blackPct/fillPct/words)', () => {
    const props = baseProps({ stats: { total: 225, black: 36, blackPct: 16, fillPct: 42, words: 78 } });
    const { container } = render(<ToolRail {...props} />);
    const rows = Array.from(container.querySelectorAll('.xw-rail-stat')).map((el) => el.textContent);
    expect(rows).toEqual(['Total225', 'Black36·16%', 'Filled42%', 'Words78']);
  });

  // --- VIOLATIONS section (Task 8D, F2) ---

  it('renders a .xw-rail-violation row per violation when violations are present', () => {
    const props = baseProps({ violations: ['2-letter word at R3C4', 'Isolated region'] });
    const { container, getByText } = render(<ToolRail {...props} />);
    expect(getByText('2-letter word at R3C4')).toBeInTheDocument();
    expect(getByText('Isolated region')).toBeInTheDocument();
    expect(container.querySelectorAll('.xw-rail-violation')).toHaveLength(2);
    // Label present, no "(unverified)" suffix when unverified is default (false).
    expect(getByText('VIOLATIONS')).toBeInTheDocument();
  });

  it('renders no VIOLATIONS section when violations is empty', () => {
    const props = baseProps({ violations: [] });
    const { container, queryByText } = render(<ToolRail {...props} />);
    expect(container.querySelector('.xw-rail-violation')).toBeNull();
    expect(queryByText(/VIOLATIONS/)).toBeNull();
  });

  it('appends the "(unverified)" suffix to the VIOLATIONS label when unverified is true', () => {
    const props = baseProps({ violations: ['2-letter word at R3C4'], unverified: true });
    const { getByText } = render(<ToolRail {...props} />);
    expect(getByText(/VIOLATIONS/)).toHaveTextContent('(unverified)');
  });
});
