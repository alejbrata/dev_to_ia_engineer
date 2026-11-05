# site

Web del curso (Astro + Starlight).

```sh
npm install
npm run dev      # servidor local
npm run build    # build de producción en dist/
```

Las páginas viven en `src/content/docs/`. El sidebar (`src/sidebar.json`) y el esqueleto de las lecciones se generan desde `docs/PLAN.md` con `uv run python scripts/plan_sync.py`, desde la raíz del repo.

## Componentes interactivos y medidas reales

La portada y algunas lecciones usan componentes propios en `src/components/` (consola de la portada, visor de tokens, deslizador de temperatura, repetición del streaming). Los datos que muestran salen de `src/data/medidas.json`, grabado con llamadas reales al modelo del curso. Para regenerarlo, con Ollama arrancado y desde la raíz del repo:

```sh
uv run python scripts/datos_web.py
```


## Estadísticas de visitas (Umami Cloud)

La web admite analítica opcional con [Umami](https://umami.is/), sin banners, contadores ni cookies de seguimiento. **No se activa hasta configurar un identificador real**. La integración está preparada para el alojamiento GitHub Pages del curso; las páginas y las prácticas siguen funcionando sin Umami.

1. Crea una cuenta en [Umami Cloud](https://cloud.umami.is/signup) (el plan Hobby es gratuito) y selecciona, si te interesa, la región de datos de la UE.
2. En **Websites → Add website**, pon nombre `Curso AI Engineer` y dominio `alejbrata.github.io` (sin `https://` ni `/dev_to_ia_engineer`).
3. En **Websites → Edit → Tracking code** copia el valor de `data-website-id` (un UUID). **No copies el script entero**: ya lo integra Astro.
4. En GitHub, entra en **Settings → Secrets and variables → Actions → Variables → New repository variable** y añade `UMAMI_WEBSITE_ID` con ese UUID. No es una contraseña ni una API key; el ID se publicará en el HTML y es normal.
5. En **Actions → Despliegue → Run workflow** ejecuta el workflow sobre `main`. Así se recompila la web con el identificador configurado.
6. Abre la [web del curso](https://alejbrata.github.io/dev_to_ia_engineer/) sin un bloqueador de analítica y consulta el panel de Umami en **Websites → View**. Para comprobar la carga, usa el inspector del navegador (F12 → Network): busca `cloud.umami.is/script.js` y las peticiones de Umami. En `Pages` verás qué lecciones se visitan y en `Referrers`, los orígenes detectables del tráfico.

Las estadísticas comienzan **desde el momento de activación**, no recuperan visitas anteriores. La medición es aproximada: bloqueadores, DNT y otras condiciones pueden reducir el recuento. El script respeta **Do Not Track** y no recoge fragmentos (`#...`) ni parámetros de consulta (`?...`) de la URL. Solo registra datos del dominio indicado por `SITIO_URL` (por defecto, `alejbrata.github.io`), no del servidor de desarrollo local.

### Desactivar o cambiar de servicio

Borra la variable `UMAMI_WEBSITE_ID` en GitHub y vuelve a ejecutar **Despliegue**. Con el ID vacío, Astro no inyecta ningún script de analítica. En un despliegue propio, configura el ID en el entorno del proceso de **build**, además del dominio mediante `SITIO_URL`. Para usar Umami alojado por cuenta propia, habría que adaptar `src` a tu servidor.

La ausencia de cookies no implica automáticamente una exención de todas las obligaciones de privacidad. Revisa la información de privacidad y las condiciones de Umami antes de activar el seguimiento público.
