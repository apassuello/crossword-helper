/**
 * Tests for ThemeWordsPanel - theme word management
 * Tests file upload, placement suggestions, conflict detection, apply placements
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ThemeWordsPanel from '../../components/ThemeWordsPanel';
import { emptyGrid15x15 } from '../fixtures/gridFixtures';
import { mockApiEndpoint } from '../fixtures/apiMocks';

describe('ThemeWordsPanel Component', () => {
  const defaultProps = {
    grid: emptyGrid15x15,
    onGridUpdate: vi.fn(),
    size: 15,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders file upload input', () => {
    render(<ThemeWordsPanel {...defaultProps} />);
    expect(screen.getByLabelText(/upload theme words/i)).toBeInTheDocument();
  });

  it('validates uploaded theme words', async () => {
    const user = userEvent.setup();

    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY', 'CELEBRATION'],
      valid_count: 2,
      invalid_words: [],
    });

    render(<ThemeWordsPanel {...defaultProps} />);

    const file = new File(['BIRTHDAY\nCELEBRATION'], 'theme.txt', { type: 'text/plain' });
    const input = screen.getByLabelText(/upload theme words/i);

    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByText('BIRTHDAY')).toBeInTheDocument();
      expect(screen.getByText('CELEBRATION')).toBeInTheDocument();
    });
  });

  it('shows placement suggestions', async () => {
    const user = userEvent.setup();

    mockApiEndpoint('post', '/theme/suggest-placements', {
      placements: [{
        word: 'BIRTHDAY',
        row: 0,
        col: 0,
        direction: 'across',
        score: 90,
        conflicts: [],
      }],
    });

    render(<ThemeWordsPanel {...defaultProps} />);

    // Simulate theme word upload first
    const file = new File(['BIRTHDAY'], 'theme.txt');
    await user.upload(screen.getByLabelText(/upload/i), file);

    await waitFor(() => {
      expect(screen.getByText(/suggest placements/i)).toBeInTheDocument();
    });

    const suggestButton = screen.getByRole('button', { name: /suggest placements/i });
    await user.click(suggestButton);

    await waitFor(() => {
      expect(screen.getByText(/across at \(0, 0\)/i)).toBeInTheDocument();
    });
  });

  it('applies theme word placement', async () => {
    const user = userEvent.setup();
    const onGridUpdate = vi.fn();

    mockApiEndpoint('post', '/theme/apply-placement', {
      success: true,
      grid: emptyGrid15x15,
      word: 'BIRTHDAY',
      locked_cells: 8,
    });

    render(<ThemeWordsPanel {...defaultProps} onGridUpdate={onGridUpdate} />);

    // Simulate applying a placement
    const applyButton = screen.getByRole('button', { name: /apply/i });
    await user.click(applyButton);

    await waitFor(() => {
      expect(onGridUpdate).toHaveBeenCalled();
    });
  });
});
