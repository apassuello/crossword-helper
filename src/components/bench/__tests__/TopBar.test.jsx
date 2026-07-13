/**
 * Tests for TopBar (Task 6, U2) — the ported Constructor's Bench top bar.
 *
 * Fully controlled: no internal state. `status` here is the `{online, degraded}`
 * verdict shape produced by `useHealth` (wired by a later unit, U3) — TopBar derives
 * the health-dot kind/label and the Verify-disabled state from it.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { TopBar } from '../TopBar';

function baseProps(overrides = {}) {
  return {
    status: { online: true, degraded: false },
    savedLabel: 'saved locally · 2m ago',
    onVerify: vi.fn(),
    onSave: vi.fn(),
    onClean: vi.fn(),
    onToggleTheme: vi.fn(),
    dark: false,
    ...overrides,
  };
}

describe('TopBar (mounted, controlled)', () => {
  it('renders the savedLabel text verbatim', () => {
    const props = baseProps({ savedLabel: 'saved locally · 2m ago' });
    const { getByText } = render(<TopBar {...props} />);
    expect(getByText('saved locally · 2m ago')).toBeInTheDocument();
  });

  it('clicking Verify calls onVerify when online', () => {
    const props = baseProps({ status: { online: true, degraded: false } });
    const { getByText } = render(<TopBar {...props} />);
    fireEvent.click(getByText('Verify words'));
    expect(props.onVerify).toHaveBeenCalledTimes(1);
  });

  it('clicking Save calls onSave', () => {
    const props = baseProps();
    const { getByText } = render(<TopBar {...props} />);
    fireEvent.click(getByText('Save grid'));
    expect(props.onSave).toHaveBeenCalledTimes(1);
  });

  it('clicking the theme toggle calls onToggleTheme', () => {
    const props = baseProps();
    const { getByTitle } = render(<TopBar {...props} />);
    fireEvent.click(getByTitle('Toggle theme'));
    expect(props.onToggleTheme).toHaveBeenCalledTimes(1);
  });

  it('shows the dark-mode icon when dark is true and the light-mode icon when false', () => {
    const { getByTitle, rerender } = render(<TopBar {...baseProps({ dark: false })} />);
    expect(getByTitle('Toggle theme').textContent).toBe('◑');
    rerender(<TopBar {...baseProps({ dark: true })} />);
    expect(getByTitle('Toggle theme').textContent).toBe('◐');
  });

  it('health dot reflects offline status (error kind)', () => {
    const props = baseProps({ status: { online: false, degraded: false } });
    const { container, getByText } = render(<TopBar {...props} />);
    expect(container.querySelector('.xw-status[data-kind="err"]')).not.toBeNull();
    expect(getByText('offline')).toBeInTheDocument();
  });

  it('health dot reflects degraded status (warn kind)', () => {
    const props = baseProps({ status: { online: true, degraded: true } });
    const { container, getByText } = render(<TopBar {...props} />);
    expect(container.querySelector('.xw-status[data-kind="warn"]')).not.toBeNull();
    expect(getByText('degraded')).toBeInTheDocument();
  });

  it('health dot reflects online, non-degraded status (ok kind)', () => {
    const props = baseProps({ status: { online: true, degraded: false } });
    const { container, getByText } = render(<TopBar {...props} />);
    expect(container.querySelector('.xw-status[data-kind="ok"]')).not.toBeNull();
    expect(getByText('online')).toBeInTheDocument();
  });

  it('Verify is disabled when status.online is false, with a tooltip explaining why', () => {
    const props = baseProps({ status: { online: false, degraded: false } });
    const { getByText } = render(<TopBar {...props} />);
    const btn = getByText('Verify words').closest('button');
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('title', 'Backend offline');
  });

  it('Verify is enabled when status.online is true', () => {
    const props = baseProps({ status: { online: true, degraded: false } });
    const { getByText } = render(<TopBar {...props} />);
    const btn = getByText('Verify words').closest('button');
    expect(btn).not.toBeDisabled();
  });

  it('Save is NOT disabled when offline', () => {
    const props = baseProps({ status: { online: false, degraded: false } });
    const { getByText } = render(<TopBar {...props} />);
    const btn = getByText('Save grid').closest('button');
    expect(btn).not.toBeDisabled();
  });

  it('clicking Clean calls onClean when online', () => {
    const props = baseProps({ status: { online: true, degraded: false } });
    const { getByText } = render(<TopBar {...props} />);
    fireEvent.click(getByText('Clean grid'));
    expect(props.onClean).toHaveBeenCalledTimes(1);
  });

  it('Clean is disabled when status.online is false, with a tooltip explaining why', () => {
    const props = baseProps({ status: { online: false, degraded: false } });
    const { getByText } = render(<TopBar {...props} />);
    const btn = getByText('Clean grid').closest('button');
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('title', 'Backend offline');
  });

  it('Clean is enabled when status.online is true', () => {
    const props = baseProps({ status: { online: true, degraded: false } });
    const { getByText } = render(<TopBar {...props} />);
    const btn = getByText('Clean grid').closest('button');
    expect(btn).not.toBeDisabled();
  });
});
