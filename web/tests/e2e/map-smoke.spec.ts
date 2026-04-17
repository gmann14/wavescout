import { test, expect } from "@playwright/test";

test("map page shell renders primary navigation", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("link", { name: "Map" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Atlas" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Compare" })).toBeVisible();
  await expect(page.getByText("WaveScout")).toBeVisible();
});
