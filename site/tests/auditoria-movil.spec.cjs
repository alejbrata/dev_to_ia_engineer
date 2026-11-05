const { test, expect } = require('@playwright/test');
const { readdirSync } = require('node:fs');
const { join, relative, sep } = require('node:path');

// Recorrido representativo: portada, temario, los nueve módulos, sus retos y laboratorios.
const paginas = [
  '',
  '00-introduccion/01-la-rotacion/',
  '00-introduccion/04-entorno-de-trabajo/',
  '01-fundamentos-de-llms/01-como-funciona-un-llm/',
  '01-fundamentos-de-llms/03-sampling/',
  '01-fundamentos-de-llms/08-reto-del-modulo/',
  '02-prompting/06-tu-primera-eval/',
  '02-prompting/07-reto-del-modulo/',
  '03-rag/02-ingesta-y-chunking/',
  '03-rag/03-embeddings-y-bases-vectoriales/',
  '03-rag/09-reto-del-modulo/',
  '04-evals/05-evals-de-rag/',
  '05-agentes/09-sistemas-multiagente-desde-cero/',
  '05-agentes/16-reto-del-modulo/',
  '06-produccion/09-calidad-en-produccion/',
  '07-modelos-propios/05-fine-tuning-con-lora-qlora/',
  '08-proyecto-final/05-reto-del-modulo/',
  'anexos/g-apis-comerciales/',
];

for (const ancho of [320, 390, 768]) {
  test('móvil ' + ancho + 'px: sin desplazamiento horizontal de página', async ({ page }) => {
    test.setTimeout(240_000);
    await page.setViewportSize({ width: ancho, height: 844 });
    for (const ruta of paginas) {
      // Astro puede emitir una navegación/redirección al montar las páginas.
      // Reintentamos una medición interrumpida, pero no ocultamos desbordamientos.
      let medidas;
      for (let intento = 0; intento < 3; intento++) {
        await page.goto(ruta || './', { waitUntil: 'load' });
        try {
          await page.waitForLoadState('networkidle', { timeout: 10_000 });
          medidas = await page.evaluate(() => ({
            ancho: document.documentElement.clientWidth,
            contenido: document.documentElement.scrollWidth,
          }));
          break;
        } catch (error) {
          if (intento === 2 || !/navigation|Execution context was destroyed/i.test(String(error))) {
            throw error;
          }
        }
      }
      expect.soft(
        medidas.contenido - medidas.ancho,
        'Desbordamiento en ' + ruta + ' a ' + ancho + ' px',
      ).toBeLessThanOrEqual(2);
    }
  });
}

test('móvil: los atajos permiten saltar a práctica y autoevaluación', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('01-fundamentos-de-llms/03-sampling/');
  const saltos = page.locator('.curso-saltos');
  await expect(saltos).toBeVisible();
  const practica = saltos.getByRole('link', { name: 'Práctica' });
  await expect(practica).toHaveAttribute('href', '#práctica');
  await practica.click();
  await expect(page).toHaveURL(/#pr/);
  await expect(saltos.getByRole('link', { name: 'Autoevaluación' })).toBeVisible();
});

test('móvil: la autoevaluación se puede responder con teclado y da explicación', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto('01-fundamentos-de-llms/03-sampling/');
  const primera = page.locator('.autoevaluacion [data-pregunta]').first();
  const opcion = primera.getByRole('button').first();
  await opcion.focus();
  await page.keyboard.press('Enter');
  await expect(primera.locator('[data-explicacion]')).not.toBeEmpty();
});

test('móvil: temperatura, chunking y embeddings reaccionan a los controles', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('01-fundamentos-de-llms/03-sampling/');
  const temp = page.locator('.laboratorio').filter({ has: page.locator('[data-t]') });
  await temp.locator('[data-t]').fill('0.5');
  await expect(temp.locator('[data-valor]')).toHaveText('0.50');
  await temp.locator('[data-sortear]').click();
  await expect(temp.locator('[data-sorteo]')).not.toBeEmpty();

  await page.goto('03-rag/02-ingesta-y-chunking/');
  const chunk = page.locator('.lab-chunking');
  await chunk.locator('[data-modo]').selectOption('secciones');
  await expect(chunk.locator('[data-resumen]')).toContainText('fragmentos');
  await chunk.locator('[data-modo]').selectOption('fijo');
  await chunk.locator('[data-palabras]').fill('60');
  await expect(chunk.locator('[data-v-palabras]')).toHaveText('60');

  await page.goto('03-rag/03-embeddings-y-bases-vectoriales/');
  const emb = page.locator('.lab-embeddings');
  const opciones = emb.locator('[data-pregunta] option');
  expect(await opciones.count()).toBeGreaterThan(1);
  await emb.locator('[data-pregunta]').selectOption(await opciones.nth(1).getAttribute('value'));
  await expect(emb.locator('[data-vecinos] li').first()).toBeVisible();
});

test('móvil: el filtro de la tabla de evals y el área desplazable son utilizables', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto('02-prompting/06-tu-primera-eval/');
  const tabla = page.locator('.tabla-eval');
  await expect(tabla.locator('.desplazable')).toBeVisible();
  await tabla.locator('[data-filtro]').check();
  const ocultas = await tabla.locator('tbody tr.oculta').count();
  expect(ocultas).toBeGreaterThan(0);
});

// Derivado directamente del árbol de documentos: también prueba los enlaces que
// Starlight deja ocultos dentro de módulos plegados, sin abrirlos en el navegador.
function rutasDeDocumentos() {
  const raiz = join(__dirname, '..', 'src', 'content', 'docs');
  const archivos = [];
  const visitar = (dir) => {
    for (const entrada of readdirSync(dir, { withFileTypes: true })) {
      const archivo = join(dir, entrada.name);
      if (entrada.isDirectory()) visitar(archivo);
      else if (/\.mdx?$/.test(entrada.name)) archivos.push(archivo);
    }
  };
  visitar(raiz);
  return archivos.map((archivo) => relative(raiz, archivo)
    .split(sep).join('/')
    .replace(/\.mdx?$/, '')
    .replace(/(^|\/)index$/, '$1'))
    .filter((ruta) => ruta && ruta !== '404');
}

test('navegación: todas las páginas del curso y anexos responden sin 404', async ({ request }) => {
  test.setTimeout(240_000);
  const rutas = rutasDeDocumentos();
  expect(rutas.length).toBeGreaterThan(75);
  const incorrectos = [];
  for (let i = 0; i < rutas.length; i += 8) {
    const bloque = rutas.slice(i, i + 8);
    const resultados = await Promise.all(bloque.map(async (ruta) => {
      const url = '/dev_to_ia_engineer/' + ruta.replace(/\/?$/, '/') ;
      const resultado = await request.get(url, { failOnStatusCode: false });
      return { url, estado: resultado.status() };
    }));
    incorrectos.push(...resultados.filter((resultado) => resultado.estado >= 400));
  }
  expect(incorrectos, 'Páginas inexistentes o caídas').toEqual([]);
});
