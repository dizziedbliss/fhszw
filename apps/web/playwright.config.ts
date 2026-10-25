import { defineConfig, devices } from '@playwright/test'

// The smoke test runs a real browser against a real deployment: the prod compose
// profile by default, or any URL in SMOKE_URL (e.g. a Vercel preview).
// Protected Vercel previews: the short-lived local Vercel OIDC token, injected by
// `vercel env run`, lets automation in without a long-lived bypass secret.
const oidc = process.env.VERCEL_OIDC_TOKEN

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  // Every assertion waits on live Elexon (uncached in a fresh container), which can take a
  // few seconds. The page shows its loading line meanwhile, so allow for that, not 5s.
  expect: { timeout: 20_000 },
  // The tests are independent and both wait on live Elexon: run them side by side.
  fullyParallel: true,
  reporter: 'list',
  use: {
    ...devices['Desktop Chrome'],
    baseURL: process.env.SMOKE_URL ?? 'http://localhost:8080',
    extraHTTPHeaders: oidc ? { 'x-vercel-trusted-oidc-idp-token': oidc } : {},
  },
})
