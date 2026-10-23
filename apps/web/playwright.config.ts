import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  workers: 1,
  use: {
    baseURL: process.env.E2E_WEB_URL ?? 'http://localhost:33001',
    headless: true,
    launchOptions: process.env.E2E_CHROME_PATH ? {executablePath: process.env.E2E_CHROME_PATH} : undefined,
    screenshot: 'only-on-failure',
  },
});
