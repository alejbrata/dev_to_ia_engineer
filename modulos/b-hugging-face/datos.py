"""Los tuits en español del dataset de Cardiff NLP, para los laboratorios del anexo B.

El repo del dataset trae un script de carga (`tweet_sentiment_multilingual.py`), que las
versiones actuales de `datasets` ya no ejecutan; por eso se cargan sus ficheros JSONL
directamente con rutas `hf://` (anexo B.4). Licencia: CC BY 3.0, más los términos de
Twitter; se descarga del Hub y no se redistribuye.
"""

from __future__ import annotations

REPO = "cardiffnlp/tweet_sentiment_multilingual"
BASE = f"hf://datasets/{REPO}/data/spanish/"
# Las etiquetas del dataset, en su orden: "0", "1" y "2" en los ficheros.
ETIQUETAS = ["negative", "neutral", "positive"]


def cargar(split: str) -> tuple[list[str], list[str]]:
    """Textos y etiquetas (por nombre) de un split: train, validation o test."""
    from datasets import load_dataset

    ds = load_dataset("json", data_files={split: f"{BASE}{split}.jsonl"}, split=split)
    return list(ds["text"]), [ETIQUETAS[int(e)] for e in ds["label"]]
