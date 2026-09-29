import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Output stays INSIDE landing-src/dist, never at the MIRA project root —
// the built landing.html/js/css are copied out by hand (see landing-src/README.md),
// a deliberate manual step so nothing here can ever touch the FastAPI server's
// files automatically. server/app.py's _LANDING_FILES whitelist only serves
// three exact root-level names (landing.html, landing.css, landing.js, no
// hashing, no /assets subfolder) and is NOT edited by this project — the
// build is shaped to fit that existing contract instead.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsDir: '.',
    rollupOptions: {
      input: 'landing.html',
      output: {
        entryFileNames: 'landing.js',
        chunkFileNames: 'landing-chunk-[hash].js',
        assetFileNames: (info) => (info.name && info.name.endsWith('.css')) ? 'landing.css' : '[name][extname]',
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/children': 'http://localhost:8000',
      '/progress': 'http://localhost:8000',
      '/sessions': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
