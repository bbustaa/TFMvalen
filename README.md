# TFM — Clasificación de Tráfico Web Cifrado (H2Classifier)

Este repositorio contiene el código, datos y resultados del Trabajo Fin de Máster sobre **Website Fingerprinting en tráfico TLS cifrado**. El objetivo es demostrar que es posible identificar qué página web está visitando un usuario aunque el tráfico esté cifrado con TLS/HTTPS, analizando únicamente los metadatos de los paquetes (tamaños de registros TLS, ráfagas, estadísticas de conexión) sin acceder al contenido.

El proyecto implementa una pipeline completa:
1. **Extracción de características** a partir de capturas de red (archivos PCAP)
2. **Análisis de solapamiento** entre sitios web (¿son distinguibles entre sí?)
3. **Clasificación con Random Forest** para identificar el sitio web visitado
4. **Evaluación en múltiples escenarios** con distinto grado de dificultad

---

## Estructura del repositorio

```
TFMvalen/
├── src/                        # Código fuente principal
│   ├── featuresH2C/            # Módulos de extracción de características (exploratorios)
│   ├── extractMetrics/         # Pipeline principal de extracción
│   ├── clasificador/           # Modelos de clasificación y visualización
│   └── comprobaciones/         # Scripts de inspección y depuración
├── scripts/                    # Scripts de análisis y visualización
├── datos/                      # Resultados y ficheros de datos por escenario
├── graficas/                   # Imágenes generadas por los scripts
└── Papers/                     # Artículos de referencia
```

---

## Requisitos

