"""Previews raster por composición de tiles (RF5.6, design.md §9).

Cada símbolo, número y marca se rasteriza una sola vez a t × t px; la imagen final se arma
indexando los tiles con la matriz de niveles, sin dibujar celda por celda.
"""

import io
from functools import lru_cache

import numpy as np
import numpy.typing as npt
from PIL import Image, ImageDraw, ImageFont

from mosaico_tramas.simbolos.primitivas import Simbolo
from mosaico_tramas.simbolos.raster import rasterizar

TILE_MIN_PX = 4
# Grises en escala 0–255 (equivalentes a los del PDF)
GRIS_GRILLA = 166  # 35 % de negro
GRIS_NUMEROS = 128  # 50 % de negro

type Imagen = npt.NDArray[np.uint8]


def tamano_tile(columnas: int, filas: int, lado_px: int) -> int:
    """Lado del tile para que el lado largo de la imagen no supere lado_px."""
    return max(TILE_MIN_PX, lado_px // max(columnas, filas))


def _componer(tiles: Imagen, niveles: npt.NDArray[np.uint8]) -> Imagen:
    """(N+1, t, t) indexados por niveles (F, C) → imagen (F·t, C·t)."""
    filas, cols = niveles.shape
    t = tiles.shape[1]
    return tiles[niveles].transpose(0, 2, 1, 3).reshape(filas * t, cols * t)


def _a_png(pixeles: Imagen) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(pixeles, "L").save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def png_solucion(
    niveles: npt.NDArray[np.uint8], simbolos: tuple[Simbolo, ...], lado_px: int
) -> bytes:
    """Resultado terminado: símbolos en negro sobre blanco."""
    t = tamano_tile(niveles.shape[1], niveles.shape[0], lado_px)
    tinta = [np.zeros((t, t), np.float32)] + [rasterizar(s, t) for s in simbolos]
    tiles = np.round((1.0 - np.stack(tinta)) * 255).astype(np.uint8)
    return _a_png(_componer(tiles, niveles))


@lru_cache(maxsize=32)
def _tiles_plantilla(n: int, t: int, marca_blanco: bool) -> Imagen:
    """Tiles con borde gris arriba y a la izquierda, número gris y marca en el vacío."""
    fuente = ImageFont.load_default(size=max(6, round(0.45 * t)))
    tiles = []
    for nivel in range(n + 1):
        tile = Image.new("L", (t, t), 255)
        dibujo = ImageDraw.Draw(tile)
        dibujo.line([(0, 0), (t - 1, 0)], fill=GRIS_GRILLA)
        dibujo.line([(0, 0), (0, t - 1)], fill=GRIS_GRILLA)
        if nivel > 0:
            dibujo.text((t / 2, t / 2), str(nivel), fill=GRIS_NUMEROS, font=fuente, anchor="mm")
        elif marca_blanco:
            r = max(1.0, 0.04 * t)
            dibujo.ellipse([t / 2 - r, t / 2 - r, t / 2 + r, t / 2 + r], fill=GRIS_GRILLA)
        tiles.append(np.asarray(tile))
    return np.stack(tiles)


def png_plantilla(niveles: npt.NDArray[np.uint8], lado_px: int, marca_blanco: bool) -> bytes:
    """Plantilla: grilla y números en gris; las celdas vacías sin número."""
    filas, cols = niveles.shape
    t = tamano_tile(cols, filas, lado_px)
    n = int(niveles.max()) if niveles.size else 0
    imagen = _componer(_tiles_plantilla(max(n, 1), t, marca_blanco), niveles).copy()
    # Cierra la grilla a la derecha y abajo
    imagen[:, -1] = np.minimum(imagen[:, -1], GRIS_GRILLA)
    imagen[-1, :] = np.minimum(imagen[-1, :], GRIS_GRILLA)
    return _a_png(imagen)
