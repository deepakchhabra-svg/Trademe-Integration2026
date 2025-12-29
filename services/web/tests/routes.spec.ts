import { test, expect } from "@playwright/test";
import { ROUTES } from "./routes";

/**
 * Route Coverage Test Suite
 * Ensures that every page in the application loads without crashing,
 * has no console errors, and displays the main navigation shell.
 */

test.describe("Route Coverage", () => {
    for (const route of ROUTES) {
        test(`page "${route}" should load without errors @smoke`, async ({ page }) => {
            const consoleErrors: string[] = [];
            const failedRequests: string[] = [];

            // Track console errors
            page.on("console", (msg) => {
                if (msg.type() === "error") {
                    const text = msg.text();
                    // Ignore standard browser resource 404 logs in tests
                    if (text.includes("Failed to load resource") || text.includes("404")) {
                        return;
                    }
                    // Ignore React key warnings (already fixed but for safety)
                    if (text.includes("unique \"key\" prop")) {
                        return;
                    }
                    consoleErrors.push(text);
                }
            });

            // Monitor failed network requests (excluding 3rd party if any)
            // Track failed requests
            page.on("requestfailed", (request) => {
                const url = request.url();
                // Ignore image failures from the local media server in tests (often ORB issues on Windows)
                if (url.includes("/media/") || url.endsWith(".jpg") || url.endsWith(".png") || url.endsWith(".ico")) {
                    return;
                }
                failedRequests.push(`${request.method()} ${url} - ${request.failure()?.errorText}`);
            });

            // Visit the route
            const response = await page.goto(route);

            // Assertions
            expect(response?.status()).toBe(200);

            // Wait for a reasonable indication of rendering
            await expect(page.locator("aside")).toBeVisible({ timeout: 10000 });
            await expect(page.locator("main")).toBeVisible();

            // Special check for skeleton pages
            const skeletonRoutes = [
                "/fulfillment/shipments",
                "/fulfillment/messages",
                "/fulfillment/returns",
                "/fulfillment/refunds",
                "/fulfillment/risk",
            ];
            if (skeletonRoutes.includes(route)) {
                await expect(page.getByTestId("coming-soon")).toBeVisible();
            }

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
