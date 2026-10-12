"""Las imágenes sintéticas son deterministas (T9)."""

import hashlib

import numpy as np

from tests.conftest import (
    a_png,
    generar_degradado,
    generar_fondo_plano,
    generar_foto_sintetica,
    generar_plana,
)


def _hash(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def test_generadores_deterministas():
    for generar in (generar_degradado, generar_foto_sintetica, generar_fondo_plano, generar_plana):
        assert _hash(a_png(generar())) == _hash(a_png(generar()))


def test_foto_sintetica_tiene_buen_rango_tonal():
    img = generar_foto_sintetica()
    p2, p98 = (float(v) for v in np.percentile(img, [2, 98]))
    assert p98 - p2 > 120
