import importlib


def test_modulos_importables() -> None:
    for nombre in ("curso_core", "curso_core.client", "curso_core.tracing", "curso_core.metrics"):
        assert importlib.import_module(nombre)
