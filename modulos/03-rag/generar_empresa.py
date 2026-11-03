"""Genera la documentación "de empresa" de las lecciones 07 y 08: la misma plataforma de este
módulo, pero con los documentos como suelen estar en una empresa.

En `datos/empresa/originales/`:

- `proveedores-2026.pdf`: una tabla de proveedores con celdas de varias líneas. Solo Finanzas.
- `sla-2025.pdf`: la versión anterior del SLA, con otras cifras. Sigue en la carpeta compartida.
- `sla.md`: el SLA vigente, el mismo de este módulo.
- `guardias.docx`: la política de guardias, con la compensación en una tabla.
- `postmortem-pagos-2026-03-interno.docx`: el postmortem con nombres y notas internas. Solo
  el equipo Cobros.
- `runbook-pagos-conexiones.md`, su copia (`... (copia).md`) y su exportación a PDF.
- Dos runbooks más del módulo, tal cual.

`datos/empresa/manifiesto.toml` dice, para cada fichero, a qué familia de documentos pertenece,
su fecha y qué grupos pueden verlo: es lo que daría un gestor documental. Los nombres de
personas son inventados. Necesita el grupo de desarrollo (fpdf2).
Uso: `uv run python modulos/03-rag/generar_empresa.py`
"""

from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document
from fpdf import FPDF

AQUI = Path(__file__).resolve().parent
DOCS = AQUI / "datos" / "docs"
EMPRESA = AQUI / "datos" / "empresa"
ORIGINALES = EMPRESA / "originales"

PROVEEDORES = [
    ("Proveedor", "Servicio que presta", "Coste mensual", "Renovación del contrato"),
    (
        "Pagonet",
        "Pasarela de pago con tarjeta para los cobros de la tienda",
        "4.200 euros",
        "enero",
    ),
    ("Mensatel", "Envío de SMS de verificación y de avisos de envío", "850 euros", "junio"),
    ("Nubecast", "CDN de las imágenes del catálogo", "1.300 euros", "marzo"),
    ("Indexa", "OpenSearch gestionado para la búsqueda de la tienda", "2.100 euros", "septiembre"),
]
SLA_2025 = [
    ("Servicio", "Disponibilidad"),
    ("pagos", "99,9 %"),
    ("usuarios", "99,5 %"),
    ("catalogo", "99,5 %"),
    ("notificaciones", "99,9 %"),
    ("busqueda", "99,0 %"),
]
COMPENSACION = [
    ("Guardia", "Compensación"),
    ("Semana de lunes a viernes", "un día libre"),
    ("Fin de semana", "150 euros"),
    ("Festivo", "200 euros"),
]


def pdf(titulo: str) -> FPDF:
    documento = FPDF()
    documento.set_auto_page_break(auto=True, margin=15)
    documento.add_page()
    documento.set_font("Helvetica", "B", 15)
    documento.cell(0, 10, titulo, new_x="LMARGIN", new_y="NEXT")
    documento.set_font("Helvetica", size=11)
    return documento


def tabla_pdf(documento: FPDF, filas: list[tuple[str, ...]], anchos: tuple[int, ...]) -> None:
    with documento.table(col_widths=anchos, text_align="LEFT") as tabla:
        for fila in filas:
            celdas = tabla.row()
            for texto in fila:
                celdas.cell(texto)


def parrafo(documento: FPDF, texto: str) -> None:
    documento.ln(3)
    documento.multi_cell(0, 6, texto, new_x="LMARGIN", new_y="NEXT")


def proveedores() -> None:
    d = pdf("Proveedores externos de la plataforma (2026)")
    parrafo(d, "Documento de Finanzas. Contratos vigentes y su coste. Uso interno de Finanzas.")
    d.ln(3)
    tabla_pdf(d, PROVEEDORES, (25, 75, 30, 40))
    parrafo(d, "Los costes no incluyen IVA. Las renovaciones se negocian dos meses antes.")
    d.output(str(ORIGINALES / "proveedores-2026.pdf"))


def sla_2025() -> None:
    d = pdf("Acuerdos de nivel de servicio (SLA)")
    parrafo(d, "Documento revisado en enero de 2025.")
    d.set_font("Helvetica", "B", 12)
    d.cell(0, 10, "Disponibilidad mensual comprometida", new_x="LMARGIN", new_y="NEXT")
    d.set_font("Helvetica", size=11)
    tabla_pdf(d, SLA_2025, (60, 60))
    d.output(str(ORIGINALES / "sla-2025.pdf"))


def runbook_pdf() -> None:
    """La exportación a PDF del runbook en Markdown, como la que hace cualquier wiki."""
    lineas = (DOCS / "runbook-pagos-conexiones.md").read_text(encoding="utf-8").splitlines()
    d = pdf(lineas[0].removeprefix("# "))
    for linea in lineas[1:]:
        if linea.startswith("## "):
            d.set_font("Helvetica", "B", 12)
            d.cell(0, 10, linea[3:], new_x="LMARGIN", new_y="NEXT")
            d.set_font("Helvetica", size=11)
        elif linea.strip():
            d.multi_cell(0, 6, linea, new_x="LMARGIN", new_y="NEXT")
    d.output(str(ORIGINALES / "Runbook pagos conexiones.pdf"))


def guardias() -> None:
    d = Document()
    d.add_heading("Política de guardias", level=1)
    d.add_paragraph("Cada equipo tiene una persona de guardia por semana, de lunes a lunes.")
    d.add_heading("Responsabilidades", level=2)
    d.add_paragraph(
        "La persona de guardia atiende las alertas de producción de su equipo. Tiene que "
        "confirmar la alerta en 15 minutos como máximo."
    )
    d.add_heading("Compensación", level=2)
    d.add_paragraph("La guardia se compensa según cuándo se haga:")
    tabla = d.add_table(rows=0, cols=2)
    for fila in COMPENSACION:
        celdas = tabla.add_row().cells
        celdas[0].text, celdas[1].text = fila
    d.add_paragraph("La compensación se cobra en la nómina del mes siguiente.")
    d.save(str(ORIGINALES / "guardias.docx"))


def postmortem_interno() -> None:
    d = Document()
    d.add_heading("Postmortem interno: caída de pagos de marzo de 2026", level=1)
    d.add_paragraph("Uso interno del equipo Cobros. No compartir fuera del equipo.")
    d.add_heading("Quién participó", level=2)
    d.add_paragraph(
        "Laura Méndez lideró la respuesta al incidente. Iván Soler estaba de guardia y no "
        "confirmó la alerta hasta 25 minutos después: se ha hablado con él en privado."
    )
    d.add_heading("Coste", level=2)
    d.add_paragraph("Se estima una pérdida de 38.000 euros en cobros que no se completaron.")
    d.save(str(ORIGINALES / "postmortem-pagos-2026-03-interno.docx"))


def main() -> None:
    ORIGINALES.mkdir(parents=True, exist_ok=True)
    proveedores()
    sla_2025()
    runbook_pdf()
    guardias()
    postmortem_interno()
    for nombre in ("sla", "runbook-pagos-conexiones", "runbook-notificaciones-push",
                   "runbook-busqueda-disco"):  # fmt: skip
        shutil.copy(DOCS / f"{nombre}.md", ORIGINALES / f"{nombre}.md")
    shutil.copy(
        DOCS / "runbook-pagos-conexiones.md", ORIGINALES / "runbook-pagos-conexiones (copia).md"
    )
    print(f"{len(list(ORIGINALES.iterdir()))} ficheros en {ORIGINALES}")


if __name__ == "__main__":
    main()
