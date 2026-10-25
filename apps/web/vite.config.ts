import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// In dev, /api goes to FastAPI just like Vercel's /api rewrite does in prod.
// Inside docker compose the api service is reachable as http://api-dev:8000.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  // Host is set by the dev script's --host flag: Vite drops a config-file host when it
  // restarts after a config change, which silently breaks the Docker port mapping.
  server: {
    port: 5173,
    proxy: { '/api': apiTarget },
  },
  test: {
    // Unit and page tests only; e2e/ belongs to Playwright.
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
  },
})
