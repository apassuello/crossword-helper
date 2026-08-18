// Existence-based acceptance test for Task 4 (#16): BlackSquareSuggestions deletion.
//
// This is a guard against partial reintroduction of the deleted feature, not a
// behavioural test. It asserts the deletion surface is fully gone:
//   (a) the component + its stylesheet do not exist on disk
//   (b) client.js no longer exports suggestBlackSquare / applyBlackSquares
//   (c) apiMocks.js no longer handles the two black-square endpoints
import { existsSync, readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');

describe('BlackSquareSuggestions deletion (#16)', () => {
  it('(a) component and stylesheet do not exist', () => {
    expect(existsSync(path.join(repoRoot, 'src/components/BlackSquareSuggestions.jsx'))).toBe(false);
    expect(existsSync(path.join(repoRoot, 'src/components/BlackSquareSuggestions.scss'))).toBe(false);
  });

  it('(b) client.js exposes neither suggestBlackSquare nor applyBlackSquares', () => {
    const source = readFileSync(path.join(repoRoot, 'src/api/client.js'), 'utf-8');
    expect(source).not.toMatch(/suggestBlackSquare/);
    expect(source).not.toMatch(/applyBlackSquares/);
  });

  it('(c) apiMocks.js has no handler for the black-square endpoints', () => {
    const source = readFileSync(path.join(repoRoot, 'src/__tests__/fixtures/apiMocks.js'), 'utf-8');
    expect(source).not.toMatch(/suggest-black-square/);
    expect(source).not.toMatch(/apply-black-squares/);
  });
});
