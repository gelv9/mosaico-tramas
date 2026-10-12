# Mosaico por tramas — Diseño

> Estado: **aprobado** (Fase 2, 2026-10-11)
> Referencia: [requirements.md](requirements.md). Los IDs RF, RNF y CA remiten a ese documento.

## 1. Visión general

```
bytes de la imagen ──► imagen.py ──► grilla de luminancia (filas × cols, float 0..1)
                                         │
config (MosaicoConfig) ──► layout.py ────┤ (las filas y el recorte dependen del papel)
                                         ▼
                        cuantizacion.py ──► niveles (filas × cols, int 0..N) + Distribucion
                                         │
              simbolos/seleccion.py ─────┤ (N símbolos ordenados de claro a oscuro)
                                         ▼
                 render_pdf.py / render_png.py ──► bytes PDF, bytes PNG
                                         │
                            pipeline.py ──► Resultado (+ avisos)
                                         ▲
                                  ui/app.py (Streamlit; solo llama a pipeline)
```

**Principios:**
- **Núcleo puro.** El núcleo no importa Streamlit (RNF3).
- **Funciones puras y deterministas.** No hay ninguna fuente de aleatoriedad (RNF2). Si en el futuro se agrega alguna, tiene que usar `numpy.random.default_rng(config.semilla)`.
- **Unidades internas.** El layout trabaja en **puntos PDF** (1 pt = 1/72"), y la conversión desde mm se hace una sola vez, en el borde (`mm_a_pt`). Los símbolos usan **coordenadas normalizadas** de la celda (0–1), con el origen arriba a la izquierda y el eje y hacia abajo. El renderer de PDF invierte el eje y.

## 2. Estructura de módulos

```
src/mosaico_tramas/
├── settings.py          # (existe) entorno, pydantic-settings
├── errores.py           # jerarquía de excepciones con mensajes en español
├── avisos.py            # Aviso(codigo, mensaje) y los códigos de aviso
├── config.py            # MosaicoConfig (pydantic), enums y validaciones en español
├── papel.py             # registro de papeles + papel personalizado + orientación
├── simbolos/
│   ├── __init__.py
│   ├── primitivas.py    # Linea, Punto, Poligono (dataclasses inmutables)
│   ├── biblioteca.py    # BIBLIOTECA: tupla de Simbolo(id, familia, primitivas)
│   ├── raster.py        # rasterizar(simbolo, px, trazo) y cobertura(simbolo)
│   └── seleccion.py     # elegir_simbolos(n) -> tuple[Simbolo, ...]
├── imagen.py            # carga, EXIF, alfa, gris, recorte, suavizado, reducción, estiramiento
├── cuantizacion.py      # quantiles / kmeans / uniform, límite de oscuros, ruido, distribución
├── layout.py            # celda, filas, leyenda debajo o aparte, sugerencias ante celda chica
├── render_pdf.py        # ReportLab: plantilla, leyenda, solución (invariant=1)
├── render_png.py        # previews raster por composición de tiles (NumPy + Pillow)
├── muestra.py           # hoja de muestra de símbolos (RF2.8)
├── pipeline.py          # generar_mosaico(), generar_multi_papel() -> Resultado
└── ui/
    └── app.py           # Streamlit
```

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `errores` | `MosaicoError` (base), `ConfigInvalidaError`, `ImagenInvalidaError`, `CeldaDemasiadoChicaError` (con las `sugerencias`) | — |
| `avisos` | `Aviso` (dataclass frozen) y los códigos `LEYENDA_MOVIDA`, `NIVEL_INFRAUTILIZADO` y `POCO_RANGO_TONAL` | — |
| `config` | Validar y normalizar todos los parámetros | `papel`, `errores` |
| `papel` | `Papel(nombre, ancho_mm, alto_mm)`, `REGISTRO_PAPELES`, `papel_personalizado()` y `orientar()` | `errores` |
| `simbolos.*` | Geometría, medición de cobertura y selección del subconjunto | NumPy, OpenCV |
| `imagen` | De bytes a una grilla de luminancia | Pillow, OpenCV, NumPy |
| `cuantizacion` | De luminancia a niveles, y la distribución | NumPy, scikit-image (`label`) |
| `layout` | Geometría de las páginas, decisión sobre la leyenda y errores de celda chica | `papel`, `config` |
| `render_pdf` | Dibujar las páginas | ReportLab, `simbolos`, `layout` |
| `render_png` | Previews raster | `simbolos.raster`, Pillow |
| `pipeline` | Orquestar y juntar avisos | todo lo anterior |

## 3. Modelo de configuración

```python
class MetodoCuantizacion(StrEnum):
    QUANTILES = "quantiles"
    KMEANS = "kmeans"
    UNIFORM = "uniform"


class Orientacion(StrEnum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    AUTO = "auto"


class Recorte(StrEnum):
    FIT = "fit"
    CENTER = "center"


class UbicacionLeyenda(StrEnum):
    BELOW = "below"
    SEPARATE = "separate"


class PapelPersonalizado(BaseModel, frozen=True):
    ancho_mm: float  # 100..1200
    alto_mm: float  # 100..1200


class MosaicoConfig(BaseModel, frozen=True):
    n_simbolos: int = 6  # 5..6 (RF1)
    columnas: int = 40  # 10..200 (RF4.1)
    metodo: MetodoCuantizacion = QUANTILES
    reduccion_ruido: bool = True
    umbral_ruido: int = 2  # 2..20 (RF3.4)
    limitar_oscuros: bool = True
    max_oscuros_pct: float = 8.0  # 1..100 (RF3.5)
    papeles: tuple[str, ...] = ("A4",)  # claves de REGISTRO_PAPELES o "CUSTOM"; 1 o más
    papel_personalizado: PapelPersonalizado | None = None  # obligatorio si "CUSTOM" está en papeles
    orientacion: Orientacion = AUTO
    margen_mm: float = 12.7  # 5..40
    recorte: Recorte = FIT
    leyenda: UbicacionLeyenda = BELOW
    incluir_solucion: bool = True
    marca_blanco: bool = True  # RF7.1a
    grilla_en_solucion: bool = False  # Q9
    percentil_bajo: float = 2.0  # RP4; 0..49
    percentil_alto: float = 98.0  # RP4; 51..100
    png_lado_px: int = 2000  # 500..6000
```

**Mensajes en español.** Pydantic genera sus mensajes en inglés, así que los rangos **no** se declaran con `Field(ge=…)`. Cada campo con restricciones tiene un `field_validator(mode="before")` que valida el tipo y el rango, y lanza `ValueError` con el texto en español. Además, `MosaicoConfig.crear(**kwargs)` envuelve la `ValidationError` en una `ConfigInvalidaError` cuyo mensaje lista solo los textos en español. Por ejemplo, para RF1.3: *"La cantidad de símbolos debe ser un entero entre 5 y 10 (valor recibido: 4)."* Los valores `bool` y los `float` no enteros se rechazan en `n_simbolos`.

**Validaciones cruzadas** (`model_validator(mode="after")`): `percentil_bajo < percentil_alto`; si `"CUSTOM"` está en `papeles`, hace falta `papel_personalizado`; `papeles` no puede tener duplicados.

## 4. Biblioteca de símbolos

### 4.1 Primitivas

```python
@dataclass(frozen=True) class Linea:    p0: tuple[float, float]; p1: tuple[float, float]   # trazo con extremos planos (butt)
@dataclass(frozen=True) class Punto:    radio: float                                      # centrado
@dataclass(frozen=True) class Poligono: vertices: tuple[tuple[float, float], ...]         # relleno
@dataclass(frozen=True) class Simbolo:  id: str; familia: str; primitivas: tuple[Primitiva, ...]; nombre_en: str
```

- **Grosor del trazo:** `TRAZO_REL = 0.07` × el lado de la celda. Equivale a 0,35 mm en una celda de 5 mm (la referencia de RF2.3). Escala con la celda (Q2).
- **Medición de la cobertura (RF2.3):** rasterizado con OpenCV a 1000 × 1000 px, antialiasing y recorte a la celda; la cobertura es la media de la tinta. Se calcula una vez y se cachea con `lru_cache`. Ningún valor se carga a mano.
- **Un solo origen de la geometría.** Las primitivas son la única fuente: tanto ReportLab como OpenCV dibujan a partir de ellas, así que la cobertura medida y lo que se imprime coinciden.

### 4.2 Catálogo (16 candidatos en 9 familias: solo rayas, punto y celda llena)

Las líneas van de borde a borde de la celda y con **espaciado parejo también entre celdas vecinas**, para que en zonas parejas formen un tramado continuo, como en un grabado. Esto lo verifica un test geométrico (ver la corrección durante la T7).

| id | familia | boceto | trazos | cobertura |
|---|---|---|---|---|
| `punto` | punto | `·····` `·····` `··●··` `·····` `·····` | 1 | **2,0 %** |
| `diag1` | diagonal | `/` de esquina a esquina | 1 | 9,9 % |
| `diag2` | diagonal | `///` doble densidad (x+y = ½, 1, 3⁄2) | 3 | 19,7 % |
| `diag3` | diagonal | triple densidad (x+y = ⅓ … 5⁄3) | 5 | 29,5 % |
| `horiz1` | horizontal | `—` al centro | 1 | 7,1 % |
| `horiz2` | horizontal | `=` (a ¼ y ¾) | 2 | 14,3 % |
| `horiz3` | horizontal | `≡` (a ⅙, ½ y ⅚) | 3 | 21,4 % |
| `vert1` | vertical | `│` al centro | 1 | 7,1 % |
| `cruz` | cruz | `+` | 2 | 13,8 % |
| `aspa1` | aspa | `X` de esquina a esquina | 2 | 19,3 % |
| `aspa2` | aspa | `diag2` + una `\` central | 4 | 28,1 % |
| `aspa3` | aspa | trama cruzada densa: 3 `/` + 3 `\` | 6 | 36,5 % |
| `reja1` | reja | `#` (a ¼ y ¾) | 4 | 26,5 % |
| `reja2` | reja | reja densa (a ⅙, ½ y ⅚) | 6 | 38,2 % |
| `asterisco` | asterisco | `+` + `X` | 4 | 31,6 % |
| `lleno` | lleno | celda rellena | 1 | **100 %** |

Todos los símbolos cumplen RF2.6 y RF2.6a: solo rectas, el punto central y la celda llena, como máximo 6 trazos. *Checkpoint A:* se quitaron los rellenos parciales (bloque, triángulos, tres cuartos, esquina, mitad), porque repetidos se leían como mosaico geométrico y no como tramado a pluma.

### 4.3 Enmienda a RF2.4c (distinción de forma) — aprobada

Con el prototipo comprobé que la regla aprobada, **1 − IoU ≥ 0,35**, es **infactible** para los símbolos oscuros. Si dos símbolos tienen una cobertura ≥ 65 % y uno está "contenido" en el otro (por ejemplo, `tres_cuartos` dentro de `lleno`), el IoU es igual a la razón de sus coberturas: 75/100 = 0,75, es decir, una disimilitud de 0,25. Como el nivel N es siempre `lleno`, ningún símbolo de más de 65 % podría convivir con él, y N = 10 se volvería imposible.

**Propuesta de reemplazo:** cada símbolo declara su **familia visual** en la biblioteca (columna `familia`), y **un subconjunto no puede tener dos símbolos de la misma familia**. Así, `/`, `//` y `///` nunca aparecen juntos, y lo mismo pasa con `X` y `XX`. Es un criterio más fuerte para la vista humana (que no confunda formas parecidas) y siempre se puede verificar. CA9 pasa a decir: *"los símbolos elegidos para cada N pertenecen a familias distintas"*.

### 4.4 Algoritmo de selección del subconjunto (RF2.4 y RF2.5)

```
entrada: N (5..6)
fijos:   nivel 1 = punto, nivel N = lleno           (RF2.4e, RF2.4d)
candidatos = biblioteca − {punto, lleno}, ordenados por (cobertura, id)
para cada combinación C de N−2 candidatos:          # como mucho C(14,4) = 1001; se poda por familia y gaps
    si hay familias repetidas en C → descartar
    secuencia = [punto, *C ordenada por cobertura, lleno]
    gaps = diferencias consecutivas de cobertura
    si cobertura(punto) − 0 < 1,5 o min(gaps) < 6 → descartar
    clave = (min(gaps), −total_trazos, ids)          # 1) máximo contraste  2) más fácil de dibujar  3) desempate estable
elegir la mejor clave; si no hay ninguna → ErrorBibliotecaSimbolos (RF2.7)
```

- La búsqueda es por backtracking sobre la lista ordenada y poda en cuanto un gap queda por debajo de 6 o se repite una familia. Tarda milisegundos y el resultado se cachea por N.
- Resultado del prototipo, con N : gap mínimo → símbolos:

| N | gap mín. | niveles 1…N (resultado real de `elegir_simbolos`) |
|---|---|---|
| 5 | 10,2 | punto 2 · cruz 14 · aspa2 28 · reja2 38 · lleno 100 |
| 6 | 7,6 | punto 2 · cruz 14 · horiz3 21 · diag3 29 · reja2 38 · lleno 100 |

## 5. Preprocesamiento (`imagen.py`)

1. **Carga** con Pillow: `ImageOps.exif_transpose`. Si la imagen tiene alfa, se compone sobre fondo blanco. Después se pasa a `L` (luminancia ITU-R 601) y a float32 en el rango 0..1. Si falla, o si se supera el tamaño máximo, se lanza `ImagenInvalidaError` (RP5).
2. **Recorte.** Con `fit` no se recorta. Con `center`, se recorta al centro con la proporción `filas/cols` que define el layout (§7).
3. **Suavizado.** `cv2.GaussianBlur` con σ = 0,35 × (ancho de la imagen / columnas), con un mínimo de 0, para evitar aliasing (RP2).
4. **Reducción** con `cv2.resize(..., INTER_AREA)` a cols × filas (RP3).
5. **Estiramiento de contraste:** `p_lo, p_hi = percentile(lum, [2, 98])`, y luego `lum = clip((lum − p_lo)/(p_hi − p_lo), 0, 1)` (RP4). Si `p_hi − p_lo < 0,02`, se emite el aviso `POCO_RANGO_TONAL` y se omite el estiramiento (RP6).
6. Se trabaja con la **oscuridad** `d = 1 − lum`: más alto significa más oscuro, igual que el nivel.

## 6. Cuantización (`cuantizacion.py`)

Todos los métodos devuelven **cortes** `c_1 < … < c_N` sobre la oscuridad, y el nivel se calcula como `nivel = searchsorted(cortes, d, side="right")` (de 0 a N). Las celdas con el mismo valor siempre caen en el mismo nivel, así que un fondo plano no se "desparrama" en varios niveles.

### 6.1 `quantiles` (por defecto)
- Se arma un histograma de **4096 bins** de `d` y su acumulado `F`.
- **Cuotas objetivo.** Sin límite de oscuros, cada nivel recibe `1/(N+1)`. **Con el límite activo**, el nivel N recibe `min(1/(N+1), L)` y lo que sobra se reparte en partes iguales entre los niveles 0…N−1. Así, el exceso no recarga el nivel N−1. Esto es importante porque con N ≤ 11 la cuota ideal (≥ 9 %) siempre supera el 8 % por defecto.
- **Corte k.** Es el borde de bin donde `F` queda más cerca del acumulado objetivo, con la condición de ser estrictamente mayor que el corte k−1. Si hay empates en el histograma, se elige el borde más bajo.
- Si un empate masivo hace imposible separar dos niveles (por ejemplo, un fondo blanco puro que ocupa el 40 %), el nivel afectado queda chico. Ese caso lo detecta RF3.7 y emite el aviso. Esto cumple RF3.3: no se parte un valor idéntico entre niveles, porque eso agregaría ruido.

### 6.2 `kmeans`
- Es k-means 1D con k = N + 1 sobre el **histograma ponderado**, no sobre las celdas, así que el costo no depende del tamaño de la grilla.
- **Inicialización:** los centros parten de los cortes por cuantiles (§6.1, sin límite), así que es determinística y no usa semilla. Se itera Lloyd hasta converger (con un cambio < 1e-6) o hasta 100 iteraciones.
- **Cluster vacío:** se re-siembra en el bin de mayor error cuadrático, con desempate por el índice más bajo.
- **Cortes:** los puntos medios entre centros ordenados. Después, si el límite de oscuros está activo, se aplica como post-paso (§6.4).

### 6.3 `uniform`
- Cortes equiespaciados en (0, 1]: `c_k = k/(N+1)`. Es igual al prototipo y sirve para comparar. El límite de oscuros también se aplica como post-paso.

### 6.4 Límite de oscuros (post-paso)
- Si `count(nivel N) > floor(L·total)`, las celdas de nivel N se ordenan por `(d desc, índice asc)`, se conservan las primeras `floor(L·total)` y el resto pasa a N−1. Para `quantiles` normalmente no hace nada (ya se respetó en las cuotas), pero se aplica igual por seguridad, porque la reducción de ruido puede volver a superar el límite.

### 6.5 Reducción de ruido (RF3.4)
```
repetir hasta 3 pasadas o hasta que no haya cambios:
    para cada nivel v (0..N):
        comps = skimage.measure.label(niveles == v, connectivity=2)
        por cada componente con tamaño < umbral:
            vecinos = dilatación 3×3 del componente − el componente
            nuevo = moda de niveles[vecinos]; empate → el más cercano a v; empate → el menor
            se registra el cambio (todos se aplican juntos al final de la pasada)
```
Con el umbral por defecto (2) solo se eliminan las celdas sueltas. Si después la reducción vuelve a superar el límite de oscuros, se aplica de nuevo §6.4 (RF3.8).

### 6.6 Distribución (RF3.6 y RF3.7)
`Distribucion(conteos: tuple[int, ...], porcentajes: tuple[float, ...])`. Se emite el aviso `NIVEL_INFRAUTILIZADO` para cada nivel con `pct < 0,5 · 100/(N+1)`, **salvo** el nivel N cuando su cuota fue recortada a propósito por el límite de oscuros.

## 7. Layout (`layout.py`)

### 7.1 Papel y orientación
- Las entradas de `REGISTRO_PAPELES` son: `A4 (210 × 297)`, `LETTER (215,9 × 279,4)`, `A3 (297 × 420)` y `TABLOID (279,4 × 431,8)`, más `CUSTOM` a partir de la config. Para sumar un papel alcanza con agregar una línea.
- `auto` → `landscape` si `ancho_img > alto_img` (después del EXIF); `portrait` en cualquier otro caso.
- Área útil: `(W − 2m, H − 2m)` en pt.

### 7.2 Bloque de leyenda
Es un bloque de alto fijo, calculable antes de dibujar:
- Línea de instrucción: 9 pt + 4 pt de interlineado.
- Entradas: una por nivel 1…N, y una más para la celda vacía si `marca_blanco` está activa. Cada entrada mide **32 mm × 14 mm** y contiene el número (10 pt), el símbolo a escala real (el lado de la celda) y el símbolo ampliado (10 mm).
- Entradas por fila: `floor(ancho_util / 32 mm)`, por lo que en A4 vertical entran 5. La cantidad de filas es `ceil(entradas / por_fila)`.
- `alto_leyenda = 6 mm (separación) + 4,6 mm (instrucción) + filas × 14 mm`. Por ejemplo, con N = 6 y la marca de blanco en A4 vertical: 7 entradas en 2 filas ≈ 38,6 mm.
- Como el símbolo a escala real depende de la celda, se calcula después de fijarla. El alto de la entrada usa el máximo de los dos tamaños (10 mm), así que no hay dependencia circular.

### 7.3 Algoritmo
```
def calcular_layout(config, proporcion_img, papel) -> Layout:
    orient   = resolver(config.orientacion, proporcion_img)
    uw, uh   = area_util(papel, orient, margen)
    leg_h    = alto_leyenda(N, marca_blanco, uw)
    filas    = filas_para(config, proporcion_img, uw, uh − leg_h si BELOW sino uh)
               # FIT: round(cols · alto_img/ancho_img); CENTER: round(cols · alto_disp/uw)
    celda_full = min(uw/cols, uh/filas)
    si celda_full < 4 mm → raise CeldaDemasiadoChicaError(sugerencias(...))      # RF4.6a / RF6.4
    si leyenda == BELOW:
        celda_leg = min(uw/cols, (uh − leg_h)/filas)
        si celda_leg ≥ 4 mm → leyenda en la misma página, celda = celda_leg
        si no → leyenda en página aparte + aviso LEYENDA_MOVIDA, celda = celda_full  (RF6.3)
                (con CENTER se recalculan las filas usando el área completa, porque cambia la proporción)
    si no → página aparte, celda = celda_full                                    (RF6.5)
    origen = centrado dentro del área asignada a la grilla (RF4.7)
    return Layout(papel, orient, celda_pt, cols, filas, origen, leyenda_en, rect_leyenda, páginas)
```

### 7.4 Multi-papel (RF5.7)
La grilla (cols × filas) se fija **una sola vez**: con `fit`, a partir de la imagen; con `center`, a partir del primer papel de la lista (Q5). Después se calcula `calcular_layout` para cada papel con esas filas fijas. Si alguno da error, se lanza `CeldaDemasiadoChicaError` nombrando ese papel y con sugerencias que sirven para **todos** (RF5.7a).

### 7.5 Sugerencias ante una celda chica (RF4.6a)
1. **Columnas máximas:** el mayor `c` en `[10, cols)` tal que `celda(c) ≥ 4 mm` con el papel, la orientación, los márgenes y la ubicación de la leyenda actuales. Se busca de forma descendente, porque las filas dependen de `c`. En multi-papel, es el mínimo entre los papeles.
2. **Papel del registro:** el de menor área que admite `cols`, probando las dos orientaciones si la orientación es `auto`. Si ninguno sirve, se omite.
3. **Papel personalizado:** `ancho = ceil(cols·4 + 2m)` y `alto = ceil(filas·4 + 2m (+ leg_h si BELOW))`, en mm. Si se pasa de 1200 mm, se omite y se sugiere bajar las columnas.

Ejemplo de mensaje: *"Con 60 columnas en A4 vertical las celdas miden 3,1 mm (mínimo 4 mm). Opciones: usar hasta 46 columnas, usar papel A3, o un papel personalizado de 266 × 372 mm."*

## 8. Render del PDF (`render_pdf.py`)

- `canvas.Canvas(buffer, pagesize=…, invariant=1, pageCompression=1)`. Los metadatos son fijos (título "Hatch Mosaic", sin fecha), así que el PDF sale idéntico byte a byte (RNF2).
- **Plantilla (RF7.1, RF7.1a, RF7.2):**
  - Grilla: `cols+1` líneas verticales y `filas+1` horizontales, de 0,3 pt y gris al 35 %.
  - Números: `drawCentredString` en Helvetica, con un tamaño de `max(4 pt, 0,45 · celda)` y gris al 50 %, centrados en vertical con un ajuste según la altura de la x.
  - Marca de blanco: `circle` relleno de radio `max(0,15 mm, 0,04 · celda)`, en el gris de la grilla.
- **Leyenda:** la instrucción en inglés (RF6.7), y para cada entrada el número, el recuadro a escala real con el símbolo y el recuadro de 10 mm con el símbolo. Si la marca de blanco está activa, se agrega una entrada "blank" con el texto de RF6.8.
- **Solución (RF7.4):** se agrupan las celdas por nivel. Para cada nivel se construye **un solo path** con las primitivas trasladadas a todas sus celdas: un path de líneas, con `lineWidth = 0,07 · celda` y extremos planos, y un path de rellenos. Esto reduce la cantidad de operaciones a ~2·N paths, lo que es clave para RNF1. Todo se recorta (`clipPath`) al rectángulo de la grilla. La grilla tenue solo se dibuja si `grilla_en_solucion` está activa.
- **Orden de las páginas:** plantilla → leyenda (si va aparte) → solución (RF7.5).
- Todo el texto del PDF va en inglés (RF7.6).

## 9. Render PNG (`render_png.py`)

- **Composición por tiles:** cada símbolo, cada número y la marca de blanco se rasterizan **una sola vez** a `t × t` px, con `t = png_lado_px // max(cols, filas)`. Después se compone con NumPy, `tiles[niveles]`, y un reshape a `(filas·t, cols·t)`. Para 100 × 140 esto toma milisegundos.
- Se generan dos PNG, la solución y la plantilla. Se guardan con Pillow, `optimize=False` y sin metadatos de tiempo, así que son deterministas.

## 10. Pipeline (`pipeline.py`)

```python
@dataclass(frozen=True)
class Resultado:
    niveles: np.ndarray                 # (filas, cols) uint8
    simbolos: tuple[Simbolo, ...]       # niveles 1..N
    distribucion: Distribucion
    layouts: dict[str, Layout]          # por papel
    pdfs: dict[str, bytes]              # por papel
    png_solucion: bytes
    png_plantilla: bytes
    avisos: tuple[Aviso, ...]

def generar_mosaico(imagen: bytes, config: MosaicoConfig, *, con_pdf: bool = True) -> Resultado
def generar_preview(imagen: bytes, config: MosaicoConfig) -> Resultado   # con_pdf=False, PNG chico
def empaquetar_zip(resultado: Resultado, nombre_base: str) -> bytes        # RF5.7 y RF5.8
```

`generar_preview` es la variante rápida para la UI: no genera el PDF y el PNG sale a 1200 px.

## 11. Hoja de muestra (`muestra.py`, RF2.8)

`hoja_muestra(n: int | None) -> bytes` genera un PDF A4. Con un `n`, muestra los N símbolos elegidos con su número, su cobertura medida, una celda a 5 mm (escala de referencia) y otra a 20 mm. Con `None`, muestra la biblioteca completa agrupada por familia. Se usa en la Fase 5 con N = 5 y 6.

## 12. Flujo de la UI (`ui/app.py`)

```
┌ Sidebar ─────────────────────────┐  ┌ Principal ──────────────────────────────────┐
│ Imagen (JPG/PNG)                 │  │ [avisos / errores en español]                │
│ Símbolos  [5 ── 7 ── 10]         │  │ ┌ Tabs: Resultado | Plantilla | Distribución ┐│
│ Columnas  [40]                   │  │ │ PNG preview                                ││
│ Método    (quantiles|kmeans|unif)│  │ │ histograma (st.bar_chart) por nivel, con   ││
│ Ruido     [x] umbral [2]         │  │ │ la línea del 50 % de la cuota ideal        ││
│ Oscuros   [x] máx % [8]          │  │ └────────────────────────────────────────────┘│
│ Papel(es) [A4, Letter, ... ]     │  │ Grilla 40×56 · celda 4,6 mm · leyenda debajo │
│  └ personalizado: ancho/alto mm  │  │ [Generar PDF]  →  [⬇ PDF / ZIP] [⬇ PNG]      │
│ Orientación · Márgenes · Recorte │  └──────────────────────────────────────────────┘
│ Leyenda (debajo|aparte)          │
│ [x] Solución [x] Marca de blanco │
└──────────────────────────────────┘
```

1. Cada cambio de un control recalcula `generar_preview` (con `st.cache_data`, usando como clave el hash de los bytes y el JSON de la config).
2. Si salta `CeldaDemasiadoChicaError`, se muestra `st.error` con las sugerencias y un botón **"Usar N columnas"**, que actualiza `st.session_state["columnas"]` y re-ejecuta la app (RF4.6b).
3. El botón **Generar PDF** llama a `generar_mosaico` (cacheado) y habilita las descargas: el PDF si hay un solo papel, o un ZIP si hay varios, más el PNG.
4. Si la configuración es inválida (`ConfigInvalidaError`), se muestra el mensaje en español. La UI igual acota los widgets a los rangos válidos.

## 13. Estrategia de tests

| Área | Tests | CA |
|---|---|---|
| config | rangos, tipos y mensajes exactos en español | CA2 |
| símbolos | coberturas crecientes, gaps, extremos fijos, familias distintas, ≤ 6 trazos, ≥ 14 candidatos | CA1, CA9 |
| cuantización | equi-reparto en un degradado sintético y en una "foto" sintética (degradado + formas + ruido con semilla), límite de oscuros, ruido sin celdas sueltas, empates | CA3, CA10, CA11 |
| layout | celda ≥ 4 mm o error; las sugerencias son válidas; leyenda debajo o movida; multi-papel | CA5, CA6, CA7 |
| PDF | MediaBox por papel y orientación (pypdf); cantidad de páginas; texto extraído (sin números en las celdas vacías); contenido dentro de los márgenes (bbox de los operadores) | CA4, CA14, CA15 |
| determinismo | dos corridas dan bytes iguales (PDF y PNG, quantiles y kmeans) | CA8 |
| arquitectura | importar `pipeline` no carga `streamlit` (subproceso) | CA12 |
| rendimiento | 100 × 140, papel CUSTOM de 430 × 600, < 5 s (`@pytest.mark.slow`) | CA13 |

**"Contenido dentro de los márgenes" (CA4).** El renderer expone `Layout.bbox_contenido()`, y el test verifica que esté contenido en el área útil. Además, se hace un chequeo independiente: se parsean los operadores del content stream con pypdf para obtener las coordenadas extremas.

## 14. Decisiones y riesgos

| Tema | Decisión / mitigación |
|---|---|
| Distinción de forma | Se reemplaza 1−IoU por familias distintas (§4.3). Aprobado. |
| Sin scikit-learn | El k-means 1D sobre el histograma es propio, exacto y determinista. |
| Rendimiento del PDF | Un path por nivel en la solución; la grilla con líneas largas y no con rectángulos por celda. |
| Escala de la cobertura | Se mide con un trazo relativo (0,07). En celdas más grandes, la birome del comprador cubre proporcionalmente menos y los tonos se aclaran algo. Por eso se recomienda un fineliner de 0,3–0,5 mm. Esto se puede documentar en el listing. |
| Tiempo de rasterizado de la cobertura | 16 símbolos a 1000 px, ~50 ms en total, una sola vez (cacheado). |
