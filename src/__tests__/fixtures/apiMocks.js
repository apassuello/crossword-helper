/**
 * Mock Service Worker (MSW) handlers for API mocking
 *
 * This file defines mock responses for all 30+ API endpoints.
 * Tests can override these defaults for specific scenarios.
 */

import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { gridToCliFormat } from './gridFixtures';

// Base API URL — relative paths to match jsdom URL resolution
const API_BASE = '/api';

/**
 * Mock API handlers
 */
export const handlers = [
  // Health check
  http.get(`${API_BASE}/health`, () => {
    return HttpResponse.json({
      status: 'healthy',
      version: '0.2.0',
      architecture: 'cli-backend',
      components: {
        cli_adapter: 'ok',
        api_server: 'ok',
      },
    });
  }),

  // Pattern search
  http.post(`${API_BASE}/pattern`, async ({ request }) => {
    const body = await request.json();
    const pattern = body.pattern || 'C?T';

    return HttpResponse.json({
      results: [
        { word: 'CAT', score: 95, source: 'comprehensive' },
        { word: 'COT', score: 92, source: 'comprehensive' },
        { word: 'CUT', score: 90, source: 'comprehensive' },
      ],
      meta: {
        total: 3,
        pattern,
        algorithm: body.algorithm || 'trie',
      },
    });
  }),

  // Pattern search with progress (SSE)
  http.post(`${API_BASE}/pattern/with-progress`, async () => {
    return HttpResponse.json({
      task_id: 'test-pattern-123',
      progress_url: '/api/progress/test-pattern-123',
    }, { status: 202 });
  }),

  // Grid numbering
  http.post(`${API_BASE}/number`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      grid: body.grid,
      numbered: true,
      word_count: 42,
    });
  }),

  // Text normalization
  http.post(`${API_BASE}/normalize`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      normalized: (body.text || '').toUpperCase().replace(/[^A-Z]/g, ''),
      original: body.text,
    });
  }),

  // Grid fill (direct)
  http.post(`${API_BASE}/fill`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      grid: body.grid, // Return same grid (in real scenario, would be filled)
      slots_filled: 42,
      total_slots: 50,
      time_elapsed: 12.5,
    });
  }),

  // Grid fill with progress (SSE)
  http.post(`${API_BASE}/fill/with-progress`, async ({ request }) => {
    const body = await request.json();
    const taskId = `test-fill-${Date.now()}`;

    return HttpResponse.json({
      task_id: taskId,
      progress_url: `/api/progress/${taskId}`,
    }, { status: 202 });
  }),

  // Pause autofill
  http.post(`${API_BASE}/fill/pause/:taskId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      task_id: params.taskId,
      message: 'Pause signal sent',
    });
  }),

  // Cancel autofill
  http.post(`${API_BASE}/fill/cancel/:taskId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      task_id: params.taskId,
      state_saved: true,
      state_path: `/tmp/state-${params.taskId}.json.gz`,
    });
  }),

  // Resume autofill
  http.post(`${API_BASE}/fill/resume`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      task_id: `test-resume-${Date.now()}`,
      progress_url: '/api/progress/test-resume-123',
      resumed_from: body.state_path,
    }, { status: 202 });
  }),

  // Get saved state
  http.get(`${API_BASE}/fill/state/:taskId`, ({ params }) => {
    return HttpResponse.json({
      task_id: params.taskId,
      slots_filled: 25,
      total_slots: 50,
      progress: 50,
      timestamp: new Date().toISOString(),
    });
  }),

  // Delete saved state
  http.delete(`${API_BASE}/fill/state/:taskId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      task_id: params.taskId,
      deleted: true,
    });
  }),

  // List saved states
  http.get(`${API_BASE}/fill/states`, () => {
    return HttpResponse.json({
      states: [
        {
          task_id: 'state-1',
          slots_filled: 30,
          total_slots: 50,
          age_hours: 2,
        },
      ],
    });
  }),

  // Cleanup old states
  http.post(`${API_BASE}/fill/states/cleanup`, () => {
    return HttpResponse.json({
      deleted_count: 5,
      freed_mb: 12.5,
    });
  }),

  // Edit summary
  http.post(`${API_BASE}/fill/edit-summary`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      edits: {
        added: 3,
        removed: 1,
        changed: 2,
      },
      conflicts: [],
      warnings: [],
    });
  }),

  // Progress stream (SSE)
  http.get(`${API_BASE}/progress/:taskId`, ({ params }) => {
    // Return SSE-formatted data
    const messages = [
      { type: 'start', progress: 0, message: 'Starting...' },
      { type: 'progress', progress: 50, message: 'Filling slots...' },
      { type: 'complete', progress: 100, message: 'Complete', success: true },
    ];

    const sseData = messages.map(msg =>
      `data: ${JSON.stringify(msg)}\n\n`
    ).join('');

    return new HttpResponse(sseData, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
    });
  }),

  // Black square suggestions
  http.post(`${API_BASE}/grid/suggest-black-square`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      suggestions: [
        {
          row: 5,
          col: 5,
          score: 85,
          reasoning: 'Improves word distribution',
          symmetric_position: { row: 9, col: 9 },
        },
      ],
    });
  }),

  // Apply black squares
  http.post(`${API_BASE}/grid/apply-black-squares`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      grid: body.grid, // Return modified grid
      applied: 2, // Primary + symmetric
    });
  }),

  // Validate grid
  http.post(`${API_BASE}/grid/validate`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      valid: true,
      word_count: 42,
      black_square_percentage: 15.5,
      errors: [],
      warnings: [],
    });
  }),

  // Theme upload
  http.post(`${API_BASE}/theme/upload`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      words: ['BIRTHDAY', 'CELEBRATION'],
      valid_count: 2,
      invalid_words: [],
    });
  }),

  // Theme placement suggestions
  http.post(`${API_BASE}/theme/suggest-placements`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      placements: [
        {
          word: 'BIRTHDAY',
          row: 0,
          col: 0,
          direction: 'across',
          score: 90,
          conflicts: [],
        },
      ],
    });
  }),

  // Validate theme words
  http.post(`${API_BASE}/theme/validate`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      valid_words: body.words || [],
      invalid_words: [],
      warnings: [],
    });
  }),

  // Apply theme placement
  http.post(`${API_BASE}/theme/apply-placement`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      grid: body.grid, // Return grid with theme word
      word: body.word,
      locked_cells: 8,
    });
  }),

  // List wordlists
  http.get(`${API_BASE}/wordlists`, () => {
    return HttpResponse.json({
      wordlists: [
        {
          name: 'comprehensive',
          category: 'core',
          word_count: 454321,
          description: 'Comprehensive word list',
        },
        {
          name: 'themed',
          category: 'themed',
          word_count: 5000,
          description: 'Themed words',
        },
      ],
    });
  }),

  // Get wordlist
  http.get(`${API_BASE}/wordlists/:name`, ({ params }) => {
    return HttpResponse.json({
      name: params.name,
      words: ['CAT', 'DOG', 'BIRD'],
      word_count: 3,
      category: 'core',
    });
  }),

  // Create wordlist
  http.post(`${API_BASE}/wordlists/:name`, async ({ params, request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      name: params.name,
      word_count: body.words?.length || 0,
    }, { status: 201 });
  }),

  // Update wordlist
  http.put(`${API_BASE}/wordlists/:name`, async ({ params, request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      name: params.name,
      word_count: 100,
    });
  }),

  // Delete wordlist
  http.delete(`${API_BASE}/wordlists/:name`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      name: params.name,
      deleted: true,
    });
  }),

  // Wordlist stats
  http.get(`${API_BASE}/wordlists/:name/stats`, ({ params }) => {
    return HttpResponse.json({
      name: params.name,
      word_count: 454321,
      avg_length: 7.5,
      min_length: 3,
      max_length: 15,
      by_length: {
        3: 1000,
        4: 2000,
        5: 3000,
      },
    });
  }),

  // Search wordlists
  http.post(`${API_BASE}/wordlists/search`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      results: [
        { word: 'CAT', source: 'comprehensive', score: 95 },
      ],
    });
  }),

  // Import wordlist
  http.post(`${API_BASE}/wordlists/import`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      name: body.name || 'imported',
      word_count: 100,
    }, { status: 201 });
  }),
];

/**
 * Create MSW server instance
 */
export const server = setupServer(...handlers);

/**
 * Helper to add custom handlers in tests
 */
export function mockApiEndpoint(method, path, response, status = 200) {
  const fullPath = path.startsWith('http') ? path : `${API_BASE}${path}`;

  const httpMethod = http[method.toLowerCase()];
  if (!httpMethod) {
    throw new Error(`Invalid HTTP method: ${method}`);
  }

  server.use(
    httpMethod(fullPath, () => {
      return HttpResponse.json(response, { status });
    })
  );
}

/**
 * Helper to simulate API errors
 */
export function mockApiError(method, path, status = 500, message = 'Internal Server Error') {
  const fullPath = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const httpMethod = http[method.toLowerCase()];

  server.use(
    httpMethod(fullPath, () => {
      return HttpResponse.json(
        { error: message, code: status },
        { status }
      );
    })
  );
}

export default { server, handlers, mockApiEndpoint, mockApiError };
