# Relatoría Técnica de Ingeniería de Datos — Hito [E1]
## Observatorio de Precios y Disponibilidad para Pescadería Valencia
### Diagnóstico Estadístico, Tratamiento de Calidad y Decisiones de Arquitectura

| Metadato | Detalle |
| :--- | :--- |
| **Documento** | Relatoría Técnica y Metodológica — Entrega E1 |
| **Ingeniero Autor** | Felipe Sandoval |
| **Rol** | Lead Data Engineer / Trusted Data Lab Architect |
| **Cliente Operativo** | Pescadería Valencia (Colima y Manzanillo, México) |
| **Fecha de Emisión** | 13 de noviembre de 2026 |
| **Versión** | 1.0.0 |

---

## 1. Resumen Ejecutivo y Hallazgos Estadísticos Iniciales

El presente documento expone las justificaciones teóricas, matemáticas y de arquitectura que fundamentaron la construcción de la **Capa Plata** y la **Capa Oro** del Observatorio de Precios y Disponibilidad de Mariscos para la Pescadería Valencia.

### 1.1 Perfil del Dataset Inicial (Capa Bronce)
A partir de la serie de 36 semanas cronológicas continuas (equivalentes a 108 registros distribuidos entre Mojarra, Huachinango y Filete de Pez Vela), el análisis exploratorio reveló tres comportamientos macroscópicos determinantes:

1. **Divergencia Estructural por Origen del Producto:**
   - **Mojarra Fresca Entera:** Presenta un comportamiento de precio relativamente estable durante los periodos ordinarios (media de \$78.50 MXN/kg con desviación estándar $\sigma = \$4.20$ MXN/kg), pero sufre un salto abrupto en Cuaresma (alcanzando hasta \$118.00 MXN/kg). El volumen de abasto se mantiene continuo gracias a la procedencia acuícola controlada.
   - **Huachinango del Pacífico:** Presenta una varianza extrema ($\sigma = \$38.60$ MXN/kg). Los precios basales (\$160 - \$175 MXN/kg) escalan hasta \$280 - \$298 MXN/kg en semanas de alerta meteorológica combinadas con cierre de puerto en Manzanillo. La pesca ribereña artesanal evidencia una correlación negativa directa entre altura de oleaje y volumen desembarcado ($r = -0.74$).
   - **Filete de Pez Vela:** Funciona como un amortiguador de mercado. Su precio base oscila en \$120 - \$135 MXN/kg, pero en temporada de tormentas (septiembre y octubre) la escasez de capturas de altura provoca una contracción de volumen del 55%, empujando su precio hacia \$175 MXN/kg.

```
Distribución Bivariada Conceptual (Precio vs Disponibilidad):
============================================================
Precio ($/kg)
  ^
  |        [Huachinango en Huracán / Cierre Puerto]
  |          *  *
  |             [Huachinango en Cuaresma]
  |               *    *
  |                      [Filete Vela en Lluvias]
  |                         *
  |                               [Mojarra en Cuaresma]
  |                                  *  *  *
  |                                           [Mojarra Regular]
  |                                             o  o  o  o
  +------------------------------------------------------------> Volumen (kg)
```

---

## 2. Diagnóstico Formal y Tratamiento de Valores Faltantes

La literatura estadística (Little & Rubin, 2019) clasifica la ausencia de datos en tres mecanismos con implicaciones severas sobre el sesgo del estimador. En el pipeline de Pescadería Valencia se diagnosticaron y trataron formalmente los tres mecanismos:

### 2.1 MCAR (Missing Completely at Random — Faltante Completamente al Azar)
- **Definición:** La probabilidad de que un dato falte es totalmente independiente de variables observadas y no observadas:
  $$P(M | Y_{obs}, Y_{mis}) = P(M)$$
- **Manifestación en el Negocio:** Pérdidas aleatorias de telemetría en la estación meteorológica marina de Manzanillo (desconexión de red, reinicios de la API de Open-Meteo).
- **Tratamiento Técnico:** Dado que no existe sesgo sistemático, se aplica **Interpolación Temporal Lineal Local**:
  $$\hat{y}_t = y_{t-1} + \frac{y_{t+1} - y_{t-1}}{2}$$
  complementada con `bfill()` y `ffill()` en los extremos de la serie temporal.

