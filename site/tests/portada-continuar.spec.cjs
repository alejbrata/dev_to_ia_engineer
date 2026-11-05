const { test, expect } = require('@playwright/test');

const CLAVE_COMPLETADAS = 'curso-ai-engineer:completadas:v1';
const CLAVE_ULTIMA = 'curso-ai-engineer:ultima:v1';

async function prepararProgreso(page, escenario) {
  await page.goto('./');
  const datos = await page.locator('[data-curso-modulos]').evaluate((panel, tipo) => {
    const modulos = JSON.parse(panel.dataset.cursoModulos);
    const todas = modulos.flatMap((modulo) => modulo.lecciones);
    let hechas = [];
    let ultima = null;
    let orden = null;
    let retomar = null;

    if (tipo === 'tres-marcadas') {
      hechas = todas.slice(0, 3).map((l) => l.id);
      ultima = todas[2].id;
      orden = todas[3].id;
    } else if (tipo === 'saltos') {
      hechas = [
        ...modulos[0].lecciones, ...modulos[1].lecciones,
        modulos[3].lecciones[0],
      ].map((l) => l.id);
      ultima = modulos[3].lecciones[0].id;
      orden = modulos[2].lecciones[0].id;
      retomar = modulos[3].lecciones[1].id;
    } else if (tipo === 'completo') {
      hechas = todas.map((l) => l.id);
      ultima = todas.at(-1).id;
    }

    localStorage.setItem('curso-ai-engineer:completadas:v1', JSON.stringify(hechas));
    if (ultima) {
      localStorage.setItem('curso-ai-engineer:ultima:v1', JSON.stringify({ id: ultima }));
    }
    return { orden, retomar, total: hechas.length };
  }, escenario);
  await page.reload();
  return datos;
}

test('alumno nuevo: el botón de portada sigue empezando en la primera lección', async ({ page }) => {
  await page.goto('./');
  const principal = page.locator('.portada .acciones a:first-child');
  await expect(principal.locator('[data-curso-boton-texto]')).toHaveText('Empezar el curso');
  await expect(principal).toHaveAttribute('href', /00-introduccion\/01-la-rotacion\/$/);
});

test('tres lecciones vistas: el botón principal abre la cuarta pendiente', async ({ page }) => {
  const datos = await prepararProgreso(page, 'tres-marcadas');
  const principal = page.locator('.portada .acciones a:first-child');
  await expect(page.locator('[data-global]')).toContainText('3 / 77');
  await expect(principal.locator('[data-curso-boton-texto]')).toHaveText('Continuar curso');
  await expect(principal).toHaveAttribute('href', new RegExp(datos.orden));
  await principal.click();
  await expect(page).toHaveURL(new RegExp(datos.orden));
  await expect(page.getByRole('checkbox', { name: 'Marcar como completada' })).not.toBeChecked();
});

test('progreso salteado: el principal sigue el temario, retomar sigue el módulo activo', async ({ page }) => {
  const datos = await prepararProgreso(page, 'saltos');
  await expect(page.locator('.portada .acciones a:first-child')).toHaveAttribute(
    'href', new RegExp(datos.orden),
  );
  await expect(page.locator('[data-accion-retomar]')).toHaveAttribute(
    'href', new RegExp(datos.retomar),
  );
});

test('curso completo: el botón principal permite revisar el progreso', async ({ page }) => {
  await prepararProgreso(page, 'completo');
  const principal = page.locator('.portada .acciones a:first-child');
  await expect(principal.locator('[data-curso-boton-texto]')).toHaveText('Ver tu progreso');
  await expect(principal).toHaveAttribute('href', '#progreso');
  await principal.click();
  await expect(page).toHaveURL(/#progreso$/);
});
