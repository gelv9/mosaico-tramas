"""Rasterizado de símbolos con OpenCV y medición de la cobertura de tinta (RF2.3)."""

from functools import lru_cache

import cv2
import numpy as np
import numpy.typing as npt

from mosaico_tramas.simbolos.primitivas import TRAZO_REL, Linea, Poligono, Punto, Simbolo

# Resolución usada para medir la cobertura (px por lado de la celda)
PX_COBERTURA = 1000
# Bits de precisión subpíxel para cv2.fillPoly / cv2.circle
_SHIFT = 4
_ESCALA_SHIFT = 1 << _SHIFT


def _a_enteros(puntos: npt.NDArray[np.float64], px: int) -> npt.NDArray[np.int32]:
    """Pasa coordenadas normalizadas a píxeles en punto fijo (con _SHIFT bits decimales)."""
    return np.round(puntos * px * _ESCALA_SHIFT).astype(np.int32)


def _poligono_de_linea(linea: Linea, trazo_rel: float) -> npt.NDArray[np.float64]:
    """Rectángulo que ocupa una línea con extremos planos."""
    p0 = np.asarray(linea.p0, dtype=np.float64)
    p1 = np.asarray(linea.p1, dtype=np.float64)
    direccion = p1 - p0
    normal = np.array([-direccion[1], direccion[0]]) / np.linalg.norm(direccion)
    desplazamiento = normal * trazo_rel / 2
    return np.array(
        [p0 + desplazamiento, p1 + desplazamiento, p1 - desplazamiento, p0 - desplazamiento]
    )


def rasterizar(simbolo: Simbolo, px: int, trazo_rel: float = TRAZO_REL) -> npt.NDArray[np.float32]:
    """Dibuja el símbolo en una celda de px × px; devuelve tinta en [0, 1] (1 = negro)."""
    lienzo = np.zeros((px, px), dtype=np.uint8)
    for primitiva in simbolo.primitivas:
        match primitiva:
            case Linea():
                poligono = _poligono_de_linea(primitiva, trazo_rel)
                cv2.fillPoly(lienzo, [_a_enteros(poligono, px)], 255, cv2.LINE_AA, _SHIFT)
            case Poligono():
                vertices = np.asarray(primitiva.vertices, dtype=np.float64)
                cv2.fillPoly(lienzo, [_a_enteros(vertices, px)], 255, cv2.LINE_AA, _SHIFT)
            case Punto():
                # El centro de la celda en coordenadas continuas es px/2 (borde a borde)
                centro = round(px / 2 * _ESCALA_SHIFT)
                radio = round(primitiva.radio * px * _ESCALA_SHIFT)
                cv2.circle(lienzo, (centro, centro), radio, 255, -1, cv2.LINE_AA, _SHIFT)
    return lienzo.astype(np.float32) / 255.0


@lru_cache(maxsize=256)
def cobertura(simbolo: Simbolo) -> float:
    """Porcentaje del área de la celda que queda negro, medido a PX_COBERTURA px."""
    return float(rasterizar(simbolo, PX_COBERTURA).mean() * 100.0)
