"""Tests de la cuantización (T10–T14)."""

import numpy as np
import numpy.typing as npt
import pytest

from mosaico_tramas.avisos import CodigoAviso
from mosaico_tramas.config import MosaicoConfig, Recorte
from mosaico_tramas.cuantizacion import (
    aplicar_cortes,
    cortes_kmeans,
    cortes_quantiles,
    cortes_uniformes,
    cuantizar,
    limitar_oscuros,
    reducir_ruido,
)
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


# --- T11: k-means y uniforme ---


def test_kmeans_determinista(png_foto: bytes):
    d = _oscuridad(png_foto)
    assert np.array_equal(cortes_kmeans(d, 7), cortes_kmeans(d, 7))


def test_kmeans_encuentra_grupos_obvios():
    # Tres grupos bien separados de oscuridad: 0,1 / 0,5 / 0,9
    d = np.repeat(np.array([0.1, 0.5, 0.9], dtype=np.float32), 1000).reshape(30, 100)
    cortes = cortes_kmeans(d, 2)
    assert 0.1 < cortes[0] < 0.5 < cortes[1] < 0.9
    niveles = aplicar_cortes(d, cortes)
    assert np.bincount(niveles.ravel()).tolist() == [1000, 1000, 1000]


@pytest.mark.parametrize("n", RANGO_N)
def test_kmeans_sin_clusters_vacios(n: int, png_foto: bytes):
    d = _oscuridad(png_foto)
    cortes = cortes_kmeans(d, n)
    assert len(cortes) == n
    assert np.all(np.diff(cortes) > 0)
    niveles = aplicar_cortes(d, cortes)
    assert (np.bincount(niveles.ravel(), minlength=n + 1) > 0).all()


def test_kmeans_con_menos_valores_que_clusters_no_falla():
    d = np.array([[0.2, 0.8]] * 10, dtype=np.float32)
    cortes = cortes_kmeans(d, 6)
    assert len(cortes) == 6
    assert np.all(np.diff(cortes) > 0)


def test_uniforme():
    assert np.allclose(cortes_uniformes(5), [1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6])


# --- T12: límite de oscuros (post-paso) ---


def test_limitar_oscuros_respeta_el_limite(png_foto: bytes):
    d = _oscuridad(png_foto)
    n = 5
    niveles = aplicar_cortes(d, cortes_uniformes(n))
    limitados = limitar_oscuros(niveles, d, n, 3.0)
    assert (limitados == n).sum() <= int(0.03 * d.size)


def test_limitar_oscuros_baja_las_menos_oscuras_a_n_menos_1():
    d = np.array([[0.90, 0.95, 0.99, 0.97]], dtype=np.float32)
    niveles = np.array([[5, 5, 5, 5]], dtype=np.uint8)
    # 50 % de 4 celdas = 2: se quedan en 5 las dos más oscuras (0,99 y 0,97)
    resultado = limitar_oscuros(niveles, d, 5, 50.0)
    assert resultado.tolist() == [[4, 4, 5, 5]]


def test_limitar_oscuros_desempate_estable():
    d = np.full((1, 4), 0.9, dtype=np.float32)
    niveles = np.full((1, 4), 5, dtype=np.uint8)
    # Con oscuridades iguales, se quedan las primeras en orden de lectura
    assert limitar_oscuros(niveles, d, 5, 50.0).tolist() == [[5, 5, 4, 4]]


def test_limitar_oscuros_no_toca_si_no_excede():
    d = np.array([[0.1, 0.9]], dtype=np.float32)
    niveles = np.array([[0, 5]], dtype=np.uint8)
    assert np.array_equal(limitar_oscuros(niveles, d, 5, 50.0), niveles)


# --- T13: reducción de ruido ---


def _componentes_de_tamano_1(niveles: npt.NDArray[np.uint8]) -> int:
    from skimage.measure import label

    total = 0
    for v in np.unique(niveles):
        etiquetas = label(niveles == v, connectivity=2)
        total += int((np.bincount(etiquetas.ravel())[1:] == 1).sum())
    return total


def test_ca11_sin_celdas_sueltas(png_foto: bytes):
    d = _oscuridad(png_foto)
    niveles = aplicar_cortes(d, cortes_quantiles(d, 7))
    assert _componentes_de_tamano_1(niveles) > 0  # la foto con ruido sí tiene sueltas
    limpio = reducir_ruido(niveles, umbral=2)
    assert _componentes_de_tamano_1(limpio) == 0


