import { expect, test } from "@playwright/test";

test("compare gallery images resolve to real public assets", async ({ page }) => {
  await page.goto("/compare");
  await expect(page.getByText("Cross-spot comparison.")).toBeVisible();
  await page.waitForSelector("img");

  await page.waitForFunction(() => {
    const visibleImages = Array.from(document.images).filter((img) => {
      const rect = img.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.bottom >= 0 && rect.top <= window.innerHeight;
    });

    return (
      visibleImages.length > 0 &&
      visibleImages.every((img) => img.complete && img.naturalWidth > 0)
    );
  });

  const brokenVisibleImages = await page.evaluate(() =>
    Array.from(document.images)
      .filter((img) => {
        const rect = img.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && rect.bottom >= 0 && rect.top <= window.innerHeight;
      })
      .filter((img) => !img.complete || img.naturalWidth === 0)
      .map((img) => img.currentSrc || img.src || img.getAttribute("src")),
  );

  expect(brokenVisibleImages).toEqual([]);
});
