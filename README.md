# Observatorio de Precios y Disponibilidad: Pescadería Valencia

[![Pipeline Medallion](https://github.com/usuario/observatorio-pescaderia-valencia/actions/workflows/extractor.yml/badge.svg)](https://github.com/usuario/observatorio-pescaderia-valencia/actions/workflows/extractor.yml)
[![Entrega E0](https://img.shields.io/badge/Entrega-E0%20(Completado)-brightgreen.svg)](#)
[![Entrega E1](https://img.shields.io/badge/Entrega-E1%20(Completado)-brightgreen.svg)](#)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](#)
[![Calidad Pandera](https://img.shields.io/badge/Calidad-Pandera%20Validado-orange.svg)](#)
[![Arquitectura](https://img.shields.io/badge/Arquitectura-Medallion%20(Bronce%20%7C%20Plata%20%7C%20Oro)-purple.svg)](#)

> **Trusted Data Lab:** Plataforma de analítica predictiva y observabilidad de la cadena de suministro marina para **Pescadería Valencia** en Colima y Manzanillo, México.

---

## 🎯 Objetivo General
Anticipar y mitigar el desabasto y la volatilidad imprevista en el precio de adquisición de pescados frescos clave (**Mojarra Fresca Entera**, **Huachinango del Pacífico** y **Filete de Pez Vela**) mediante la ingesta continua, modelado y correlación analítica entre precios mayoristas (SNIIM) y variables hidrometeorológicas del litoral del Pacífico mexicano.

---

## 📁 Estructura del Repositorio

```
observatorio-pescaderia-valencia/
│
├── .github/
│   └── workflows/
│       └── extractor.yml         # GitHub Actions: Orquestador Medallion semanal
│
├── calidad/
│   ├── tiempo-felipe.csv        # Bitácora PSP de gestión de tiempos por fase (E0 y E1)
│   └── defectos-felipe.csv      # Bitácora PSP de registro y remoción de defectos (E0 y E1)
│
├── data/
│   ├── bronce/
│   │   ├── precios_clima_historico_36p.csv  # Serie cruda calibrada (36 periodos)
│   │   └── metadatos_extraccion.json        # Manifiesto y contrato de ingesta
│   ├── cuarentena/
│   │   └── registros_invalidos.csv          # Registros rechazados por la Puerta de Calidad
│   ├── plata/
│   │   └── datos_limpios.csv                # Datos curados, imputados, escalados y discretizados
│   └── oro/
│       ├── dataset_analitico.csv            # Dataset mensual agregado para modelos predictivos
│       └── metadatos_pipeline_e1.json       # Auditoría y métricas del pipeline de calidad
│
├── docs/
│   ├── E0/
│   │   ├── propuesta.md         # Documento maestro de propuesta y arquitectura E0
│   │   └── ENTREGA.md           # Ficha técnica y checklist de git tag e0
│   ├── E1/
│   │   ├── limpieza.ipynb       # Notebook interactivo documentado paso a paso
│   │   └── ENTREGA.md           # Ficha técnica de entrega y checklist de git tag e1
│   └── relatoria-E1.md          # Relatoría técnica detallada sobre estadística y decisiones
│
├── src/
│   ├── extractor_bronce.py      # Motor de extracción y captura capa Bronce
│   └── pipeline_plata_oro.py    # Pipeline de integración, Puerta de Calidad Pandera y Capa Oro
│
├── requirements.txt             # Dependencias del proyecto
└── README.md                    # Documentación principal
```

---

## 🚀 Inicio Rápido

```bash
# 1. Clonar el repositorio
git clone https://github.com/<tu-usuario>/observatorio-pescaderia-valencia.git
cd observatorio-pescaderia-valencia

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar la máquina de captura Bronce
python src/extractor_bronce.py

# 4. Ejecutar el pipeline de Calidad, Limpieza y Generación Plata/Oro
python src/pipeline_plata_oro.py
```

---

## 📋 Documentación de Entregas
- **[Entrega E0 - Propuesta y Arranque](docs/E0/propuesta.md)** | **[Ficha E0](docs/E0/ENTREGA.md)**
- **[Entrega E1 - Capa Plata y Puerta de Calidad](docs/E1/ENTREGA.md)** | **[Relatoría Técnica E1](docs/relatoria-E1.md)** | **[Notebook E1](docs/E1/limpieza.ipynb)**

---
**Responsable del Proyecto:** Felipe Sandoval | Lead Data Engineer  
**Contacto Operativo:** Pescadería Valencia (Colima / Manzanillo)
