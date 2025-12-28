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
        await page.getByTestId(UI.pages.bulkOps.supplier).selectOption({ label: "ONECHEQ (id 1)" });
        await page.getByTestId(UI.pages.bulkOps.category).fill("smartphones");
        await page.getByTestId(UI.pages.bulkOps.scrapeBtn).click();

        // Success message should appear
        await expect(page.getByText(/Enqueued SCRAPE_SUPPLIER/)).toBeVisible();

        // 2. Check Commands Page
        await page.goto("/ops/commands");
        const firstCommand = page.locator("tr").nth(1);
        await expect(firstCommand).toContainText("SCRAPE_SUPPLIER");

        // Wait for worker to pick it up and succeed (max 10s for simulation)
        await expect(firstCommand.getByText("SUCCEEDED")).toBeVisible({ timeout: 15000 });

        // 3. Repeat for Enrich
        await page.goto("/ops/bulk");
        await page.getByTestId(UI.pages.bulkOps.supplier).selectOption({ label: "ONECHEQ (id 1)" });
        await page.getByTestId(UI.pages.bulkOps.category).fill("smartphones");
        await page.getByTestId(UI.pages.bulkOps.enrichBtn).click();
        await expect(page.getByText(/Enqueued ENRICH_SUPPLIER/)).toBeVisible();

        await page.goto("/ops/commands");
        await expect(page.locator("tr").nth(1)).toContainText("ENRICH_SUPPLIER");
        await expect(page.locator("tr").nth(1).getByText("SUCCEEDED")).toBeVisible({ timeout: 15000 });

        // 4. Repeat for Dry-Run
        await page.goto("/ops/bulk");
        await page.getByTestId(UI.pages.bulkOps.supplier).selectOption({ label: "ONECHEQ (id 1)" });
        await page.getByTestId(UI.pages.bulkOps.dryRunBtn).click();
        await expect(page.getByText(/Dry-run queued/)).toBeVisible();

        // 5. Repeat for Publish
        await page.goto("/ops/bulk");
        await page.getByTestId(UI.pages.bulkOps.supplier).selectOption({ label: "ONECHEQ (id 1)" });
        await page.getByTestId(UI.pages.bulkOps.approveBtn).click();
        await expect(page.getByText(/Approved publish queued/)).toBeVisible();
    });
});
