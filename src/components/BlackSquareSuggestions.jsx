import React, { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import './BlackSquareSuggestions.scss';

function BlackSquareSuggestions({
  grid,
  gridSize,
  problematicSlot,
  onApplySuggestion,
  onClose
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);

  useEffect(() => {
    if (problematicSlot) {
      fetchSuggestions();
    }
  }, [problematicSlot]);

  const fetchSuggestions = async () => {
    setLoading(true);

    try {
      const response = await axios.post('/api/grid/suggest-black-square', {
        grid: grid,
        grid_size: gridSize,
        problematic_slot: problematicSlot,
        max_suggestions: 3
      });

      const data = response.data;
      setSuggestions(data.suggestions || []);

      if (data.suggestions.length === 0) {
        toast('No viable black square positions found', { icon: '⚠️' });
      }

    } catch (error) {
      console.error('Error fetching black square suggestions:', error);
      const errorMsg = error.response?.data?.error || error.message || 'Failed to get suggestions';
      toast.error(errorMsg);
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleApplySuggestion = async (suggestion) => {
    try {
      const response = await axios.post('/api/grid/apply-black-squares', {
        grid: grid,
        primary: { row: suggestion.row, col: suggestion.col },
        symmetric: suggestion.symmetric_position
      });

      const data = response.data;

      // Notify parent component
      if (onApplySuggestion) {
        onApplySuggestion(data.grid, suggestion);
      }

      toast.success('Applied black square pair!');
      onClose();

    } catch (error) {
      console.error('Error applying black squares:', error);
      const errorMsg = error.response?.data?.error || error.message || 'Failed to apply black squares';
      toast.error(errorMsg);
    }
  };

  const handleMouseEnterSuggestion = (suggestion) => {
    setSelectedSuggestion(suggestion);
  };

  const handleMouseLeaveSuggestion = () => {
    setSelectedSuggestion(null);
  };

  const formatSlotInfo = () => {
    if (!problematicSlot) return '';

    const { row, col, direction, length, pattern, candidate_count } = problematicSlot;
    return `${direction === 'across' ? 'Across' : 'Down'} at Row ${row}, Col ${col} - ${length} letters (${pattern})`;
  };

  if (!problematicSlot) return null;

  return (
    <div className="black-square-modal-overlay" onClick={onClose}>
      <div className="black-square-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>⬛ Strategic Black Square Placement</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="modal-content">
          {/* Problem Description */}
          <div className="problem-section">
            <h3>Problematic Slot</h3>
            <div className="slot-info">
              <div className="slot-detail">
                <span className="label">Position:</span>
                <span className="value">{formatSlotInfo()}</span>
              </div>
              <div className="slot-detail">
                <span className="label">Pattern:</span>
                <span className="value pattern-text">{problematicSlot.pattern}</span>
              </div>
              <div className="slot-detail">
                <span className="label">Candidates:</span>
                <span className="value candidates-count">
                  {problematicSlot.candidate_count || 0}
                  {problematicSlot.candidate_count === 0 && ' (STUCK!)'}
                </span>
              </div>
            </div>
            <p className="help-text">
              This slot has very few valid words. Consider placing a "cheater square"
              (black square) to split it into smaller, more fillable segments.
            </p>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="loading-section">
              <div className="spinner"></div>
              <p>Analyzing optimal black square positions...</p>
            </div>
          )}

          {/* Suggestions */}
          {!loading && suggestions.length > 0 && (
            <div className="suggestions-section">
              <h3>Top Suggestions</h3>
              <p className="help-text">
                Hover to preview, click "Apply" to place the black square pair (maintains symmetry).
              </p>

              {suggestions.map((suggestion, idx) => (
                <div
                  key={idx}
                  className="suggestion-card"
                  onMouseEnter={() => handleMouseEnterSuggestion(suggestion)}
                  onMouseLeave={() => handleMouseLeaveSuggestion()}
                >
                  <div className="suggestion-header">
                    <div className="position-info">
                      <span className="rank">#{idx + 1}</span>
                      <span className="position">
                        Position {suggestion.position} → Split into {suggestion.left_length}+{suggestion.right_length} letters
                      </span>
                    </div>
                    <div className={`score score-${Math.floor(suggestion.score / 200)}`}>
                      {suggestion.score}
                    </div>
                  </div>

                  <div className="grid-positions">
                    <div className="position-pair">
                      <div className="position-item">
                        <span className="icon">⬛</span>
                        <span>Primary: ({suggestion.row}, {suggestion.col})</span>
                      </div>
                      <div className="position-item">
                        <span className="icon">⬛</span>
                        <span>
                          Symmetric: ({suggestion.symmetric_position.row}, {suggestion.symmetric_position.col})
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="reasoning">
                    {suggestion.reasoning}
                  </div>

                  <div className="metrics">
                    <div className="metric">
                      <span className="metric-label">New word count:</span>
                      <span className="metric-value">{suggestion.new_word_count}</span>
                    </div>
                    <div className="metric">
                      <span className="metric-label">Constraint reduction:</span>
                      <span className="metric-value">{suggestion.constraint_reduction}/5</span>
                    </div>
                  </div>

                  <button
                    className="apply-btn"
                    onClick={() => handleApplySuggestion(suggestion)}
                  >
                    ✓ Apply This Placement
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* No Suggestions */}
          {!loading && suggestions.length === 0 && (
            <div className="no-suggestions">
              <p>⚠️ No viable black square positions found for this slot.</p>
              <p className="help-text">
                The slot may be too short to split, or all positions would violate grid constraints.
                Consider manually adjusting the grid or changing existing black squares.
              </p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="cancel-btn" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default BlackSquareSuggestions;
