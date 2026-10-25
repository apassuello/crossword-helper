/**
 * One content signature (novice-readiness spec 0.2.18 §3.9, "What one step is" / "What a step
 * holds"): App, the history and the hook all compare grid content through `lib/contentSig`.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { snapshotContent } from '../history';

const cell = (patch = {}) => ({
  letter: '', isBlack: false, isThemeLocked: false, isAutofilled: false, ...patch,
});
const grid = (patch) => [[cell(patch)]];

describe('contentSigOf', () => {
  it('treats isAutofilled undefined as false', async () => {
    const { contentSigOf } = await import(/* @vite-ignore */ ['..', 'contentSig'].join('/'));
    const undef = grid();
    delete undef[0][0].isAutofilled;
    expect(contentSigOf(1, undef)).toBe(contentSigOf(1, grid({ isAutofilled: false })));
    expect(contentSigOf(1, undef)).not.toBe(contentSigOf(1, grid({ isAutofilled: true })));
  });

  it('a snapshot of an undefined-isAutofilled grid has the signature of the false grid', async () => {
    const { contentSigOf } = await import(/* @vite-ignore */ ['..', 'contentSig'].join('/'));
    const undef = grid();
    delete undef[0][0].isAutofilled;
    const a = snapshotContent(undef, 1);
    const b = snapshotContent(grid({ isAutofilled: false }), 1);
    expect(contentSigOf(a.size, a.cells)).toBe(contentSigOf(b.size, b.cells));
    expect(a.sig).toBe(contentSigOf(1, grid({ isAutofilled: false })));
  });

  it('App, the history and the hook import it from lib/contentSig and define no copy', () => {
    const read = (p) => fs.readFileSync(path.resolve(__dirname, '../..', p), 'utf8');
    for (const f of ['App.jsx', 'lib/history.js', 'hooks/useUndoHistory.js']) {
      expect(read(f), f).toMatch(/from '(\.\.\/|\.\/)(lib\/)?contentSig'/);
    }
    expect(read('App.jsx')).not.toMatch(/function contentSigOf/);
  });
});
