---
title: "B. Hugging Face"
description: "Hugging Face, el ecosistema de modelos abiertos más usado en empresa, como laboratorio: elegir modelo, arquitecturas, clasificación, datasets e infraestructura del Hub"
---

:::note[Revisado: 2026-11]
Versiones con las que se construyó el anexo: `transformers` 5.22, `datasets` 5.1 y `huggingface_hub` 2.4, en CPU. Los modelos y datasets del Hub cambian a menudo; cada práctica guarda lo que encontró, y con `--grabadas` lo reproduce.
:::

Hugging Face es, en la práctica, el lugar donde vive el ecosistema de modelos abiertos: el Hub (modelos, datasets y aplicaciones de demostración), las librerías para usarlos (`transformers`, `datasets`, `huggingface_hub`) y servicios para servirlos. En una empresa que trabaja con modelos abiertos, lo normal es encontrárselo en algún punto: para elegir un modelo, para entrenar o ajustar uno, para versionar datasets o para enseñar una demo.

Este anexo es un laboratorio. No repite la documentación: la recorre con prácticas medidas, como el resto del curso, y deja la conclusión que más se olvida en los proyectos con LLMs. Para clasificar texto, un modelo pequeño y especializado del Hub puede acertar más que un LLM, y en la B.3 lo hace: 79 % frente a 66-68 %, unas cien veces más rápido que el LLM local y sin coste por llamada.

| Página | Qué aprendes | Práctica |
| --- | --- | --- |
| [B.1 El Hub y elegir modelo](../b1-el-hub-y-elegir-modelo/) | Leer una ficha, filtrar por tarea, idioma y licencia, y qué revisar antes de usar un modelo | `elegir_modelo.py` |
| [B.2 Encoder, decoder y encoder-decoder](../b2-encoder-decoder-y-encoder-decoder/) | Qué hace cada arquitectura, con qué clase de `transformers` se carga y cuándo usar cada una | `arquitecturas.py` |
| [B.3 Laboratorio: clasificador de sentimiento](../b3-laboratorio-clasificador-de-sentimiento/) | Encoders del Hub, un LLM sin ejemplos y embeddings con una regresión, medidos sobre el mismo test | `sentimiento.py` |
| [B.4 Datasets](../b4-datasets/) | Cargar, transformar y leer en streaming; subir un dataset propio, privado y versionado | `datasets_practica.py` |
| [B.5 El Hub como infraestructura](../b5-el-hub-como-infraestructura/) | Inference Providers, buckets, Spaces, Inference Endpoints y lo que añaden los planes de empresa | `hub_infra.py` |

## Antes de empezar

El código está en [`modulos/b-hugging-face/`](https://github.com/alejbrata/dev_to_ia_engineer/tree/main/modulos/b-hugging-face). Necesita `transformers` y `torch`, que pesan bastante (torch para CPU, unos 500 MB), así que no entran en la instalación base del curso. Instálalos con el grupo opcional:

```sh title="Terminal de VS Code · raíz del repo"
uv sync --group hf
```

Mientras hagas el anexo, usa siempre `uv sync --group hf`: un `uv sync` a secas quita lo que no está en la instalación base. Lo demás:

- **Cuenta en Hugging Face**: no hace falta para descargar modelos y datasets públicos. Un token de lectura en `.env` (`HF_TOKEN`) da más margen de peticiones.
- **Para subir cosas** (B.4 y B.5): un token con permiso de escritura. Todo lo que se crea es privado y gratis.
- **Ollama** con `qwen3:8b` y `bge-m3`, como en el módulo 5: la B.3 los compara con los modelos del Hub.
- **Opcional**: créditos de Inference Providers (incluidos en la cuenta PRO) para el LLM grande de la B.3 y el rol `chat_hf` (anexo G).
