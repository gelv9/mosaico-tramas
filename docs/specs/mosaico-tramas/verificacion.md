# Mosaico por tramas — Verificación (Fase 5)

> Fecha: 2026-10-11 · Código verificado: `main` con el estilo clásico y la grilla al 18 %.
> Salidas de verificación en `output/verificacion/` (fuera de git).

## 1. Qué se corrió

| Paso | Resultado |
|---|---|
| **V1** — `pytest` completo (con el test `slow`) | **275 tests en verde** en 26 s. Cobertura del núcleo: 94–100 % por módulo, 88 % total. La UI figura con 0 % porque `AppTest` ejecuta el script en otro contexto que coverage no registra, pero tiene 10 tests propios. |
| **V1** — `ruff check` y `ruff format --check` | Sin errores; 42 archivos formateados. |
| **V2** — Hoja de muestra | `muestra_estilo_clasico.pdf`: los 6 símbolos con su cobertura medida, a 4 mm, a 20 mm y en un parche de 5 × 5. |
| **V3** — PDFs con fotos reales | 3 fotos × 2 papeles (A4 y Letter) × 2 ubicaciones de leyenda = **12 PDFs**, más los PNG y los ZIP. Cada caso se chequeó automáticamente (tabla 2). |

## 2. Resultados con las fotos del usuario

| Caso | Grilla | Celda | Páginas | Leyenda en | Medidas | Márgenes | Determinista | Nivel mínimo (≥ 7,1 %) | Celdas llenas |
|---|---|---|---|---|---|---|---|---|---|
| perro · A4 · debajo | 54×36 (horizontal) | 4,44 mm | 2 | pág. 1 | ✅ | ✅ | ✅ | 14,9 % | 8,0 % |
| perro · Letter · debajo | 54×36 | 4,61 mm | 2 | pág. 1 | ✅ | ✅ | ✅ | 14,9 % | 8,0 % |
| perro · A4 · aparte | 54×36 | 5,03 mm | 3 | pág. 2 | ✅ | ✅ | ✅ | 14,9 % | 8,0 % |
| perro · Letter · aparte | 54×36 | 4,70 mm | 3 | pág. 2 | ✅ | ✅ | ✅ | 14,9 % | 8,0 % |
| retrato · A4 · debajo | 32×57 (vertical) | 4,09 mm | 2 | pág. 1 | ✅ | ✅ | ✅ | 14,9 % | 7,9 % |
| retrato · Letter · debajo | 32×57 | 4,46 mm | 3 | **pág. 2 (movida, con aviso)** | ✅ | ✅ | ✅ | 14,9 % | 7,9 % |
| retrato · A4 · aparte | 32×57 | 4,76 mm | 3 | pág. 2 | ✅ | ✅ | ✅ | 14,9 % | 7,9 % |
| retrato · Letter · aparte | 32×57 | 4,46 mm | 3 | pág. 2 | ✅ | ✅ | ✅ | 14,9 % | 7,9 % |
| interior · A4 · debajo | 45×45 | 4,10 mm | 2 | pág. 1 | ✅ | ✅ | ✅ | 14,6 % | 8,0 % |
| interior · Letter · debajo | 45×45 | 4,23 mm | 2 | pág. 1 | ✅ | ✅ | ✅ | 14,6 % | 8,0 % |
| interior · A4 · aparte | 45×45 | 4,10 mm | 3 | pág. 2 | ✅ | ✅ | ✅ | 14,6 % | 8,0 % |
| interior · Letter · aparte | 45×45 | 4,23 mm | 3 | pág. 2 | ✅ | ✅ | ✅ | 14,6 % | 8,0 % |

Cada generación (los dos papeles juntos) tardó entre 0,14 y 0,49 s.

## 3. Criterios de aceptación

