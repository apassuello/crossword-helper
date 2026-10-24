import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api/client';
import toast from 'react-hot-toast';
import './ThemeWordsPanel.scss';

// novice-readiness spec 0.2.7 §3.8 (TH2b), plan default PD-6-G13: the spec says
// "debounced" and gives no value.
export const SUGGESTION_REFETCH_DEBOUNCE_MS = 400;

// apply-placement's 400 body carries the conflict reasons in `details` (client.js
// rule 5); `details` is polymorphic across endpoints, so guard the shape before
// reading it as a conflicts array. First detail, plus a count of the rest.
function conflictText(details) {
  if (!Array.isArray(details) || details.length === 0) return null;
  const [first, ...rest] = details;
  return rest.length > 0 ? `${first} (+${rest.length} more)` : first;
}

// novice-readiness spec 0.2.7 §3.8 (TH3, PD-6-G17): the reason Apply All gives for
// one word whose apply request failed. "skipped due to conflicts" only for a real
// conflicts array; status 0 (no response arrived) is "could not reach the server"; anything else is the
// error's own message. The synthesised HTTP_<status> code never reaches the user.
function describeApplyFailure(error) {
  const conflicts = conflictText(error.details);
  if (conflicts) return `skipped due to conflicts: ${conflicts}`;
  if (error.status === 0) return 'Could not reach the server';
  return error.message || 'Failed to apply placement';
}

// novice-readiness spec 0.2.7 §3.8 (TH2b): the per-cell [letter, isBlack] plus
// gridSize. Deliberately local: isError, number, isHighlighted, isThemeLocked and
// isAutofilled must not trigger a refetch, so App's contentSigOf is not reused.
function gridSigOf(grid, gridSize) {
  if (!Array.isArray(grid)) return JSON.stringify([gridSize, null]);
  return JSON.stringify([
    gridSize,
    grid.map((row) =>
      Array.isArray(row)
        ? row.map((cell) => {
            if (typeof cell === 'string') return cell === '#' ? ['', true] : [cell === '.' ? '' : cell, false];
            return [(cell && cell.letter) || '', !!(cell && cell.isBlack)];
          })
        : row
    ),
  ]);
}

const SUPERSEDED_MSG = 'Suggestions updated for the changed grid.';

