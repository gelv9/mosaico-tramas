"""Tests de la biblioteca de símbolos (T5)."""

import pytest

from mosaico_tramas.simbolos.biblioteca import BIBLIOTECA, ID_LLENO, ID_PUNTO, POR_ID
from mosaico_tramas.simbolos.primitivas import Linea, Poligono, Punto
from mosaico_tramas.simbolos.raster import cobertura

# Coberturas de design.md §4.2 (%)
COBERTURAS_DISENO = {
    "punto": 2.0,
    "diag1": 9.9,
    "diag2": 13.2,
    "diag3": 19.8,
    "horiz1": 7.1,
    "horiz2": 14.3,
    "horiz3": 21.4,
    "vert1": 7.1,
    "cruz": 13.8,
    "aspa1": 19.3,
    "aspa2": 24.3,
    "aspa3": 36.5,
    "reja1": 26.5,
    "reja2": 38.3,
    "asterisco": 31.6,
    "bloque50": 25.1,
    "bloque60": 36.2,
    "triangulo": 50.1,
    "tri_rayas": 59.9,
    "mitad_rayas": 64.3,
    "tres_cuartos": 75.1,
    "esquina": 87.5,
    "lleno": 100.0,
}


def test_al_menos_14_candidatos_con_ids_unicos():
    assert len(BIBLIOTECA) >= 14
    assert len(POR_ID) == len(BIBLIOTECA)


def test_extremos_fijos_existen():
    assert ID_PUNTO in POR_ID
    assert ID_LLENO in POR_ID
    assert cobertura(POR_ID[ID_LLENO]) == pytest.approx(100.0, abs=0.01)


@pytest.mark.parametrize("simbolo", BIBLIOTECA, ids=lambda s: s.id)
def test_dibujable_a_mano(simbolo):
    # RF2.6: como máximo 6 trazos, solo rectas, puntos y rellenos
    assert 1 <= simbolo.trazos <= 6
    for primitiva in simbolo.primitivas:
        assert isinstance(primitiva, Linea | Punto | Poligono)


@pytest.mark.parametrize("simbolo", BIBLIOTECA, ids=lambda s: s.id)
def test_coordenadas_dentro_de_la_celda(simbolo):
    for primitiva in simbolo.primitivas:
        match primitiva:
            case Linea(p0, p1):
                puntos = [p0, p1]
            case Poligono(vertices):
                puntos = list(vertices)
            case Punto(radio):
                assert 0 < radio < 0.5
                puntos = []
        for x, y in puntos:
            assert 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0


@pytest.mark.parametrize("simbolo", BIBLIOTECA, ids=lambda s: s.id)
def test_cobertura_coincide_con_el_diseno(simbolo):
    assert cobertura(simbolo) == pytest.approx(COBERTURAS_DISENO[simbolo.id], abs=1.0)


def test_cada_simbolo_tiene_familia_y_nombre_en_ingles():
    for simbolo in BIBLIOTECA:
        assert simbolo.familia
        assert simbolo.nombre_en.isascii()