Los criterios CA1 a CA8 son los del pedido original; CA9 a CA16 se agregaron durante la especificación.

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| CA1 | Orden y coberturas de los símbolos | ✅ Cumple **la versión enmendada** · ⚠️ ver §4 | `test_seleccion.py` |
| CA2 | Cantidad de símbolos inválida → error en español | ✅ | `test_config.py` (9 casos) |
| CA3 | Con cuantiles, ningún nivel < 50 % de la cuota ideal | ✅ | `test_cuantizacion.py`; en las fotos reales el mínimo es 14,6 % (el umbral es 7,1 %) |
| CA4 | Medidas del PDF por papel y contenido dentro de los márgenes | ✅ | `test_ca4_*` (4 papeles × 2 orientaciones + personalizado); 12/12 casos reales |
| CA5 | Leyenda debajo: en la plantilla si entra, aparte con aviso si no | ✅ | `test_ca5_*`; el retrato en Letter lo mostró con datos reales |
| CA6 | Leyenda aparte → siempre en su propia página | ✅ | `test_ca6_*`; 6/6 casos reales |
| CA7 | Celda < 4 mm → aviso con sugerencia | ✅ **Endurecido**: no se genera nada y hay 3 sugerencias que funcionan | `test_ca7_*`; demo en vivo en la UI (80 columnas → 67) |
| CA8 | Salida determinista | ✅ | `test_ca8_*` (PDF, PNG y ZIP; cuantiles y k-means); 12/12 casos reales |
| CA9 | Regla física de dibujo y tramado continuo | ✅ | `test_biblioteca.py` (geométrico) |
| CA10 | Límite de celdas llenas, también después del ruido | ✅ | `test_ca10_*`; en las fotos reales, 7,9–8,0 % |
| CA11 | Sin celdas sueltas con la reducción de ruido | ✅ | `test_ca11_*` |
| CA12 | El núcleo no importa Streamlit | ✅ | `test_ca12_*` (subproceso) |
| CA13 | 100 × 140 en menos de 5 s | ✅ | `test_ca13_*` tarda ~1,4 s con calentamiento incluido |
| CA14 | Celdas vacías sin número | ✅ | `test_ca14_*` (cuenta los `Tj` dentro de la grilla) |
| CA15 | Marca tenue solo en las celdas vacías de la plantilla | ✅ | `test_ca15_*` |
| CA16 | Estilo de grilla: líneas o puntos | ✅ | `test_ca16_*` |

## 4. Qué **no** cumple el pedido original (por decisión)

Estas diferencias son conscientes y están registradas como enmiendas en `requirements.md`:

1. **RF1, cantidad de símbolos configurable de 5 al máximo → ahora es fija en 6.** El estilo clásico de la referencia reemplazó a la selección automática (checkpoint D).
2. **RF2, densidad estrictamente creciente con diferencia mínima y formas distintas → no se cumple entre los niveles 2 y 3.** La / y la \ comparten tono a propósito, como en la referencia. Cuesta un tono de la escala: hay 5 tonos distintos más una variación de dirección.
3. **RF4.6, celda chica → aviso.** Se endureció a "no se genera" por pedido del usuario (4 mm es lo mínimo visible).
4. **El primer diseño de la biblioteca** (23 símbolos, después 10, después la selección automática) quedó como historia en `design.md`. Las iteraciones salieron de mirar hojas impresas y fotos reales.

## 5. Observaciones y ajustes que propongo

| # | Observación | Ajuste propuesto | Esfuerzo |
|---|---|---|---|
| 1 | Con la leyenda debajo queda un **hueco grande** entre la grilla y la leyenda, porque la grilla se centra en el área y la leyenda va al pie. | Pegar la leyenda debajo de la grilla, a 6 mm, y centrar el bloque completo (grilla + leyenda). | Bajo |
| 2 | **Laberinto de / y \.** Donde se tocan esas dos zonas aparecen zigzags que bajan la legibilidad de los medios tonos. | Elegir / o \ según la **dirección del contorno local** (gradiente de la imagen) en vez de usarlas como dos niveles de tono. Así las rayas siguen la forma, como en un grabado real, y se recupera un tono para la escala. | Medio |
| 3 | **Salto asterisco (52 %) → lleno (100 %).** Los negros quedan duros. | Dejarlo así (es el estilo de la referencia), o permitir que el límite de llenas baje por imagen. Ya es configurable; podría sugerirse según el histograma. | Bajo |
| 4 | La **marca de vacío al 18 %** casi no se ve y la referencia no la usa. | Apagarla por defecto. | Bajo |
| 5 | La referencia usa **45 columnas** en A4. | Pasar el valor por defecto de 40 a 45 (en A4 vertical da 4,1 mm). | Bajo |
| 6 | **Retratos muy verticales** en A4 dan pocas columnas (32) y quedan abstractos. | En el catálogo de Etsy, ofrecer retratos en A3/Tabloid o con recorte al centro. | — |
| 7 | **Prueba física pendiente:** la legibilidad del gris al 18 % y de los números al 50 % en impresoras hogareñas, y el tono real con fibra de 0,5 mm frente a rotulador de 0,2 mm. | Imprimir una hoja de cada papel y dibujar un parche de 10 × 10 por nivel. | — |
| 8 | Llegó una foto en **WEBP** y la app solo acepta JPG o PNG. | Aceptar WEBP (Pillow ya lo lee). | Bajo |
| 9 | `MOSAICO_OUTPUT_DIR` y `MOSAICO_LOG_LEVEL` se validan pero no se usan. | Usarlas en una futura CLI o quitarlas. | Bajo |
