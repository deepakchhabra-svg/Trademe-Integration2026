import { chromium, type FullConfig } from "@playwright/test";
import fs from "fs";
import path from "path";

/**
 * Deterministic auth setup for E2E.
 *
 * We authenticate using the real token boundary:
 * - cookie `retailos_token` matches backend env `RETAIL_OS_POWER_TOKEN`
 * - cookie `retailos_role` is set to "power" for UI affordances
 *
 * No insecure header roles required.
 */
export default async function globalSetup(config: FullConfig) {
  const baseURL = (config.projects[0]?.use?.baseURL as string | undefined) || "http://127.0.0.1:3000";
  const token = process.env.RETAIL_OS_POWER_TOKEN;
  if (!token) {
    throw new Error("RETAIL_OS_POWER_TOKEN must be set for Playwright E2E.");
  }

  const outPath = path.resolve(__dirname, "..", ".playwright", "storageState.json");
  fs.mkdirSync(path.dirname(outPath), { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext();

  // We can set cookies without hitting the server.
  await context.addCookies([
    { name: "retailos_token", value: token, url: baseURL, httpOnly: false, sameSite: "Lax" },
    { name: "retailos_role", value: "power", url: baseURL, httpOnly: false, sameSite: "Lax" },
  ]);

  await context.storageState({ path: outPath });
  await browser.close();
}

