import { test, expect } from "@playwright/test";

test.describe("RetailOS MVP missions (smoke)", () => {
  test("Mission 0: Home loads and shows API status", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByText("API")).toBeVisible();
  });

  test("Mission A (read): Vault 1 raw page loads", async ({ page }) => {
    await page.goto("/vaults/raw");
    await expect(page.getByRole("heading", { name: "Vault 1 · Raw" })).toBeVisible();
  });

  test("Mission B (read): Vault 2 enriched page loads", async ({ page }) => {
    await page.goto("/vaults/enriched");
    await expect(page.getByRole("heading", { name: "Vault 2 · Enriched" })).toBeVisible();
  });

  test("Mission C (read): Vault 3 listings page loads", async ({ page }) => {
    await page.goto("/vaults/live");
    await expect(page.getByRole("heading", { name: "Vault 3 · Listings" })).toBeVisible();
  });

  test("Mission D (read): Commands page loads", async ({ page }) => {
    await page.goto("/ops/commands");
    await expect(page.getByRole("heading", { name: "Commands" })).toBeVisible();
  });

  test("Mission E (read): Jobs page loads", async ({ page }) => {
    await page.goto("/ops/jobs");
    await expect(page.getByRole("heading", { name: "Jobs" })).toBeVisible();
  });

  test("Mission F (read): Audits page loads", async ({ page }) => {
    await page.goto("/ops/audits");
    await expect(page.getByRole("heading", { name: "Audits" })).toBeVisible();
  });

  test("Mission J (read): Operator Inbox loads", async ({ page }) => {
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

  test("Mission N (read): DRY_RUN queue view loads", async ({ page }) => {
    await page.goto("/vaults/live?status=DRY_RUN");
    await expect(page.getByRole("heading", { name: "Vault 3 · Listings" })).toBeVisible();
  });

  test("Mission G (drilldown): open a raw product inspector if available", async ({ page, request }) => {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const res = await request.get(`${api}/vaults/raw?page=1&per_page=1`, { headers: { "X-RetailOS-Role": "root" } });
    if (!res.ok()) test.skip(true, `API not available: ${res.status()}`);
    const data = (await res.json()) as { items: Array<{ id: number }>; total: number };
    if (!data.total) test.skip(true, "No supplier products in DB");

    const id = data.items[0]?.id;
    await page.goto(`/vaults/raw/${id}`);
    await expect(page.getByText(`SupplierProduct #${id}`)).toBeVisible();
  });

  test("Mission H (drilldown): open an enriched inspector if available", async ({ page, request }) => {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const res = await request.get(`${api}/vaults/enriched?page=1&per_page=1`, { headers: { "X-RetailOS-Role": "root" } });
    if (!res.ok()) test.skip(true, `API not available: ${res.status()}`);
    const data = (await res.json()) as { items: Array<{ id: number }>; total: number };
    if (!data.total) test.skip(true, "No internal products in DB");

    const id = data.items[0]?.id;
    await page.goto(`/vaults/enriched/${id}`);
    await expect(page.getByText("Trust blockers").or(page.getByText("passes gates"))).toBeVisible();
  });

  test("Mission I (drilldown): open a listing inspector if available", async ({ page, request }) => {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    const res = await request.get(`${api}/vaults/live?page=1&per_page=1`, { headers: { "X-RetailOS-Role": "root" } });
    if (!res.ok()) test.skip(true, `API not available: ${res.status()}`);
    const data = (await res.json()) as { items: Array<{ id: number }>; total: number };
    if (!data.total) test.skip(true, "No listings in DB");

    const id = data.items[0]?.id;
    await page.goto(`/vaults/live/${id}`);
    await expect(page.getByText(`Listing #${id}`)).toBeVisible();
  });
});

