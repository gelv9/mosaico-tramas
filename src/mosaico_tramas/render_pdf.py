"""Render vectorial con ReportLab (RF5.5, RF6, RF7; design.md §8).

Los símbolos usan coordenadas normalizadas con y hacia abajo; acá se convierten a puntos PDF
(y hacia arriba) a partir de la esquina superior izquierda de la celda.

Cada símbolo (y el punto de la grilla) se define una vez como Form XObject del tamaño de la
celda y se coloca en cada celda: el PDF queda chico, el BBox del form recorta el símbolo a su
celda y los tests pueden contar exactamente qué se dibujó.
"""

import io

import numpy as np
import numpy.typing as npt
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from mosaico_tramas.config import EstiloGrilla, MosaicoConfig
from mosaico_tramas.layout import (
    ALTO_ENTRADA_MM,
    ALTO_INSTRUCCION_MM,
    ANCHO_ENTRADA_MM,
    LADO_AMPLIADO_MM,
    SEPARACION_LEYENDA_MM,
    Layout,
    Rect,
    alto_leyenda,
    entradas_por_fila,
)
from mosaico_tramas.papel import mm_a_pt
from mosaico_tramas.simbolos.primitivas import TRAZO_REL, Linea, Poligono, Punto, Simbolo

TITULO_PDF = "Hatch Mosaic"

# Grises de la plantilla (RF7.2): 0 = negro, 1 = blanco
GRIS_GRILLA = 0.82  # 18 % de negro: gris muy claro, no afecta el dibujo final
GRIS_NUMEROS = 0.5  # 50 % de negro
GRIS_GRILLA_SOLUCION = 0.90  # 10 % de negro
ANCHO_LINEA_GRILLA = 0.3
FUENTE = "Helvetica"
FUENTE_NEGRITA = "Helvetica-Bold"

INSTRUCCION = "Draw the symbol shown for each number in every cell."

NOMBRE_PUNTO_GRILLA = "punto_grilla"
NOMBRE_PUNTO_GRILLA_TENUE = "punto_grilla_tenue"
RADIO_PUNTO_GRILLA = 0.5  # pt (diámetro ≈ 0,35 mm)


def nombre_form(simbolo: Simbolo) -> str:
    """Nombre del Form XObject de un símbolo (ReportLab lo publica como FormXob.<nombre>)."""
    return f"simbolo_{simbolo.id}"


def nuevo_canvas(buffer: io.BytesIO, tamano_pt: tuple[float, float]) -> Canvas:
    """Canvas determinista: modo invariant (sin fecha ni ID variables) y metadatos fijos."""
    canvas = Canvas(buffer, pagesize=tamano_pt, invariant=1, pageCompression=1)
    canvas.setTitle(TITULO_PDF)
    canvas.setAuthor("")
    canvas.setCreator("mosaico-tramas")
    canvas.setProducer("mosaico-tramas")
    return canvas


def dibujar_simbolo(
    canvas: Canvas, simbolo: Simbolo, x: float, y_sup: float, lado: float, *, recortar: bool = True
) -> None:
    """Dibuja un símbolo en negro en la celda cuya esquina superior izquierda es (x, y_sup)."""
    canvas.saveState()
    if recortar:
        borde = canvas.beginPath()
        borde.rect(x, y_sup - lado, lado, lado)
        canvas.clipPath(borde, stroke=0, fill=0)
    canvas.setFillGray(0)
    canvas.setStrokeGray(0)
    canvas.setLineWidth(TRAZO_REL * lado)
    canvas.setLineCap(0)  # extremos planos (butt), igual que en el rasterizado

    def punto(u: float, v: float) -> tuple[float, float]:
        return x + u * lado, y_sup - v * lado

    for primitiva in simbolo.primitivas:
        match primitiva:
            case Linea(p0, p1):
                canvas.line(*punto(*p0), *punto(*p1))
            case Poligono(vertices):
                camino = canvas.beginPath()
                camino.moveTo(*punto(*vertices[0]))
                for vertice in vertices[1:]:
                    camino.lineTo(*punto(*vertice))
                camino.close()
                canvas.drawPath(camino, stroke=0, fill=1)
            case Punto(radio):
                canvas.circle(*punto(0.5, 0.5), radio * lado, stroke=0, fill=1)
    canvas.restoreState()


