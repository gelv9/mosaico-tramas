# Mosaico por tramas — Tareas

> Estado: **aprobado** (Fase 3, 2026-10-11)
> Referencias: [requirements.md](requirements.md) · [design.md](design.md)
>
> **Cómo se trabaja cada tarea:** primero el test (en rojo), después el código (en verde), luego `ruff check` + `pytest`, marcar `[x]` acá y hacer **un commit por tarea** (`feat(<área>): … (T<n>)`).
> **🛑 Checkpoint:** al terminar cada bloque se muestra el resultado y se espera el OK.

---

## Bloque A — Base y biblioteca de símbolos

- [x] **T1 — Errores y avisos.** `errores.py` (`MosaicoError`, `ConfigInvalidaError`, `ImagenInvalidaError`, `CeldaDemasiadoChicaError(mensaje, sugerencias)`, `ErrorBibliotecaSimbolos`) y `avisos.py` (`Aviso`, códigos).
  - Cubre: base de RF1.3, RF4.6a, RF6.3, RF3.7 y RP6.
  - Test: `test_errores.py`. Las excepciones heredan de `MosaicoError`, el mensaje se conserva y `Aviso` es inmutable.

- [x] **T2 — Papeles.** `papel.py`: `Papel`, `REGISTRO_PAPELES` (A4, LETTER, A3, TABLOID), `papel_personalizado(ancho, alto)` con validación de 100 a 1200 mm, `orientar()` y `mm_a_pt()`.
  - Cubre: RF5.1, RF5.1a, RF5.1b, RF5.2 y RF5.3.
  - Test: `test_papel.py`. Las medidas en pt coinciden (±0,01) con la tabla de RF5.1, `auto` responde según la proporción, y un papel personalizado fuera de rango da error en español.

- [x] **T3 — Configuración.** `config.py`: `MosaicoConfig`, los enums y `PapelPersonalizado`, con validadores en español y validaciones cruzadas.
  - Cubre: RF1.1, RF1.3, RF3.4, RF3.5, RF4.1, RF5.4, RNF4 y RF5.1a.
  - Test: `test_config.py` (**CA2**). Con N = 4, 11, 7,5, `True` y `"x"` se obtiene el mensaje exacto de RF1.3. También se prueban los rangos de columnas, márgenes, umbral y porcentaje de oscuros, que se exija `papel_personalizado` cuando se elige CUSTOM, que `percentil_bajo` sea menor que `percentil_alto` y que la config sea inmutable.

- [x] **T4 — Primitivas y rasterizado.** `simbolos/primitivas.py` y `simbolos/raster.py`: `rasterizar(simbolo, px, trazo_rel)` con OpenCV y `cobertura(simbolo)` cacheada.
  - Cubre: RF2.2 y RF2.3.
  - Test: `test_raster.py`. La celda llena da 100 %, la vacía 0 % y una línea horizontal ≈ `TRAZO_REL` (±0,3 pp). Un triángulo de media celda da ≈ 50 %, y el rasterizado es determinista.

- [x] **T5 — Biblioteca.** `simbolos/biblioteca.py`: los símbolos de design.md §4.2 (10 tras el checkpoint A: símbolos fáciles con regla física), con familia y `nombre_en`.
  - Cubre: RF2.1, RF2.2 y RF2.6.
  - Test: `test_biblioteca.py`. Hay ≥ 14 candidatos y los ids son únicos. Cada símbolo tiene ≤ 6 trazos, coordenadas en [0, 1], está compuesto solo de `Linea`, `Punto` o `Poligono`, y existen `punto` y `lleno`. Las coberturas medidas quedan a ±1 pp de la tabla de diseño.

- [x] **T6 — Selección del subconjunto.** `simbolos/seleccion.py`: `elegir_simbolos(n)` por backtracking con poda y cache.
  - Cubre: RF2.4 (a–e), RF2.5 y RF2.7.
  - Test: `test_seleccion.py` (**CA1, CA9**). Para N = 5…7: cobertura estrictamente creciente, Δ ≥ 6 pp entre los niveles 1…N, Δ ≥ 1,5 pp entre el vacío y el nivel 1, nivel 1 = punto, nivel N = lleno, familias distintas y mismo resultado en dos llamadas. Con una biblioteca imposible (inyectada) se lanza `ErrorBibliotecaSimbolos`.

