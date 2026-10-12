"""Tests del render del PDF (T19–T22)."""

import io
import re
from collections import Counter

import numpy as np
import numpy.typing as npt
import pytest
from pypdf import PdfReader

from mosaico_tramas.config import MosaicoConfig
from mosaico_tramas.layout import Layout, calcular_layout
from mosaico_tramas.papel import REGISTRO_PAPELES, Orientacion, mm_a_pt
from mosaico_tramas.render_pdf import (
    INSTRUCCION,
    NOMBRE_PUNTO_GRILLA,
    NOMBRE_PUNTO_GRILLA_TENUE,
    generar_pdf,
    nombre_form,
)
from mosaico_tramas.simbolos.seleccion import simbolos_para

_NUMERO_EN = re.compile(r"1 0 0 1 (-?[\d.]+) (-?[\d.]+) Tm \((\d+)\) Tj")
_FORM = re.compile(r"/FormXob\.(\w+) Do")


def _niveles(filas: int, cols: int, n: int, semilla: int = 7) -> npt.NDArray[np.uint8]:
    return np.random.default_rng(semilla).integers(1, n + 1, (filas, cols)).astype(np.uint8)


def _generar(
    filas: int = 20,
    cols: int = 15,
    papel: str = "A4",
    ancho_img: int = 750,
    alto_img: int = 1000,
    **valores: object,
) -> tuple[PdfReader, npt.NDArray[np.uint8], Layout, MosaicoConfig]:
    config = MosaicoConfig.crear(columnas=cols, papeles=[papel], **valores)
    layout = calcular_layout(
        config, ancho_img, alto_img, REGISTRO_PAPELES[papel], filas_fijas=filas
    )
    niveles = _niveles(filas, cols, config.n_simbolos)
    pdf = generar_pdf(niveles, simbolos_para(config), layout, config)
    return PdfReader(io.BytesIO(pdf)), niveles, layout, config


def _contenido(lector: PdfReader, pagina: int) -> str:
    return lector.pages[pagina].get_contents().get_data().decode("latin-1")


def _numeros_en_grilla(contenido: str, layout: Layout) -> list[int]:
    """Números escritos dentro de la grilla (la leyenda también tiene números)."""
    x0, y0, x1, y1 = layout.rect_grilla
    return [
        int(n)
        for x, y, n in _NUMERO_EN.findall(contenido)
        if x0 <= float(x) <= x1 and y0 <= float(y) <= y1
    ]


# --- T19: plantilla ---


def test_ca14_todas_las_celdas_tienen_numero():
    lector, niveles, layout, _ = _generar()
    numeros = _numeros_en_grilla(_contenido(lector, 0), layout)
    assert len(numeros) == niveles.size
    assert Counter(numeros) == Counter(int(v) for v in niveles.ravel())
    assert 0 not in numeros


def test_no_hay_marca_de_vacio_ni_entrada_blank():
    lector, _, _, _ = _generar(leyenda="separate")
    assert all("marca" not in nombre for nombre in _FORM.findall(_contenido(lector, 0)))
    assert "blank" not in lector.pages[1].extract_text()


def test_numeros_y_grilla_en_gris():
    lector, _, _, _ = _generar()
    contenido = _contenido(lector, 0)
    assert ".82 G" in contenido  # trazo de la grilla al 18 % de negro (gris muy claro)
    assert ".5 g" in contenido  # relleno de los números al 50 % de negro


# --- T20: leyenda ---


def test_ca5_leyenda_debajo_en_la_plantilla():
    lector, _, layout, _ = _generar(filas=20, cols=15)
    assert layout.leyenda_en_plantilla
    assert len(lector.pages) == 2  # plantilla + solución
    assert INSTRUCCION in lector.pages[0].extract_text().replace("\n", " ")


def test_ca5_leyenda_movida_va_en_la_pagina_2():
    # 45 × 65 en A4: con la leyenda debajo la celda bajaría de 4 mm
    lector, _, layout, _ = _generar(
        filas=65, cols=45, ancho_img=1000, alto_img=1450, celda_min_mm=4.0
    )
    assert not layout.leyenda_en_plantilla
    assert len(lector.pages) == 3
    assert INSTRUCCION not in lector.pages[0].extract_text().replace("\n", " ")
    assert INSTRUCCION in lector.pages[1].extract_text().replace("\n", " ")


