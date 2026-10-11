"""Configuración de entorno validada con pydantic-settings.

Estas variables son de infraestructura (rutas, logging, límites). Los parámetros de cada
mosaico (símbolos, columnas, papel, etc.) se modelan aparte.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Nombres legibles de cada campo para los mensajes de error en español
_NOMBRES_ENV: dict[str, str] = {
    "output_dir": "MOSAICO_OUTPUT_DIR",
    "log_level": "MOSAICO_LOG_LEVEL",
    "max_upload_mb": "MOSAICO_MAX_UPLOAD_MB",
    "default_paper": "MOSAICO_DEFAULT_PAPER",
}


class ConfiguracionInvalidaError(RuntimeError):
    """Se lanza cuando alguna variable de entorno no pasa la validación."""


class Settings(BaseSettings):
    """Variables de entorno de la aplicación (prefijo MOSAICO_)."""

    model_config = SettingsConfigDict(
        env_prefix="MOSAICO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    output_dir: Path = Path("./output")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    max_upload_mb: int = Field(default=20, ge=1, le=200)
    default_paper: Literal["A4", "LETTER", "A3", "TABLOID"] = "A4"


def _limites(campo: str) -> tuple[object, object]:
    """Devuelve los límites (ge, le) declarados en un campo numérico de Settings."""
    minimo: object = "?"
    maximo: object = "?"
    for restriccion in Settings.model_fields[campo].metadata:
        minimo = getattr(restriccion, "ge", minimo)
        maximo = getattr(restriccion, "le", maximo)
    return minimo, maximo


def _traducir_error(error: ValidationError) -> str:
    """Convierte los errores de pydantic en un mensaje claro en español."""
    lineas: list[str] = ["La configuración de entorno es inválida:"]
    for detalle in error.errors():
        campo = str(detalle["loc"][0]) if detalle["loc"] else "?"
        nombre = _NOMBRES_ENV.get(campo, campo)
        valor = detalle.get("input")
        ctx = detalle.get("ctx") or {}
        tipo = detalle["type"]
        if tipo in ("greater_than_equal", "less_than_equal"):
            minimo, maximo = _limites(campo)
            motivo = f"debe estar entre {minimo} y {maximo}"
        elif tipo == "literal_error":
            motivo = f"debe ser uno de: {ctx.get('expected', '?')}"
        elif tipo in ("int_parsing", "int_type"):
            motivo = "debe ser un número entero"
        else:
            motivo = f"no es válido ({detalle['msg']})"
        lineas.append(f"  - {nombre} {motivo} (valor recibido: {valor!r}).")
    lineas.append("Revisá tu archivo .env o las variables de entorno (ver .env.example).")
    return "\n".join(lineas)


def cargar_settings(**overrides: object) -> Settings:
    """Carga y valida los settings; ante un error lanza un mensaje en español."""
    try:
        return Settings(**overrides)  # type: ignore[arg-type]
    except ValidationError as error:
        raise ConfiguracionInvalidaError(_traducir_error(error)) from None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings cacheados para usar en toda la app."""
    return cargar_settings()
