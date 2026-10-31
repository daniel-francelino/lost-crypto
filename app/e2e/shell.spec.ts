import { expect, test } from "@playwright/test";

test("the login page renders its form", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByLabel("Usuário")).toBeVisible();
  await expect(page.getByLabel(/^Senha/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Entrar" })).toBeVisible();
});

test("the backoffice shell renders with its navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Painel" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Painel" }).first()).toBeVisible();
});

test("an unknown address shows the not-found page inside the app", async ({ page }) => {
  await page.goto("/does-not-exist");
  await expect(page.getByText(/não encontrad/i).first()).toBeVisible();
});
