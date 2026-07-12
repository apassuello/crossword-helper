/**
 * API client — the ONLY module allowed to call fetch / EventSource.
 * Every function corresponds to a real backend endpoint (see the plan's
 * "Authoritative endpoint contracts" table). Each returns parsed JSON or
 * throws `ApiError{status, code, message, details}`.
 *
 * All URL literals and payload shapes live here and nowhere else.
 */

export class ApiError extends Error {
  constructor({ status, code, message, details }) {
    super(message || code || 'Request failed');
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** Drop keys whose value is `undefined` so optional fields aren't serialized. */
function clean(obj) {
  const out = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined) out[k] = v;
  }
  return out;
}

/** Rule 2: unparseable/empty body is swallowed to {} — never throws on parse. */
async function parseBody(response) {
  try {
    const text = await response.text();
    if (!text) return {};
    return JSON.parse(text);
  } catch {
    return {};
  }
}

/**
 * Normalize an error response into an ApiError.
 * Rule 3: flat-string (`{error:"msg"}`) and envelope (`{error:{code,message}}`)
 *         bodies both yield a coherent ApiError.
 * Rule 4: non-envelope code synthesis — 409 -> "UNSOLVABLE_EDITS", else "HTTP_<status>".
 * Rule 5: `details` from top-level `data.details` OR nested `err.details`.
 */
function normalizeError(status, data) {
  const body = data || {};
  const err = body.error;
  let code;
  let message;
  let details = body.details; // top-level first (rule 5)

  if (err && typeof err === 'object') {
    code = err.code;
    message = err.message;
    if (details === undefined) details = err.details; // nested fallback (rule 5)
  } else if (typeof err === 'string') {
    message = err;
  }

  if (!code) {
    code = status === 409 ? 'UNSOLVABLE_EDITS' : `HTTP_${status}`; // rule 4
  }

  return new ApiError({ status, code, message, details });
}

/** Core request. `body === undefined` -> no body, no Content-Type header. */
async function request(method, path, body) {
  const opts = { method };
  if (body !== undefined) {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, opts);
  } catch (e) {
    // Rule 1: network failure (fetch rejects)
    throw new ApiError({
      status: 0,
      code: 'NETWORK',
      message: (e && e.message) || 'Network request failed',
    });
  }

  const data = await parseBody(response);
  if (!response.ok) throw normalizeError(response.status, data);
  return data;
}

const get = (path) => request('GET', path);
const post = (path, body) => request('POST', path, body);
const put = (path, body) => request('PUT', path, body);
const del = (path) => request('DELETE', path);