- [x] **T7 — Hoja de muestra.** `muestra.py`: `hoja_muestra(n | None) -> bytes` (PDF A4).
  - Cubre: RF2.8.
  - Test: `test_muestra.py`. El PDF es válido (pypdf), mide A4, su texto contiene los ids o números y las coberturas, y la salida es determinista.

> 🛑 **Checkpoint A.** Muestro las hojas de muestra para N = 5, 7 y 10, y la biblioteca completa. **Resultado:** biblioteca de 10 símbolos fáciles (≤ 3 trazos, ≥ 2 mm entre rayas en 4 mm), con triángulo y celda llena, fibra de 0,5 mm y N_MAX = 7.

---

## Bloque B — Imagen y cuantización

- [x] **T8 — Preprocesamiento.** `imagen.py`: `cargar_luminancia(bytes, max_mb)` (EXIF, alfa, L, float) y `a_grilla(lum, cols, filas, recorte, percentiles) -> (oscuridad, avisos)`.
  - Cubre: RP1–RP6 y RF4.3/RF4.4 (el recorte).
  - Test: `test_imagen.py`. Un PNG con alfa se compone sobre blanco y una imagen rotada por EXIF queda bien orientada. Bytes basura dan `ImagenInvalidaError` en español, igual que un archivo mayor al límite. La forma de la salida es la pedida. El estiramiento lleva p2→0 y p98→1, y una imagen plana emite `POCO_RANGO_TONAL`. `center` recorta al centro.

- [x] **T9 — Fixtures de imágenes sintéticas.** En `tests/conftest.py`: un degradado, una "foto" sintética (degradado radial, formas y ruido con semilla fija), una imagen con un fondo blanco plano y una imagen plana.
  - Cubre: soporte para CA3 y CA8.
  - Test: las fixtures son deterministas, porque el hash de los bytes es estable.

- [x] **T10 — Cuantización por cuantiles.** `cuantizacion.py`: histograma de 4096 bins, cuotas objetivo (con y sin límite de oscuros), cortes estrictamente crecientes y `aplicar_cortes`.
  - Cubre: RF3.1, RF3.2, RF3.3 y RF3.5 (vía cuotas).
  - Test: `test_cuantizacion.py` (**CA3**). Con el degradado y la foto sintética, para N = 5…7, ningún nivel tiene menos de 0,5·100/(N+1) %. Las celdas idénticas comparten nivel. Con el límite en L %, el nivel N queda ≤ L % y los demás quedan ≈ parejos.

- [x] **T11 — K-means y uniforme.** k-means 1D ponderado sobre el histograma, inicializado con los cuantiles, más el re-sembrado de clusters vacíos, y `uniform`.
  - Cubre: RF3.1 y RNF2.
  - Test: k-means da el mismo resultado en dos corridas, converge en un caso de 3 clusters obvios y no deja clusters vacíos. `uniform` usa los cortes k/(N+1).

- [x] **T12 — Límite de oscuros (post-paso).** `limitar_oscuros(niveles, d, N, pct)`.
  - Cubre: RF3.5.
  - Test (**CA10**, primera parte): después del post-paso, el nivel N queda ≤ L %; las celdas degradadas son las menos oscuras y van a N−1; el orden de desempate es estable.

- [x] **T13 — Reducción de ruido.** `reducir_ruido(niveles, umbral)`: componentes con conectividad 8, moda de los vecinos, desempates, hasta 3 pasadas.
  - Cubre: RF3.4.
  - Test (**CA11**): con umbral 2 no queda ningún componente de tamaño 1. Un bloque grande no se toca. Los desempates siguen el diseño y el resultado es determinista.

