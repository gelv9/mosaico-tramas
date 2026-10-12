"""Tests del render PNG (T23)."""

import io

import numpy as np
import pytest
from PIL import Image

from mosaico_tramas.config import MosaicoConfig
from mosaico_tramas.render_png import png_plantilla, png_solucion, tamano_tile
from mosaico_tramas.simbolos.seleccion import simbolos_para

SIMBOLOS = simbolos_para(MosaicoConfig.crear())


def _niveles() -> np.ndarray:
    return np.random.default_rng(3).integers(1, 7, (30, 20)).astype(np.uint8)


def _abrir(datos: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(datos)).convert("L"))


def test_tamano_tile():
    assert tamano_tile(20, 30, 2000) == 66
    assert tamano_tile(200, 200, 500) == 4  # nunca menos de 4 px


@pytest.mark.parametrize("lado", [1200, 2000])
def test_dimensiones(lado: int):
    niveles = _niveles()
    t = tamano_tile(20, 30, lado)
    for img in (
        _abrir(png_solucion(niveles, SIMBOLOS, lado)),
        _abrir(png_plantilla(niveles, lado)),
    ):
        assert img.shape == (30 * t, 20 * t)
        assert lado - t < max(img.shape) <= lado


def test_solucion_lleno_negro_y_punto_casi_blanco():
    niveles = np.ones((4, 4), dtype=np.uint8)  # todo punto (lo más claro)
    niveles[0, 0] = 6
    t = tamano_tile(4, 4, 800)
    img = _abrir(png_solucion(niveles, SIMBOLOS, 800))
    assert img[:t, :t].max() == 0  # celda llena
    celda_punto = img[t : 2 * t, t : 2 * t]
    assert celda_punto[t // 2, t // 2] < 128  # el punto en el centro
    assert celda_punto[1, 1] == 255  # el resto de la celda, blanco


def test_plantilla_numero_en_cada_celda():
    niveles = np.array([[1, 3]], dtype=np.uint8)
    t = tamano_tile(2, 1, 800)
    img = _abrir(png_plantilla(niveles, 800))
    for celda in (img[2:-2, 2 : t - 2], img[2:-2, t + 2 : -2]):
        assert 0 < celda.min() < 255  # número en gris, nunca negro puro


def test_png_determinista():
    niveles = _niveles()
    assert png_solucion(niveles, SIMBOLOS, 1200) == png_solucion(niveles, SIMBOLOS, 1200)
    assert png_plantilla(niveles, 1200) == png_plantilla(niveles, 1200)


# --- T30: estilo de grilla ---


def test_plantilla_con_puntos_es_distinta_y_determinista():
    niveles = _niveles()
    lineas = png_plantilla(niveles, 1200)
    puntos = png_plantilla(niveles, 1200, estilo_grilla="dots")
    assert puntos != lineas
    assert puntos == png_plantilla(niveles, 1200, estilo_grilla="dots")
    img = _abrir(puntos)
    t = tamano_tile(20, 30, 1200)
    # A mitad de un borde de celda no hay línea, en la esquina sí hay punto
    assert img[0, t // 2] == 255
    assert img[0, 0] < 255
