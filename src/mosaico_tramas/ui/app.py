"""UI interna en Streamlit (stub del scaffold)."""

import streamlit as st

from mosaico_tramas import __version__
from mosaico_tramas.settings import ConfiguracionInvalidaError, get_settings


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
    st.caption(f"Versión {__version__} · papel por defecto: {settings.default_paper}")
    st.info("En construcción: la generación del mosaico llega en las próximas fases.")


main()
