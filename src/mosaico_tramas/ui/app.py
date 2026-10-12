"""UI interna en Streamlit (RF8). Toda la lógica vive en el núcleo (pipeline)."""

import hashlib

import altair as alt
import pandas as pd
import streamlit as st

from mosaico_tramas import __version__
from mosaico_tramas.config import MosaicoConfig
from mosaico_tramas.errores import CeldaDemasiadoChicaError, MosaicoError
from mosaico_tramas.papel import PERSONALIZADO, REGISTRO_PAPELES
from mosaico_tramas.pipeline import (
    Resultado,
    archivos,
    empaquetar_zip,
    generar_mosaico,
    generar_preview,
    nombre_base_seguro,
)
from mosaico_tramas.settings import ConfiguracionInvalidaError, Settings, get_settings

# Claves de session_state que la UI también usa para aplicar sugerencias
CLAVE_IMAGEN_PRUEBA = "imagen_prueba"  # permite inyectar una imagen en los tests
CLAVE_NOMBRE_PRUEBA = "imagen_nombre"

METODOS = {
    "quantiles": "Cuantiles (recomendado)",
    "kmeans": "K-means",
    "uniform": "Uniforme (prototipo, para comparar)",
}
ORIENTACIONES = {"auto": "Automática", "portrait": "Vertical", "landscape": "Horizontal"}
LEYENDAS = {"below": "Debajo de la grilla", "separate": "En hoja aparte"}


def _etiqueta_papel(nombre: str) -> str:
    if nombre == PERSONALIZADO:
        return "Personalizado (mm)"
    papel = REGISTRO_PAPELES[nombre]
    return f"{nombre} ({papel.ancho_mm:g} × {papel.alto_mm:g} mm)"


@st.cache_data(show_spinner=False, max_entries=16)
def _preview(imagen: bytes, config_json: str, max_mb: float) -> Resultado:
    return generar_preview(imagen, MosaicoConfig.model_validate_json(config_json), max_mb)


@st.cache_data(show_spinner=False, max_entries=4)
def _final(imagen: bytes, config_json: str, max_mb: float) -> Resultado:
    return generar_mosaico(imagen, MosaicoConfig.model_validate_json(config_json), max_mb=max_mb)


def _imagen() -> tuple[bytes, str] | None:
    """Imagen subida, o la inyectada por los tests."""
    subida = st.sidebar.file_uploader("Imagen (JPG o PNG)", type=["jpg", "jpeg", "png"])
    if subida is not None:
        return subida.getvalue(), subida.name
    if CLAVE_IMAGEN_PRUEBA in st.session_state:
        return st.session_state[CLAVE_IMAGEN_PRUEBA], st.session_state.get(
            CLAVE_NOMBRE_PRUEBA, "prueba.png"
        )
    return None


