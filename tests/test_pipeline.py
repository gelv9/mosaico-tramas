"""Tests del pipeline completo (T24, T25)."""

import io
import subprocess
import sys
import time
import zipfile

import pytest
from pypdf import PdfReader

from mosaico_tramas.avisos import CodigoAviso
from mosaico_tramas.config import MosaicoConfig
from mosaico_tramas.errores import CeldaDemasiadoChicaError
from mosaico_tramas.pipeline import (
    archivos,
    empaquetar_zip,
    generar_mosaico,
    generar_preview,
    nombre_archivo,
    nombre_base_seguro,
)
from tests.conftest import a_png, generar_foto_sintetica


def test_genera_pdf_png_y_distribucion(png_foto: bytes):
    resultado = generar_mosaico(png_foto, MosaicoConfig.crear(columnas=30))
    assert set(resultado.pdfs) == {"A4"}
    assert resultado.pdfs["A4"].startswith(b"%PDF")
    assert resultado.png_solucion.startswith(b"\x89PNG")
    assert resultado.columnas == 30
    assert resultado.filas == 40  # foto de 600 × 800
    assert sum(resultado.distribucion.conteos) == 30 * 40
    assert [s.id for s in resultado.simbolos][0] == "punto"


@pytest.mark.parametrize("metodo", ["quantiles", "kmeans"])
def test_ca8_determinismo_de_punta_a_punta(metodo: str, png_foto: bytes):
    config = MosaicoConfig.crear(columnas=30, metodo=metodo, papeles=["A4", "LETTER"])
    a = generar_mosaico(png_foto, config)
    b = generar_mosaico(png_foto, config)
    assert a.pdfs == b.pdfs
    assert a.png_solucion == b.png_solucion
    assert a.png_plantilla == b.png_plantilla
    assert empaquetar_zip(a, "foto") == empaquetar_zip(b, "foto")


def test_multi_papel_misma_grilla_y_zip(png_foto: bytes):
    config = MosaicoConfig.crear(columnas=30, papeles=["A4", "LETTER"])
    resultado = generar_mosaico(png_foto, config)
    assert set(resultado.pdfs) == {"A4", "LETTER"}
    with zipfile.ZipFile(io.BytesIO(empaquetar_zip(resultado, "foto"))) as zf:
        assert sorted(zf.namelist()) == [
            "foto_A4_6sym_30x40.pdf",
            "foto_LETTER_6sym_30x40.pdf",
            "foto_solution_6sym_30x40.png",
            "foto_template_6sym_30x40.png",
        ]
    for pdf in resultado.pdfs.values():
        assert len(PdfReader(io.BytesIO(pdf)).pages) == 2


def test_rf5_8_nombres(png_foto: bytes):
    resultado = generar_mosaico(png_foto, MosaicoConfig.crear(columnas=30))
    assert nombre_archivo("perro", resultado, "A4", "pdf") == "perro_A4_6sym_30x40.pdf"
    assert "perro_solution_6sym_30x40.png" in archivos(resultado, "perro")


@pytest.mark.parametrize(
    ("original", "esperado"),
    [
        ("Mi Perro (1).jpg", "Mi_Perro_1"),
        ("árbol.png", "rbol"),
        ("....png", "mosaico"),
        ("foto", "foto"),
    ],
)
def test_nombre_base_seguro(original: str, esperado: str):
    assert nombre_base_seguro(original) == esperado


def test_preview_sin_pdf_y_mas_chica(png_foto: bytes):
    resultado = generar_preview(png_foto, MosaicoConfig.crear(columnas=30))
    assert resultado.pdfs == {}
    assert resultado.png_solucion


def test_avisos_combinados(png_plana: bytes):
    resultado = generar_mosaico(png_plana, MosaicoConfig.crear(columnas=20), con_pdf=False)
    assert CodigoAviso.POCO_RANGO_TONAL in {a.codigo for a in resultado.avisos}


def test_aviso_de_leyenda_movida_nombra_el_papel():
    imagen = a_png(generar_foto_sintetica(1000, 1450))
    config = MosaicoConfig.crear(columnas=45, papeles=["A4", "LETTER"], leyenda="below")
    with pytest.raises(CeldaDemasiadoChicaError):
        generar_mosaico(imagen, config)  # en Letter no entra: error, no PDF a medias
    resultado = generar_mosaico(
        imagen, config.model_copy(update={"papeles": ("A4",)}), con_png=False
    )
    assert any(a.codigo is CodigoAviso.LEYENDA_MOVIDA for a in resultado.avisos)


def test_celda_chica_no_genera_nada(png_foto: bytes):
    with pytest.raises(CeldaDemasiadoChicaError, match="4 mm"):
        generar_mosaico(png_foto, MosaicoConfig.crear(columnas=80))


def test_ca12_el_nucleo_no_importa_streamlit(tmp_path):
    imagen = tmp_path / "foto.png"
    imagen.write_bytes(a_png(generar_foto_sintetica()))
    codigo = (
        "import sys\n"
        "from mosaico_tramas.config import MosaicoConfig\n"
        "from mosaico_tramas.pipeline import generar_mosaico\n"
        f"r = generar_mosaico(open(r'{imagen}', 'rb').read(), MosaicoConfig.crear(columnas=20))\n"
        "print('streamlit' in sys.modules, len(r.pdfs))\n"
    )
    salida = subprocess.run(
        [sys.executable, "-c", codigo], capture_output=True, text=True, check=True
    ).stdout.split()
    assert salida == ["False", "1"]


# --- T25: rendimiento (RNF1, CA13) ---


@pytest.mark.slow
def test_ca13_100x140_en_menos_de_5_segundos():
    imagen = a_png(generar_foto_sintetica(1000, 1400))
    config = MosaicoConfig.crear(columnas=100, papeles=["CUSTOM"], papel_personalizado=(430, 600))
    generar_mosaico(imagen, config, con_png=False)  # calienta imports y caches
    inicio = time.perf_counter()
    resultado = generar_mosaico(imagen, config, con_png=False)
    duracion = time.perf_counter() - inicio
    assert (resultado.columnas, resultado.filas) == (100, 140)
    assert duracion < 5.0, f"tardó {duracion:.2f} s"
