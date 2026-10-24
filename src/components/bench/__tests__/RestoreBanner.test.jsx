/**
 * novice-readiness spec 0.2.7 §3.4 (PD-6-G2, PD-6-G9): the restore banner. Presentational:
 * App decides when it shows and what "Start blank" does.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import RestoreBanner from '../RestoreBanner';

// Built from a local Date so the expected stamp does not depend on the timezone.
const SAVED_AT = new Date(2026, 9, 22, 9, 30).toISOString();

const renderBanner = (over = {}) => {
  const props = { name: 'Mine', savedAt: SAVED_AT, onStartBlank: vi.fn(), onDismiss: vi.fn(), ...over };
  render(<RestoreBanner {...props} />);
  return props;
};

describe('RestoreBanner', () => {
  it('reads Restored "<name>" (saved <local stamp>)', () => {
    renderBanner();
    expect(screen.getByText('Restored "Mine" (saved 2026-10-22 09:30)')).toBeInTheDocument();
  });

  it('shows the name it is given, quotes included', () => {
    renderBanner({ name: '15×15 2026-10-01 08:05' });
    expect(screen.getByText(/^Restored "15×15 2026-10-01 08:05" \(saved /)).toBeInTheDocument();
  });

  it('Start blank calls onStartBlank only', async () => {
    const props = renderBanner();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Start blank' }));
    expect(props.onStartBlank).toHaveBeenCalledTimes(1);
    expect(props.onDismiss).not.toHaveBeenCalled();
  });

  it('the dismiss button is labelled Dismiss, shows U+00D7, and calls onDismiss only', async () => {
    const props = renderBanner();
    const btn = screen.getByRole('button', { name: 'Dismiss' });
    expect(btn.textContent).toBe('×');
    await userEvent.setup().click(btn);
    expect(props.onDismiss).toHaveBeenCalledTimes(1);
    expect(props.onStartBlank).not.toHaveBeenCalled();
  });
});
