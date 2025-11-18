/**
 * Numbering validation UI controller
 *
 * This module manages the grid numbering interface, allowing users
 * to validate and generate crossword grid numbering schemes.
 */

document.addEventListener('DOMContentLoaded', () => {
    const gridInput = document.getElementById('grid-input');
    const numberBtn = document.getElementById('grid-number-btn');
    const clearBtn = document.getElementById('grid-clear-btn');
    const resultsContainer = 'grid-results';

    // Auto-number on button click
    numberBtn.addEventListener('click', () => autoNumberGrid());

    // Clear results
    clearBtn.addEventListener('click', () => {
        gridInput.value = '';
        clearResults(resultsContainer);
        gridInput.focus();
    });

    /**
     * Auto-number grid
     */
    async function autoNumberGrid() {
        const gridJson = gridInput.value.trim();

        if (!gridJson) {
            showError(resultsContainer, 'Please enter grid JSON');
            return;
        }

        let gridData;
        try {
            gridData = JSON.parse(gridJson);
        } catch (e) {
            showError(resultsContainer, 'Invalid JSON format');
            return;
        }

        showLoading(resultsContainer);

        try {
            const data = await apiRequest('/number', 'POST', gridData);
            displayResults(data);
        } catch (error) {
            showError(resultsContainer, error.message);
        }
    }

    /**
     * Display numbering results
     */
    function displayResults(data) {
        const container = document.getElementById(resultsContainer);

        let html = '<div class="success">Grid numbered successfully!</div>';

        // Display numbering
        html += '<div class="grid-display">';
        html += '<h3>Numbering:</h3>';
        html += '<pre>' + JSON.stringify(data.numbering, null, 2) + '</pre>';
        html += '</div>';

        // Display grid info
        if (data.grid_info) {
            html += '<div class="grid-info">';
            html += '<h3>Grid Analysis:</h3>';
            html += `<div class="grid-info-item">Size: ${data.grid_info.size[0]}×${data.grid_info.size[1]}</div>`;
            html += `<div class="grid-info-item">Black squares: ${data.grid_info.black_squares} (${data.grid_info.black_square_percentage}%)</div>`;
            html += `<div class="grid_info-item">White squares: ${data.grid_info.white_squares}</div>`;
            html += `<div class="grid-info-item">Estimated words: ${data.grid_info.word_count}</div>`;
            html += `<div class="grid-info-item">Meets NYT standards: ${data.grid_info.meets_nyt_standards ? '✓ Yes' : '✗ No'}</div>`;
            html += '</div>';
        }

        // Display validation results if present
        if (data.validation) {
            html += '<div class="grid-info">';
            html += '<h3>Validation:</h3>';
            if (data.validation.is_valid) {
                html += '<div class="success">✓ Numbering is correct</div>';
            } else {
                html += '<div class="error">✗ Found ' + data.validation.errors.length + ' errors:</div>';
                data.validation.errors.forEach(err => {
                    html += `<div class="error">${escapeHtml(err.message)}</div>`;
                });
            }
            html += '</div>';
        }

        container.innerHTML = html;
    }
});
