import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, ApiError } from '../client';

/** Build a minimal Response-like object for the mocked fetch. */
function res(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  };
}

describe('api client', () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('searchPattern posts to /api/pattern with signature defaults and returns results untouched', async () => {
    const results = [{ word: 'CAT', score: 90, source: 'comprehensive', length: 3 }];
    fetchMock.mockResolvedValue(res({ meta: {}, results }));

    const out = await api.searchPattern({ pattern: 'C?T' });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/pattern');
    expect(opts.method).toBe('POST');
    expect(opts.headers['Content-Type']).toBe('application/json');
    const body = JSON.parse(opts.body);
    expect(body.pattern).toBe('C?T');
    expect(body.max_results).toBe(40);
    expect(body.algorithm).toBe('trie');
    expect(body.wordlists).toEqual(['comprehensive']);
    // results passed through untouched (client does not transform them)
    expect(out.results).toEqual(results);
  });

  it('pauseFill POSTs to /api/fill/pause/<id> with no body', async () => {
    fetchMock.mockResolvedValue(res({ success: true, task_id: 't1' }));

    await api.pauseFill('t1');

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/fill/pause/t1');
    expect(opts.method).toBe('POST');
    expect(opts.body).toBeUndefined();
    expect(opts.headers).toBeUndefined();
  });

  it('resumeFill 409 throws ApiError with UNSOLVABLE_EDITS code and top-level details', async () => {
    fetchMock.mockResolvedValue(
      res(
        {
          error: 'User edits create unsolvable configuration',
          details: { conflicting_slots: ['3-across'] },
        },
        409
      )
    );

    let caught;
    try {
      await api.resumeFill({ taskId: 't1', editedGrid: [['A']] });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught.status).toBe(409);
    expect(caught.code).toBe('UNSOLVABLE_EDITS');
    expect(caught.message).toBe('User edits create unsolvable configuration');
    expect(caught.details).toEqual({ conflicting_slots: ['3-across'] });
  });

  it('normalizes flat-string error bodies (rule 3/4)', async () => {
    fetchMock.mockResolvedValue(res({ error: 'Missing grid' }, 400));

    let caught;
    try {
      await api.numberGrid({ grid: [] });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught.status).toBe(400);
    expect(caught.code).toBe('HTTP_400');
    expect(caught.message).toBe('Missing grid');
  });

  it('normalizes envelope error bodies (rule 3/5)', async () => {
    fetchMock.mockResolvedValue(
      res({ error: { code: 'TIMEOUT', message: 'took too long', details: { t: 300 } } }, 504)
    );

    let caught;
    try {
      await api.numberGrid({ grid: [] });
    } catch (e) {
      caught = e;
    }
    expect(caught.code).toBe('TIMEOUT');
    expect(caught.message).toBe('took too long');
    expect(caught.details).toEqual({ t: 300 });
  });

  it('network failure -> ApiError status 0 code NETWORK (rule 1)', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));

    let caught;
    try {
      await api.health();
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught.status).toBe(0);
    expect(caught.code).toBe('NETWORK');
  });

  it('swallows unparseable/empty response bodies to {} (rule 2)', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, text: async () => 'not json' });
    const out = await api.normalize('hi');
    expect(out).toEqual({});
  });

  it('health returns the body on HTTP 503 (rule 6)', async () => {
    fetchMock.mockResolvedValue(res({ status: 'degraded', components: {} }, 503));
    const out = await api.health();
    expect(out.status).toBe('degraded');
  });

  it('openProgress parses SSE data JSON via MockEventSource and forwards to onEvent', () => {
    const events = [];
    const conn = api.openProgress('t1', { onEvent: (e) => events.push(e) });

    // MockEventSource (setupTests) broadcasts via the static helper
    global.EventSource.sendMessage({ progress: 42, status: 'running' });

    expect(events).toEqual([{ progress: 42, status: 'running' }]);
    conn.close();
  });

  it('openProgress close() is idempotent', () => {
    const conn = api.openProgress('t2', {});
    conn.close();
    expect(() => conn.close()).not.toThrow();
  });

  it('RED-3: empty-body 500 yields an empty message, code unchanged (rule 1/4)', async () => {
    fetchMock.mockResolvedValue(res(undefined, 500));

    let caught;
    try {
      await api.numberGrid({ grid: [] });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught.message).toBe('');
    expect(caught.code).toBe('HTTP_500');
  });

  it('RED-4: flat-string 400 + conflicts array surfaces as caught.details (rule 5 extended)', async () => {
    fetchMock.mockResolvedValue(
      res(
        {
          error: 'Placement conflicts detected',
          conflicts: ['Boundary black square at (7, 4) requires a symmetric black square'],
          applied: false,
        },
        400
      )
    );

    let caught;
    try {
      await api.themeApplyPlacement({ grid: [], placement: {} });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught.message).toBe('Placement conflicts detected');
    expect(caught.details).toEqual([
      'Boundary black square at (7, 4) requires a symmetric black square',
    ]);
  });

  it('importWordlist sends dry_run (true and false) and omits it when undefined', async () => {
    fetchMock.mockResolvedValue(res({ words: [], skipped: [] }));
    await api.importWordlist({ name: 'n', content: 'A', dryRun: true });
    await api.importWordlist({ name: 'n', content: 'A', dryRun: false });
    await api.importWordlist({ name: 'n', content: 'A' });
    const bodies = fetchMock.mock.calls.map((c) => JSON.parse(c[1].body));
    expect(bodies[0].dry_run).toBe(true);
    expect(bodies[1].dry_run).toBe(false);
    expect('dry_run' in bodies[2]).toBe(false);
  });

  it('import 400 "No valid words found" surfaces skipped count and reasons as details', async () => {
    fetchMock.mockResolvedValue(
      res({ error: 'No valid words found', skipped: 3, reasons: { 'too short': 3 } }, 400)
    );
    let caught;
    try {
      await api.importWordlist({ name: 'n', content: 'x', dryRun: true });
    } catch (e) {
      caught = e;
    }
    expect(caught.message).toBe('No valid words found');
    expect(caught.details).toEqual({ skipped: 3, reasons: { 'too short': 3 } });
  });
});

