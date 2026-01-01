/**
 * Tests for PatternMatcher component
 *
 * PatternMatcher allows users to search for words matching a pattern (e.g., C?T).
 * It supports multiple wordlists, algorithms (regex/trie), and sorting options.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PatternMatcher from '../../components/PatternMatcher';
import { mockApiEndpoint, mockApiError } from '../fixtures/apiMocks';

// Mock useSSEProgress hook
vi.mock('../../hooks/useSSEProgress', () => ({
  useSSEProgress: () => ({
    status: 'idle',
    progress: 0,
    message: '',
    connect: vi.fn(),
    disconnect: vi.fn(),
  }),
}));

describe('PatternMatcher Component', () => {
  const defaultProps = {
    selectedCell: { row: 0, col: 0 },
    onSelectWord: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders pattern input field', () => {
      render(<PatternMatcher {...defaultProps} />);
      expect(screen.getByPlaceholderText(/enter pattern/i)).toBeInTheDocument();
    });

    it('renders search button', () => {
      render(<PatternMatcher {...defaultProps} />);
      expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument();
    });

    it('renders algorithm selector', () => {
      render(<PatternMatcher {...defaultProps} />);
      expect(screen.getByLabelText(/algorithm/i)).toBeInTheDocument();
    });

    it('loads wordlists on mount', async () => {
      render(<PatternMatcher {...defaultProps} />);

      await waitFor(() => {
        // Wordlists loaded from API
        expect(screen.getByText(/comprehensive/i)).toBeInTheDocument();
      });
    });
  });

  describe('Pattern Input', () => {
    it('allows typing in pattern field', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      expect(input).toHaveValue('C?T');
    });

    it('shows error for patterns < 3 characters', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText(/at least 3 characters/i)).toBeInTheDocument();
      });
    });
  });

  describe('Search Functionality', () => {
    it('performs search and displays results', async () => {
      const user = userEvent.setup();

      // Mock search response
      mockApiEndpoint('post', '/pattern', {
        results: [
          { word: 'CAT', score: 95, source: 'comprehensive' },
          { word: 'COT', score: 92, source: 'comprehensive' },
        ],
        meta: { total: 2, pattern: 'C?T' },
      });

      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText('CAT')).toBeInTheDocument();
        expect(screen.getByText('COT')).toBeInTheDocument();
      });
    });

    it('converts pattern to uppercase', async () => {
      const user = userEvent.setup();
      const mockPost = vi.fn(() => Promise.resolve({
        data: { results: [], meta: {} }
      }));

      vi.spyOn(require('axios'), 'default', 'get').mockReturnValue({
        post: mockPost,
      });

      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'c?t'); // lowercase

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        expect(mockPost).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({ pattern: 'C?T' }) // Uppercase
        );
      });
    });

    it('handles search errors gracefully', async () => {
      const user = userEvent.setup();

      // Mock error response
      mockApiError('post', '/pattern/with-progress', 500, 'Search failed');

      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText(/search failed/i)).toBeInTheDocument();
      });
    });
  });

  describe('Sorting and Filtering', () => {
    const mockResults = [
      { word: 'CAT', score: 95, source: 'comprehensive' },
      { word: 'BAT', score: 92, source: 'comprehensive' },
      { word: 'CART', score: 88, source: 'comprehensive' },
    ];

    beforeEach(() => {
      mockApiEndpoint('post', '/pattern', {
        results: mockResults,
        meta: { total: 3, pattern: 'C?T' },
      });
    });

    it('sorts results by score (default)', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        const results = screen.getAllByRole('listitem');
        expect(results[0]).toHaveTextContent('CAT'); // Highest score first
      });
    });

    it('sorts results alphabetically', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      // Change sort to alphabetical
      const sortSelect = screen.getByLabelText(/sort by/i);
      await user.selectOptions(sortSelect, 'alpha');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        const results = screen.getAllByRole('listitem');
        expect(results[0]).toHaveTextContent('BAT'); // Alphabetically first
      });
    });

    it('filters results by minimum score', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      // Set minimum score filter
      const filterInput = screen.getByLabelText(/minimum score/i);
      await user.clear(filterInput);
      await user.type(filterInput, '90');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText('CAT')).toBeInTheDocument(); // Score 95
        expect(screen.getByText('BAT')).toBeInTheDocument(); // Score 92
        expect(screen.queryByText('CART')).not.toBeInTheDocument(); // Score 88 - filtered out
      });
    });
  });

  describe('Wordlist Selection', () => {
    it('allows selecting multiple wordlists', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByLabelText(/comprehensive/i)).toBeInTheDocument();
      });

      const wordlistCheckbox = screen.getByLabelText(/comprehensive/i);
      expect(wordlistCheckbox).toBeChecked(); // Default

      // Uncheck comprehensive
      await user.click(wordlistCheckbox);
      expect(wordlistCheckbox).not.toBeChecked();
    });
  });

  describe('Algorithm Selection', () => {
    it('defaults to regex algorithm', () => {
      render(<PatternMatcher {...defaultProps} />);
      const algorithmSelect = screen.getByLabelText(/algorithm/i);
      expect(algorithmSelect).toHaveValue('regex');
    });

    it('allows switching to trie algorithm', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const algorithmSelect = screen.getByLabelText(/algorithm/i);
      await user.selectOptions(algorithmSelect, 'trie');

      expect(algorithmSelect).toHaveValue('trie');
    });
  });

  describe('Word Selection', () => {
    it('calls onSelectWord when word is clicked', async () => {
      const user = userEvent.setup();
      const onSelectWord = vi.fn();

      mockApiEndpoint('post', '/pattern', {
        results: [{ word: 'CAT', score: 95, source: 'comprehensive' }],
        meta: { total: 1, pattern: 'C?T' },
      });

      render(<PatternMatcher {...defaultProps} onSelectWord={onSelectWord} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText('CAT')).toBeInTheDocument();
      });

      const wordButton = screen.getByText('CAT');
      await user.click(wordButton);

      expect(onSelectWord).toHaveBeenCalledWith('CAT');
    });
  });

  describe('Loading States', () => {
    it('shows loading indicator during search', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      // Check for loading state (may be spinner, text, or disabled button)
      expect(searchButton).toBeDisabled();
    });

    it('clears previous results before new search', async () => {
      const user = userEvent.setup();

      // First search
      mockApiEndpoint('post', '/pattern', {
        results: [{ word: 'CAT', score: 95 }],
        meta: {},
      });

      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText('CAT')).toBeInTheDocument();
      });

      // Second search
      mockApiEndpoint('post', '/pattern', {
        results: [{ word: 'DOG', score: 90 }],
        meta: {},
      });

      await user.clear(input);
      await user.type(input, 'D?G');
      await user.click(searchButton);

      await waitFor(() => {
        expect(screen.queryByText('CAT')).not.toBeInTheDocument(); // Old result cleared
        expect(screen.getByText('DOG')).toBeInTheDocument(); // New result shown
      });
    });
  });
});
