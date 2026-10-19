# Fase 0 — Preparar el entorno

Meta: tener tu computador listo y entender **por qué** existe cada archivo base del repositorio.

## 1. Instala las herramientas

| Herramienta | Para qué | Verifica con |
|---|---|---|
| [Python 3.12+](https://www.python.org/downloads/) | el lenguaje del backend | `python --version` |
| [Git](https://git-scm.com/) | control de versiones | `git --version` |
| [VS Code](https://code.visualstudio.com/) + extensión *Python* | editor | — |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | correr PostgreSQL y n8n sin instalarlos a mano (desde la Fase 2) | `docker --version` |

En Windows, marca **"Add Python to PATH"** al instalar Python.

## 2. Clona el repositorio y cambia a la rama de trabajo

```bash
git clone https://github.com/NeiderJPCuervo/Proyecto-1.git
cd Proyecto-1
git checkout claude/portfolio-python-n8n-project-j5fjvm
```

## 3. Crea un entorno virtual

Un **entorno virtual** (`.venv`) es una carpeta con una copia aislada de Python y sus librerías
para este proyecto. Así las versiones de este proyecto no chocan con las de otros.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

- `-e` ("editable"): instala el proyecto apuntando a tu código. Si editas un archivo, el cambio
  se refleja de inmediato.
- `[dev]`: además instala las herramientas de desarrollo (pytest, ruff).

Sabrás que el entorno está activo porque la terminal muestra `(.venv)` al inicio.

## 4. Los archivos base, explicados

| Archivo | Por qué existe |
|---|---|
| `backend/pyproject.toml` | Declara el proyecto, sus dependencias y la configuración de pytest y ruff. Es el estándar moderno; reemplaza a `requirements.txt` + `setup.py`. |
| `.gitignore` | Lista lo que git **no** debe subir: el entorno virtual, cachés, datos descargados y, sobre todo, `.env` con tus contraseñas. |
| `.env.example` | Plantilla de configuración **sin secretos**. Cada persona la copia como `.env` y pone sus valores. Así el código no tiene contraseñas escritas a mano (principio *12-factor app*). |
| `README.md` | La portada del proyecto. Un reclutador decide en 30 segundos si sigue leyendo. |

## 5. Flujo de git que usaremos

```bash
git status                 # ¿qué cambió?
git add archivo.py         # preparar cambios
git commit -m "Fase 2: modelo de datos inicial"   # guardar una "foto" con un mensaje claro
git push                   # subir a GitHub
```

Regla de oro: **commits pequeños con mensajes que expliquen el porqué**. El historial de git
también es parte de tu portafolio.

## ✅ Checklist

- [ ] `python --version` muestra 3.12 o superior
- [ ] El entorno virtual está activo y `pip install -e ".[dev]"` terminó sin errores
- [ ] `pytest` muestra los tests en verde
- [ ] `ruff check .` dice `All checks passed!`
