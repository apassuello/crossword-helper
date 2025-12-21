import React from 'react';
import './ToolPanel.scss';

function ToolPanel({ gridSize, onSizeChange, onClearGrid, validationErrors, gridStats }) {
  return (
    <div className="tool-panel">
      <h2>Grid Tools</h2>

      <div className="tool-section">
        <h3>Grid Size</h3>
        <div className="size-selector">
          {[11, 15, 21].map(size => (
            <button
              key={size}
              className={`size-btn ${gridSize === size ? 'active' : ''}`}
              onClick={() => onSizeChange(size)}
            >
              {size}×{size}
            </button>
          ))}
        </div>
        <p className="help-text">
          Standard crossword sizes: 11×11 (easy), 15×15 (standard), 21×21 (Sunday)
        </p>
      </div>

      {gridStats && (
        <div className="tool-section">
          <h3>Grid Statistics</h3>
          <div className="stats-list">
            <div className="stat-item">
              <span className="stat-label">Total Cells:</span>
              <span className="stat-value">{gridStats.totalCells}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Black Squares:</span>
              <span className="stat-value">
                {gridStats.blackSquares} ({gridStats.blackSquarePercent}%)
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Filled:</span>
              <span className="stat-value">
                {gridStats.filledCells} ({gridStats.fillPercent}%)
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="tool-section">
        <h3>Validation</h3>
        {validationErrors.length === 0 ? (
          <div className="validation-success">
            ✓ Grid is valid
          </div>
        ) : (
          <div className="validation-errors">
            {validationErrors.map((error, idx) => (
              <div key={idx} className="error-item">
                • {error}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="tool-section">
        <h3>Actions</h3>
        <div className="action-buttons">
          <button onClick={onClearGrid} className="action-btn">
            Clear Grid
          </button>
          <button className="action-btn">
            Load Grid
          </button>
          <button className="action-btn">
            Save Grid
          </button>
        </div>
      </div>

      <div className="tool-section">
        <h3>NYT Standards</h3>
        <ul className="standards-list">
          <li>180° rotational symmetry required</li>
          <li>All letters must be checked (in both across and down)</li>
          <li>Minimum word length: 3 letters</li>
          <li>Black squares: typically 15-17% for 15×15</li>
          <li>Grid must be fully connected</li>
        </ul>
      </div>
    </div>
  );
}

export default ToolPanel;