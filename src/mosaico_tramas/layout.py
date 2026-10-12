"""Geometría de las páginas: celda, grilla, leyenda y sugerencias (design.md §7).

Todo se calcula en puntos PDF con el origen abajo a la izquierda (convención de ReportLab).
"""

import math

from mosaico_tramas.papel import mm_a_pt

# --- Bloque de leyenda (design.md §7.2) ---
ANCHO_ENTRADA_MM = 32
ALTO_ENTRADA_MM = 14
SEPARACION_LEYENDA_MM = 6
ALTO_INSTRUCCION_MM = 4.6
LADO_AMPLIADO_MM = 10


def entradas_por_fila(ancho_util_pt: float) -> int:
    """Cuántas entradas de leyenda entran a lo ancho (al menos una)."""
    return max(1, int(ancho_util_pt // mm_a_pt(ANCHO_ENTRADA_MM)))


def alto_leyenda(n: int, marca_blanco: bool, ancho_util_pt: float) -> float:
    """Alto total del bloque de leyenda en pt: separación + instrucción + filas de entradas."""
    entradas = n + (1 if marca_blanco else 0)
    filas = math.ceil(entradas / entradas_por_fila(ancho_util_pt))
    return mm_a_pt(SEPARACION_LEYENDA_MM + ALTO_INSTRUCCION_MM + filas * ALTO_ENTRADA_MM)
