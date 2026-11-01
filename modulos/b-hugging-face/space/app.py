"""El Space del anexo B.5: el clasificador de sentimiento de la B.3, con una interfaz web.

Hugging Face ejecuta este fichero al arrancar el Space (ver README.md, `app_file`). El
modelo se descarga una vez, al arrancar; después cada petición tarda lo que tarda el encoder.
"""

import gradio as gr
from transformers import pipeline

MODELO = "UMUTeam/roberta-spanish-sentiment-analysis"
clasificador = pipeline("text-classification", model=MODELO, top_k=None)


def clasificar(texto: str) -> dict[str, float]:
    """La probabilidad de cada clase, que gr.Label muestra como barras."""
    return {s["label"]: s["score"] for s in clasificador([texto])[0]}


demo = gr.Interface(
    fn=clasificar,
    inputs=gr.Textbox(label="Texto", placeholder="Escribe un mensaje en español"),
    outputs=gr.Label(label="Sentimiento"),
    title="Clasificador de sentimiento",
    description=f"Modelo: {MODELO}. Ejemplo del anexo B del curso de AI Engineering.",
    examples=["Me encanta, llegó antes de lo previsto", "El pedido sigue sin aparecer"],
)

if __name__ == "__main__":
    demo.launch()
