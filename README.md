# Observatorio de Precios y Disponibilidad: Pescadería Valencia

[![Extractor Bronce](https://github.com/usuario/observatorio-pescaderia-valencia/actions/workflows/extractor.yml/badge.svg)](https://github.com/usuario/observatorio-pescaderia-valencia/actions/workflows/extractor.yml)
[![Entrega E0](https://img.shields.io/badge/Entrega-E0%20(Completado)-brightgreen.svg)](#)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](#)
[![Arquitectura](https://img.shields.io/badge/Arquitectura-Medallion%20(Bronce)-orange.svg)](#)

> **Trusted Data Lab:** Plataforma de analítica predictiva y observabilidad de la cadena de suministro marina para **Pescadería Valencia** en Colima y Manzanillo, México.

---

## 🎯 Objetivo General
Anticipar y mitigar el desabasto y la volatilidad imprevista en el precio de adquisición de pescados frescos clave (**Mojarra**, **Huachinango** y **Filete de Pez Vela**) mediante la ingesta continua, modelado y correlación analítica entre precios mayoristas (SNIIM) y variables hidrometeorológicas del litoral del Pacífico mexicano.

---

## 📁 Estructura del Repositorio

```
observatorio-pescaderia-valencia/
│
├── .github/
│   └── workflows/
│       └── extractor.yml         # GitHub Actions: Orquestador semanal de ingesta
│
├── calidad/
│   ├── tiempo-felipe.csv        # Bitácora PSP de gestión de tiempos por fase
│   └── defectos-felipe.csv      # Bitácora PSP de registro y remoción de defectos
│
├── data/
│   └── bronce/
│       ├── precios_clima_historico_36p.csv  # Serie cruda calibrada (36 periodos)
│       └── metadatos_extraccion.json        # Manifiesto y contrato de ingesta
│
├── docs/
│   └── E0/
│       ├── propuesta.md         # Documento maestro de propuesta y arquitectura
│       └── ENTREGA.md           # Ficha de entrega técnica y checklist de git tag e0
│
├── src/
│   └── extractor_bronce.py      # Motor de extracción y captura capa Bronce
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
```

---

## 📋 Documentación de Entregas
- **[Entrega E0 - Documento de Propuesta](docs/E0/propuesta.md):** Ficha técnica, transcripción de entrevista de campo, 3 preguntas analíticas, plan de recopilación y análisis ético/legal.
- **[Entrega E0 - Ficha de Cierre y Verificación](docs/E0/ENTREGA.md):** Matriz de cumplimiento de rúbrica y comandos oficiales para etiquetar con `git tag e0`.

---
**Responsable del Proyecto:** Felipe Sandoval | PSP Data Engineer  
**Contacto Operativo:** Pescadería Valencia (Colima / Manzanillo)
