"""Tests del set fijo del estilo clásico (T29, CA1)."""

import pytest

from mosaico_tramas.config import MosaicoConfig
from mosaico_tramas.errores import ErrorBibliotecaSimbolos
from mosaico_tramas.simbolos.biblioteca import BIBLIOTECA, ORDEN_CLASICO, POR_ID
from mosaico_tramas.simbolos.raster import cobertura
from mosaico_tramas.simbolos.seleccion import DELTA_MIN_0, elegir_simbolos, simbolos_para


def test_orden_fijo_de_la_referencia():
    ids = [s.id for s in elegir_simbolos()]
    assert ids == ["punto", "diag_asc", "diag_desc", "aspa", "asterisco", "lleno"]
    assert tuple(ids) == ORDEN_CLASICO


def test_ca1_cobertura_no_decreciente_con_igualdad_solo_entre_diagonales():
    coberturas = [cobertura(s) for s in elegir_simbolos()]
    assert coberturas[0] - 0.0 >= DELTA_MIN_0  # vacío → punto
    for nivel, (anterior, siguiente) in enumerate(zip(coberturas, coberturas[1:], strict=False), 1):
        if nivel == 2:
            # / y \ comparten tono a propósito: la dirección da textura
            assert siguiente == pytest.approx(anterior, abs=0.01)
        else:
            assert siguiente > anterior + 6


def test_diagonales_en_direcciones_opuestas():
    asc, desc = POR_ID["diag_asc"].primitivas[0], POR_ID["diag_desc"].primitivas[0]
    # "/" sube hacia la derecha (y hacia abajo en la celda); "\" baja hacia la derecha
    assert {asc.p0, asc.p1} == {(0.0, 1.0), (1.0, 0.0)}
    assert {desc.p0, desc.p1} == {(0.0, 0.0), (1.0, 1.0)}


def test_simbolos_para_la_config():
    assert simbolos_para(MosaicoConfig.crear()) == elegir_simbolos()


def test_biblioteca_incompleta_lanza_error():
    incompleta = tuple(s for s in BIBLIOTECA if s.id != "asterisco")
    with pytest.raises(ErrorBibliotecaSimbolos, match="asterisco"):
        elegir_simbolos(incompleta)
