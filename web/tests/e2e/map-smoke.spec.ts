import { test, expect } from "@playwright/test";

test("map page shell renders primary navigation", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("link", { name: "Map", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Compare" })).toBeVisible();
  await expect(page.getByRole("link", { name: "WaveScout Nova Scotia" })).toBeVisible();
  await expect(page.getByText(/high candidates/i)).toBeVisible();
  await expect(page.getByText("Discovery map")).toBeVisible();
  await expect(page.getByLabel("Show section analysis")).toBeVisible();
});