// Task 9 (clue-authoring spec 0.1.4, sections 3.5 and 3.6): the grid-file import checks `clues` through
// POST /api/clues/check. Appended as its own block; no existing line above is touched.
describe('api.checkClues (spec 3.6)', () => {
  let fetchMock;
  const grid = [
    ['C', 'A', 'T'],
    ['.', '#', '.'],
    ['.', '.', '.'],
  ];

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('POSTs {size, grid, clues} as JSON to /api/clues/check and returns the body', async () => {
    const clues = { '0,0,across': { text: 'Feline', answer: 'CAT' } };
    const reply = { success: true, statuses: { '0,0,across': 'ok' } };
    fetchMock.mockResolvedValue(res(reply));

    const out = await api.checkClues({ size: 3, grid, clues });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/clues/check');
    expect(opts.method).toBe('POST');
    expect(opts.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(opts.body)).toEqual({ size: 3, grid, clues });
    expect(Object.keys(JSON.parse(opts.body)).sort()).toEqual(['clues', 'grid', 'size']);
    expect(out).toEqual(reply);
  });

  it('sends clues of {} as {}', async () => {
    fetchMock.mockResolvedValue(res({ success: true, statuses: {} }));
    await api.checkClues({ size: 3, grid, clues: {} });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).clues).toEqual({});
  });

  it('sends clues of null as null, not dropped', async () => {
    fetchMock.mockResolvedValue(res({ error: { code: 'INVALID_CLUES', message: 'x' } }, 400));
    await api.checkClues({ size: 3, grid, clues: null }).catch(() => {});
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect('clues' in body).toBe(true);
    expect(body.clues).toBeNull();
  });

  it('a 400 envelope rejects with an ApiError carrying the envelope message', async () => {
    fetchMock.mockResolvedValue(
      res(
        { error: { code: 'INVALID_CLUES', message: 'Invalid clues: must be an object.' } },
        400
      )
    );

    let caught;
    try {
      await api.checkClues({ size: 3, grid, clues: null });
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught.status).toBe(400);
    expect(caught.code).toBe('INVALID_CLUES');
    expect(caught.message).toBe('Invalid clues: must be an object.');
  });
});
