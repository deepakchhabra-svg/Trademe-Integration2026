import { test, expect } from "@playwright/test";
import { UI } from "./uiMap";

test.describe("Vault Functional Flows", () => {
    test.beforeEach(async ({ page }) => {
        await page.goto("/");
        await page.waitForLoadState("networkidle");
    });

    test("Raw Vault: List -> Detail -> Breadcrumb", async ({ page }) => {
        await page.goto("/vaults/raw");

        // Wait for table to load
        const table = page.getByTestId(UI.common.table.container);
        await expect(table).toBeVisible();

        // Get first ID link
        const firstIdLink = page.locator('[data-testid^="lnk-id-"]').first();
        const firstId = await firstIdLink.innerText();
        await firstIdLink.click();

        // Verify Detail Page
        await expect(page).toHaveURL(new RegExp(`/vaults/raw/${firstId}`));
        await expect(page.getByTestId('page-title')).toBeVisible();
        await expect(page.getByTestId('badge-status-present')).toBeVisible();

        // Breadcrumb back
        await page.getByTestId('lnk-breadcrumb-vault1').click();
        await expect(page).toHaveURL("/vaults/raw");
    });

    test("Enriched Vault: List -> Detail -> Raw Ref", async ({ page }) => {
        await page.goto("/vaults/enriched");

        const table = page.getByTestId(UI.common.table.container);
        await expect(table).toBeVisible();

        const firstIdLink = page.locator('[data-testid^="lnk-id-"]').first();
        const firstId = await firstIdLink.innerText();
        await firstIdLink.click();

        // Verify Detail Page
        await expect(page).toHaveURL(new RegExp(`/vaults/enriched/${firstId}`));

        // Check link to Raw product
        const rawRef = page.getByTestId(/^lnk-raw-ref-/);
        await expect(rawRef).toBeVisible();
        await rawRef.click();

        await expect(page).toHaveURL(/\/vaults\/raw\/\d+/);
    });

    test("Live Vault: List -> Detail -> Internal Ref", async ({ page }) => {
        await page.goto("/vaults/live");

        const table = page.getByTestId(UI.common.table.container);
        await expect(table).toBeVisible();

        const firstIdLink = page.locator('[data-testid^="lnk-id-"]').first();
        const firstId = await firstIdLink.innerText();
        await firstIdLink.click();

        // Verify Detail Page
        await expect(page).toHaveURL(new RegExp(`/vaults/live/${firstId}`));

        // Check link to Internal product
        const internalRef = page.getByTestId('lnk-internal-ref');
        await expect(internalRef).toBeVisible();
        await internalRef.click();

        await expect(page).toHaveURL(/\/vaults\/enriched\/\d+/);
    });
});
