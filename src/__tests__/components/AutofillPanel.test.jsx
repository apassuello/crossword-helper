/**
 * Tests for AutofillPanel - the core autofill UI component
 * Tests algorithm selection, start button, adaptive mode, pause button
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AutofillPanel from '../../components/AutofillPanel';
import { emptyGrid15x15 } from '../fixtures/gridFixtures';

// Mock react-hot-toast to avoid side effects
vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  }),
}));

// Mock ProgressIndicator to simplify DOM
vi.mock('../../components/ProgressIndicator', () => ({
  default: ({ message }) => <div data-testid="progress-indicator">{message}</div>,
}));

// Mock BlackSquareSuggestions
vi.mock('../../components/BlackSquareSuggestions', () => ({
  default: () => <div data-testid="black-square-suggestions" />,
}));

describe('AutofillPanel Component', () => {
  const defaultProps = {
    onStartAutofill: vi.fn(),
    onCancelAutofill: vi.fn(),
    onResetAutofill: vi.fn(),
    progress: null,
    grid: emptyGrid15x15,
    currentTaskId: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders algorithm radio buttons', () => {
    render(<AutofillPanel {...defaultProps} />);
    // The component uses radio buttons for algorithm selection
    expect(screen.getByText('Algorithm')).toBeInTheDocument();
    // Check that radio inputs for each algorithm exist
    const radioButtons = document.querySelectorAll('input[type="radio"][name="algorithm"]');
    expect(radioButtons.length).toBe(4); // repair, beam, trie, regex
    // Check repair is selected by default
    const repairRadio = document.querySelector('input[type="radio"][value="repair"]');
    expect(repairRadio.checked).toBe(true);
  });

  it('renders start autofill button', () => {
    render(<AutofillPanel {...defaultProps} />);
    expect(screen.getByRole('button', { name: /start autofill/i })).toBeInTheDocument();
  });

  it('calls onStartAutofill when start button is clicked', async () => {
    const user = userEvent.setup();
    const onStartAutofill = vi.fn();

    render(<AutofillPanel {...defaultProps} onStartAutofill={onStartAutofill} />);

    const startButton = screen.getByRole('button', { name: /start autofill/i });
    await user.click(startButton);

    expect(onStartAutofill).toHaveBeenCalledWith(
      expect.objectContaining({
        algorithm: 'repair', // default algorithm
      })
    );
  });

  it('shows adaptive mode toggle', () => {
    render(<AutofillPanel {...defaultProps} />);
    expect(screen.getByLabelText(/adaptive mode/i)).toBeInTheDocument();
  });

  it('shows pause button when progress status is running', () => {
    render(
      <AutofillPanel
        {...defaultProps}
        progress={{ status: 'running', progress: 50, message: 'Filling...' }}
        currentTaskId="test-123"
      />
    );

    expect(screen.getByRole('button', { name: /pause/i })).toBeInTheDocument();
  });
});
