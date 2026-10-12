"""Avisos no bloqueantes que el pipeline devuelve junto al resultado."""

from dataclasses import dataclass
from enum import StrEnum


class CodigoAviso(StrEnum):
    """Tipos de aviso, para que la UI o una API puedan filtrarlos."""

    LEYENDA_MOVIDA = "leyenda_movida"
    NIVEL_INFRAUTILIZADO = "nivel_infrautilizado"
    POCO_RANGO_TONAL = "poco_rango_tonal"


@dataclass(frozen=True)
class Aviso:
    """Aviso con código estable y mensaje en español para el usuario."""

    codigo: CodigoAviso
    mensaje: str
