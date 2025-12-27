import React, { useState, useRef } from 'react';
import toast from 'react-hot-toast';
import './ThemeWordsPanel.scss';

function ThemeWordsPanel({ grid, gridSize, onApplyPlacement, onClose }) {
  const [file, setFile] = useState(null);
  const [themeWords, setThemeWords] = useState([]);
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);
  const [selectedWord, setSelectedWord] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    // Validate file type
    if (!selectedFile.name.endsWith('.txt')) {
      toast.error('Please select a .txt file');
      return;
    }

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
      const response = await fetch('/api/theme/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: content,
          grid_size: gridSize
        })
      });

      if (!response.ok) {
        throw new Error('Failed to parse theme words');
      }

      const data = await response.json();

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

  const analyzePlacements = async (words) => {
    setLoading(true);

    try {
      const response = await fetch('/api/theme/suggest-placements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          theme_words: words || themeWords,
          grid_size: gridSize,
          existing_grid: grid,
          max_suggestions: 3
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to analyze placements');
      }

      const data = await response.json();
      setSuggestions(data.suggestions);
      toast.success('Found placement suggestions!');

    } catch (error) {
      console.error('Error analyzing placements:', error);
      toast.error(error.message || 'Failed to analyze placements');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPlacement = async (wordData, suggestionIndex) => {
    const suggestion = wordData.suggestions[suggestionIndex];

    try {
      // Apply placement to grid
      const response = await fetch('/api/theme/apply-placement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          grid: grid,
          placement: {
            word: suggestion.word,
            row: suggestion.row,
            col: suggestion.col,
            direction: suggestion.direction
          }
        })
      });

      if (!response.ok) {
        throw new Error('Failed to apply placement');
      }

      const data = await response.json();

      // Update parent grid
      if (onApplyPlacement) {
        onApplyPlacement(data.grid, suggestion);
      }

      toast.success(`Applied ${suggestion.word} to grid`);

    } catch (error) {
      console.error('Error applying placement:', error);
      toast.error('Failed to apply placement');
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
            Upload a .txt file with one word per line (e.g., partner's name, special dates)
          </p>

          <div className="file-upload">
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt"
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
          </div>
        )}

        {/* Placement Suggestions */}
        {suggestions && suggestions.length > 0 && (
          <div className="suggestions-section">
            <h3>Placement Suggestions</h3>
            <p className="help-text">
              Hover over suggestions to preview on grid. Click "Apply" to lock the word.
            </p>

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
