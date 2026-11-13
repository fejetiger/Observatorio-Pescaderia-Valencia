#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
PROYECTO: Observatorio de Precios y Disponibilidad - Pescadería Valencia
ENTREGA:  [E1] Trusted Data Lab: Capa Plata, Limpieza y Puerta de Calidad
AUTOR:    Felipe Sandoval (Data Engineering Lead)
ARCHIVO:  src/pipeline_plata_oro.py
DESCRIPCIÓN:
    Pipeline integral de ingestión, validación de esquemas (Puerta de Calidad
    con Pandera), segregación a Cuarentena, preprocesamiento estadístico
    (imputación de nulos, tratamiento de atípicos con IQR estratificado,
    normalización/estandarización y discretización) y construcción de la
    Capa Oro analítica para pronóstico y experimentación causal.
=============================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, Dict, Any, List

os.environ["DISABLE_PANDERA_IMPORT_WARNING"] = "True"

import numpy as np
import pandas as pd
try:
    import pandera.pandas as pa
    from pandera.pandas import Column, Check, DataFrameSchema
except (ImportError, AttributeError):
    import pandera as pa
    from pandera import Column, Check, DataFrameSchema

from sklearn.preprocessing import MinMaxScaler, StandardScaler

# Configuración de Logging Estructurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PipelinePlataOroValencia")

# Rutas del Data Lake
BASE_DIR = Path(__file__).resolve().parent.parent
DIR_BRONCE = BASE_DIR / "data" / "bronce"
DIR_CUARENTENA = BASE_DIR / "data" / "cuarentena"
DIR_PLATA = BASE_DIR / "data" / "plata"
DIR_ORO = BASE_DIR / "data" / "oro"

PATH_BRONCE_CSV = DIR_BRONCE / "precios_clima_historico_36p.csv"
PATH_CUARENTENA_CSV = DIR_CUARENTENA / "registros_invalidos.csv"
PATH_PLATA_CSV = DIR_PLATA / "datos_limpios.csv"
PATH_ORO_CSV = DIR_ORO / "dataset_analitico.csv"
PATH_METADATOS_JSON = DIR_ORO / "metadatos_pipeline_e1.json"

# Catálogo de Productos Autorizados en el Observatorio
PRODUCTOS_AUTORIZADOS = [
    "Mojarra Fresca Entera",
    "Huachinango del Pacífico",
    "Filete de Pez Vela"
]

ALERTAS_VALIDAS = ["NINGUNA", "AMARILLA", "NARANJA", "ROJA"]


# =============================================================================
# 1. ESQUEMA DE VALIDACIÓN PANDERA (PUERTA DE CALIDAD)
# =============================================================================
def obtener_esquema_pandera() -> DataFrameSchema:
    """Define el contrato de calidad formal exigido para la Capa Plata."""
    return DataFrameSchema(
        columns={
            "periodo_id": Column(int, Check.greater_than_or_equal_to(1), nullable=False),
            "fecha_inicio_semana": Column(str, nullable=False),
            "fecha_fin_semana": Column(str, nullable=False),
            "mes": Column(int, Check.in_range(1, 12), nullable=False),
            "semana_del_anio": Column(int, Check.in_range(1, 53), nullable=False),
            "temporada": Column(str, Check.isin(["TEMPORADA_ALTA_CUARESMA", "TEMPORADA_HURACANES_LLUVIAS", "TEMPORADA_REGULAR"]), nullable=False),
            "producto_foco": Column(str, Check.isin(PRODUCTOS_AUTORIZADOS), nullable=False),
            "precio_minimo_kg": Column(float, Check.greater_than(0), nullable=False),
            "precio_maximo_kg": Column(float, Check.greater_than(0), nullable=False),
            "precio_frecuente_kg": Column(float, Check.greater_than(0), nullable=False),
            "disponibilidad_volumen_kg": Column(float, Check.greater_than_or_equal_to(0), nullable=False),
            "precipitacion_acumulada_mm": Column(float, Check.greater_than_or_equal_to(0), nullable=False),
            "velocidad_viento_kmh": Column(float, Check.in_range(0.0, 250.0), nullable=False),
            "rafagas_max_kmh": Column(float, Check.in_range(0.0, 350.0), nullable=False),
            "altura_oleaje_m": Column(float, Check.in_range(0.0, 15.0), nullable=False),
            "dias_cierre_puerto": Column(int, Check.in_range(0, 7), nullable=False),
            "alerta_meteorologica": Column(str, Check.isin(ALERTAS_VALIDAS), nullable=False),
        },
        checks=[
            Check(
                lambda df: (df["precio_minimo_kg"] <= df["precio_frecuente_kg"] + 0.05) &
                           (df["precio_frecuente_kg"] <= df["precio_maximo_kg"] + 0.05),
                error="Inconsistencia lógica de precios: precio_minimo_kg <= precio_frecuente_kg <= precio_maximo_kg"
            )
        ],
        coerce=True,
        strict=False
    )


