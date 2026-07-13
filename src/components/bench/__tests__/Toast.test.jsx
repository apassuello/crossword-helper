/**
 * Tests for Toast (Task 6, U1b) — bespoke top-right toast surface.
 *
 * Establishes fake-timer coverage for a synchronous-state hook (contrast with
 * useHealth.test.jsx, which advances timers *async* to flush promise
 * microtasks). Here `pushToast` mutates state synchronously, so a plain
 * `act(() => { vi.advanceTimersByTime(...) })` is correct and sufficient —
 * no `advanceTimersByTimeAsync` needed.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, screen } from '@testing-library/react';
import { act } from '@testing-library/react';
import { ToastProvider, useToasts } from '../Toast';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

// Harness: a consumer that exposes buttons driving pushToast with fixed args,
// so tests can fireEvent.click instead of reaching into the hook directly.
function Harness() {
  const { pushToast } = useToasts();
  return (
    <div>
      <button onClick={() => pushToast({ kind: 'error', message: 'X' })}>push-error-x</button>
      <button onClick={() => pushToast({ kind: 'error', message: 'first' })}>push-first</button>
      <button onClick={() => pushToast({ kind: 'info', message: 'second' })}>push-second</button>
    </div>
  );
}

function renderHarness() {
  return render(
    <ToastProvider>
      <Harness />
    </ToastProvider>
  );
}

describe('ToastProvider / useToasts', () => {
  it('pushToast adds a toast with the message text to the document', () => {
    renderHarness();
    fireEvent.click(screen.getByText('push-error-x'));
    expect(screen.getByText('X')).toBeInTheDocument();
  });

  it('auto-dismisses a toast after 6000ms', () => {
    renderHarness();
    fireEvent.click(screen.getByText('push-error-x'));
    expect(screen.getByText('X')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(6000);
    });

    expect(screen.queryByText('X')).not.toBeInTheDocument();
  });

  it('stacks multiple toasts — both render simultaneously', () => {
    renderHarness();
    fireEvent.click(screen.getByText('push-first'));
    fireEvent.click(screen.getByText('push-second'));

    expect(screen.getByText('first')).toBeInTheDocument();
    expect(screen.getByText('second')).toBeInTheDocument();
  });

  it('maps kind to the expected class: error -> .xw-toast-error, info -> .xw-toast-info', () => {
    renderHarness();
    fireEvent.click(screen.getByText('push-first'));
    fireEvent.click(screen.getByText('push-second'));

    const errorToast = screen.getByText('first').closest('.xw-toast');
    const infoToast = screen.getByText('second').closest('.xw-toast');

    expect(errorToast).toHaveClass('xw-toast-error');
    expect(infoToast).toHaveClass('xw-toast-info');
  });

  it('an error toast is announced via role="alert" + aria-live="assertive"', () => {
    renderHarness();
    fireEvent.click(screen.getByText('push-first'));

    const errorToast = screen.getByRole('alert');
    expect(errorToast).toHaveTextContent('first');
    expect(errorToast).toHaveAttribute('aria-live', 'assertive');
  });

  it('an info toast is announced via role="status" + aria-live="polite"', () => {
    renderHarness();
    fireEvent.click(screen.getByText('push-second'));

    const infoToast = screen.getByRole('status');
    expect(infoToast).toHaveTextContent('second');
    expect(infoToast).toHaveAttribute('aria-live', 'polite');
  });

  it('manual dismiss (x) removes only the clicked toast', () => {
    renderHarness();
    fireEvent.click(screen.getByText('push-first'));
    fireEvent.click(screen.getByText('push-second'));

    const firstToast = screen.getByText('first').closest('.xw-toast');
    const dismissBtn = firstToast.querySelector('button');
    fireEvent.click(dismissBtn);

    expect(screen.queryByText('first')).not.toBeInTheDocument();
    expect(screen.getByText('second')).toBeInTheDocument();
  });

  it('unmounting with a pending toast clears its timer (no leak, no throw on later advance)', () => {
    const { unmount } = renderHarness();
    fireEvent.click(screen.getByText('push-error-x'));
    expect(screen.getByText('X')).toBeInTheDocument();
    expect(vi.getTimerCount()).toBe(1);

    unmount();

    // The real assertion: the pending auto-dismiss timer was cleared on
    // unmount, not left to fire against a dead component.
    expect(vi.getTimerCount()).toBe(0);

    expect(() => {
      act(() => {
        vi.advanceTimersByTime(6000);
      });
    }).not.toThrow();
  });

  it('useToasts() throws a clear error when used outside a ToastProvider', () => {
    // Swallow the expected React error-boundary console noise for this one assertion.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    function Bare() {
      useToasts();
      return null;
    }

    expect(() => render(<Bare />)).toThrow(/useToasts/);

    spy.mockRestore();
  });
});
