"""Tests del modelo de configuración del mosaico (T3, CA2)."""

import pydantic
import pytest

from mosaico_tramas.config import (
    MetodoCuantizacion,
    MosaicoConfig,
    Recorte,
    UbicacionLeyenda,
)
from mosaico_tramas.errores import ConfigInvalidaError
from mosaico_tramas.papel import Orientacion


def test_defaults():
    config = MosaicoConfig.crear()
    assert config.n_simbolos == 6
    assert config.columnas == 40
    assert config.metodo is MetodoCuantizacion.QUANTILES
    assert config.reduccion_ruido and config.umbral_ruido == 2
    assert config.limitar_oscuros and config.max_oscuros_pct == 8.0
    assert config.papeles == ("A4",)
    assert config.orientacion is Orientacion.AUTO
    assert config.margen_mm == 12.7
    assert config.recorte is Recorte.FIT
    assert config.leyenda is UbicacionLeyenda.BELOW
    assert config.incluir_solucion and config.marca_blanco
    assert not config.grilla_en_solucion


# --- CA2: cantidad de símbolos fuera de rango o no entera ---


@pytest.mark.parametrize("valor", [4, 8, 11, 0, -3, 5.5, True, "x", None])
def test_n_simbolos_invalido_mensaje_exacto(valor: object):
    with pytest.raises(ConfigInvalidaError) as info:
        MosaicoConfig.crear(n_simbolos=valor)
    esperado = (
        f"La cantidad de símbolos debe ser un entero entre 5 y 7 (valor recibido: {valor!r})."
    )
    assert esperado in str(info.value)


@pytest.mark.parametrize("valor", [5, 6, 7])
def test_n_simbolos_valido(valor: int):
    assert MosaicoConfig.crear(n_simbolos=valor).n_simbolos == valor


# --- Otros rangos ---


@pytest.mark.parametrize(
    ("campo", "valor", "fragmento"),
    [
        ("columnas", 9, "columnas deben ser un entero entre 10 y 200"),
        ("columnas", 201, "columnas deben ser un entero entre 10 y 200"),
        ("umbral_ruido", 1, "umbral de ruido debe ser un entero entre 2 y 20"),
        ("umbral_ruido", 21, "umbral de ruido debe ser un entero entre 2 y 20"),
        ("max_oscuros_pct", 0.5, "límite de oscuros debe estar entre 1 y 100"),
        ("max_oscuros_pct", 101, "límite de oscuros debe estar entre 1 y 100"),
        ("margen_mm", 4.9, "márgenes deben estar entre 5 y 40 mm"),
        ("margen_mm", 41, "márgenes deben estar entre 5 y 40 mm"),
        ("png_lado_px", 100, "lado del PNG debe ser un entero entre 500 y 6000"),
        ("metodo", "otsu", "método de cuantización debe ser uno de"),
        ("orientacion", "diagonal", "orientación debe ser una de"),
        ("recorte", "stretch", "recorte debe ser uno de"),
        ("leyenda", "arriba", "ubicación de la leyenda debe ser una de"),
    ],
)
def test_rangos_con_mensaje_en_espanol(campo: str, valor: object, fragmento: str):
    with pytest.raises(ConfigInvalidaError) as info:
        MosaicoConfig.crear(**{campo: valor})
    assert fragmento in str(info.value)


def test_enums_aceptan_strings():
    config = MosaicoConfig.crear(metodo="kmeans", orientacion="landscape", leyenda="separate")
    assert config.metodo is MetodoCuantizacion.KMEANS
    assert config.orientacion is Orientacion.LANDSCAPE
    assert config.leyenda is UbicacionLeyenda.SEPARATE


# --- Papeles ---


def test_papeles_normaliza_y_acepta_varios():
    config = MosaicoConfig.crear(papeles=["a4", "Letter"])
    assert config.papeles == ("A4", "LETTER")


def test_papel_unico_como_string():
    assert MosaicoConfig.crear(papeles="A3").papeles == ("A3",)


@pytest.mark.parametrize(
    ("papeles", "fragmento"),
    [
        ([], "al menos un papel"),
        (["A4", "A4"], "repetido"),
        (["B5"], "Papel desconocido"),
    ],
)
def test_papeles_invalidos(papeles: list[str], fragmento: str):
    with pytest.raises(ConfigInvalidaError, match=fragmento):
        MosaicoConfig.crear(papeles=papeles)


def test_custom_exige_medidas():
    with pytest.raises(ConfigInvalidaError, match="personalizado"):
        MosaicoConfig.crear(papeles=["CUSTOM"])


def test_custom_con_medidas():
    config = MosaicoConfig.crear(papeles=["CUSTOM"], papel_personalizado=(430, 600))
    assert config.papel_personalizado is not None
    assert config.papel_personalizado.ancho_mm == 430


def test_custom_fuera_de_rango():
    with pytest.raises(ConfigInvalidaError, match="entre 100 y 1200 mm"):
        MosaicoConfig.crear(papeles=["CUSTOM"], papel_personalizado=(50, 600))


# --- Validaciones cruzadas y extras ---


@pytest.mark.parametrize(
    ("campo", "valor"), [("percentil_bajo", 50), ("percentil_bajo", -1), ("percentil_alto", 50)]
)
def test_percentiles_fuera_de_rango(campo: str, valor: float):
    # Los rangos (0..49 y 51..100) garantizan que el bajo siempre sea menor que el alto
    with pytest.raises(ConfigInvalidaError, match="percentil"):
        MosaicoConfig.crear(**{campo: valor})


def test_parametro_desconocido():
    with pytest.raises(ConfigInvalidaError, match="Parámetro desconocido: 'colores'"):
        MosaicoConfig.crear(colores=3)


def test_varios_errores_juntos():
    with pytest.raises(ConfigInvalidaError) as info:
        MosaicoConfig.crear(n_simbolos=3, columnas=5)
    mensaje = str(info.value)
    assert "cantidad de símbolos" in mensaje
    assert "columnas" in mensaje


def test_config_inmutable():
    config = MosaicoConfig.crear()
    with pytest.raises(pydantic.ValidationError):
        config.columnas = 10  # type: ignore[misc]


def test_config_hashable_y_serializable():
    a = MosaicoConfig.crear(papeles=["A4", "LETTER"])
    b = MosaicoConfig.crear(papeles=["A4", "LETTER"])
    assert a == b
    assert hash(a) == hash(b)
    assert a.model_dump_json() == b.model_dump_json()


# --- Triángulo opcional (checkpoint B) ---


def test_triangulo_activado_por_defecto():
    assert MosaicoConfig.crear().usar_triangulo is True


def test_sin_triangulo_n_maximo_6():
    assert MosaicoConfig.crear(usar_triangulo=False, n_simbolos=6).n_simbolos == 6
    with pytest.raises(ConfigInvalidaError) as info:
        MosaicoConfig.crear(usar_triangulo=False, n_simbolos=7)
    assert (
        "Sin el triángulo, la cantidad de símbolos debe ser un entero entre 5 y 6 "
        "(valor recibido: 7)."
    ) in str(info.value)
