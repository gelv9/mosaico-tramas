"""Catálogo de símbolos candidatos (design.md §4.2).

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


def bloque(lado: float) -> Poligono:
    """Cuadrado relleno centrado."""
    a = (1 - lado) / 2
    b = 1 - a
    return Poligono(((a, a), (b, a), (b, b), (a, b)))


_TERCIOS = (1 / 3, 2 / 3)
_CUARTOS = (0.25, 0.5, 0.75)
_TRIANGULO = Poligono(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0)))  # ◣ mitad inferior izquierda


def _s(id_: str, familia: str, nombre_en: str, *primitivas: Linea | Punto | Poligono) -> Simbolo:
    return Simbolo(id_, familia, nombre_en, tuple(primitivas))


BIBLIOTECA: tuple[Simbolo, ...] = (
    _s("punto", "punto", "center dot", Punto(0.08)),
    _s("diag1", "diagonal", "one diagonal", diagonal(1.0)),
    _s("diag2", "diagonal", "two diagonals", diagonal(2 / 3), diagonal(4 / 3)),
    _s("diag3", "diagonal", "three diagonals", diagonal(0.5), diagonal(1.0), diagonal(1.5)),
    _s("horiz1", "horizontal", "one horizontal", horizontal(0.5)),
    _s("horiz2", "horizontal", "two horizontals", *(horizontal(y) for y in _TERCIOS)),
    _s("horiz3", "horizontal", "three horizontals", *(horizontal(y) for y in _CUARTOS)),
    _s("vert1", "vertical", "one vertical", vertical(0.5)),
    _s("cruz", "cruz", "plus", horizontal(0.5), vertical(0.5)),
    _s("aspa1", "aspa", "cross", diagonal(1.0), antidiagonal(0.0)),
    _s(
        "aspa2",
        "aspa",
        "double cross",
        diagonal(2 / 3),
        diagonal(4 / 3),
        antidiagonal(1 / 3),
        antidiagonal(-1 / 3),
    ),
    _s(
        "aspa3",
        "aspa",
        "dense cross-hatch",
        *(diagonal(c) for c in (0.5, 1.0, 1.5)),
        *(antidiagonal(c) for c in (0.5, 0.0, -0.5)),
    ),
    _s(
        "reja1",
        "reja",
        "grid",
        *(horizontal(y) for y in _TERCIOS),
        *(vertical(x) for x in _TERCIOS),
    ),
    _s(
        "reja2",
        "reja",
        "dense grid",
        *(horizontal(y) for y in _CUARTOS),
        *(vertical(x) for x in _CUARTOS),
    ),
    _s(
        "asterisco",
        "asterisco",
        "asterisk",
        horizontal(0.5),
        vertical(0.5),
        diagonal(1.0),
        antidiagonal(0.0),
    ),
    _s("bloque50", "bloque", "small square", bloque(0.5)),
    _s("bloque60", "bloque", "square", bloque(0.6)),
    _s("triangulo", "triangulo", "half triangle", _TRIANGULO),
    # Triángulo + 2 rayas paralelas a la hipotenusa, solo en la mitad libre (y < x)
    _s(
        "tri_rayas",
        "triangulo_rayado",
        "half triangle with lines",
        _TRIANGULO,
        antidiagonal(-1 / 3),
        antidiagonal(-2 / 3),
    ),
    _s(
        "mitad_rayas",
        "mitad",
        "bottom half with lines",
        Poligono(((0.0, 0.5), (1.0, 0.5), (1.0, 1.0), (0.0, 1.0))),
        horizontal(1 / 6),
        horizontal(2 / 6),
    ),
    _s(
        "tres_cuartos",
        "tres_cuartos",
        "three quarters",
        Poligono(((0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (1.0, 0.5), (1.0, 1.0), (0.0, 1.0))),
    ),
    _s(
        "esquina",
        "esquina",
        "solid with white corner",
        Poligono(((0.0, 0.0), (0.5, 0.0), (1.0, 0.5), (1.0, 1.0), (0.0, 1.0))),
    ),
    _s("lleno", "lleno", "solid", Poligono(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)))),
)

POR_ID: dict[str, Simbolo] = {s.id: s for s in BIBLIOTECA}
ID_PUNTO = "punto"
ID_LLENO = "lleno"
