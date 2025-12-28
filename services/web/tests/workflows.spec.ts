import { test, expect } from "@playwright/test";
import { UI } from "./uiMap";

/**
 * Deep Workflow Flows Test Suite
 * Validates the end-to-end flow from dashboard actions to worker processing and UI reflection.
 */

test.describe("Deep Workflow Flows", () => {
    test.use({
        extraHTTPHeaders: {
            "x-test-mode": "1",
        },
    });

    test("Full Cycle: Scrape -> Enrich -> Dry-Run -> Publish @smoke", async ({ page }) => {
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
        await page.goto("/ops/commands");
        const scrapeRow = page.locator("tr").filter({ hasText: "SCRAPE_SUPPLIER" }).first();
        await expect(scrapeRow).toBeVisible();

        // Wait for worker to pick it up and succeed (timeout increased for Real Mode)
        await expect(scrapeRow.getByText("SUCCEEDED")).toBeVisible({ timeout: 60000 });

        // 3. Repeat for Enrich
        await page.goto("/ops/bulk");
        await page.getByTestId(UI.pages.bulkOps.supplier).selectOption("1:ONECHEQ");
        await page.getByTestId(UI.pages.bulkOps.category).fill("smartphones");
        await page.getByTestId(UI.pages.bulkOps.enrichBtn).click();
        await expect(page.getByText(/Enqueued ENRICH_SUPPLIER/)).toBeVisible();

        await page.goto("/ops/commands");
        const enrichRow = page.locator("tr").filter({ hasText: "ENRICH_SUPPLIER" }).first();
        await expect(enrichRow).toBeVisible();
        await expect(enrichRow.getByText("SUCCEEDED")).toBeVisible({ timeout: 15000 });

        // 4. Repeat for Dry-Run
        await page.goto("/ops/bulk");
        await page.getByTestId(UI.pages.bulkOps.supplier).selectOption("1:ONECHEQ");
        await page.getByTestId(UI.pages.bulkOps.dryRunBtn).click();
        await expect(page.getByText(/Dry-run queued/)).toBeVisible();

        // 5. Repeat for Publish
        await page.goto("/ops/bulk");
        await page.getByTestId(UI.pages.bulkOps.supplier).selectOption("1:ONECHEQ");
        await page.getByTestId(UI.pages.bulkOps.approveBtn).click();
        await expect(page.getByText(/Approved publish queued/)).toBeVisible();
    });
});
