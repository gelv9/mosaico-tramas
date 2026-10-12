"""Geometría de las páginas: celda, grilla, leyenda y sugerencias (design.md §7).

Todo se calcula en puntos PDF con el origen abajo a la izquierda (convención de ReportLab).
"""

import math
from dataclasses import dataclass

from mosaico_tramas.avisos import Aviso, CodigoAviso
from mosaico_tramas.config import MosaicoConfig, Recorte, UbicacionLeyenda
from mosaico_tramas.errores import CeldaDemasiadoChicaError
from mosaico_tramas.papel import (
    PERSONALIZADO_MAX_MM,
    PERSONALIZADO_MIN_MM,
    REGISTRO_PAPELES,
    Orientacion,
    Papel,
    mm_a_pt,
    obtener_papel,
    resolver_orientacion,
)

# --- Bloque de leyenda (design.md §7.2) ---
ANCHO_ENTRADA_MM = 32
ALTO_ENTRADA_MM = 14
SEPARACION_LEYENDA_MM = 6
ALTO_INSTRUCCION_MM = 4.6
LADO_AMPLIADO_MM = 10

CELDA_MIN_MM = 4.0
_EPS = 1e-9

type Rect = tuple[float, float, float, float]  # (x0, y0, x1, y1) en pt, origen abajo


