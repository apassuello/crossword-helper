import React, { useState, useCallback, useEffect } from 'react';
import { api } from '../api/client';
import './PatternMatcher.scss';
import ProgressIndicator from './ProgressIndicator';
import { useSSEProgress } from '../hooks/useSSEProgress';

function PatternMatcher({ selectedCell, onSelectWord }) {
  const [pattern, setPattern] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('score');
  const [filterMinScore, setFilterMinScore] = useState(0);
  const [availableWordlists, setAvailableWordlists] = useState([]);
  const [selectedWordlists, setSelectedWordlists] = useState(['comprehensive']);
  const [algorithm, setAlgorithm] = useState('regex');  // Algorithm selection state
  const searchProgress = useSSEProgress();

  // Load available wordlists on mount
  useEffect(() => {
    const loadWordlists = async () => {
      try {
        const response = await api.getWordlists();
        setAvailableWordlists(response.wordlists || []);
      } catch (error) {
        console.error('Failed to load wordlists:', error);
        // Fall back to the default list so the panel stays usable
        setAvailableWordlists([{ key: 'comprehensive', name: 'Comprehensive' }]);
      }
    };
    loadWordlists();
  }, []);

  const searchPattern = useCallback(async () => {
    if (!pattern || pattern.length < 3) {
      setError('Pattern must be at least 3 characters');
      return;
    }

    // Reset the progress hook BEFORE flipping `loading`. Without this there is
    // a render in which loading === true while status is still 'complete' and
    // data still holds the previous search's payload — connect() below is what
    // resets them, and it only runs after the POST resolves. The completion
    // effect keys on exactly that pair, so it would publish the stale results
    // and clear `loading`, after which the real completion is rejected by its
    // own `loading` guard. See issue #11.
    searchProgress.reset();

    setLoading(true);
    setError(null);
    setResults([]);  // Clear previous results

    try {
      // Start search with progress tracking
      const { task_id } = await api.startPatternSearch({
        pattern: pattern.toUpperCase(),
        maxResults: 50,
        wordlists: selectedWordlists,
        algorithm,
      });

      // Connect to SSE for progress updates
      searchProgress.connect(task_id);

    } catch (err) {
      // ApiError carries the normalized message (src/api/client.js:normalizeError).
      const errorMsg = err.message || 'Search failed';
      setError(errorMsg);
      setResults([]);
      setLoading(false);
    }
  }, [pattern, selectedWordlists, algorithm, searchProgress]);

  // Watch for search completion.
  // The final SSE event already carries the results (searchProgress.data.results),
  // so use them directly — no redundant follow-up POST to /api/pattern.
  useEffect(() => {
    if (searchProgress.status === 'complete' && loading) {
      let searchResults = [...(searchProgress.data?.results || [])];

      // Sort results
      if (sortBy === 'score') {
        searchResults.sort((a, b) => b.score - a.score);
      } else if (sortBy === 'alpha') {
        searchResults.sort((a, b) => a.word.localeCompare(b.word));
      } else if (sortBy === 'length') {
        searchResults.sort((a, b) => a.word.length - b.word.length);
      }

      // Filter by minimum score
      if (filterMinScore > 0) {
        searchResults = searchResults.filter(r => r.score >= filterMinScore);
      }

      if (searchResults.length === 0) {
        setError('No matching words found');
      }

      setResults(searchResults);
      setLoading(false);
    } else if (searchProgress.status === 'error' && loading) {
      setError(searchProgress.message || 'Search failed');
      setResults([]);
      setLoading(false);
    }
  }, [searchProgress.status, searchProgress.data, searchProgress.message, loading, sortBy, filterMinScore]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      searchPattern();
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#4caf50';
    if (score >= 60) return '#ff9800';
    if (score >= 40) return '#ff5722';
    return '#f44336';
  };

  const renderLetterQuality = (word) => {
    const commonLetters = new Set('EARIOTNS');
    const uncommonLetters = new Set('JQXZ');

    return word.split('').map((letter, idx) => {
      let className = 'letter';
      if (commonLetters.has(letter)) className += ' common';
      else if (uncommonLetters.has(letter)) className += ' uncommon';

      return (
        <span key={idx} className={className}>
          {letter}
        </span>
      );
    });
  };

  return (
    <div className="pattern-matcher">
      <h2>Pattern Search</h2>

      <div className="search-controls">
        <div className="pattern-input-group">
          <input
            type="text"
            value={pattern}
            onChange={(e) => setPattern(e.target.value.toUpperCase())}
            onKeyPress={handleKeyPress}
            placeholder="Enter pattern (e.g., ?I?A)"
            className="pattern-input"
          />
          <button onClick={searchPattern} disabled={loading} className="search-btn">
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>

        <div className="pattern-help">
          Use <code>?</code> for unknown letters. Example: <code>C?T</code> finds CAT, COT, CUT
        </div>

        <div className="wordlist-selector">
          <label>Search in wordlists:</label>
          <div className="wordlist-checkboxes">
            {availableWordlists.length === 0 && (
              <div className="wordlist-loading">Loading wordlists...</div>
            )}
            {availableWordlists.map((wl) => (
              <label key={wl.key || wl.name} className="wordlist-option">
                <input
                  type="checkbox"
                  checked={selectedWordlists.includes(wl.key)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedWordlists([...selectedWordlists, wl.key]);
                    } else {
                      setSelectedWordlists(selectedWordlists.filter(w => w !== wl.key));
                    }
                  }}
                />
                <span>
                  {wl.name}
                  {wl.word_count ? ` (${wl.word_count.toLocaleString()} words)` : ''}
                </span>
              </label>
            ))}
          </div>
        </div>

        <div className="filter-controls">
          <div className="control-group">
            <label>Algorithm:</label>
            <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
              <option value="regex">Regex (Classic)</option>
              <option value="trie">Trie (Fast)</option>
            </select>
            {algorithm === 'trie' && (
              <span className="algorithm-badge" style={{marginLeft: '8px', color: '#4caf50', fontSize: '12px'}}>
                ⚡ 4-10x faster
              </span>
            )}
          </div>

          <div className="control-group">
            <label>Sort by:</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="score">Score</option>
              <option value="alpha">Alphabetical</option>
              <option value="length">Length</option>
            </select>
          </div>

          <div className="control-group">
            <label>Min Score:</label>
            <input
              type="range"
              min="0"
              max="100"
              step="10"
              value={filterMinScore}
              onChange={(e) => setFilterMinScore(parseInt(e.target.value))}
            />
            <span className="range-value">{filterMinScore}</span>
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading && (
        <ProgressIndicator
          type={searchProgress.progress > 0 ? "bar" : "spinner"}
          progress={searchProgress.progress || 0}
          message={searchProgress.message || `Searching with ${algorithm === 'trie' ? 'Trie (Fast)' : 'Regex (Classic)'} algorithm...`}
          size="medium"
          color={
            searchProgress.status === 'error' ? 'danger' :
            searchProgress.status === 'complete' ? 'success' :
            'primary'
          }
        />
      )}

      {results.length > 0 && (
        <div className="results-section">
          <h3>Results ({results.length})</h3>
          <div className="results-list">
            {results.map((result, idx) => (
              <div
                key={idx}
                className="result-item"
                onClick={() => onSelectWord(result.word)}
              >
                <div className="word-display">
                  {renderLetterQuality(result.word)}
                </div>
                <div className="word-meta">
                  <span
                    className="score-badge"
                    style={{ backgroundColor: getScoreColor(result.score) }}
                  >
                    {result.score}
                  </span>
                  <span className="source-badge">
                    {result.source || 'local'}
                  </span>
                  <span className="length-badge">
                    {result.word.length} letters
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedCell && (
        <div className="selected-cell-info">
          <p>
            Selected: Row {selectedCell.row + 1}, Col {selectedCell.col + 1}
            {selectedCell.direction && ` (${selectedCell.direction})`}
          </p>
          <p className="hint">Click a word to fill it in the grid</p>
        </div>
      )}
    </div>
  );
}

export default PatternMatcher;