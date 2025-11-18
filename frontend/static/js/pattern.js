/**
 * Pattern matching UI controller
 *
 * This module handles the user interface for pattern-based word lookups,
 * including input validation, API calls, and result rendering.
 */

document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('pattern-input');
    const searchBtn = document.getElementById('pattern-search-btn');
    const clearBtn = document.getElementById('pattern-clear-btn');
    const resultsContainer = 'pattern-results';

    // Search on button click
    searchBtn.addEventListener('click', () => searchPattern());

    // Search on Enter key
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchPattern();
        }
    });

    // Clear results
    clearBtn.addEventListener('click', () => {
        input.value = '';
        clearResults(resultsContainer);
        input.focus();
    });

    /**
     * Search for pattern
     */
    async function searchPattern() {
        const pattern = input.value.trim().toUpperCase();

        if (!pattern) {
            showError(resultsContainer, 'Please enter a pattern');
            return;
        }

        showLoading(resultsContainer);

        try {
            const data = await apiRequest('/pattern', 'POST', {
                pattern,
                max_results: 20
            });

            displayResults(data);
        } catch (error) {
            showError(resultsContainer, error.message);
        }
    }

    /**
     * Display search results
     */
    function displayResults(data) {
        const container = document.getElementById(resultsContainer);

        if (!data.results || data.results.length === 0) {
            container.innerHTML = '<div class="error">No words found matching pattern</div>';
            return;
        }

        let html = `<div class="success">Found ${data.results.length} words:</div>`;

        data.results.forEach(result => {
            html += `
                <div class="word-card">
                    <span class="word-text">${escapeHtml(result.word)}</span>
                    <div class="word-meta">
                        <span class="score">Score: ${result.score}</span>
                        <span class="source-badge">${result.source}</span>
                        <span title="Common: ${result.letter_quality.common}, Uncommon: ${result.letter_quality.uncommon}">
                            ${result.length} letters
                        </span>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }
});
