"""Tests de la biblioteca de símbolos (T5)."""

import pytest

from mosaico_tramas.simbolos.biblioteca import BIBLIOTECA, ID_LLENO, ID_PUNTO, POR_ID
from mosaico_tramas.simbolos.primitivas import Linea, Poligono, Punto
from mosaico_tramas.simbolos.raster import cobertura

# Coberturas de design.md §4.2 (%)
COBERTURAS_DISENO = {
    "punto": 2.0,
    "diag_asc": 17.0,
    "diag_desc": 17.0,
    "aspa": 32.4,
    "asterisco": 51.6,
    "lleno": 100.0,
}


def test_seis_simbolos_con_ids_unicos():
    assert len(BIBLIOTECA) == 6
    assert len(POR_ID) == len(BIBLIOTECA)


def test_extremos_fijos_existen():
    assert ID_PUNTO in POR_ID
    assert ID_LLENO in POR_ID
    assert cobertura(POR_ID[ID_LLENO]) == pytest.approx(100.0, abs=0.01)


@pytest.mark.parametrize("simbolo", BIBLIOTECA, ids=lambda s: s.id)
def test_dibujable_a_mano(simbolo):
    # RF2.6: como máximo 3 trazos, o 4 si todos se cruzan en el centro (asterisco)
    assert 1 <= simbolo.trazos <= 4
    if simbolo.trazos == 4:
        for linea in simbolo.primitivas:
            assert isinstance(linea, Linea)
            medio = ((linea.p0[0] + linea.p1[0]) / 2, (linea.p0[1] + linea.p1[1]) / 2)
            assert medio == pytest.approx((0.5, 0.5))
    for primitiva in simbolo.primitivas:
        assert isinstance(primitiva, Linea | Punto | Poligono)


@pytest.mark.parametrize("simbolo", BIBLIOTECA, ids=lambda s: s.id)
def test_coordenadas_dentro_de_la_celda(simbolo):
    for primitiva in simbolo.primitivas:
        match primitiva:
            case Linea(p0, p1):
                puntos = [p0, p1]
            case Poligono(vertices):
                puntos = list(vertices)
            case Punto(radio):
                assert 0 < radio < 0.5
                puntos = []
        for x, y in puntos:
            assert 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0


@pytest.mark.parametrize("simbolo", BIBLIOTECA, ids=lambda s: s.id)
def test_cobertura_coincide_con_el_diseno(simbolo):
    assert cobertura(simbolo) == pytest.approx(COBERTURAS_DISENO[simbolo.id], abs=1.0)


def test_unico_relleno_es_la_celda_llena():
    # RF2.6a (estilo clásico): solo rayas, el punto y la celda llena
    for simbolo in BIBLIOTECA:
        if any(isinstance(p, Poligono) for p in simbolo.primitivas):
            assert simbolo.id == ID_LLENO, simbolo.id


def test_cada_simbolo_tiene_familia_y_nombre_en_ingles():
    for simbolo in BIBLIOTECA:
        assert simbolo.familia
        assert simbolo.nombre_en.isascii()


# --- Continuidad del tramado entre celdas vecinas ---

_VECINOS = {(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - {(0, 0)}


def _lineas(simbolo):
    return [p for p in simbolo.primitivas if isinstance(p, Linea)]


def _solo_lineas(simbolo) -> bool:
    return bool(simbolo.primitivas) and all(isinstance(p, Linea) for p in simbolo.primitivas)


def _direccion(linea: Linea) -> tuple[float, float]:
    dx, dy = linea.p1[0] - linea.p0[0], linea.p1[1] - linea.p0[1]
    norma = (dx * dx + dy * dy) ** 0.5
    dx, dy = dx / norma, dy / norma
    # Normaliza el sentido para comparar direcciones
    if dx < -1e-9 or (abs(dx) < 1e-9 and dy < 0):
        dx, dy = -dx, -dy
    return round(dx, 6), round(dy, 6)


@pytest.mark.parametrize("simbolo", [s for s in BIBLIOTECA if _solo_lineas(s)], ids=lambda s: s.id)
def test_tramado_continuo_entre_celdas(simbolo):
    """Cada extremo de una raya tiene su continuación en la celda vecina (misma dirección)."""
    lineas = _lineas(simbolo)
    extremos = [
        (round(x, 6), round(y, 6), _direccion(lin)) for lin in lineas for x, y in (lin.p0, lin.p1)
    ]
    conjunto = set(extremos)
    for x, y, d in extremos:
        assert any((round(x + dx, 6), round(y + dy, 6), d) in conjunto for dx, dy in _VECINOS), (
            f"{simbolo.id}: la raya que termina en ({x}, {y}) no sigue en la celda vecina"
        )


def _desplazamiento(linea: Linea) -> tuple[tuple[float, float], float]:
    """Dirección y posición de la raya, con período 1 al trasladar la celda."""
    d = _direccion(linea)
    x, y = linea.p0
    if d == (1.0, 0.0):
        return d, y
    if d in ((0.0, 1.0), (0.0, -1.0)):
        return d, x
    return d, (x + y) if d[1] < 0 else (y - x)


@pytest.mark.parametrize("simbolo", [s for s in BIBLIOTECA if _solo_lineas(s)], ids=lambda s: s.id)
def test_espaciado_parejo_entre_celdas(simbolo):
    """Las rayas paralelas quedan equiespaciadas también al repetir la celda."""
    por_direccion: dict[tuple[float, float], set[float]] = {}
    for linea in _lineas(simbolo):
        d, pos = _desplazamiento(linea)
        por_direccion.setdefault(d, set()).add(round(pos % 1.0, 6) % 1.0)
    for d, posiciones in por_direccion.items():
        orden = sorted(posiciones)
        saltos = [b - a for a, b in zip(orden, orden[1:], strict=False)] + [
            1 - orden[-1] + orden[0]
        ]
        assert max(saltos) - min(saltos) < 1e-4, f"{simbolo.id} {d}: espaciado {saltos}"


# --- Regla física de dibujabilidad (RF2.6) ---

CELDA_MIN_MM = 4.0
SEPARACION_MIN_MM = 2.0


@pytest.mark.parametrize("simbolo", BIBLIOTECA, ids=lambda s: s.id)
def test_rayas_paralelas_separadas_al_menos_2_mm_en_celda_de_4_mm(simbolo):
    """Entre rayas paralelas (también contra la celda vecina) quedan al menos 2 mm."""
    por_direccion: dict[tuple[float, float], set[float]] = {}
    for linea in _lineas(simbolo):
        d, pos = _desplazamiento(linea)
        por_direccion.setdefault(d, set()).add(round(pos % 1.0, 6) % 1.0)
    for d, posiciones in por_direccion.items():
        orden = sorted(posiciones)
        saltos = [b - a for a, b in zip(orden, orden[1:], strict=False)] + [
            1 - orden[-1] + orden[0]
        ]
        # En diagonales la posición se mide en x ± y: la distancia perpendicular es salto / √2
        factor = 1.0 if d in ((1.0, 0.0), (0.0, 1.0), (0.0, -1.0)) else 2**-0.5
        separacion_mm = min(saltos) * factor * CELDA_MIN_MM
        assert separacion_mm >= SEPARACION_MIN_MM - 1e-6, f"{simbolo.id}: {separacion_mm:.2f} mm"
