"""Modelo de configuración del mosaico, validado con pydantic y con mensajes en español.

Los rangos no se declaran con Field(ge=..., le=...) porque pydantic genera esos mensajes
en inglés: cada campo tiene su validador propio que lanza ValueError con el texto final.
"""

from enum import StrEnum
from numbers import Integral, Real
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from mosaico_tramas.errores import ConfigInvalidaError
from mosaico_tramas.papel import (
    PERSONALIZADO,
    REGISTRO_PAPELES,
    Orientacion,
    papel_personalizado,
)

# Estilo clásico de la referencia: siempre 6 símbolos (checkpoint D)
N_SIMBOLOS = 6


class MetodoCuantizacion(StrEnum):
    """Método para repartir la luminancia en N niveles (sin celdas vacías)."""

    QUANTILES = "quantiles"
    KMEANS = "kmeans"
    UNIFORM = "uniform"


class Recorte(StrEnum):
    """FIT conserva la imagen entera; CENTER recorta al centro para llenar la página."""

    FIT = "fit"
    CENTER = "center"


class EstiloGrilla(StrEnum):
    """Grilla de la plantilla: líneas grises o puntos en las esquinas (RF7.2a)."""

    LINEAS = "lines"
    PUNTOS = "dots"


class UbicacionLeyenda(StrEnum):
    """Dónde va la leyenda de símbolos."""

    BELOW = "below"
    SEPARATE = "separate"


# --- Helpers de validación ---


def _entero(valor: Any, minimo: int, maximo: int, mensaje: str) -> int:
    """Valida un entero en rango (rechaza bool y floats); el mensaje se completa con el valor."""
    if isinstance(valor, bool) or not isinstance(valor, Integral) or not minimo <= valor <= maximo:
        raise ValueError(f"{mensaje} (valor recibido: {valor!r}).")
    return int(valor)


def _numero(valor: Any, minimo: float, maximo: float, mensaje: str) -> float:
    """Valida un número real en rango (rechaza bool)."""
    if isinstance(valor, bool) or not isinstance(valor, Real) or not minimo <= valor <= maximo:
        raise ValueError(f"{mensaje} (valor recibido: {valor!r}).")
    return float(valor)


def _opcion[E: StrEnum](valor: Any, enum: type[E], mensaje: str) -> E:
    """Convierte un string en el miembro del enum, o explica las opciones válidas."""
    try:
        return enum(valor)
    except ValueError:
        opciones = ", ".join(m.value for m in enum)
        raise ValueError(f"{mensaje}: {opciones} (valor recibido: {valor!r}).") from None


class PapelPersonalizado(BaseModel):
    """Medidas del papel CUSTOM en milímetros."""

    model_config = ConfigDict(frozen=True)

    ancho_mm: float
    alto_mm: float


