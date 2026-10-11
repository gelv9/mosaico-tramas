# Mosaico por tramas

Genera una grilla numerada en la que cada número corresponde a un símbolo (rayas, cruces,
relleno…). Al dibujar los símbolos aparece la imagen con efecto de grabado a pluma.
La salida es un PDF vectorial imprimible y un PNG de preview.

La especificación vive en [`docs/specs/mosaico-tramas/`](docs/specs/mosaico-tramas/).

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

## Tests y lint

```bash
pytest
ruff check .
```
