// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// Generado desde docs/PLAN.md con `uv run python scripts/plan_sync.py`. No lo edites a mano.
import sidebar from './src/sidebar.json' with { type: 'json' };

// https://astro.build/config
export default defineConfig({
	integrations: [
		starlight({
			title: 'Curso de AI Engineer',
			// El español es el idioma raíz (sin prefijo en la URL).
			// Para añadir inglés: descomenta `en` y crea las páginas en src/content/docs/en/
			// con los mismos nombres de fichero.
			defaultLocale: 'root',
			locales: {
				root: { label: 'Español', lang: 'es' },
				// en: { label: 'English', lang: 'en' },
			},
			sidebar,
			customCss: ['./src/styles/custom.css'],
		}),
	],
});