def _controles(settings: Settings) -> dict[str, object]:
    """Barra lateral con todos los parámetros (RF8.2)."""
    barra = st.sidebar
    barra.subheader("Tonos")
    barra.caption(r"Estilo clásico: punto · / · \ · X · asterisco · celda llena.")
    metodo = barra.selectbox(
        "Método de cuantización", list(METODOS), format_func=METODOS.get, key="metodo"
    )
    reduccion = barra.checkbox("Reducir ruido (celdas sueltas)", value=True, key="reduccion_ruido")
    umbral = barra.slider(
        "Tamaño mínimo de zona (celdas)", 2, 20, 2, key="umbral_ruido", disabled=not reduccion
    )
    limitar = barra.checkbox("Limitar celdas llenas", value=True, key="limitar_oscuros")
    max_oscuros = barra.slider(
        "Máximo de celdas llenas (%)", 1, 100, 8, key="max_oscuros_pct", disabled=not limitar
    )

    barra.subheader("Grilla y papel")
    columnas = barra.number_input("Columnas", 10, 200, 40, step=1, key="columnas")
    opciones_papel = [*REGISTRO_PAPELES, PERSONALIZADO]
    papeles = barra.multiselect(
        "Papel (podés elegir varios)",
        opciones_papel,
        default=[settings.default_paper],
        format_func=_etiqueta_papel,
        key="papeles",
    )
    personalizado = None
    if PERSONALIZADO in papeles:
        col_a, col_b = barra.columns(2)
        ancho = col_a.number_input("Ancho (mm)", 100.0, 1200.0, 430.0, key="custom_ancho")
        alto = col_b.number_input("Alto (mm)", 100.0, 1200.0, 600.0, key="custom_alto")
        personalizado = (ancho, alto)
    orientacion = barra.radio(
        "Orientación",
        list(ORIENTACIONES),
        format_func=ORIENTACIONES.get,
        key="orientacion",
        horizontal=True,
    )
    margen = barra.number_input("Márgenes (mm)", 5.0, 40.0, 12.7, step=0.5, key="margen_mm")
    rellenar = barra.checkbox(
        "Rellenar la hoja (recortar al centro)",
        value=False,
        key="rellenar",
        help="Apagado: la imagen entra completa. Encendido: se recorta al centro.",
    )

    barra.subheader("Contenido del PDF")
    leyenda = barra.radio("Leyenda", list(LEYENDAS), format_func=LEYENDAS.get, key="leyenda")
    solucion = barra.checkbox("Incluir página de solución", value=True, key="incluir_solucion")
    marca = barra.checkbox("Puntito tenue en celdas vacías", value=True, key="marca_blanco")
    grilla_sol = barra.checkbox(
        "Grilla tenue en la solución", value=False, key="grilla_en_solucion"
    )

    return {
        "metodo": metodo,
        "reduccion_ruido": reduccion,
        "umbral_ruido": umbral,
        "limitar_oscuros": limitar,
        "max_oscuros_pct": float(max_oscuros),
        "columnas": int(columnas),
        "papeles": papeles,
        "papel_personalizado": personalizado,
        "orientacion": orientacion,
        "margen_mm": float(margen),
        "recorte": "center" if rellenar else "fit",
        "leyenda": leyenda,
        "incluir_solucion": solucion,
        "marca_blanco": marca,
        "grilla_en_solucion": grilla_sol,
    }


def _aplicar(**cambios: object) -> None:
    """Callback de los botones de sugerencia: cambia los controles y la app se re-ejecuta."""
    for clave, valor in cambios.items():
        st.session_state[clave] = valor


def _error_celda_chica(error: CeldaDemasiadoChicaError) -> None:
    """Error en español con las sugerencias aplicables en un clic (RF4.6b)."""
    st.error(str(error))
    columnas = st.columns(3)
    if error.columnas_max is not None:
        columnas[0].button(
            f"Usar {error.columnas_max} columnas",
            key="sugerencia_columnas",
            on_click=_aplicar,
            kwargs={"columnas": error.columnas_max},
        )
    if error.papel_sugerido is not None:
        columnas[1].button(
            f"Usar papel {error.papel_sugerido}",
            key="sugerencia_papel",
            on_click=_aplicar,
            kwargs={"papeles": [error.papel_sugerido]},
        )
    if error.personalizado_mm is not None:
        ancho, alto = error.personalizado_mm
        columnas[2].button(
            f"Usar {ancho} × {alto} mm",
            key="sugerencia_custom",
            on_click=_aplicar,
            kwargs={
                "papeles": [PERSONALIZADO],
                "custom_ancho": float(ancho),
                "custom_alto": float(alto),
            },
        )


