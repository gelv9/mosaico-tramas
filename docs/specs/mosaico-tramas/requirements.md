# Mosaico por tramas — Requisitos

> Estado: **aprobado** (Fase 1, 2026-10-11)
> Formato: EARS. Palabras clave en inglés, contenido en español.
>
> - `THE SYSTEM SHALL …` → requisito siempre vigente (ubicuo)
> - `WHEN <evento> THE SYSTEM SHALL …` → disparado por un evento
> - `IF <condición indeseada> THEN THE SYSTEM SHALL …` → manejo de errores y casos borde
> - `WHERE <opción activa> THE SYSTEM SHALL …` → comportamiento opcional o configurable
> - `WHILE <estado> THE SYSTEM SHALL …` → mientras se cumple un estado

## 0. Glosario

| Término | Definición |
|---|---|
| **Celda vacía** | Celda que queda en blanco. No lleva número ni símbolo y **no cuenta como símbolo**. |
| **Símbolo** | Trazo vectorial que el comprador dibuja en una celda: rayas, cruces, puntos, relleno… |
| **N** | Cantidad de símbolos elegida. La imagen tiene **N + 1 tonos**: vacío y N símbolos. |
| **Nivel** | Tono cuantizado de una celda. El nivel 0 es la celda vacía, y los niveles 1…N son los símbolos, ordenados de claro a oscuro. |
| **Cobertura de tinta** | Porcentaje del área de la celda que queda negro al rasterizar el símbolo en las condiciones de referencia (§2.2). |
| **Área útil** | Página menos los márgenes. |
| **Plantilla** | Página con la grilla y los números, que el comprador completa. |
| **Leyenda** | Tabla número → símbolo, con la instrucción de uso. |
| **Solución** | Resultado terminado: cada celda dibujada con su símbolo. |

## 1. Preprocesamiento de la imagen (heredado del prototipo)

- **RP1** — WHEN se carga una imagen JPG o PNG, THE SYSTEM SHALL convertirla a escala de grises (luminancia), respetando la orientación EXIF y componiendo la transparencia sobre fondo blanco.
- **RP2** — THE SYSTEM SHALL suavizar la imagen antes de reducirla, para evitar aliasing.
- **RP3** — THE SYSTEM SHALL reducir la imagen a la grilla de columnas × filas con interpolación por promedio de área.
- **RP4** — THE SYSTEM SHALL estirar el contraste de la grilla entre los percentiles 2 y 98 de su luminancia, con percentiles configurables.
- **RP5** — IF el archivo no es una imagen válida, o supera `MOSAICO_MAX_UPLOAD_MB`, THEN THE SYSTEM SHALL rechazarlo con un mensaje en español que indique el motivo.
- **RP6** — IF la imagen es casi uniforme (p98 − p2 < 2 % del rango), THEN THE SYSTEM SHALL avisar que no tiene rango tonal suficiente y generar igual el resultado.

## 2. Requisitos funcionales

### RF1 — Cantidad de símbolos configurable

- **RF1.1** — THE SYSTEM SHALL permitir elegir N con **N_MIN = 5** y **N_MAX = 10** (valor propuesto).
- **RF1.2** — THE SYSTEM SHALL generar N + 1 niveles: la celda vacía más N símbolos. La celda vacía no se cuenta dentro de N.
- **RF1.3** — IF N < 5 o N > 10, o N no es un entero, THEN THE SYSTEM SHALL rechazar la configuración con el mensaje en español *"La cantidad de símbolos debe ser un entero entre 5 y 10 (valor recibido: X)."*

### RF2 — Biblioteca de símbolos distinguibles

