"""Orquestación del generador (design.md §10). No depende de Streamlit (RNF3).

Uso desde una CLI, una API o la UI:

    resultado = generar_mosaico(bytes_de_la_imagen, MosaicoConfig.crear(columnas=40))
    resultado.pdfs["A4"], resultado.png_solucion, resultado.avisos
"""

import io
import re
import zipfile
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from mosaico_tramas.avisos import Aviso
from mosaico_tramas.config import MosaicoConfig
from mosaico_tramas.cuantizacion import Distribucion, cuantizar
from mosaico_tramas.imagen import a_grilla, cargar_luminancia
from mosaico_tramas.layout import Layout, calcular_layouts
from mosaico_tramas.render_pdf import generar_pdf
from mosaico_tramas.render_png import png_plantilla, png_solucion
from mosaico_tramas.simbolos.primitivas import Simbolo
from mosaico_tramas.simbolos.seleccion import simbolos_para

LADO_PREVIEW_PX = 1200
MAX_MB_POR_DEFECTO = 20.0
# Fecha fija para las entradas del ZIP: mismo contenido → mismos bytes (RNF2)
_FECHA_ZIP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class Resultado:
    """Todo lo que produce una generación."""

    config: MosaicoConfig
    niveles: npt.NDArray[np.uint8]
    simbolos: tuple[Simbolo, ...]  # niveles 1…N
    distribucion: Distribucion
    layouts: dict[str, Layout]  # por papel
    pdfs: dict[str, bytes]  # por papel (vacío en la preview)
    png_solucion: bytes
    png_plantilla: bytes
    avisos: tuple[Aviso, ...]

    @property
    def filas(self) -> int:
        return int(self.niveles.shape[0])

    @property
    def columnas(self) -> int:
        return int(self.niveles.shape[1])


def generar_mosaico(
    imagen: bytes,
    config: MosaicoConfig,
    *,
    con_pdf: bool = True,
    con_png: bool = True,
    lado_png: int | None = None,
    max_mb: float = MAX_MB_POR_DEFECTO,
) -> Resultado:
    """Imagen → grilla → niveles → PDF(s) y PNG. Lanza MosaicoError con mensajes en español."""
    lum = cargar_luminancia(imagen, max_mb)
    alto_img, ancho_img = lum.shape

    # El layout fija la grilla (las filas dependen del papel con recorte CENTER)
    layouts = calcular_layouts(config, ancho_img, alto_img)
    primero = next(iter(layouts.values()))
    oscuridad, avisos_imagen = a_grilla(
        lum,
        primero.columnas,
        primero.filas,
        config.recorte,
        config.percentil_bajo,
        config.percentil_alto,
    )
    cuantizacion = cuantizar(oscuridad, config)
    simbolos = simbolos_para(config)

    pdfs: dict[str, bytes] = {}
    if con_pdf:
        pdfs = {
            nombre: generar_pdf(cuantizacion.niveles, simbolos, layout, config)
            for nombre, layout in layouts.items()
        }

    lado = lado_png or config.png_lado_px
    solucion = png_solucion(cuantizacion.niveles, simbolos, lado) if con_png else b""
    plantilla = png_plantilla(cuantizacion.niveles, lado, config.marca_blanco) if con_png else b""

    return Resultado(
        config=config,
        niveles=cuantizacion.niveles,
        simbolos=simbolos,
        distribucion=cuantizacion.distribucion,
        layouts=layouts,
        pdfs=pdfs,
        png_solucion=solucion,
        png_plantilla=plantilla,
        avisos=avisos_imagen + _avisos_layout(layouts) + cuantizacion.avisos,
    )


def generar_preview(
    imagen: bytes, config: MosaicoConfig, max_mb: float = MAX_MB_POR_DEFECTO
) -> Resultado:
    """Variante rápida para la UI: sin PDF y con PNG de 1200 px."""
    return generar_mosaico(imagen, config, con_pdf=False, lado_png=LADO_PREVIEW_PX, max_mb=max_mb)


def _avisos_layout(layouts: dict[str, Layout]) -> tuple[Aviso, ...]:
    """Avisos de layout; con varios papeles se aclara a cuál corresponde cada uno."""
    varios = len(layouts) > 1
    avisos: list[Aviso] = []
    for nombre, layout in layouts.items():
        for aviso in layout.avisos:
            mensaje = f"{nombre}: {aviso.mensaje}" if varios else aviso.mensaje
            avisos.append(Aviso(aviso.codigo, mensaje))
    return tuple(avisos)


# --- Nombres de archivo y ZIP (RF5.7, RF5.8) ---


def nombre_base_seguro(nombre: str) -> str:
    """Deriva un nombre de archivo seguro del nombre original (sin extensión)."""
    base = nombre.rsplit(".", 1)[0] if "." in nombre else nombre
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", base).strip("_")[:60]
    return base or "mosaico"


def nombre_archivo(base: str, resultado: Resultado, sufijo: str, extension: str) -> str:
    """<nombre>_<sufijo>_<N>sym_<cols>x<filas>.<ext>; el sufijo es el papel o el tipo de PNG."""
    n = resultado.config.n_simbolos
    return f"{base}_{sufijo}_{n}sym_{resultado.columnas}x{resultado.filas}.{extension}"


def archivos(resultado: Resultado, base: str) -> dict[str, bytes]:
    """Todos los entregables con su nombre final: un PDF por papel y los dos PNG."""
    salida = {
        nombre_archivo(base, resultado, papel, "pdf"): pdf for papel, pdf in resultado.pdfs.items()
    }
    if resultado.png_solucion:
        salida[nombre_archivo(base, resultado, "solution", "png")] = resultado.png_solucion
    if resultado.png_plantilla:
        salida[nombre_archivo(base, resultado, "template", "png")] = resultado.png_plantilla
    return salida


def empaquetar_zip(resultado: Resultado, base: str) -> bytes:
    """ZIP determinista con todos los entregables (para entregar A4 y Letter juntos)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for nombre, datos in archivos(resultado, base).items():
            info = zipfile.ZipInfo(nombre, date_time=_FECHA_ZIP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, datos)
    return buffer.getvalue()