class MosaicoConfig(BaseModel):
    """Parámetros de un mosaico. Inmutable y hashable (sirve como clave de cache)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    n_simbolos: int = 6
    columnas: int = 40
    metodo: MetodoCuantizacion = MetodoCuantizacion.QUANTILES
    reduccion_ruido: bool = True
    umbral_ruido: int = 2
    limitar_oscuros: bool = True
    max_oscuros_pct: float = 8.0
    papeles: tuple[str, ...] = ("A4",)
    papel_personalizado: PapelPersonalizado | None = None
    orientacion: Orientacion = Orientacion.AUTO
    margen_mm: float = 12.7
    celda_min_mm: float = 3.5  # RF4.6: límite duro configurable entre 3 y 4 mm
    grosor_trazo_mm: float = 0.5  # RF5.0: microfibra del comprador
    recorte: Recorte = Recorte.FIT
    leyenda: UbicacionLeyenda = UbicacionLeyenda.BELOW
    incluir_solucion: bool = True
    grilla_en_solucion: bool = False
    estilo_grilla: EstiloGrilla = EstiloGrilla.LINEAS
    percentil_bajo: float = 2.0
    percentil_alto: float = 98.0
    png_lado_px: int = 2000

    @classmethod
    def crear(cls, **valores: Any) -> Self:
        """Construye la config; ante errores lanza ConfigInvalidaError con mensajes en español."""
        try:
            return cls(**valores)
        except ValidationError as error:
            raise ConfigInvalidaError(_mensaje_error(error)) from None

    # --- Validadores por campo ---

    @field_validator("n_simbolos", mode="before")
    @classmethod
    def _v_n(cls, v: Any) -> int:
        return _entero(
            v,
            N_SIMBOLOS,
            N_SIMBOLOS,
            f"La cantidad de símbolos es fija: el estilo clásico usa {N_SIMBOLOS}",
        )

    @field_validator("columnas", mode="before")
    @classmethod
    def _v_columnas(cls, v: Any) -> int:
        return _entero(v, 10, 200, "Las columnas deben ser un entero entre 10 y 200")

    @field_validator("umbral_ruido", mode="before")
    @classmethod
    def _v_umbral(cls, v: Any) -> int:
        return _entero(v, 2, 20, "El umbral de ruido debe ser un entero entre 2 y 20")

    @field_validator("max_oscuros_pct", mode="before")
    @classmethod
    def _v_oscuros(cls, v: Any) -> float:
        return _numero(v, 1, 100, "El límite de oscuros debe estar entre 1 y 100 %")

    @field_validator("margen_mm", mode="before")
    @classmethod
    def _v_margen(cls, v: Any) -> float:
        return _numero(v, 5, 40, "Los márgenes deben estar entre 5 y 40 mm")

    @field_validator("celda_min_mm", mode="before")
    @classmethod
    def _v_celda_min(cls, v: Any) -> float:
        return _numero(v, 3, 4, "La celda mínima debe estar entre 3 y 4 mm")

    @field_validator("grosor_trazo_mm", mode="before")
    @classmethod
    def _v_grosor(cls, v: Any) -> float:
        return _numero(v, 0.1, 1, "El grosor del trazo debe estar entre 0.1 y 1 mm")

    @field_validator("percentil_bajo", mode="before")
    @classmethod
    def _v_p_bajo(cls, v: Any) -> float:
        return _numero(v, 0, 49, "El percentil bajo debe estar entre 0 y 49")

    @field_validator("percentil_alto", mode="before")
    @classmethod
    def _v_p_alto(cls, v: Any) -> float:
        return _numero(v, 51, 100, "El percentil alto debe estar entre 51 y 100")

    @field_validator("png_lado_px", mode="before")
    @classmethod
    def _v_png(cls, v: Any) -> int:
        return _entero(v, 500, 6000, "El lado del PNG debe ser un entero entre 500 y 6000 px")

    @field_validator("metodo", mode="before")
    @classmethod
    def _v_metodo(cls, v: Any) -> MetodoCuantizacion:
        return _opcion(v, MetodoCuantizacion, "El método de cuantización debe ser uno de")

    @field_validator("orientacion", mode="before")
    @classmethod
    def _v_orientacion(cls, v: Any) -> Orientacion:
        return _opcion(v, Orientacion, "La orientación debe ser una de")

    @field_validator("recorte", mode="before")
    @classmethod
    def _v_recorte(cls, v: Any) -> Recorte:
        return _opcion(v, Recorte, "El recorte debe ser uno de")

    @field_validator("leyenda", mode="before")
    @classmethod
    def _v_leyenda(cls, v: Any) -> UbicacionLeyenda:
        return _opcion(v, UbicacionLeyenda, "La ubicación de la leyenda debe ser una de")

    @field_validator("estilo_grilla", mode="before")
    @classmethod
    def _v_estilo_grilla(cls, v: Any) -> EstiloGrilla:
        return _opcion(v, EstiloGrilla, "El estilo de grilla debe ser uno de")

    @field_validator("papeles", mode="before")
    @classmethod
    def _v_papeles(cls, v: Any) -> tuple[str, ...]:
        crudos = [v] if isinstance(v, str) else list(v)
        if not crudos:
            raise ValueError("Elegí al menos un papel.")
        nombres = tuple(str(p).strip().upper() for p in crudos)
        validos = {*REGISTRO_PAPELES, PERSONALIZADO}
        for nombre in nombres:
            if nombre not in validos:
                opciones = ", ".join([*REGISTRO_PAPELES, PERSONALIZADO])
                raise ValueError(f"Papel desconocido: {nombre!r}. Opciones válidas: {opciones}.")
        if len(set(nombres)) != len(nombres):
            raise ValueError("Hay un papel repetido en la lista de papeles.")
        return nombres

    @field_validator("papel_personalizado", mode="before")
    @classmethod
    def _v_personalizado(cls, v: Any) -> Any:
        if v is None or isinstance(v, PapelPersonalizado):
            return v
        if isinstance(v, dict):
            ancho, alto = v.get("ancho_mm"), v.get("alto_mm")
        else:
            ancho, alto = v
        if not _son_numeros(ancho, alto):
            raise ValueError("Las medidas del papel personalizado deben ser números en mm.")
        try:
            papel = papel_personalizado(float(ancho), float(alto))
        except ConfigInvalidaError as error:
            # pydantic solo agrupa ValueError; se re-lanza para no perder los demás errores
            raise ValueError(str(error)) from None
        return PapelPersonalizado(ancho_mm=papel.ancho_mm, alto_mm=papel.alto_mm)

    @model_validator(mode="after")
    def _v_cruzadas(self) -> Self:
        if PERSONALIZADO in self.papeles and self.papel_personalizado is None:
            raise ValueError(
                "Elegiste papel personalizado pero no indicaste su ancho y alto en mm."
            )
        return self


def _son_numeros(*valores: Any) -> bool:
    return all(isinstance(v, Real) and not isinstance(v, bool) for v in valores)


def _mensaje_error(error: ValidationError) -> str:
    """Junta los mensajes en español de cada error de pydantic."""
    lineas: list[str] = []
    for detalle in error.errors():
        ctx_error = (detalle.get("ctx") or {}).get("error")
        if detalle["type"] == "extra_forbidden":
            lineas.append(f"Parámetro desconocido: {detalle['loc'][0]!r}.")
        elif ctx_error is not None:
            lineas.append(str(ctx_error))
        else:
            campo = ".".join(str(p) for p in detalle["loc"]) or "configuración"
            lineas.append(f"Valor inválido para {campo!r} (valor recibido: {detalle['input']!r}).")
    return "\n".join(lineas)