- **RF2.1** — THE SYSTEM SHALL tener una biblioteca de **al menos 14 símbolos candidatos** (propuesta). Supera el mínimo de N_MAX = 10, de modo que haya margen para elegir según la forma y la densidad.
- **RF2.2** — THE SYSTEM SHALL definir cada símbolo como vector, en coordenadas normalizadas de la celda (0–1), usando solo líneas, puntos y polígonos rellenos de ReportLab. Ningún símbolo puede ser una imagen raster.
- **RF2.3** — THE SYSTEM SHALL **medir** la cobertura de tinta de cada símbolo rasterizándolo en las condiciones de referencia (propuesta: celda de 5 mm, trazo de 0,35 mm y 400 × 400 px por celda). No se aceptan coberturas cargadas a mano.
- **RF2.4** — WHEN se pide un subconjunto para N, THE SYSTEM SHALL devolver N símbolos que cumplan:
  - (a) **cobertura estrictamente creciente** del nivel 1 al nivel N;
  - (b) **diferencia mínima Δ_MIN = 6 puntos porcentuales** de cobertura entre niveles consecutivos 1…N, y **Δ_MIN_0 = 1,5 pp** entre el vacío (0 %) y el nivel 1 *(decidido, Q4a)*;
  - (c) **forma distinta**: dos símbolos elegidos no pueden compartir la misma *firma de forma* (orientaciones de los trazos + tipo de primitiva). Además, su disimilitud raster (1 − IoU de la tinta) tiene que ser ≥ **0,35** (propuesta).
  - (d) **el nivel N es siempre la celda rellena** (cobertura 100 %) *(decidido, Q3)*;
  - (e) **el nivel 1 es siempre el punto central** *(decidido, Q4a)*. Los niveles 2…N−1 los elige el algoritmo.
- **RF2.5** — WHEN hay más de un subconjunto válido, THE SYSTEM SHALL elegir el que **maximice la diferencia mínima** entre niveles consecutivos (máximo contraste perceptible). Los empates se resuelven de forma determinística.
- **RF2.6** — THE SYSTEM SHALL limitar los símbolos a lo dibujable a mano: solo trazos rectos, puntos y relleno; **como máximo 6 trazos** por símbolo, donde un relleno cuenta como un trazo, y sin curvas ni detalles de menos de 1 mm a escala de referencia.
- **RF2.7** — IF para algún N entre 5 y 10 no existe un subconjunto que cumpla RF2.4, THEN THE SYSTEM SHALL fallar con un error interno explícito. Se trata de un error de la biblioteca, no del usuario, y un test lo cubre.
- **RF2.8** — THE SYSTEM SHALL poder generar una **hoja de muestra de símbolos** para un N dado: cada símbolo con su número y su cobertura medida, a escala real y ampliada.

### RF3 — Cuantización que aprovecha todos los niveles

- **RF3.1** — THE SYSTEM SHALL ofrecer tres métodos de cuantización a N + 1 niveles:
  - `quantiles` (**por defecto**): umbrales en los cuantiles de la luminancia, de modo que cada nivel reciba ≈ 1/(N+1) de las celdas;
  - `kmeans`: k-means 1D sobre la luminancia, con k = N + 1 e inicialización y desempate determinísticos;
  - `uniform`: bins uniformes, como en el prototipo, solo para comparar.
- **RF3.2** — THE SYSTEM SHALL asignar el nivel 0 (vacío) a las celdas más claras y el nivel N a las más oscuras.
- **RF3.3** — IF hay luminancias repetidas que hacen colapsar dos cuantiles, THEN THE SYSTEM SHALL repartir los empates de forma determinística (por rango estable) para que ningún nivel quede vacío sin necesidad.
- **RF3.4** — WHERE la reducción de ruido está activa, THE SYSTEM SHALL reasignar al nivel mayoritario de sus vecinos todo componente conexo (vecindad de 8) de un mismo nivel cuyo tamaño sea **menor al umbral**. El umbral es configurable de 2 a 20 celdas y por defecto vale **2**, que elimina las celdas sueltas. Si hay empate entre vecinos, gana el nivel más cercano al original.
- **RF3.5** — WHERE el límite de oscuros está activo, THE SYSTEM SHALL asegurar que el nivel N no supere el **porcentaje máximo de celdas configurado**. El rango va de 1 % a 100 % y el valor por defecto propuesto es **8 %**. Las celdas que exceden el límite pasan al nivel N − 1, empezando por las menos oscuras.
- **RF3.6** — THE SYSTEM SHALL calcular y exponer la **distribución de celdas por nivel**: cantidad y porcentaje de cada nivel 0…N.
- **RF3.7** — IF algún nivel queda con menos del **50 % de la cuota ideal** (100/(N+1) %), THEN THE SYSTEM SHALL emitir el aviso de nivel infrautilizado, indicando el nivel y su porcentaje.
- **RF3.8** — THE SYSTEM SHALL aplicar los pasos en este orden: cuantización → límite de oscuros → reducción de ruido → verificación del límite de oscuros. Esa última verificación existe porque la reducción de ruido puede volver a superar el límite.

### RF4 — Grilla

