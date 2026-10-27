// Source guard for Task 6.12 (novice-readiness spec 0.2.7 §3.6, TH5, G11): the
// Theme panel starts below the top bar. jsdom has no box model, so this guards
// the regression only; it is NOT evidence the layout is right (browser check is).
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const read = (p) => readFileSync(path.join(repoRoot, p), 'utf-8');

// body of the first rule whose selector is exactly `selector`
const ruleBody = (src, selector) => {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const m = src.match(new RegExp(`(?:^|\\n)\\s*${esc}\\s*\\{([^}]*)\\}`));
  return m ? m[1] : null;
};

describe('Theme panel sits below the top bar (§3.6 TH5)', () => {
  it('--xw-topbar-h is defined exactly once, in tokens.css', () => {
    const src = read('src/styles/bench/tokens.css');
    expect(src.match(/--xw-topbar-h\s*:/g) || []).toHaveLength(1);
    expect(src).toMatch(/--xw-topbar-h:\s*54px/);
  });

  it('.xw-app reads its first row from the variable', () => {
    const body = ruleBody(read('src/styles/bench/base.css'), '.xw-app');
    expect(body).not.toBeNull();
    expect(body).toMatch(/grid-template-rows:\s*var\(--xw-topbar-h\)\s+1fr/);
  });

  it('.theme-words-panel offsets by the variable, not top: 0', () => {
    const body = ruleBody(read('src/components/ThemeWordsPanel.scss'), '.theme-words-panel');
    expect(body).not.toBeNull();
    expect(body).not.toMatch(/\btop:\s*0\b/);
    expect(body).toMatch(/\btop:\s*var\(--xw-topbar-h\)/);
    expect(body).toMatch(/height:\s*calc\(100vh - var\(--xw-topbar-h\)\)/);
  });
});

// Source guard for novice-readiness spec 0.2.22 §3.6, #93: Save grid's name prompt
// opens above the Theme panel, and toasts stay above the prompt. Same limit as
// above: it pins the z-index order in source, NOT evidence the layout is right.
describe('Save prompt stacks above the Theme panel, below toasts (§3.6, #93)', () => {
  const zIndex = (file, selector) => {
    const body = ruleBody(read(file), selector);
    expect(body).not.toBeNull();
    const m = body.match(/z-index:\s*(\d+)/);
    expect(m).not.toBeNull();
    return parseInt(m[1], 10);
  };

  it('.theme-words-panel < .xw-save-prompt < .xw-toast-stack', () => {
    const panel = zIndex('src/components/ThemeWordsPanel.scss', '.theme-words-panel');
    const prompt = zIndex('src/styles/bench/base.css', '.xw-save-prompt');
    const toast = zIndex('src/styles/bench/base.css', '.xw-toast-stack');
    expect(panel).toBeLessThan(prompt);
    expect(prompt).toBeLessThan(toast);
  });
});
