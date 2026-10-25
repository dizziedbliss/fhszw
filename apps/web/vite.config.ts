import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// In dev, /api goes to FastAPI just like Vercel's /api rewrite does in prod.
// Inside docker compose the api service is reachable as http://api-dev:8000.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: { '/api': apiTarget },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
  },
})
