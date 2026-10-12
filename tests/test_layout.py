"""Tests del cálculo de layout (T15–T18)."""

import pytest

from mosaico_tramas.avisos import CodigoAviso
from mosaico_tramas.config import MosaicoConfig
from mosaico_tramas.errores import CeldaDemasiadoChicaError
from mosaico_tramas.layout import (
    ALTO_ENTRADA_MM,
    ANCHO_ENTRADA_MM,
    alto_leyenda,
    calcular_layout,
    calcular_layouts,
    entradas_por_fila,
)
from mosaico_tramas.papel import REGISTRO_PAPELES, Orientacion, mm_a_pt, papel_personalizado

A4_ANCHO_UTIL = mm_a_pt(210 - 2 * 12.7)


# --- T15: alto de la leyenda ---


def test_alto_leyenda_n6_en_a4_vertical():
    # 6 entradas en filas de 5 → 2 filas: 6 + 4,6 + 2 × 14 = 38,6 mm
    assert alto_leyenda(6, A4_ANCHO_UTIL) == pytest.approx(mm_a_pt(38.6), abs=0.01)


def test_alto_leyenda_una_fila():
    # 5 entradas en filas de 5 → 1 fila
    assert alto_leyenda(5, A4_ANCHO_UTIL) == pytest.approx(mm_a_pt(24.6), abs=0.01)


def test_entradas_por_fila_segun_ancho():
    assert entradas_por_fila(A4_ANCHO_UTIL) == 5
    ancho_a3_horizontal = REGISTRO_PAPELES["A3"].tamano_pt(Orientacion.LANDSCAPE)[0] - mm_a_pt(25.4)
    assert entradas_por_fila(ancho_a3_horizontal) == 12
    # Nunca menos de una entrada por fila
    assert entradas_por_fila(mm_a_pt(10)) == 1


def test_dimensiones_de_la_entrada():
    assert ANCHO_ENTRADA_MM == 32
    assert ALTO_ENTRADA_MM == 14


# --- T16: cálculo del layout ---

CELDA_MIN = mm_a_pt(4)


def _config(**valores: object) -> MosaicoConfig:
    return MosaicoConfig.crear(**valores)


def _dentro(
    interno: tuple[float, float, float, float], externo: tuple[float, float, float, float]
) -> bool:
    x0, y0, x1, y1 = interno
    ex0, ey0, ex1, ey1 = externo
    tol = 1e-6
    return x0 >= ex0 - tol and y0 >= ey0 - tol and x1 <= ex1 + tol and y1 <= ey1 + tol


def test_leyenda_debajo_entra():
    layout = calcular_layout(_config(columnas=40), 1000, 1000, REGISTRO_PAPELES["A4"])
    assert layout.leyenda_en_plantilla
    assert layout.avisos == ()
    assert layout.filas == 40
    assert layout.celda_pt >= CELDA_MIN
    assert layout.celda_pt == pytest.approx(mm_a_pt(184.6) / 40)
    # La grilla queda arriba de la leyenda, sin superponerse
    assert layout.rect_grilla[1] >= layout.rect_leyenda[3] - 1e-6


def test_leyenda_debajo_no_entra_y_se_mueve_con_aviso():
    # Imagen alta: con la leyenda debajo la celda bajaría de 4 mm, sin ella no
    layout = calcular_layout(_config(columnas=45), 1000, 1450, REGISTRO_PAPELES["A4"])
    assert not layout.leyenda_en_plantilla
    assert [a.codigo for a in layout.avisos] == [CodigoAviso.LEYENDA_MOVIDA]
    assert "hoja aparte" in layout.avisos[0].mensaje
    assert layout.celda_pt >= CELDA_MIN
    assert layout.rect_leyenda is None


def test_leyenda_aparte_siempre_en_su_pagina():
    layout = calcular_layout(
        _config(columnas=20, leyenda="separate"), 1000, 1000, REGISTRO_PAPELES["A4"]
    )
    assert not layout.leyenda_en_plantilla
    assert layout.avisos == ()


@pytest.mark.parametrize("nombre", ["A4", "LETTER", "A3", "TABLOID"])
@pytest.mark.parametrize("proporcion", [(1000, 700), (700, 1000), (1000, 1000)])
@pytest.mark.parametrize("leyenda", ["below", "separate"])
def test_contenido_dentro_del_area_util(nombre: str, proporcion: tuple[int, int], leyenda: str):
    layout = calcular_layout(
        _config(columnas=30, leyenda=leyenda), *proporcion, REGISTRO_PAPELES[nombre]
    )
    assert _dentro(layout.bbox_contenido(), layout.area_util())


def test_grilla_centrada_horizontalmente():
    layout = calcular_layout(_config(columnas=30), 1000, 1000, REGISTRO_PAPELES["A4"])
    x0, _, x1, _ = layout.rect_grilla
    ancho, _ = layout.pagina_pt
    assert x0 == pytest.approx(ancho - x1)


def test_orientacion_auto_horizontal_para_imagen_ancha():
    layout = calcular_layout(_config(columnas=40), 1600, 900, REGISTRO_PAPELES["A4"])
    assert layout.orientacion is Orientacion.LANDSCAPE
    ancho, alto = layout.pagina_pt
    assert ancho > alto


def test_recorte_center_usa_la_proporcion_del_area():
    layout = calcular_layout(
        _config(columnas=40, recorte="center"), 1000, 3000, REGISTRO_PAPELES["A4"]
    )
    # Área disponible con leyenda: 184,6 × 233 mm → 40 × 50
    assert layout.filas == 50


