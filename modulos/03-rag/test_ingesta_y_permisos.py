"""Lecciones 07 y 08 sin modelos: extracción, copias, versiones, permisos y sincronización."""

from __future__ import annotations

import json
import tomllib

import httpx
import ingesta_real
import permisos
from curso_core import ClienteLLM
from curso_core import config as cfg
from curso_core.rag import IndiceVectorial

MANIFIESTO = tomllib.loads((ingesta_real.EMPRESA / "manifiesto.toml").read_text(encoding="utf-8"))


def _cliente(tmp_path) -> ClienteLLM:
    """Embeddings falsos: un vector por longitud del texto, suficiente para indexar."""

    def manejador(request: httpx.Request) -> httpx.Response:
        textos = json.loads(request.content)["input"]
        return httpx.Response(200, json={"embeddings": [[1.0, len(t) / 1000] for t in textos]})

    config = cfg.Config.model_validate(
        {
            "roles": {"embeddings": {"provider": "p", "model": "m"}},
            "providers": {"p": {"tipo": "ollama", "base_url": "http://p.test"}},
        }
    )
    return ClienteLLM(config, trazas=tmp_path / "t.jsonl", transport=httpx.MockTransport(manejador))


def test_la_extraccion_ingenua_pierde_la_tabla_del_docx() -> None:
    ruta = ingesta_real.ORIGINALES / "guardias.docx"
    assert "150 euros" not in ingesta_real.extraer_ingenuo(ruta)
    con_tablas = ingesta_real.extraer_con_tablas(ruta)
    assert "Guardia: Fin de semana; Compensación: 150 euros." in con_tablas
    assert "## Compensación" in con_tablas


def test_cada_fila_del_pdf_lleva_su_cabecera() -> None:
    texto = ingesta_real.extraer_con_tablas(ingesta_real.ORIGINALES / "proveedores-2026.pdf")
    assert "Proveedor: Mensatel; Servicio que presta: Envío de SMS" in texto
    assert "Coste mensual: 850 euros" in texto


def test_las_copias_se_encuentran_por_contenido() -> None:
    textos = {r.name: ingesta_real.extraer_con_tablas(r) for r in ingesta_real.ORIGINALES.iterdir()}
    _, quitados = ingesta_real.sin_duplicados(textos)
    assert sorted(quitados) == [
        ("Runbook pagos conexiones.pdf", "runbook-pagos-conexiones.md"),
        ("runbook-pagos-conexiones (copia).md", "runbook-pagos-conexiones.md"),
    ]


def test_de_cada_familia_queda_la_version_mas_reciente() -> None:
    textos = {"sla-2025.pdf": "viejo", "sla.md": "nuevo", "guardias.docx": "g"}
    assert set(ingesta_real.solo_vigentes(textos, MANIFIESTO)) == {"sla.md", "guardias.docx"}


def test_contiene_no_parte_numeros() -> None:
    assert not ingesta_real.contiene("Coste mensual: 4.200 euros", "200 euros")
    assert ingesta_real.contiene("Festivo: 200 euros.", "200 euros")


def test_sincronizar_solo_embebe_lo_que_cambia(tmp_path) -> None:
    indice, registro = IndiceVectorial(_cliente(tmp_path)), {}
    textos = {"sla.md": "# SLA\n\n## A\n\nuno\n\n## B\n\ndos", "guardias.docx": "# G\n\ntexto"}
    primera = permisos.sincronizar(indice, registro, textos, MANIFIESTO)
    assert primera == {"borrados": 0, "cambiados": 0, "nuevos": 2, "embebidos": 3}
    assert permisos.sincronizar(indice, registro, textos, MANIFIESTO)["embebidos"] == 0
    cambiados = {"sla.md": textos["sla.md"].replace("dos", "tres")}  # y guardias desaparece
    cuenta = permisos.sincronizar(indice, registro, cambiados, MANIFIESTO)
    assert cuenta == {"borrados": 1, "cambiados": 1, "nuevos": 0, "embebidos": 2}
    assert {f.doc for f in indice.fragmentos} == {"sla.md"}
    assert any("tres" in f.texto for f in indice.fragmentos)
    assert not any("dos" in f.texto for f in indice.fragmentos)


def test_filtrar_antes_no_deja_fugas_ni_huecos(tmp_path) -> None:
    indice = IndiceVectorial(_cliente(tmp_path))
    textos = {
        "postmortem-pagos-2026-03-interno.docx": "# P\n\n## A\n\nconfidencial\n\n## B\n\nmás",
        "guardias.docx": "# G\n\n## A\n\nuno\n\n## B\n\ndos\n\n## C\n\ntres",
    }
    permisos.sincronizar(indice, {}, textos, MANIFIESTO)
    plataforma = permisos.PERSONAS["Ana (Plataforma)"]
    for forma in ("filtro después", "filtro antes"):
        rs = permisos.buscar(indice, "pregunta", plataforma, forma)
        assert all(permisos.puede_ver(plataforma, r.fragmento) for r in rs)
    assert len(permisos.buscar(indice, "pregunta", plataforma, "filtro antes")) == 3
