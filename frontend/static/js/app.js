/**
 * Crossword Helper - Main Application
 * Common utilities and API client
 */

const API_BASE = '/api';

/**
 * Make API request
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const json = await response.json();

        if (!response.ok) {
            throw new Error(json.error?.message || 'Request failed');
        }

        return json;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Show loading state
 */
function showLoading(containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '<div class="loading">Loading</div>';
}

/**
 * Show error message
 */
function showError(containerId, message) {
    const container = document.getElementById(containerId);
    container.innerHTML = `<div class="error">${escapeHtml(message)}</div>`;
}

/**
 * Clear results
 */
function clearResults(containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Initialize application
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('Crossword Helper initialized');

    // Health check
    apiRequest('/health')
        .then(data => console.log('API health:', data))
        .catch(err => console.error('API health check failed:', err));
});
