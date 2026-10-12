"""Hoja de muestra de símbolos (RF2.8): para revisar la biblioteca o el subconjunto de un N."""

import io

from reportlab.pdfgen.canvas import Canvas

from mosaico_tramas.papel import REGISTRO_PAPELES, Orientacion, mm_a_pt
from mosaico_tramas.render_pdf import dibujar_simbolo, nuevo_canvas
from mosaico_tramas.simbolos.biblioteca import BIBLIOTECA
from mosaico_tramas.simbolos.primitivas import Simbolo
from mosaico_tramas.simbolos.raster import cobertura
from mosaico_tramas.simbolos.seleccion import elegir_simbolos

_MARGEN = mm_a_pt(12.7)
_ALTO_FILA = mm_a_pt(24)
_CELDA_REF = mm_a_pt(4)  # celda mínima: escala de referencia de la cobertura
_CELDA_GRANDE = mm_a_pt(20)
_PARCHE_CELDAS = 5  # parche de 5 × 5 celdas de 4 mm para ver cómo tramea
_GRIS_GRILLA = 0.65


def hoja_muestra(n: int | None) -> bytes:
    """PDF A4 con los símbolos elegidos para N (o la biblioteca completa si n es None)."""
    if n is None:
        simbolos = sorted(BIBLIOTECA, key=lambda s: (cobertura(s), s.id))
        titulo = "Symbol library (all candidates)"
    else:
        simbolos = list(elegir_simbolos(n))
        titulo = f"Symbol sample - N = {n}"

    ancho, alto = REGISTRO_PAPELES["A4"].tamano_pt(Orientacion.PORTRAIT)
    buffer = io.BytesIO()
    canvas = nuevo_canvas(buffer, (ancho, alto))
    filas_por_pagina = int((alto - 2 * _MARGEN - mm_a_pt(16)) // _ALTO_FILA)

    for inicio in range(0, len(simbolos), filas_por_pagina):
        if inicio:
            canvas.showPage()
        y = alto - _MARGEN
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(_MARGEN, y - 14, titulo)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            _MARGEN,
            y - 28,
            "Columns: level, id (family), ink coverage (0.5 mm pen), 4 mm cell, 20 mm cell, "
            "5x5 patch at 4 mm.",
        )
        y -= mm_a_pt(16)
        for indice, simbolo in enumerate(simbolos[inicio : inicio + filas_por_pagina], inicio):
            nivel = indice + 1 if n is not None else None
            _fila(canvas, simbolo, nivel, _MARGEN, y)
            y -= _ALTO_FILA

    canvas.save()
    return buffer.getvalue()


def _fila(canvas: Canvas, simbolo: Simbolo, nivel: int | None, x: float, y_sup: float) -> None:
    """Una fila de la hoja: textos, celda de 5 mm, celda de 20 mm y parche de 4 × 4."""
    centro_y = y_sup - _ALTO_FILA / 2
    canvas.setFillGray(0)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(x, centro_y - 4, str(nivel) if nivel is not None else "-")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(x + mm_a_pt(10), centro_y + 2, f"{simbolo.id} ({simbolo.familia})")
    canvas.drawString(x + mm_a_pt(10), centro_y - 9, f"{cobertura(simbolo):.1f}%")

    x_celda = x + mm_a_pt(55)
    _celda_con_borde(canvas, simbolo, x_celda, centro_y + _CELDA_REF / 2, _CELDA_REF)
    x_grande = x_celda + mm_a_pt(12)
    _celda_con_borde(canvas, simbolo, x_grande, centro_y + _CELDA_GRANDE / 2, _CELDA_GRANDE)

    x_parche = x_grande + mm_a_pt(28)
    lado_parche = _PARCHE_CELDAS * _CELDA_REF
    y_parche = centro_y + lado_parche / 2
    for fila in range(_PARCHE_CELDAS):
        for col in range(_PARCHE_CELDAS):
            dibujar_simbolo(
                canvas,
                simbolo,
                x_parche + col * _CELDA_REF,
                y_parche - fila * _CELDA_REF,
                _CELDA_REF,
            )
    canvas.setStrokeGray(_GRIS_GRILLA)
    canvas.setLineWidth(0.3)
    canvas.rect(x_parche, y_parche - lado_parche, lado_parche, lado_parche, stroke=1, fill=0)


def _celda_con_borde(canvas: Canvas, simbolo: Simbolo, x: float, y_sup: float, lado: float) -> None:
    dibujar_simbolo(canvas, simbolo, x, y_sup, lado)
    canvas.setStrokeGray(_GRIS_GRILLA)
    canvas.setLineWidth(0.3)
    canvas.rect(x, y_sup - lado, lado, lado, stroke=1, fill=0)
