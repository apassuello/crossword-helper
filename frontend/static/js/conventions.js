/**
 * Convention normalization UI controller
 *
 * This module provides the interface for normalizing crossword entries
 * according to various publication standards and style guides.
 */

document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('convention-input');
    const normalizeBtn = document.getElementById('convention-normalize-btn');
    const clearBtn = document.getElementById('convention-clear-btn');
    const resultsContainer = 'convention-results';

    // Normalize on button click
    normalizeBtn.addEventListener('click', () => normalizeEntry());

    // Normalize on Enter key
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            normalizeEntry();
        }
    });

    // Clear results
    clearBtn.addEventListener('click', () => {
        input.value = '';
        clearResults(resultsContainer);
        input.focus();
    });

    /**
     * Normalize convention entry
     */
    async function normalizeEntry() {
        const text = input.value.trim();

        if (!text) {
            showError(resultsContainer, 'Please enter text to normalize');
            return;
        }

        showLoading(resultsContainer);

        try {
            const data = await apiRequest('/normalize', 'POST', {
                text
            });

            displayResults(data);
        } catch (error) {
            showError(resultsContainer, error.message);
        }
    }

    /**
     * Display normalization results
     */
    function displayResults(data) {
        const container = document.getElementById(resultsContainer);

        let html = '<div class="normalized-result">';
        html += `<div><strong>Original:</strong> ${escapeHtml(data.original)}</div>`;
        html += `<div class="normalized-text">${escapeHtml(data.normalized)}</div>`;
        html += '</div>';

        // Display rule info
        if (data.rule) {
            html += '<div class="rule-info">';
            html += `<div class="rule-type">Rule: ${data.rule.type}</div>`;
            html += `<div>${escapeHtml(data.rule.description)}</div>`;
            if (data.rule.explanation) {
                html += `<div style="margin-top: 8px;"><em>${escapeHtml(data.rule.explanation)}</em></div>`;
            }
            if (data.rule.examples && data.rule.examples.length > 0) {
                html += '<div style="margin-top: 12px;"><strong>Examples:</strong></div>';
                data.rule.examples.forEach(ex => {
                    html += `<div style="font-family: monospace; margin-left: 16px;">${escapeHtml(ex[0])} → ${escapeHtml(ex[1])}</div>`;
                });
            }
            html += '</div>';
        }

        // Display alternatives
        if (data.alternatives && data.alternatives.length > 0) {
            html += '<div class="alternatives">';
            html += '<h3>Alternative Forms:</h3>';
            data.alternatives.forEach(alt => {
                html += '<div class="alternative-item">';
                html += `<strong>${escapeHtml(alt.form)}</strong>`;
                html += `<div style="font-size: 0.9em; margin-top: 4px;">${escapeHtml(alt.note)}</div>`;
                html += '</div>';
            });
            html += '</div>';
        }

        container.innerHTML = html;
    }
});
