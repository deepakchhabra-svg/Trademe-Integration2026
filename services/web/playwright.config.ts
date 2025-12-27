import { defineConfig } from "@playwright/test";

// These tests assume the stack is running:
// - web: http://localhost:3000
// - api: http://localhost:8000
//
// For CI, you can set:
// - PLAYWRIGHT_BASE_URL (defaults to http://localhost:3000)

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "retain-on-failure",
  },
});

