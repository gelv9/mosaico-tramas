"""Preprocesamiento: de los bytes subidos a una grilla de oscuridad (RP1–RP6, design.md §5)."""

import io

import cv2
import numpy as np
import numpy.typing as npt
from PIL import Image, ImageOps, UnidentifiedImageError

from mosaico_tramas.avisos import Aviso, CodigoAviso
from mosaico_tramas.config import Recorte
from mosaico_tramas.errores import ImagenInvalidaError

FORMATOS_VALIDOS = {"JPEG", "PNG"}
# Factor del sigma del suavizado respecto del tamaño de celda en píxeles de origen (RP2)
SUAVIZADO_REL = 0.35
# Rango mínimo p_alto − p_bajo para estirar el contraste (RP6)
RANGO_MINIMO = 0.02

type Matriz = npt.NDArray[np.float32]


def cargar_luminancia(datos: bytes, max_mb: float) -> Matriz:
    """Decodifica JPG o PNG y devuelve la luminancia en [0, 1] (1 = blanco)."""
    tamano_mb = len(datos) / (1024 * 1024)
    if tamano_mb > max_mb:
        raise ImagenInvalidaError(
            f"La imagen pesa {tamano_mb:.1f} MB y el máximo es {max_mb:g} MB."
        )
    try:
        imagen = Image.open(io.BytesIO(datos))
        imagen.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ImagenInvalidaError("El archivo no es una imagen JPG o PNG válida.") from None
    if imagen.format not in FORMATOS_VALIDOS:
        raise ImagenInvalidaError(f"Formato no soportado ({imagen.format}). Subí un JPG o PNG.")

    imagen = ImageOps.exif_transpose(imagen)
    if imagen.mode in ("RGBA", "LA", "PA") or "transparency" in imagen.info:
        # Lo transparente se compone sobre blanco (RP1)
        fondo = Image.new("RGBA", imagen.size, (255, 255, 255, 255))
        imagen = Image.alpha_composite(fondo, imagen.convert("RGBA"))
    gris = imagen.convert("L")  # luminancia ITU-R 601
    return np.asarray(gris, dtype=np.float32) / 255.0


def recortar_centro(lum: Matriz, proporcion: float) -> Matriz:
    """Recorta al centro para que alto/ancho quede igual a `proporcion`."""
    alto, ancho = lum.shape
    if alto / ancho > proporcion:
        nuevo_alto = max(1, round(ancho * proporcion))
        inicio = (alto - nuevo_alto) // 2
        return lum[inicio : inicio + nuevo_alto, :]
    nuevo_ancho = max(1, round(alto / proporcion))
    inicio = (ancho - nuevo_ancho) // 2
    return lum[:, inicio : inicio + nuevo_ancho]


def a_grilla(
    lum: Matriz,
    columnas: int,
    filas: int,
    recorte: Recorte,
    percentil_bajo: float = 2.0,
    percentil_alto: float = 98.0,
) -> tuple[Matriz, tuple[Aviso, ...]]:
    """Reduce la luminancia a filas × columnas y devuelve la oscuridad (1 = negro) y avisos."""
    if recorte is Recorte.CENTER:
        lum = recortar_centro(lum, filas / columnas)

    # Suavizado proporcional al tamaño de la celda en la imagen original (RP2)
    sigma = SUAVIZADO_REL * lum.shape[1] / columnas
    if sigma >= 0.5:
        lum = cv2.GaussianBlur(lum, (0, 0), sigmaX=sigma, sigmaY=sigma)

    # Reducción por promedio de área (RP3)
    grilla = cv2.resize(lum, (columnas, filas), interpolation=cv2.INTER_AREA).astype(np.float32)

    # Estiramiento de contraste entre percentiles (RP4) o aviso si no hay rango (RP6)
    p_bajo, p_alto = (float(v) for v in np.percentile(grilla, [percentil_bajo, percentil_alto]))
    avisos: tuple[Aviso, ...] = ()
    if p_alto - p_bajo < RANGO_MINIMO:
        avisos = (
            Aviso(
                CodigoAviso.POCO_RANGO_TONAL,
                "La imagen casi no tiene rango tonal (es muy pareja): el mosaico va a salir "
                "plano. Probá con una foto con más contraste.",
            ),
        )
    else:
        grilla = np.clip((grilla - p_bajo) / (p_alto - p_bajo), 0.0, 1.0)

    oscuridad = (1.0 - grilla).astype(np.float32)
    return oscuridad, avisos
