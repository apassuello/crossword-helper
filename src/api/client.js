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
    super(message || '');
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
 * Rule 5: `details` precedence chain — top-level `data.details`, else nested
 *         `err.details`, else `data.conflicts` (the apply-placement 400 shape,
 *         which has no `details` key of its own). Whichever is present first
 *         wins; the others are never consulted.
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

  if (details === undefined) details = body.conflicts; // conflicts channel (rule 5)

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
// One contracts-table row is intentionally NOT surfaced here (no consumer in
// M1; the name would be invented): constraintsImpact (/api/constraints/impact).
// Add when a task needs it.
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

  /**
   * Asynchronous pattern search: returns { task_id, progress_url } and streams
   * results over SSE. NOT interchangeable with searchPattern above, which posts
   * to the synchronous /api/pattern and returns results directly.
   */
  startPatternSearch({ pattern, wordlists, maxResults = 50, algorithm = 'regex' }) {
    return post('/api/pattern/with-progress', {
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

  // `wordlists` is not optional in practice: omitting it makes the backend
  // validate against every installed list merged, while verifyWords validates
  // against the ones passed here. Clean would then spare words that the grid
  // is painting red (present in top_200k, a themed list, ...), leaving red
  // cells behind after a "successful" clean. Pass the same selection to both.
  cleanGrid({ grid, size, wordlists }) {
    return post('/api/grid/clean', clean({ grid, size, wordlists }));
  },

  normalize(text) {
    return post('/api/normalize', { text });
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
