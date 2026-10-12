"""Tests de primitivas, rasterizado y cobertura de tinta (T4)."""

import numpy as np
import pytest

from mosaico_tramas.simbolos.primitivas import TRAZO_REL, Linea, Poligono, Punto, Simbolo
from mosaico_tramas.simbolos.raster import cobertura, rasterizar

LLENO = Simbolo("t_lleno", "lleno", "solid", (Poligono(((0, 0), (1, 0), (1, 1), (0, 1))),))
VACIO = Simbolo("t_vacio", "vacio", "blank", ())
HORIZONTAL = Simbolo("t_h", "horizontal", "line", (Linea((0, 0.5), (1, 0.5)),))
TRIANGULO = Simbolo("t_tri", "triangulo", "triangle", (Poligono(((0, 1), (1, 1), (0, 0))),))


def test_lleno_y_vacio():
    assert cobertura(LLENO) == pytest.approx(100.0, abs=0.01)
    assert cobertura(VACIO) == 0.0


def test_linea_horizontal_cubre_el_grosor_del_trazo():
    assert cobertura(HORIZONTAL) == pytest.approx(TRAZO_REL * 100, abs=0.3)


def test_triangulo_media_celda():
    assert cobertura(TRIANGULO) == pytest.approx(50.0, abs=0.3)


def test_punto_area_del_circulo():
    punto = Simbolo("t_p", "punto", "dot", (Punto(0.1),))
    assert cobertura(punto) == pytest.approx(np.pi * 0.1**2 * 100, abs=0.2)


def test_rasterizar_forma_tipo_y_rango():
    img = rasterizar(HORIZONTAL, 64)
    assert img.shape == (64, 64)
    assert img.dtype == np.float32
    assert img.min() >= 0.0 and img.max() <= 1.0
    # La línea está en la fila central, no arriba
    assert img[32].mean() > 0.9
    assert img[2].mean() == 0.0


def test_eje_y_hacia_abajo():
    # Triángulo con vértices abajo-izquierda: la fila inferior tiene más tinta que la superior
    img = rasterizar(TRIANGULO, 100)
    assert img[95].mean() > img[5].mean()


def test_rasterizado_determinista():
    a = rasterizar(TRIANGULO, 200)
    b = rasterizar(TRIANGULO, 200)
    assert np.array_equal(a, b)


def test_trazo_mas_grueso_cubre_mas():
    fino = rasterizar(HORIZONTAL, 200, trazo_rel=0.05).mean()
    grueso = rasterizar(HORIZONTAL, 200, trazo_rel=0.10).mean()
    assert grueso > fino
