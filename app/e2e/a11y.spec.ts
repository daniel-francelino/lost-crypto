import AxeBuilder from "@axe-core/playwright";
import { type Page, expect, test } from "@playwright/test";

const ADMIN = process.env["E2E_ADMIN_USER"] ?? "";
const ADMIN_PASSWORD = process.env["E2E_ADMIN_PASSWORD"] ?? "";
const THEMES = ["light", "dark"] as const;

test.skip(ADMIN === "", "needs the backend with E2E_* users (see docs/08-quality.md)");

const scan = async (page: Page) => {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  return result.violations.map(
    (violation) =>
      `${violation.id} (${violation.impact}): ${violation.nodes
        .slice(0, 3)
        .map((node) => node.target.join(" "))
        .join(" | ")}`,
  );
};

const setTheme = async (page: Page, theme: (typeof THEMES)[number]) => {
  await page.evaluate((value) => {
    document.documentElement.classList.toggle("dark", value === "dark");
  }, theme);
  await page.waitForTimeout(600);
};

for (const theme of THEMES) {
  test(`login page has no WCAG A/AA violations (${theme})`, async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("button", { name: "Entrar" })).toBeVisible();
    await setTheme(page, theme);
    expect(await scan(page)).toEqual([]);
  });

  test(`main screens have no WCAG A/AA violations (${theme})`, async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto("/login");
    await page.getByLabel("Usuário").fill(ADMIN);
    await page.getByLabel(/^Senha/).fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: "Entrar" }).click();
    await page.waitForURL((url) => !url.pathname.startsWith("/login"));

    const problems: string[] = [];
    for (const path of [
      "/",
      "/bots",
      "/bots/new",
      "/backtests",
      "/backtests/new",
      "/market-data",
      "/system",
      "/exchanges",
      "/audit",
    ]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await setTheme(page, theme);
      for (const problem of await scan(page)) problems.push(`${path}: ${problem}`);
    }
    expect(problems).toEqual([]);
  });
}
