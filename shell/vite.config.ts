import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    conditions: ['import', 'default'],
  },
  optimizeDeps: {
    include: ['pixi.js', 'pixi-filters'],
    force: true,
  },
  ssr: {
    noExternal: ['pixi.js', 'pixi-filters'],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
});
