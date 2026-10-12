"""Render vectorial con ReportLab.

Los símbolos usan coordenadas normalizadas con y hacia abajo; acá se convierten a puntos PDF
(y hacia arriba) a partir de la esquina superior izquierda de la celda.
"""

import io

from reportlab.pdfgen.canvas import Canvas

from mosaico_tramas.simbolos.primitivas import TRAZO_REL, Linea, Poligono, Punto, Simbolo

TITULO_PDF = "Hatch Mosaic"


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
