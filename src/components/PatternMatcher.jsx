import React, { useState, useCallback, useEffect } from 'react';
import axios from 'axios';
import './PatternMatcher.scss';

function PatternMatcher({ selectedCell, onSelectWord }) {
  const [pattern, setPattern] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('score');
  const [filterMinScore, setFilterMinScore] = useState(0);
  const [availableWordlists, setAvailableWordlists] = useState([]);
  const [selectedWordlists, setSelectedWordlists] = useState(['comprehensive']);

  // Load available wordlists on mount
  useEffect(() => {
    const loadWordlists = async () => {
      try {
        const response = await axios.get('/api/wordlists');
        setAvailableWordlists(response.data.wordlists);
      } catch (error) {
        console.error('Failed to load wordlists:', error);
      }
    };
    loadWordlists();
  }, []);

  const searchPattern = useCallback(async () => {
    if (!pattern || pattern.length < 3) {
      setError('Pattern must be at least 3 characters');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/pattern', {
        pattern: pattern.toUpperCase(),
        max_results: 50,
        wordlists: selectedWordlists
      });

      let searchResults = response.data.results || [];

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

      setResults(searchResults);
    } catch (err) {
      setError(err.response?.data?.error || 'Search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [pattern, sortBy, filterMinScore, selectedWordlists]);

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
            <label className="wordlist-option">
              <input
                type="checkbox"
                checked={selectedWordlists.includes('comprehensive')}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedWordlists([...selectedWordlists, 'comprehensive']);
                  } else {
                    setSelectedWordlists(selectedWordlists.filter(w => w !== 'comprehensive'));
                  }
                }}
              />
              <span>Comprehensive (454k words)</span>
            </label>
            <label className="wordlist-option">
              <input
                type="checkbox"
                checked={selectedWordlists.includes('core/common_3_letter')}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedWordlists([...selectedWordlists, 'core/common_3_letter']);
                  } else {
                    setSelectedWordlists(selectedWordlists.filter(w => w !== 'core/common_3_letter'));
                  }
                }}
              />
              <span>Common 3-Letter</span>
            </label>
            <label className="wordlist-option">
              <input
                type="checkbox"
                checked={selectedWordlists.includes('core/crosswordese')}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedWordlists([...selectedWordlists, 'core/crosswordese']);
                  } else {
                    setSelectedWordlists(selectedWordlists.filter(w => w !== 'core/crosswordese'));
                  }
                }}
              />
              <span>Crosswordese</span>
            </label>
            <label className="wordlist-option">
              <input
                type="checkbox"
                checked={selectedWordlists.includes('themed/expressions_and_slang')}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedWordlists([...selectedWordlists, 'themed/expressions_and_slang']);
                  } else {
                    setSelectedWordlists(selectedWordlists.filter(w => w !== 'themed/expressions_and_slang'));
                  }
                }}
              />
              <span>Expressions & Slang</span>
            </label>
          </div>
        </div>

        <div className="filter-controls">
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