def _histograma(resultado: Resultado) -> alt.LayerChart:
    """Barras de celdas por nivel y una línea con el mínimo aceptable (RF3.6, RF3.7)."""
    n = resultado.config.n_simbolos
    nombres = ["vacío", *(s.id for s in resultado.simbolos)]
    datos = pd.DataFrame(
        {
            "nivel": [f"{i} · {nombres[i]}" for i in range(n + 1)],
            "porcentaje": resultado.distribucion.porcentajes,
            "celdas": resultado.distribucion.conteos,
        }
    )
    barras = (
        alt.Chart(datos)
        .mark_bar()
        .encode(
            x=alt.X("nivel:N", sort=None, title="Nivel"),
            y=alt.Y("porcentaje:Q", title="% de celdas"),
            tooltip=["nivel", "celdas", alt.Tooltip("porcentaje:Q", format=".1f")],
        )
    )
    minimo = (
        alt.Chart(pd.DataFrame({"minimo": [50 / (n + 1)]}))
        .mark_rule(strokeDash=[4, 4], color="gray")
        .encode(y="minimo:Q")
    )
    return barras + minimo


def _resumen(resultado: Resultado) -> str:
    partes = [f"Grilla {resultado.columnas} × {resultado.filas}"]
    for nombre, layout in resultado.layouts.items():
        leyenda = "leyenda debajo" if layout.leyenda_en_plantilla else "leyenda aparte"
        partes.append(f"{nombre}: celda {layout.celda_mm:.1f} mm, {leyenda}")
    return " · ".join(partes)


def _descargas(imagen: bytes, nombre: str, config: MosaicoConfig, max_mb: float) -> None:
    """Botón para generar el PDF final y descargas del PDF/ZIP y el PNG (RF8.5)."""
    clave = hashlib.sha256(imagen).hexdigest() + config.model_dump_json()
    if st.button("Generar PDF", type="primary", key="generar"):
        st.session_state["clave_final"] = clave
    if st.session_state.get("clave_final") != clave:
        return
    with st.spinner("Generando PDF…"):
        resultado = _final(imagen, config.model_dump_json(), max_mb)
    base = nombre_base_seguro(nombre)
    entregables = archivos(resultado, base)
    columnas = st.columns(2)
    if len(resultado.pdfs) == 1:
        nombre_pdf = next(n for n in entregables if n.endswith(".pdf"))
        columnas[0].download_button(
            "Descargar PDF",
            entregables[nombre_pdf],
            file_name=nombre_pdf,
            mime="application/pdf",
            key="descargar_pdf",
        )
    else:
        columnas[0].download_button(
            f"Descargar ZIP ({', '.join(resultado.pdfs)})",
            empaquetar_zip(resultado, base),
            file_name=f"{base}.zip",
            mime="application/zip",
            key="descargar_zip",
        )
    nombre_png = next(n for n in entregables if "_solution_" in n)
    columnas[1].download_button(
        "Descargar PNG (preview)",
        entregables[nombre_png],
        file_name=nombre_png,
        mime="image/png",
        key="descargar_png",
    )


def main() -> None:
    """Punto de entrada de la UI."""
    st.set_page_config(page_title="Mosaico por tramas", layout="wide")
    try:
        settings = get_settings()
    except ConfiguracionInvalidaError as error:
        st.error(str(error))
        st.stop()
        return

    st.title("Mosaico por tramas")
    st.caption(f"Versión {__version__}")

    imagen = _imagen()
    valores = _controles(settings)
    if imagen is None:
        st.info("Subí una imagen JPG o PNG para empezar.")
        return
    datos, nombre = imagen

    try:
        config = MosaicoConfig.crear(**valores)
        resultado = _preview(datos, config.model_dump_json(), float(settings.max_upload_mb))
    except CeldaDemasiadoChicaError as error:
        _error_celda_chica(error)
        return
    except MosaicoError as error:
        st.error(str(error))
        return

    for aviso in resultado.avisos:
        st.warning(aviso.mensaje)
    st.caption(_resumen(resultado))

    tab_resultado, tab_plantilla, tab_distribucion = st.tabs(
        ["Resultado", "Plantilla", "Distribución"]
    )
    tab_resultado.image(resultado.png_solucion, width="stretch")
    tab_plantilla.image(resultado.png_plantilla, width="stretch")
    tab_distribucion.altair_chart(_histograma(resultado), width="stretch")
    tab_distribucion.caption("La línea punteada marca el mínimo aceptable por nivel.")

    _descargas(datos, nombre, config, float(settings.max_upload_mb))


main()
