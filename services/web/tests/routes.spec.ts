import { test, expect } from "@playwright/test";
import { ROUTES } from "./routes";

/**
 * Route Coverage Test Suite
 * Ensures that every page in the application loads without crashing,
 * has no console errors, and displays the main navigation shell.
 */

test.describe("Route Coverage", () => {
    // Use demo mode for all tests
    test.use({
        extraHTTPHeaders: {
            "x-test-mode": "1",
        },
    });

    for (const route of ROUTES) {
        test(`page "${route}" should load without errors`, async ({ page }) => {
            const consoleErrors: string[] = [];
            const failedRequests: string[] = [];

            // Monitor console errors
            page.on("console", (msg) => {
                if (msg.type() === "error") {
                    consoleErrors.push(msg.text());
                }
            });

            // Monitor failed network requests (excluding 3rd party if any)
            page.on("requestfailed", (request) => {
                failedRequests.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText}`);
            });

            // Visit the route
            const response = await page.goto(route);

            // Assertions
            expect(response?.status()).toBe(200);

            // Wait for a reasonable indication of rendering
            await expect(page.locator("aside")).toBeVisible({ timeout: 10000 });
            await expect(page.locator("main")).toBeVisible();

            // Check for console errors
            if (consoleErrors.length > 0) {
                console.error(`Console errors on ${route}:`, consoleErrors);
            }
            expect(consoleErrors).toHaveLength(0);

            // Check for failed requests
            if (failedRequests.length > 0) {
                console.error(`Failed requests on ${route}:`, failedRequests);
            }
            expect(failedRequests).toHaveLength(0);
        });
    }
});
