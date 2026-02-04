import { expect, test } from "@playwright/test";

test("home page renders", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("ParallelDialer - Coming Soon")).toBeVisible();
});
