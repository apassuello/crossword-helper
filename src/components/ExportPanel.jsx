import React, { useState } from 'react';
import './ExportPanel.scss';
import ProgressIndicator from './ProgressIndicator';

function ExportPanel({ grid, gridSize, numbering }) {
  const [exportFormat, setExportFormat] = useState('json');
  const [includeClues, setIncludeClues] = useState(false);
  const [preview, setPreview] = useState(null);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    if (!grid || isExporting) return;

    setIsExporting(true);

    const gridData = {
      size: gridSize,
      grid: grid.map(row => row.map(cell =>
        cell.isBlack ? '#' : (cell.letter || '.')
      )),
      numbering: numbering
    };

    // Add a small delay to show the progress indicator
    setTimeout(() => {
      if (exportFormat === 'json') {
        const json = JSON.stringify(gridData, null, 2);
        downloadFile('crossword.json', json, 'application/json');
      } else if (exportFormat === 'html') {
        const html = generateHTML(gridData);
        downloadFile('crossword.html', html, 'text/html');
      } else if (exportFormat === 'text') {
        const text = generateText(gridData);
        downloadFile('crossword.txt', text, 'text/plain');
      }
      setIsExporting(false);
    }, 500);
  };

  const downloadFile = (filename, content, mimeType) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const generateHTML = (gridData) => {
    let html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Crossword Puzzle</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
    .grid { border-collapse: collapse; margin: 20px auto; }
    .grid td {
      width: 30px; height: 30px; border: 1px solid #333; text-align: center;
      position: relative; font-size: 18px; font-weight: bold;
    }
    .grid td.black { background: #333; }
    .grid td .number {
      position: absolute; top: 2px; left: 2px; font-size: 10px; font-weight: normal;
    }
    h1 { text-align: center; }
  </style>
</head>
<body>
  <h1>Crossword Puzzle</h1>
  <table class="grid">`;

    for (let row = 0; row < gridData.size; row++) {
      html += '<tr>';
      for (let col = 0; col < gridData.size; col++) {
        const cell = gridData.grid[row][col];
        const number = gridData.numbering[`${row},${col}`];

        if (cell === '#') {
          html += '<td class="black"></td>';
        } else {
          html += '<td>';
          if (number) {
            html += `<span class="number">${number}</span>`;
          }
          if (cell !== '.') {
            html += cell;
          }
          html += '</td>';
        }
      }
      html += '</tr>';
    }

    html += '</table></body></html>';
    return html;
  };

  const generateText = (gridData) => {
    let text = `Crossword Puzzle (${gridData.size}×${gridData.size})\n\n`;

    for (let row = 0; row < gridData.size; row++) {
      for (let col = 0; col < gridData.size; col++) {
        const cell = gridData.grid[row][col];
        if (cell === '#') {
          text += '■ ';
        } else if (cell === '.') {
          text += '_ ';
        } else {
          text += cell + ' ';
        }
      }
      text += '\n';
    }

    return text;
  };

  const handlePreview = () => {
    if (!grid) return;

    const gridData = {
      size: gridSize,
      grid: grid.map(row => row.map(cell =>
        cell.isBlack ? '#' : (cell.letter || '.')
      )),
      numbering: numbering
    };

    if (exportFormat === 'json') {
      setPreview(JSON.stringify(gridData, null, 2));
    } else if (exportFormat === 'text') {
      setPreview(generateText(gridData));
    } else {
      setPreview('HTML preview not available - use Export to download');
    }
  };

  return (
    <div className="export-panel">
      <h2>Export Grid</h2>

      <div className="export-options">
        <div className="format-selector">
          <label htmlFor="export-format">Export Format</label>
          <select
            id="export-format"
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
          >
            <option value="json">JSON (for reimport)</option>
            <option value="html">HTML (printable)</option>
            <option value="text">Text (simple)</option>
            <option value="pdf" disabled>PDF (coming soon)</option>
            <option value="puz" disabled>.puz (coming soon)</option>
          </select>
        </div>

        <div className="export-settings">
          <label htmlFor="include-clues">
            <input
              id="include-clues"
              type="checkbox"
              checked={includeClues}
              onChange={(e) => setIncludeClues(e.target.checked)}
              disabled
            />
            Include clues (if available)
          </label>
        </div>

        <div className="export-actions">
          <button onClick={handlePreview} className="preview-btn">
            Preview
          </button>
          <button onClick={handleExport} className="export-btn" disabled={isExporting}>
            {isExporting ? 'Exporting...' : 'Export'}
          </button>
        </div>
      </div>

      {isExporting && (
        <div style={{marginTop: '1rem'}}>
          <ProgressIndicator
            type="spinner"
            message={`Generating ${exportFormat.toUpperCase()} file...`}
            size="medium"
            color="primary"
          />
        </div>
      )}

      {preview && (
        <div className="preview-section">
          <h3>Preview</h3>
          <pre className="preview-content">
            {preview}
          </pre>
        </div>
      )}

      <div className="export-info">
        <h3>Format Information</h3>
        <dl>
          <dt>JSON</dt>
          <dd>Complete grid data that can be reimported into this tool</dd>

          <dt>HTML</dt>
          <dd>Printable webpage with styled grid</dd>

          <dt>Text</dt>
          <dd>Simple text representation using ■ for black squares</dd>

          <dt>PDF</dt>
          <dd>Professional print-ready format (coming soon)</dd>

          <dt>.puz</dt>
          <dd>Compatible with crossword solving software (coming soon)</dd>
        </dl>
      </div>
    </div>
  );
}

export default ExportPanel;