"""Tests de la jerarquía de errores y de los avisos (T1)."""

import dataclasses

import pytest

from mosaico_tramas.avisos import Aviso, CodigoAviso
from mosaico_tramas.errores import (
    CeldaDemasiadoChicaError,
    ConfigInvalidaError,
    ErrorBibliotecaSimbolos,
    ImagenInvalidaError,
    MosaicoError,
)


@pytest.mark.parametrize(
    "clase", [ConfigInvalidaError, ImagenInvalidaError, ErrorBibliotecaSimbolos]
)
def test_errores_heredan_de_mosaico_error(clase: type[MosaicoError]):
    error = clase("mensaje en español")
    assert isinstance(error, MosaicoError)
    assert str(error) == "mensaje en español"


def test_celda_chica_conserva_sugerencias():
    error = CeldaDemasiadoChicaError(
        "Celdas de 3,1 mm (mínimo 4 mm).",
        columnas_max=46,
        papel_sugerido="A3",
        personalizado_mm=(266, 372),
    )
    assert isinstance(error, MosaicoError)
    assert error.columnas_max == 46
    assert error.papel_sugerido == "A3"
    assert error.personalizado_mm == (266, 372)
    assert "4 mm" in str(error)


def test_aviso_es_inmutable():
    aviso = Aviso(CodigoAviso.LEYENDA_MOVIDA, "La leyenda se movió a una hoja aparte.")
    with pytest.raises(dataclasses.FrozenInstanceError):
        aviso.mensaje = "otro"  # type: ignore[misc]
    assert aviso.codigo is CodigoAviso.LEYENDA_MOVIDA
