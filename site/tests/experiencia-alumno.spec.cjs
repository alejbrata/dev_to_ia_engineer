const { test, expect } = require('@playwright/test');

const modulo = '01-fundamentos-de-llms/06-coste-y-latencia/';
const CLAVE_COMPLETADAS = 'curso-ai-engineer:completadas:v1';
const CLAVE_ULTIMA = 'curso-ai-engineer:ultima:v1';

async function montarEscenario(page, crear) {
  await page.goto('./');
  const escenario = await page.locator('[data-curso-modulos]').evaluate((element, claves) => {
    const modulos = JSON.parse(element.dataset.cursoModulos);
    const m = (n) => modulos.find((grupo) => grupo.id.startsWith(String(n).padStart(2, '0') + '-'));
    const todos = modulos.flatMap((grupo) => grupo.lecciones);
    let datos;
    if (claves.tipo === 'inicio-parcial') datos = {
      completadas: m(0).lecciones.slice(0, 3).map((l) => l.id),
      ultima: m(0).lecciones[2].id,
      orden: m(0).lecciones[3].id,
    };
    else if (claves.tipo === 'saltos') datos = {
      completadas: [...m(0).lecciones, ...m(1).lecciones, m(3).lecciones[0]].map((l) => l.id),
      ultima: m(3).lecciones[0].id, orden: m(2).lecciones[0].id,
      retomar: m(3).lecciones[1].id, m1: m(1).id, m3: m(3).id,
    };
    else if (claves.tipo === 'modulo-terminado') datos = {
      completadas: [...m(0).lecciones, ...m(1).lecciones].map((l) => l.id),
      ultima: m(1).lecciones.at(-1).id,
      orden: m(2).lecciones[0].id, retomar: m(2).lecciones[0].id,
    };
    else if (claves.tipo === 'todo') datos = {
      completadas: todos.map((l) => l.id), ultima: todos.at(-1).id,
    };
    else datos = {
      completadas: ['otra-carpeta/pagina', m(1).lecciones[0].id],
      ultima: 'https://example.com/malicioso',
      orden: m(0).lecciones[0].id,
    };
    localStorage.setItem(claves.completadas, JSON.stringify(datos.completadas));
    if (datos.ultima) localStorage.setItem(claves.ultima, JSON.stringify({ id: datos.ultima }));
    return datos;
  }, { tipo: crear, completadas: CLAVE_COMPLETADAS, ultima: CLAVE_ULTIMA });
  await page.reload();
  return escenario;
}

test('el alumno puede marcar una lección y conservarla tras recargar', async ({ page }) => {
  await page.goto(modulo);
  const casilla = page.getByRole('checkbox', { name: 'Marcar como completada' });
  await expect(casilla).toBeVisible();
  await casilla.check();
  await expect(casilla).toBeChecked();
  await page.reload();
  await expect(page.getByRole('checkbox', { name: 'Marcar como completada' })).toBeChecked();
  await expect(page.locator('[data-curso-progreso]')).toContainText('1 / 77');
  await expect(page.locator('[data-curso-progreso]')).toContainText('este módulo: 1 / 8');
});

test('el botón principal empieza desde cero para un alumno nuevo', async ({ page }) => {
  await page.goto('./');
  const inicio = page.locator('.portada .acciones a:first-child');
  await expect(inicio).toHaveText('Empezar el curso');
  await expect(inicio).toHaveAttribute('href', /00-introduccion\/01-la-rotacion\/$/);
});

