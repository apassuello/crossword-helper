/**
 * isAdoptableEntry (clue-authoring spec 0.1.4 section 3.5, "Saved document"): the `clues` rule.
 * An absent key is accepted; a present value must be a plain object whose values are all
 * `{text: string, answer: string}`. Key format is not validated.
 */
import { describe, it, expect } from 'vitest';
import { isAdoptableEntry } from '../App';

const base = () => ({
  size: 3,
  grid: Array.from({ length: 3 }, () => Array.from({ length: 3 }, () => ({}))),
});
const withClues = (clues) => ({ ...base(), clues });
const good = { text: 'a', answer: 'ABC' };

describe('isAdoptableEntry clues', () => {
  it('accepts an entry with the clues key absent', () => {
    expect(isAdoptableEntry(base())).toBe(true);
  });

  it('accepts {}', () => {
    expect(isAdoptableEntry(withClues({}))).toBe(true);
  });

  it('accepts one well-formed clue', () => {
    expect(isAdoptableEntry(withClues({ '0,0,across': good }))).toBe(true);
  });

  it.each([
    ['null', null],
    ['an array', []],
    ['a string', 'x'],
  ])('rejects clues that are %s', (_n, v) => {
    expect(isAdoptableEntry(withClues(v))).toBe(false);
  });

  it.each([
    ['null', null],
    ['missing text', { answer: 'ABC' }],
    ['text: 5', { text: 5, answer: 'ABC' }],
    ['answer: null', { text: 'a', answer: null }],
    ['a string', 'text'],
  ])('rejects a clue value that is %s', (_n, v) => {
    expect(isAdoptableEntry(withClues({ '0,0,across': v }))).toBe(false);
  });

  it.each([
    ['null', null],
    ['text: 5', { text: 5, answer: 'ABC' }],
  ])('rejects a map holding a good entry first and a bad value (%s) second', (_n, bad) => {
    expect(isAdoptableEntry(withClues({ '0,0,across': good, '0,0,down': bad }))).toBe(false);
  });

  it.each([
    ['null', null],
    ['text: 5', { text: 5, answer: 'ABC' }],
  ])('rejects a map holding a bad value (%s) first and a good entry second', (_n, bad) => {
    const clues = { '0,0,down': bad, '0,0,across': good };
    expect(Object.keys(clues)[0]).toBe('0,0,down');
    expect(isAdoptableEntry(withClues(clues))).toBe(false);
  });

  it('does not check the key format, only the values', () => {
    expect(isAdoptableEntry(withClues({ 'not-a-key': good }))).toBe(true);
  });

  it('still rejects valid clues on a size below the bound', () => {
    const e = { size: 2, grid: [[{}, {}], [{}, {}]], clues: { '0,0,across': good } };
    expect(isAdoptableEntry(e)).toBe(false);
  });
});