- [x] **T14 — Distribución y orquestación de la cuantización.** `cuantizar(d, config) -> (niveles, Distribucion, avisos)`, con el orden de RF3.8 y el aviso de nivel infrautilizado.
  - Cubre: RF3.6, RF3.7 y RF3.8.
  - Test (**CA10**, segunda parte): con ruido y límite activos, el límite se sigue cumpliendo al final. Los conteos suman el total, y el aviso aparece en una imagen con un fondo plano enorme y no aparece en el degradado. No se avisa por el nivel N cuando fue recortado a propósito.

- [x] **T14b — Triángulo opcional** *(decidido en el checkpoint B)*. `usar_triangulo` en la config, `SIN_TRIANGULO` en la biblioteca y `simbolos_para(config)`.
  - Cubre: RF1.4.
  - Test: sin triángulo y con N = 7 da error en español. Para N = 5 y 6, no hay triángulo y se cumplen los saltos y las familias.

> 🛑 **Checkpoint B.** Muestro las previews raster (con un render PNG mínimo) y los histogramas para quantiles, kmeans y uniform sobre la foto sintética, en una comparación lado a lado.

---

## Bloque C — Layout, PDF, PNG y pipeline

- [ ] **T15 — Alto de la leyenda.** `layout.alto_leyenda(n, marca_blanco, ancho_util)` y la grilla de entradas.
  - Cubre: RF6.2 y RF6.6.
  - Test: N = 6 con la marca en A4 vertical da ≈ 38,6 mm. La cantidad de entradas por fila depende del ancho útil.

- [ ] **T16 — Cálculo del layout.** `calcular_layout(config, proporcion, papel, filas_fijas=None) -> Layout`: orientación, filas, celda, decisión sobre la leyenda, centrado y `bbox_contenido()`.
  - Cubre: RF4.2–RF4.7, RF6.1–RF6.5 y RF5.4.
  - Test (**CA5, CA6** a nivel de layout): `below` en un caso que entra deja la leyenda en la página de la plantilla. Si no entra, va aparte y se emite `LEYENDA_MOVIDA`. `separate` la pone siempre aparte. La celda es ≥ 4 mm, la grilla está centrada y el bbox queda dentro del área útil.

- [ ] **T17 — Celda chica y sugerencias.** `CeldaDemasiadoChicaError` con las 3 sugerencias de design §7.5, más el mensaje en español.
  - Cubre: RF4.6, RF4.6a y RF6.4.
  - Test (**CA7**): 60 columnas en A4 dan error y no se genera nada. Las columnas sugeridas, el papel sugerido y el personalizado sugerido dan cada uno una celda ≥ 4 mm (se verifica recalculando). El mensaje contiene "4 mm" y las tres opciones. Cuando ningún papel del registro sirve, esa sugerencia se omite.

- [ ] **T18 — Layout multi-papel.** `calcular_layouts(config, proporcion) -> dict[papel, Layout]` con la grilla fija.
  - Cubre: RF5.7 y RF5.7a.
  - Test: A4 + Letter dan las mismas cols × filas. Si un papel falla, el error lo nombra y las sugerencias sirven para ambos.

- [ ] **T19 — PDF de la plantilla.** `render_pdf`: canvas invariante, grilla, números grises y marca de blanco.
  - Cubre: RF5.5, RF7.1, RF7.1a y RF7.2.
  - Test (**CA14, CA15**): el texto extraído contiene exactamente un número por celda no vacía y ninguno extra. La cantidad de puntitos de la marca coincide con las celdas vacías (se cuentan los operadores del content stream); con `marca_blanco=False` hay 0.

- [ ] **T20 — PDF de la leyenda.** Leyenda `below` en la misma página o `separate` en su propia página, con las instrucciones en inglés (RF6.7 y RF6.8).
  - Cubre: RF6.1–RF6.8 y RF7.6.
  - Test (**CA5, CA6**): con `below` (si entra) hay 1 página de plantilla y su texto incluye "Draw the symbol shown for each number". Con `below` movida o con `separate`, la leyenda está en la página 2. El texto blank aparece solo con la marca activa.

- [ ] **T21 — PDF de la solución y orden de páginas.** Un path por nivel, clip y grilla tenue opcional.
  - Cubre: RF7.4 y RF7.5.
  - Test: la cantidad de páginas es la esperada para cada combinación (leyenda × solución). La solución no tiene números ni puntitos de marca.

