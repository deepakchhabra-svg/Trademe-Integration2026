import { test, expect } from "@playwright/test";

test.describe("RetailOS MVP missions (smoke)", () => {
  test("Mission 0: Home loads and shows API status @smoke", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Ops Workbench" })).toBeVisible();
    await expect(page.getByText("Backend:")).toBeVisible();
    // Canonical workflow affordance should be present.
    await expect(page.getByRole("link", { name: "Open Pipeline" }).first()).toBeVisible();
  });

  test("Mission A (read): Vault 1 raw page loads @smoke", async ({ page }) => {
    await page.goto("/vaults/raw");
    await expect(page.getByRole("heading", { name: "Vault 1 · Raw" })).toBeVisible();
  });

  test("Mission B (read): Vault 2 enriched page loads @smoke", async ({ page }) => {
    await page.goto("/vaults/enriched");
    await expect(page.getByRole("heading", { name: "Vault 2 · Enriched" })).toBeVisible();
  });

  test("Mission C (read): Vault 3 listings page loads @smoke", async ({ page }) => {
    await page.goto("/vaults/live");
    await expect(page.getByRole("heading", { name: "Vault 3 · Listings" })).toBeVisible();
  });

  test("Mission D (read): Commands page loads @smoke", async ({ page }) => {
    await page.goto("/ops/commands");
    await expect(page.getByRole("heading", { name: "Command log" })).toBeVisible();
  });

  test("Mission E (read): Jobs page loads", async ({ page }) => {
    await page.goto("/ops/jobs");
    await expect(page.getByRole("heading", { name: "Jobs" })).toBeVisible();
  });

  test("Mission F (read): Audits page loads", async ({ page }) => {
    await page.goto("/ops/audits");
    await expect(page.getByRole("heading", { name: "Audits" })).toBeVisible();
  });

  test("Mission J (read): Operator Inbox loads @smoke", async ({ page }) => {
    await page.goto("/ops/inbox");
    await expect(page.getByRole("heading", { name: "Operator Inbox" })).toBeVisible();
  });

  test("Mission K (read): Trade Me health page loads", async ({ page }) => {
    await page.goto("/ops/trademe");
    await expect(page.getByRole("heading", { name: "Trade Me Health" })).toBeVisible();
  });

  test("Mission L (read): Alerts page loads", async ({ page }) => {
    await page.goto("/ops/alerts");
    await expect(page.getByRole("heading", { name: "Alerts" })).toBeVisible();
  });

  test("Mission M (read): Bulk ops page loads", async ({ page }) => {
    await page.goto("/ops/bulk");
    await expect(page.getByRole("heading", { name: "Bulk Ops" })).toBeVisible();
  });

  test("Mission O (read): Suppliers page loads", async ({ page }) => {
    await page.goto("/suppliers");
    await expect(page.getByRole("heading", { name: "Suppliers" })).toBeVisible();
  });

  test("Mission N (read): DRY_RUN queue view loads", async ({ page }) => {
    await page.goto("/vaults/live?status=DRY_RUN");
    await expect(page.getByRole("heading", { name: "Vault 3 · Listings" })).toBeVisible();
  });

  test("Mission G (drilldown): open a raw product inspector if available", async ({ page, request }) => {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const token = process.env.RETAIL_OS_POWER_TOKEN || "";
    const res = await request.get(`${api}/vaults/raw?page=1&per_page=1`, { headers: token ? { "X-RetailOS-Token": token } : {} });
    if (!res.ok()) test.skip(true, `API not available: ${res.status()}`);
    const data = (await res.json()) as { items: Array<{ id: number }>; total: number };
    if (!data.total) test.skip(true, "No supplier products in DB");

    const id = data.items[0]?.id;
    await page.goto(`/vaults/raw/${id}`);
    await expect(page.getByText(`SupplierProduct #${id}`)).toBeVisible();
  });

  test("Mission H (drilldown): open an enriched inspector if available", async ({ page, request }) => {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const token = process.env.RETAIL_OS_POWER_TOKEN || "";
    const res = await request.get(`${api}/vaults/enriched?page=1&per_page=1`, { headers: token ? { "X-RetailOS-Token": token } : {} });
    if (!res.ok()) test.skip(true, `API not available: ${res.status()}`);
    const data = (await res.json()) as { items: Array<{ id: number }>; total: number };
    if (!data.total) test.skip(true, "No internal products in DB");

    const id = data.items[0]?.id;
    await page.goto(`/vaults/enriched/${id}`);
    // Either state is acceptable; avoid strict-mode violations by checking each explicitly.
    const blockers = page.getByText("Trust blockers").first();
    const passes = page.getByText("passes gates").first();
    try {
      await expect(blockers).toBeVisible({ timeout: 3000 });
    } catch {
      await expect(passes).toBeVisible();
    }
  });

  test("Mission I (drilldown): open a listing inspector if available", async ({ page, request }) => {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const token = process.env.RETAIL_OS_POWER_TOKEN || "";
    const res = await request.get(`${api}/vaults/live?page=1&per_page=1`, { headers: token ? { "X-RetailOS-Token": token } : {} });
    if (!res.ok()) test.skip(true, `API not available: ${res.status()}`);
    const data = (await res.json()) as { items: Array<{ id: number }>; total: number };
    if (!data.total) test.skip(true, "No listings in DB");

    const id = data.items[0]?.id;
    await page.goto(`/vaults/live/${id}`);
    await expect(page.getByText(`Listing #${id}`)).toBeVisible();
  });

  test("Mission P (drilldown): open a supplier policy page if available", async ({ page, request }) => {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const token = process.env.RETAIL_OS_POWER_TOKEN || "";
    const res = await request.get(`${api}/suppliers`, { headers: token ? { "X-RetailOS-Token": token } : {} });
    if (!res.ok()) test.skip(true, `API not available: ${res.status()}`);
    const data = (await res.json()) as Array<{ id: number }>;
    if (!data.length) test.skip(true, "No suppliers in DB");

    const id = data[0]?.id;
    await page.goto(`/suppliers/${id}`);
    await expect(page.getByText("Supplier policy")).toBeVisible();
  });
});

