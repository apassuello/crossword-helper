/**
 * PatternMatcher — SSE completion against the REAL useSSEProgress hook.
 *
 * The sibling file (PatternMatcher.test.jsx) mocks useSSEProgress wholesale with
 * a fixed status/data pair. That mock cannot express the ordering between
 * `setLoading(true)` and the hook's own reset, so the completion race in issue
 * #11 is invisible to it — a green suite coexisted with every search after the
 * first rendering the previous search's results.
 *
 * These tests therefore mock nothing but the transport: MSW answers the POST
 * (via the shared handler in fixtures/apiMocks.js) and the global
 * MockEventSource from setupTests.js stands in for the SSE stream. The
 * component and the hook are the real ones, so this stays a valid guard when
 * the hook is ported onto src/api/client.js (issue #12).
 */

import { describe, it, expect } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PatternMatcher from '../../components/PatternMatcher';

const sources = () => global.EventSource.instances;

/**
 * Words currently in the results list. Read from the DOM rather than via
 * getByText: renderLetterQuality splits every word into one span per letter, so
 * the default text matcher (direct text nodes only) never sees the whole word.
 */
const shownWords = () =>
  Array.from(document.querySelectorAll('.word-display')).map((el) => el.textContent);

/** Deliver a terminal SSE event to one specific stream, as the server would. */
async function completeStream(index, results) {
  await act(async () => {
    sources()[index].onmessage({
      data: JSON.stringify({
        status: 'complete',
        progress: 100,
        message: 'Search complete',
        data: { results },
      }),
    });
  });
}

async function runSearch(user, input, button, pattern) {
  await user.clear(input);
  await user.type(input, pattern);
  const before = sources().length;
  await user.click(button);
  await waitFor(() => expect(sources().length).toBe(before + 1));
}

describe('PatternMatcher SSE completion (real hook)', () => {
  const props = { selectedCell: null, onSelectWord: () => {} };

  it('renders the second search results, not the first search results', async () => {
    const user = userEvent.setup();
    render(<PatternMatcher {...props} />);

    const input = screen.getByPlaceholderText(/enter pattern/i);
    const button = screen.getByRole('button', { name: /search/i });

    await runSearch(user, input, button, 'C?T');
    await completeStream(0, [{ word: 'CAT', score: 95 }]);
    await waitFor(() => expect(shownWords()).toEqual(['CAT']));

    await runSearch(user, input, button, '?I?A');
    await completeStream(1, [{ word: 'RITA', score: 80 }]);

    await waitFor(() => expect(shownWords()).toEqual(['RITA']));
  });

  it('does not publish the previous payload while the new search is still running', async () => {
    const user = userEvent.setup();
    render(<PatternMatcher {...props} />);

    const input = screen.getByPlaceholderText(/enter pattern/i);
    const button = screen.getByRole('button', { name: /search/i });

    await runSearch(user, input, button, 'C?T');
    await completeStream(0, [{ word: 'CAT', score: 95 }]);
    expect(await screen.findByText(/results \(1\)/i)).toBeInTheDocument();

    // Second search started, no terminal event delivered yet: the panel must be
    // showing progress, not a results list carried over from the first search.
    await runSearch(user, input, button, '?I?A');

    expect(screen.queryByText(/results \(/i)).not.toBeInTheDocument();
    expect(button).toBeDisabled();
  });
});