def _definir_forms(canvas: Canvas, simbolos: tuple[Simbolo, ...], celda: float) -> None:
    """Un Form XObject por símbolo (del tamaño de la celda) y los puntos de grilla."""
    for simbolo in simbolos:
        canvas.beginForm(nombre_form(simbolo), lowerx=0, lowery=0, upperx=celda, uppery=celda)
        dibujar_simbolo(canvas, simbolo, 0, celda, celda, recortar=False)
        canvas.endForm()
    # Puntos de la grilla (RF7.2a), centrados en el origen del form
    r = RADIO_PUNTO_GRILLA
    for nombre, gris in (
        (NOMBRE_PUNTO_GRILLA, GRIS_GRILLA),
        (NOMBRE_PUNTO_GRILLA_TENUE, GRIS_GRILLA_SOLUCION),
    ):
        canvas.beginForm(nombre, lowerx=-r, lowery=-r, upperx=r, uppery=r)
        canvas.setFillGray(gris)
        canvas.circle(0, 0, r, stroke=0, fill=1)
        canvas.endForm()


def _celdas(niveles: npt.NDArray[np.uint8], layout: Layout) -> list[tuple[int, float, float]]:
    """(nivel, x, y_inf) de cada celda, en orden de lectura."""
    x0, _, _, y1 = layout.rect_grilla
    c = layout.celda_pt
    filas, cols = niveles.shape
    return [
        (int(niveles[f, k]), x0 + k * c, y1 - (f + 1) * c)
        for f in range(filas)
        for k in range(cols)
    ]


def _grilla(
    canvas: Canvas, layout: Layout, gris: float, estilo: EstiloGrilla, tenue: bool = False
) -> None:
    """Grilla de líneas, o un punto en cada esquina de celda (RF7.2a)."""
    x0, y0, x1, y1 = layout.rect_grilla
    c = layout.celda_pt
    if estilo is EstiloGrilla.PUNTOS:
        nombre = NOMBRE_PUNTO_GRILLA_TENUE if tenue else NOMBRE_PUNTO_GRILLA
        for f in range(layout.filas + 1):
            for k in range(layout.columnas + 1):
                _colocar_form(canvas, nombre, x0 + k * c, y1 - f * c)
        return
    lineas = [(x0 + k * c, y0, x0 + k * c, y1) for k in range(layout.columnas + 1)]
    lineas += [(x0, y1 - f * c, x1, y1 - f * c) for f in range(layout.filas + 1)]
    canvas.saveState()
    canvas.setStrokeGray(gris)
    canvas.setLineWidth(ANCHO_LINEA_GRILLA)
    canvas.lines(lineas)
    canvas.restoreState()


def _colocar_form(canvas: Canvas, nombre: str, x: float, y: float) -> None:
    canvas.saveState()
    canvas.translate(x, y)
    canvas.doForm(nombre)
    canvas.restoreState()


def _pagina_plantilla(
    canvas: Canvas, niveles: npt.NDArray[np.uint8], layout: Layout, config: MosaicoConfig
) -> None:
    """Grilla gris con el número de cada celda: no hay celdas vacías (RF7.1–7.2)."""
    _grilla(canvas, layout, GRIS_GRILLA, config.estilo_grilla)
    c = layout.celda_pt
    tamano = max(4.0, 0.45 * c)
    canvas.setFont(FUENTE, tamano)
    canvas.setFillGray(GRIS_NUMEROS)
    for nivel, x, y in _celdas(niveles, layout):
        # Centrado vertical aproximando la altura de las cifras a 0,7 del tamaño
        canvas.drawCentredString(x + c / 2, y + c / 2 - 0.35 * tamano, str(nivel))


def _pagina_solucion(
    canvas: Canvas,
    niveles: npt.NDArray[np.uint8],
    simbolos: tuple[Simbolo, ...],
    layout: Layout,
    config: MosaicoConfig,
) -> None:
    """Resultado terminado: cada celda con su símbolo, sin números (RF7.4).

    Esta página no lleva leyenda: la grilla se centra en el área útil completa.
    """
    _, ay0, _, ay1 = layout.area_util()
    _, gy0, _, gy1 = layout.rect_grilla
    canvas.translate(0, (ay0 + ay1) / 2 - (gy0 + gy1) / 2)
    if config.grilla_en_solucion:
        _grilla(canvas, layout, GRIS_GRILLA_SOLUCION, config.estilo_grilla, tenue=True)
    for nivel, x, y in _celdas(niveles, layout):
        _colocar_form(canvas, nombre_form(simbolos[nivel - 1]), x, y)


