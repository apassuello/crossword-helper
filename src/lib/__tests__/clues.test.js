/**
 * Browser clue library (clue-authoring spec 0.1.4 sections 3.1-3.3, 6.2): keys, key order, the
 * section 3.1 trim, the section 3.2 status (display only) and the section 3.3 Commit / Keep / Delete.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fromCliStrings } from '../../api/gridCodec';

const load = () => import(/* @vite-ignore */ ['..', 'clues'].join('/'));

const FIXTURE = path.resolve(__dirname, '../../..', 'tests/fixtures/clue_status_cases.json');
const cases = JSON.parse(fs.readFileSync(FIXTURE, 'utf8')).cases;

const ROSE = [
  ['R', 'O', 'S', 'E'],
  ['.', '.', '.', '.'],
  ['.', '.', '.', '.'],
  ['.', '.', '.', '.'],
];

const frozen = (o) => structuredClone(o);

describe('clueStatus: shared fixture rows', () => {
  it('the fixture holds 14 cases', async () => {
    await load();
    expect(cases.length).toBe(14);
  });

  it.each(cases.map((c, i) => [i, c]))('row %i', async (_i, c) => {
    const { clueStatus } = await load();
    const grid = fromCliStrings(c.grid);
    expect(
      clueStatus(grid, c.key, { text: 'x', answer: c.answer }),
      `${c.key} ${JSON.stringify(c.grid)} answer ${c.answer}`
    ).toBe(c.status);
  });
});

describe('clueStatus: entry lookup', () => {
  it('a key naming a cell inside an entry but not its start is orphaned', async () => {
    const { clueStatus } = await load();
    expect(clueStatus(fromCliStrings(ROSE), '0,2,across', { text: 'x', answer: 'ROSE' })).toBe('orphaned');
  });

  it('a 2-letter down entry is found and compared', async () => {
    const { clueStatus } = await load();
    const grid = fromCliStrings([
      ['.', '.', 'A', '.'],
      ['.', '.', 'B', '.'],
      ['.', '.', '#', '.'],
      ['.', '.', '.', '.'],
    ]);
    expect(clueStatus(grid, '0,2,down', { text: 'x', answer: 'AB' })).toBe('ok');
    expect(clueStatus(grid, '0,2,down', { text: 'x', answer: 'AC' })).toBe('stale');
    expect(clueStatus(grid, '0,2,across', { text: 'x', answer: 'AB' })).toBe('orphaned');
  });

  it('an entry that grew from its answer is stale (RO vs ROSE)', async () => {
    const { clueStatus } = await load();
    expect(clueStatus(fromCliStrings(ROSE), '0,0,across', { text: 'x', answer: 'RO' })).toBe('stale');
  });
});

describe('clueStatuses', () => {
  it('returns one status per key of clues and nothing else', async () => {
    const { clueStatuses } = await load();
    const grid = fromCliStrings(ROSE);
    const clues = {
      '0,0,across': { text: 'a', answer: 'ROSE' },
      '0,0,down': { text: 'b', answer: 'RO' },
      '0,2,across': { text: 'c', answer: 'ROSE' },
    };
    expect(clueStatuses(grid, clues)).toEqual({
      '0,0,across': 'ok',
      '0,0,down': 'stale',
      '0,2,across': 'orphaned',
    });
  });

  it('gives {} for {}', async () => {
    const { clueStatuses } = await load();
    expect(clueStatuses(fromCliStrings(ROSE), {})).toEqual({});
  });
});

describe('keys', () => {
  it('clueKey joins row, col and dir', async () => {
    const { clueKey } = await load();
    expect(clueKey(10, 0, 'across')).toBe('10,0,across');
  });

  it('parseClueKey returns numbers', async () => {
    const { parseClueKey } = await load();
    expect(parseClueKey('10,2,down')).toStrictEqual({ row: 10, col: 2, dir: 'down' });
  });
});

describe('compareClueKeys', () => {
  it('sorts by row, then column numerically, then across before down', async () => {
    const { compareClueKeys } = await load();
    const keys = ['10,0,across', '2,0,down', '2,0,across', '0,10,down', '0,2,across'];
    expect([...keys].sort(compareClueKeys)).toEqual([
      '0,2,across',
      '0,10,down',
      '2,0,across',
      '2,0,down',
      '10,0,across',
    ]);
  });

  it('"2,0,down" sorts before "10,0,across"', async () => {
    const { compareClueKeys } = await load();
    expect(compareClueKeys('2,0,down', '10,0,across') < 0).toBe(true);
    expect(compareClueKeys('10,0,across', '2,0,down') > 0).toBe(true);
  });

  it('a key compares equal to itself', async () => {
    const { compareClueKeys } = await load();
    expect(compareClueKeys('3,4,down', '3,4,down')).toBe(0);
  });
});

