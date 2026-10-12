"""Tests de la selección del subconjunto de símbolos (T6, CA1, CA9)."""

import pytest

from mosaico_tramas.errores import ConfigInvalidaError, ErrorBibliotecaSimbolos
from mosaico_tramas.simbolos.biblioteca import BIBLIOTECA, ID_LLENO, ID_PUNTO, POR_ID, horizontal
from mosaico_tramas.simbolos.primitivas import Simbolo
from mosaico_tramas.simbolos.raster import cobertura
from mosaico_tramas.simbolos.seleccion import DELTA_MIN, DELTA_MIN_0, elegir_simbolos

RANGO_N = range(5, 8)


@pytest.mark.parametrize("n", RANGO_N)
def test_cantidad_y_extremos(n: int):
    simbolos = elegir_simbolos(n)
    assert len(simbolos) == n
    assert simbolos[0].id == ID_PUNTO
    assert simbolos[-1].id == ID_LLENO


@pytest.mark.parametrize("n", RANGO_N)
def test_ca1_cobertura_creciente_y_saltos_minimos(n: int):
    coberturas = [cobertura(s) for s in elegir_simbolos(n)]
    # Salto vacío (0 %) → nivel 1
    assert coberturas[0] - 0.0 >= DELTA_MIN_0
    for anterior, siguiente in zip(coberturas, coberturas[1:], strict=False):
        assert siguiente > anterior
        assert siguiente - anterior >= DELTA_MIN


@pytest.mark.parametrize("n", RANGO_N)
def test_ca9_familias_distintas(n: int):
    familias = [s.familia for s in elegir_simbolos(n)]
    assert len(set(familias)) == n


def test_umbrales_del_diseno():
    assert DELTA_MIN == 6.0
    assert DELTA_MIN_0 == 1.5


@pytest.mark.parametrize("n", RANGO_N)
def test_determinista(n: int):
    elegir_simbolos.cache_clear()
    primera = [s.id for s in elegir_simbolos(n)]
    elegir_simbolos.cache_clear()
    assert [s.id for s in elegir_simbolos(n)] == primera


def test_maximiza_el_salto_minimo():
    # Con N = 5 hay mucho margen: el salto mínimo tiene que ser holgado (~15 pp)
    coberturas = [cobertura(s) for s in elegir_simbolos(5)]
    saltos = [b - a for a, b in zip(coberturas, coberturas[1:], strict=False)]
    assert min(saltos) > 14


def test_resultado_de_diseno_para_n7():
    ids = [s.id for s in elegir_simbolos(7)]
    assert ids == ["punto", "horiz1", "cruz", "aspa1", "estrella", "triangulo", "lleno"]


def test_biblioteca_imposible_lanza_error():
    # Solo dos candidatos intermedios con la misma cobertura: no alcanza para N = 5
    chica = (
        POR_ID[ID_PUNTO],
        Simbolo("h_a", "familia_a", "a", (horizontal(0.5),)),
        Simbolo("h_b", "familia_b", "b", (horizontal(0.25),)),
        POR_ID[ID_LLENO],
    )
    with pytest.raises(ErrorBibliotecaSimbolos, match="no permite armar 5 símbolos"):
        elegir_simbolos(5, chica)


@pytest.mark.parametrize("n", [4, 8])
def test_n_fuera_de_rango(n: int):
    with pytest.raises(ConfigInvalidaError, match="entre 5 y 7"):
        elegir_simbolos(n)


def test_biblioteca_por_defecto_es_la_completa():
    assert elegir_simbolos(6) == elegir_simbolos(6, BIBLIOTECA)
