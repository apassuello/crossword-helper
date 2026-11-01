/**
 * useClueReconcile (clue-authoring spec 0.1.4, Task 10): section 5.6 "Status display and
 * reconciliation" and section 6.2 "Reconciliation". The hook sends `api.checkClues` when `active`
 * (panel open and no run live) becomes true and 300 ms after the status signature last changed, and
 * shows the server's status only for a reply whose signature equals the current one.
 *
 * Implements Decision 6 (clue-authoring spec 0.1.4, section 1): the CLI owns the authoritative status.
 *
 * `renderHook` with the inputs as props; fake timers; `api.checkClues` stubbed so each call returns a
 * promise the test releases by hand.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useClueReconcile } from '../useClueReconcile';
import { fromCliStrings, toCliStrings } from '../../api/gridCodec';
import { clueStatuses } from '../../lib/clues';
import { ApiError } from '../../api/client';
import { deferred, stubCheckClues } from '../../__tests__/importExportHelpers';

const KEY = '0,0,across';
const KEY2 = '1,0,across';

// Rows are arrays of single characters.
const CAT = fromCliStrings([
  ['C', 'A', 'T'],
  ['.', '.', '.'],
  ['.', '.', '.'],
]);
const CAR = fromCliStrings([
  ['C', 'A', 'R'],
  ['.', '.', '.'],
  ['.', '.', '.'],
]);
const COT = fromCliStrings([
  ['C', 'O', 'T'],
  ['.', '.', '.'],
  ['.', '.', '.'],
]);

const clue = (text, answer) => ({ text, answer });
const ONE = { [KEY]: clue('Feline', 'CAT') };
const TWO = { [KEY]: clue('Feline', 'CAT'), [KEY2]: clue('Blank row', '???') };

let stub;
let pending; // one deferred per api.checkClues call, in call order

beforeEach(() => {
  vi.useFakeTimers();
  pending = [];
  stub = stubCheckClues(() => {
    const d = deferred();
    pending.push(d);
    return d.promise;
  });
});
afterEach(() => {
  stub.restore();
  vi.useRealTimers();
});

const props = (over = {}) => ({ grid: CAT, gridSize: 3, clues: ONE, active: true, ...over });
const mount = (over) => renderHook((p) => useClueReconcile(p), { initialProps: props(over) });
const calls = () => stub.fn.mock.calls.length;
const body = (n) => stub.fn.mock.calls[n][0];
const advance = (ms) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
const reply = (n, statuses) =>
  act(async () => {
    pending[n].resolve({ success: true, statuses });
  });
const fail = (n) =>
  act(async () => {
    pending[n].reject(new ApiError({ status: 500, code: 'INTERNAL_ERROR', message: 'boom' }));
  });
const change = (view, over) => act(() => view.rerender(props(over)));

describe('no grid (App starts with grid null; allSlots(null) throws)', () => {
  it('shows {} and sends nothing', async () => {
    const view = mount({ grid: null, clues: {} });
    await advance(1000);
    expect(view.result.current).toStrictEqual({});
    expect(calls()).toBe(0);
  });
});

describe('a request when the panel opens (spec 5.6)', () => {
  it('sends exactly one request with {size, grid as CLI strings, the full clue map}', async () => {
    mount({ clues: TWO });
    expect(calls()).toBe(1);
    expect(body(0)).toStrictEqual({
      size: 3,
      grid: [
        ['C', 'A', 'T'],
        ['.', '.', '.'],
        ['.', '.', '.'],
      ],
      clues: TWO,
    });
    expect(body(0).grid).toStrictEqual(toCliStrings(CAT));
    await advance(1000);
    expect(calls()).toBe(1);
  });

  it('shows the browser statuses while the reply is outstanding', () => {
    const view = mount();
    expect(view.result.current).toStrictEqual(clueStatuses(CAT, ONE));
    expect(view.result.current).toStrictEqual({ [KEY]: 'ok' });
  });
});

describe('no request while active is false (spec 5.6, 6.2 "no request during a run")', () => {
  it('(a) steady state: nothing is sent and the statuses are the browser\'s', async () => {
    const view = mount({ active: false });
    await advance(1000);
    expect(calls()).toBe(0);
    expect(view.result.current).toStrictEqual(clueStatuses(CAT, ONE));
  });

  it('(b) a status change while inactive, then 300 ms: nothing is sent', async () => {
    const view = mount({ active: false });
    change(view, { active: false, grid: CAR });
    await advance(300);
    expect(calls()).toBe(0);
    await advance(1000);
    expect(calls()).toBe(0);
    expect(view.result.current).toStrictEqual(clueStatuses(CAR, ONE));
    expect(view.result.current).toStrictEqual({ [KEY]: 'stale' });
  });

  it('(c) active goes false 100 ms after a change: the pending request is dropped and the statuses are the browser\'s even after an earlier matching reply', async () => {
    const view = mount();
    expect(calls()).toBe(1);
    await reply(0, { [KEY]: 'orphaned' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'orphaned' }); // the reply applied
    change(view, { grid: CAR });
    await advance(100);
    change(view, { grid: CAR, active: false });
    await advance(200); // 300 ms after the change
    expect(calls()).toBe(1);
    await advance(1000);
    expect(calls()).toBe(1);
    expect(view.result.current).toStrictEqual(clueStatuses(CAR, ONE));
    expect(view.result.current).toStrictEqual({ [KEY]: 'stale' });
  });

  it('going inactive with an unchanged signature after a matching reply shows the browser statuses', async () => {
    const view = mount();
    await reply(0, { [KEY]: 'stale' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'stale' });
    change(view, { active: false });
    expect(view.result.current).toStrictEqual({ [KEY]: 'ok' });
  });

  it('a reply that lands after active went false is not shown', async () => {
    const view = mount();
    change(view, { active: false });
    await reply(0, { [KEY]: 'stale' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'ok' });
  });
});

describe('one request 300 ms after the last status change (spec 5.6; CA-3)', () => {
  it('two changes 100 ms apart give one request, 300 ms after the second, and none at 299 ms', async () => {
    const view = mount();
    expect(calls()).toBe(1); // the open request
    change(view, { grid: CAR });
    await advance(100);
    change(view, { grid: COT });
    await advance(299);
    expect(calls()).toBe(1);
    await advance(1);
    expect(calls()).toBe(2);
    expect(body(1)).toStrictEqual({ size: 3, grid: toCliStrings(COT), clues: ONE });
    await advance(2000);
    expect(calls()).toBe(2);
  });

  it('a clue answer change is a status change and sends a request', async () => {
    const view = mount();
    change(view, { clues: { [KEY]: clue('Feline', '???') } });
    await advance(300);
    expect(calls()).toBe(2);
    expect(body(1).clues).toStrictEqual({ [KEY]: clue('Feline', '???') });
  });

  it('a text-only change sends nothing', async () => {
    const view = mount();
    expect(calls()).toBe(1);
    change(view, { clues: { [KEY]: clue('Cat, say', 'CAT') } });
    await advance(1000);
    expect(calls()).toBe(1);
    expect(view.result.current).toStrictEqual({ [KEY]: 'ok' });
  });
});

describe('a reply is applied only on an exact signature match (spec 5.6)', () => {
  it('a reply for the current signature shows the server status where it differs from the browser\'s', async () => {
    const view = mount();
    expect(clueStatuses(CAT, ONE)).toStrictEqual({ [KEY]: 'ok' });
    await reply(0, { [KEY]: 'stale' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'stale' });
  });

  it('(6.3 target) a reply for an older status signature is not applied', async () => {
    const view = mount();
    change(view, { grid: CAR }); // the signature moves on; the request for CAT is still out
    await advance(100);
    await reply(0, { [KEY]: 'orphaned' }); // the old reply lands, 200 ms before the new request
    expect(calls()).toBe(1);
    expect(view.result.current).toStrictEqual(clueStatuses(CAR, ONE));
    expect(view.result.current).toStrictEqual({ [KEY]: 'stale' });
  });

  it('an older reply that lands after the newer request has gone out is still not applied', async () => {
    const view = mount();
    change(view, { grid: CAR });
    await advance(300);
    expect(calls()).toBe(2);
    await reply(0, { [KEY]: 'orphaned' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'stale' });
    await reply(1, { [KEY]: 'ok' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'ok' }); // the matching one applies
  });

  it('a key missing from the reply shows the browser\'s status; a reply key that is no current clue is dropped', async () => {
    const view = mount({ clues: TWO });
    expect(clueStatuses(CAT, TWO)).toStrictEqual({ [KEY]: 'ok', [KEY2]: 'stale' });
    await reply(0, { [KEY]: 'orphaned', '9,9,down': 'stale' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'orphaned', [KEY2]: 'stale' });
  });

  it('after the signature moves on the browser statuses show until a new matching reply lands', async () => {
    const view = mount();
    await reply(0, { [KEY]: 'orphaned' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'orphaned' });
    change(view, { grid: CAR });
    expect(view.result.current).toStrictEqual({ [KEY]: 'stale' });
    await advance(300);
    expect(calls()).toBe(2);
    expect(view.result.current).toStrictEqual({ [KEY]: 'stale' }); // still the browser's
    await reply(1, { [KEY]: 'ok' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'ok' });
  });
});

describe('a failed request (spec 5.6: "A failure shows nothing")', () => {
  it('shows the browser statuses and nothing else', async () => {
    const view = mount();
    await fail(0);
    expect(view.result.current).toStrictEqual({ [KEY]: 'ok' });
    expect(view.result.error).toBeUndefined();
  });

  it('shows the browser statuses after an earlier applied reply for the same signature', async () => {
    const view = mount();
    await reply(0, { [KEY]: 'stale' });
    expect(view.result.current).toStrictEqual({ [KEY]: 'stale' });
    change(view, { active: false });
    change(view, { active: true }); // reopened, same signature: a new request
    expect(calls()).toBe(2);
    await fail(1);
    expect(view.result.current).toStrictEqual({ [KEY]: 'ok' });
  });
});

describe('a run ending with the panel open (spec 5.6)', () => {
  it('active going true again sends one request', async () => {
    const view = mount();
    expect(calls()).toBe(1);
    change(view, { active: false }); // a run starts
    await advance(1000);
    expect(calls()).toBe(1);
    change(view, { active: true }); // the run ends, panel still open
    expect(calls()).toBe(2);
    expect(body(1)).toStrictEqual({ size: 3, grid: toCliStrings(CAT), clues: ONE });
    await advance(1000);
    expect(calls()).toBe(2);
  });
});
