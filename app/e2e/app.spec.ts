import { type Page, expect, test } from "@playwright/test";

const ADMIN = process.env["E2E_ADMIN_USER"] ?? "";
const ADMIN_PASSWORD = process.env["E2E_ADMIN_PASSWORD"] ?? "";
const VIEWER = process.env["E2E_VIEWER_USER"] ?? "";
const VIEWER_PASSWORD = process.env["E2E_VIEWER_PASSWORD"] ?? "";
const HAS_BACKEND = ADMIN !== "" && VIEWER !== "";

test.skip(!HAS_BACKEND, "needs the backend with E2E_* users (see docs/08-quality.md)");
test.describe.configure({ mode: "serial" });

const signIn = async (page: Page, user: string, password: string) => {
  await page.goto("/login");
  await page.getByLabel("Usuário").fill(user);
  await page.getByLabel(/^Senha/).fill(password);
  await page.getByRole("button", { name: "Entrar" }).click();
};

const signInAndWait = async (page: Page, user: string, password: string) => {
  await signIn(page, user, password);
  await page.waitForURL((url) => !url.pathname.startsWith("/login"));
};

const signInAdmin = (page: Page) => signInAndWait(page, ADMIN, ADMIN_PASSWORD);

test("a protected page sends an anonymous visitor to the login with a way back", async ({
  page,
}) => {
  await page.goto("/bots");
  await expect(page).toHaveURL(/\/login\?redirect=%2Fbots/);
  await expect(page.getByRole("button", { name: "Entrar" })).toBeVisible();
});

test("a wrong password gives one generic message", async ({ page }) => {
  await signIn(page, ADMIN, "not the right passphrase");
  await expect(page.getByText(/inválidos, ou conta temporariamente bloqueada/)).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});

test("login, reload keeps the session through the refresh cookie, logout ends it", async ({
  page,
}) => {
  await signInAdmin(page);
  await expect(page.getByRole("heading", { name: "Painel" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Painel" })).toBeVisible();
  await page.goto("/system");
  await expect(page.getByRole("heading", { name: "Status do sistema" })).toBeVisible();

  await page.getByRole("button", { name: /e2e-admin/ }).click();
  await page.getByRole("menuitem", { name: /sair/i }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/bots");
  await expect(page).toHaveURL(/\/login/);
});

test("the dashboard shows the totals per mode from the API", async ({ page }) => {
  await signInAdmin(page);
  await expect(page.getByRole("heading", { name: "Painel" })).toBeVisible();
  await expect(page.getByText("USDT").first()).toBeVisible();
  await expect(page.getByText("PAPER").first()).toBeVisible();
});

test("a viewer reads but cannot write", async ({ page }) => {
  await signInAndWait(page, VIEWER, VIEWER_PASSWORD);
  await page.goto("/bots");
  await expect(page.getByRole("heading", { name: "Bots" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Novo bot" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Kill switch/ })).toHaveCount(0);
  await page.goto("/bots/new");
  await expect(page.getByText(/acesso|permiss/i).first()).toBeVisible();
  await page.goto("/settings/users");
  await expect(page.getByText(/acesso|permiss/i).first()).toBeVisible();
});

test("an admin creates a paper bot, starts it and stops it", async ({ page }) => {
  const name = `e2e-bot-${Date.now()}`;
  await signInAdmin(page);
  await page.goto("/bots/new");
  await page.getByLabel(/^Nome/).fill(name);
  await page.getByRole("button", { name: "Criar bot" }).click();

  await expect(page.getByRole("heading", { name })).toBeVisible();
  await expect(page.getByText("PAPER").first()).toBeVisible();

  await page.getByRole("button", { name: "Iniciar", exact: true }).click();
  await expect(page.getByText(/Comando enviado|Aguardando o worker/).first()).toBeVisible();
  await expect(page.getByText("Rodando").first()).toBeVisible({ timeout: 45_000 });

  await page.getByRole("button", { name: "Parar" }).click();
  await expect(page.getByRole("dialog")).toContainText(`Parar bot ${name}?`);
  await page.getByRole("dialog").getByRole("button", { name: "Parar bot" }).click();
  await expect(page.getByText("Parado").first()).toBeVisible({ timeout: 45_000 });

  await page.getByRole("tab", { name: "Auditoria" }).click();
  await expect(page.getByRole("cell", { name: /bot\./ }).first()).toBeVisible();
});

test("promoting to live explains why it is unavailable instead of trying", async ({ page }) => {
  const name = `e2e-live-${Date.now()}`;
  await signInAdmin(page);
  await page.goto("/bots/new");
  await page.getByLabel(/^Nome/).fill(name);
  await page.getByRole("button", { name: "Criar bot" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();

  await page.getByRole("button", { name: /Promover para LIVE/ }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("O live não está disponível neste ambiente")).toBeVisible();
  await expect(dialog.getByText("LIVE_TRADING_ENABLED is off")).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Continuar" })).toBeDisabled();
});

test("the kill switch blocks starting and releasing it needs a reason", async ({ page }) => {
  const name = `e2e-kill-${Date.now()}`;
  await signInAdmin(page);
  await page.goto("/bots/new");
  await page.getByLabel(/^Nome/).fill(name);
  await page.getByRole("button", { name: "Criar bot" }).click();
  await expect(page.getByRole("heading", { name })).toBeVisible();

  await page.getByRole("button", { name: "Kill switch" }).click();
  await page
    .getByRole("dialog")
    .getByLabel(/Motivo/)
    .fill("teste e2e");
  await page.getByRole("dialog").getByRole("button", { name: "Ativar kill switch" }).click();
  try {
    await expect(page.getByText(/Kill switch ativo: nenhuma ordem/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Iniciar", exact: true })).toBeDisabled();
  } finally {
    await page.getByRole("button", { name: "Liberar kill switch" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Liberar", exact: true }).click();
    await expect(dialog.getByText("Informe o motivo.")).toBeVisible();
    await dialog.getByLabel(/Motivo/).fill("fim do teste e2e");
    await dialog.getByRole("button", { name: "Liberar", exact: true }).click();
    await expect(page.getByText(/Kill switch ativo: nenhuma ordem/)).toHaveCount(0);
  }
});

test("research and system screens load", async ({ page }) => {
  await signInAdmin(page);
  for (const [path, heading] of [
    ["/backtests", "Backtests"],
    ["/backtests/new", "Novo backtest"],
    ["/market-data", "Dados de mercado"],
    ["/exchanges", "Conexões"],
    ["/audit", "Auditoria"],
    ["/settings/users", "Usuários"],
    ["/settings/profile", "Meu perfil"],
  ] as const) {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
  }
});

test("key screens fit a 360 px phone without horizontal scroll", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await signInAdmin(page);
  for (const path of ["/", "/bots", "/backtests", "/market-data", "/system", "/exchanges"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(overflow, `horizontal overflow on ${path}`).toBe(false);
  }
});
