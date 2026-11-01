/**
 * Browser clue library (clue-authoring spec 0.1.4, sections 3.1-3.3).
 *
 * Pure functions: keys and key order (3.1), the 3.1 trim, status (3.2) and the Commit / Keep /
 * Delete transitions (3.3). The status computed here is for DISPLAY ONLY (R4): the CLI is the
 * validator and the authoritative status. No endpoint access lives here (check-guards Guard 2).
 *
 * A clue map is `{ [key]: { text, answer } }` with key `"<row>,<col>,<dir>"`. Every apply*
 * function returns a new map when something changes and never mutates its input.
 */
import { allSlots } from '../hooks/useGridGeometry';

export const CLUE_MAX_LENGTH = 200;
export const CLUE_TOO_LONG = 'At most 200 characters.';

// Spec 3.1 whitespace set, written out. Not String.prototype.trim: that strips U+FEFF (not in
// the set) and keeps U+0085 (in the set).
const WS =
  '[\\u0009-\\u000D\\u0020\\u0085\\u00A0\\u1680\\u2000-\\u200A\\u2028\\u2029\\u202F\\u205F\\u3000]';
const LEADING_WS = new RegExp(`^${WS}+`);
const TRAILING_WS = new RegExp(`${WS}+$`);

const KEY_RE = /^(0|[1-9][0-9]*),(0|[1-9][0-9]*),(across|down)$/;

const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

/** "<row>,<col>,<dir>" */
export function clueKey(row, col, dir) {
  return `${row},${col},${dir}`;
}

/** @returns {{row:number, col:number, dir:string}|null} null for a malformed key (never throws). */
export function parseClueKey(key) {
  const m = typeof key === 'string' ? KEY_RE.exec(key) : null;
  if (!m) return null;
  return { row: Number(m[1]), col: Number(m[2]), dir: m[3] };
}

/**
 * Key order (spec 3.1): row, then column, numerically, then across before down.
 * A malformed key sorts after every well-formed one, by plain string order among themselves.
 */
export function compareClueKeys(a, b) {
  const pa = parseClueKey(a);
  const pb = parseClueKey(b);
  if (!pa || !pb) {
    if (pa) return -1;
    if (pb) return 1;
    return a < b ? -1 : a > b ? 1 : 0;
  }
  if (pa.row !== pb.row) return pa.row - pb.row;
  if (pa.col !== pb.col) return pa.col - pb.col;
  if (pa.dir === pb.dir) return 0;
  return pa.dir === 'across' ? -1 : 1;
}

/** Strip the spec 3.1 whitespace set at both ends. */
export function trimClueText(s) {
  return String(s).replace(LEADING_WS, '').replace(TRAILING_WS, '');
}

function statusFrom(slots, key, clue) {
  const p = parseClueKey(key);
  if (!p) return 'orphaned';
  const list = p.dir === 'across' ? slots.across : slots.down;
  const entry = list.find((s) => s.cells[0][0] === p.row && s.cells[0][1] === p.col);
  if (!entry) return 'orphaned';
  return entry.pattern === clue.answer ? 'ok' : 'stale';
}

/** 'ok' | 'stale' | 'orphaned' per spec 3.2 (display only, R4). */
export function clueStatus(grid, key, clue) {
  return statusFrom(allSlots(grid), key, clue);
}

/** One status per key of `clues`. */
export function clueStatuses(grid, clues) {
  const slots = allSlots(grid);
  const out = {};
  for (const key of Object.keys(clues)) out[key] = statusFrom(slots, key, clues[key]);
  return out;
}

function without(clues, key) {
  const next = { ...clues };
  delete next[key];
  return next;
}

/**
 * Spec 3.3 Commit, in its stated order. `error` is null unless the commit is refused.
 * @returns {{clues: object, changed: boolean, error: string|null}}
 */
export function applyCommit(clues, key, draft, currentPattern) {
  const trimmed = trimClueText(draft);
  const existing = has(clues, key) ? clues[key] : undefined;
  if ((existing && trimmed === existing.text) || (trimmed === '' && !existing)) {
    return { clues, changed: false, error: null };
  }
  if (trimmed === '') return { clues: without(clues, key), changed: true, error: null };
  if (Array.from(trimmed).length > CLUE_MAX_LENGTH) {
    return { clues, changed: false, error: CLUE_TOO_LONG };
  }
  return {
    clues: { ...clues, [key]: { text: trimmed, answer: currentPattern } },
    changed: true,
    error: null,
  };
}

/** Keep: answer becomes the current pattern, text unchanged. No clue at `key`: the same map. */
export function applyKeep(clues, key, currentPattern) {
  if (!has(clues, key)) return clues;
  return { ...clues, [key]: { ...clues[key], answer: currentPattern } };
}

/** Delete: the entry is removed. No clue at `key`: the same map. */
export function applyDelete(clues, key) {
  if (!has(clues, key)) return clues;
  return without(clues, key);
}