def test_ca6_leyenda_aparte_siempre_en_su_pagina():
    lector, _, _, _ = _generar(leyenda="separate")
    assert len(lector.pages) == 3
    assert INSTRUCCION not in lector.pages[0].extract_text().replace("\n", " ")
    assert INSTRUCCION in lector.pages[1].extract_text().replace("\n", " ")


def test_instruccion_sin_celdas_vacias():
    assert INSTRUCCION == "Draw the symbol shown for each number in every cell."


def test_leyenda_lista_todos_los_niveles():
    lector, _, _, config = _generar(leyenda="separate")
    texto = lector.pages[1].extract_text()
    for nivel in range(1, config.n_simbolos + 1):
        assert str(nivel) in texto


# --- T21: solución y orden de páginas ---


@pytest.mark.parametrize(
    ("leyenda", "solucion", "paginas"),
    [("below", True, 2), ("below", False, 1), ("separate", True, 3), ("separate", False, 2)],
)
def test_cantidad_de_paginas(leyenda: str, solucion: bool, paginas: int):
    lector, _, _, _ = _generar(leyenda=leyenda, incluir_solucion=solucion)
    assert len(lector.pages) == paginas


def test_solucion_tiene_cada_simbolo_y_nada_mas():
    lector, niveles, _, config = _generar()
    contenido = _contenido(lector, 1)
    assert _NUMERO_EN.findall(contenido) == []
    formas = Counter(_FORM.findall(contenido))
    assert sum(formas.values()) == niveles.size  # un símbolo en cada celda
    simbolos = simbolos_para(config)
    for nivel in range(1, config.n_simbolos + 1):
        assert formas[nombre_form(simbolos[nivel - 1])] == int((niveles == nivel).sum())


def test_pdf_determinista():
    config = MosaicoConfig.crear(columnas=15)
    layout = calcular_layout(config, 750, 1000, REGISTRO_PAPELES["A4"], filas_fijas=20)
    niveles = _niveles(20, 15, config.n_simbolos)
    simbolos = simbolos_para(config)
    assert generar_pdf(niveles, simbolos, layout, config) == generar_pdf(
        niveles, simbolos, layout, config
    )


# --- T22: dimensiones y márgenes (CA4) ---

ESPERADOS_PT = {
    "A4": (595.28, 841.89),
    "LETTER": (612.0, 792.0),
    "A3": (841.89, 1190.55),
    "TABLOID": (792.0, 1224.0),
}
_COORD = r"(-?\d+(?:\.\d+)?)"
_MOVER = re.compile(rf"{_COORD} {_COORD} [ml]\b")
_TRASLADAR = re.compile(rf"q\n1 0 0 1 {_COORD} {_COORD} cm")  # forms colocados
_TEXTO = re.compile(rf"1 0 0 1 {_COORD} {_COORD} Tm")


def _extremos(contenido: str, celda: float) -> tuple[float, float, float, float]:
    """Caja que envuelve las coordenadas dibujadas (líneas, textos y forms colocados)."""
    xs: list[float] = []
    ys: list[float] = []
    for x, y in _MOVER.findall(contenido):
        xs.append(float(x))
        ys.append(float(y))
    for x, y in _TEXTO.findall(contenido):
        xs.append(float(x))
        ys.append(float(y))
    for x, y in _TRASLADAR.findall(contenido):
        # Un form colocado en (x, y) ocupa hasta (x + celda, y + celda)
        xs += [float(x), float(x) + celda]
        ys += [float(y), float(y) + celda]
    return min(xs), min(ys), max(xs), max(ys)


