import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import axios from 'axios';
import './AutofillPanel.scss';
import ProgressIndicator from './ProgressIndicator';
import BlackSquareSuggestions from './BlackSquareSuggestions';

function AutofillPanel({ onStartAutofill, onCancelAutofill, progress, grid, currentTaskId }) {
  const [options, setOptions] = useState({
    minScore: 50,
    preferPersonalWords: true,
    timeout: 300,
    wordlists: ['comprehensive'],
    themeList: null,  // NEW: designated theme list for priority (null or wordlist key)
    algorithm: 'beam',  // 'regex', 'trie', or 'beam' (default: beam with thrashing fixes)
    adaptiveMode: false,  // Auto black square placement when stuck
    maxAdaptations: 3  // Max number of adaptive black squares
  });

  // Available wordlists (loaded from API)
  const [availableWordlists, setAvailableWordlists] = useState({
    built_in: [],
    custom: []
  });
  const [wordlistsLoading, setWordlistsLoading] = useState(true);

  // Pause/Resume state
  const [pausedTaskId, setPausedTaskId] = useState(null);
  const [pausedStateInfo, setPausedStateInfo] = useState(null);
  const [showResumePrompt, setShowResumePrompt] = useState(false);

  // Black Square Suggestions state
  const [showBlackSquareModal, setShowBlackSquareModal] = useState(false);
  const [problematicSlot, setProblematicSlot] = useState(null);

  const handleOptionChange = (key, value) => {
    setOptions(prev => ({ ...prev, [key]: value }));
  };

  // Load available wordlists on mount
  useEffect(() => {
    loadAvailableWordlists();
  }, []);

  // Check for paused state on mount
  useEffect(() => {
    const savedTaskId = localStorage.getItem('paused_autofill_task');
    if (savedTaskId) {
      fetchPausedState(savedTaskId);
    }
  }, []);

  const loadAvailableWordlists = async () => {
    try {
      const response = await axios.get('/api/wordlists');
      const wordlists = response.data.wordlists;

      // Separate built-in from custom
      const builtIn = wordlists.filter(wl => wl.category !== 'custom');
      const custom = wordlists.filter(wl => wl.category === 'custom');

      setAvailableWordlists({ built_in: builtIn, custom: custom });
      setWordlistsLoading(false);
    } catch (error) {
      console.error('Failed to load wordlists:', error);
      setWordlistsLoading(false);
      // Fall back to hardcoded lists if API fails
    }
  };

  // Save task ID when autofill starts (don't wait for 'running' status to avoid race condition)
  useEffect(() => {
    if (currentTaskId) {
      localStorage.setItem('current_autofill_task', currentTaskId);
    }
  }, [currentTaskId]);

  const fetchPausedState = async (taskId) => {
    try {
      const response = await axios.get(`/api/fill/state/${taskId}`);
      const stateInfo = response.data;
      setPausedTaskId(taskId);
      setPausedStateInfo(stateInfo);
      setShowResumePrompt(true);
    } catch (err) {
      // State no longer exists (404) or other error, clear localStorage
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
      await axios.post(`/api/fill/pause/${currentTaskId}`);

      toast.success('Pause requested - waiting for autofill to stop...');
      // Save task ID for later resume
      localStorage.setItem('paused_autofill_task', currentTaskId);
      localStorage.removeItem('current_autofill_task');

      // Wait a moment for pause to take effect
      setTimeout(() => {
        fetchPausedState(currentTaskId);
      }, 2000);
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

      const response = await axios.post('/api/fill/resume', {
        task_id: pausedTaskId,
        edited_grid: gridArray,
        options: options
      });

      const data = response.data;

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

      if (err.response?.status === 409) {
        // User edits create unsolvable configuration
        const error = err.response.data;
        toast.error(
          `Cannot resume: Your edits create an unsolvable grid. ${error.details || ''} Please adjust your changes and try again.`,
          { duration: 6000 }
        );
        return;
      }

      const errorMsg = err.response?.data?.error || err.message || 'Resume failed';
      toast.error(`Failed to resume: ${errorMsg}`);
    }
  };

  const handleDiscardPaused = () => {
    if (confirm('Discard paused state? This cannot be undone.')) {
      if (pausedTaskId) {
        // Delete state file
        axios.delete(`/api/fill/state/${pausedTaskId}`)
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

  const findMostConstrainedSlot = () => {
    if (!grid) return null;

    const slots = [];

    // Helper to get pattern for a slot
    const getPattern = (row, col, direction) => {
      let pattern = '';
      if (direction === 'across') {
        let c = col;
        while (c < grid[row].length && !grid[row][c].isBlack) {
          pattern += grid[row][c].letter || '?';
          c++;
        }
      } else {
        let r = row;
        while (r < grid.length && !grid[r][col].isBlack) {
          pattern += grid[r][col].letter || '?';
          r++;
        }
      }
      return pattern;
    };

    // Find all slots with empty cells
    const processedSlots = new Set();

    for (let row = 0; row < grid.length; row++) {
      for (let col = 0; col < grid[row].length; col++) {
        const cell = grid[row][col];

        if (!cell.isBlack) {
          // Check across slot
          const isStartAcross = col === 0 || grid[row][col - 1].isBlack;
          if (isStartAcross) {
            const slotKey = `${row},${col},across`;
            if (!processedSlots.has(slotKey)) {
              const pattern = getPattern(row, col, 'across');
              if (pattern.length >= 3 && pattern.includes('?')) {
                slots.push({
                  row,
                  col,
                  direction: 'across',
                  length: pattern.length,
                  pattern,
                  emptyCount: (pattern.match(/\?/g) || []).length
                });
                processedSlots.add(slotKey);
              }
            }
          }

          // Check down slot
          const isStartDown = row === 0 || grid[row - 1][col].isBlack;
          if (isStartDown) {
            const slotKey = `${row},${col},down`;
            if (!processedSlots.has(slotKey)) {
              const pattern = getPattern(row, col, 'down');
              if (pattern.length >= 3 && pattern.includes('?')) {
                slots.push({
                  row,
                  col,
                  direction: 'down',
                  length: pattern.length,
                  pattern,
                  emptyCount: (pattern.match(/\?/g) || []).length
                });
                processedSlots.add(slotKey);
              }
            }
          }
        }
      }
    }

    // Find slot with longest length or most empty cells (most likely to be problematic)
    if (slots.length === 0) return null;

    // Prioritize by length (longer slots are harder to fill)
    slots.sort((a, b) => b.length - a.length);

    const mostConstrained = slots[0];
    return {
      ...mostConstrained,
      candidate_count: 0 // Will be calculated by backend
    };
  };

  const handleSuggestBlackSquares = () => {
    const slot = findMostConstrainedSlot();

    if (!slot) {
      toast('No problematic slots found', { icon: 'ℹ️' });
      return;
    }

    setProblematicSlot(slot);
    setShowBlackSquareModal(true);
  };

  const handleApplyBlackSquares = (updatedGrid, suggestion) => {
    // Close modal
    setShowBlackSquareModal(false);
    setProblematicSlot(null);

    // The grid update should be handled by the parent component
    // through the onApplyPlacement callback or similar mechanism
    toast.success('Black squares applied! Grid will update shortly.');
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
          <label>
            <input
              type="checkbox"
              checked={options.adaptiveMode}
              onChange={(e) => handleOptionChange('adaptiveMode', e.target.checked)}
            />
            ⚡ Adaptive Mode (Auto Black Squares)
          </label>
          <p className="help-text">
            Automatically place strategic black squares when autofill gets stuck
          </p>

          {options.adaptiveMode && (
            <div className="slider-group" style={{marginTop: '0.5rem'}}>
              <label style={{fontSize: '0.9rem', fontWeight: 'normal'}}>Max Adaptations:</label>
              <input
                type="range"
                min="1"
                max="5"
                step="1"
                value={options.maxAdaptations}
                onChange={(e) => handleOptionChange('maxAdaptations', parseInt(e.target.value))}
              />
              <span className="value">{options.maxAdaptations}</span>
            </div>
          )}
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

          {wordlistsLoading ? (
            <div className="wordlist-loading">Loading wordlists...</div>
          ) : (
            <>
              {/* Built-in wordlists */}
              {availableWordlists.built_in.length > 0 && (
                <div className="wordlist-section">
                  <h4>Built-in Lists</h4>
                  <div className="wordlist-checkboxes">
                    {availableWordlists.built_in.map(wl => (
                      <label key={wl.key}>
                        <input
                          type="checkbox"
                          checked={options.wordlists.includes(wl.key)}
                          onChange={(e) => {
                            const lists = e.target.checked
                              ? [...options.wordlists, wl.key]
                              : options.wordlists.filter(l => l !== wl.key);
                            handleOptionChange('wordlists', lists);
                          }}
                        />
                        {wl.name} {wl.word_count && `(${wl.word_count.toLocaleString()} words)`}
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Custom wordlists */}
              {availableWordlists.custom.length > 0 && (
                <div className="wordlist-section custom-section">
                  <h4>🎨 Custom Lists</h4>
                  <div className="wordlist-checkboxes">
                    {availableWordlists.custom.map(wl => (
                      <div key={wl.key} className="wordlist-item-container">
                        <label className="wordlist-checkbox">
                          <input
                            type="checkbox"
                            checked={options.wordlists.includes(wl.key)}
                            onChange={(e) => {
                              const lists = e.target.checked
                                ? [...options.wordlists, wl.key]
                                : options.wordlists.filter(l => l !== wl.key);
                              handleOptionChange('wordlists', lists);

                              // If unchecking and it's the theme list, clear theme designation
                              if (!e.target.checked && options.themeList === wl.key) {
                                handleOptionChange('themeList', null);
                              }
                            }}
                          />
                          {wl.name} {wl.word_count && `(${wl.word_count.toLocaleString()} words)`}
                        </label>

                        {/* Theme designation radio button - only show if checked */}
                        {options.wordlists.includes(wl.key) && (
                          <label className="theme-designation">
                            <input
                              type="radio"
                              name="themeList"
                              checked={options.themeList === wl.key}
                              onChange={() => handleOptionChange('themeList', wl.key)}
                            />
                            <span className="theme-label">⭐ Theme List</span>
                          </label>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Theme list info banner */}
                  {options.themeList && (
                    <div className="theme-info">
                      <strong>⭐ Theme List Active:</strong> {availableWordlists.custom.find(w => w.key === options.themeList)?.name}
                      <p className="help-text">
                        The autofill algorithm will prioritize words from this list and try to use as many as possible.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {availableWordlists.custom.length === 0 && (
                <div className="no-custom-lists">
                  <p className="help-text">
                    No custom wordlists yet. Upload one in the "Word Lists" tab!
                  </p>
                </div>
              )}
            </>
          )}
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
              <button className="suggest-black-btn" onClick={handleSuggestBlackSquares}>
                ⬛ Suggest Black Square
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

        {!progress && getEmptySlots() > 0 && (
          <div style={{marginTop: '1rem'}}>
            <button
              className="suggest-black-btn"
              onClick={handleSuggestBlackSquares}
              style={{width: '100%'}}
            >
              ⬛ Suggest Strategic Black Square
            </button>
            <p className="help-text" style={{marginTop: '0.5rem', fontSize: '0.85rem'}}>
              Get suggestions for placing "cheater squares" to make difficult slots easier to fill
            </p>
          </div>
        )}
      </div>

      {/* Black Square Suggestions Modal */}
      {showBlackSquareModal && problematicSlot && (
        <BlackSquareSuggestions
          grid={grid}
          gridSize={grid ? grid.length : 15}
          problematicSlot={problematicSlot}
          onApplySuggestion={handleApplyBlackSquares}
          onClose={() => {
            setShowBlackSquareModal(false);
            setProblematicSlot(null);
          }}
        />
      )}
    </div>
  );
}

export default AutofillPanel;