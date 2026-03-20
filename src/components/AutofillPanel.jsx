import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import axios from 'axios';
import './AutofillPanel.scss';
import ProgressIndicator from './ProgressIndicator';
import BlackSquareSuggestions from './BlackSquareSuggestions';

function AutofillPanel({ onStartAutofill, onCancelAutofill, onResetAutofill, progress, grid, currentTaskId }) {
  const [options, setOptions] = useState({
    minScore: 50,
    preferPersonalWords: true,
    timeout: 300,
    wordlists: ['comprehensive'],
    themeList: null,  // NEW: designated theme list for priority (null or wordlist key)
    algorithm: 'repair',  // 'repair' (fast, reliable), 'trie', or 'beam' (slow, buggy)
    adaptiveMode: false,  // Auto black square placement when stuck
    maxAdaptations: 3,  // Max number of adaptive black squares
    partialFill: false,  // Enable collaborative partial fill mode
    cleanup: false  // Remove invalid words after fill, keep valid crossing letters
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
    const visited = new Set();

    // Helper to extract contiguous theme-locked cells
    const extractThemeWord = (startRow, startCol, direction) => {
      let word = '';
      let positions = [];

      if (direction === 'across') {
        let c = startCol;
        while (c < grid[startRow].length &&
               !grid[startRow][c].isBlack &&
               grid[startRow][c].isThemeLocked &&
               grid[startRow][c].letter) {
          word += grid[startRow][c].letter;
          positions.push(`${startRow},${c}`);
          visited.add(`${startRow},${c},across`);
          c++;
        }
      } else {
        let r = startRow;
        while (r < grid.length &&
               !grid[r][startCol].isBlack &&
               grid[r][startCol].isThemeLocked &&
               grid[r][startCol].letter) {
          word += grid[r][startCol].letter;
          positions.push(`${r},${startCol}`);
          visited.add(`${r},${startCol},down`);
          r++;
        }
      }

      return { word, positions };
    };

    // Find all contiguous theme-locked sequences (across)
    for (let row = 0; row < grid.length; row++) {
      let col = 0;
      while (col < grid[row].length) {
        const cell = grid[row][col];

        if (cell.isThemeLocked && !cell.isBlack && cell.letter) {
          // Check if this is the start of a new theme word (not visited)
          const cellKey = `${row},${col},across`;
          if (!visited.has(cellKey)) {
            // Check if previous cell is NOT theme-locked (or we're at start)
            const isThemeStart = col === 0 ||
                                !grid[row][col - 1].isThemeLocked ||
                                grid[row][col - 1].isBlack;

            if (isThemeStart) {
              const { word, positions } = extractThemeWord(row, col, 'across');
              if (word.length > 1) {
                const slotKey = `${row},${col},across`;
                themeEntries[`(${slotKey})`] = word;
              }
            }
          }
        }
        col++;
      }
    }

    // Find all contiguous theme-locked sequences (down)
    for (let col = 0; col < grid[0].length; col++) {
      let row = 0;
      while (row < grid.length) {
        const cell = grid[row][col];

        if (cell.isThemeLocked && !cell.isBlack && cell.letter) {
          // Check if this is the start of a new theme word (not visited)
          const cellKey = `${row},${col},down`;
          if (!visited.has(cellKey)) {
            // Check if previous cell is NOT theme-locked (or we're at start)
            const isThemeStart = row === 0 ||
                                !grid[row - 1][col].isThemeLocked ||
                                grid[row - 1][col].isBlack;

            if (isThemeStart) {
              const { word, positions } = extractThemeWord(row, col, 'down');
              if (word.length > 1) {
                const slotKey = `${row},${col},down`;
                themeEntries[`(${slotKey})`] = word;
              }
            }
          }
        }
        row++;
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
      <div className="autofill-header">
        <h2>Autofill Grid</h2>
        <div className="empty-slots">
          <strong>{getEmptySlots()}</strong> empty slots
          {Object.keys(getThemeEntries()).length > 0 && (
            <span className="theme-count"> | <strong>{Object.keys(getThemeEntries()).length}</strong> theme words</span>
          )}
        </div>
      </div>

      {showResumePrompt && pausedStateInfo && !progress && (
        <div className="resume-prompt">
          <h3>Paused Autofill Available</h3>
          <p>
            <strong>{pausedStateInfo.slots_filled}/{pausedStateInfo.total_slots}</strong> slots filled
          </p>
          <div style={{display: 'flex', gap: '0.5rem'}}>
            <button className="resume-btn" onClick={handleResume}>
              Resume Autofill
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
            <div style={{display: 'flex', gap: '0.5rem', marginTop: '0.75rem', flexWrap: 'wrap'}}>
              <button className="pause-btn" onClick={handlePause}>
                Pause
              </button>
              <button className="cancel-btn" onClick={onCancelAutofill}>
                Cancel
              </button>
              <button className="suggest-black-btn" onClick={handleSuggestBlackSquares}>
                Suggest Black Square
              </button>
            </div>
          )}
          {(progress.status === 'error' || progress.status === 'complete' || progress.status === 'warning') && (
            <div style={{display: 'flex', gap: '0.5rem', marginTop: '0.75rem', flexWrap: 'wrap'}}>
              <button className="reset-btn" onClick={onResetAutofill}>
                Reset Autofill
              </button>
            </div>
          )}
        </div>
      )}

      <div className="autofill-options">
        <h3>Options</h3>

        <div className="compact-row">
          <label>Algorithm</label>
          <select
            value={options.algorithm}
            onChange={(e) => handleOptionChange('algorithm', e.target.value)}
          >
            <option value="repair">Repair (Recommended)</option>
            <option value="hybrid">Hybrid (Beam + Repair)</option>
            <option value="beam">Beam Search</option>
            <option value="trie">Trie (Classic CSP)</option>
          </select>
        </div>

        <div className="compact-row">
          <label>Timeout</label>
          <select
            value={options.timeout}
            onChange={(e) => handleOptionChange('timeout', parseInt(e.target.value))}
          >
            <option value="60">1 min</option>
            <option value="180">3 min</option>
            <option value="300">5 min</option>
            <option value="600">10 min</option>
          </select>
        </div>

        <div className="compact-row">
          <label>Min Score: {options.minScore}</label>
          <input
            type="range"
            min="0"
            max="100"
            step="10"
            value={options.minScore}
            onChange={(e) => handleOptionChange('minScore', parseInt(e.target.value))}
          />
        </div>

        <div className="checkbox-row">
          <label>
            <input
              type="checkbox"
              checked={options.preferPersonalWords}
              onChange={(e) => handleOptionChange('preferPersonalWords', e.target.checked)}
            />
            Prefer personal words
          </label>
          <label>
            <input
              type="checkbox"
              checked={options.adaptiveMode}
              onChange={(e) => handleOptionChange('adaptiveMode', e.target.checked)}
            />
            Adaptive mode
          </label>
          <label>
            <input
              type="checkbox"
              checked={options.partialFill}
              onChange={(e) => handleOptionChange('partialFill', e.target.checked)}
            />
            Partial fill
          </label>
          <label>
            <input
              type="checkbox"
              checked={options.cleanup}
              onChange={(e) => handleOptionChange('cleanup', e.target.checked)}
            />
            Cleanup invalid words
          </label>
        </div>

        {options.adaptiveMode && (
          <div className="compact-row">
            <label>Max adaptations: {options.maxAdaptations}</label>
            <input
              type="range"
              min="1"
              max="5"
              step="1"
              value={options.maxAdaptations}
              onChange={(e) => handleOptionChange('maxAdaptations', parseInt(e.target.value))}
            />
          </div>
        )}

        <div className="option-group wordlists-group">
          <label>Word Lists</label>

          {wordlistsLoading ? (
            <div className="wordlist-loading">Loading...</div>
          ) : (
            <div className="wordlist-scroll-container">
              {availableWordlists.built_in.length > 0 && (
                <div className="wordlist-section">
                  <h4>Built-in</h4>
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
                        {wl.name} {wl.word_count && `(${wl.word_count.toLocaleString()})`}
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {availableWordlists.custom.length > 0 && (
                <div className="wordlist-section custom-section">
                  <h4>Custom</h4>
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

                              if (!e.target.checked && options.themeList === wl.key) {
                                handleOptionChange('themeList', null);
                              }
                            }}
                          />
                          {wl.name} {wl.word_count && `(${wl.word_count.toLocaleString()})`}
                        </label>

                        {options.wordlists.includes(wl.key) && (
                          <label className="theme-designation">
                            <input
                              type="radio"
                              name="themeList"
                              checked={options.themeList === wl.key}
                              onChange={() => handleOptionChange('themeList', wl.key)}
                            />
                            <span className="theme-label">Theme List</span>
                          </label>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {options.themeList && (
            <div className="theme-info">
              <strong>Theme List Active:</strong> {availableWordlists.custom.find(w => w.key === options.themeList)?.name}
            </div>
          )}
        </div>
      </div>

      {!progress && getEmptySlots() > 0 && (
        <button
          className="suggest-black-btn"
          onClick={handleSuggestBlackSquares}
          style={{width: '100%', marginTop: '0.5rem'}}
        >
          Suggest Strategic Black Square
        </button>
      )}

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