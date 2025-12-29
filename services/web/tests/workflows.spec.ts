import { test, expect, type Page } from "@playwright/test";
import { UI } from "./uiMap";

/**
 * Deep Workflow Flows Test Suite
 * Validates the end-to-end flow from dashboard actions to worker processing and UI reflection.
 */

test.describe("Deep Workflow Flows", () => {
    async function waitForCommandStatus(page: Page, type: string, status: string, timeoutMs = 180000) {
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            await page.goto("/ops/commands");
            const row = page.locator("tr").filter({ hasText: type }).first();
            if (await row.isVisible()) {
                if (await row.getByText(status).isVisible()) return;
            }
            await page.waitForTimeout(1500);
        }
        throw new Error(`Timed out waiting for ${type} to reach ${status}`);
    }

    test("Full Cycle: Scrape -> Enrich -> Dry-Run -> Publish @smoke", async ({ page }) => {
        // This flow hits real external systems (supplier sites + potentially Trade Me).
        // Keep it opt-in to avoid flaky CI and accidental publishing.
        if (process.env.RETAILOS_E2E_LIVE !== "1") {
            test.skip(true, "Live flow is opt-in. Set RETAILOS_E2E_LIVE=1 to run.");
        }
        test.setTimeout(6 * 60_000);

        // 1. Dashboard - Enqueue Scrape
        await page.goto("/");
        await page.getByTestId(UI.pages.dashboard.actions.scrape).click();

        // Should land on Bulk Ops page
        await expect(page).toHaveURL(/\/ops\/bulk/);

        // Fill form and enqueue
        const supplierSelect = page.getByTestId(UI.pages.bulkOps.supplier);
        await expect(supplierSelect).toBeVisible();
        await supplierSelect.selectOption("1:ONECHEQ");
        await page.getByTestId(UI.pages.bulkOps.category).fill("smartphones");
        await page.getByTestId(UI.pages.bulkOps.scrapeBtn).click();

        // Success message should appear
        await expect(page.getByText(/Enqueued SCRAPE_SUPPLIER/)).toBeVisible();

        // 2. Check Commands Page
        await waitForCommandStatus(page, "SCRAPE_SUPPLIER", "SUCCEEDED", 180000);

        // 3. Repeat for Enrich
        await page.goto("/ops/bulk");
        await page.getByTestId(UI.pages.bulkOps.supplier).selectOption("1:ONECHEQ");
        await page.getByTestId(UI.pages.bulkOps.category).fill("smartphones");
        await page.getByTestId(UI.pages.bulkOps.enrichBtn).click();
        await expect(page.getByText(/Enqueued ENRICH_SUPPLIER/)).toBeVisible();

        await waitForCommandStatus(page, "ENRICH_SUPPLIER", "SUCCEEDED", 180000);

        // 4. Repeat for Dry-Run
        await page.goto("/ops/bulk");
        await page.getByTestId(UI.pages.bulkOps.supplier).selectOption("1:ONECHEQ");
        await page.getByTestId(UI.pages.bulkOps.dryRunBtn).click();
        await expect(page.getByText(/Dry-run queued/)).toBeVisible();

        // 5. Optional Publish (destructive!)
        if (process.env.RETAILOS_E2E_ALLOW_PUBLISH === "1") {
            await page.goto("/ops/bulk");
            await page.getByTestId(UI.pages.bulkOps.supplier).selectOption("1:ONECHEQ");
            await page.getByTestId(UI.pages.bulkOps.approveBtn).click();
            await expect(page.getByText(/Approved publish queued/)).toBeVisible();
        }
    });
});
