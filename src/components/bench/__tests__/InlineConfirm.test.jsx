// novice-readiness spec 0.2.7 §3.2 (#55): the in-panel confirm, never window.confirm.
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InlineConfirm from '../InlineConfirm';

const setup = (over = {}) => {
  const onConfirm = vi.fn();
  const onCancel = vi.fn();
  render(
    <InlineConfirm
      message="Replace it?"
      confirmLabel="Replace"
      onConfirm={onConfirm}
      onCancel={onCancel}
      {...over}
    />
  );
  return { onConfirm, onCancel };
};

describe('InlineConfirm', () => {
  it('is a group showing the message and exactly two buttons', () => {
    setup();
    const group = screen.getByRole('group');
    expect(group).toHaveTextContent('Replace it?');
    expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual([
      'Replace',
      'Cancel',
    ]);
  });

  it('confirm calls onConfirm once and not onCancel', async () => {
    const { onConfirm, onCancel } = setup();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Replace' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('cancel calls onCancel once and not onConfirm', async () => {
    const { onConfirm, onCancel } = setup();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('honours a custom cancelLabel', () => {
    setup({ cancelLabel: 'Keep it' });
    expect(screen.getByRole('button', { name: 'Keep it' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull();
  });

  it('never opens a browser dialog', async () => {
    const spy = vi.spyOn(window, 'confirm');
    setup();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Replace' }));
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});