@pytest.mark.parametrize("papel", sorted(ESPERADOS_PT))
@pytest.mark.parametrize("orientacion", ["portrait", "landscape"])
def test_ca4_medidas_y_margenes(papel: str, orientacion: str):
    lector, _, layout, _ = _generar(
        papel=papel, orientacion=orientacion, filas=20, cols=20, ancho_img=1000, alto_img=1000
    )
    ancho, alto = ESPERADOS_PT[papel]
    if orientacion == "landscape":
        ancho, alto = alto, ancho
    for pagina in lector.pages:
        assert float(pagina.mediabox.width) == pytest.approx(ancho, abs=0.01)
        assert float(pagina.mediabox.height) == pytest.approx(alto, abs=0.01)
    margen = mm_a_pt(12.7)
    for i in range(len(lector.pages)):
        x0, y0, x1, y1 = _extremos(_contenido(lector, i), layout.celda_pt)
        tol = 0.5
        assert x0 >= margen - tol and y0 >= margen - tol
        assert x1 <= ancho - margen + tol and y1 <= alto - margen + tol
    assert layout.orientacion is Orientacion(orientacion)


def test_ca4_papel_personalizado():
    config = MosaicoConfig.crear(columnas=20, papeles=["CUSTOM"], papel_personalizado=(300, 400))
    from mosaico_tramas.papel import papel_personalizado

    layout = calcular_layout(config, 1000, 1000, papel_personalizado(300, 400), filas_fijas=20)
    pdf = generar_pdf(_niveles(20, 20, 6), simbolos_para(config), layout, config)
    caja = PdfReader(io.BytesIO(pdf)).pages[0].mediabox
    assert float(caja.width) == pytest.approx(mm_a_pt(300), abs=0.01)
    assert float(caja.height) == pytest.approx(mm_a_pt(400), abs=0.01)


def test_solucion_centrada_en_la_pagina():
    # Con la leyenda debajo, la plantilla sube la grilla; la solución la centra
    lector, _, layout, _ = _generar(filas=20, cols=15)
    assert layout.leyenda_en_plantilla
    contenido = _contenido(lector, 1)
    desplazamiento = re.search(rf"\n1 0 0 1 0 {_COORD} cm", contenido)
    assert desplazamiento is not None
    _, ay0, _, ay1 = layout.area_util()
    _, gy0, _, gy1 = layout.rect_grilla
    dy = float(desplazamiento.group(1))
    assert (gy0 + dy) - ay0 == pytest.approx(ay1 - (gy1 + dy), abs=0.01)


# --- T30: estilo de grilla (CA16) ---


def test_ca16_grilla_de_puntos_en_cada_esquina():
    lector, _, layout, _ = _generar(filas=20, cols=15, leyenda="separate", estilo_grilla="dots")
    contenido = _contenido(lector, 0)
    formas = Counter(_FORM.findall(contenido))
    assert formas[NOMBRE_PUNTO_GRILLA] == (layout.columnas + 1) * (layout.filas + 1)
    # Sin la leyenda en la página, no queda ningún segmento de línea (la grilla son puntos)
    assert not re.search(r" l\n", contenido)


def test_ca16_grilla_de_lineas_sin_puntos():
    lector, _, _, _ = _generar(filas=20, cols=15, leyenda="separate")
    assert NOMBRE_PUNTO_GRILLA not in _FORM.findall(_contenido(lector, 0))


def test_grilla_tenue_de_la_solucion_respeta_el_estilo():
    lector, _, layout, _ = _generar(estilo_grilla="dots", grilla_en_solucion=True)
    formas = Counter(_FORM.findall(_contenido(lector, 1)))
    assert formas[NOMBRE_PUNTO_GRILLA_TENUE] == (layout.columnas + 1) * (layout.filas + 1)


# --- T32: grosor de trazo (CA17) ---


def _ancho_de_linea_del_form(lector: PdfReader, pagina: int, nombre: str) -> float:
    xobjetos = lector.pages[pagina]["/Resources"]["/XObject"]
    datos = xobjetos[f"/FormXob.{nombre}"].get_object().get_data().decode("latin-1")
    return float(re.search(r"(-?[\d.]+) w", datos).group(1))


@pytest.mark.parametrize("grosor", [0.2, 0.5])
def test_ca17_la_solucion_usa_el_grosor_configurado(grosor: float):
    lector, _, _, config = _generar(grosor_trazo_mm=grosor)
    simbolo = simbolos_para(config)[1]  # diagonal /
    ancho = _ancho_de_linea_del_form(lector, 1, nombre_form(simbolo))
    assert ancho == pytest.approx(mm_a_pt(grosor), abs=0.01)