describe('trimClueText', () => {
  // Spec 3.1 White_Space set, transcribed as escapes. Never read from clues.js.
  const SPEC_WS = [
    '\u0009', '\u000A', '\u000B', '\u000C', '\u000D', '\u0020', '\u0085', '\u00A0', '\u1680',
    '\u2000', '\u2001', '\u2002', '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008',
    '\u2009', '\u200A', '\u2028', '\u2029', '\u202F', '\u205F', '\u3000',
  ];

  it('the transcribed spec 3.1 set has 25 members', () => {
    expect(SPEC_WS.length).toBe(25);
    expect(new Set(SPEC_WS).size).toBe(25);
  });

  it.each(SPEC_WS.map((ch) => [`U+${ch.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')}`, ch]))(
    'spec 3.1 member %s is stripped as a leading and as a trailing character',
    async (_n, ch) => {
      const { trimClueText } = await load();
      expect(trimClueText(`${ch}abc`)).toBe('abc');
      expect(trimClueText(`abc${ch}`)).toBe('abc');
    }
  );

  it.each([
    ['U+0085', '\u0085'],
    ['U+00A0', ' '],
    ['U+3000', '　'],
    ['ASCII space', ' '],
    ['tab', '\t'],
    ['newline', '\n'],
  ])('strips leading and trailing %s', async (_n, ch) => {
    const { trimClueText } = await load();
    expect(trimClueText(`${ch}abc${ch}`)).toBe('abc');
  });

  it('keeps a leading U+FEFF (JS trim would strip it)', async () => {
    const { trimClueText } = await load();
    expect(trimClueText('﻿abc')).toBe('﻿abc');
  });

  it('keeps a leading U+001C (Python strip would strip it)', async () => {
    const { trimClueText } = await load();
    expect(trimClueText('\u001Cabc')).toBe('\u001Cabc');
  });

  it('keeps interior whitespace unchanged', async () => {
    const { trimClueText } = await load();
    expect(trimClueText('a  b')).toBe('a  b');
  });
});

describe('constants', () => {
  it('CLUE_MAX_LENGTH is 200 and CLUE_TOO_LONG is the message', async () => {
    const { CLUE_MAX_LENGTH, CLUE_TOO_LONG } = await load();
    expect(CLUE_MAX_LENGTH).toBe(200);
    expect(CLUE_TOO_LONG).toBe('At most 200 characters.');
  });
});

