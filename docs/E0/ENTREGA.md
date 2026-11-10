# Ficha Técnica de Entrega — Hito [E0]
## Observatorio de Precios y Disponibilidad para Pescadería Valencia

| Atributo | Detalle |
| :--- | :--- |
| **Proyecto** | Observatorio de Precios y Disponibilidad de Mariscos |
| **Hito / Entrega** | **[E0] Trusted Data Lab: Arranque, Propuesta y Máquina de Captura** |
| **Estudiante / Ingeniero PSP** | **Felipe Sandoval** |
| **Organización Receptora** | Pescadería Valencia (Colima / Manzanillo) |
| **Fecha de Validación** | 10 de noviembre de 2026 |
| **Etiqueta Git (Release Tag)** | `e0` |
| **Estado de la Entrega** | **COMPLETADO / LISTO PARA EVALUACIÓN** |

---

## 1. Resumen Ejecutivo del Proyecto

La **Pescadería Valencia**, ubicada en el estado de Colima con centro de acopio ribereño en el puerto de Manzanillo, enfrenta severas dificultades operacionales originadas por la doble volatilidad de la cadena de suministro marina:
1. **Inestabilidad del abasto de captura silvestre** (especialmente Huachinango del Pacífico y Filete de Pez Vela), fuertemente condicionada por eventos hidrometeorológicos, mar de fondo y cierres de capitanía de puerto durante la temporada de lluvias y huracanes (septiembre a octubre).
2. **Inflación impredecible en compras spot** de especies acuícolas y de alta rotación (como la Mojarra / Tilapia fresca), que sufre escaladas abruptas de precio superiores al 50% durante la Cuaresma y Semana Santa (febrero a abril).

El presente proyecto implementa un **Trusted Data Lab** sobre arquitectura Medallion en GitHub, integrando fuentes de información de precios mayoristas oficiales (**SNIIM**) y variables marítimo-climatológicas oficiales (**APIs meteorológicas**) para proveer alertas tempranas de desabasto y pronósticos predictivos a 30 días para la toma de decisiones de inventario y compras preventivas.

---

## 2. Checklist de Cumplimiento de Criterios de Aceptación (Rúbrica E0)

