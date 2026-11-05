const { test, expect } = require('@playwright/test');

const modulo = '01-fundamentos-de-llms/06-coste-y-latencia/';

test('el alumno puede marcar una lección y conservarla tras recargar', async ({ page }) => {
  await page.goto(modulo);
  const casilla = page.getByRole('checkbox', { name: 'Marcar como completada' });
  await expect(casilla).toBeVisible();
  await casilla.check();
  await expect(casilla).toBeChecked();
  await page.reload();
  await expect(page.getByRole('checkbox', { name: 'Marcar como completada' })).toBeChecked();
  await expect(page.locator('[data-curso-progreso]')).toContainText('1 /');
});

test('la portada recupera la última lección visitada', async ({ page }) => {
  await page.goto(modulo);
  await page.goto('./');
  const continuar = page.getByRole('link', { name: /Continuar:/ });
  await expect(continuar).toBeVisible();
  await continuar.click();
  await expect(page).toHaveURL(/01-fundamentos-de-llms\/06-coste-y-latencia/);
});

test('en móvil se puede abrir la lista de lecciones del módulo', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(modulo);
  const indice = page.locator('.curso-indice');
  await expect(indice).toBeVisible();
  await indice.locator('summary').click();
  await expect(indice.locator('a[aria-current="page"]')).toBeVisible();
  await expect(indice.locator('a')).toHaveCount(8);
});

test('el enlace para informar un error contiene la lección', async ({ page }) => {
  await page.goto(modulo);
  const enlace = page.getByRole('link', { name: 'Avisar de un error' });
  await expect(enlace).toHaveAttribute('href', /github.com\/alejbrata\/dev_to_ia_engineer\/issues\/new/);
  await expect(enlace).toHaveAttribute('href', /coste-y-latencia/);
});

test('los botones de copiar código funcionan después de navegar', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('00-introduccion/04-entorno-de-trabajo/');
  await page.goto(modulo);
  const copiar = page.getByRole('button', { name: /copiar|copy/i }).first();
  await expect(copiar).toBeAttached();
  await copiar.click();
  const texto = await page.evaluate(async () => navigator.clipboard.readText());
  expect(texto.trim().length).toBeGreaterThan(0);
});