def test_filas_fijas_se_respetan():
    layout = calcular_layout(
        _config(columnas=40), 1000, 1000, REGISTRO_PAPELES["LETTER"], filas_fijas=43
    )
    assert layout.filas == 43


# --- T17: celda chica y sugerencias ---


def test_ca7_celda_chica_da_error_con_sugerencias():
    config = _config(columnas=60)
    with pytest.raises(CeldaDemasiadoChicaError) as info:
        calcular_layout(config, 1000, 1000, REGISTRO_PAPELES["A4"])
    error = info.value
    mensaje = str(error)
    assert "4 mm" in mensaje and "3,1 mm" in mensaje
    assert error.columnas_max == 46
    assert error.papel_sugerido == "TABLOID"
    assert error.personalizado_mm is not None
    assert "46 columnas" in mensaje and "TABLOID" in mensaje and "personalizado" in mensaje


def test_ca7_las_sugerencias_funcionan():
    config = _config(columnas=60)
    with pytest.raises(CeldaDemasiadoChicaError) as info:
        calcular_layout(config, 1000, 1000, REGISTRO_PAPELES["A4"])
    error = info.value
    # 1) Columnas sugeridas en el mismo papel
    con_columnas = calcular_layout(
        _config(columnas=error.columnas_max), 1000, 1000, REGISTRO_PAPELES["A4"]
    )
    assert con_columnas.celda_pt >= CELDA_MIN
    # 2) Papel sugerido con las mismas columnas
    con_papel = calcular_layout(config, 1000, 1000, REGISTRO_PAPELES[error.papel_sugerido])
    assert con_papel.celda_pt >= CELDA_MIN
    # 3) Papel personalizado sugerido (con la leyenda incluida debajo)
    personalizado = papel_personalizado(*error.personalizado_mm)
    con_custom = calcular_layout(config, 1000, 1000, personalizado)
    assert con_custom.celda_pt >= CELDA_MIN
    assert con_custom.leyenda_en_plantilla


def test_columnas_maximas_es_la_mayor_posible():
    with pytest.raises(CeldaDemasiadoChicaError) as info:
        calcular_layout(_config(columnas=60), 1000, 1000, REGISTRO_PAPELES["A4"])
    siguiente = info.value.columnas_max + 1
    with pytest.raises(CeldaDemasiadoChicaError):
        calcular_layout(_config(columnas=siguiente), 1000, 1000, REGISTRO_PAPELES["A4"])


def test_sin_papel_del_registro_que_sirva():
    with pytest.raises(CeldaDemasiadoChicaError) as info:
        calcular_layout(_config(columnas=200), 1000, 1000, REGISTRO_PAPELES["A4"])
    assert info.value.papel_sugerido is None
    assert "usar papel" not in str(info.value)


def test_personalizado_demasiado_grande_se_omite():
    # 200 × 300 celdas a 4 mm superan los 1200 mm de alto
    with pytest.raises(CeldaDemasiadoChicaError) as info:
        calcular_layout(_config(columnas=200), 1000, 1500, REGISTRO_PAPELES["A4"])
    assert info.value.personalizado_mm is None


def test_rf6_4_celda_chica_aun_sin_leyenda_da_error():
    with pytest.raises(CeldaDemasiadoChicaError):
        calcular_layout(
            _config(columnas=60, leyenda="separate"), 1000, 1000, REGISTRO_PAPELES["A4"]
        )


# --- T18: multi-papel ---


def test_multi_papel_misma_grilla():
    config = _config(columnas=40, papeles=["A4", "LETTER"])
    layouts = calcular_layouts(config, 1000, 1300)
    assert list(layouts) == ["A4", "LETTER"]
    a4, letter = layouts["A4"], layouts["LETTER"]
    assert (a4.columnas, a4.filas) == (letter.columnas, letter.filas)
    assert a4.celda_pt != letter.celda_pt  # cambia el tamaño de celda, no la grilla


def test_multi_papel_con_recorte_center_usa_el_primer_papel():
    config = _config(columnas=40, papeles=["LETTER", "A4"], recorte="center")
    layouts = calcular_layouts(config, 1000, 1300)
    solo_letter = calcular_layout(config, 1000, 1300, REGISTRO_PAPELES["LETTER"])
    assert layouts["A4"].filas == solo_letter.filas


def test_multi_papel_falla_un_papel_y_lo_nombra():
    # Imagen alta con 36 columnas: entra en A4 pero no en Letter (que es más bajo)
    config = _config(columnas=36, papeles=["A4", "LETTER"], leyenda="separate")
    with pytest.raises(CeldaDemasiadoChicaError) as info:
        calcular_layouts(config, 1000, 1800)
    assert "LETTER" in str(info.value)
    columnas = info.value.columnas_max
    assert columnas is not None
    # Las columnas sugeridas sirven para los dos papeles
    arreglada = _config(columnas=columnas, papeles=["A4", "LETTER"], leyenda="separate")
    layouts = calcular_layouts(arreglada, 1000, 1800)
    assert all(lay.celda_pt >= CELDA_MIN for lay in layouts.values())


def test_multi_papel_custom():
    config = _config(columnas=40, papeles=["A4", "CUSTOM"], papel_personalizado=(300, 400))
    layouts = calcular_layouts(config, 1000, 1000)
    assert layouts["CUSTOM"].papel.ancho_mm == 300