| ID | Criterio de Evaluación / Entregable | Estado | Evidencia / Ruta de Archivo |
| :---: | :--- | :---: | :--- |
| **C1** | **Ficha del Observatorio:** Definición de sector (pesquero/alimentario), región (Colima/Manzanillo), cliente potencial (Pescadería Valencia) y pregunta detonadora. |  Cumplido | [`docs/E0/propuesta.md`](propuesta.md#1-ficha-del-observatorio) (Sección 1) |
| **C2** | **Entrevista de Campo (15 min):** Levantamiento estructurado de 5 preguntas/respuestas realistas con el dueño (Don Aurelio Valencia) sobre escasez, lluvias, Cuaresma y precios. |  Cumplido | [`docs/E0/propuesta.md`](propuesta.md#2-diagnóstico-del-negocio-y-entrevista-de-campo-15-minutos) (Sección 2) |
| **C3** | **3 Preguntas Analíticas de Negocio:** E1 (Pronóstico 30 días), E2 (Alertas meteorológicas vs. desabasto) y E3 (Comparación multivariada Cuaresma vs. Lluvias). |  Cumplido | [`docs/E0/propuesta.md`](propuesta.md#3-las-tres-preguntas-analíticas-de-negocio) (Sección 3) |
| **C4** | **Plan de Recopilación (Mín. 2 fuentes):** Especificación de SNIIM y API meteorológica (Open-Meteo / OpenWeatherMap) para Manzanillo. |  Cumplido | [`docs/E0/propuesta.md`](propuesta.md#4-plan-de-recopilación-de-datos-y-estrategia-de-ingesta) (Sección 4) |
| **C5** | **Análisis Ético y Legal:** Evaluación de `robots.txt` (Crawl-delay 5s, User-Agent), Términos de Servicio (ToS), Ley General de Transparencia (datos abiertos) y no recolección de PII. |  Cumplido | [`docs/E0/propuesta.md`](propuesta.md#5-análisis-ético-legal-y-de-cumplimiento-normativo-compliance) (Sección 5) |
| **C6** | **Máquina de Captura CI/CD:** GitHub Actions configurado con trigger cron semanal y manual para ingesta desatendida. |  Cumplido | [`.github/workflows/extractor.yml`](../../.github/workflows/extractor.yml) |
| **C7** | **Script Extractor Capa Bronce:** Código Python modular que extrae/simula una serie histórica calibrada de 36 periodos cronológicos con contrato de datos. |  Cumplido | [`src/extractor_bronce.py`](../../src/extractor_bronce.py) |
| **C8** | **Dataset Crudo Inicial (36 periodos):** Datos históricos generados en CSV y manifiesto de metadatos en JSON en la capa Bronce. |  Cumplido | [`data/bronce/precios_clima_historico_36p.csv`](../../data/bronce/precios_clima_historico_36p.csv) y [`data/bronce/metadatos_extraccion.json`](../../data/bronce/metadatos_extraccion.json) |
| **C9** | **Bitácoras de Calidad PSP:** Registro detallado de tiempos por fase y bitácora de defectos encontrados/removidos a nombre de Felipe Sandoval. |  Cumplido | [`calidad/tiempo-felipe.csv`](../../calidad/tiempo-felipe.csv) y [`calidad/defectos-felipe.csv`](../../calidad/defectos-felipe.csv) |

---

## 3. Resumen de la Serie Histórica Generada en Capa Bronce

El script [`src/extractor_bronce.py`](../../src/extractor_bronce.py) fue ejecutado y validado en el entorno local con los siguientes resultados métricos:

- **Total de Periodos Semanales:** 36 semanas continuas (del 2025-06-02 al 2026-02-08).
- **Total de Registros en CSV:** 108 filas (36 semanas × 3 especies: Mojarra fresca, Huachinango del Pacífico y Filete de vela).
- **Rango de Precios Registrado:**
  - Mínimo absoluto: **\$71.16 MXN/kg** (Mojarra en periodo regular).
  - Máximo absoluto: **\$298.54 MXN/kg** (Huachinango en pico de Cuaresma con mar de fondo).
  - Promedio general: **\$144.33 MXN/kg**.
- **Variables Hidrometeorológicas Involucradas:**
  - Precipitación acumulada semanal (rango: 0.0 mm a 157.8 mm).
  - Velocidad y ráfagas máximas de viento (hasta 88.5 km/h en eventos de tormenta).
  - Altura de oleaje en Manzanillo (hasta 3.7 metros en alertas rojas de mar de fondo).
  - Días de cierre oficial de puerto (0 a 5 días por semana de temporal).

---

## 4. Instrucciones para Reproducir Localmente

### 4.1 Clonar el Repositorio y Configurar Entorno
```bash
git clone https://github.com/<tu-usuario>/observatorio-pescaderia-valencia.git
cd observatorio-pescaderia-valencia

# Crear entorno virtual de Python
python -m venv .venv

# Activar entorno virtual
# En Windows PowerShell:
.venv\Scripts\Activate.ps1
# En Linux / macOS:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 4.2 Ejecutar la Máquina de Captura Bronce
```bash
python src/extractor_bronce.py
```
Salida esperada:
```
[INFO] === INICIANDO EXTRACCIÓN Y PIPELINE CAPA BRONCE (E0) ===
[INFO] Iniciando generación de serie histórica sintética calibrada (36 periodos)...
[INFO] Serie sintética construida con éxito: 108 registros (36 semanas x 3 especies).
[INFO] Archivo CSV guardado en: data/bronce/precios_clima_historico_36p.csv
[INFO] Metadatos JSON guardados en: data/bronce/metadatos_extraccion.json
[INFO] === PIPELINE CAPA BRONCE CONCLUIDO CON ÉXITO ===
```

---

## 5. Comandos para Etiquetar y Publicar la Entrega con Git Tag `e0`

Para congelar formalmente el estado del repositorio y asociarlo a la entrega académica de la Entrega [E0], ejecuta la siguiente secuencia de comandos desde la raíz del proyecto:

```bash
# 1. Asegurar que todos los archivos requeridos estén en el área de preparación (stage)
git add .

# 2. Confirmar el estado de los archivos agregados
git status

# 3. Crear el commit de cierre de entrega E0
git commit -m "feat(E0): entrega de Trusted Data Lab - arranque, propuesta y maquina de captura"

# 4. Crear la etiqueta anotada (annotated git tag) 'e0'
git tag -a e0 -m "Entrega E0: Trusted Data Lab - Arranque, Propuesta y Maquina de Captura (Felipe Sandoval)"

# 5. Enviar los cambios de la rama principal a GitHub
git push origin main

# 6. Publicar la etiqueta oficial 'e0' en el repositorio remoto
git push origin e0
```

### 5.1 Comprobación de la Etiqueta Creada
```bash
# Verificar los detalles de la etiqueta e0
git show e0
```
