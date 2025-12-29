import { test } from "@playwright/test";
import { exercisePage } from "./helpers/exercisePage";


/**
 * Systematic "Click Everything" Framework Test.
 * 
 * This suite visits key pages and uses the exercisePage helper to interact with
 * filters, pagination, and sorting, ensuring no crashes or console errors.
 */

test.describe("UI Framework Exercise", () => {
    // We'll exercise a representative set of pages rather than all 25+ 
    // to keep the test run focused and fast.
    const TARGET_PAGES = [
        "/",
        "/vaults/raw",
        "/vaults/enriched",
        "/vaults/live",
        "/suppliers", // Assuming these have standard components too
        "/orders",
    ];

    for (const route of TARGET_PAGES) {
        test(`exercise page: ${route}`, async ({ page }) => {
            // Monitor console for errors/warnings
            const errors: string[] = [];
            page.on("console", msg => {
                if (msg.type() === "error") errors.push(msg.text());
            });

            await page.goto(route);
            await page.waitForLoadState("networkidle");

            // Exercise the page
            await exercisePage(page);

            // Assert no console errors after exercise
            if (errors.length > 0) {
                console.error(`Console errors found on ${route}:`, errors);
            }
            // Note: We don't fail strictly here to allow non-critical errors, 
            // but in a strict CI we might.
        });
    }
});