test('el botón de la portada avanza a la primera lección pendiente', async ({ page }) => {
  const datos = await montarEscenario(page, 'inicio-parcial');
  const inicio = page.locator('.portada .acciones a:first-child');
  await expect(page.locator('[data-global]')).toContainText('3 / 77');
  await expect(inicio).toHaveText('Continuar curso');
  await expect(inicio).toHaveAttribute('href', new RegExp(datos.orden + '/
  await page.goto(modulo);
  await page.goto('./');
  const retomar = page.locator('[data-accion-retomar]');
  await expect(retomar).toBeVisible();
  await expect(retomar).toHaveAttribute('href', /01-fundamentos-de-llms\/06-coste-y-latencia\/$/);
  await retomar.click();
  await expect(page).toHaveURL(/01-fundamentos-de-llms\/06-coste-y-latencia/);
});

test('si termina módulo 1 y hace una lección del 3, puede retomar 3 o continuar 2', async ({ page }) => {
  const datos = await montarEscenario(page, 'saltos');
  const retomar = page.locator('[data-accion-retomar]');
  const orden = page.locator('[data-accion-orden]');
  await expect(retomar).toHaveAttribute('href', new RegExp(datos.retomar + '/$'));
  await expect(orden).toHaveAttribute('href', new RegExp(datos.orden + '/$'));
  await expect(page.locator('[data-retomar-modulo]')).toContainText('Módulo 3');
  await expect(page.locator('[data-orden-modulo]')).toContainText('Módulo 2');

  await page.locator('.curso-desglose summary').click();
  await expect(page.locator('[data-modulo="' + datos.m1 + '"] progress')).toHaveJSProperty('value', 8);
  await expect(page.locator('[data-modulo="' + datos.m3 + '"] progress')).toHaveJSProperty('value', 1);
});

test('si se completa el último módulo visitado, retomar propone el siguiente pendiente', async ({ page }) => {
  const datos = await montarEscenario(page, 'modulo-terminado');
  await expect(page.locator('[data-accion-retomar]')).toHaveAttribute(
    'href', new RegExp(datos.retomar + '/$'),
  );
  await expect(page.locator('[data-accion-orden]')).toHaveAttribute(
    'href', new RegExp(datos.orden + '/$'),
  );
});

test('con todas las páginas marcadas no manda al inicio', async ({ page }) => {
  await montarEscenario(page, 'todo');
  await expect(page.locator('[data-acciones]')).toBeHidden();
  await expect(page.locator('[data-curso-finalizado]')).toBeVisible();
  await expect(page.locator('[data-global]')).toContainText('77 / 77');
});

test('las páginas antiguas o desconocidas no inflan las cifras ni generan enlaces inseguros', async ({ page }) => {
  const datos = await montarEscenario(page, 'desconocidos');
  await expect(page.locator('[data-global]')).toContainText('1 / 77');
  await expect(page.locator('[data-accion-orden]')).toHaveAttribute(
    'href', new RegExp(datos.orden + '/$'),
  );
  await expect(page.locator('[data-bloque-retomar]')).toBeHidden();
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
));
  await inicio.click();
  await expect(page).toHaveURL(new RegExp(datos.orden + '/
  await page.goto(modulo);
  await page.goto('./');
  const retomar = page.locator('[data-accion-retomar]');
  await expect(retomar).toBeVisible();
  await expect(retomar).toHaveAttribute('href', /01-fundamentos-de-llms\/06-coste-y-latencia\/$/);
  await retomar.click();
  await expect(page).toHaveURL(/01-fundamentos-de-llms\/06-coste-y-latencia/);
});

test('si termina módulo 1 y hace una lección del 3, puede retomar 3 o continuar 2', async ({ page }) => {
  const datos = await montarEscenario(page, 'saltos');
  const retomar = page.locator('[data-accion-retomar]');
  const orden = page.locator('[data-accion-orden]');
  await expect(retomar).toHaveAttribute('href', new RegExp(datos.retomar + '/$'));
  await expect(orden).toHaveAttribute('href', new RegExp(datos.orden + '/$'));
  await expect(page.locator('[data-retomar-modulo]')).toContainText('Módulo 3');
  await expect(page.locator('[data-orden-modulo]')).toContainText('Módulo 2');

  await page.locator('.curso-desglose summary').click();
  await expect(page.locator('[data-modulo="' + datos.m1 + '"] progress')).toHaveJSProperty('value', 8);
  await expect(page.locator('[data-modulo="' + datos.m3 + '"] progress')).toHaveJSProperty('value', 1);
});

test('si se completa el último módulo visitado, retomar propone el siguiente pendiente', async ({ page }) => {
  const datos = await montarEscenario(page, 'modulo-terminado');
  await expect(page.locator('[data-accion-retomar]')).toHaveAttribute(
    'href', new RegExp(datos.retomar + '/$'),
  );
  await expect(page.locator('[data-accion-orden]')).toHaveAttribute(
    'href', new RegExp(datos.orden + '/$'),
  );
});

test('con todas las páginas marcadas no manda al inicio', async ({ page }) => {
  await montarEscenario(page, 'todo');
  await expect(page.locator('[data-acciones]')).toBeHidden();
  await expect(page.locator('[data-curso-finalizado]')).toBeVisible();
  await expect(page.locator('[data-global]')).toContainText('77 / 77');
});

test('las páginas antiguas o desconocidas no inflan las cifras ni generan enlaces inseguros', async ({ page }) => {
  const datos = await montarEscenario(page, 'desconocidos');
  await expect(page.locator('[data-global]')).toContainText('1 / 77');
  await expect(page.locator('[data-accion-orden]')).toHaveAttribute(
    'href', new RegExp(datos.orden + '/$'),
  );
  await expect(page.locator('[data-bloque-retomar]')).toBeHidden();
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
));
  await expect(page.getByRole('checkbox', { name: 'Marcar como completada' })).not.toBeChecked();
});

