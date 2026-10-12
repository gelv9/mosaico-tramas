"""Registro de tamaños de papel y resolución de orientación."""

from dataclasses import dataclass
from enum import StrEnum

from mosaico_tramas.errores import ConfigInvalidaError

PT_POR_MM = 72.0 / 25.4
PERSONALIZADO = "CUSTOM"
PERSONALIZADO_MIN_MM = 100.0
PERSONALIZADO_MAX_MM = 1200.0


def mm_a_pt(mm: float) -> float:
    """Convierte milímetros a puntos PDF (1 pt = 1/72")."""
    return mm * PT_POR_MM


class Orientacion(StrEnum):
    """Orientación de la página; AUTO se resuelve según la proporción de la imagen."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    AUTO = "auto"


@dataclass(frozen=True)
class Papel:
    """Papel definido en vertical (ancho ≤ alto), en milímetros."""

    nombre: str
    ancho_mm: float
    alto_mm: float

    def tamano_mm(self, orientacion: Orientacion) -> tuple[float, float]:
        """Ancho y alto en mm para la orientación pedida (PORTRAIT o LANDSCAPE)."""
        corto, largo = sorted((self.ancho_mm, self.alto_mm))
        if orientacion is Orientacion.LANDSCAPE:
            return largo, corto
        return corto, largo

    def tamano_pt(self, orientacion: Orientacion) -> tuple[float, float]:
        """Ancho y alto en puntos para la orientación pedida."""
        ancho, alto = self.tamano_mm(orientacion)
        return mm_a_pt(ancho), mm_a_pt(alto)


# Registro extensible: para sumar un papel alcanza con agregar una entrada
REGISTRO_PAPELES: dict[str, Papel] = {
    p.nombre: p
    for p in (
        Papel("A4", 210.0, 297.0),
        Papel("LETTER", 215.9, 279.4),
        Papel("A3", 297.0, 420.0),
        Papel("TABLOID", 279.4, 431.8),
    )
}


def papel_personalizado(ancho_mm: float, alto_mm: float) -> Papel:
    """Crea un papel personalizado validando el rango permitido."""
    for valor in (ancho_mm, alto_mm):
        if not PERSONALIZADO_MIN_MM <= valor <= PERSONALIZADO_MAX_MM:
            raise ConfigInvalidaError(
                f"El papel personalizado debe medir entre {PERSONALIZADO_MIN_MM:.0f} y "
                f"{PERSONALIZADO_MAX_MM:.0f} mm por lado "
                f"(recibido: {ancho_mm:g} × {alto_mm:g} mm)."
            )
    return Papel(PERSONALIZADO, float(ancho_mm), float(alto_mm))


def obtener_papel(nombre: str, personalizado_mm: tuple[float, float] | None = None) -> Papel:
    """Busca un papel por nombre; para CUSTOM hacen falta las medidas."""
    if nombre == PERSONALIZADO:
        if personalizado_mm is None:
            raise ConfigInvalidaError(
                "Elegiste papel personalizado pero no indicaste su ancho y alto en mm."
            )
        return papel_personalizado(*personalizado_mm)
    try:
        return REGISTRO_PAPELES[nombre]
    except KeyError:
        validos = ", ".join([*REGISTRO_PAPELES, PERSONALIZADO])
        raise ConfigInvalidaError(
            f"Papel desconocido: {nombre!r}. Opciones válidas: {validos}."
        ) from None


def resolver_orientacion(orientacion: Orientacion, ancho_img: int, alto_img: int) -> Orientacion:
    """Resuelve AUTO: horizontal si la imagen es más ancha que alta, vertical en otro caso."""
    if orientacion is not Orientacion.AUTO:
        return orientacion
    return Orientacion.LANDSCAPE if ancho_img > alto_img else Orientacion.PORTRAIT
