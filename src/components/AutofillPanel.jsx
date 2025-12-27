import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import './AutofillPanel.scss';
import ProgressIndicator from './ProgressIndicator';

function AutofillPanel({ onStartAutofill, onCancelAutofill, progress, grid, currentTaskId }) {
  const [options, setOptions] = useState({
    minScore: 50,
    preferPersonalWords: true,
    timeout: 300,
    wordlists: ['comprehensive'],
    algorithm: 'beam'  // 'regex', 'trie', or 'beam' (default: beam with thrashing fixes)
  });

  // Pause/Resume state
  const [pausedTaskId, setPausedTaskId] = useState(null);
  const [pausedStateInfo, setPausedStateInfo] = useState(null);
  const [showResumePrompt, setShowResumePrompt] = useState(false);

  const handleOptionChange = (key, value) => {
    setOptions(prev => ({ ...prev, [key]: value }));
  };

  // Check for paused state on mount
  useEffect(() => {
    const savedTaskId = localStorage.getItem('paused_autofill_task');
    if (savedTaskId) {
      fetchPausedState(savedTaskId);
    }
  }, []);

  // Save task ID when autofill starts (don't wait for 'running' status to avoid race condition)
  useEffect(() => {
    if (currentTaskId) {
      localStorage.setItem('current_autofill_task', currentTaskId);
    }
  }, [currentTaskId]);

  const fetchPausedState = async (taskId) => {
    try {
      const response = await fetch(`/api/fill/state/${taskId}`);
      if (response.ok) {
        const stateInfo = await response.json();
        setPausedTaskId(taskId);
        setPausedStateInfo(stateInfo);
        setShowResumePrompt(true);
      } else {
        // State no longer exists, clear localStorage
        localStorage.removeItem('paused_autofill_task');
      }
    } catch (err) {
      console.error('Failed to fetch paused state:', err);
      localStorage.removeItem('paused_autofill_task');
    }
  };

  const handlePause = async () => {
    if (!currentTaskId) {
      toast.error('No active autofill task to pause');
      return;
    }

    try {
      const response = await fetch(`/api/fill/pause/${currentTaskId}`, {
        method: 'POST'
      });

      if (response.ok) {
        toast.success('Pause requested - waiting for autofill to stop...');
        // Save task ID for later resume
        localStorage.setItem('paused_autofill_task', currentTaskId);
        localStorage.removeItem('current_autofill_task');

        // Wait a moment for pause to take effect
        setTimeout(() => {
          fetchPausedState(currentTaskId);
        }, 2000);
      }
    } catch (err) {
      console.error('Failed to pause autofill:', err);
      toast.error('Failed to pause autofill. Please try again.');
    }
  };

  const handleResume = async () => {
    if (!pausedTaskId) {
      toast.error('No paused state to resume');
      return;
    }

    try {
      // Get current grid for edit detection
      const gridArray = grid.map(row =>
        row.map(cell => cell.letter ? [cell.letter] : ['.'])
      );

      const response = await fetch('/api/fill/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: pausedTaskId,
          edited_grid: gridArray,
          options: options
        })
      });

      if (!response.ok) {
        const error = await response.json();

        if (response.status === 409) {
          // User edits create unsolvable configuration
          toast.error(
            `Cannot resume: Your edits create an unsolvable grid. ${error.details || ''} Please adjust your changes and try again.`,
            { duration: 6000 }
          );
          return;
        }

        throw new Error(error.error || 'Resume failed');
      }

      const data = await response.json();

      // Clear paused state
      setPausedTaskId(null);
      setPausedStateInfo(null);
      setShowResumePrompt(false);
      localStorage.removeItem('paused_autofill_task');

      // Start autofill with new task ID
      toast.success('Resuming autofill from saved state...');
      console.log(`Resuming with new task ID: ${data.new_task_id}`);
      onStartAutofill({...options, theme_entries: getThemeEntries(), resumeTaskId: data.new_task_id});

    } catch (err) {
      console.error('Failed to resume autofill:', err);
      toast.error(`Failed to resume: ${err.message}`);
    }
  };

  const handleDiscardPaused = () => {
    if (confirm('Discard paused state? This cannot be undone.')) {
      if (pausedTaskId) {
        // Delete state file
        fetch(`/api/fill/state/${pausedTaskId}`, { method: 'DELETE' })
          .then(() => toast.success('Paused state discarded'))
          .catch(err => {
            console.error('Failed to delete state:', err);
            toast.error('Failed to delete saved state');
          });
      }

      setPausedTaskId(null);
      setPausedStateInfo(null);
      setShowResumePrompt(false);
      localStorage.removeItem('paused_autofill_task');
    }
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

  const getThemeEntries = () => {
    if (!grid) return {};

    const themeEntries = {};

    // Helper to extract word from grid
    const extractWord = (row, col, direction) => {
      let word = '';
      if (direction === 'across') {
        let c = col;
        while (c < grid[row].length && !grid[row][c].isBlack) {
          word += grid[row][c].letter || '.';
          c++;
        }
      } else {
        let r = row;
        while (r < grid.length && !grid[r][col].isBlack) {
          word += grid[r][col].letter || '.';
          r++;
        }
      }
      return word;
    };

    // Find all theme-locked words
    const processedSlots = new Set();

    for (let row = 0; row < grid.length; row++) {
      for (let col = 0; col < grid[row].length; col++) {
        const cell = grid[row][col];

        if (cell.isThemeLocked && !cell.isBlack && cell.letter) {
          // Check if this is the start of an across word
          const isStartAcross = col === 0 || grid[row][col - 1].isBlack;
          if (isStartAcross) {
            const slotKey = `${row},${col},across`;
            if (!processedSlots.has(slotKey)) {
              const word = extractWord(row, col, 'across');
              // Only add if word is complete (no dots) and length > 1
              if (!word.includes('.') && word.length > 1) {
                themeEntries[`(${slotKey})`] = word;
                processedSlots.add(slotKey);
              }
            }
          }

          // Check if this is the start of a down word
          const isStartDown = row === 0 || grid[row - 1][col].isBlack;
          if (isStartDown) {
            const slotKey = `${row},${col},down`;
            if (!processedSlots.has(slotKey)) {
              const word = extractWord(row, col, 'down');
              // Only add if word is complete (no dots) and length > 1
              if (!word.includes('.') && word.length > 1) {
                themeEntries[`(${slotKey})`] = word;
                processedSlots.add(slotKey);
              }
            }
          }
        }
      }
    }

    return themeEntries;
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
        {Object.keys(getThemeEntries()).length > 0 && (
          <div className="theme-entries" style={{marginTop: '0.5rem', color: '#7b1fa2', fontWeight: '500'}}>
            Theme entries locked: <strong>{Object.keys(getThemeEntries()).length}</strong>
            <small style={{display: 'block', fontSize: '0.85rem', fontWeight: 'normal', color: '#666', marginTop: '0.25rem'}}>
              Right-click cells to lock/unlock theme words
            </small>
          </div>
        )}
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
                value="beam"
                checked={options.algorithm === 'beam'}
                onChange={(e) => handleOptionChange('algorithm', e.target.value)}
              />
              <span className="radio-label">
                <strong>Beam Search</strong> (Recommended)
                <small>Best for complex grids, with anti-thrashing fixes</small>
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
                <small>Classic CSP, faster for simple grids</small>
              </span>
            </label>
            <label className="radio-option">
              <input
                type="radio"
                name="algorithm"
                value="regex"
                checked={options.algorithm === 'regex'}
                onChange={(e) => handleOptionChange('algorithm', e.target.value)}
              />
              <span className="radio-label">
                <strong>Regex</strong> (Legacy)
                <small>Fallback option, slower</small>
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

      {/* Resume Prompt Banner */}
      {showResumePrompt && pausedStateInfo && !progress && (
        <div className="resume-prompt">
          <h3>⏸ Paused Autofill Available</h3>
          <p>
            You have a paused autofill from {new Date(pausedStateInfo.timestamp).toLocaleString()}
          </p>
          <p>
            <strong>{pausedStateInfo.slots_filled}/{pausedStateInfo.total_slots}</strong> slots filled
          </p>
          <div style={{display: 'flex', gap: '0.5rem'}}>
            <button className="resume-btn" onClick={handleResume}>
              ▶ Resume Autofill
            </button>
            <button className="discard-btn" onClick={handleDiscardPaused}>
              Discard
            </button>
          </div>
        </div>
      )}

      {!progress && !showResumePrompt && (
        <button
          className="autofill-btn"
          onClick={() => onStartAutofill({...options, theme_entries: getThemeEntries()})}
          disabled={getEmptySlots() === 0}
        >
          Start Autofill
        </button>
      )}

      {progress && (
        <div className="progress-section">
          <h3>Autofill Progress</h3>
          <ProgressIndicator
            type={progress.progress > 0 ? "bar" : "spinner"}
            progress={progress.progress || 0}
            message={progress.message || `Using ${options.algorithm === 'trie' ? 'Trie (Fast)' : 'Regex (Classic)'} algorithm...`}
            size="large"
            color={
              progress.status === 'error' ? 'danger' :
              progress.status === 'complete' ? 'success' :
              progress.status === 'paused' ? 'warning' :
              'primary'
            }
          />
          {progress.status === 'running' && (
            <div style={{display: 'flex', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap'}}>
              <button className="pause-btn" onClick={handlePause}>
                ⏸ Pause
              </button>
              <button className="cancel-btn" onClick={onCancelAutofill}>
                Cancel
              </button>
            </div>
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