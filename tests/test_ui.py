"""Tests de la UI con streamlit.testing (T26, T27)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.conftest import a_png, generar_foto_sintetica

APP = str(Path(__file__).resolve().parents[1] / "src" / "mosaico_tramas" / "ui" / "app.py")
TIMEOUT = 60


@pytest.fixture
def app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=TIMEOUT)


@pytest.fixture
def app_con_imagen(app: AppTest) -> AppTest:
    app.session_state["imagen_prueba"] = a_png(generar_foto_sintetica())
    app.session_state["imagen_nombre"] = "foto prueba.png"
    return app


def _textos(elementos: object) -> str:
    return " ".join(str(e.value) for e in elementos)  # type: ignore[attr-defined]


# --- T26: controles y preview ---


def test_arranca_sin_imagen(app: AppTest):
    app.run()
    assert not app.exception
    assert "Subí una imagen" in _textos(app.info)


def test_tiene_todos_los_controles(app: AppTest):
    app.run()
    claves = {
        "n_simbolos",
        "usar_triangulo",
        "metodo",
        "reduccion_ruido",
        "umbral_ruido",
        "limitar_oscuros",
        "max_oscuros_pct",
        "columnas",
        "papeles",
        "orientacion",
        "margen_mm",
        "rellenar",
        "leyenda",
        "incluir_solucion",
        "marca_blanco",
    }
    for clave in claves:
        assert clave in app.session_state, clave


def test_preview_con_imagen(app_con_imagen: AppTest):
    app_con_imagen.run()
    assert not app_con_imagen.exception
    assert not app_con_imagen.error
    assert len(app_con_imagen.tabs) == 3
    assert "Grilla 40 × 53" in _textos(app_con_imagen.caption)


def test_sin_triangulo_baja_el_maximo_de_simbolos(app_con_imagen: AppTest):
    app_con_imagen.run()
    app_con_imagen.slider(key="n_simbolos").set_value(7).run()
    app_con_imagen.checkbox(key="usar_triangulo").uncheck().run()
    assert app_con_imagen.slider(key="n_simbolos").value == 6
    assert not app_con_imagen.error


def test_celda_chica_muestra_error_en_espanol(app_con_imagen: AppTest):
    app_con_imagen.run()
    app_con_imagen.number_input(key="columnas").set_value(80).run()
    assert "4 mm" in _textos(app_con_imagen.error)
    assert len(app_con_imagen.tabs) == 0


def test_papel_personalizado_pide_medidas(app_con_imagen: AppTest):
    app_con_imagen.run()
    app_con_imagen.multiselect(key="papeles").set_value(["CUSTOM"]).run()
    assert app_con_imagen.number_input(key="custom_ancho").value == 430.0
    assert "CUSTOM" in _textos(app_con_imagen.caption)


# --- T27: sugerencia con un clic y descargas ---


def test_sugerencia_de_columnas_en_un_clic(app_con_imagen: AppTest):
    app_con_imagen.run()
    app_con_imagen.number_input(key="columnas").set_value(80).run()
    app_con_imagen.button(key="sugerencia_columnas").click().run()
    assert app_con_imagen.number_input(key="columnas").value < 80
    assert not app_con_imagen.error


def test_generar_pdf_habilita_descargas(app_con_imagen: AppTest):
    app_con_imagen.run()
    app_con_imagen.button(key="generar").click().run()
    assert not app_con_imagen.exception
    descargas = app_con_imagen.get("download_button")
    etiquetas = " ".join(d.proto.label for d in descargas)
    assert "Descargar PDF" in etiquetas and "Descargar PNG" in etiquetas


def test_multi_papel_descarga_zip(app_con_imagen: AppTest):
    app_con_imagen.run()
    app_con_imagen.multiselect(key="papeles").set_value(["A4", "LETTER"]).run()
    app_con_imagen.button(key="generar").click().run()
    etiquetas = " ".join(d.proto.label for d in app_con_imagen.get("download_button"))
    assert "Descargar ZIP (A4, LETTER)" in etiquetas