def test_celda_suelta_toma_el_nivel_de_sus_vecinas():
    niveles = np.full((5, 5), 2, dtype=np.uint8)
    niveles[2, 2] = 6
    assert np.all(reducir_ruido(niveles, umbral=2) == 2)


def test_empate_entre_vecinas_gana_el_mas_cercano():
    # Celda de nivel 3 rodeada por 4 vecinas de nivel 1 y 4 de nivel 4: gana 4 (más cercano)
    niveles = np.array([[1, 4, 1], [4, 3, 4], [1, 4, 1]], dtype=np.uint8)
    resultado = reducir_ruido(niveles, umbral=2)
    assert resultado[1, 1] == 4


def test_bloques_grandes_no_se_tocan():
    niveles = np.zeros((10, 10), dtype=np.uint8)
    niveles[:, 5:] = 3
    assert np.array_equal(reducir_ruido(niveles, umbral=5), niveles)


def test_umbral_mayor_elimina_componentes_mas_grandes():
    niveles = np.zeros((8, 8), dtype=np.uint8)
    niveles[3:5, 3:5] = 4  # componente de 4 celdas
    assert np.array_equal(reducir_ruido(niveles, umbral=4), niveles)
    assert np.all(reducir_ruido(niveles, umbral=5) == 0)


def test_reduccion_de_ruido_determinista(png_foto: bytes):
    d = _oscuridad(png_foto)
    niveles = aplicar_cortes(d, cortes_quantiles(d, 6))
    assert np.array_equal(reducir_ruido(niveles, 3), reducir_ruido(niveles, 3))


# --- T14: distribución y orquestación ---


@pytest.mark.parametrize("metodo", ["quantiles", "kmeans", "uniform"])
def test_ca10_limite_se_cumple_con_ruido_activo(metodo: str, png_foto: bytes):
    d = _oscuridad(png_foto)
    config = MosaicoConfig.crear(
        n_simbolos=6, metodo=metodo, limitar_oscuros=True, max_oscuros_pct=5, umbral_ruido=4
    )
    resultado = cuantizar(d, config)
    assert (resultado.niveles == 6).sum() <= int(0.05 * d.size)
    assert resultado.distribucion.porcentajes[6] <= 5.0


def test_distribucion_suma_el_total(png_foto: bytes):
    d = _oscuridad(png_foto)
    resultado = cuantizar(d, MosaicoConfig.crear(n_simbolos=7))
    dist = resultado.distribucion
    assert len(dist.conteos) == 8
    assert sum(dist.conteos) == d.size
    assert sum(dist.porcentajes) == pytest.approx(100.0)


def test_aviso_nivel_infrautilizado():
    # 80 % de celdas idénticas (blancas): los demás niveles quedan con muy pocas celdas
    d = np.zeros((50, 50), dtype=np.float32)
    d.ravel()[-500:] = np.linspace(0.01, 1.0, 500)
    config = MosaicoConfig.crear(n_simbolos=6, reduccion_ruido=False, limitar_oscuros=False)
    resultado = cuantizar(d, config)
    codigos = {a.codigo for a in resultado.avisos}
    assert CodigoAviso.NIVEL_INFRAUTILIZADO in codigos
    assert any("nivel 3" in a.mensaje for a in resultado.avisos)


def test_sin_avisos_en_el_degradado(png_degradado: bytes):
    d = _oscuridad(png_degradado)
    config = MosaicoConfig.crear(n_simbolos=7, reduccion_ruido=False, limitar_oscuros=False)
    assert cuantizar(d, config).avisos == ()


def test_no_avisa_por_el_nivel_n_recortado_a_proposito(png_degradado: bytes):
    d = _oscuridad(png_degradado)
    # 2 % < la mitad de la cuota ideal (7,1 % para N = 6): recortado a propósito, sin aviso
    config = MosaicoConfig.crear(n_simbolos=6, limitar_oscuros=True, max_oscuros_pct=2)
    resultado = cuantizar(d, config)
    assert resultado.distribucion.porcentajes[6] <= 2.0
    assert not any("nivel 6" in a.mensaje for a in resultado.avisos)


def test_cuantizar_determinista(png_foto: bytes):
    d = _oscuridad(png_foto)
    config = MosaicoConfig.crear(metodo="kmeans")
    assert np.array_equal(cuantizar(d, config).niveles, cuantizar(d, config).niveles)
