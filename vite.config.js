import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { configDefaults } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '127.0.0.1',  // Force IPv4
    proxy: {
      '/api': {
        // novice-readiness spec 0.2.4 §5 (I6): follows run.py's PORT (default 5000)
        target: `http://localhost:${process.env.PORT || 5000}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'frontend/dist',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['src/__tests__/setupTests.js'],
    globals: true,
    exclude: [...configDefaults.exclude, '.claude/**'],
  },
});