import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// The config imports vite, whose esbuild cannot load under this suite's jsdom
// environment; stub the three imports so only the config's own values are read.
vi.mock('vite', () => ({ defineConfig: (c) => c }));
vi.mock('@vitejs/plugin-react', () => ({ default: () => ({}) }));
vi.mock('vitest/config', () => ({ configDefaults: { exclude: [] } }));

// novice-readiness spec 0.2.4 §5 (I6): the dev proxy target follows PORT.
describe('vite.config.js proxy target', () => {
  const saved = process.env.PORT;

  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    if (saved === undefined) delete process.env.PORT;
    else process.env.PORT = saved;
    vi.resetModules();
  });

  async function loadTarget() {
    const mod = await import('../../vite.config.js');
    return mod.default.server.proxy['/api'].target;
  }

  it('defaults to 5000 when PORT is unset', async () => {
    delete process.env.PORT;
    expect(await loadTarget()).toBe('http://localhost:5000');
  });

  it('follows PORT when set', async () => {
    process.env.PORT = '5057';
    expect(await loadTarget()).toBe('http://localhost:5057');
  });
});