test('el botón principal respeta el temario en orden aunque la última visita sea al módulo 3', async ({ page }) => {
  const datos = await montarEscenario(page, 'saltos');
  await expect(page.locator('.portada .acciones a:first-child')).toHaveAttribute(
    'href', new RegExp(datos.orden + '/
  await page.goto(modulo);
  await page.goto('./');
  const retomar = page.locator('[data-accion-retomar]');
  await expect(retomar).toBeVisible();
  await expect(retomar).toHaveAttribute('href', /01-fundamentos-de-llms\/06-coste-y-latencia\/$/);
  await retomar.click();
  await expect(page).toHaveURL(/01-fundamentos-de-llms\/06-coste-y-latencia/);
});

test('si termina módulo 1 y hace una lección del 3, puede retomar 3 o continuar 2', async ({ page }) => {
  const datos = await montarEscenario(page, 'saltos');
  const retomar = page.locator('[data-accion-retomar]');
  const orden = page.locator('[data-accion-orden]');
  await expect(retomar).toHaveAttribute('href', new RegExp(datos.retomar + '/$'));
  await expect(orden).toHaveAttribute('href', new RegExp(datos.orden + '/$'));
  await expect(page.locator('[data-retomar-modulo]')).toContainText('Módulo 3');
  await expect(page.locator('[data-orden-modulo]')).toContainText('Módulo 2');

  await page.locator('.curso-desglose summary').click();
  await expect(page.locator('[data-modulo="' + datos.m1 + '"] progress')).toHaveJSProperty('value', 8);
  await expect(page.locator('[data-modulo="' + datos.m3 + '"] progress')).toHaveJSProperty('value', 1);
});

test('si se completa el último módulo visitado, retomar propone el siguiente pendiente', async ({ page }) => {
  const datos = await montarEscenario(page, 'modulo-terminado');
  await expect(page.locator('[data-accion-retomar]')).toHaveAttribute(
    'href', new RegExp(datos.retomar + '/$'),
  );
  await expect(page.locator('[data-accion-orden]')).toHaveAttribute(
    'href', new RegExp(datos.orden + '/$'),
  );
});

test('con todas las páginas marcadas no manda al inicio', async ({ page }) => {
  await montarEscenario(page, 'todo');
  await expect(page.locator('[data-acciones]')).toBeHidden();
  await expect(page.locator('[data-curso-finalizado]')).toBeVisible();
  await expect(page.locator('[data-global]')).toContainText('77 / 77');
});

test('las páginas antiguas o desconocidas no inflan las cifras ni generan enlaces inseguros', async ({ page }) => {
  const datos = await montarEscenario(page, 'desconocidos');
  await expect(page.locator('[data-global]')).toContainText('1 / 77');
  await expect(page.locator('[data-accion-orden]')).toHaveAttribute(
    'href', new RegExp(datos.orden + '/$'),
  );
  await expect(page.locator('[data-bloque-retomar]')).toBeHidden();
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
),
  );
});

