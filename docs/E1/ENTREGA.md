# Ficha Técnica de Entrega — Hito [E1]
## Observatorio de Precios y Disponibilidad para Pescadería Valencia
### Trusted Data Lab: Capa Plata, Limpieza y Puerta de Calidad

| Metadato | Detalle |
| :--- | :--- |
| **Proyecto** | Observatorio de Precios y Disponibilidad de Productos del Mar |
| **Entrega** | **[E1] Trusted Data Lab: Capa Plata, Limpieza y Puerta de Calidad** |
| **Ingeniero Responsable / PSP** | **Felipe Sandoval** |
| **Cliente / Entidad Receptora** | **Pescadería Valencia** (Colima / Manzanillo) |
| **Fecha de Validación** | 13 de noviembre de 2026 |
| **Etiqueta Git (Release Tag)** | `e1` |
| **Estado del Hito** | **COMPLETADO / VALIDADO TÉCNICAMENTE** |

---

## 1. Arquitectura de Datos Implementada (Medallion Avanzada)

En este hito se consolida la transición de datos crudos e inmutables hacia capas curadas, validadas y analíticas, incorporando el patrón de **Aislamiento en Cuarentena** para salvaguardar la pureza de la Capa Plata.

```mermaid
flowchart TD
    subgraph Capa Bronce (Raw Inmutable)
        B1["data/bronce/precios_clima_historico_36p.csv<br/>(108 registros crudos)"]
        B2["Casos de Prueba / Feeds Externos Heterogéneos"]
    end

    subgraph Puerta de Calidad (Quality Gate con Pandera)
        QG{"Pandera DataFrameSchema<br/>Validación Estricta de Contrato"}
    end

    subgraph Aislamiento (Cuarentena)
        C1["data/cuarentena/registros_invalidos.csv<br/>(motivo_rechazo documentado)"]
    end

    subgraph Capa Plata (Curated & Preprocessed)
        P1["Limpieza e Imputación (MCAR / MAR)"]
        P2["IQR Estratificado (Picos Cuaresma vs Ruido)"]
        P3["Normalización MinMax & Z-Score"]
        P4["Discretización Conceptual (Escasez, Precios)"]
        P5["data/plata/datos_limpios.csv<br/>(108 registros validados)"]
    end

    subgraph Capa Oro (Analytics & Feature Store)
        O1["data/oro/dataset_analitico.csv<br/>(27 vistas mensuales agregadas)"]
        O2["data/oro/metadatos_pipeline_e1.json<br/>(Manifiesto y métricas de auditoría)"]
    end

    B1 --> QG
    B2 --> QG
    QG -->|Registros Infractores / Corruptos| C1
    QG -->|Registros Conformes al Contrato| P1
    P1 --> P2 --> P3 --> P4 --> P5
    P5 --> O1
    P5 --> O2
```

---

## 2. Reglas de Validación de la Puerta de Calidad (Pandera 0.20+)

El contrato de datos implementado en `src/pipeline_plata_oro.py` y documentado en `docs/E1/limpieza.ipynb` rige las siguientes restricciones inviolables:

| Columna / Variable | Tipo de Dato | Regla de Validación (Pandera Check) | Acción en caso de Infracción |
| :--- | :--- | :--- | :--- |
| `periodo_id` | Entero (`int`) | $\ge 1$, no nulo (`nullable=False`) | Desvío a Cuarentena |
| `fecha_inicio_semana` | Texto (`str`) | Formato estricto ISO 8601 (`YYYY-MM-DD`) | Desvío a Cuarentena |
| `mes` | Entero (`int`) | En rango $[1, 12]$ | Desvío a Cuarentena |
| `semana_del_anio` | Entero (`int`) | En rango $[1, 53]$ | Desvío a Cuarentena |
| `temporada` | Categórico | Pertenencia a `["TEMPORADA_ALTA_CUARESMA", "TEMPORADA_HURACANES_LLUVIAS", "TEMPORADA_REGULAR"]` | Desvío a Cuarentena |
| `producto_foco` | Categórico | Pertenencia a `["Mojarra Fresca Entera", "Huachinango del Pacífico", "Filete de Pez Vela"]` | Desvío a Cuarentena |
| `precio_minimo_kg` | Flotante (`float`) | Estrictamente $> 0$ ($ MXN) | Desvío a Cuarentena |
| `precio_frecuente_kg` | Flotante (`float`) | Estrictamente $> 0$ ($ MXN) | Desvío a Cuarentena |
| `precio_maximo_kg` | Flotante (`float`) | Estrictamente $> 0$ ($ MXN) | Desvío a Cuarentena |
| **Consistencia de Precios** | Lógica multi-columna | $\text{precio\_minimo} \le \text{precio\_frecuente} \le \text{precio\_maximo}$ | Desvío a Cuarentena |
| `disponibilidad_volumen_kg` | Flotante (`float`) | $\ge 0$ kg | Desvío a Cuarentena |
| `precipitacion_acumulada_mm` | Flotante (`float`) | $\ge 0.0$ mm | Desvío a Cuarentena |
| `velocidad_viento_kmh` | Flotante (`float`) | En rango físico verosímil $[0.0, 250.0]$ km/h | Desvío a Cuarentena |
| `rafagas_max_kmh` | Flotante (`float`) | En rango físico verosímil $[0.0, 350.0]$ km/h | Desvío a Cuarentena |
| `altura_oleaje_m` | Flotante (`float`) | En rango físico verosímil $[0.0, 15.0]$ m | Desvío a Cuarentena |
| `dias_cierre_puerto` | Entero (`int`) | En rango $[0, 7]$ días semanales | Desvío a Cuarentena |
| `alerta_meteorologica` | Categórico | Pertenencia a `["NINGUNA", "AMARILLA", "NARANJA", "ROJA"]` | Desvío a Cuarentena |

