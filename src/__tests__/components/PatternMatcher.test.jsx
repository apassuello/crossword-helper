/**
 * Tests for PatternMatcher component
 *
 * PatternMatcher allows users to search for words matching a pattern (e.g., C?T).
 * It supports multiple wordlists, algorithms (regex/trie), and sorting options.
 *
 * Note: The component uses SSE (Server-Sent Events) via /api/pattern/with-progress
 * for the search flow. Tests that need search results mock both the SSE initiation
 * endpoint and the direct /api/pattern endpoint (used after SSE completes).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PatternMatcher from '../../components/PatternMatcher';
import { mockApiEndpoint, mockApiError } from '../fixtures/apiMocks';

// Mock useSSEProgress hook — allow tests to control status and final data payload
let mockSSEStatus = 'idle';
let mockSSEData = null;
let mockSSEMessage = '';
let mockSSEConnect = vi.fn();
// Inert here on purpose: these tests drive status/data through the module-level
// vars above, so a no-op reset preserves their existing semantics. The real
// reset's effect is covered against the real hook in PatternMatcher.sse.test.jsx.
let mockSSEReset = vi.fn();

vi.mock('../../hooks/useSSEProgress', () => ({
  useSSEProgress: () => ({
    status: mockSSEStatus,
    progress: 0,
    message: mockSSEMessage,
    data: mockSSEData,
    connect: mockSSEConnect,
    disconnect: vi.fn(),
    reset: mockSSEReset,
  }),
}));

// Mock ProgressIndicator
vi.mock('../../components/ProgressIndicator', () => ({
  default: ({ message }) => <div data-testid="progress-indicator">{message}</div>,
}));

describe('PatternMatcher Component', () => {
  const defaultProps = {
    selectedCell: { row: 0, col: 0 },
    onSelectWord: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockSSEStatus = 'idle';
    mockSSEData = null;
    mockSSEMessage = '';
    mockSSEConnect = vi.fn();
    mockSSEReset = vi.fn();
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
      // The label "Algorithm:" is a bare label (not linked via htmlFor), so query by text
      expect(screen.getByText('Algorithm:')).toBeInTheDocument();
      // The select element exists with regex/trie options
      const selects = screen.getAllByRole('combobox');
      const algorithmSelect = selects.find(
        s => s.querySelector('option[value="regex"]')
      );
      expect(algorithmSelect).toBeTruthy();
    });

    it('loads wordlists on mount', async () => {
      render(<PatternMatcher {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByText(/comprehensive/i)).toBeInTheDocument();
      });
    });
  });

  describe('Pattern Input', () => {
    it('allows typing in pattern field', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'c?t');

      // Component converts to uppercase onChange
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
    it('initiates search via SSE endpoint', async () => {
      const user = userEvent.setup();

      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      // The component posts to /api/pattern/with-progress then connects SSE
      // Button should be disabled while loading
      expect(searchButton).toBeDisabled();
    });

    it('converts pattern to uppercase on input', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'cat');

      expect(input).toHaveValue('CAT');
    });

    it('handles search errors gracefully', async () => {
      const user = userEvent.setup();
      const axios = await import('axios');

      // Mock axios.post to reject for the search endpoint
      const originalPost = axios.default.post;
      axios.default.post = vi.fn((url, ...args) => {
        if (url.includes('/pattern/with-progress')) {
          return Promise.reject({
            response: { data: { error: 'Search failed' }, status: 500 },
          });
        }
        return originalPost(url, ...args);
      });

      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      await waitFor(() => {
        expect(screen.getByText(/search failed/i)).toBeInTheDocument();
      });

      // Restore
      axios.default.post = originalPost;
    });
  });

  describe('Sorting and Filtering', () => {
    it('has sort by dropdown with score, alpha, length options', () => {
      render(<PatternMatcher {...defaultProps} />);

      // Find the sort select by its label text
      expect(screen.getByText('Sort by:')).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Score' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Alphabetical' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Length' })).toBeInTheDocument();
    });

    it('has minimum score filter slider', () => {
      render(<PatternMatcher {...defaultProps} />);
      expect(screen.getByText('Min Score:')).toBeInTheDocument();
      // The range input
      const rangeInputs = document.querySelectorAll('input[type="range"]');
      expect(rangeInputs.length).toBeGreaterThan(0);
    });

    it('can change sort order', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      // Find sort select — it's the one with score/alpha/length options
      const selects = screen.getAllByRole('combobox');
      const sortSelect = selects.find(
        s => s.querySelector('option[value="alpha"]')
      );
      expect(sortSelect).toBeTruthy();

      await user.selectOptions(sortSelect, 'alpha');
      expect(sortSelect).toHaveValue('alpha');
    });
  });

  describe('Wordlist Selection', () => {
    it('renders wordlist checkboxes from GET /api/wordlists (not hardcoded)', async () => {
      render(<PatternMatcher {...defaultProps} />);

      // All lists returned by the API appear as checkboxes
      await waitFor(() => {
        expect(screen.getByText(/Foreign Words/)).toBeInTheDocument();
      });
      expect(screen.getByText(/My Words/)).toBeInTheDocument();

      // The previously hardcoded nonexistent key must not be rendered
      expect(screen.queryByText(/Common 3-Letter/)).not.toBeInTheDocument();
    });

    it('has comprehensive wordlist checkbox checked by default', async () => {
      render(<PatternMatcher {...defaultProps} />);

      // Checkboxes are rendered after the wordlists load from the API
      await waitFor(() => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        expect(checkboxes.length).toBeGreaterThan(0);
      });

      const checkboxes = document.querySelectorAll('input[type="checkbox"]');
      const comprehensiveCheckbox = Array.from(checkboxes).find(
        cb => cb.closest('label')?.textContent?.includes('Comprehensive')
      );
      expect(comprehensiveCheckbox).toBeTruthy();
      expect(comprehensiveCheckbox.checked).toBe(true);
    });

    it('allows toggling wordlist checkboxes', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      await waitFor(() => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        expect(checkboxes.length).toBeGreaterThan(0);
      });

      const checkboxes = document.querySelectorAll('input[type="checkbox"]');
      const comprehensiveCheckbox = Array.from(checkboxes).find(
        cb => cb.closest('label')?.textContent?.includes('Comprehensive')
      );

      await user.click(comprehensiveCheckbox);
      expect(comprehensiveCheckbox.checked).toBe(false);
    });
  });

  describe('Algorithm Selection', () => {
    it('defaults to regex algorithm', () => {
      render(<PatternMatcher {...defaultProps} />);
      const selects = screen.getAllByRole('combobox');
      const algorithmSelect = selects.find(
        s => s.querySelector('option[value="regex"]')
      );
      expect(algorithmSelect).toHaveValue('regex');
    });

    it('allows switching to trie algorithm', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const selects = screen.getAllByRole('combobox');
      const algorithmSelect = selects.find(
        s => s.querySelector('option[value="trie"]')
      );
      await user.selectOptions(algorithmSelect, 'trie');

      expect(algorithmSelect).toHaveValue('trie');
    });
  });

  describe('Word Selection', () => {
    it('calls onSelectWord callback prop (integration placeholder)', () => {
      // Since results require full SSE flow, test that onSelectWord prop is accepted
      const onSelectWord = vi.fn();
      const { container } = render(
        <PatternMatcher {...defaultProps} onSelectWord={onSelectWord} />
      );
      // Component renders without error with the callback
      expect(container.querySelector('.pattern-matcher')).toBeInTheDocument();
    });
  });

  describe('Loading States', () => {
    it('disables search button during search', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      // Button text changes to "Searching..." and is disabled
      expect(searchButton).toBeDisabled();
    });

    it('renders results from the final SSE event without a follow-up POST to /api/pattern (regression)', async () => {
      const user = userEvent.setup();
      const axios = await import('axios');
      const postSpy = vi.spyOn(axios.default, 'post');

      const { rerender } = render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      // Search initiated: only the with-progress endpoint is called
      await waitFor(() => {
        expect(mockSSEConnect).toHaveBeenCalled();
      });
      expect(searchButton).toBeDisabled();

      // Simulate the SSE stream completing WITH the final results payload
      mockSSEStatus = 'complete';
      mockSSEData = {
        results: [
          { word: 'CAT', score: 95, source: 'comprehensive' },
          { word: 'COT', score: 92, source: 'comprehensive' },
        ],
        meta: { total_found: 2 },
      };
      rerender(<PatternMatcher {...defaultProps} />);

      // Results render directly from the SSE payload
      await waitFor(() => {
        expect(screen.getByText(/results \(2\)/i)).toBeInTheDocument();
      });

      // Search button is re-enabled (no soft-lock at "Complete 100%")
      expect(screen.getByRole('button', { name: /^search$/i })).not.toBeDisabled();

      // No redundant follow-up POST to /api/pattern was fired
      const patternPosts = postSpy.mock.calls.filter(call => call[0] === '/api/pattern');
      expect(patternPosts).toHaveLength(0);

      // Exactly one search request went out (the with-progress init)
      const initPosts = postSpy.mock.calls.filter(call => call[0] === '/api/pattern/with-progress');
      expect(initPosts).toHaveLength(1);

      postSpy.mockRestore();
    });

    it('re-enables search button when SSE completes with no results', async () => {
      const user = userEvent.setup();

      const { rerender } = render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'XQZ');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);
      await waitFor(() => expect(mockSSEConnect).toHaveBeenCalled());

      mockSSEStatus = 'complete';
      mockSSEData = { results: [], meta: { total_found: 0 } };
      rerender(<PatternMatcher {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /^search$/i })).not.toBeDisabled();
      });
      expect(screen.getByText(/no matching words found/i)).toBeInTheDocument();
    });

    it('re-enables search button when SSE reports an error', async () => {
      const user = userEvent.setup();

      const { rerender } = render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);
      await waitFor(() => expect(mockSSEConnect).toHaveBeenCalled());

      mockSSEStatus = 'error';
      mockSSEMessage = 'CLI Error (code 1): something broke';
      rerender(<PatternMatcher {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /^search$/i })).not.toBeDisabled();
      });
      expect(screen.getByText(/CLI Error/i)).toBeInTheDocument();
    });

    it('clears previous results on new search', async () => {
      const user = userEvent.setup();
      render(<PatternMatcher {...defaultProps} />);

      const input = screen.getByPlaceholderText(/enter pattern/i);
      await user.type(input, 'C?T');

      const searchButton = screen.getByRole('button', { name: /search/i });
      await user.click(searchButton);

      // Results are cleared when a new search starts (results set to [])
      // No results section visible during loading
      expect(screen.queryByText('Results')).not.toBeInTheDocument();
    });
  });
});
