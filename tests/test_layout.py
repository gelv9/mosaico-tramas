"""Tests del cálculo de layout (T15–T18)."""

import pytest

from mosaico_tramas.layout import (
    ALTO_ENTRADA_MM,
    ANCHO_ENTRADA_MM,
    alto_leyenda,
    entradas_por_fila,
)
from mosaico_tramas.papel import REGISTRO_PAPELES, Orientacion, mm_a_pt

A4_ANCHO_UTIL = mm_a_pt(210 - 2 * 12.7)


# --- T15: alto de la leyenda ---


def test_alto_leyenda_n6_con_marca_en_a4_vertical():
    # 7 entradas (6 símbolos + vacío) en filas de 5 → 2 filas: 6 + 4,6 + 2 × 14 = 38,6 mm
    assert alto_leyenda(6, True, A4_ANCHO_UTIL) == pytest.approx(mm_a_pt(38.6), abs=0.01)


def test_alto_leyenda_sin_marca_tiene_una_entrada_menos():
    # 5 entradas en filas de 5 → 1 fila
    assert alto_leyenda(5, False, A4_ANCHO_UTIL) == pytest.approx(mm_a_pt(24.6), abs=0.01)


def test_entradas_por_fila_segun_ancho():
    assert entradas_por_fila(A4_ANCHO_UTIL) == 5
    ancho_a3_horizontal = REGISTRO_PAPELES["A3"].tamano_pt(Orientacion.LANDSCAPE)[0] - mm_a_pt(25.4)
    assert entradas_por_fila(ancho_a3_horizontal) == 12
    # Nunca menos de una entrada por fila
    assert entradas_por_fila(mm_a_pt(10)) == 1


def test_dimensiones_de_la_entrada():
    assert ANCHO_ENTRADA_MM == 32
    assert ALTO_ENTRADA_MM == 14
