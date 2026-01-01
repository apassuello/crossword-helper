/**
 * Tests for AutofillPanel - the core autofill UI component
 * Tests algorithm selection, SSE progress, pause/resume, adaptive mode
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AutofillPanel from '../../components/AutofillPanel';
import { emptyGrid15x15 } from '../fixtures/gridFixtures';
import { mockApiEndpoint } from '../fixtures/apiMocks';

vi.mock('../../hooks/useSSEProgress', () => ({
  useSSEProgress: () => ({
    status: 'idle',
    progress: 0,
    message: '',
    data: null,
    connect: vi.fn(),
    disconnect: vi.fn(),
  }),
}));

describe('AutofillPanel Component', () => {
  const defaultProps = {
    grid: emptyGrid15x15,
    onGridUpdate: vi.fn(),
    size: 15,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders algorithm selector', () => {
    render(<AutofillPanel {...defaultProps} />);
    expect(screen.getByLabelText(/algorithm/i)).toBeInTheDocument();
  });

  it('renders start autofill button', () => {
    render(<AutofillPanel {...defaultProps} />);
    expect(screen.getByRole('button', { name: /start autofill/i })).toBeInTheDocument();
  });

  it('starts autofill with selected parameters', async () => {
    const user = userEvent.setup();
    let capturedRequest;

    mockApiEndpoint('post', '/fill/with-progress', (req) => {
      capturedRequest = req.body;
      return {
        task_id: 'test-123',
        progress_url: '/api/progress/test-123',
      };
    });

    render(<AutofillPanel {...defaultProps} />);

    const startButton = screen.getByRole('button', { name: /start autofill/i });
    await user.click(startButton);

    await waitFor(() => {
      expect(capturedRequest).toBeDefined();
      expect(capturedRequest.algorithm).toBe('beam');
      expect(capturedRequest.size).toBe(15);
    });
  });

  it('shows adaptive mode toggle', () => {
    render(<AutofillPanel {...defaultProps} />);
    expect(screen.getByLabelText(/adaptive mode/i)).toBeInTheDocument();
  });

  it('enables pause button during autofill', async () => {
    const user = userEvent.setup();
    render(<AutofillPanel {...defaultProps} />);

    const startButton = screen.getByRole('button', { name: /start autofill/i });
    await user.click(startButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /pause/i })).toBeEnabled();
    });
  });
});
