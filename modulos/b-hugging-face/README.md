# Anexo B — Hugging Face

Prácticas del anexo B (Hugging Face en la práctica). Necesitan el grupo opcional de
dependencias, con `transformers` y `torch` para CPU:

```sh
uv sync --group hf
```

- `elegir_modelo.py`: busca en el Hub los modelos para una tarea e idioma y señala lo que hay que revisar (licencia, datos de entrenamiento, safetensors) (B.1).
- `arquitecturas.py`: un encoder, un encoder-decoder y un decoder sobre los mismos tickets, con su coste (B.2).
- `sentimiento.py` y `datos.py`: el laboratorio de clasificación de sentimiento: encoders del Hub, un LLM sin ejemplos y embeddings con regresión logística, sobre los tuits en español de Cardiff NLP (B.3).
- `datasets_practica.py`: la librería `datasets` y la subida de un dataset propio, privado (`--subir`) (B.4).
- `hub_infra.py` y `space/`: Inference Providers, hardware, un bucket y un Space privados (`--crear`) (B.5).
- `test_hugging_face.py`: las alertas de la B.1 y las métricas de la B.3, sin red ni modelos.
- `resultados/`: lo que encontró cada práctica. Con `--grabadas`, se reutiliza sin llamar a nada.

Subir y crear (`--subir`, `--crear`) necesita `HF_TOKEN` con permiso de escritura en `.env`.