def _texto_ajustado(canvas: Canvas, texto: str, x: float, y: float, ancho_max: float) -> None:
    """Escribe en 9 pt, achicando la fuente si no entra en el ancho disponible."""
    tamano = 9.0
    while tamano > 5 and stringWidth(texto, FUENTE, tamano) > ancho_max:
        tamano -= 0.5
    canvas.setFont(FUENTE, tamano)
    canvas.drawString(x, y, texto)


def _leyenda(
    canvas: Canvas,
    simbolos: tuple[Simbolo, ...],
    layout: Layout,
    config: MosaicoConfig,
    rect: Rect,
) -> None:
    """Instrucción en inglés y una entrada por nivel, de claro a oscuro (RF6.6–6.8)."""
    x0, _, x1, y1 = rect
    ancho = x1 - x0
    texto = INSTRUCCION
    y_texto = y1 - mm_a_pt(SEPARACION_LEYENDA_MM) - mm_a_pt(ALTO_INSTRUCCION_MM) + 3
    canvas.saveState()
    canvas.setFillGray(0)
    _texto_ajustado(canvas, texto, x0, y_texto, ancho)

    por_fila = entradas_por_fila(ancho)
    techo = y1 - mm_a_pt(SEPARACION_LEYENDA_MM + ALTO_INSTRUCCION_MM)
    real = min(layout.celda_pt, mm_a_pt(LADO_AMPLIADO_MM))
    ampliado = mm_a_pt(LADO_AMPLIADO_MM)
    entradas = [(str(i), s) for i, s in enumerate(simbolos, 1)]

    for i, (etiqueta, simbolo) in enumerate(entradas):
        ex = x0 + (i % por_fila) * mm_a_pt(ANCHO_ENTRADA_MM)
        centro_y = techo - (i // por_fila) * mm_a_pt(ALTO_ENTRADA_MM) - mm_a_pt(ALTO_ENTRADA_MM) / 2
        canvas.setFillGray(0)
        canvas.setFont(FUENTE_NEGRITA, 11)
        canvas.drawString(ex, centro_y - 4, etiqueta)
        x_real = ex + mm_a_pt(7)
        x_ampliado = x_real + real + mm_a_pt(2)
        for x_caja, lado in ((x_real, real), (x_ampliado, ampliado)):
            y_sup = centro_y + lado / 2
            dibujar_simbolo(canvas, simbolo, x_caja, y_sup, lado)
            _caja(canvas, x_caja, y_sup - lado, lado, config.estilo_grilla)
    canvas.restoreState()


def _caja(canvas: Canvas, x: float, y: float, lado: float, estilo: EstiloGrilla) -> None:
    """Recuadro de una entrada de la leyenda, con el mismo estilo que la grilla."""
    canvas.saveState()
    if estilo is EstiloGrilla.PUNTOS:
        for px, py in ((x, y), (x + lado, y), (x, y + lado), (x + lado, y + lado)):
            _colocar_form(canvas, NOMBRE_PUNTO_GRILLA, px, py)
    else:
        canvas.setStrokeGray(GRIS_GRILLA)
        canvas.setLineWidth(ANCHO_LINEA_GRILLA)
        canvas.rect(x, y, lado, lado, stroke=1, fill=0)
    canvas.restoreState()


def rect_leyenda_aparte(layout: Layout, config: MosaicoConfig) -> Rect:
    """Rectángulo de la leyenda en su propia página: arriba del área útil."""
    x0, _, x1, y1 = layout.area_util()
    alto = alto_leyenda(config.n_simbolos, x1 - x0)
    return (x0, y1 - alto, x1, y1)


def generar_pdf(
    niveles: npt.NDArray[np.uint8],
    simbolos: tuple[Simbolo, ...],
    layout: Layout,
    config: MosaicoConfig,
) -> bytes:
    """PDF: plantilla (+ leyenda si entra) → leyenda aparte → solución (RF7.5)."""
    buffer = io.BytesIO()
    canvas = nuevo_canvas(buffer, layout.pagina_pt)
    _definir_forms(canvas, simbolos, layout.celda_pt)

    _pagina_plantilla(canvas, niveles, layout, config)
    if layout.leyenda_en_plantilla and layout.rect_leyenda is not None:
        _leyenda(canvas, simbolos, layout, config, layout.rect_leyenda)
    canvas.showPage()

    if not layout.leyenda_en_plantilla:
        _leyenda(canvas, simbolos, layout, config, rect_leyenda_aparte(layout, config))
        canvas.showPage()

    if config.incluir_solucion:
        _pagina_solucion(canvas, niveles, simbolos, layout, config)
        canvas.showPage()

    canvas.save()
    return buffer.getvalue()