---

## 3. Resumen de Métricas de Flujo y Cuarentena

Durante la ejecución y validación técnica del pipeline, se obtuvieron las siguientes métricas de procesamiento:

```json
{
  "total_registros_evaluados": 111,
  "registros_aprobados_plata": 108,
  "registros_aislados_cuarentena": 3,
  "tasa_rechazo_pct": 2.7,
  "filas_agregadas_oro": 27
}
```

### 3.1 Detalle de Registros Aislados en Cuarentena (`data/cuarentena/registros_invalidos.csv`)

| Periodo ID | Producto Reportado | Motivo Exacto de Rechazo | Impacto Preventivo |
| :---: | :--- | :--- | :--- |
| **991** | `Salmón Atlántico Importado` | `Producto no autorizado: 'Salmón Atlántico Importado'` | Evita la contaminación de la canasta regional de especies de Colima. |
| **992** | `Huachinango del Pacífico` | `precio_minimo_kg inválido (-45.0); precio_frecuente_kg inválido (-20.0)` | Bloquea precios negativos absurdos originados por errores contables o de escaneo. |
| **993** | `Mojarra Fresca Entera` | `Inconsistencia lógica de precios: min(120.0) <= freq(95.0) <= max(80.0); velocidad_viento_kmh fuera de rango físico: 480.0` | Evita distorsiones extremas causadas por fallas de sensor anemométrico y precios invertidos. |

---

## 4. Checklist de Cumplimiento de Criterios de Aceptación (Rúbrica E1)

| Criterio / Entregable Requerido | Estado | Ubicación / Evidencia |
| :--- | :---: | :--- |
| **Actualización de `requirements.txt`** con pandas, pandera, scikit-learn, jupyter, nbformat. |  Cumplido | [`requirements.txt`](../../requirements.txt) |
| **Script de Integración y Limpieza `src/pipeline_plata_oro.py`** con resolución de heterogeneidades. |  Cumplido | [`src/pipeline_plata_oro.py`](../../src/pipeline_plata_oro.py) |
| **Puerta de Calidad Automática con Pandera** con segregación activa a Cuarentena y motivo documentado. |  Cumplido | [`data/cuarentena/registros_invalidos.csv`](../../data/cuarentena/registros_invalidos.csv) |
| **Preprocesamiento Estadístico:** Diagnóstico formal MCAR/MAR/MNAR, imputación temporal/mediana. |  Cumplido | [`src/pipeline_plata_oro.py`](../../src/pipeline_plata_oro.py#L312-L345) y [`docs/relatoria-E1.md`](../relatoria-E1.md) |
| **Tratamiento Contextual de Outliers:** IQR estratificado preservando Cuaresma y huracanes. |  Cumplido | [`src/pipeline_plata_oro.py`](../../src/pipeline_plata_oro.py#L347-L388) |
| **Normalización y Estandarización:** Escalamiento MinMax $[0, 1]$ y Z-Score ($\mu=0, \sigma=1$). |  Cumplido | [`src/pipeline_plata_oro.py`](../../src/pipeline_plata_oro.py#L390-L410) |
| **Discretización y Jerarquías:** `temporada_conceptual`, `nivel_escasez`, `nivel_precio_relativo`. |  Cumplido | [`src/pipeline_plata_oro.py`](../../src/pipeline_plata_oro.py#L412-L445) |
| **Datasets Generados:** `data/plata/datos_limpios.csv` y `data/oro/dataset_analitico.csv`. |  Cumplido | [`data/plata/datos_limpios.csv`](../../data/plata/datos_limpios.csv) y [`data/oro/dataset_analitico.csv`](../../data/oro/dataset_analitico.csv) |
| **Notebook Interactivo Paso a Paso:** `docs/E1/limpieza.ipynb`. |  Cumplido | [`docs/E1/limpieza.ipynb`](limpieza.ipynb) |
| **Automatización CI/CD:** `.github/workflows/extractor.yml` actualizado para Bronce, Plata, Oro y Cuarentena. |  Cumplido | [`.github/workflows/extractor.yml`](../../.github/workflows/extractor.yml) |
| **Relatoría Técnica Detallada:** `docs/relatoria-E1.md` con justificaciones estadísticas y matemáticas. |  Cumplido | [`docs/relatoria-E1.md`](../relatoria-E1.md) |
| **Bitácoras de Calidad PSP:** Entradas de E1 actualizadas en tiempo y defectos. |  Cumplido | [`calidad/tiempo-felipe.csv`](../../calidad/tiempo-felipe.csv) y [`calidad/defectos-felipe.csv`](../../calidad/defectos-felipe.csv) |

---

## 5. Instrucciones para Ejecución Local

```bash
# 1. Asegurar entorno virtual y dependencias
pip install -r requirements.txt

# 2. Ejecutar el extractor de Capa Bronce
python src/extractor_bronce.py

# 3. Ejecutar el pipeline de Puerta de Calidad, Limpieza y Generación Plata/Oro
python src/pipeline_plata_oro.py
```

---

## 6. Comandos Oficiales Git para la Etiqueta `e1`

```bash
# 1. Preparar archivos modificados y nuevos
git add .

# 2. Confirmar el estado de los archivos agregados
git status

# 3. Crear el commit de la entrega E1
git commit -m "feat(E1): implementacion de capa plata, puerta de calidad con pandera y dataset analitico oro"

# 4. Crear la etiqueta anotada 'e1'
git tag -a e1 -m "Entrega E1: Trusted Data Lab - Capa Plata, Limpieza y Puerta de Calidad (Felipe Sandoval)"

# 5. Enviar a GitHub
git push origin main
git push origin e1
```