test('cuando el curso está completo el botón principal abre el resumen de progreso', async ({ page }) => {
  await montarEscenario(page, 'todo');
  const inicio = page.locator('.portada .acciones a:first-child');
  await expect(inicio).toHaveText('Ver tu progreso');
  await expect(inicio).toHaveAttribute('href', '#progreso');
  await inicio.click();
  await expect(page).toHaveURL(/#progreso$/);
});

test('retomar mantiene la última lección si todavía no se completó', async ({ page }) => {
  await page.goto(modulo);
  await page.goto('./');
  const retomar = page.locator('[data-accion-retomar]');
  await expect(retomar).toBeVisible();
  await expect(retomar).toHaveAttribute('href', /01-fundamentos-de-llms\/06-coste-y-latencia\/$/);
  await retomar.click();
  await expect(page).toHaveURL(/01-fundamentos-de-llms\/06-coste-y-latencia/);
});

test('si termina módulo 1 y hace una lección del 3, puede retomar 3 o continuar 2', async ({ page }) => {
  const datos = await montarEscenario(page, 'saltos');
  const retomar = page.locator('[data-accion-retomar]');
  const orden = page.locator('[data-accion-orden]');
  await expect(retomar).toHaveAttribute('href', new RegExp(datos.retomar + '/$'));
  await expect(orden).toHaveAttribute('href', new RegExp(datos.orden + '/$'));
  await expect(page.locator('[data-retomar-modulo]')).toContainText('Módulo 3');
  await expect(page.locator('[data-orden-modulo]')).toContainText('Módulo 2');

  await page.locator('.curso-desglose summary').click();
  await expect(page.locator('[data-modulo="' + datos.m1 + '"] progress')).toHaveJSProperty('value', 8);
  await expect(page.locator('[data-modulo="' + datos.m3 + '"] progress')).toHaveJSProperty('value', 1);
});

test('si se completa el último módulo visitado, retomar propone el siguiente pendiente', async ({ page }) => {
  const datos = await montarEscenario(page, 'modulo-terminado');
  await expect(page.locator('[data-accion-retomar]')).toHaveAttribute(
    'href', new RegExp(datos.retomar + '/$'),
  );
  await expect(page.locator('[data-accion-orden]')).toHaveAttribute(
    'href', new RegExp(datos.orden + '/$'),
  );
});

test('con todas las páginas marcadas no manda al inicio', async ({ page }) => {
  await montarEscenario(page, 'todo');
  await expect(page.locator('[data-acciones]')).toBeHidden();
  await expect(page.locator('[data-curso-finalizado]')).toBeVisible();
  await expect(page.locator('[data-global]')).toContainText('77 / 77');
});

test('las páginas antiguas o desconocidas no inflan las cifras ni generan enlaces inseguros', async ({ page }) => {
  const datos = await montarEscenario(page, 'desconocidos');
  await expect(page.locator('[data-global]')).toContainText('1 / 77');
  await expect(page.locator('[data-accion-orden]')).toHaveAttribute(
    'href', new RegExp(datos.orden + '/$'),
  );
  await expect(page.locator('[data-bloque-retomar]')).toBeHidden();
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
