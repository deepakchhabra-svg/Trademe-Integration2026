import { test, expect } from "@playwright/test";
import { UI } from "./uiMap";

test.describe("Ops Dashboard Flows", () => {
    test.beforeEach(async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");
    });

    test("Dashboard: Summary Statistics Visibility", async ({ page }) => {
        // Assert major stat sections are present
        await expect(page.getByTestId('val-pending')).toBeVisible();
        await expect(page.getByTestId('val-executing')).toBeVisible();
        await expect(page.getByTestId('val-raw-present')).toBeVisible();
        await expect(page.getByTestId('val-listings-dry')).toBeVisible();
    });

    test("Dashboard: Guided Flow Navigation", async ({ page }) => {
        // Step 1: Scrape
        await page.getByTestId('btn-scrape-vault').click();
        await expect(page).toHaveURL("/vaults/raw");
        await page.goBack();

        // Step 2: Enrich
        await page.getByTestId('btn-enrich-vault').click();
        await expect(page).toHaveURL("/vaults/enriched");
        await page.goBack();

        // Step 3: Dry Run Review
        await page.getByTestId('btn-dryrun-vault').click();
        await expect(page).toHaveURL(/\/vaults\/live\?status=DRY_RUN/);
    });

    test("Dashboard: Nav Actions", async ({ page }) => {
        await page.getByTestId(UI.pages.dashboard.bulkBatch).click();
        await expect(page).toHaveURL("/ops/bulk");
        await page.goBack();

        await page.getByTestId(UI.pages.dashboard.inbox).click();
        await expect(page).toHaveURL("/ops/inbox");
    });
});