// The Interfaces block is the single binding reference for exported names.
// Two contracts-table rows are intentionally NOT surfaced here (no consumer in
// M1; names would be invented): patternWithProgress (/api/pattern/with-progress)
// and constraintsImpact (/api/constraints/impact). Add when a task needs them.
export const api = {
  /** GET /api/health — returns the body even on 503 (rule 6: degraded is data). */
  async health() {
    let response;
    try {
      response = await fetch('/api/health');
    } catch (e) {
      throw new ApiError({
        status: 0,
        code: 'NETWORK',
        message: (e && e.message) || 'Network request failed',
      });
    }
    return parseBody(response);
  },

  // ---- grid numbering / validation ----
  numberGrid({ size, grid }) {
    return post('/api/number', clean({ size, grid }));
  },

  validateGrid({ grid, gridSize }) {
    return post('/api/grid/validate', clean({ grid, grid_size: gridSize }));
  },

  // ---- pattern search ----
  searchPattern({ pattern, wordlists, maxResults = 40, algorithm = 'trie' }) {
    return post('/api/pattern', {
      pattern,
      wordlists: wordlists || ['comprehensive'],
      max_results: maxResults,
      algorithm,
    });
  },

  // ---- autofill lifecycle ----
  // options carries REAL fill fields (size, grid, wordlists, timeout, ...).
  // resumeTaskId (Task 15) maps to resume_task_id.
  startFill(options = {}) {
    const { resumeTaskId, ...rest } = options;
    return post('/api/fill/with-progress', clean({ ...rest, resume_task_id: resumeTaskId }));
  },

  /** SSE. No named server events — uses the onmessage property handler. */
  openProgress(taskId, { onEvent, onError } = {}) {
    const source = new EventSource('/api/progress/' + taskId);
    source.onmessage = (e) => {
      if (!onEvent) return;
      let parsed;
      try {
        parsed = JSON.parse(e.data);
      } catch {
        return; // ignore non-JSON data lines
      }
      onEvent(parsed);
    };
    source.onerror = (e) => {
      if (onError) onError(e);
    };
    let closed = false;
    return {
      close() {
        if (closed) return;
        closed = true;
        source.close();
      },
    };
  },

  pauseFill(taskId) {
    return post('/api/fill/pause/' + taskId);
  },

  cancelFill(taskId) {
    return post('/api/fill/cancel/' + taskId);
  },

  resumeFill({ taskId, editedGrid, options }) {
    return post(
      '/api/fill/resume',
      clean({ task_id: taskId, edited_grid: editedGrid, options })
    );
  },

  getFillState(taskId) {
    return get('/api/fill/state/' + taskId);
  },

  listFillStates(maxAgeDays) {
    const q = maxAgeDays !== undefined ? `?max_age_days=${maxAgeDays}` : '';
    return get('/api/fill/states' + q);
  },

  deleteFillState(taskId) {
    return del('/api/fill/state/' + taskId);
  },

  cleanupFillStates(maxAgeDays = 7) {
    return post('/api/fill/states/cleanup', { max_age_days: maxAgeDays });
  },

  editSummary({ taskId, editedGrid }) {
    return post('/api/fill/edit-summary', { task_id: taskId, edited_grid: editedGrid });
  },

  // ---- verify / clean ----
  verifyWords({ grid, size, wordlists }) {
    return post('/api/grid/verify-words', clean({ grid, size, wordlists }));
  },

  cleanGrid({ grid, size }) {
    return post('/api/grid/clean', clean({ grid, size }));
  },

  normalize(text) {
    return post('/api/normalize', { text });
  },

  // ---- black-square helpers ----
  suggestBlackSquare({ grid, problematicSlot, gridSize, maxSuggestions = 3 }) {
    return post(
      '/api/grid/suggest-black-square',
      clean({
        grid,
        problematic_slot: problematicSlot,
        grid_size: gridSize,
        max_suggestions: maxSuggestions,
      })
    );
  },

  applyBlackSquares({ grid, primary, symmetric }) {
    return post('/api/grid/apply-black-squares', { grid, primary, symmetric });
  },

  // ---- wordlists ----
  getWordlists() {
    return get('/api/wordlists');
  },

  getWordlist(name, { stats } = {}) {
    return get('/api/wordlists/' + name + (stats ? '?stats=true' : ''));
  },

  updateWordlist(name, body) {
    return put('/api/wordlists/' + name, body);
  },

  deleteWordlist(name) {
    return del('/api/wordlists/' + name);
  },

  importWordlist({ name, content, category, metadata }) {
    return post('/api/wordlists/import', clean({ name, content, category, metadata }));
  },

  searchWordlists({ pattern, wordlists }) {
    return post('/api/wordlists/search', clean({ pattern, wordlists }));
  },

  // ---- theme ----
  themeUpload({ content, gridSize }) {
    return post('/api/theme/upload', clean({ content, grid_size: gridSize }));
  },

  themeValidate({ themeWords, gridSize }) {
    return post('/api/theme/validate', clean({ theme_words: themeWords, grid_size: gridSize }));
  },

  themeSuggestPlacements({ themeWords, gridSize, existingGrid, maxSuggestions = 3 }) {
    return post(
      '/api/theme/suggest-placements',
      clean({
        theme_words: themeWords,
        grid_size: gridSize,
        existing_grid: existingGrid,
        max_suggestions: maxSuggestions,
      })
    );
  },

  themeApplyPlacement({ grid, placement }) {
    return post('/api/theme/apply-placement', { grid, placement });
  },

  // ---- constraints ----
  getConstraints({ grid, wordlists }) {
    return post('/api/constraints', { grid, wordlists: wordlists || ['comprehensive'] });
  },
};
