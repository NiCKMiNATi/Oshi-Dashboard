import { defineConfig } from "@playwright/test";

const backendPython =
  process.platform === "win32"
    ? "../backend/.venv/Scripts/python.exe"
    : "../backend/.venv/bin/python";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    channel: "chrome",
    viewport: { width: 1440, height: 1024 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `"${backendPython}" ../scripts/integration-backend.py`,
      url: "http://127.0.0.1:8000/api/stats",
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:3000",
      env: { NEXT_PUBLIC_API_URL: "http://127.0.0.1:8000" },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
