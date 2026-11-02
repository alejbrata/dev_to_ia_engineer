"""Arrancar y parar servidores de inferencia para las prácticas del módulo 7.

llama.cpp se busca en el PATH o en la carpeta de LLAMA_CPP_DIR (en `.env`). vLLM se
arranca con su imagen oficial para CPU en Docker.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import httpx


def binario(nombre: str) -> str:
    """La ruta de un ejecutable de llama.cpp (llama-server, llama-quantize...)."""
    from dotenv import load_dotenv

    if ruta := shutil.which(nombre):
        return ruta
    load_dotenv()
    carpeta = os.environ.get("LLAMA_CPP_DIR")
    for candidato in [Path(carpeta) / nombre, Path(carpeta) / f"{nombre}.exe"] if carpeta else []:
        if candidato.exists():
            return str(candidato)
    raise FileNotFoundError(
        f"No encuentro {nombre}: añade llama.cpp al PATH o pon su carpeta en LLAMA_CPP_DIR"
    )


def esperar(url: str, segundos: float = 600) -> None:
    """Espera a que el servidor responda 200 en su ruta de salud."""
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        try:
            if httpx.get(url, timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise TimeoutError(f"{url} no respondió en {segundos:.0f} s")


class LlamaServer:
    """Un llama-server en primer plano mientras dura el bloque `with`. El registro del
    servidor queda en `self.registro`, para leer cómo se configuró."""

    def __init__(self, argumentos: list[str], puerto: int = 8081):
        self.argumentos = [*argumentos, "--port", str(puerto), "--host", "127.0.0.1"]
        self.url = f"http://127.0.0.1:{puerto}"
        self.registro = Path(tempfile.mkdtemp()) / "llama-server.log"

    def __enter__(self) -> LlamaServer:
        self._log = self.registro.open("w", encoding="utf-8")
        self.proceso = subprocess.Popen(
            [binario("llama-server"), *self.argumentos], stdout=self._log, stderr=self._log
        )
        esperar(f"{self.url}/health")
        return self

    def __exit__(self, *_) -> None:
        self.proceso.terminate()
        self.proceso.wait(timeout=30)
        self._log.close()

    def leer_registro(self) -> str:
        return self.registro.read_text(encoding="utf-8", errors="replace")


class VLLM:
    """vLLM con la imagen oficial para CPU, con la caché de Hugging Face montada."""

    IMAGEN = "vllm/vllm-openai-cpu:v0.33.0-x86_64"

    def __init__(self, modelo: str, argumentos: list[str], puerto: int = 8000):
        self.nombre = "curso-vllm"
        cache = Path.home() / ".cache" / "huggingface"
        self.orden = [
            "docker", "run", "-d", "--name", self.nombre,
            "-p", f"127.0.0.1:{puerto}:8000", "--shm-size=4g",
            "-v", f"{cache}:/root/.cache/huggingface",
            self.IMAGEN, modelo, *argumentos,
        ]  # fmt: skip
        self.url = f"http://127.0.0.1:{puerto}"

    def __enter__(self) -> VLLM:
        subprocess.run(["docker", "rm", "-f", self.nombre], capture_output=True)
        subprocess.run(self.orden, check=True, capture_output=True)
        limite = time.monotonic() + 1800  # en CPU, el arranque puede tardar muchos minutos
        while time.monotonic() < limite:
            try:
                if httpx.get(f"{self.url}/health", timeout=2).status_code == 200:
                    return self
            except httpx.HTTPError:
                pass
            if not self.vivo():
                self.ultimo_registro = self.registro()
                self.__exit__()
                raise RuntimeError("vLLM se paró al arrancar; ver ultimo_registro")
            time.sleep(2)
        self.ultimo_registro = self.registro()
        self.__exit__()
        raise TimeoutError("vLLM no respondió en 30 minutos")

    def vivo(self) -> bool:
        r = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", self.nombre],
            capture_output=True,
            text=True,
        )
        return r.stdout.strip() == "true"

    def registro(self) -> str:
        r = subprocess.run(["docker", "logs", self.nombre], capture_output=True, text=True)
        return r.stdout + r.stderr

    def __exit__(self, *_) -> None:
        subprocess.run(["docker", "rm", "-f", self.nombre], capture_output=True)
