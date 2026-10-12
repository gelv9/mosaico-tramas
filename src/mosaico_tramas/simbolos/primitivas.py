"""Primitivas vectoriales de los símbolos, en coordenadas normalizadas de la celda.

El origen (0, 0) es la esquina superior izquierda y el eje y crece hacia abajo; (1, 1) es la
esquina inferior derecha. El renderer de PDF invierte el eje y al dibujar.
"""

from dataclasses import dataclass

# Grosor del trazo relativo al lado de la celda: 0,35 mm en una celda de 5 mm (referencia RF2.3)
TRAZO_REL = 0.07

type Coordenada = tuple[float, float]


@dataclass(frozen=True)
class Linea:
    """Segmento recto con extremos planos (butt), de grosor TRAZO_REL."""

    p0: Coordenada
    p1: Coordenada


@dataclass(frozen=True)
class Punto:
    """Círculo relleno centrado en la celda."""

    radio: float


@dataclass(frozen=True)
class Poligono:
    """Polígono relleno."""

    vertices: tuple[Coordenada, ...]


type Primitiva = Linea | Punto | Poligono


@dataclass(frozen=True)
class Simbolo:
    """Símbolo de la biblioteca. Cada primitiva cuenta como un trazo a mano."""

    id: str
    familia: str
    nombre_en: str
    primitivas: tuple[Primitiva, ...]

    @property
    def trazos(self) -> int:
        """Cantidad de trazos que hace falta dibujar a mano."""
        return len(self.primitivas)
