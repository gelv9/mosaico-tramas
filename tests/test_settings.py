"""Smoke tests de la configuración de entorno."""

from pathlib import Path

import pytest

from mosaico_tramas.settings import ConfiguracionInvalidaError, cargar_settings


def test_defaults_validan():
    settings = cargar_settings()
    assert settings.output_dir == Path("./output")
    assert settings.log_level == "INFO"
    assert settings.max_upload_mb == 20
    assert settings.default_paper == "A4"


def test_lee_variables_de_entorno(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MOSAICO_DEFAULT_PAPER", "LETTER")
    monkeypatch.setenv("MOSAICO_MAX_UPLOAD_MB", "50")
    settings = cargar_settings()
    assert settings.default_paper == "LETTER"
    assert settings.max_upload_mb == 50


def test_valor_fuera_de_rango_da_error_en_espanol(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MOSAICO_MAX_UPLOAD_MB", "0")
    with pytest.raises(ConfiguracionInvalidaError) as info:
        cargar_settings()
    mensaje = str(info.value)
    assert "MOSAICO_MAX_UPLOAD_MB" in mensaje
    assert "debe estar entre 1 y 200" in mensaje


def test_papel_desconocido_da_error_en_espanol(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MOSAICO_DEFAULT_PAPER", "B5")
    with pytest.raises(ConfiguracionInvalidaError) as info:
        cargar_settings()
    assert "MOSAICO_DEFAULT_PAPER debe ser uno de" in str(info.value)