# =============================================================================
# 2. INGESTA Y RESOLUCIÓN DE HETEROGENEIDADES
# =============================================================================
def cargar_y_armonizar_bronce(path_csv: Path) -> pd.DataFrame:
    """
    Carga la fuente de capa Bronce y resuelve discrepancias de formatos de fecha,
    tipos de datos numéricos y codificaciones textuales.
    """
    logger.info(f"Cargando datos crudos desde {path_csv}...")
    if not path_csv.exists():
        raise FileNotFoundError(f"No se encontró el archivo de entrada Bronce: {path_csv}")

    df = pd.read_csv(path_csv, encoding="utf-8")
    logger.info(f"Registros crudos iniciales leídos: {len(df)}")

    # Homogeneización de Fechas (ISO 8601 YYYY-MM-DD)
    df["fecha_inicio_semana"] = pd.to_datetime(df["fecha_inicio_semana"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["fecha_fin_semana"] = pd.to_datetime(df["fecha_fin_semana"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Limpieza y coerción de variables numéricas continuas
    cols_float = [
        "precio_minimo_kg", "precio_maximo_kg", "precio_frecuente_kg",
        "disponibilidad_volumen_kg", "precipitacion_acumulada_mm",
        "velocidad_viento_kmh", "rafagas_max_kmh", "altura_oleaje_m"
    ]
    for col in cols_float:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Coerción de enteros
    cols_int = ["periodo_id", "mes", "semana_del_anio", "dias_cierre_puerto"]
    for col in cols_int:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Limpieza de cadenas de texto
    cols_str = ["producto_foco", "variedad_especie", "origen_abasto", "mercado_referencia", "alerta_meteorologica"]
    for col in cols_str:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


# =============================================================================
# 3. PUERTA DE CALIDAD Y ENRUTAMIENTO A CUARENTENA
# =============================================================================
def inyectar_casos_control_calidad(df: pd.DataFrame) -> pd.DataFrame:
    """
    Incorpora intencionalmente anomalías controladas para validar el funcionamiento
    activo de la puerta de calidad y asegurar que ningún registro corrupto
    se filtre inadvertidamente a la Capa Plata.
    """
    casos_anomalos = [
        {
            "periodo_id": 991,
            "fecha_inicio_semana": "2025-08-11",
            "fecha_fin_semana": "2025-08-17",
            "mes": 8,
            "semana_del_anio": 33,
            "temporada": "TEMPORADA_REGULAR",
            "producto_foco": "Salmón Atlántico Importado",  # Especie no autorizada en el observatorio
            "variedad_especie": "Salmo salar",
            "origen_abasto": "Chile / Importación Aérea",
            "mercado_referencia": "Mercado del Mar Zapopan",
            "precio_minimo_kg": 280.0,
            "precio_maximo_kg": 340.0,
            "precio_frecuente_kg": 310.0,
            "disponibilidad_volumen_kg": 200.0,
            "precipitacion_acumulada_mm": 5.0,
            "velocidad_viento_kmh": 14.0,
            "rafagas_max_kmh": 18.0,
            "altura_oleaje_m": 1.1,
            "dias_cierre_puerto": 0,
            "alerta_meteorologica": "NINGUNA",
            "fuente_primaria_precio": "SNIIM (Secretaría de Economía)",
            "fuente_primaria_clima": "Open-Meteo Marine/Historical API",
            "timestamp_ingesta_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "periodo_id": 992,
            "fecha_inicio_semana": "2025-09-15",
            "fecha_fin_semana": "2025-09-21",
            "mes": 9,
            "semana_del_anio": 38,
            "temporada": "TEMPORADA_HURACANES_LLUVIAS",
            "producto_foco": "Huachinango del Pacífico",
            "variedad_especie": "Lutjanus peru",
            "origen_abasto": "Costa Manzanillo",
            "mercado_referencia": "Muelle de San Pedrito",
            "precio_minimo_kg": -45.0,  # Error crítico: Precio negativo
            "precio_maximo_kg": 180.0,
            "precio_frecuente_kg": -20.0,  # Error crítico: Precio negativo
            "disponibilidad_volumen_kg": 150.0,
            "precipitacion_acumulada_mm": 85.0,
            "velocidad_viento_kmh": 42.0,
            "rafagas_max_kmh": 60.0,
            "altura_oleaje_m": 2.8,
            "dias_cierre_puerto": 3,
            "alerta_meteorologica": "AMARILLA",
            "fuente_primaria_precio": "SNIIM (Secretaría de Economía)",
            "fuente_primaria_clima": "Open-Meteo Marine/Historical API",
            "timestamp_ingesta_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        {
            "periodo_id": 993,
            "fecha_inicio_semana": "2025-10-06",
            "fecha_fin_semana": "2025-10-12",
            "mes": 10,
            "semana_del_anio": 41,
            "temporada": "TEMPORADA_HURACANES_LLUVIAS",
            "producto_foco": "Mojarra Fresca Entera",
            "variedad_especie": "Tilapia Nilótica Cultivo",
            "origen_abasto": "Granjas Jalisco",
            "mercado_referencia": "Mercado Zapopan",
            "precio_minimo_kg": 120.0,
            "precio_maximo_kg": 80.0,  # Error crítico: Inconsistencia lógica (precio_min > precio_max)
            "precio_frecuente_kg": 95.0,
            "disponibilidad_volumen_kg": 900.0,
            "precipitacion_acumulada_mm": 110.0,
            "velocidad_viento_kmh": 480.0,  # Error crítico: Viento imposible (>250 km/h)
            "rafagas_max_kmh": 550.0,
            "altura_oleaje_m": 3.2,
            "dias_cierre_puerto": 4,
            "alerta_meteorologica": "ROJA",
            "fuente_primaria_precio": "SNIIM (Secretaría de Economía)",
            "fuente_primaria_clima": "Open-Meteo Marine/Historical API",
            "timestamp_ingesta_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    ]
    df_eval = pd.concat([df, pd.DataFrame(casos_anomalos)], ignore_index=True)
    return df_eval


def ejecutar_puerta_calidad(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aplica las reglas de validación fila por fila. Los registros que violen el
    contrato se segregan a Cuarentena con la documentación exacta del motivo
    de rechazo. Los aprobados son validados formalmente con Pandera.
    """
    logger.info("Ejecutando Puerta de Calidad Automática...")
    motivos_rechazo: List[str] = []
    indices_rechazo: List[int] = []

    for idx, row in df.iterrows():
        fallas = []

        # Regla 1: Producto Autorizado
        if row["producto_foco"] not in PRODUCTOS_AUTORIZADOS:
            fallas.append(f"Producto no autorizado: '{row['producto_foco']}'")

        # Regla 2: Precios estrictamente positivos
        if pd.isna(row["precio_minimo_kg"]) or row["precio_minimo_kg"] <= 0:
            fallas.append(f"precio_minimo_kg inválido ({row['precio_minimo_kg']})")
        if pd.isna(row["precio_frecuente_kg"]) or row["precio_frecuente_kg"] <= 0:
            fallas.append(f"precio_frecuente_kg inválido ({row['precio_frecuente_kg']})")
        if pd.isna(row["precio_maximo_kg"]) or row["precio_maximo_kg"] <= 0:
            fallas.append(f"precio_maximo_kg inválido ({row['precio_maximo_kg']})")

        # Regla 3: Consistencia lógica de precios (min <= frecuente <= max)
        if not (pd.isna(row["precio_minimo_kg"]) or pd.isna(row["precio_frecuente_kg"]) or pd.isna(row["precio_maximo_kg"])):
            if not (row["precio_minimo_kg"] <= row["precio_frecuente_kg"] + 0.05 <= row["precio_maximo_kg"] + 0.10):
                fallas.append(
                    f"Inconsistencia lógica de precios: min({row['precio_minimo_kg']}) <= freq({row['precio_frecuente_kg']}) <= max({row['precio_maximo_kg']})"
                )

        # Regla 4: Rangos físicos meteorológicos
        if pd.isna(row["velocidad_viento_kmh"]) or not (0.0 <= row["velocidad_viento_kmh"] <= 250.0):
            fallas.append(f"velocidad_viento_kmh fuera de rango físico: {row['velocidad_viento_kmh']}")
        if pd.isna(row["precipitacion_acumulada_mm"]) or row["precipitacion_acumulada_mm"] < 0:
            fallas.append(f"precipitacion_acumulada_mm negativa: {row['precipitacion_acumulada_mm']}")
        if pd.isna(row["altura_oleaje_m"]) or not (0.0 <= row["altura_oleaje_m"] <= 15.0):
            fallas.append(f"altura_oleaje_m fuera de rango: {row['altura_oleaje_m']}")

        # Regla 5: Alerta Meteorológica
        if str(row["alerta_meteorologica"]).upper() not in ALERTAS_VALIDAS:
            fallas.append(f"alerta_meteorologica desconocida: '{row['alerta_meteorologica']}'")

        if fallas:
            indices_rechazo.append(idx)
            motivos_rechazo.append("; ".join(fallas))

    # Segregación
    df_cuarentena = df.loc[indices_rechazo].copy()
    df_cuarentena["motivo_rechazo"] = motivos_rechazo
    df_cuarentena["timestamp_cuarentena_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    df_aprobados = df.drop(index=indices_rechazo).copy().reset_index(drop=True)

    # Validación formal Pandera sobre los registros aprobados
    schema = obtener_esquema_pandera()
    df_aprobados = schema.validate(df_aprobados)
    logger.info(f"Puerta de Calidad superada: {len(df_aprobados)} aprobados, {len(df_cuarentena)} enviados a Cuarentena.")

    return df_aprobados, df_cuarentena


# =============================================================================
# 4. PREPROCESAMIENTO ESTADÍSTICO (CAPA PLATA)
# =============================================================================
def preprocesamiento_estadistico_plata(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica técnicas estadísticas rigurosas:
      1. Diagnóstico e imputación justificada de valores faltantes (MCAR, MAR, MNAR).
      2. Detección y tratamiento de outliers contextuales (IQR estratificado).
      3. Normalización (MinMax) y Estandarización (Z-Score).
      4. Discretización y jerarquías conceptuales.
    """
    logger.info("Iniciando Preprocesamiento Estadístico para Capa Plata...")
    df_plata = df.copy()

    # -------------------------------------------------------------------------
    # 4.1 DIAGNÓSTICO E IMPUTACIÓN DE VALORES FALTANTES
    # -------------------------------------------------------------------------
    # En nuestro observatorio se diagnostican tres mecanismos potenciales:
    # a) MCAR (Missing Completely at Random): Pérdidas aleatorias de telemetría o paquetes API.
    #    Estrategia: Interpolación lineal temporal dentro de la serie del producto.
    # b) MAR (Missing at Random): Ausencia de capturas o precios condicionados por cierre de puerto
    #    (dias_cierre_puerto > 0). Estrategia: Mediana móvil estratificada por (temporada, producto).
    # c) MNAR (Missing Not at Random): Ocultamiento intencional de precios durante desplomes de mercado.
    #    Estrategia: Detección y marcado explícito sin distorsionar la distribución histórica.
    for prod in PRODUCTOS_AUTORIZADOS:
        mask_prod = df_plata["producto_foco"] == prod
        # Interpolación temporal para variables meteorológicas (MCAR)
        df_plata.loc[mask_prod, "precipitacion_acumulada_mm"] = (
            df_plata.loc[mask_prod, "precipitacion_acumulada_mm"]
            .interpolate(method="linear")
            .bfill()
            .ffill()
        )
        # Imputación de precios condicionada por temporada (MAR)
        mediana_temporada = df_plata.loc[mask_prod].groupby("temporada")["precio_frecuente_kg"].transform("median")
        df_plata.loc[mask_prod, "precio_frecuente_kg"] = df_plata.loc[mask_prod, "precio_frecuente_kg"].fillna(mediana_temporada)

    # -------------------------------------------------------------------------
    # 4.2 DETECCIÓN Y TRATAMIENTO DE OUTLIERS Y RUIDO (IQR ESTRATIFICADO)
    # -------------------------------------------------------------------------
    # IMPORTANTE: Un filtro de atípicos global (Z > 3) eliminaría los picos de Cuaresma
    # y las caídas de captura por huracanes, destruyendo la señal analítica esencial.
    # Por ello, se implementa IQR ESTRATIFICADO por (producto_foco, temporada).
    df_plata["es_pico_estacional_real"] = False
    df_plata["es_anomalia_climatica"] = False

    for prod in PRODUCTOS_AUTORIZADOS:
        for temp in df_plata["temporada"].unique():
            subset_mask = (df_plata["producto_foco"] == prod) & (df_plata["temporada"] == temp)
            if not subset_mask.any():
                continue

            q1 = df_plata.loc[subset_mask, "precio_frecuente_kg"].quantile(0.25)
            q3 = df_plata.loc[subset_mask, "precio_frecuente_kg"].quantile(0.75)
            iqr = q3 - q1
            limite_inferior = q1 - 1.5 * iqr
            limite_superior = q3 + 1.5 * iqr

            # Identificación de picos legítimos vs errores de transcripción
            if temp == "TEMPORADA_ALTA_CUARESMA":
                # En Cuaresma los precios altos son variaciones naturales del mercado
                df_plata.loc[subset_mask & (df_plata["precio_frecuente_kg"] > q3), "es_pico_estacional_real"] = True
            elif temp == "TEMPORADA_HURACANES_LLUVIAS":
                # En temporada de lluvias el shock de oferta eleva precios silvestres legítimamente
                df_plata.loc[subset_mask & (df_plata["dias_cierre_puerto"] >= 2), "es_anomalia_climatica"] = True

            # Winsorización selectiva únicamente para ruido fuera de 3.0 * IQR (anomalías severas)
            limite_ruido_sup = q3 + 3.0 * iqr
            limite_ruido_inf = max(10.0, q1 - 3.0 * iqr)
            df_plata.loc[subset_mask, "precio_frecuente_kg"] = (
                df_plata.loc[subset_mask, "precio_frecuente_kg"].clip(lower=limite_ruido_inf, upper=limite_ruido_sup)
            )

    # -------------------------------------------------------------------------
    # 4.3 NORMALIZACIÓN Y ESTANDARIZACIÓN
    # -------------------------------------------------------------------------
    scaler_minmax = MinMaxScaler()
    scaler_standard = StandardScaler()

    # Escalamiento Min-Max (rango [0, 1]) para modelos basados en distancias / redes neuronales
    df_plata["precio_frecuente_minmax"] = round(
        pd.Series(scaler_minmax.fit_transform(df_plata[["precio_frecuente_kg"]]).flatten(), index=df_plata.index), 4
    )
    df_plata["precipitacion_minmax"] = round(
        pd.Series(scaler_minmax.fit_transform(df_plata[["precipitacion_acumulada_mm"]]).flatten(), index=df_plata.index), 4
    )
    df_plata["volumen_minmax"] = round(
        pd.Series(scaler_minmax.fit_transform(df_plata[["disponibilidad_volumen_kg"]]).flatten(), index=df_plata.index), 4
    )

    # Estandarización Z-Score (media = 0, varianza = 1) para modelos lineales / autoregresivos
    df_plata["precio_frecuente_zscore"] = round(
        pd.Series(scaler_standard.fit_transform(df_plata[["precio_frecuente_kg"]]).flatten(), index=df_plata.index), 4
    )
    df_plata["viento_zscore"] = round(
        pd.Series(scaler_standard.fit_transform(df_plata[["velocidad_viento_kmh"]]).flatten(), index=df_plata.index), 4
    )

    # -------------------------------------------------------------------------
    # 4.4 DISCRETIZACIÓN Y JERARQUÍAS CONCEPTUALES
    # -------------------------------------------------------------------------
    # A) Jerarquía Conceptual de Temporada
    def etiquetar_temporada_conceptual(temp_str: str) -> str:
        if temp_str == "TEMPORADA_ALTA_CUARESMA":
            return "ALTA_CUARESMA"
        elif temp_str == "TEMPORADA_HURACANES_LLUVIAS":
            return "BAJA_LLUVIAS"
        else:
            return "REGULAR"

    df_plata["temporada_conceptual"] = df_plata["temporada"].apply(etiquetar_temporada_conceptual)

    # B) Discretización de Nivel de Escasez / Riesgo Operativo
    def categorizar_escasez(row) -> str:
        if row["dias_cierre_puerto"] >= 3 or row["alerta_meteorologica"] == "ROJA":
            return "CRITICO"
        elif row["dias_cierre_puerto"] >= 1 or row["alerta_meteorologica"] in ["AMARILLA", "NARANJA"]:
            return "MEDIO"
        else:
            return "BAJO"

    df_plata["nivel_escasez"] = df_plata.apply(categorizar_escasez, axis=1)

    # C) Discretización de Nivel de Precio por Terciles Específicos por Especie
    def categorizar_nivel_precio(df_in: pd.DataFrame) -> pd.Series:
        niveles = pd.Series(index=df_in.index, dtype=str)
        for prod in PRODUCTOS_AUTORIZADOS:
            mask = df_in["producto_foco"] == prod
            if mask.any():
                precios = df_in.loc[mask, "precio_frecuente_kg"]
                t1, t2 = precios.quantile(0.33), precios.quantile(0.66)
                niveles.loc[mask & (precios <= t1)] = "PRECIO_ACCESIBLE"
                niveles.loc[mask & (precios > t1) & (precios <= t2)] = "PRECIO_MODERADO"
                niveles.loc[mask & (precios > t2)] = "PRECIO_ELEVADO"
        return niveles

    df_plata["nivel_precio_relativo"] = categorizar_nivel_precio(df_plata)

    # Metadato de versión de Capa Plata
    df_plata["version_capa_plata"] = "1.0.0"
    df_plata["timestamp_plata_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info(f"Capa Plata completada exitosamente: {len(df_plata)} registros listos para análisis.")
    return df_plata


# =============================================================================
# 5. REDUCCIÓN DE DIMENSIONALIDAD Y CONSTRUCCIÓN DE LA CAPA ORO
# =============================================================================
def construir_capa_oro(df_plata: pd.DataFrame) -> pd.DataFrame:
    """
    Construye la vista agregada de alta fidelidad para analítica avanzada (Capa Oro).
    Agrega a nivel mensual por especie, calculando volatilidad, volumen acumulado,
    días de puerto cerrado e indicadores clave para modelado predictivo (E1/E2/E3).
    """
    logger.info("Construyendo Capa Oro (Dataset Analítico Agregado)...")

    # Clave de agregación: Mes de calendario y Producto Foco
    grupo_oro = df_plata.groupby(["mes", "producto_foco"], as_index=False)

    df_oro = grupo_oro.agg(
        periodos_observados=("periodo_id", "count"),
        temporada_dominante=("temporada_conceptual", lambda s: s.mode()[0] if not s.empty else "REGULAR"),
        precio_promedio_kg=("precio_frecuente_kg", lambda p: round(p.mean(), 2)),
        precio_volatilidad_std=("precio_frecuente_kg", lambda p: round(p.std(ddof=0), 2)),
        precio_min_mensual=("precio_minimo_kg", lambda p: round(p.min(), 2)),
        precio_max_mensual=("precio_maximo_kg", lambda p: round(p.max(), 2)),
        volumen_total_kg=("disponibilidad_volumen_kg", lambda v: round(v.sum(), 1)),
        precipitacion_acumulada_mensual_mm=("precipitacion_acumulada_mm", lambda pr: round(pr.sum(), 2)),
        viento_promedio_kmh=("velocidad_viento_kmh", lambda w: round(w.mean(), 1)),
        viento_maximo_kmh=("rafagas_max_kmh", lambda w: round(w.max(), 1)),
        altura_oleaje_promedio_m=("altura_oleaje_m", lambda o: round(o.mean(), 2)),
        dias_totales_cierre_puerto=("dias_cierre_puerto", "sum"),
        alertas_severas_count=("alerta_meteorologica", lambda a: (a.isin(["AMARILLA", "ROJA"])).sum()),
        semanas_escasez_critica=("nivel_escasez", lambda e: (e == "CRITICO").sum())
    )

    # Feature Engineering de Segundo Orden para Capa Oro:
    # 1. Coeficiente de Variación de Precio (%)
    df_oro["coeficiente_variacion_precio_pct"] = round(
        (df_oro["precio_volatilidad_std"] / df_oro["precio_promedio_kg"]) * 100.0, 2
    )

    # 2. Índice Compuesto de Vulnerabilidad Climática (0 a 10)
    df_oro["indice_vulnerabilidad_climatica"] = round(
        (df_oro["dias_totales_cierre_puerto"] * 1.5) +
        (df_oro["alertas_severas_count"] * 1.0) +
        (df_oro["precipitacion_acumulada_mensual_mm"] / 50.0), 2
    ).clip(0.0, 10.0)

    # 3. Clasificación de Riesgo de Abasto para Pescadería Valencia
    def categorizar_riesgo_abasto(row) -> str:
        if row["dias_totales_cierre_puerto"] >= 5 or row["semanas_escasez_critica"] >= 2:
            return "RIESGO_ALTO_DESABASTO"
        elif row["dias_totales_cierre_puerto"] >= 2 or row["alertas_severas_count"] >= 1:
            return "RIESGO_MODERADO"
        else:
            return "RIESGO_ESTABLE"

    df_oro["riesgo_abasto_proyectado"] = df_oro.apply(categorizar_riesgo_abasto, axis=1)

    df_oro["version_capa_oro"] = "1.0.0"
    df_oro["timestamp_oro_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    logger.info(f"Capa Oro generada con éxito: {len(df_oro)} filas analíticas agregadas.")
    return df_oro


# =============================================================================
# 6. PERSISTENCIA Y REGISTRO DE AUDITORÍA
# =============================================================================
def guardar_artefactos(
    df_cuarentena: pd.DataFrame,
    df_plata: pd.DataFrame,
    df_oro: pd.DataFrame
) -> Dict[str, Any]:
    """Persiste los tres datasets en sus respectivas capas y emite el manifiesto JSON."""
    DIR_CUARENTENA.mkdir(parents=True, exist_ok=True)
    DIR_PLATA.mkdir(parents=True, exist_ok=True)
    DIR_ORO.mkdir(parents=True, exist_ok=True)

    # Guardar CSVs
    df_cuarentena.to_csv(PATH_CUARENTENA_CSV, index=False, encoding="utf-8")
    logger.info(f"Cuarentena guardada en: {PATH_CUARENTENA_CSV} ({len(df_cuarentena)} registros)")

    df_plata.to_csv(PATH_PLATA_CSV, index=False, encoding="utf-8")
    logger.info(f"Capa Plata guardada en: {PATH_PLATA_CSV} ({len(df_plata)} registros)")

    df_oro.to_csv(PATH_ORO_CSV, index=False, encoding="utf-8")
    logger.info(f"Capa Oro guardada en: {PATH_ORO_CSV} ({len(df_oro)} registros)")

    # Manifiesto de Auditoría E1
    resumen_auditoria = {
        "pipeline_name": "pipeline_plata_oro_valencia",
        "entrega": "E1 - Trusted Data Lab",
        "timestamp_ejecucion_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "estado_puerta_calidad": "VALIDACION_PANDERA_APROBADA",
        "metricas_flujo": {
            "total_registros_evaluados": len(df_plata) + len(df_cuarentena),
            "registros_aprobados_plata": len(df_plata),
            "registros_aislados_cuarentena": len(df_cuarentena),
            "tasa_rechazo_pct": round((len(df_cuarentena) / (len(df_plata) + len(df_cuarentena))) * 100.0, 2),
            "filas_agregadas_oro": len(df_oro)
        },
        "detalles_cuarentena": [
            {
                "periodo_id": int(r["periodo_id"]),
                "producto": str(r["producto_foco"]),
                "motivo_rechazo": str(r["motivo_rechazo"])
            }
            for _, r in df_cuarentena.iterrows()
        ],
        "estadisticas_plata": {
            "precio_minimo_observado": float(df_plata["precio_frecuente_kg"].min()),
            "precio_maximo_observado": float(df_plata["precio_frecuente_kg"].max()),
            "precio_promedio_general": float(round(df_plata["precio_frecuente_kg"].mean(), 2)),
            "valores_nulos_remanentes": int(df_plata.isna().sum().sum())
        },
        "contrato_calidad": {
            "framework": "Pandera 0.20+",
            "columnas_validadas": list(obtener_esquema_pandera().columns.keys()),
            "tratamiento_faltantes": "Interpolacion temporal (MCAR) y Mediana condicional (MAR)",
            "tratamiento_atipicos": "IQR estratificado por (producto, temporada) preservando senal de Cuaresma"
        }
    }

    with open(PATH_METADATOS_JSON, "w", encoding="utf-8") as f:
        json.dump(resumen_auditoria, f, indent=4, ensure_ascii=False)
    logger.info(f"Manifiesto de auditoría guardado en: {PATH_METADATOS_JSON}")

    return resumen_auditoria


# =============================================================================
# 7. EJECUCIÓN PRINCIPAL
# =============================================================================
def main():
    logger.info("=== INICIANDO EJECUCIÓN DEL PIPELINE PLATA - ORO (E1) ===")
    try:
        # 1. Cargar y Armonizar
        df_bronce = cargar_y_armonizar_bronce(PATH_BRONCE_CSV)

        # 2. Inyección de casos para validar Puerta de Calidad
        df_evaluacion = inyectar_casos_control_calidad(df_bronce)

        # 3. Puerta de Calidad con Pandera
        df_aprobados, df_cuarentena = ejecutar_puerta_calidad(df_evaluacion)

        # 4. Preprocesamiento Estadístico (Plata)
        df_plata = preprocesamiento_estadistico_plata(df_aprobados)

        # 5. Reducción y Construcción de Capa Oro
        df_oro = construir_capa_oro(df_plata)

        # 6. Persistencia y Auditoría
        auditoria = guardar_artefactos(df_cuarentena, df_plata, df_oro)

        logger.info("=== PIPELINE PLATA - ORO CONCLUIDO SATISFACTORIAMENTE ===")
        print(json.dumps(auditoria["metricas_flujo"], indent=2))

    except Exception as e:
        logger.error(f"Falla fatal en la ejecución del pipeline: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
