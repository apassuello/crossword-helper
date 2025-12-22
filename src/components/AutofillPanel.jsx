import React, { useState } from 'react';
import './AutofillPanel.scss';

function AutofillPanel({ onStartAutofill, progress, grid }) {
  const [options, setOptions] = useState({
    minScore: 50,
    preferPersonalWords: true,
    timeout: 300,
    wordlists: ['comprehensive'],
    algorithm: 'regex'  // 'regex' or 'trie'
  });

  const handleOptionChange = (key, value) => {
    setOptions(prev => ({ ...prev, [key]: value }));
  };

  const getEmptySlots = () => {
    if (!grid) return 0;

    let emptySlots = 0;
    let currentWord = false;

    // Count across words
    for (let row = 0; row < grid.length; row++) {
      for (let col = 0; col < grid[row].length; col++) {
        const cell = grid[row][col];
        if (!cell.isBlack && !cell.letter) {
          if (!currentWord) {
            emptySlots++;
            currentWord = true;
          }
        } else {
          currentWord = false;
        }
      }
    }

    // Count down words
    for (let col = 0; col < grid[0].length; col++) {
      for (let row = 0; row < grid.length; row++) {
        const cell = grid[row][col];
        if (!cell.isBlack && !cell.letter) {
          if (!currentWord) {
            emptySlots++;
            currentWord = true;
          }
        } else {
          currentWord = false;
        }
      }
    }

    return emptySlots;
  };

  return (
    <div className="autofill-panel">
      <h2>Autofill Grid</h2>

      <div className="autofill-info">
        <p>
          The autofill engine uses constraint satisfaction with backtracking
          to find valid word combinations for your grid.
        </p>
        <div className="empty-slots">
          Empty slots to fill: <strong>{getEmptySlots()}</strong>
        </div>
      </div>

      <div className="autofill-options">
        <h3>Options</h3>

        <div className="option-group">
          <label>Minimum Word Score</label>
          <div className="slider-group">
            <input
              type="range"
              min="0"
              max="100"
              step="10"
              value={options.minScore}
              onChange={(e) => handleOptionChange('minScore', parseInt(e.target.value))}
            />
            <span className="value">{options.minScore}</span>
          </div>
          <p className="help-text">Higher scores mean better crossword words</p>
        </div>

        <div className="option-group">
          <label>
            <input
              type="checkbox"
              checked={options.preferPersonalWords}
              onChange={(e) => handleOptionChange('preferPersonalWords', e.target.checked)}
            />
            Prefer personal word list
          </label>
        </div>

        <div className="option-group">
          <label>Algorithm</label>
          <div className="algorithm-selector">
            <label className="radio-option">
              <input
                type="radio"
                name="algorithm"
                value="regex"
                checked={options.algorithm === 'regex'}
                onChange={(e) => handleOptionChange('algorithm', e.target.value)}
              />
              <span className="radio-label">
                <strong>Regex</strong> (Classic)
                <small>Stable, well-tested algorithm</small>
              </span>
            </label>
            <label className="radio-option">
              <input
                type="radio"
                name="algorithm"
                value="trie"
                checked={options.algorithm === 'trie'}
                onChange={(e) => handleOptionChange('algorithm', e.target.value)}
              />
              <span className="radio-label">
                <strong>Trie</strong> (Fast)
                <small>10-50x faster for large wordlists</small>
              </span>
            </label>
          </div>
        </div>

        <div className="option-group">
          <label>Timeout (seconds)</label>
          <select
            value={options.timeout}
            onChange={(e) => handleOptionChange('timeout', parseInt(e.target.value))}
          >
            <option value="60">1 minute</option>
            <option value="180">3 minutes</option>
            <option value="300">5 minutes</option>
            <option value="600">10 minutes</option>
          </select>
        </div>

        <div className="option-group">
          <label>Word Lists</label>
          <div className="wordlist-checkboxes">
            <label>
              <input
                type="checkbox"
                checked={options.wordlists.includes('comprehensive')}
                onChange={(e) => {
                  const lists = e.target.checked
                    ? [...options.wordlists, 'comprehensive']
                    : options.wordlists.filter(l => l !== 'comprehensive');
                  handleOptionChange('wordlists', lists);
                }}
              />
              Comprehensive (454k words)
            </label>
            <label>
              <input
                type="checkbox"
                checked={options.wordlists.includes('core/common_3_letter')}
                onChange={(e) => {
                  const lists = e.target.checked
                    ? [...options.wordlists, 'core/common_3_letter']
                    : options.wordlists.filter(l => l !== 'core/common_3_letter');
                  handleOptionChange('wordlists', lists);
                }}
              />
              3-Letter Words
            </label>
            <label>
              <input
                type="checkbox"
                checked={options.wordlists.includes('core/crosswordese')}
                onChange={(e) => {
                  const lists = e.target.checked
                    ? [...options.wordlists, 'core/crosswordese']
                    : options.wordlists.filter(l => l !== 'core/crosswordese');
                  handleOptionChange('wordlists', lists);
                }}
              />
              Crosswordese
            </label>
            <label>
              <input
                type="checkbox"
                checked={options.wordlists.includes('themed/expressions_and_slang')}
                onChange={(e) => {
                  const lists = e.target.checked
                    ? [...options.wordlists, 'themed/expressions_and_slang']
                    : options.wordlists.filter(l => l !== 'themed/expressions_and_slang');
                  handleOptionChange('wordlists', lists);
                }}
              />
              Expressions & Slang
            </label>
            <label>
              <input
                type="checkbox"
                checked={options.wordlists.includes('themed/foreign_classics')}
                onChange={(e) => {
                  const lists = e.target.checked
                    ? [...options.wordlists, 'themed/foreign_classics']
                    : options.wordlists.filter(l => l !== 'themed/foreign_classics');
                  handleOptionChange('wordlists', lists);
                }}
              />
              Foreign Classics (ES/FR)
            </label>
            <label>
              <input
                type="checkbox"
                checked={options.wordlists.includes('themed/foreign_words')}
                onChange={(e) => {
                  const lists = e.target.checked
                    ? [...options.wordlists, 'themed/foreign_words']
                    : options.wordlists.filter(l => l !== 'themed/foreign_words');
                  handleOptionChange('wordlists', lists);
                }}
              />
              Foreign Words (5.7k)
            </label>
          </div>
        </div>
      </div>

      {!progress && (
        <button
          className="autofill-btn"
          onClick={() => onStartAutofill(options)}
          disabled={getEmptySlots() === 0}
        >
          Start Autofill
        </button>
      )}

      {progress && (
        <div className="progress-section">
          <h3>Progress</h3>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{
                width: `${progress.progress}%`,
                backgroundColor:
                  progress.status === 'error' ? '#f44336' :
                  progress.status === 'complete' ? '#4caf50' :
                  '#2196f3'
              }}
            />
          </div>
          <div className="progress-message">
            {progress.message}
          </div>
          {progress.status === 'running' && (
            <button className="cancel-btn">
              Cancel
            </button>
          )}
        </div>
      )}

      <div className="autofill-tips">
        <h3>Tips</h3>
        <ul>
          <li>Place theme answers manually before autofilling</li>
          <li>Add more black squares if autofill is too slow</li>
          <li>Use a higher minimum score for cleaner fill</li>
          <li>Personal word lists help create unique puzzles</li>
        </ul>
      </div>
    </div>
  );
}

export default AutofillPanel;