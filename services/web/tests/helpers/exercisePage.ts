import { Page, expect } from "@playwright/test";

/**
 * Generic helper to "exercise" a page by interacting with standard controls.
 * It follows a non-destructive path by default (e.g., clicking filters, pagination).
 */
export async function exercisePage(page: Page) {
    // 1. Check for basic page structure
    await expect(page.locator('main')).toBeVisible();

    // 2. Check for Page Header
    const title = page.getByTestId('page-title');
    if (await title.isVisible()) {
        console.log(`Exercising page: ${await title.innerText()}`);
    }

    // 3. Interact with Search/Filters if present
    const searchInp = page.getByTestId('inp-search-q');
    if (await searchInp.isVisible()) {
        await searchInp.fill('test-exercise');
        await page.getByTestId('btn-search-apply').click();
        await page.waitForLoadState('networkidle');

        // Reset
        await page.getByTestId('lnk-search-reset').click();
        await page.waitForLoadState('networkidle');
    }

    // 4. Interact with DataTable if present
    const table = page.getByTestId('data-table');
    if (await table.isVisible()) {
        // Try pagination
        const nextBtn = page.getByTestId('pagination-next');
        if (await nextBtn.isVisible() && !await nextBtn.isDisabled()) {
            await nextBtn.click();
            await page.waitForLoadState('networkidle');
        }

        // Try sorting if any sortable column exists
        const firstSortable = page.locator('[data-testid^="col-sort-"]').first();
        if (await firstSortable.isVisible()) {
            await firstSortable.click();
            await page.waitForLoadState('networkidle');
        }
    }

    // 5. Ensure no console errors happened during interaction
    // (Consoles are already monitored in global hooks or per test)
}
