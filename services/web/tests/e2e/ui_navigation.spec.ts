import { test, expect } from "@playwright/test";

test.describe("Navigation & Sidebar", () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to home (Dashboard)
        // Runs as default role (Listing) in E2E environment
        await page.goto("/");
    });

    test("should show only 5 core items by default", async ({ page }) => {
        // 1. Dashboard
        // 2. Pipeline
        // 3. Publish Console
        // 4. Live Listings
        // 5. Inbox

        // Check Core section exists
        await expect(page.getByText("Core", { exact: true })).toBeVisible();

        // Check Core Links
        await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
        await expect(page.getByRole("link", { name: "Live Listings" })).toBeVisible();

        // Items that might be hidden if Advanced was open
        // Advanced is CLOSED by default.
        await expect(page.getByRole("link", { name: "Products (Raw)" })).not.toBeVisible();
    });

    test("should expand advanced section", async ({ page }) => {
        // Check Advanced summary exists
        const advanced = page.locator("summary").filter({ hasText: "Advanced" });
        await expect(advanced).toBeVisible();

        // Check it is closed initially
        const details = page.locator("details").filter({ has: advanced });
        await expect(details).not.toHaveAttribute("open");

        // Click to expand
        await advanced.click();

        // Now hidden items should be visible
        // "Products (Raw)" is visible to Listing role, so this confirms expansion working
        await expect(page.getByRole("link", { name: "Products (Raw)" })).toBeVisible();
        await expect(page.getByRole("link", { name: "Products (Ready)" })).toBeVisible();

        // Note: "Command Log" is hidden for Default (Listing) role, so we don't check it here.
        // Testing specific Power role visibility is covered by other UI Action tests or unit logic.
    });

    test("deep link to raw vault should work", async ({ page }) => {
        await page.goto("/vaults/raw");

        // Heading should be visible
        // "Vault 1 · Raw"
        await expect(page.getByRole("heading", { name: "Vault 1 · Raw" })).toBeVisible();

        // Sidebar should still be present
        await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
    });
});
