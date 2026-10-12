"""Elección del subconjunto de N símbolos (RF2.4, RF2.5, RF2.7; design.md §4.4).

Reglas: nivel 1 = punto, nivel N = lleno, cobertura estrictamente creciente, saltos de al
menos DELTA_MIN entre niveles 1…N (y DELTA_MIN_0 entre el vacío y el nivel 1), y una sola
familia visual por subconjunto. Entre los válidos se elige el que maximiza el salto mínimo;
el desempate prefiere menos trazos y después el orden de los ids (determinista).
"""

from functools import lru_cache

from mosaico_tramas.config import N_MAX, N_MIN, MosaicoConfig
from mosaico_tramas.errores import ConfigInvalidaError, ErrorBibliotecaSimbolos
from mosaico_tramas.simbolos.biblioteca import BIBLIOTECA, ID_LLENO, ID_PUNTO, SIN_TRIANGULO
from mosaico_tramas.simbolos.primitivas import Simbolo
from mosaico_tramas.simbolos.raster import cobertura

DELTA_MIN = 6.0  # pp entre niveles consecutivos 1…N
DELTA_MIN_0 = 1.5  # pp entre el vacío (0 %) y el nivel 1
_EPS = 1e-9

# Clave de comparación: (salto mínimo, −trazos totales, ids negados para preferir el menor)
type _Clave = tuple[float, int, tuple[str, ...]]


@lru_cache(maxsize=64)
def elegir_simbolos(n: int, biblioteca: tuple[Simbolo, ...] = BIBLIOTECA) -> tuple[Simbolo, ...]:
    """Devuelve los N símbolos ordenados de claro a oscuro."""
    if not N_MIN <= n <= N_MAX:
        raise ConfigInvalidaError(
            f"La cantidad de símbolos debe ser un entero entre {N_MIN} y {N_MAX} "
            f"(valor recibido: {n!r})."
        )
    por_id = {s.id: s for s in biblioteca}
    punto, lleno = por_id.get(ID_PUNTO), por_id.get(ID_LLENO)
    if punto is None or lleno is None:
        raise ErrorBibliotecaSimbolos("La biblioteca debe incluir los símbolos 'punto' y 'lleno'.")

    cob_punto, cob_lleno = cobertura(punto), cobertura(lleno)
    if cob_punto < DELTA_MIN_0 - _EPS:
        raise ErrorBibliotecaSimbolos(
            f"El punto cubre {cob_punto:.2f} %, menos que el salto mínimo de {DELTA_MIN_0} pp."
        )

    candidatos = sorted(
        (s for s in biblioteca if s.id not in (ID_PUNTO, ID_LLENO)),
        key=lambda s: (cobertura(s), s.id),
    )
    coberturas = [cobertura(s) for s in candidatos]
    k = n - 2
    mejor: tuple[_Clave, tuple[int, ...]] | None = None

    def buscar(
        desde: int, elegidos: list[int], familias: set[str], ultima: float, salto_min: float
    ) -> None:
        nonlocal mejor
        # Poda: el salto mínimo solo puede empeorar al agregar niveles
        if mejor is not None and salto_min < mejor[0][0] - _EPS:
            return
        if len(elegidos) == k:
            salto_final = cob_lleno - ultima
            if salto_final < DELTA_MIN - _EPS:
                return
            clave = _clave(min(salto_min, salto_final), elegidos, candidatos)
            if mejor is None or _supera(clave, mejor[0]):
                mejor = (clave, tuple(elegidos))
            return
        faltan = k - len(elegidos)
        for i in range(desde, len(candidatos) - faltan + 1):
            simbolo = candidatos[i]
            salto = coberturas[i] - ultima
            if salto < DELTA_MIN - _EPS or simbolo.familia in familias:
                continue
            # Si ya no entran los niveles restantes antes del lleno, cortar
            if coberturas[i] + DELTA_MIN * faltan > cob_lleno + _EPS:
                break
            elegidos.append(i)
            familias.add(simbolo.familia)
            buscar(i + 1, elegidos, familias, coberturas[i], min(salto_min, salto))
            familias.discard(simbolo.familia)
            elegidos.pop()

    buscar(0, [], {punto.familia, lleno.familia}, cob_punto, float("inf"))

    if mejor is None:
        raise ErrorBibliotecaSimbolos(
            f"La biblioteca no permite armar {n} símbolos con saltos de al menos {DELTA_MIN} pp "
            "y familias distintas."
        )
    return (punto, *(candidatos[i] for i in mejor[1]), lleno)


def _clave(salto_min: float, elegidos: list[int], candidatos: list[Simbolo]) -> _Clave:
    trazos = sum(candidatos[i].trazos for i in elegidos)
    ids = tuple(candidatos[i].id for i in elegidos)
    return (salto_min, -trazos, ids)


def _supera(nueva: _Clave, actual: _Clave) -> bool:
    """True si la nueva clave es mejor: mayor salto, menos trazos, ids menores."""
    if abs(nueva[0] - actual[0]) > _EPS:
        return nueva[0] > actual[0]
    if nueva[1] != actual[1]:
        return nueva[1] > actual[1]
    return nueva[2] < actual[2]


def simbolos_para(config: MosaicoConfig) -> tuple[Simbolo, ...]:
    """Símbolos de la config: con o sin triángulo según `usar_triangulo`."""
    biblioteca = BIBLIOTECA if config.usar_triangulo else SIN_TRIANGULO
    return elegir_simbolos(config.n_simbolos, biblioteca)