- **RF4.1** — THE SYSTEM SHALL permitir configurar las columnas (propuesta: entre 10 y 200; por defecto **40**, que en A4 vertical da ≈ 4,6 mm por celda).
- **RF4.2** — THE SYSTEM SHALL usar celdas **cuadradas**.
- **RF4.3** — WHERE el recorte es `fit` (ajustar a la página, por defecto), THE SYSTEM SHALL conservar la imagen completa y calcular filas = round(columnas × alto / ancho).
- **RF4.4** — WHERE el recorte es `center` (recortar al centro), THE SYSTEM SHALL recortar la imagen al centro con la proporción del área disponible para la grilla, para que llene la página, y calcular las filas a partir de esa proporción.
- **RF4.5** — THE SYSTEM SHALL calcular el lado de la celda como min(ancho disponible / columnas, alto disponible / filas), donde el área disponible ya descuenta la leyenda si va debajo.
- **RF4.6** — THE SYSTEM SHALL tratar **CELDA_MIN = 4 mm** como un **límite duro**: nunca genera una plantilla con celdas de menos de 4 mm de lado *(decidido, Q1)*.
- **RF4.6a** — IF el lado de la celda calculado queda por debajo de CELDA_MIN, THEN THE SYSTEM SHALL **no generar el PDF** y devolver un error en español con tres sugerencias concretas:
  - (1) la cantidad máxima de columnas que respeta los 4 mm con el papel, la orientación y los márgenes actuales;
  - (2) el papel más chico del registro que admite las columnas pedidas, si existe alguno;
  - (3) el tamaño de papel personalizado mínimo, en mm, que las admite.
- **RF4.6b** — WHEN se muestra el error de RF4.6a en la UI, THE SYSTEM SHALL ofrecer aplicar la sugerencia (1) con un clic.
- **RF4.7** — THE SYSTEM SHALL centrar la grilla dentro del área disponible.

### RF5 — Formato de salida de impresión