def entradas_por_fila(ancho_util_pt: float) -> int:
    """Cuántas entradas de leyenda entran a lo ancho (al menos una)."""
    return max(1, int(ancho_util_pt // mm_a_pt(ANCHO_ENTRADA_MM)))


def alto_leyenda(n: int, ancho_util_pt: float) -> float:
    """Alto total del bloque de leyenda en pt: separación + instrucción + filas de entradas."""
    filas = math.ceil(n / entradas_por_fila(ancho_util_pt))
    return mm_a_pt(SEPARACION_LEYENDA_MM + ALTO_INSTRUCCION_MM + filas * ALTO_ENTRADA_MM)


# --- Layout de una página (design.md §7.3) ---


@dataclass(frozen=True)
class Layout:
    """Geometría resuelta para un papel."""

    papel: Papel
    orientacion: Orientacion
    pagina_pt: tuple[float, float]
    margen_pt: float
    columnas: int
    filas: int
    celda_pt: float
    rect_grilla: Rect
    leyenda_en_plantilla: bool
    rect_leyenda: Rect | None  # solo si la leyenda va en la página de la plantilla
    avisos: tuple[Aviso, ...] = ()

    @property
    def celda_mm(self) -> float:
        return self.celda_pt / mm_a_pt(1)

    def area_util(self) -> Rect:
        ancho, alto = self.pagina_pt
        m = self.margen_pt
        return (m, m, ancho - m, alto - m)

    def bbox_contenido(self) -> Rect:
        """Rectángulo que envuelve todo lo dibujado en la plantilla (grilla y leyenda)."""
        if self.rect_leyenda is None:
            return self.rect_grilla
        g, ley = self.rect_grilla, self.rect_leyenda
        return (min(g[0], ley[0]), min(g[1], ley[1]), max(g[2], ley[2]), max(g[3], ley[3]))


def _filas(
    config: MosaicoConfig,
    ancho_img: int,
    alto_img: int,
    ancho_disp: float,
    alto_disp: float,
    filas_fijas: int | None,
) -> int:
    """FIT: según la imagen. CENTER: según el área disponible (la imagen se recorta)."""
    if filas_fijas is not None:
        return filas_fijas
    if config.recorte is Recorte.CENTER:
        return max(1, round(config.columnas * alto_disp / ancho_disp))
    return max(1, round(config.columnas * alto_img / ancho_img))


def _geometria_util(
    config: MosaicoConfig, ancho_img: int, alto_img: int, papel: Papel
) -> tuple[Orientacion, float, float, float, float, float]:
    """Orientación, página, margen y área útil (todo en pt)."""
    orientacion = resolver_orientacion(config.orientacion, ancho_img, alto_img)
    ancho, alto = papel.tamano_pt(orientacion)
    margen = mm_a_pt(config.margen_mm)
    return orientacion, ancho, alto, margen, ancho - 2 * margen, alto - 2 * margen


def calcular_layout(
    config: MosaicoConfig,
    ancho_img: int,
    alto_img: int,
    papel: Papel,
    filas_fijas: int | None = None,
) -> Layout:
    """Resuelve celda, filas y ubicación de la leyenda; error si la celda queda < 4 mm."""
    orientacion, ancho, alto, margen, uw, uh = _geometria_util(config, ancho_img, alto_img, papel)
    cols = config.columnas
    minimo = mm_a_pt(CELDA_MIN_MM)
    debajo = config.leyenda is UbicacionLeyenda.BELOW
    alto_ley = alto_leyenda(config.n_simbolos, uw)

    filas = _filas(config, ancho_img, alto_img, uw, uh - alto_ley if debajo else uh, filas_fijas)
    celda_completa = min(uw / cols, uh / filas)
    if celda_completa < minimo - _EPS:
        # RF4.6a / RF6.4: no se genera nada por debajo de 4 mm
        raise _error_celda_chica(
            config, ancho_img, alto_img, papel, orientacion, filas, celda_completa
        )

    avisos: tuple[Aviso, ...] = ()
    en_plantilla = False
    celda = celda_completa
    if debajo:
        celda_con_leyenda = min(uw / cols, (uh - alto_ley) / filas)
        if celda_con_leyenda >= minimo - _EPS:
            en_plantilla, celda = True, celda_con_leyenda
        else:
            avisos = (
                Aviso(
                    CodigoAviso.LEYENDA_MOVIDA,
                    "La leyenda no entra debajo sin achicar las celdas por debajo de "
                    f"{CELDA_MIN_MM:g} mm; se movió a una hoja aparte.",
                ),
            )
            if config.recorte is Recorte.CENTER and filas_fijas is None:
                # Sin la leyenda cambia la proporción del área: se recalculan las filas
                filas = _filas(config, ancho_img, alto_img, uw, uh, None)
                celda = min(uw / cols, uh / filas)

    # Área asignada a la grilla: todo el alto útil, menos la leyenda si va debajo (RF4.7)
    piso_area = margen + (alto_ley if en_plantilla else 0.0)
    techo_area = alto - margen
    ancho_grilla, alto_grilla = cols * celda, filas * celda
    x0 = margen + (uw - ancho_grilla) / 2
    y1 = techo_area - ((techo_area - piso_area) - alto_grilla) / 2
    rect_grilla = (x0, y1 - alto_grilla, x0 + ancho_grilla, y1)
    rect_leyenda = (margen, margen, ancho - margen, margen + alto_ley) if en_plantilla else None

    return Layout(
        papel=papel,
        orientacion=orientacion,
        pagina_pt=(ancho, alto),
        margen_pt=margen,
        columnas=cols,
        filas=filas,
        celda_pt=celda,
        rect_grilla=rect_grilla,
        leyenda_en_plantilla=en_plantilla,
        rect_leyenda=rect_leyenda,
        avisos=avisos,
    )


# --- Sugerencias ante una celda chica (design.md §7.5) ---


def _celda_completa(
    config: MosaicoConfig,
    ancho_img: int,
    alto_img: int,
    papel: Papel,
    filas_fijas: int | None = None,
) -> float:
    """Celda sin contar la leyenda: el criterio duro de los 4 mm."""
    _, _, _, _, uw, uh = _geometria_util(config, ancho_img, alto_img, papel)
    debajo = config.leyenda is UbicacionLeyenda.BELOW
    alto_ley = alto_leyenda(config.n_simbolos, uw)
    filas = _filas(config, ancho_img, alto_img, uw, uh - alto_ley if debajo else uh, filas_fijas)
    return min(uw / config.columnas, uh / filas)


def columnas_maximas(
    config: MosaicoConfig,
    ancho_img: int,
    alto_img: int,
    papeles: list[Papel],
) -> int | None:
    """Mayor cantidad de columnas (≥ 10, < las pedidas) que da ≥ 4 mm en todos los papeles."""
    minimo = mm_a_pt(CELDA_MIN_MM)
    for cols in range(config.columnas - 1, 9, -1):
        prueba = config.model_copy(update={"columnas": cols})
        if all(_celda_completa(prueba, ancho_img, alto_img, p) >= minimo - _EPS for p in papeles):
            return cols
    return None


def papel_minimo(config: MosaicoConfig, ancho_img: int, alto_img: int) -> str | None:
    """Papel del registro de menor área que admite las columnas pedidas."""
    minimo = mm_a_pt(CELDA_MIN_MM)
    por_area = sorted(REGISTRO_PAPELES.values(), key=lambda p: (p.ancho_mm * p.alto_mm, p.nombre))
    for papel in por_area:
        if _celda_completa(config, ancho_img, alto_img, papel) >= minimo - _EPS:
            return papel.nombre
    return None


def personalizado_minimo(
    config: MosaicoConfig, filas: int, ancho_util_pt: float
) -> tuple[int, int] | None:
    """Papel personalizado mínimo (mm) para las columnas y filas actuales, con la leyenda."""
    margen = config.margen_mm
    ancho = math.ceil(config.columnas * CELDA_MIN_MM + 2 * margen)
    alto_ley_mm = 0.0
    if config.leyenda is UbicacionLeyenda.BELOW:
        # La leyenda se mide con el ancho útil del papel sugerido (más angosto o más ancho)
        ancho_util_sugerido = mm_a_pt(ancho - 2 * margen)
        alto_ley_mm = alto_leyenda(config.n_simbolos, ancho_util_sugerido) / mm_a_pt(1)
    alto = math.ceil(filas * CELDA_MIN_MM + 2 * margen + alto_ley_mm)
    if max(ancho, alto) > PERSONALIZADO_MAX_MM or min(ancho, alto) < PERSONALIZADO_MIN_MM:
        return None
    return ancho, alto


_ORIENTACION_ES = {Orientacion.PORTRAIT: "vertical", Orientacion.LANDSCAPE: "horizontal"}


def _error_celda_chica(
    config: MosaicoConfig,
    ancho_img: int,
    alto_img: int,
    papel: Papel,
    orientacion: Orientacion,
    filas: int,
    celda_pt: float,
) -> CeldaDemasiadoChicaError:
    ancho_util = papel.tamano_pt(orientacion)[0] - 2 * mm_a_pt(config.margen_mm)
    cols_max = columnas_maximas(config, ancho_img, alto_img, [papel])
    sugerido = papel_minimo(config, ancho_img, alto_img)
    custom = personalizado_minimo(config, filas, ancho_util)
    return CeldaDemasiadoChicaError(
        mensaje_celda_chica(
            config.columnas, papel.nombre, orientacion, celda_pt, cols_max, sugerido, custom
        ),
        columnas_max=cols_max,
        papel_sugerido=sugerido,
        personalizado_mm=custom,
    )


def mensaje_celda_chica(
    cols: int,
    papel: str,
    orientacion: Orientacion,
    celda_pt: float,
    cols_max: int | None,
    sugerido: str | None,
    custom: tuple[int, int] | None,
) -> str:
    """Mensaje en español con la medida de la celda y las opciones disponibles."""
    celda_mm = f"{celda_pt / mm_a_pt(1):.1f}".replace(".", ",")
    opciones: list[str] = []
    if cols_max is not None:
        opciones.append(f"usar hasta {cols_max} columnas")
    if sugerido is not None:
        opciones.append(f"usar papel {sugerido}")
    if custom is not None:
        opciones.append(f"un papel personalizado de {custom[0]} × {custom[1]} mm")
    texto = (
        f"Con {cols} columnas en {papel} {_ORIENTACION_ES[orientacion]} las celdas miden "
        f"{celda_mm} mm (mínimo {CELDA_MIN_MM:g} mm), demasiado chicas para dibujar."
    )
    if opciones:
        cuerpo = ", ".join(opciones[:-1]) + (" o " if len(opciones) > 1 else "") + opciones[-1]
        texto += f" Opciones: {cuerpo}."
    return texto


# --- Multi-papel (RF5.7, design.md §7.4) ---


def calcular_layouts(config: MosaicoConfig, ancho_img: int, alto_img: int) -> dict[str, Layout]:
    """Un layout por papel con la misma grilla; la fija el primer papel de la lista."""
    personalizado = (
        (config.papel_personalizado.ancho_mm, config.papel_personalizado.alto_mm)
        if config.papel_personalizado is not None
        else None
    )
    papeles = [obtener_papel(nombre, personalizado) for nombre in config.papeles]
    layouts: dict[str, Layout] = {}
    filas: int | None = None
    for papel in papeles:
        try:
            layout = calcular_layout(config, ancho_img, alto_img, papel, filas_fijas=filas)
        except CeldaDemasiadoChicaError as error:
            if len(papeles) == 1:
                raise
            raise _error_multi_papel(
                config, ancho_img, alto_img, papel, papeles, filas, error
            ) from None
        filas = layout.filas if filas is None else filas
        layouts[papel.nombre] = layout
    return layouts


def _error_multi_papel(
    config: MosaicoConfig,
    ancho_img: int,
    alto_img: int,
    papel: Papel,
    papeles: list[Papel],
    filas: int | None,
    error: CeldaDemasiadoChicaError,
) -> CeldaDemasiadoChicaError:
    """Rehace el error nombrando el papel que falla, con columnas que sirven para todos."""
    orientacion = resolver_orientacion(config.orientacion, ancho_img, alto_img)
    celda = _celda_completa(config, ancho_img, alto_img, papel, filas)
    cols_max = columnas_maximas(config, ancho_img, alto_img, papeles)
    mensaje = f"Falla el papel {papel.nombre}. " + mensaje_celda_chica(
        config.columnas,
        papel.nombre,
        orientacion,
        celda,
        cols_max,
        error.papel_sugerido,
        error.personalizado_mm,
    )
    return CeldaDemasiadoChicaError(
        mensaje,
        columnas_max=cols_max,
        papel_sugerido=error.papel_sugerido,
        personalizado_mm=error.personalizado_mm,
    )