### 2.2 MAR (Missing at Random — Faltante al Azar)
- **Definición:** La probabilidad de ausencia depende de una variable observada en el dataset, pero no del valor no observado en sí:
  $$P(M | Y_{obs}, Y_{mis}) = P(M | Y_{obs})$$
- **Manifestación en el Negocio:** Durante semanas con `dias_cierre_puerto >= 3`, el registro del precio mínimo de huachinango en playa no se reporta porque las cooperativas no zarparon. La ausencia de datos de captura está explicada completamente por la variable meteorológica observable `dias_cierre_puerto`.
- **Tratamiento Técnico:** La eliminación de estas filas subestimaría drásticamente el impacto de las tormentas en el desabasto. Se utiliza **Imputación por Mediana Condicional Estratificada por Estrato Operativo**:
  $$\hat{y}_{i, prod, temp} = \text{Mediana}\left(\{ y_j : producto_j = prod \land temporada_j = temp \}\right)$$
  La mediana es preferida sobre la media para evitar distorsiones por asimetría positiva en precios de mariscos.

### 2.3 MNAR (Missing Not at Random — Faltante No al Azar)
- **Definición:** La ausencia del dato está correlacionada directamente con el valor no observado:
  $$P(M | Y_{obs}, Y_{mis}) \neq P(M | Y_{obs})$$
- **Manifestación en el Negocio:** En escenarios de colapso de precios o sobreoferta clandestina, los intermediarios omiten intencionalmente reportar transacciones al SNIIM para evitar registrar precios por debajo de acuerdos gremiales.
- **Tratamiento Técnico:** En lugar de forzar una imputación ingenua que maquille la anomalía, el pipeline introduce banderas binarias de observabilidad y audita la estabilidad de las series antes de derivar variables a la Capa Oro.

---

## 3. Detección y Tratamiento Contextual de Outliers

### 3.1 La Falacia del Filtro Global Ciego
Un error común en pipelines novatos consiste en aplicar filtros estadísticos globales no supervisados (por ejemplo, descartar o recortar todo registro con $|Z| > 3.0$ o fuera de $1.5 \times \text{IQR}$ general).

> **Peligro Crítico para Pescadería Valencia:** En nuestro negocio, el precio de la mojarra sube un 50% en Semana Santa y el huachinango se dispara un 70% cuando entra un huracán en Manzanillo. Un filtro global ciego clasificaría estos incrementos reales como "errores atípicos" y los eliminaría o recortaría. Esto destruiría el fenómeno analítico central que el cliente nos contrató para predecir.

### 3.2 Solución Implementada: IQR Estratificado por Especie y Régimen Estacional
El pipeline `src/pipeline_plata_oro.py` descompone la población en subgrupos homogéneos:
$$\text{Estrato} = (\text{producto\_foco}, \text{temporada})$$

Para cada estrato se calculan los cuartiles $Q_1$, $Q_3$ y el rango intercuartílico:
$$\text{IQR}_{e} = Q_{3, e} - Q_{1, e}$$

```
+-------------------------------------------------------------------------------------------------+
|                                 ESQUEMA DE CLASIFICACIÓN DE VALORES                             |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   [ Inferior Severo ]    [ Variación Ordinaria ]    [ Picos Reales de Negocio ]    [ Ruido ]    |
|   < Q1 - 3.0*IQR         Q1 - 1.5*IQR a Q3+1.5*IQR   Q3+1.5*IQR a Q3+3.0*IQR       > Q3+3.0*IQR |
|   (Winsorizado)          (Conservado Intacto)        (Etiquetado con Flag)         (Winsorizado)|
+-------------------------------------------------------------------------------------------------+
```

1. **Picos Reales de Mercado ($Q_3 + 1.5 \times \text{IQR} \le x \le Q_3 + 3.0 \times \text{IQR}$):**
   - Si ocurre en `TEMPORADA_ALTA_CUARESMA`: Se activa la bandera `es_pico_estacional_real = True`.
   - Si ocurre en `TEMPORADA_HURACANES_LLUVIAS` con `dias_cierre_puerto >= 2`: Se activa `es_anomalia_climatica = True`.
   - **Acción:** El valor de precio se conserva íntegro sin modificación para alimentar los modelos predictivos E1 y E2.
