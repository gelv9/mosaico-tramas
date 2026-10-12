"""Tests del preprocesamiento de imágenes (T8)."""

import io

import numpy as np
import pytest
from PIL import Image

from mosaico_tramas.avisos import CodigoAviso
from mosaico_tramas.config import Recorte
from mosaico_tramas.errores import ImagenInvalidaError
from mosaico_tramas.imagen import a_grilla, cargar_luminancia
from tests.conftest import a_png, generar_degradado


def test_carga_png_en_rango(png_degradado: bytes):
    lum = cargar_luminancia(png_degradado, max_mb=20)
    assert lum.shape == (300, 400)
    assert lum.dtype == np.float32
    assert lum.min() == pytest.approx(0.0) and lum.max() == pytest.approx(1.0)


def test_alfa_se_compone_sobre_blanco():
    rgba = np.zeros((10, 10, 4), dtype=np.uint8)  # negro totalmente transparente
    lum = cargar_luminancia(a_png(rgba, "RGBA"), max_mb=20)
    assert np.allclose(lum, 1.0)


def test_respeta_orientacion_exif():
    # Imagen de 40 × 20 (apaisada) con orientación EXIF 6: se ve vertical (20 × 40)
    img = Image.fromarray(generar_degradado(40, 20))
    exif = Image.Exif()
    exif[0x0112] = 6
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", exif=exif.tobytes())
    lum = cargar_luminancia(buffer.getvalue(), max_mb=20)
    assert lum.shape == (40, 20)


def test_bytes_basura_dan_error_en_espanol():
    with pytest.raises(ImagenInvalidaError, match="no es una imagen JPG o PNG válida"):
        cargar_luminancia(b"esto no es una imagen", max_mb=20)


def test_formato_no_soportado():
    buffer = io.BytesIO()
    Image.new("L", (10, 10)).save(buffer, format="GIF")
    with pytest.raises(ImagenInvalidaError, match="Subí un JPG o PNG"):
        cargar_luminancia(buffer.getvalue(), max_mb=20)


def test_archivo_demasiado_grande(png_degradado: bytes):
    with pytest.raises(ImagenInvalidaError, match="el máximo es 0.0001 MB"):
        cargar_luminancia(png_degradado, max_mb=0.0001)


def test_grilla_forma_y_oscuridad(png_degradado: bytes):
    lum = cargar_luminancia(png_degradado, max_mb=20)
    oscuridad, avisos = a_grilla(lum, columnas=40, filas=30, recorte=Recorte.FIT)
    assert oscuridad.shape == (30, 40)
    assert oscuridad.dtype == np.float32
    assert avisos == ()
    # El degradado va de negro (izquierda) a blanco (derecha): la oscuridad baja
    assert oscuridad[:, 0].mean() > 0.95
    assert oscuridad[:, -1].mean() < 0.05


def test_estiramiento_lleva_percentiles_a_extremos():
    # Imagen de bajo contraste (grises entre 100 y 150)
    img = (100 + generar_degradado(200, 100) // 5).astype(np.uint8)
    lum = cargar_luminancia(a_png(img), max_mb=20)
    oscuridad, _ = a_grilla(lum, columnas=50, filas=25, recorte=Recorte.FIT)
    assert oscuridad.min() == pytest.approx(0.0, abs=1e-6)
    assert oscuridad.max() == pytest.approx(1.0, abs=1e-6)
    assert np.percentile(oscuridad, 50) == pytest.approx(0.5, abs=0.05)


def test_imagen_plana_avisa_poco_rango(png_plana: bytes):
    lum = cargar_luminancia(png_plana, max_mb=20)
    oscuridad, avisos = a_grilla(lum, columnas=20, filas=20, recorte=Recorte.FIT)
    assert [a.codigo for a in avisos] == [CodigoAviso.POCO_RANGO_TONAL]
    assert "rango tonal" in avisos[0].mensaje
    assert np.allclose(oscuridad, oscuridad[0, 0])


def test_recorte_center_toma_el_centro():
    # Imagen apaisada: mitad izquierda negra, centro gris, derecha blanca
    img = np.full((100, 300), 128, dtype=np.uint8)
    img[:, :100] = 0
    img[:, 200:] = 255
    img[40:60, 140:160] = 0  # detalle oscuro en el centro, para que haya rango
    lum = cargar_luminancia(a_png(img), max_mb=20)
    oscuridad, _ = a_grilla(lum, columnas=10, filas=10, recorte=Recorte.CENTER)
    # Con recorte cuadrado al centro no quedan las franjas negra ni blanca de los costados
    assert oscuridad[0, 0] == pytest.approx(oscuridad[0, -1], abs=0.05)


def test_grilla_determinista(png_foto: bytes):
    lum = cargar_luminancia(png_foto, max_mb=20)
    a, _ = a_grilla(lum, columnas=40, filas=53, recorte=Recorte.FIT)
    b, _ = a_grilla(lum, columnas=40, filas=53, recorte=Recorte.FIT)
    assert np.array_equal(a, b)
