# Mosaico por tramas

Genera una grilla numerada en la que cada número corresponde a un símbolo (punto, diagonales,
X, asterisco, celda llena). Al dibujar los símbolos aparece la imagen con efecto de
grabado a pluma. La salida es un PDF vectorial imprimible (plantilla, leyenda y solución) y un
PNG de preview para el listing.

La especificación vive en [`docs/specs/mosaico-tramas/`](docs/specs/mosaico-tramas/):
[requisitos](docs/specs/mosaico-tramas/requirements.md),
[diseño](docs/specs/mosaico-tramas/design.md) y
[tareas](docs/specs/mosaico-tramas/tasks.md).

## Requisitos

- Python 3.12
- Git Bash (Windows) o cualquier shell POSIX

## Instalación

```bash
py -3.12 -m venv .venv
source .venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Correr la app

```bash
streamlit run src/mosaico_tramas/ui/app.py
```

1. Subí una imagen JPG o PNG en la barra lateral.
2. Ajustá los parámetros: la preview, la plantilla y el histograma se actualizan solos.
3. Tocá **Generar PDF** y descargá el PDF (o el ZIP si elegiste varios papeles) y el PNG.

> **Después de actualizar el código, reiniciá la app** (Ctrl+C y volvé a correr el comando).
> Streamlit recarga solo `app.py`, no los módulos del núcleo: si la app queda corriendo,
> la UI nueva puede usar una configuración vieja y mostrar errores como
> "Parámetro desconocido".

## Parámetros principales

| Parámetro | Valores | Notas |
|---|---|---|
| Símbolos | 6 fijos (estilo clásico) | 1 punto · 2 / · 3 \ · 4 X · 5 asterisco · 6 celda llena. / y \ comparten tono. |
| Columnas | 10 a 200 | Las filas salen de la proporción de la imagen. |
| Método | cuantiles (recomendado), k-means, uniforme | Cuantiles reparte las celdas parejo entre niveles. |
| Reducir ruido | umbral 2 a 20 celdas | Elimina zonas más chicas que el umbral. |
| Limitar celdas llenas | 1 a 100 % (por defecto 8 %) | Evita manchas negras pesadas. |
| Papel | A4, Letter, A3, Tabloid, personalizado (100–1200 mm) | Se pueden elegir varios: misma grilla en todos. |
| Orientación | automática, vertical, horizontal | La automática sigue la proporción de la imagen. |
| Márgenes | 5 a 40 mm (por defecto 12,7 mm) | Seguro para impresoras hogareñas. |
| Rellenar la hoja | sí / no | Sí: recorta la imagen al centro para llenar la hoja. |
| Estilo de grilla | líneas / puntos en las esquinas | Gris muy claro (18 %) para que no se note en el dibujo final. |
| Leyenda | debajo / en hoja aparte | Si no entra debajo, pasa sola a una hoja aparte con un aviso. |

**Celda mínima de 4 mm.** Por debajo de 4 mm no se genera nada: la app explica por qué y
ofrece, con un clic, usar menos columnas, otro papel o un papel personalizado. Como referencia,
A4 admite unas 45 columnas en vertical y 54 en horizontal.

**Útil recomendado (para el listing):** una fibra o fineliner de **0,5 mm**. Las coberturas de
tinta de los símbolos están medidas con ese trazo en una celda de 4 mm; con una birome más
fina el dibujo sale algo más claro.

## Uso desde código (sin Streamlit)

```python
from mosaico_tramas.config import MosaicoConfig
from mosaico_tramas.pipeline import empaquetar_zip, generar_mosaico

config = MosaicoConfig.crear(columnas=45, papeles=["A4", "LETTER"], estilo_grilla="dots")
resultado = generar_mosaico(open("perro.jpg", "rb").read(), config)
open("perro.zip", "wb").write(empaquetar_zip(resultado, "perro"))
```

Misma imagen y misma configuración dan exactamente los mismos bytes.

## Tests y lint

```bash
pytest
```
```bash
pytest -m "not slow"
```
```bash
ruff check .
```

El test marcado `slow` mide el rendimiento (grilla de 100 × 140 en menos de 5 s).

## Variables de entorno

Ver [`.env.example`](.env.example). Se validan al arrancar: si alguna es inválida, la app se
detiene con un mensaje en español.
