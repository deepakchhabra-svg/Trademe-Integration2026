import { test, expect } from "@playwright/test";

test.describe("RetailOS MVP missions (smoke)", () => {
  test("Mission 0: Home loads and shows API status", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "RetailOS Admin" })).toBeVisible();
    // Either "ok" or "down" depending on API availability
    await expect(page.getByText("API")).toBeVisible();
  });

  test("Mission A (read): Vault 1 raw page loads", async ({ page }) => {
    await page.goto("/vaults/raw");
    await expect(page.getByRole("heading", { name: "Vault 1 (Raw)" })).toBeVisible();
    await expect(page.getByText("Supplier products")).toBeVisible();
  });

  test("Mission B (read): Vault 2 enriched page loads", async ({ page }) => {
    await page.goto("/vaults/enriched");
    await expect(page.getByRole("heading", { name: "Vault 2 (Enriched)" })).toBeVisible();
  });

  test("Mission D (read): Command Center page loads", async ({ page }) => {
    await page.goto("/ops/commands");
    await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
  });
});

