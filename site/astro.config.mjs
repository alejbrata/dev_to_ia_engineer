// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// Generado desde docs/PLAN.md con `uv run python scripts/plan_sync.py`. No lo edites a mano.
import sidebar from './src/sidebar.json' with { type: 'json' };

// El identificador lo configura quien administra el despliegue en GitHub Actions.
// Sin él no se carga ningún script ni se envían datos de visitas.
const umamiWebsiteId = process.env.UMAMI_WEBSITE_ID?.trim();
const umamiDomain = new URL(process.env.SITIO_URL ?? 'https://alejbrata.github.io').hostname;

// https://astro.build/config
export default defineConfig({
	// Por defecto, GitHub Pages. Para otro servidor o dominio (deploy/README.md), se cambian
	// al construir: SITIO_URL=https://midominio.es SITIO_BASE=/ npm run build
	site: process.env.SITIO_URL ?? 'https://alejbrata.github.io',
	// Subruta de GitHub Pages. Los enlaces entre páginas son relativos y funcionan con cualquiera.
	base: process.env.SITIO_BASE ?? '/dev_to_ia_engineer',
	integrations: [
		starlight({
			title: 'Curso de AI Engineer',
			// Métricas de todas las lecciones sin cookies, solo si hay un Website ID.
			head: umamiWebsiteId ? [{
				tag: 'script',
				attrs: {
					defer: true,
					src: 'https://cloud.umami.is/script.js',
					'data-website-id': umamiWebsiteId,
					'data-domains': umamiDomain,
					'data-exclude-search': 'true',
					'data-exclude-hash': 'true',
					'data-do-not-track': 'true',
				},
			}] : [],
			// El español es el idioma raíz (sin prefijo en la URL).
			// Para añadir inglés: descomenta `en` y crea las páginas en src/content/docs/en/
			// con los mismos nombres de fichero.
			defaultLocale: 'root',
			locales: {
				root: { label: 'Español', lang: 'es' },
				// en: { label: 'English', lang: 'en' },
			},
			sidebar,
			customCss: [
				'@fontsource/ibm-plex-sans/400.css',
				'@fontsource/ibm-plex-sans/500.css',
				'@fontsource/ibm-plex-sans/600.css',
				'@fontsource/ibm-plex-mono/400.css',
				'@fontsource/ibm-plex-mono/500.css',
				'./src/styles/custom.css',
			],
			components: {
				// En la portada, una consola que reproduce una llamada real; en el resto, el Hero normal.
				Hero: './src/components/Hero.astro',
				PageTitle: './src/components/CursoPageTitle.astro',
			},
		}),
	],
});
