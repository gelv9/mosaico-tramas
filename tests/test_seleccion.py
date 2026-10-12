"""Tests de la selección del subconjunto de símbolos (T6, CA1, CA9)."""

import pytest

from mosaico_tramas.errores import ConfigInvalidaError, ErrorBibliotecaSimbolos
from mosaico_tramas.simbolos.biblioteca import BIBLIOTECA, ID_LLENO, ID_PUNTO, POR_ID, bloque
from mosaico_tramas.simbolos.primitivas import Simbolo
from mosaico_tramas.simbolos.raster import cobertura
from mosaico_tramas.simbolos.seleccion import DELTA_MIN, DELTA_MIN_0, elegir_simbolos

RANGO_N = range(5, 11)


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
    # Con N = 5 hay mucho margen: el salto mínimo tiene que ser holgado (diseño: ~23,6 pp)
    coberturas = [cobertura(s) for s in elegir_simbolos(5)]
    saltos = [b - a for a, b in zip(coberturas, coberturas[1:], strict=False)]
    assert min(saltos) > 20


def test_resultado_de_diseno_para_n10():
    ids = [s.id for s in elegir_simbolos(10)]
    assert ids == [
        "punto",
        "diag1",
        "aspa1",
        "reja1",
        "bloque60",
        "triangulo",
        "mitad_rayas",
        "tres_cuartos",
        "esquina",
        "lleno",
    ]


def test_biblioteca_imposible_lanza_error():
    # Solo dos candidatos intermedios muy parecidos: no alcanza para N = 5
    chica = (
        POR_ID[ID_PUNTO],
        Simbolo("b40", "bloque_a", "a", (bloque(0.40),)),
        Simbolo("b42", "bloque_b", "b", (bloque(0.42),)),
        POR_ID[ID_LLENO],
    )
    with pytest.raises(ErrorBibliotecaSimbolos, match="no permite armar 5 símbolos"):
        elegir_simbolos(5, chica)


@pytest.mark.parametrize("n", [4, 11])
def test_n_fuera_de_rango(n: int):
    with pytest.raises(ConfigInvalidaError, match="entre 5 y 10"):
        elegir_simbolos(n)


def test_biblioteca_por_defecto_es_la_completa():
    assert elegir_simbolos(7) == elegir_simbolos(7, BIBLIOTECA)
