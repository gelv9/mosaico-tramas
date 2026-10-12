"""Cuantización de la oscuridad en N + 1 niveles (RF3, design.md §6).

Nivel 0 = vacío (lo más claro), nivel N = celda llena (lo más oscuro). Todos los métodos
producen cortes c_1 < … < c_N sobre la oscuridad; el nivel de una celda es la cantidad de
cortes ≤ su oscuridad. Así, celdas con el mismo valor siempre caen en el mismo nivel.
"""

import numpy as np
import numpy.typing as npt

BINS = 4096

type Matriz = npt.NDArray[np.float32]
type Niveles = npt.NDArray[np.uint8]
type Cortes = npt.NDArray[np.float64]

_BORDES = np.linspace(0.0, 1.0, BINS + 1)


def _histograma(d: Matriz) -> npt.NDArray[np.int64]:
    conteos, _ = np.histogram(d, bins=BINS, range=(0.0, 1.0))
    return conteos


def cuotas_objetivo(n: int, max_oscuros_pct: float | None = None) -> npt.NDArray[np.float64]:
    """Fracción objetivo de celdas por nivel 0…N (suma 1).

    Sin límite, cada nivel recibe 1/(N+1). Con límite, el nivel N recibe
    min(1/(N+1), L) y lo que sobra se reparte en partes iguales entre los niveles 0…N−1.
    """
    ideal = 1.0 / (n + 1)
    cuota_n = ideal if max_oscuros_pct is None else min(ideal, max_oscuros_pct / 100.0)
    cuotas = np.full(n + 1, (1.0 - cuota_n) / n)
    cuotas[n] = cuota_n
    return cuotas


def cortes_quantiles(d: Matriz, n: int, max_oscuros_pct: float | None = None) -> Cortes:
    """Cortes por cuantiles sobre un histograma de 4096 bins (RF3.1, design.md §6.1)."""
    acumulado = np.cumsum(_histograma(d))  # acumulado[i] = celdas en los bins 0…i
    objetivos = np.cumsum(cuotas_objetivo(n, max_oscuros_pct))[:-1] * d.size
    indices: list[int] = []
    anterior = -1
    for k, objetivo in enumerate(objetivos):
        # El corte k cae después del bin i (valor _BORDES[i + 1]); tiene que dejar lugar
        # para los cortes que faltan y ser estrictamente mayor que el anterior.
        desde = anterior + 1
        hasta = BINS - 1 - (n - 1 - k)
        tramo = np.abs(acumulado[desde:hasta] - objetivo)
        anterior = desde + int(np.argmin(tramo))  # empate → el borde más bajo
        indices.append(anterior)
    return _BORDES[np.asarray(indices) + 1]


def aplicar_cortes(d: Matriz, cortes: Cortes) -> Niveles:
    """Nivel de cada celda = cantidad de cortes menores o iguales a su oscuridad."""
    return np.searchsorted(cortes, d, side="right").astype(np.uint8)
