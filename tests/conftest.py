"""Fixtures compartidas de pytest."""

import pytest


@pytest.fixture(autouse=True)
def _entorno_limpio(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    """Aísla los tests de un .env local y de variables MOSAICO_ del sistema."""
    import os

    for clave in list(os.environ):
        if clave.startswith("MOSAICO_"):
            monkeypatch.delenv(clave, raising=False)
    monkeypatch.chdir(tmp_path)  # type: ignore[arg-type]