function ThemeWordsPanel({ grid, gridSize, docId, onApplyPlacement, onClose, editingPaused = false }) {
  const [file, setFile] = useState(null);
  const [themeWords, setThemeWords] = useState([]);
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);
  const [selectedWord, setSelectedWord] = useState(null);
  const [applyingAll, setApplyingAll] = useState(false);
  const fileInputRef = useRef(null);

  // novice-readiness spec 0.2.7 §3.8 (TH2b): the signature the showing list was
  // fetched with, the latest request's token, and the live grid signature.
  const gridSig = gridSigOf(grid, gridSize);
  const gridSigRef = useRef(gridSig);
  gridSigRef.current = gridSig;
  const listSigRef = useRef(null);
  const requestTokenRef = useRef(0);

  // novice-readiness spec 0.2.8 §3.8 (F1): Apply All stops sending once the panel
  // is closed (unmounted).
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    // Validate file size (max 1MB)
    if (selectedFile.size > 1024 * 1024) {
      toast.error('File too large (max 1MB)');
      return;
    }

    setFile(selectedFile);

    // Read file content
    const reader = new FileReader();
    reader.onload = (event) => {
      handleFileContent(event.target.result);
    };
    reader.onerror = () => {
      toast.error('Failed to read file');
    };
    reader.readAsText(selectedFile);
  };

  const handleFileContent = async (content) => {
    setLoading(true);
    setValidationErrors([]);

    try {
      // Upload to backend for parsing and validation
      const data = await api.themeUpload({
        content: content,
        gridSize: gridSize
      });

      // Check validation
      if (!data.validation.valid) {
        setValidationErrors(data.validation.errors);
        toast.error(`Invalid theme words: ${data.validation.errors[0]}`);
        setLoading(false);
        return;
      }

      // Show warnings if any
      if (data.validation.warnings.length > 0) {
        data.validation.warnings.forEach(warning => {
          toast(warning, { icon: '⚠️', duration: 4000 });
        });
      }

      setThemeWords(data.words);
      toast.success(`Loaded ${data.count} theme words`);

      // Auto-analyze placements
      await analyzePlacements(data.words);

    } catch (error) {
      console.error('Error uploading theme words:', error);
      toast.error('Failed to upload theme words');
    } finally {
      setLoading(false);
    }
  };

  // `silent` is the grid-change refetch (PD-6-G16): no loading overlay, no success toast.
  const analyzePlacements = async (words, { silent = false } = {}) => {
    // novice-readiness spec 0.2.8 §3.8 (G#77-ThemeWordsPanel.jsx:133): the signature
    // comes from the grid this request sends, not from a ref read after an await.
    const requestSig = gridSigOf(grid, gridSize);
    const token = ++requestTokenRef.current;
    if (!silent) setLoading(true);

    // Convert frontend grid format to backend format if needed
    const convertGrid = (frontendGrid) => {
      if (!frontendGrid) return null;

      // If grid is already in the right format (array of arrays of strings), use it
      if (Array.isArray(frontendGrid) && Array.isArray(frontendGrid[0])) {
        if (typeof frontendGrid[0][0] === 'string') {
          return frontendGrid;
        }

        // Convert from object format to string format
        return frontendGrid.map(row =>
          row.map(cell => {
            if (!cell) return '.';
            if (cell === '#' || cell.isBlack) return '#';
            if (cell.letter) return cell.letter;
            return '.';
          })
        );
      }
      return frontendGrid;
    };

    try {
      const data = await api.themeSuggestPlacements({
        themeWords: words || themeWords,
        gridSize: gridSize,
        existingGrid: convertGrid(grid),
        maxSuggestions: 3
      });

      // A response that is not for the latest request, or (refetch) not for the
      // latest grid signature, is dropped (novice-readiness spec 0.2.7 §3.8 (TH2b)).
      if (token !== requestTokenRef.current) return;
      if (silent && requestSig !== gridSigRef.current) return;

      // Ensure suggestions are in correct format
      if (data.suggestions && Array.isArray(data.suggestions)) {
        listSigRef.current = requestSig;
        setSuggestions(data.suggestions);
        if (!silent) {
          toast.success(`Found placement suggestions for ${data.suggestions.length} words!`);
        }
      } else {
        console.error('Invalid suggestions format:', data.suggestions);
        toast.error('Received invalid placement data');
      }

    } catch (error) {
      if (token !== requestTokenRef.current) return;
      console.error('Error analyzing placements:', error);
      const errorMsg = error.message || 'Failed to analyze placements';
      toast.error(errorMsg);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  // A list is superseded while the grid signature differs from the one it was
  // fetched with (derived, not a timer flag): novice-readiness spec 0.2.7 §3.8 (TH2b).
  const isSuperseded = () => listSigRef.current !== gridSigRef.current;

  // novice-readiness spec 0.2.7 §3.8 (TH2b, PD-6-G13/G15): while suggestions show,
  // a grid change refetches for the same words after the debounce; suspended while
  // Apply All runs, then one refetch if the grid differs from the list's.
  useEffect(() => {
    if (!suggestions || applyingAll) return undefined;
    if (listSigRef.current === gridSig) return undefined;
    const timer = setTimeout(() => {
      analyzePlacements(themeWords, { silent: true });
    }, SUGGESTION_REFETCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // analyzePlacements and themeWords are read at fire time; the triggers are these.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gridSig, suggestions, applyingAll]);

  const handleApplyPlacement = async (wordData, suggestionIndex) => {
    const suggestion = wordData.suggestions[suggestionIndex];

    if (isSuperseded()) {
      toast(SUPERSEDED_MSG);
      return;
    }

    // novice-readiness spec 0.2.8 §3.8 (F1, F4): the grid and document this request is sent under.
    const sentGrid = grid;
    const requestDocId = docId;
    try {
      // Apply placement to grid
      const data = await api.themeApplyPlacement({
        grid: sentGrid,
        placement: {
          word: suggestion.word,
          row: suggestion.row,
          col: suggestion.col,
          direction: suggestion.direction
        }
      });

      // Update parent grid
      // A `false` return means App dropped the reply (novice-readiness spec 0.2.8 §3.8,
      // PD-6-G12); a caller that returns nothing is treated as applied.
      if (onApplyPlacement) {
        const applied = onApplyPlacement(data.grid, suggestion, { sentGrid, docId: requestDocId });
        if (applied === false) return;
      }

      toast.success(`Applied ${suggestion.word} to grid`);

    } catch (error) {
      console.error('Error applying placement:', error);
      toast.error(conflictText(error.details) || error.message || 'Failed to apply placement');
    }
  };

  // Apply all best placements at once
  const handleApplyAllPlacements = async () => {
    if (!suggestions || suggestions.length === 0) {
      toast.error('No placement suggestions available. Please analyze placements first.');
      return;
    }

    if (isSuperseded()) {
      toast(SUPERSEDED_MSG);
      return;
    }

    setApplyingAll(true);
    let successCount = 0;
    const skipped = []; // `WORD (reason)`, in suggestion order
    let currentGrid = grid; // Track grid state through applications
    const requestDocId = docId;

    toast.loading('Applying all theme words...', { id: 'apply-all' });

    for (const wordData of suggestions) {
      if (!mountedRef.current) break; // panel closed: send nothing further
      // Skip words with no valid placements
      if (!wordData.suggestions || wordData.suggestions.length === 0) {
        skipped.push(`${wordData.word} (no valid placement)`);
        continue;
      }

      // Get the best (first) suggestion
      const bestSuggestion = wordData.suggestions[0];

      // Skip if it has conflicts (WARNING in reasoning)
      if (bestSuggestion.reasoning && bestSuggestion.reasoning.includes('WARNING')) {
        skipped.push(
          `${wordData.word} (skipped due to conflicts: ${bestSuggestion.reasoning})`
        );
        continue;
      }

      try {
        // Apply this placement (word comes from wordData, not suggestion)
        const response = await api.themeApplyPlacement({
          grid: currentGrid,
          placement: {
            word: wordData.word,  // Use the actual word
            row: bestSuggestion.row,
            col: bestSuggestion.col,
            direction: bestSuggestion.direction
          }
        });

        if (response && response.grid) {
          const sentGrid = currentGrid; // the grid this word's request was built from
          currentGrid = response.grid; // Update grid for next placement

          // Update parent grid. `false` = App dropped the reply: the document the summary
          // would describe is gone, so stop and say nothing (spec 0.2.8 §3.8, PD-6-G12).
          if (onApplyPlacement) {
            const applied = onApplyPlacement(currentGrid, bestSuggestion, {
              sentGrid,
              docId: requestDocId,
            });
            if (applied === false) {
              toast.dismiss('apply-all');
              setApplyingAll(false);
              return;
            }
          }
          successCount++;
        }
      } catch (error) {
        skipped.push(`${wordData.word} (${describeApplyFailure(error)})`);
      }
    }

    setApplyingAll(false);

    // Show results: novice-readiness spec 0.2.7 §3.8 (TH3, PD-6-G19). N counts only
    // the words this action applied; every skipped word is listed with its reason.
    const skippedText = skipped.length > 0 ? ` Skipped: ${skipped.join('; ')}` : '';
    if (successCount > 0) {
      toast.success(`Applied ${successCount} theme words successfully!${skippedText}`, {
        id: 'apply-all',
      });
    } else {
      toast.error(`Could not apply any theme words${skippedText}`, { id: 'apply-all' });
    }
  };

  const handleMouseEnterSuggestion = (word, suggestionIndex) => {
    setSelectedWord({ word, suggestionIndex });
  };

  const handleMouseLeaveSuggestion = () => {
    setSelectedWord(null);
  };

  return (
    <div className="theme-words-panel">
      <div className="panel-header">
        <h2>🎯 Theme Words</h2>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="panel-content">
        {/* File Upload Section */}
        <div className="upload-section">
          <h3>Upload Theme Words</h3>
          <p className="help-text">
            Upload a text file with one word per line (e.g., partner's name, special dates)
          </p>

          <div className="file-upload">
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <button
              className="upload-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
            >
              📤 Choose File
            </button>
            {file && <span className="file-name">{file.name}</span>}
          </div>

          {validationErrors.length > 0 && (
            <div className="validation-errors">
              {validationErrors.map((error, i) => (
                <div key={i} className="error">{error}</div>
              ))}
            </div>
          )}
        </div>

        {/* Theme Words List */}
        {themeWords.length > 0 && (
          <div className="words-list">
            <h3>Loaded Words ({themeWords.length})</h3>
            <div className="words-chips">
              {themeWords.map((word, i) => (
                <span key={i} className="word-chip">
                  {word} <small>({word.length})</small>
                </span>
              ))}
            </div>
            {/* Manual analyze button if no suggestions yet */}
            {!suggestions && (
              <button
                className="analyze-btn"
                onClick={() => analyzePlacements(themeWords)}
                disabled={loading}
                style={{ marginTop: '10px', padding: '8px 16px' }}
              >
                📍 Analyze Placements
              </button>
            )}
          </div>
        )}

        {/* Placement Suggestions */}
        {suggestions && suggestions.length > 0 && (
          <div className="suggestions-section">
            <h3>Placement Suggestions</h3>
            <p className="help-text">
              Hover over suggestions to preview on grid. Click "Apply" to lock the word.
            </p>

            {/* Apply All Button */}
            <div className="apply-all-section">
              <button
                className="apply-all-btn"
                onClick={handleApplyAllPlacements}
                disabled={applyingAll || loading || editingPaused}
              >
                {applyingAll ? '⏳ Applying...' : '🚀 Apply All Best Placements'}
              </button>
              <p className="apply-all-hint">
                Automatically place all theme words with their best non-conflicting positions
              </p>
            </div>

            {suggestions.map((wordData, wordIdx) => (
              <div key={wordIdx} className="word-suggestions">
                <h4>{wordData.word} <small>({wordData.length} letters)</small></h4>

                {wordData.suggestions.length === 0 && (
                  <div className="no-suggestions">
                    ⚠️ No valid placements found for this word
                  </div>
                )}

                {wordData.suggestions.map((suggestion, sugIdx) => (
                  <div
                    key={sugIdx}
                    className="suggestion-card"
                    onMouseEnter={() => handleMouseEnterSuggestion(wordData.word, sugIdx)}
                    onMouseLeave={() => handleMouseLeaveSuggestion()}
                  >
                    <div className="suggestion-header">
                      <span className="placement-info">
                        Row {suggestion.row}, Col {suggestion.col} ({suggestion.direction})
                      </span>
                      <span className={`score score-${Math.floor(suggestion.score / 20)}`}>
                        {suggestion.score}/100
                      </span>
                    </div>

                    <div className="reasoning">
                      {suggestion.reasoning}
                    </div>

                    <button
                      className="apply-btn"
                      disabled={editingPaused}
                      onClick={() => handleApplyPlacement(wordData, sugIdx)}
                    >
                      ✓ Apply This Placement
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Analyzing placements...</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ThemeWordsPanel;
