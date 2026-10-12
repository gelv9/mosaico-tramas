"""Fixtures compartidas de pytest: entorno aislado e imágenes sintéticas deterministas."""

import io
import os
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from PIL import Image


@pytest.fixture(autouse=True)
def _entorno_limpio(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Aísla los tests de un .env local y de variables MOSAICO_ del sistema."""
    for clave in list(os.environ):
        if clave.startswith("MOSAICO_"):
            monkeypatch.delenv(clave, raising=False)
    monkeypatch.chdir(tmp_path)


# --- Generadores de imágenes sintéticas (T9) ---


def a_png(pixeles: npt.NDArray[np.uint8], modo: str = "L") -> bytes:
    """Codifica un array como PNG (Pillow sin metadatos: bytes estables)."""
    buffer = io.BytesIO()
    Image.fromarray(pixeles, modo).save(buffer, format="PNG")
    return buffer.getvalue()


def generar_degradado(ancho: int = 400, alto: int = 300) -> npt.NDArray[np.uint8]:
    """Degradado horizontal de negro a blanco: rango tonal completo y parejo."""
    fila = np.linspace(0, 255, ancho)
    return np.tile(fila, (alto, 1)).round().astype(np.uint8)


def generar_foto_sintetica(ancho: int = 600, alto: int = 800) -> npt.NDArray[np.uint8]:
    """'Retrato' sintético: fondo radial, óvalo claro, formas oscuras y ruido con semilla."""
    yy, xx = np.mgrid[0:alto, 0:ancho].astype(np.float64)
    cx, cy = ancho / 2, alto / 2
    radial = np.hypot((xx - cx) / ancho, (yy - cy) / alto)
    img = 200 - 260 * radial  # fondo: más claro al centro
    cara = ((xx - cx) / (ancho * 0.28)) ** 2 + ((yy - cy * 0.9) / (alto * 0.3)) ** 2 < 1
    img[cara] = 225 - 60 * ((yy[cara] - cy * 0.6) / alto)  # óvalo con sombreado vertical
    for ox in (-0.1, 0.1):  # "ojos"
        ojo = np.hypot(xx - cx - ox * ancho, yy - cy * 0.75) < ancho * 0.04
        img[ojo] = 30
    pelo = (yy < alto * 0.25) & (np.abs(xx - cx) < ancho * 0.35)
    img[pelo] = 50 + 40 * (yy[pelo] / alto)
    rng = np.random.default_rng(42)
    img += rng.normal(0, 8, img.shape)
    return np.clip(img, 0, 255).round().astype(np.uint8)


def generar_fondo_plano(ancho: int = 400, alto: int = 400) -> npt.NDArray[np.uint8]:
    """El 40 % superior es blanco puro y el resto un degradado: prueba empates masivos."""
    img = generar_degradado(ancho, alto)
    img[: int(alto * 0.4)] = 255
    return img


def generar_plana(ancho: int = 300, alto: int = 300) -> npt.NDArray[np.uint8]:
    """Imagen gris uniforme: sin rango tonal."""
    return np.full((alto, ancho), 128, dtype=np.uint8)


@pytest.fixture
def png_degradado() -> bytes:
    return a_png(generar_degradado())


@pytest.fixture
def png_foto() -> bytes:
    return a_png(generar_foto_sintetica())


@pytest.fixture
def png_fondo_plano() -> bytes:
    return a_png(generar_fondo_plano())


@pytest.fixture
def png_plana() -> bytes:
    return a_png(generar_plana())