describe('applyCommit', () => {
  const KEY = '0,0,across';

  it('unchanged trimmed text keeps the same map and a stale answer', async () => {
    const { applyCommit } = await load();
    const clues = { [KEY]: { text: 'Flower', answer: 'RODE' } };
    const r = applyCommit(clues, KEY, '  Flower ', 'ROSE');
    expect(r.changed).toBe(false);
    expect(r.error).toBe(null);
    expect(r.clues).toBe(clues);
    expect(r.clues[KEY].answer).toBe('RODE');
  });

  it.each([
    ['whitespace-only', '   '],
    ['empty', ''],
  ])('no clue and a %s draft is a no-op on the same map', async (_n, draft) => {
    const { applyCommit } = await load();
    const clues = { '1,0,down': { text: 'k', answer: 'AB' } };
    const r = applyCommit(clues, KEY, draft, 'ROSE');
    expect(r.changed).toBe(false);
    expect(r.error).toBe(null);
    expect(r.clues).toBe(clues);
  });

  it.each([
    ['empty', ''],
    ['whitespace-only (incl. U+3000)', ' 　 '],
  ])('a committed clue with a %s draft is removed', async (_n, draft) => {
    const { applyCommit } = await load();
    const clues = { [KEY]: { text: 'Flower', answer: 'ROSE' }, '1,0,down': { text: 'k', answer: 'AB' } };
    const before = frozen(clues);
    const r = applyCommit(clues, KEY, draft, 'ROSE');
    expect(r.changed).toBe(true);
    expect(r.error).toBe(null);
    expect(KEY in r.clues).toBe(false);
    expect(r.clues).toEqual({ '1,0,down': { text: 'k', answer: 'AB' } });
    expect(r.clues).not.toBe(clues);
    expect(clues).toEqual(before);
  });

  it('201 code points is refused with CLUE_TOO_LONG and the map unchanged', async () => {
    const { applyCommit, CLUE_TOO_LONG } = await load();
    const clues = { [KEY]: { text: 'Flower', answer: 'ROSE' } };
    const before = frozen(clues);
    const r = applyCommit(clues, KEY, 'a'.repeat(201), 'ROSE');
    expect(r.changed).toBe(false);
    expect(r.error).toBe(CLUE_TOO_LONG);
    expect(r.error).toBe('At most 200 characters.');
    expect(r.clues).toEqual(before);
    expect(clues).toEqual(before);
  });

  it('a refused commit on a stale clue writes nothing and keeps the old answer', async () => {
    const { applyCommit, CLUE_TOO_LONG } = await load();
    const clues = { [KEY]: { text: 'Flower', answer: 'RODE' } };
    const before = structuredClone(clues);
    const r = applyCommit(clues, KEY, 'a'.repeat(201), 'ROSE');
    expect(r.error).toBe(CLUE_TOO_LONG);
    expect(r.changed).toBe(false);
    expect(r.clues).toEqual(before);
    expect(r.clues[KEY].answer).toBe('RODE');
    expect(clues).toEqual(before);
  });

  it('200 emoji (400 UTF-16 units) is accepted', async () => {
    const { applyCommit } = await load();
    const draft = '😀'.repeat(200);
    const r = applyCommit({}, KEY, draft, 'ROSE');
    expect(r.changed).toBe(true);
    expect(r.error).toBe(null);
    expect(r.clues[KEY].text).toBe(draft);
  });

  it('200 code points with surrounding spaces is accepted, trimmed', async () => {
    const { applyCommit } = await load();
    const body = 'b'.repeat(200);
    const r = applyCommit({}, KEY, `  ${body} `, 'ROSE');
    expect(r.changed).toBe(true);
    expect(r.error).toBe(null);
    expect(r.clues[KEY].text).toBe(body);
  });

  it('a new clue is exactly {text: trimmed, answer: currentPattern}', async () => {
    const { applyCommit } = await load();
    const clues = {};
    const r = applyCommit(clues, KEY, ' Rose ', 'RO?E');
    expect(r.changed).toBe(true);
    expect(r.error).toBe(null);
    expect(r.clues[KEY]).toStrictEqual({ text: 'Rose', answer: 'RO?E' });
    expect(r.clues).not.toBe(clues);
    expect(clues).toEqual({});
  });

  it('a different draft on a stale clue clears stale (answer becomes currentPattern)', async () => {
    const { applyCommit } = await load();
    const clues = { [KEY]: { text: 'Flower', answer: 'RODE' }, '1,0,down': { text: 'k', answer: 'AB' } };
    const before = frozen(clues);
    const r = applyCommit(clues, KEY, 'Bloom', 'ROSE');
    expect(r.changed).toBe(true);
    expect(r.error).toBe(null);
    expect(r.clues[KEY]).toStrictEqual({ text: 'Bloom', answer: 'ROSE' });
    expect(r.clues['1,0,down']).toEqual({ text: 'k', answer: 'AB' });
    expect(r.clues).not.toBe(clues);
    expect(clues).toEqual(before);
  });
});

describe('applyKeep', () => {
  it('sets answer to currentPattern, keeps text and other keys, and does not mutate', async () => {
    const { applyKeep } = await load();
    const clues = { '0,0,across': { text: 'Flower', answer: 'RODE' }, '1,0,down': { text: 'k', answer: 'AB' } };
    const before = frozen(clues);
    const r = applyKeep(clues, '0,0,across', 'ROSE');
    expect(r).toEqual({ '0,0,across': { text: 'Flower', answer: 'ROSE' }, '1,0,down': { text: 'k', answer: 'AB' } });
    expect(r).not.toBe(clues);
    expect(clues).toEqual(before);
  });
});

describe('applyDelete', () => {
  it('removes the key, keeps others, and does not mutate', async () => {
    const { applyDelete } = await load();
    const clues = { '0,0,across': { text: 'Flower', answer: 'RODE' }, '1,0,down': { text: 'k', answer: 'AB' } };
    const before = frozen(clues);
    const r = applyDelete(clues, '0,0,across');
    expect('0,0,across' in r).toBe(false);
    expect(r).toEqual({ '1,0,down': { text: 'k', answer: 'AB' } });
    expect(r).not.toBe(clues);
    expect(clues).toEqual(before);
  });
});