- [ ] **T22 — Dimensiones y márgenes del PDF.** Verificación integral para cada papel y orientación.
  - Cubre: RF5.1 y RF5.4.
  - Test (**CA4**): el MediaBox es correcto (±0,01 pt) para A4, LETTER, A3, TABLOID y CUSTOM, tanto vertical como horizontal. Las coordenadas extremas de los operadores de dibujo quedan dentro de los márgenes.

- [ ] **T23 — Render PNG.** `render_png`: composición por tiles de la solución y la plantilla, con el lado largo configurable.
  - Cubre: RF5.6.
  - Test: las dimensiones son correctas y la salida es determinista byte a byte. Una celda de nivel N es negra y una de nivel 0 blanca en la solución.

- [ ] **T24 — Pipeline.** `generar_mosaico`, `generar_preview`, `empaquetar_zip` y la nomenclatura de archivos.
  - Cubre: RF5.7, RF5.8 y RNF3.
  - Test (**CA8, CA12**): dos corridas dan PDF, PNG y ZIP idénticos (con quantiles y con kmeans). En un subproceso, importar y ejecutar `pipeline` no deja a `streamlit` en `sys.modules`. Los nombres siguen RF5.8.

- [ ] **T25 — Rendimiento.** Marker `slow` en pyproject.
  - Cubre: RNF1.
  - Test (**CA13**): 100 × 140 en un papel CUSTOM de 430 × 600 mm (preprocesamiento + cuantización + PDF) tarda < 5 s.

> 🛑 **Checkpoint C.** Muestro PDFs de ejemplo con la foto sintética en A4 y Letter, con la leyenda debajo y aparte, más el PNG.

---

## Bloque D — UI

- [ ] **T26 — UI: controles y preview.** La barra lateral con todos los controles de RF8.2, la carga de la imagen, `generar_preview` cacheado, tabs (Resultado / Plantilla / Distribución), el histograma y los avisos.
  - Cubre: RF8.1–RF8.4 y RF8.6.
  - Test: `test_ui.py` con `streamlit.testing.v1.AppTest`. La app arranca sin errores y sin imagen muestra una indicación. Con una imagen inyectada aparecen las tabs y el histograma. Una config con celda chica muestra el error en español.

- [ ] **T27 — UI: sugerencia con un clic y descargas.** El botón "Usar N columnas", "Generar PDF" y la descarga del PDF, el ZIP o el PNG.
  - Cubre: RF4.6b y RF8.5.
  - Test (AppTest): al pulsar la sugerencia cambian las columnas y desaparece el error. Después de "Generar PDF" existen los botones de descarga, y con multi-papel la descarga es un ZIP.

- [ ] **T28 — README y `.env.example` actualizados.** Uso, parámetros y recomendación de birome.
  - Test: no aplica; se revisa en el checkpoint.

> 🛑 **Checkpoint D.** Demo de la UI en el navegador integrado.

---

## Fase 5 — Verificación (después del Checkpoint D)

- [ ] **V1** — `pytest` completo, incluido `-m slow`, y `ruff check`.
- [ ] **V2** — Hojas de muestra de símbolos para N = 5, 6 y 7 (N_MAX = 7 desde el checkpoint A).
- [ ] **V3** — *(pedir al usuario: un retrato, una mascota y un paisaje)*. Para cada imagen: PDFs en A4 y Letter × leyenda `below` / `separate`, más el PNG.
- [ ] **V4** — Informe: cada CA con su estado (cumple / no cumple / parcial), observaciones visuales y ajustes propuestos.

## Trazabilidad CA → tarea

| CA | Tarea(s) |
|---|---|
| CA1 | T6 |
| CA2 | T3 |
| CA3 | T10 |
| CA4 | T22 |
| CA5 | T16, T20 |
| CA6 | T16, T20 |
| CA7 | T17 |
| CA8 | T24 (y T11, T23) |
| CA9 | T6 |
| CA10 | T12, T14 |
| CA11 | T13 |
| CA12 | T24 |
| CA13 | T25 |
| CA14 | T19 |
| CA15 | T19, T20 |
