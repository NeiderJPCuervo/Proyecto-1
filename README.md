# 🔎 Veedor SECOP

**Vigilancia ciudadana automatizada de la contratación pública en Colombia.**

Veedor SECOP descarga a diario los contratos públicos publicados en
[SECOP II](https://www.datos.gov.co/) (datos abiertos del Estado colombiano) y los guarda en
PostgreSQL. Sobre ellos corre un **motor de banderas rojas** que detecta patrones de riesgo
(montos atípicos, posible fraccionamiento, concentración de proveedores, abuso de la contratación
directa) y calcula un **puntaje de riesgo** por contrato y por entidad. **n8n** orquesta el proceso
y envía alertas por Telegram o email.

> ⚠️ **Aviso:** una bandera roja es una **señal estadística** para priorizar la revisión
> ciudadana. **No es prueba de irregularidad ni de corrupción.**

## Arquitectura

```
                ┌──────────────┐  cron / webhooks   ┌──────────────────────────────┐
                │     n8n      │ ─────────────────▶ │   API (FastAPI, Python)      │
                │ orquestación │ ◀───────────────── │  api → application → domain  │
                │  y alertas   │   JSON (X-API-Key) │         ↓ infrastructure     │
                └──────┬───────┘                    └──────┬───────────────┬───────┘
          Telegram /   │                                   │               │
          email  ◀─────┘                          ┌────────▼──────┐  ┌─────▼──────────┐
                                                  │  PostgreSQL   │  │ datos.gov.co   │
                ┌──────────────┐                  │ contratos,    │  │ (API SECOP II) │
                │  Dashboard   │ ───────────────▶ │ banderas, ... │  └────────────────┘
                │ (Streamlit)  │                  └───────────────┘
                └──────────────┘
```

- **n8n** decide *cuándo* ejecutar y *a quién* avisar.
- **Python** decide *qué* se calcula: ingesta ETL, reglas de riesgo y reportes.
- **Clean architecture**: las reglas de negocio (`domain`) no dependen de la base de datos ni de
  HTTP, así que se prueban de forma aislada.

## Stack

Python 3.12 · FastAPI · Pydantic · SQLAlchemy 2 + Alembic · PostgreSQL 16 · n8n · Streamlit ·
Docker Compose · pytest · ruff · GitHub Actions

## Hoja de ruta

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Entorno, estructura del repo, herramientas | ✅ |
| 1 | Exploración de los datos de SECOP II | ✅ |
| 2 | Base de datos: modelo relacional, Docker, migraciones | ⏳ |
| 3 | Ingesta ETL incremental e idempotente | ⏳ |
| 4 | Motor de banderas rojas + puntaje de riesgo | ⏳ |
| 5 | API REST con FastAPI | ⏳ |
| 6 | Automatizaciones con n8n (ingesta diaria, alertas, reportes) | ⏳ |
| 7 | Dashboard con Streamlit | ⏳ |
| 8 | Calidad: CI/CD, logging, documentación | ⏳ |
| 9 | IA opcional: resúmenes y clasificación de contratos | ⏳ |
| 10 | Despliegue y publicación | ⏳ |

Las guías paso a paso de cada fase están en [`docs/fases/`](docs/fases/).

## Inicio rápido

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Explorar los datos de ejemplo (no requiere internet)
python -m scripts.explorar_secop --desde-archivo tests/fixtures/secop_contratos_muestra.json

# Explorar datos reales
python -m scripts.explorar_secop --limite 2000 --guardar data/muestra.json

# Pruebas y estilo de código
pytest
ruff check .
```

## Estructura

```
.
├── backend/
│   ├── scripts/explorar_secop.py   # Fase 1: descarga y análisis exploratorio
│   ├── tests/                      # pruebas automáticas + datos de ejemplo
│   └── pyproject.toml              # dependencias y configuración
├── docs/fases/                     # guías de aprendizaje de cada fase
└── .env.example                    # plantilla de configuración
```

Los datos de `backend/tests/fixtures/` son **ficticios**. Imitan la estructura de SECOP II para
poder hacer pruebas sin conexión, pero no corresponden a entidades ni contratos reales.
