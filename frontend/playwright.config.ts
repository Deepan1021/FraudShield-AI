import { defineConfig } from '@playwright/test';
import path from 'node:path';

// End-to-end tests start their own backend (isolated SQLite file, demo data auto-seeded) and the Vite dev server.
// Run them from an activated Python virtualenv so that `python -m uvicorn` resolves (see TESTING.md).
const root = path.resolve(__dirname, '..');
export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  webServer: [
    {
      command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: path.join(root, 'backend'),
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        APP_ENV: 'test',
        DATABASE_URL: 'sqlite:///database/e2e_fraudshield.db',
        REPORTS_DIR: 'reports/e2e',
        BACKUPS_DIR: 'backups/e2e',
        AUTO_SEED_DEMO: 'true',
        SERVE_FRONTEND: 'false',
        LOG_LEVEL: 'WARNING',
      },
    },
    { command: 'npm run dev', cwd: __dirname, url: 'http://127.0.0.1:5173', reuseExistingServer: false, timeout: 60_000 },
  ],
});
