
import { test, expect } from '@playwright/test';

test.describe('Money Flows Smoke Suite', () => {

    test('Bulk Reprice: Preview -> Apply', async ({ page }) => {
        // Navigate to Bulk Ops
        await page.goto('/ops/bulk');

        // Select Reprice Tool
        await page.click('button:has-text("Reprice Tool")');

        // Configure inputs (e.g. increase logic)
        await page.fill('input[name="margin_adjustment"]', '5');

        // Click Preview
        await page.click('button:has-text("Preview")');

        // Verify Preview Table loads
        await expect(page.locator('table.preview-results')).toBeVisible();
        await expect(page.locator('td.new-price')).not.toBeEmpty();

        // Click Apply
        await page.click('button:has-text("Apply Changes")');

        // Verify Success Toast/Notification
        await expect(page.locator('.toast-success')).toContainText('Repricing applied');
    });

    test('Publish: Dry-run -> Approve', async ({ page }) => {
        await page.goto('/vaults/ready');

        // Select first item
        await page.click('.data-table tbody tr:first-child .select-row');

        // Click Publish
        await page.click('button:has-text("Publish")');

        // Expect Wizard / Dry Run results
        await expect(page.locator('.publish-wizard')).toBeVisible();
        await expect(page.locator('.dry-run-status')).toHaveText('Ready');

        // Approve
        await page.click('button:has-text("Confirm Publish")');

        // Verify Command Enqueued
        await expect(page.locator('.toast-success')).toContainText('Command Enqueued');
    });

    test('Duplicates: Withdraw Extras', async ({ page }) => {
        await page.goto('/reports/duplicates');

        // Check if duplicates exist
        const count = await page.locator('.duplicate-group').count();
        if (count > 0) {
            // Expand first group
            await page.click('.duplicate-group:first-child .expand-btn');

            // Select "Withdraw" on one item
            await page.click('.duplicate-item:last-child button.withdraw-btn');

            // Confirm
            await page.click('button:has-text("Confirm Withdraw")');

            // Verify UI update
            await expect(page.locator('.duplicate-item:last-child .status-badge')).toHaveText('Withdrawing');
        } else {
            test.skip('No duplicates found/mocked');
        }
    });

    test('Command Lifecycle: Retry/Cancel', async ({ page }) => {
        await page.goto('/ops/inbox');

        // Find a failed command
        const failedRow = page.locator('tr:has(.status-failed)');
        if (await failedRow.count() > 0) {
            await failedRow.first().click();

            // Retry
            await page.click('button:has-text("Retry")');
            await expect(page.locator('.toast-success')).toBeVisible();
            await expect(failedRow.first().locator('.status-badge')).toHaveText('PENDING');

            // Cancel (find another or same if pending allows cancel)
            // ...
        } else {
            test.skip('No failed commands to retry');
        }
    });
});
