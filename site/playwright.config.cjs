const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:4321/dev_to_ia_engineer/',
    browserName: 'chromium',
    launchOptions: process.env.CI ? { executablePath: '/usr/bin/google-chrome' } : {},
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1',
    url: 'http://127.0.0.1:4321/dev_to_ia_engineer/',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
