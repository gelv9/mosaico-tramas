"""Tests de la hoja de muestra de símbolos (T7)."""

import io

import pytest
from pypdf import PdfReader

from mosaico_tramas.muestra import hoja_muestra
from mosaico_tramas.papel import REGISTRO_PAPELES, Orientacion
from mosaico_tramas.simbolos.biblioteca import BIBLIOTECA
from mosaico_tramas.simbolos.raster import cobertura
from mosaico_tramas.simbolos.seleccion import elegir_simbolos


def _leer(pdf: bytes) -> PdfReader:
    return PdfReader(io.BytesIO(pdf))


def _texto(lector: PdfReader) -> str:
    return "\n".join(pagina.extract_text() for pagina in lector.pages)


@pytest.mark.parametrize("n", [5, 6])
def test_hoja_para_n(n: int):
    lector = _leer(hoja_muestra(n))
    ancho, alto = REGISTRO_PAPELES["A4"].tamano_pt(Orientacion.PORTRAIT)
    caja = lector.pages[0].mediabox
    assert float(caja.width) == pytest.approx(ancho, abs=0.01)
    assert float(caja.height) == pytest.approx(alto, abs=0.01)
    texto = _texto(lector)
    assert f"N = {n}" in texto
    for simbolo in elegir_simbolos(n):
        assert simbolo.id in texto
        assert f"{cobertura(simbolo):.1f}%" in texto


def test_hoja_biblioteca_completa():
    lector = _leer(hoja_muestra(None))
    texto = _texto(lector)
    assert len(lector.pages) >= 2
    for simbolo in BIBLIOTECA:
        assert simbolo.id in texto


def test_hoja_determinista():
    assert hoja_muestra(6) == hoja_muestra(6)
    assert hoja_muestra(None) == hoja_muestra(None)