- **RF5.1** — THE SYSTEM SHALL soportar los papeles A4 (595,28 × 841,89 pt), US Letter (612 × 792 pt), A3 (841,89 × 1190,55 pt) y US Tabloid (792 × 1224 pt), definidos en un **registro extensible**: sumar un papel es sumar una entrada al registro.
- **RF5.1a** — THE SYSTEM SHALL aceptar un **papel personalizado**, con ancho y alto en mm entre 100 y 1200 *(decidido, Q1)*, para las grillas grandes que no entran en los formatos estándar sin bajar de 4 mm.
- **RF5.1b** — IF el papel personalizado está fuera de rango, THEN THE SYSTEM SHALL rechazarlo con un mensaje en español que indique el rango válido.
- **RF5.2** — THE SYSTEM SHALL permitir elegir la orientación entre `portrait`, `landscape` y `auto`.
- **RF5.3** — WHERE la orientación es `auto`, THE SYSTEM SHALL usar `landscape` si el ancho de la imagen supera su alto, y `portrait` en cualquier otro caso.
- **RF5.4** — THE SYSTEM SHALL permitir márgenes configurables de 5 a 40 mm, iguales en los cuatro lados. El valor por defecto es **12,7 mm (0,5")**, seguro para impresoras hogareñas tanto en A4 como en Letter.
- **RF5.5** — THE SYSTEM SHALL generar un **PDF vectorial**: grilla, números y símbolos como vectores, con las fuentes estándar de PDF (Helvetica).
- **RF5.6** — THE SYSTEM SHALL generar un **PNG de preview** de la solución y otro de la plantilla, con el lado largo configurable (por defecto 2000 px, apto para mockups de Etsy).
- **RF5.7** — WHERE la opción multi-papel está activa, THE SYSTEM SHALL generar en un solo paso un PDF por cada papel elegido (por defecto A4 + Letter), **con la misma grilla y los mismos niveles en todos**, y ofrecerlos juntos en un ZIP.
- **RF5.7a** — IF en alguno de los papeles elegidos la celda queda por debajo de CELDA_MIN, THEN THE SYSTEM SHALL no generar ninguno y aplicar RF4.6a indicando cuál es el papel que falla. Las columnas sugeridas tienen que servir para todos los papeles.
- **RF5.8** — THE SYSTEM SHALL nombrar los archivos de forma predecible, por ejemplo `<nombre>_<papel>_<N>sym_<cols>x<filas>.pdf`.

### RF6 — Ubicación de la leyenda

- **RF6.1** — THE SYSTEM SHALL permitir elegir la ubicación de la leyenda entre `below` (debajo de la grilla, en la misma hoja; **por defecto**) y `separate` (en una hoja aparte).
- **RF6.2** — WHERE la leyenda es `below`, THE SYSTEM SHALL reservar debajo de la grilla el alto que ocupa la leyenda y recalcular la celda.
- **RF6.3** — IF con la leyenda `below` el lado de la celda queda por debajo de CELDA_MIN y sin la leyenda no, THEN THE SYSTEM SHALL mover la leyenda a una hoja aparte y avisar en español: *"La leyenda no entra debajo sin achicar las celdas por debajo de 4 mm; se movió a una hoja aparte."*
- **RF6.4** — IF la celda ya queda por debajo de CELDA_MIN sin la leyenda, THEN THE SYSTEM SHALL aplicar RF4.6a, es decir, dar error con sugerencias y no generar el PDF.
- **RF6.5** — WHERE la leyenda es `separate`, THE SYSTEM SHALL poner siempre la leyenda en su propia página, inmediatamente después de la plantilla.
- **RF6.6** — THE SYSTEM SHALL mostrar en la leyenda, ordenados de claro a oscuro, el número de cada nivel junto a su símbolo dibujado **a escala real** (el tamaño de celda de la plantilla) y **ampliado** (propuesta: ≥ 10 mm).
- **RF6.7** — THE SYSTEM SHALL incluir en la leyenda, en inglés, la instrucción *"Draw the symbol shown for each number. Leave unnumbered cells blank."*
- **RF6.8** — WHERE la marca de blanco está activa, THE SYSTEM SHALL agregar a la leyenda la muestra de la celda vacía con su puntito tenue y el texto *"Cells with a faint dot: leave blank."* *(decidido, Q4b)*.

### RF7 — Contenido del PDF

- **RF7.1** — THE SYSTEM SHALL generar la **plantilla**: la grilla completa con el número del nivel (1…N) centrado en cada celda que no esté vacía. Las celdas vacías no llevan número.
- **RF7.1a** — WHERE la marca de blanco está activa (opción, **activada por defecto**), THE SYSTEM SHALL imprimir en cada celda vacía de la plantilla un puntito centrado en el mismo gris que la grilla, con un diámetro de ≈ 8 % del lado de la celda (mínimo 0,3 mm), para indicar que se deja en blanco a propósito *(decidido, Q4b)*. En la página de solución no se imprime.
- **RF7.2** — THE SYSTEM SHALL dibujar las líneas de la grilla y los números en **gris claro**. Propuesta: líneas de 0,3 pt al 35 % de negro y números al 50 % de negro, con un tamaño de fuente de ≈ 45 % del lado de la celda (mínimo 4 pt).
- **RF7.3** — THE SYSTEM SHALL incluir la **leyenda** según RF6.
- **RF7.4** — WHERE la solución está activa (por defecto, sí), THE SYSTEM SHALL agregar una página aparte con la **solución**: cada celda con su símbolo en negro, sin números, y la grilla opcional en gris muy claro.
- **RF7.5** — THE SYSTEM SHALL ordenar las páginas así: plantilla (con la leyenda, si va debajo) → leyenda (si va aparte) → solución (si está activa).
- **RF7.6** — THE SYSTEM SHALL escribir en inglés todo el texto visible del PDF, porque el público es internacional.

### RF8 — UI en Streamlit

- **RF8.1** — THE SYSTEM SHALL permitir subir una imagen JPG o PNG.
- **RF8.2** — THE SYSTEM SHALL ofrecer controles para: cantidad de símbolos, columnas, método de cuantización, reducción de ruido (on/off + umbral), límite de oscuros (on/off + %), papel (uno o varios), orientación, márgenes, recorte, ubicación de la leyenda e inclusión de la solución.
- **RF8.3** — WHEN cambia un control, THE SYSTEM SHALL actualizar la preview de la **solución** y de la **plantilla**, y el **histograma de celdas por nivel**.
- **RF8.4** — THE SYSTEM SHALL mostrar en la UI, en español, todos los avisos (celda chica, leyenda movida, nivel infrautilizado, poco rango tonal).
- **RF8.5** — THE SYSTEM SHALL ofrecer botones de descarga para el PDF (o el ZIP multi-papel) y el PNG.
- **RF8.6** — THE SYSTEM SHALL tener los textos de la UI en español. Solo el contenido del PDF va en inglés.

## 3. Requisitos no funcionales

- **RNF1 (rendimiento)** — WHEN se genera una grilla de 100 × 140 (preprocesamiento + cuantización + PDF, sin PNG), THE SYSTEM SHALL terminar en **< 5 s** en una PC común. Como 100 × 140 no entra en A4 respetando los 4 mm, la prueba usa un papel personalizado de 430 × 600 mm (celda ≈ 4,05 mm). El volumen de trabajo es el mismo que pedía el requisito original con A4: 14.000 celdas.
- **RNF2 (determinismo)** — WHEN se repite una generación con los mismos bytes de entrada y la misma configuración, THE SYSTEM SHALL producir un PDF **idéntico byte a byte** (modo `invariant` de ReportLab, sin fecha ni ID variables) y un PNG idéntico. Todas las semillas quedan fijas y los desempates son determinísticos.
- **RNF3 (separación)** — THE SYSTEM SHALL implementar la lógica de generación en un paquete del núcleo **sin importar Streamlit**. La UI solo llama a una función pública del tipo `generar_mosaico(imagen, config) -> Resultado`.
- **RNF4 (configuración validada)** — THE SYSTEM SHALL modelar la configuración del mosaico con un modelo pydantic validado, con mensajes de error en español.
- **RNF5 (calidad)** — THE SYSTEM SHALL tener type hints en todo el código, pasar `ruff check` sin errores y escribir los comentarios en español.
- **RNF6 (entorno)** — THE SYSTEM SHALL validar las variables de entorno al arrancar (pydantic-settings) y detenerse con un mensaje en español si alguna es inválida. *(Ya implementado en el scaffold.)*

## 4. Criterios de aceptación (cada uno con test de pytest)

| # | Criterio | Requisitos |
|---|---|---|
| CA1 | Para todo N en 5…10, los símbolos elegidos tienen cobertura **estrictamente creciente** y Δ ≥ 6 pp entre niveles consecutivos 1…N, y Δ ≥ 1,5 pp entre el vacío y el nivel 1. El nivel 1 es el punto central y el nivel N, la celda rellena. | RF2.3, RF2.4 |
| CA2 | Con N < 5, N > 10 o N no entero, se lanza un error con el mensaje en español de RF1.3. | RF1.3 |
| CA3 | Con `quantiles`, sin reducción de ruido ni límite de oscuros, en una imagen de prueba con buen rango tonal (un degradado sintético y una foto de prueba), ningún nivel tiene menos de **X = 50 % de 100/(N+1) %** de las celdas. Por ejemplo, X = 8,3 % para N = 5 y X = 4,5 % para N = 10. | RF3.1, RF3.7 |
| CA4 | Para cada papel (A4, Letter, A3 y Tabloid) y cada orientación, el MediaBox del PDF mide lo indicado en RF5.1 (±0,01 pt), y el contenido (grilla y leyenda) queda dentro del área útil. | RF5.1, RF5.4 |
| CA5 | Con `below`, si la leyenda entra: 1 página de plantilla con la leyenda incluida. Si no entra (porque con ella la celda baja de 4 mm y sin ella no): la leyenda va en una página aparte y se emite el aviso de RF6.3. | RF6.2, RF6.3 |
| CA6 | Con `separate`, la leyenda siempre sale en su propia página. | RF6.5 |
| CA7 | Con una configuración que da celdas < 4 mm, no se genera ningún PDF y se lanza el error en español con las sugerencias de RF4.6a. Las columnas sugeridas, el papel sugerido y el tamaño personalizado sugerido dan efectivamente celdas ≥ 4 mm. | RF4.6, RF4.6a, RF5.7a |
| CA8 | Dos generaciones con la misma entrada y configuración dan bytes idénticos (PDF y PNG), también con `kmeans`. | RNF2 |

**Criterios adicionales propuestos:**

| # | Criterio | Requisitos |
|---|---|---|
| CA9 | Los símbolos elegidos para cada N tienen firmas de forma distintas y disimilitud raster ≥ 0,35. | RF2.4c |
| CA10 | Con el límite de oscuros en L %, el nivel N tiene ≤ L % de las celdas, también después de la reducción de ruido. | RF3.5, RF3.8 |
| CA11 | Con la reducción de ruido activa (umbral 2), no queda ninguna celda aislada: ningún componente de tamaño 1. | RF3.4 |
| CA12 | El núcleo se importa y genera sin que `streamlit` esté en `sys.modules`. | RNF3 |
| CA13 | Una grilla de 100 × 140 en papel personalizado de 430 × 600 mm se genera en < 5 s. Es un test marcado `slow`, porque depende de la máquina. | RNF1 |
| CA14 | Las celdas vacías no tienen número en la plantilla, verificado extrayendo el texto del PDF. | RF7.1 |
| CA15 | Con la marca de blanco activa, la plantilla tiene un puntito gris por cada celda vacía, y la solución no tiene ninguno. Con la marca desactivada, no aparece ningún puntito. | RF7.1a, RF6.8 |

## 5. Valores propuestos para los umbrales abiertos (resumen)

| Parámetro | Valor propuesto | Motivo |
|---|---|---|
| N_MAX | **10** | Once tonos alcanzan para un grabado rico. Con más, se vuelve difícil diferenciar los símbolos dibujados a mano. |
| Tamaño de la biblioteca | **≥ 14** | Margen para elegir por forma y densidad. |
| Δ_MIN de cobertura | **6 pp** (niveles 1…N); **1,5 pp** (vacío → punto) | Con 10 niveles hacen falta ≥ 60 pp de rango (0 → ~100 %), así que 6 pp es alcanzable. Además, el algoritmo maximiza el contraste por encima de ese piso. |
| Disimilitud de forma | **≥ 0,35** (1 − IoU) + firma distinta | Evita pares como `//` y `///` desplazado. |
| Trazos por símbolo | **≤ 6** | Se dibujan rápido con birome. |
| Referencia de cobertura | Celda de 5 mm, trazo de 0,35 mm | Equivale a una birome o fineliner fina. |
| CELDA_MIN | **4 mm** (límite duro: no se genera) | Por debajo se hace difícil leer un "10" y dibujar una cruz densa. Recomendado: ≥ 5 mm. |
| Margen por defecto | **12,7 mm (0,5")** | Seguro en impresoras hogareñas, tanto en A4 como en Letter. |
| X de CA3 | **50 % de la cuota ideal** | Escala con N; un nivel con menos de la mitad de lo esperado se considera infrautilizado. |
| Límite de oscuros por defecto | **8 %** de las celdas | Evita las manchas negras pesadas del prototipo. |
| Umbral de ruido por defecto | **2** (elimina las celdas sueltas) | Conservador: no borra detalle real. |
| Columnas | 10–200, por defecto **40** | 40 columnas en A4 dan ≈ 4,6 mm, y el máximo en A4 con 4 mm es de 46. |
| Papel personalizado | 100–1200 mm por lado | Cubre desde tarjetas hasta impresiones grandes (A0 mide 841 × 1189 mm). |
| PNG de preview | Lado largo de **2000 px** | Tamaño típico de las imágenes de listing en Etsy. |

## 6. Preguntas abiertas

- ~~**Q1 — Conflicto entre 100 × 140 en A4 y la celda mínima.**~~ **Decidido:** 4 mm es un límite duro, que nunca se genera por debajo, y se agrega el papel personalizado para las grillas grandes (RF4.6, RF5.1a). La prueba de rendimiento pasa a un papel personalizado de 430 × 600 mm.
- **Q2 — Grosor del trazo y escala.** El comprador dibuja con su propia birome, así que la cobertura real depende de la celda. Propongo medir la cobertura con la referencia fija (5 mm y 0,35 mm) y que, en la solución y la preview, el trazo escale con la celda. ¿Te parece bien?
- ~~**Q3 — ¿El nivel N es siempre relleno sólido?**~~ **Decidido:** sí (RF2.4d).
- ~~**Q4 — Celda vacía y punto central.**~~ **Decidido:** (a) el punto central es siempre el símbolo 1, con un salto mínimo de 1,5 pp desde el vacío (RF2.4b y RF2.4e); (b) el blanco puro se reserva para las luces, con una marca de puntito gris tenue en la plantilla, activada por defecto (RF7.1a y RF6.8). Con cuantiles, el vacío recibe ≈ 1/(N+1) de las celdas.
- ~~**Q8 — Imágenes para la Fase 5.**~~ **Decidido:** las pasa el usuario cuando se las pida. Mientras tanto, los tests usan imágenes sintéticas (degradados y formas).
- **Q2, Q5, Q6, Q7 y Q9:** se aceptan las propuestas del documento, salvo indicación en contrario.
- **Q9 — Grilla en la solución.** ¿La página de solución lleva una grilla muy tenue (propuesta: opcional, apagada por defecto) o va limpia?

## 7. Fuera de alcance (esta fase)

Frontend web, API, base de datos, pagos, tiling multi-hoja (las grillas grandes se resuelven con un papel personalizado), mosaicos en color y CLI. Igualmente, la arquitectura la deja preparada (RNF3).
