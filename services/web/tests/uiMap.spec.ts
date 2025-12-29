import { test, expect } from "@playwright/test";
import { UI } from "./uiMap";

/**
 * UI Map Click-Through Test Suite
 * Validates that all key interactive elements defined in the UI Map are present and functional.
 */

test.describe("UI Map Click-Through", () => {
    test("Sidebar navigation links should work @smoke", async ({ page }) => {
        await page.goto("/");

        const navLinks = [
            { id: UI.layout.nav.dashboard, title: "Ops Workbench" },
            { id: UI.layout.nav.vaultRaw, title: "Vault 1 · Raw" },
            { id: UI.layout.nav.vaultEnriched, title: "Vault 2 · Enriched" },
            { id: UI.layout.nav.vaultLive, title: "Vault 3 · Listings" },
            { id: UI.layout.nav.suppliers, title: "Suppliers" },
            { id: UI.layout.nav.orders, title: "Orders" },
        ];

        for (const link of navLinks) {
            const locator = page.getByTestId(link.id);
            await expect(locator).toBeVisible();
            await locator.click();
            const titleLoc = page.getByRole('heading', { name: link.title, exact: false });
            await expect(titleLoc).toBeVisible();
        }
    });

    test("Dashboard quick action buttons should be visible @smoke", async ({ page }) => {
        await page.goto("/");
        await expect(page.getByTestId(UI.pages.dashboard.actions.scrape)).toBeVisible();
        await expect(page.getByTestId(UI.pages.dashboard.actions.enrich)).toBeVisible();
        await expect(page.getByTestId(UI.pages.dashboard.actions.dryRun)).toBeVisible();
        await expect(page.getByTestId(UI.pages.dashboard.actions.publish)).toBeVisible();
    });

    test("Vault search and filters should be present @smoke", async ({ page }) => {
        await page.goto("/vaults/raw");
        await expect(page.getByTestId(UI.pages.vaults.searchInp)).toBeVisible();
        await expect(page.getByTestId(UI.pages.vaults.searchApply)).toBeVisible();

        // Try a search
        await page.getByTestId(UI.pages.vaults.searchInp).fill("test-sku");
        await page.getByTestId(UI.pages.vaults.searchApply).click();

        // URL should contain the search param
        await expect(page).toHaveURL(/.*q=test-sku.*/);
    });

    test("Table pagination should be functional", async ({ page }) => {
        await page.goto("/vaults/raw");

        // Wait for table to load
        const table = page.getByTestId(UI.common.table.container);
        const empty = page.getByTestId(UI.common.table.empty);
        if (!(await table.isVisible())) {
            await expect(empty).toBeVisible();
            return;
        }

        // Check pagination if visible (might not be if few items)
        const nextBtn = page.getByTestId(UI.common.table.pagination.next);
        const isNextVisible = await nextBtn.isVisible();

        if (isNextVisible) {
            const disabled = await nextBtn.isDisabled();
            if (disabled) return;
            await nextBtn.click();
            await expect(page).toHaveURL(/.*page=2.*/);
        }
    });
});
