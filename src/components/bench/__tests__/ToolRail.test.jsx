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

const TOOL_IDS = ['edit', 'search', 'autofill', 'clues', 'theme', 'lists', 'import', 'export'];
const TOOL_LABELS = ['Grid', 'Search', 'Autofill', 'Clues', 'Theme', 'Lists', 'Import', 'Export'];

function baseProps(overrides = {}) {
  return {
    tool: 'edit',
    onSelectTool: vi.fn(),
    viewToggles: { symmetry: false, heatmap: false },
    onToggleView: vi.fn(),
    stats: { total: 225, black: 36, blackPct: 16, fillPct: 42, words: 78 },
    ...overrides,
  };
}

describe('ToolRail (mounted, controlled)', () => {
  it('renders all 8 tools', () => {
    const props = baseProps();
    const { getByText } = render(<ToolRail {...props} />);
    TOOL_LABELS.forEach((label) => {
      expect(getByText(label)).toBeInTheDocument();
    });
  });

  it('clicking a tool calls onSelectTool with its id', () => {
    const props = baseProps();
    const { getByText } = render(<ToolRail {...props} />);
    fireEvent.click(getByText('Autofill'));
    expect(props.onSelectTool).toHaveBeenCalledWith('autofill');
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

  it('clicking Heatmap calls onToggleView("heatmap")', () => {
    const props = baseProps();
    const { getByText } = render(<ToolRail {...props} />);
    fireEvent.click(getByText('Heatmap'));
    expect(props.onToggleView).toHaveBeenCalledWith('heatmap');
  });

  it('viewToggles.symmetry:true puts "on" on the Symmetry button (Heatmap unaffected)', () => {
    const props = baseProps({ viewToggles: { symmetry: true, heatmap: false } });
    const { getByText } = render(<ToolRail {...props} />);
    expect(getByText('Symmetry').closest('button')).toHaveClass('on');
    expect(getByText('Heatmap').closest('button')).not.toHaveClass('on');
  });

  it('viewToggles.heatmap:true puts "on" on the Heatmap button', () => {
    const props = baseProps({ viewToggles: { symmetry: false, heatmap: true } });
    const { getByText } = render(<ToolRail {...props} />);
    expect(getByText('Heatmap').closest('button')).toHaveClass('on');
  });

  it('renders the GRID stats block (total/black/blackPct/fillPct/words)', () => {
    const props = baseProps({ stats: { total: 225, black: 36, blackPct: 16, fillPct: 42, words: 78 } });
    const { container } = render(<ToolRail {...props} />);
    const rows = Array.from(container.querySelectorAll('.xw-rail-stat')).map((el) => el.textContent);
    expect(rows).toEqual(['Total225', 'Black36·16%', 'Filled42%', 'Words78']);
  });
});