- Python 3.8+
- [tshark](https://www.wireshark.org/docs/man-pages/tshark.html) (incluido en Wireshark) instalado y en el PATH
- Paquetes Python:

```bash
pip install pyshark numpy scikit-learn matplotlib pandas
```

---

## Escenarios de captura

Los experimentos se realizan sobre cuatro escenarios con distintas condiciones, todos en entorno **Closed World** (el clasificador solo ve sitios que conoce) salvo el cuarto que es **Open World**:

| Escenario | Descripción | Páginas | Capturas/página |
|-----------|-------------|---------|-----------------|
| 1 | Páginas con tamaño e imágenes variables (586 KB – 10.4 MB) | 100 | 100 |
| 2 | Páginas con tamaño fijo (2.57 MB) pero número de imágenes variable (0–99) | 100 | 100 |
| 3 | Páginas con tamaño e imágenes fijas (sub-escenarios: percentil 25, 50 y 75) | 100 | 100 |
| 4 | Open World — dominios web variados de Internet | Variable | Variable |

---

## Vector de características (36 919 features)

Cada captura PCAP se convierte en un vector numérico de longitud fija con la siguiente estructura:

```
[0]           incoming TLS records            ─┐
[1]           outgoing TLS records             ├─ (A) Estadísticas de conexión
[2]           total TLS bytes                 ─┘

[3 .. 7]      min / max / std / mean / median  ── (B1) Ráfagas método 1
              (bytes del servidor entre dos paquetes cliente consecutivos)

[8 .. 12]     min / max / std / mean / median  ── (B2) Ráfagas método 2
              (records del servidor en bloques de 20 registros)

[13]          nº tamaños TLS distintos incoming ─┐
[14]          nº tamaños TLS distintos outgoing  ┘ (C) Conteo de tamaños distintos

[15 .. 34]    20 tamaños menos frecuentes incoming ─┐
[35 .. 54]    20 tamaños menos frecuentes outgoing  ┘ (D) Top 20 tamaños

[55 .. 18486]    frecuencia por tamaño incoming [1..18432] ─┐
[18487..36918]   frecuencia por tamaño outgoing [1..18432]  ┘ (E) Distribución de tamaños

Total: 3 + 5 + 5 + 2 + 20 + 20 + 18432 + 18432 = 36 919 features
```

---

## Módulos principales (`src/`)

### `src/featuresH2C/` — Módulos exploratorios de extracción

Implementaciones independientes de cada grupo de características. Sirven como base y referencia para el pipeline final. Cada módulo puede usarse de forma aislada.

| Fichero | Qué hace |
|---------|----------|
| `a_ConnStats.py` | Calcula el total de registros TLS entrantes, salientes y bytes totales de la conexión |
| `b1_BurstStats.py` | Calcula estadísticas (min/max/media/std/mediana) de los bytes del servidor entre dos paquetes consecutivos del cliente (ráfagas B1) |
| `b2_BurstStats.py` | Calcula estadísticas de los records del servidor dentro de ventanas de 20 registros (ráfagas B2) |
| `c_NumDiffSizes.py` | Cuenta cuántos tamaños TLS distintos aparecen en cada dirección del flujo |
| `d_Top20Sizes.py` | Obtiene los 20 tamaños TLS menos frecuentes, ordenados por frecuencia ascendente |
| `e_SizeDist.py` | Genera dos vectores de 18 432 posiciones con la frecuencia de cada tamaño TLS posible |

Estos módulos no se ejecutan directamente, sino que son importados por los scripts de extracción.

---

### `src/extractMetrics/` — Pipeline principal de extracción

#### `ExtraerFeaturesCW.py` — Extracción para Closed World

Procesa un directorio completo de archivos PCAP y genera un CSV con el vector de 36 919 características por cada captura.

**Funcionamiento:**
1. Para cada PCAP, lanza `tshark` y extrae los frames TLS con sus metadatos (timestamp, IPs, puertos, longitudes de registros)
2. Calcula los 5 grupos de características (A–E)
3. Escribe una fila en el CSV de salida con la etiqueta de clase y todos los features

**Ejecución:**
```bash
python src/extractMetrics/ExtraerFeaturesCW.py \
    <directorio_pcaps> \
    --ip_cliente <IP> \
    --ip_servidor <IP> \
    --puerto <puerto> \
    --output resultados.csv
```

---

#### `extraerFeaturesOW.py` — Extracción para Open World

Versión adaptada para el escenario Open World donde las etiquetas son nombres de dominio en lugar de números de página. Soporta un fichero de mapeo PCAP→dominio y un fichero de dominios monitorizados.

**Ejecución:**
```bash
python src/extractMetrics/extraerFeaturesOW.py \
    <directorio_pcaps> \
    --mapeo mapeo_dominios.json \
    --monitored dominios_monitorizados.txt \
    --output resultados_ow.csv
```

---

#### `mapeo_pcaps_OW.py` — Generador de mapeo PCAP→dominio

Lee un fichero de metadatos de captura y genera un JSON con la correspondencia entre cada archivo PCAP y el dominio web al que pertenece.

**Ejecución:**
```bash
python src/extractMetrics/mapeo_pcaps_OW.py \
    metadata.txt \
    --output mapeo_dominios.json
```

---

### `src/clasificador/` — Clasificación con Random Forest

#### `clasificador_v1.py` — Versión básica

Entrena un Random Forest con todos los 36 919 features sin selección previa. Útil como línea base.

**Ejecución:**
```bash
python src/clasificador/clasificador_v1.py \
    resultados.csv \
    --n_train 80
```
- `--n_train`: porcentaje de muestras usadas para entrenamiento (el resto se usa para test)

**Salida:** Accuracy, matriz de confusión, top 20 features más importantes.

---

#### `clasificador_v2.py` — Versión con selección de features (paper original)

Replica los parámetros del clasificador propuesto en el artículo de referencia. Usa 400 árboles, profundidad máxima 50 y selecciona los 300 features más importantes en una primera pasada antes de entrenar el modelo final.

**Ejecución:**
```bash
python src/clasificador/clasificador_v2.py \
    resultados.csv \
    --n_train 80
```

**Salida:** Accuracy, matriz de confusión normalizada (mapa de calor PNG), lista de features seleccionados.

---

#### `clasificador_v3.py` — Versión con top N configurable

Igual que v2 pero permite configurar cuántos features se seleccionan en la primera pasada, lo que facilita los experimentos comparando distintos valores de N.

**Ejecución:**
```bash
python src/clasificador/clasificador_v3.py \
    resultados.csv \
    --n_train 80 \
    --top_n 50
```
- `--top_n`: número de features a seleccionar (default: 300)

---

#### `graficar_resultados.py` — Mapas de calor de la matriz de confusión

Genera una imagen PNG con la matriz de confusión normalizada por filas (cada celda muestra el porcentaje de acierto para esa clase). Es importado por los clasificadores, pero también puede usarse de forma independiente.

---

#### `mapeo_features.py` — Nombres legibles para los features

Proporciona una función `nombre_feature(i)` que devuelve una descripción textual para cualquier índice del vector (p.ej. `feature_3` → `"burst_method1_min"`). Es importado por los clasificadores para mostrar los resultados de forma comprensible.

---

### `src/comprobaciones/` — Inspección y depuración

#### `inspeccion_flujo.py`

Abre un PCAP concreto y muestra en consola todos los frames TLS que encuentra, con sus metadatos (IPs, puertos, campos TLS). Útil para depurar la extracción o verificar que tshark identifica correctamente los flujos.

**Ejecución:**
```bash
python src/comprobaciones/inspeccion_flujo.py
```
*(La ruta del PCAP se configura directamente dentro del script.)*

---

## Scripts de análisis y visualización (`scripts/`)

### `calcular_solapamientos.py`

Analiza si los valores de un feature concreto se solapan entre distintas páginas web. Un alto solapamiento significa que ese feature no es útil para distinguir esas páginas.

**Ejecución:**
```bash
python scripts/calcular_solapamientos.py \
    datos/escenario1/features.csv \
    feature_2 \
    --tolerancia 5.0
```

**Salida:** Fichero TXT con todos los pares de páginas que se solapan y cuántas muestras coinciden, ordenado de mayor a menor solapamiento.

---

### `filtrar_features.py`

Extrae columnas específicas de un CSV de features, manteniendo siempre la columna de etiqueta. Útil para trabajar con subconjuntos de features sin regenerar las capturas.

**Ejecución:**
```bash
python scripts/filtrar_features.py \
    datos/escenario1/features.csv \
    -f feature_0 feature_2 feature_55 \
    -o datos/escenario1/features_reducido.csv
```

---

### `variacion_tamanos.py`

Analiza la variación de tamaños de las imágenes de las páginas web de un escenario. Genera dos gráficas: un boxplot agrupado y un gráfico de media ± desviación típica.

**Ejecución:**
```bash
python scripts/variacion_tamanos.py <directorio_escenario>
```

**Salida:** Dos PNG con los análisis guardados en `graficas/escenario{N}/`.

---

### `grafica_interseccion.py`

Visualiza en 1D los rangos de valores de un feature para cada página web. Cada página aparece como una barra vertical que muestra su rango [mín, máx]. Las páginas cuyos rangos se solapan con otra se resaltan en color distinto.

**Ejecución:**
```bash
python scripts/grafica_interseccion.py \
    datos/escenario1/features.csv \
    feature_2
```

---

### `grafica_interseccion_2d.py`

Versión 2D del análisis anterior. Cada página se representa como un rectángulo en el plano definido por dos features. Detecta y resalta los rectángulos que se solapan.

**Ejecución:**
```bash
python scripts/grafica_interseccion_2d.py \
    datos/escenario1/features.csv \
    feature_2 feature_5
```

---

### `grafica_interseccion_3d.py`

Versión 3D: cada página se representa como un cubo en el espacio definido por tres features. Dibuja las caras semitransparentes con wireframe y resalta solapamientos.

**Ejecución:**
```bash
python scripts/grafica_interseccion_3d.py \
    datos/escenario1/features.csv \
    feature_2 feature_5 feature_10
```

---

### `solapamiento_nd.py`

Calcula el solapamiento N-dimensional usando hipercubos. Permite analizar si un conjunto de N features tomado en conjunto es suficiente para distinguir todas las páginas entre sí.

**Ejecución:**
```bash
python scripts/solapamiento_nd.py \
    datos/escenario1/features.csv \
    feature_2 feature_5 feature_10
```

**Salida:** TXT con la matriz de solapamientos y el número total de pares solapados (Θ).

---

### `theta_vs_acc.py`

Genera un gráfico con doble eje Y que muestra cómo evolucionan simultáneamente el número de pares solapados (Θ) y la accuracy del clasificador según el número de features utilizados (top N).

Los datos están definidos directamente en el script y deben actualizarse para cada escenario.

**Ejecución:**
```bash
python scripts/theta_vs_acc.py
```

**Salida:** PNG guardado en `DIRECTORIO_SALIDA` definido en el propio script.

---

### `b1.py`

Genera una figura conceptual ilustrativa del método de ráfagas B1. Muestra una línea temporal con flechas que representan peticiones GET/ACK del cliente y respuestas TLS del servidor, indicando las ráfagas B1 entre peticiones consecutivas del cliente.

**Ejecución:**
```bash
python scripts/b1.py
```

**Salida:** PNG guardado en `DIRECTORIO_SALIDA` definido en el script.

---

### `filtrar_pcaps.sh` y `recopilar.sh`

Scripts de shell auxiliares para preparar el entorno de datos: filtrar archivos PCAP y recopilar capturas en la estructura de directorios esperada por los scripts de extracción.

**Ejecución:**
```bash
bash scripts/filtrar_pcaps.sh
bash scripts/recopilar.sh
```

*(Las rutas se configuran dentro de cada script.)*

---

## Datos y resultados (`datos/`)

Cada escenario tiene su propia carpeta con los resultados de los experimentos:

```
datos/
├── INFO.txt                        # Descripción detallada de los escenarios
├── escenario1/
│   ├── analisis_solapamiento/      # Resultados del análisis ND (top 1, 2, 3, 5, 10 features)
│   └── clasificadorv2/             # Accuracy y top features del clasificador v2
├── escenario2/
│   ├── analisis_solapamiento/
│   └── clasificadorv2/
├── escenario3/
│   ├── percentil25/
│   ├── percentil50/
│   └── percentil75/
└── escenario4/
    ├── analisis_solapamiento/
    ├── clasificadorv2/
    └── urls/
```

Dentro de cada carpeta `clasificadorv2/` se encuentran ficheros `top{N}.txt` con los N features más importantes seleccionados y `result.txt` con la accuracy final.

---

## Gráficas generadas (`graficas/`)

Las imágenes PNG generadas por los scripts se guardan en esta carpeta, organizadas por escenario:

```
graficas/
├── burst_metodo1.png               # Visualización conceptual del método B1
├── escenario1/
│   ├── escenario1_boxplot.png
│   ├── escenario1_cv.png
│   ├── theta_vs_accuracy_escenario1.png
│   └── analisis_solapamiento/
├── escenario2/  ...
├── escenario3/  ...
└── escenario4/  ...
```
