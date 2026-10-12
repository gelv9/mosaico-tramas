"""Catálogo de símbolos candidatos (design.md §4.2).

Solo símbolos fáciles a mano (checkpoint A): como máximo 3 trazos y al menos 2 mm entre rayas
paralelas en una celda de 4 mm. Los únicos rellenos son la celda llena y el triángulo de media
celda (una diagonal y se rellena una mitad).

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


_TRIANGULO = Poligono(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0)))  # ◣ mitad inferior izquierda
_LLENO = Poligono(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)))


def _s(id_: str, familia: str, nombre_en: str, *primitivas: Linea | Punto | Poligono) -> Simbolo:
    return Simbolo(id_, familia, nombre_en, tuple(primitivas))


BIBLIOTECA: tuple[Simbolo, ...] = (
    _s("punto", "punto", "center dot", Punto(0.08)),
    _s("horiz1", "horizontal", "horizontal line", horizontal(0.5)),
    _s("vert1", "vertical", "vertical line", vertical(0.5)),
    _s("diag1", "diagonal", "diagonal line", diagonal(1.0)),
    _s("cruz", "cruz", "plus", horizontal(0.5), vertical(0.5)),
    # Dos horizontales a ¼ y ¾: 2 mm entre sí y contra la celda vecina en una celda de 4 mm
    _s("horiz2", "horizontal", "two horizontal lines", horizontal(0.25), horizontal(0.75)),
    _s("aspa1", "aspa", "cross", diagonal(1.0), antidiagonal(0.0)),
    _s("estrella", "estrella", "star", diagonal(1.0), antidiagonal(0.0), horizontal(0.5)),
    _s("triangulo", "triangulo", "half triangle", _TRIANGULO),
    _s("lleno", "lleno", "solid", _LLENO),
)

POR_ID: dict[str, Simbolo] = {s.id: s for s in BIBLIOTECA}
ID_PUNTO = "punto"
ID_LLENO = "lleno"
