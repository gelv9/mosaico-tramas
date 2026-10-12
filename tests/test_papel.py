"""Tests del registro de papeles y la orientación (T2)."""

import pytest

from mosaico_tramas.errores import ConfigInvalidaError
from mosaico_tramas.papel import (
    REGISTRO_PAPELES,
    Orientacion,
    mm_a_pt,
    obtener_papel,
    papel_personalizado,
    resolver_orientacion,
)

# Medidas esperadas en puntos (RF5.1)
ESPERADOS_PT = {
    "A4": (595.28, 841.89),
    "LETTER": (612.0, 792.0),
    "A3": (841.89, 1190.55),
    "TABLOID": (792.0, 1224.0),
}


@pytest.mark.parametrize("nombre", sorted(ESPERADOS_PT))
def test_medidas_en_puntos(nombre: str):
    papel = REGISTRO_PAPELES[nombre]
    ancho, alto = ESPERADOS_PT[nombre]
    assert papel.tamano_pt(Orientacion.PORTRAIT) == pytest.approx((ancho, alto), abs=0.01)
    assert papel.tamano_pt(Orientacion.LANDSCAPE) == pytest.approx((alto, ancho), abs=0.01)


def test_mm_a_pt():
    assert mm_a_pt(25.4) == pytest.approx(72.0)


def test_registro_contiene_los_cuatro_papeles():
    assert set(REGISTRO_PAPELES) >= {"A4", "LETTER", "A3", "TABLOID"}


@pytest.mark.parametrize(
    ("ancho", "alto", "esperada"),
    [
        (1200, 800, Orientacion.LANDSCAPE),
        (800, 1200, Orientacion.PORTRAIT),
        (900, 900, Orientacion.PORTRAIT),
    ],
)
def test_orientacion_auto(ancho: int, alto: int, esperada: Orientacion):
    assert resolver_orientacion(Orientacion.AUTO, ancho, alto) is esperada


def test_orientacion_explicita_se_respeta():
    assert resolver_orientacion(Orientacion.PORTRAIT, 2000, 100) is Orientacion.PORTRAIT
    assert resolver_orientacion(Orientacion.LANDSCAPE, 100, 2000) is Orientacion.LANDSCAPE


def test_papel_personalizado_valido():
    papel = papel_personalizado(430, 600)
    assert papel.nombre == "CUSTOM"
    assert papel.tamano_pt(Orientacion.PORTRAIT) == pytest.approx((mm_a_pt(430), mm_a_pt(600)))


@pytest.mark.parametrize(("ancho", "alto"), [(99, 300), (300, 1201), (0, 0)])
def test_papel_personalizado_fuera_de_rango(ancho: float, alto: float):
    with pytest.raises(ConfigInvalidaError, match="entre 100 y 1200 mm"):
        papel_personalizado(ancho, alto)


def test_obtener_papel():
    assert obtener_papel("A4").nombre == "A4"
    assert obtener_papel("CUSTOM", (300, 400)).ancho_mm == 300
    with pytest.raises(ConfigInvalidaError, match="Papel desconocido"):
        obtener_papel("B5")
    with pytest.raises(ConfigInvalidaError, match="personalizado"):
        obtener_papel("CUSTOM")
