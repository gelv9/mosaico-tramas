"""Tests de la cuantización (T10–T14)."""

import numpy as np
import numpy.typing as npt
import pytest

from mosaico_tramas.config import Recorte
from mosaico_tramas.cuantizacion import aplicar_cortes, cortes_quantiles
from mosaico_tramas.imagen import a_grilla, cargar_luminancia

RANGO_N = range(5, 8)


def _oscuridad(png: bytes, columnas: int = 60, filas: int = 80) -> npt.NDArray[np.float32]:
    lum = cargar_luminancia(png, max_mb=20)
    oscuridad, _ = a_grilla(lum, columnas=columnas, filas=filas, recorte=Recorte.FIT)
    return oscuridad


def _porcentajes(niveles: npt.NDArray[np.uint8], n: int) -> npt.NDArray[np.float64]:
    return np.bincount(niveles.ravel(), minlength=n + 1) / niveles.size * 100


# --- T10: cuantiles ---


@pytest.mark.parametrize("n", RANGO_N)
@pytest.mark.parametrize("imagen", ["png_degradado", "png_foto"])
def test_ca3_cuantiles_ningun_nivel_infrautilizado(n: int, imagen: str, request):
    d = _oscuridad(request.getfixturevalue(imagen))
    niveles = aplicar_cortes(d, cortes_quantiles(d, n))
    minimo = 0.5 * 100 / (n + 1)
    assert _porcentajes(niveles, n).min() >= minimo


@pytest.mark.parametrize("n", RANGO_N)
def test_cuantiles_reparten_parejo_en_degradado(n: int, png_degradado: bytes):
    d = _oscuridad(png_degradado)
    niveles = aplicar_cortes(d, cortes_quantiles(d, n))
    ideal = 100 / (n + 1)
    assert np.allclose(_porcentajes(niveles, n), ideal, atol=ideal * 0.25)


def test_cortes_estrictamente_crecientes(png_foto: bytes):
    d = _oscuridad(png_foto)
    cortes = cortes_quantiles(d, 7)
    assert len(cortes) == 7
    assert np.all(np.diff(cortes) > 0)


def test_nivel_0_claro_y_nivel_n_oscuro(png_degradado: bytes):
    d = _oscuridad(png_degradado)
    niveles = aplicar_cortes(d, cortes_quantiles(d, 6))
    assert niveles.dtype == np.uint8
    # Columna izquierda negra → nivel N; columna derecha blanca → nivel 0
    assert np.all(niveles[:, 0] == 6)
    assert np.all(niveles[:, -1] == 0)


def test_celdas_identicas_comparten_nivel(png_fondo_plano: bytes):
    d = _oscuridad(png_fondo_plano)
    niveles = aplicar_cortes(d, cortes_quantiles(d, 6))
    blancas = d < 1e-4  # el blanco plano sale con ruido de punto flotante (~1e-8)
    assert blancas.sum() > 0.3 * d.size
    assert len(np.unique(niveles[blancas])) == 1


def test_cuota_de_oscuros_en_los_cortes(png_foto: bytes):
    d = _oscuridad(png_foto)
    n, limite = 6, 8.0
    niveles = aplicar_cortes(d, cortes_quantiles(d, n, max_oscuros_pct=limite))
    pct = _porcentajes(niveles, n)
    assert pct[n] <= limite + 0.5
    # El resto se reparte parejo: ningún nivel recibe el exceso entero
    resto = 100 - pct[n]
    assert np.allclose(pct[:n], resto / n, atol=resto / n * 0.3)


def test_limite_mayor_a_la_cuota_ideal_no_cambia_nada(png_foto: bytes):
    d = _oscuridad(png_foto)
    sin = cortes_quantiles(d, 5)
    con = cortes_quantiles(d, 5, max_oscuros_pct=50.0)
    assert np.array_equal(sin, con)


def test_cuantiles_deterministas(png_foto: bytes):
    d = _oscuridad(png_foto)
    assert np.array_equal(cortes_quantiles(d, 7), cortes_quantiles(d, 7))
