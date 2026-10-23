import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';
import pkg from './package.json';

export default defineConfig({
  plugins: [preact()],
  base: './',
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  build: { target: 'es2020', outDir: 'dist', assetsInlineLimit: 0, chunkSizeWarningLimit: 3000 },
  test: { testTimeout: 30000 },
} as any);
