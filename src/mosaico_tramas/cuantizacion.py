"""Cuantización de la oscuridad en N niveles, 1…N (RF3, design.md §6).

No hay celdas vacías: el nivel 1 (punto) es lo más claro y el nivel N (celda llena) lo más
oscuro. Las funciones de cortes son genéricas: con k cortes producen k + 1 grupos, y el nivel
de una celda es la cantidad de cortes ≤ su oscuridad. `cuantizar` usa N − 1 cortes y suma 1.
Celdas con el mismo valor siempre caen en el mismo nivel.
"""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from mosaico_tramas.avisos import Aviso, CodigoAviso
from mosaico_tramas.config import MetodoCuantizacion, MosaicoConfig

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


@dataclass(frozen=True)
class Distribucion:
    """Cantidad y porcentaje de celdas por nivel 1…N (RF3.6); la posición i es el nivel i + 1."""

    conteos: tuple[int, ...]
    porcentajes: tuple[float, ...]

    @classmethod
    def de_niveles(cls, niveles: Niveles, n: int) -> "Distribucion":
        conteos = np.bincount(niveles.ravel(), minlength=n + 1)[1:]
        porcentajes = conteos / niveles.size * 100.0
        return cls(tuple(int(c) for c in conteos), tuple(float(p) for p in porcentajes))


@dataclass(frozen=True)
class ResultadoCuantizacion:
    niveles: Niveles
    cortes: Cortes
    distribucion: Distribucion
    avisos: tuple[Aviso, ...]


def cuantizar(d: Matriz, config: MosaicoConfig) -> ResultadoCuantizacion:
    """Aplica método → límite de oscuros → ruido → límite de nuevo (RF3.8) y reporta.

    Devuelve niveles 1…N: N − 1 cortes generan N grupos, y se suma 1 (no hay nivel vacío).
    """
    n = config.n_simbolos
    limite = config.max_oscuros_pct if config.limitar_oscuros else None

    match config.metodo:
        case MetodoCuantizacion.QUANTILES:
            cortes = cortes_quantiles(d, n - 1, limite)
        case MetodoCuantizacion.KMEANS:
            cortes = cortes_kmeans(d, n - 1)
        case MetodoCuantizacion.UNIFORM:
            cortes = cortes_uniformes(n - 1)

    niveles = (aplicar_cortes(d, cortes) + 1).astype(np.uint8)
    if limite is not None:
        niveles = limitar_oscuros(niveles, d, n, limite)
    if config.reduccion_ruido:
        niveles = reducir_ruido(niveles, config.umbral_ruido)
        if limite is not None:
            # El ruido puede volver a superar el límite (RF3.8)
            niveles = limitar_oscuros(niveles, d, n, limite)

    distribucion = Distribucion.de_niveles(niveles, n)
    return ResultadoCuantizacion(niveles, cortes, distribucion, _avisos(distribucion, n, limite))


def _avisos(distribucion: Distribucion, n: int, limite: float | None) -> tuple[Aviso, ...]:
    """Aviso por cada nivel con menos de la mitad de la cuota ideal (RF3.7)."""
    ideal = 100.0 / n
    avisos: list[Aviso] = []
    for nivel, pct in enumerate(distribucion.porcentajes, start=1):
        recortado_a_proposito = nivel == n and limite is not None and limite < ideal
        if pct >= 0.5 * ideal or recortado_a_proposito:
            continue
        avisos.append(
            Aviso(
                CodigoAviso.NIVEL_INFRAUTILIZADO,
                f"El nivel {nivel} quedó con {pct:.1f} % de las celdas "
                f"(lo esperable es ~{ideal:.1f} %): ese tono casi no va a aparecer.",
            )
        )
    return tuple(avisos)
