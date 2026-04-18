import { test, expect } from "@playwright/test";

test("atlas route renders browsing guidance", async ({ page }) => {
  await page.goto("/atlas");

  await expect(page.getByRole("link", { name: "Atlas" })).toBeVisible();
  await expect(
    page.getByText("Atlas sections are browsing units, not confirmed breaks.")
  ).toBeVisible();
});

test("compare route renders same-date guidance", async ({ page }) => {
  await page.goto("/compare");

  await expect(page.getByRole("link", { name: "Compare" })).toBeVisible();
  await expect(
    page.getByText("Every comparison card groups scenes from the same acquisition date only.")
  ).toBeVisible();
});

test("methodology route renders shipped methodology content", async ({ page }) => {
  await page.goto("/methodology");

  await expect(page.getByRole("link", { name: "How It Works" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: /WaveScout Detection Methodology/i })
  ).toBeVisible();
});

test("about route renders scope and safety boundaries", async ({ page }) => {
  await page.goto("/about");

  await expect(page.getByRole("link", { name: "About" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Scope Boundary" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Uncertainty And Safety" })).toBeVisible();
});