2. **Ruido Extremo y Errores de Transcripción ($x > Q_3 + 3.0 \times \text{IQR}$ o $x < Q_1 - 3.0 \times \text{IQR}$):**
   - Valores provocados por errores de dedo (ejemplo: capturar \$1,800 en vez de \$180).
   - **Acción:** Se aplica **Winsorización Asimétrica** acotando el valor al percentil extremo tolerable.

---

## 4. Normalización, Estandarización y Jerarquías Conceptuales

### 4.1 Transformación de Variables Continuas
Para preparar los datos para la siguiente entrega (E2: Modelado y Pronóstico), se generaron dos transformaciones complementarias:

1. **Escalamiento Min-Max ($[0, 1]$):**
   $$x_{norm} = \frac{x - x_{min}}{x_{max} - x_{min}}$$
   Preserva relaciones exactas de distancia euclidiana, siendo idóneo para algoritmos de agrupamiento y redes neuronales recurrentes (LSTM).
2. **Estandarización Z-Score ($\mu=0, \sigma=1$):**
   $$z = \frac{x - \mu}{\sigma}$$
   Garantiza que variables con escalas dispares (como la precipitación acumulada en milímetros vs. precios en cientos de pesos) no dominen artificialmente la optimización por gradiente en modelos lineales o autoregresivos (ARIMA/SARIMAX).

### 4.2 Discretización y Jerarquías Conceptuales
Para enriquecer la toma de decisiones gerenciales en la pescadería, se crearon tres jerarquías categóricas de negocio:

1. `temporada_conceptual`:
   - `ALTA_CUARESMA`: Semanas 7 a 16 (pico de demanda católica).
   - `BAJA_LLUVIAS`: Semanas 35 a 44 (pico de ciclones en Manzanillo).
   - `REGULAR`: Periodos ordinarios del año.
2. `nivel_escasez`:
   - `BAJO`: Puerto abierto, arribo continuo.
   - `MEDIO`: 1 a 2 días de cierre o alertas preventivas.
   - `CRITICO`: 3 o más días de cierre de puerto o alerta roja meteorológica.
3. `nivel_precio_relativo`:
   - Clasificación por terciles empíricos independientes para cada especie: `PRECIO_ACCESIBLE`, `PRECIO_MODERADO`, `PRECIO_ELEVADO`.

---

## 5. Diseño y Reducción de Datos en la Capa Oro

La **Capa Oro** consolida una vista agregada mensual por producto (`data/oro/dataset_analitico.csv`), reduciendo las 108 observaciones semanales a 27 vectores analíticos de alto valor.

### 5.1 Nuevas Características de Negocio Calculadas en Oro:
- `coeficiente_variacion_precio_pct`:
  $$\text{CV} = \left( \frac{\sigma_{precio}}{\mu_{precio}} \right) \times 100$$
  Permite a Don Aurelio evaluar qué especie tiene mayor riesgo de descontrol de presupuesto en cada mes.
- `indice_vulnerabilidad_climatica`:
  $$\text{IVC} = \min\left(10, \; 1.5 \times \text{dias\_cierre} + 1.0 \times \text{alertas\_severas} + \frac{\text{precipitacion\_mm}}{50}\right)$$
  Métrica sintética en escala 0 a 10 que cuantifica la presión ambiental sobre el suministro de Manzanillo.
- `riesgo_abasto_proyectado`:
  Semáforo categórico (`RIESGO_ESTABLE`, `RIESGO_MODERADO`, `RIESGO_ALTO_DESABASTO`) para la planeación logística de compras mayoristas.

---

## 6. Conclusiones y Preparación para el Hito E2

La entrega E1 dota a Pescadería Valencia de un pipeline robusto, auditable e inmune a la degradación silenciosa de datos. La separación explícita de registros anómalos hacia la **Cuarentena** y la refinación progresiva hacia las capas **Plata** y **Oro** garantizan que el entrenamiento de modelos de pronóstico en la etapa E2 se realice sobre cimientos analíticos sólidos y verificables.
