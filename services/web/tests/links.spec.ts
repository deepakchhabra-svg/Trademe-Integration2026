import { test, expect } from "@playwright/test";

/**
 * Link Integrity Test Suite
 * Crawls internal links starting from the dashboard and ensures they all point to valid routes.
 */

test.describe("Link Integrity", () => {
    // Use demo mode for all tests
    test.use({
        extraHTTPHeaders: {
            "x-test-mode": "1",
        },
    });

    test("should have no broken internal links @smoke", async ({ page }) => {
        const visited = new Set<string>();
        const queue: string[] = ["/"];
        const brokenLinks: { from: string; to: string; reason: string }[] = [];
        const consoleErrors: Record<string, string[]> = {};

        while (queue.length > 0) {
            const currentRoute = queue.shift()!;
            if (visited.has(currentRoute)) continue;
            visited.add(currentRoute);

            console.log(`Crawling: ${currentRoute}`);

            const errors: string[] = [];
            page.on("console", (msg) => {
                if (msg.type() === "error") errors.push(msg.text());
            });

            const response = await page.goto(currentRoute);

            // Check for navigation failure
            if (!response || response.status() >= 400) {
                brokenLinks.push({
                    from: "crawler",
                    to: currentRoute,
                    reason: `Status ${response?.status() || "Navigation Error"}`
                });
                continue;
            }

            if (errors.length > 0) {
                consoleErrors[currentRoute] = [...errors];
            }

            // Collect all internal links
            const links = await page.evaluate(() => {
                return Array.from(document.querySelectorAll("a[href]"))
                    .map((a) => (a as HTMLAnchorElement).getAttribute("href")!)
                    .filter((href) => {
                        // Only internal links
                        if (href.startsWith("/") || href.startsWith(window.location.origin)) {
                            // Exclude external, mailto, tel, etc.
                            if (href.startsWith("//")) return false;
                            if (href.includes(":")) return false;
                            return true;
                        }
                        return false;
                    })
                    .map((href) => {
                        // Normalize to path
                        try {
                            return new URL(href, window.location.origin).pathname;
                        } catch {
                            return href;
                        }
                    });
            });

            // Add new links to queue
            for (const link of links) {
                // Exclude some patterns that might lead to infinite loops or non-pages
                if (link.startsWith("/_next")) continue;
                if (link.startsWith("/api")) continue;
                if (link.includes("?")) continue; // Simplify by ignoring query params for crawling

                if (!visited.has(link) && !queue.includes(link)) {
                    queue.push(link);
                }
            }

            // Cleanup listener for next page
            page.removeAllListeners("console");
        }

        // Final Assertions
        if (brokenLinks.length > 0) {
            console.error("Broken internal links found:", brokenLinks);
        }
        expect(brokenLinks).toHaveLength(0);

        const routesWithErrors = Object.keys(consoleErrors);
        if (routesWithErrors.length > 0) {
            console.error("Console errors found on these routes:", consoleErrors);
        }
        expect(routesWithErrors).toHaveLength(0);
    });
});
