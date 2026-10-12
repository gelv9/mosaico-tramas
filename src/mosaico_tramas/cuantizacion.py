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


def cortes_uniformes(n: int) -> Cortes:
    """Bins uniformes, como el prototipo (solo para comparar): c_k = k/(N+1)."""
    return np.arange(1, n + 1, dtype=np.float64) / (n + 1)


def cortes_kmeans(d: Matriz, n: int, max_iter: int = 100, tolerancia: float = 1e-6) -> Cortes:
    """K-means 1D (k = N + 1) sobre el histograma ponderado (design.md §6.2).

    Se inicializa con los cuantiles, así que es determinista sin semilla. Un cluster vacío
    se re-siembra en el bin de mayor error cuadrático (desempate: índice más bajo).
    """
    k = n + 1
    pesos = _histograma(d).astype(np.float64)
    centros_bin = (_BORDES[:-1] + _BORDES[1:]) / 2
    ocupados = pesos > 0

    # Inicialización: media ponderada de cada tramo de cuantiles
    limites = np.concatenate(([0.0], cortes_quantiles(d, n), [1.0 + 1e-9]))
    centros = np.empty(k)
    for j in range(k):
        en_tramo = (centros_bin >= limites[j]) & (centros_bin < limites[j + 1])
        masa = pesos[en_tramo].sum()
        centros[j] = (
            (pesos[en_tramo] * centros_bin[en_tramo]).sum() / masa
            if masa > 0
            else (limites[j] + min(limites[j + 1], 1.0)) / 2
        )

    for _ in range(max_iter):
        centros = np.sort(centros)
        fronteras = (centros[:-1] + centros[1:]) / 2
        asignacion = np.searchsorted(fronteras, centros_bin, side="right")
        masas = np.bincount(asignacion, weights=pesos, minlength=k)
        sumas = np.bincount(asignacion, weights=pesos * centros_bin, minlength=k)
        nuevos = np.where(masas > 0, sumas / np.where(masas > 0, masas, 1), centros)
        for j in np.flatnonzero(masas == 0):
            # Re-siembra en el bin ocupado con mayor error que no sea ya un centro
            error = pesos * (centros_bin - nuevos[asignacion]) ** 2
            error[~ocupados | np.isin(centros_bin, nuevos)] = -1.0
            if error.max() > 0:
                nuevos[j] = centros_bin[int(np.argmax(error))]
        convergio = np.abs(np.sort(nuevos) - centros).max() < tolerancia
        centros = nuevos
        if convergio:
            break

    centros = np.sort(centros)
    cortes = (centros[:-1] + centros[1:]) / 2
    # Garantiza cortes estrictamente crecientes aunque haya centros repetidos
    for i in range(1, len(cortes)):
        if cortes[i] <= cortes[i - 1]:
            cortes[i] = np.nextafter(cortes[i - 1], np.inf)
    return cortes


def limitar_oscuros(niveles: Niveles, d: Matriz, n: int, max_pct: float) -> Niveles:
    """Deja como máximo max_pct % de celdas en el nivel N; el exceso pasa a N−1 (RF3.5).

    Se conservan las más oscuras; a igual oscuridad, las primeras en orden de lectura.
    """
    maximo = int(np.floor(max_pct / 100.0 * niveles.size))
    plano = niveles.ravel()
    indices = np.flatnonzero(plano == n)
    if len(indices) <= maximo:
        return niveles
    orden = np.lexsort((indices, -d.ravel()[indices]))  # oscuridad desc, índice asc
    resultado = plano.copy()
    resultado[indices[orden[maximo:]]] = n - 1
    return resultado.reshape(niveles.shape)


def reducir_ruido(niveles: Niveles, umbral: int, max_pasadas: int = 3) -> Niveles:
    """Reasigna componentes (vecindad de 8) de menos de `umbral` celdas (RF3.4, design §6.5).

    El nuevo nivel es la moda de las celdas vecinas; empate → el más cercano al original;
    empate → el menor. Los cambios de cada pasada se aplican juntos (resultado determinista).
    """
    from scipy import ndimage
    from skimage.measure import label

    estructura = np.ones((3, 3), dtype=bool)
    actual = niveles.copy()
    alto, ancho = actual.shape
    for _ in range(max_pasadas):
        cambios: list[tuple[npt.NDArray[np.bool_], tuple[slice, slice], int]] = []
        for v in np.unique(actual):
            etiquetas = label(actual == v, connectivity=2)
            tamanos = np.bincount(etiquetas.ravel())
            for etiqueta, caja in enumerate(ndimage.find_objects(etiquetas), start=1):
                if caja is None or tamanos[etiqueta] >= umbral:
                    continue
                # Caja ampliada en 1 celda para ver las vecinas
                filas = slice(max(caja[0].start - 1, 0), min(caja[0].stop + 1, alto))
                cols = slice(max(caja[1].start - 1, 0), min(caja[1].stop + 1, ancho))
                componente = etiquetas[filas, cols] == etiqueta
                vecinas = ndimage.binary_dilation(componente, estructura) & ~componente
                valores = actual[filas, cols][vecinas]
                if valores.size == 0:
                    continue
                conteos = np.bincount(valores, minlength=int(actual.max()) + 1)
                candidatos = np.flatnonzero(conteos == conteos.max())
                nuevo = int(min(candidatos, key=lambda c: (abs(int(c) - int(v)), int(c))))
                cambios.append((componente, (filas, cols), nuevo))
        if not cambios:
            break
        siguiente = actual.copy()
        for componente, (filas, cols), nuevo in cambios:
            siguiente[filas, cols][componente] = nuevo
        actual = siguiente
    return actual
