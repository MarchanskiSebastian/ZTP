import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const API = process.env.API_URL || 'http://localhost:8000';

// The SPA calls /backend/...; the dev/preview server forwards it to FastAPI without the prefix.
// Browser sees one origin, so the auth_token cookie (SameSite=Lax) works without CORS.
const proxy = {
  '/backend': { target: API, changeOrigin: true, rewrite: (path) => path.replace(/^\/backend/, '') },
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
});
