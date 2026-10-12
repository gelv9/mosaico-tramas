"""Biblioteca del estilo clásico (design.md §4.0, checkpoint D).

Replica la referencia: punto, diagonal /, diagonal \, aspa (X), asterisco de 8 rayos y celda
llena, en ese orden de claro a oscuro. Las dos diagonales comparten tono a propósito.

Convención: coordenadas normalizadas con y hacia abajo. Una diagonal "/" va de la esquina
inferior izquierda (0, 1) a la superior derecha (1, 0), es decir, x + y = c. Una "\\" cumple
y − x = c. Las líneas van de borde a borde para que en zonas parejas el tramado sea continuo.
"""

from mosaico_tramas.simbolos.primitivas import Coordenada, Linea, Poligono, Punto, Simbolo


def _recortar(puntos: list[Coordenada]) -> Linea:
    """Toma los extremos de las intersecciones de una recta con el borde de la celda."""
    unicos = sorted({(round(x, 9), round(y, 9)) for x, y in puntos})
    return Linea(unicos[0], unicos[-1])


def diagonal(c: float) -> Linea:
    """Diagonal "/" (x + y = c) recortada a la celda."""
    bordes = [(x, c - x) for x in (0.0, 1.0)] + [(c - y, y) for y in (0.0, 1.0)]
    return _recortar([(x, y) for x, y in bordes if 0 <= x <= 1 and 0 <= y <= 1])


def antidiagonal(c: float) -> Linea:
    """Diagonal "\\" (y − x = c) recortada a la celda."""
    bordes = [(x, x + c) for x in (0.0, 1.0)] + [(y - c, y) for y in (0.0, 1.0)]
    return _recortar([(x, y) for x, y in bordes if 0 <= x <= 1 and 0 <= y <= 1])


def horizontal(y: float) -> Linea:
    return Linea((0.0, y), (1.0, y))


def vertical(x: float) -> Linea:
    return Linea((x, 0.0), (x, 1.0))


_LLENO = Poligono(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)))


def _s(id_: str, familia: str, nombre_en: str, *primitivas: Linea | Punto | Poligono) -> Simbolo:
    return Simbolo(id_, familia, nombre_en, tuple(primitivas))


BIBLIOTECA: tuple[Simbolo, ...] = (
    _s("punto", "punto", "dot", Punto(0.08)),
    _s("diag_asc", "diagonal_ascendente", "diagonal /", diagonal(1.0)),
    _s("diag_desc", "diagonal_descendente", "diagonal \\", antidiagonal(0.0)),
    _s("aspa", "aspa", "cross (X)", diagonal(1.0), antidiagonal(0.0)),
    # 4 rayas que se cruzan en el centro: fácil a mano pese a ser 4 trazos (RF2.6)
    _s(
        "asterisco",
        "asterisco",
        "asterisk",
        diagonal(1.0),
        antidiagonal(0.0),
        horizontal(0.5),
        vertical(0.5),
    ),
    _s("lleno", "lleno", "solid", _LLENO),
)

POR_ID: dict[str, Simbolo] = {s.id: s for s in BIBLIOTECA}
ID_PUNTO = "punto"
ID_LLENO = "lleno"
# Orden de claro a oscuro de la referencia (niveles 1…6)
ORDEN_CLASICO: tuple[str, ...] = ("punto", "diag_asc", "diag_desc", "aspa", "asterisco", "lleno")
