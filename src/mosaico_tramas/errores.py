"""Jerarquía de excepciones del núcleo. Todos los mensajes van en español."""


class MosaicoError(Exception):
    """Base de todos los errores esperables del generador."""


class ConfigInvalidaError(MosaicoError):
    """La configuración del mosaico no pasa la validación."""


class ImagenInvalidaError(MosaicoError):
    """El archivo subido no es una imagen válida o supera el tamaño permitido."""


class ErrorBibliotecaSimbolos(MosaicoError):
    """La biblioteca no permite armar un subconjunto válido (error interno, no del usuario)."""


class CeldaDemasiadoChicaError(MosaicoError):
    """La celda quedaría por debajo del mínimo dibujable; incluye sugerencias concretas."""

    def __init__(
        self,
        mensaje: str,
        *,
        columnas_max: int | None = None,
        papel_sugerido: str | None = None,
        personalizado_mm: tuple[int, int] | None = None,
    ) -> None:
        super().__init__(mensaje)
        # Mayor cantidad de columnas que respeta el mínimo con la config actual
        self.columnas_max = columnas_max
        # Papel más chico del registro que admite las columnas pedidas
        self.papel_sugerido = papel_sugerido
        # Papel personalizado mínimo (ancho, alto) en mm
        self.personalizado_mm = personalizado_mm
