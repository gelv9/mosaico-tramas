"""Símbolos del mosaico: orden fijo del estilo clásico (RF2.4, RF2.7; design.md §4.0).

Historia: hasta el checkpoint D había una selección automática por backtracking (saltos de
cobertura de al menos 6 pp y familias distintas). La referencia del usuario la reemplazó por
un set fijo en el que las dos diagonales comparten tono a propósito.
"""

from functools import lru_cache

from mosaico_tramas.config import MosaicoConfig
from mosaico_tramas.errores import ErrorBibliotecaSimbolos
from mosaico_tramas.simbolos.biblioteca import BIBLIOTECA, ORDEN_CLASICO
from mosaico_tramas.simbolos.primitivas import Simbolo

DELTA_MIN_0 = 1.5  # pp mínimos entre el vacío (0 %) y el nivel 1


@lru_cache(maxsize=8)
def elegir_simbolos(biblioteca: tuple[Simbolo, ...] = BIBLIOTECA) -> tuple[Simbolo, ...]:
    """Los 6 símbolos del estilo clásico, de claro a oscuro."""
    por_id = {s.id: s for s in biblioteca}
    faltantes = [i for i in ORDEN_CLASICO if i not in por_id]
    if faltantes:
        raise ErrorBibliotecaSimbolos(
            "A la biblioteca le faltan símbolos del estilo clásico: " + ", ".join(faltantes) + "."
        )
    return tuple(por_id[i] for i in ORDEN_CLASICO)


def simbolos_para(config: MosaicoConfig) -> tuple[Simbolo, ...]:
    """Símbolos de una config (hoy, siempre el set clásico)."""
    return elegir_simbolos()
