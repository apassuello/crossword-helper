import React, { useState, useRef } from 'react';
import './ImportPanel.scss';
import ProgressIndicator from './ProgressIndicator';

function ImportPanel({ onImport, currentGridSize }) {
  const [importMethod, setImportMethod] = useState('file'); // 'file' or 'paste'
  const [jsonInput, setJsonInput] = useState('');
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef(null);

  /**
   * Convert CLI grid format to frontend format
   * CLI: ["A", "B", "#", "."]
   * Frontend: {letter: "A", isBlack: false, number: null, isError: false, isHighlighted: false}
   */
  const convertGridFormat = (cliGrid, size) => {
    const frontendGrid = [];

    for (let row = 0; row < size; row++) {
      const frontendRow = [];
      for (let col = 0; col < size; col++) {
        const cliCell = cliGrid[row][col];
        const cell = {
          letter: '',
          isBlack: false,
          number: null,
          isError: false,
          isHighlighted: false
        };

        if (cliCell === '#') {
          cell.isBlack = true;
        } else if (cliCell !== '.' && cliCell !== '') {
          cell.letter = cliCell;
        }

        frontendRow.push(cell);
      }
      frontendGrid.push(frontendRow);
    }

    return frontendGrid;
  };

  /**
   * Validate and parse imported JSON
   */
  const validateImportedData = (data) => {
    // Check required fields
    if (!data.size || !data.grid) {
      throw new Error('Invalid grid data: missing "size" or "grid" fields');
    }

    // Validate size
    const size = parseInt(data.size);
    if (isNaN(size) || size < 3 || size > 25) {
      throw new Error(`Invalid grid size: ${data.size}. Must be between 3 and 25.`);
    }

    // Validate grid is array
    if (!Array.isArray(data.grid)) {
      throw new Error('Invalid grid data: "grid" must be an array');
    }

    // Validate grid dimensions
    if (data.grid.length !== size) {
      throw new Error(`Grid height (${data.grid.length}) doesn't match size (${size})`);
    }

    for (let i = 0; i < data.grid.length; i++) {
      if (!Array.isArray(data.grid[i])) {
        throw new Error(`Grid row ${i} is not an array`);
      }
      if (data.grid[i].length !== size) {
        throw new Error(`Grid row ${i} has ${data.grid[i].length} cells, expected ${size}`);
      }
    }

    // Validate cell format (must be strings)
    for (let row = 0; row < size; row++) {
      for (let col = 0; col < size; col++) {
        const cell = data.grid[row][col];
        if (typeof cell !== 'string') {
          throw new Error(`Invalid cell at (${row}, ${col}): must be a string, got ${typeof cell}`);
        }
        // Valid values: '#' (black), '.' (empty), or A-Z (letter)
        if (cell !== '#' && cell !== '.' && cell !== '' && !/^[A-Z]$/.test(cell)) {
          throw new Error(`Invalid cell value at (${row}, ${col}): "${cell}". Must be '#', '.', or A-Z.`);
        }
      }
    }

    return { size, grid: data.grid, numbering: data.numbering || {} };
  };

  /**
   * Handle file upload
   */
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Check file extension
    if (!file.name.endsWith('.json')) {
      setError('Invalid file type. Please select a .json file.');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setPreview(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const jsonText = e.target.result;
        const data = JSON.parse(jsonText);
        const validated = validateImportedData(data);

        // Generate preview
        const previewText = `Size: ${validated.size}×${validated.size}\nCells: ${validated.size * validated.size}\nFilled: ${countFilledCells(validated.grid)}`;
        setPreview({
          text: previewText,
          data: validated
        });
        setIsProcessing(false);
      } catch (err) {
        setError(`Failed to parse file: ${err.message}`);
        setPreview(null);
        setIsProcessing(false);
      }
    };

    reader.onerror = () => {
      setError('Failed to read file');
      setIsProcessing(false);
    };

    reader.readAsText(file);
  };

  /**
   * Handle JSON paste
   */
  const handlePasteValidation = () => {
    if (!jsonInput.trim()) {
      setError('Please paste JSON data');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setPreview(null);

    try {
      const data = JSON.parse(jsonInput);
      const validated = validateImportedData(data);

      // Generate preview
      const previewText = `Size: ${validated.size}×${validated.size}\nCells: ${validated.size * validated.size}\nFilled: ${countFilledCells(validated.grid)}`;
      setPreview({
        text: previewText,
        data: validated
      });
      setIsProcessing(false);
    } catch (err) {
      setError(`Invalid JSON: ${err.message}`);
      setPreview(null);
      setIsProcessing(false);
    }
  };

  /**
   * Count filled cells for preview
   */
  const countFilledCells = (grid) => {
    let count = 0;
    for (const row of grid) {
      for (const cell of row) {
        if (cell !== '#' && cell !== '.' && cell !== '') {
          count++;
        }
      }
    }
    return count;
  };

  /**
   * Handle import action
   */
  const handleImport = () => {
    if (!preview || !preview.data) {
      setError('No valid data to import. Please validate first.');
      return;
    }

    setIsProcessing(true);

    // Small delay to show processing state
    setTimeout(() => {
      try {
        const { size, grid, numbering } = preview.data;

        // Convert to frontend format
        const frontendGrid = convertGridFormat(grid, size);

        // Call the onImport callback
        onImport({
          grid: frontendGrid,
          size: size,
          numbering: numbering
        });

        // Reset state
        setPreview(null);
        setJsonInput('');
        setError(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        setIsProcessing(false);
      } catch (err) {
        setError(`Import failed: ${err.message}`);
        setIsProcessing(false);
      }
    }, 300);
  };

  /**
   * Clear all state
   */
  const handleClear = () => {
    setJsonInput('');
    setPreview(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="import-panel">
      <h2>Import Grid</h2>

      <div className="import-options">
        <div className="method-selector">
          <label>Import Method</label>
          <div className="method-tabs">
            <button
              className={`method-tab ${importMethod === 'file' ? 'active' : ''}`}
              onClick={() => setImportMethod('file')}
            >
              Upload File
            </button>
            <button
              className={`method-tab ${importMethod === 'paste' ? 'active' : ''}`}
              onClick={() => setImportMethod('paste')}
            >
              Paste JSON
            </button>
          </div>
        </div>

        {importMethod === 'file' && (
          <div className="file-upload-section">
            <label htmlFor="file-upload" className="file-upload-label">
              Choose JSON file
            </label>
            <input
              id="file-upload"
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              className="file-upload-input"
            />
            <p className="file-upload-hint">
              Select a .json file exported from this tool
            </p>
          </div>
        )}

        {importMethod === 'paste' && (
          <div className="paste-section">
            <label htmlFor="json-paste">Paste JSON Data</label>
            <textarea
              id="json-paste"
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              placeholder='{"size": 11, "grid": [["A","B","#",...], ...]}'
              rows={8}
              className="json-textarea"
            />
            <button
              onClick={handlePasteValidation}
              className="validate-btn"
              disabled={!jsonInput.trim() || isProcessing}
            >
              Validate JSON
            </button>
          </div>
        )}

        {error && (
          <div className="error-message">
            <strong>Error:</strong> {error}
          </div>
        )}

        {isProcessing && (
          <div style={{ marginTop: '1rem' }}>
            <ProgressIndicator
              type="spinner"
              message="Processing..."
              size="medium"
              color="primary"
            />
          </div>
        )}

        {preview && (
          <div className="preview-section">
            <h3>Preview</h3>
            <pre className="preview-content">
              {preview.text}
            </pre>
            <div className="import-actions">
              <button onClick={handleClear} className="clear-btn">
                Clear
              </button>
              <button
                onClick={handleImport}
                className="import-btn"
                disabled={isProcessing}
              >
                {isProcessing ? 'Importing...' : 'Import Grid'}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="import-info">
        <h3>Import Instructions</h3>
        <dl>
          <dt>File Upload</dt>
          <dd>Select a .json file exported from this tool using "Export → JSON"</dd>

          <dt>Paste JSON</dt>
          <dd>Copy and paste JSON data directly from another source</dd>

          <dt>Format Requirements</dt>
          <dd>
            JSON must include "size" (number) and "grid" (2D array of strings).
            Cells should be: "#" (black), "." (empty), or A-Z (letter).
          </dd>

          <dt>Validation</dt>
          <dd>
            The tool validates grid dimensions, cell values, and format before import.
            Preview shows grid statistics before confirming import.
          </dd>
        </dl>
      </div>
    </div>
  );
}

export default ImportPanel;
