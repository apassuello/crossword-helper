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

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
  }),
}));

describe('ThemeWordsPanel Component', () => {
  const defaultProps = {
    grid: emptyGrid15x15,
    gridSize: 15,
    onApplyPlacement: vi.fn(),
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders file upload button', () => {
    render(<ThemeWordsPanel {...defaultProps} />);
    expect(screen.getByRole('button', { name: /choose file/i })).toBeInTheDocument();
  });

  it('validates uploaded theme words', async () => {
    const user = userEvent.setup();

    // Mock the upload endpoint to return valid words with required validation field
    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY', 'CELEBRATION'],
      count: 2,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
      },
    });

    // Mock suggest-placements to return empty (auto-called after upload)
    mockApiEndpoint('post', '/theme/suggest-placements', {
      suggestions: [],
    });

    render(<ThemeWordsPanel {...defaultProps} />);

    const file = new File(['BIRTHDAY\nCELEBRATION'], 'theme.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]');

    await user.upload(input, file);

    await waitFor(() => {
      expect(screen.getByText('BIRTHDAY')).toBeInTheDocument();
      expect(screen.getByText('CELEBRATION')).toBeInTheDocument();
    });
  });

  it('shows placement suggestions after upload', async () => {
    const user = userEvent.setup();

    // Mock upload endpoint
    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY'],
      count: 1,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
      },
    });

    // Mock suggest-placements to return suggestions
    mockApiEndpoint('post', '/theme/suggest-placements', {
      suggestions: [
        {
          word: 'BIRTHDAY',
          length: 8,
          suggestions: [
            {
              word: 'BIRTHDAY',
              row: 0,
              col: 0,
              direction: 'across',
              score: 90,
              reasoning: 'Good placement',
            },
          ],
        },
      ],
    });

    render(<ThemeWordsPanel {...defaultProps} />);

    const file = new File(['BIRTHDAY'], 'theme.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]');
    await user.upload(input, file);

    await waitFor(() => {
      // Placement Suggestions section appears
      expect(screen.getByText('Placement Suggestions')).toBeInTheDocument();
    });
  });

  it('shows apply button for each placement suggestion', async () => {
    const user = userEvent.setup();

    mockApiEndpoint('post', '/theme/upload', {
      words: ['BIRTHDAY'],
      count: 1,
      validation: {
        valid: true,
        errors: [],
        warnings: [],
      },
    });

    mockApiEndpoint('post', '/theme/suggest-placements', {
      suggestions: [
        {
          word: 'BIRTHDAY',
          length: 8,
          suggestions: [
            {
              word: 'BIRTHDAY',
              row: 0,
              col: 0,
              direction: 'across',
              score: 90,
              reasoning: 'Good placement',
            },
          ],
        },
      ],
    });

    render(<ThemeWordsPanel {...defaultProps} />);

    const file = new File(['BIRTHDAY'], 'theme.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]');
    await user.upload(input, file);

    await waitFor(() => {
      // There may be multiple apply buttons (one per suggestion)
      const applyButtons = screen.getAllByRole('button', { name: /apply this placement/i });
      expect(applyButtons.length).toBeGreaterThan(0);
    });
  });
});
