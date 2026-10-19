"""Fase 1 — Exploración de los datos de SECOP II.

Objetivo: entender los datos ANTES de diseñar la base de datos.
¿Qué columnas hay? ¿Qué tan sucias están? ¿Qué formatos usan las fechas y los montos?

Uso (desde la carpeta `backend/`):

    # Descargar 2000 contratos reales y guardarlos para no repetir la descarga
    python -m scripts.explorar_secop --limite 2000 --guardar data/muestra.json

    # Filtrar con SoQL (el "SQL" de la API de datos.gov.co)
    python -m scripts.explorar_secop --limite 500 --where "departamento = 'Antioquia'"

    # Trabajar sin internet con los datos de ejemplo del repositorio
    python -m scripts.explorar_secop --desde-archivo tests/fixtures/secop_contratos_muestra.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx
import pandas as pd

BASE_URL = os.getenv("SECOP_BASE_URL", "https://www.datos.gov.co/resource")
DATASET_ID = os.getenv("SECOP_DATASET_ID", "jbjy-vk9h")  # SECOP II - Contratos Electrónicos
TAM_PAGINA_MAX = 1000

# Columnas que usaremos en el resto del proyecto (modelo de datos y banderas rojas).
COLUMNAS_CLAVE = [
    "id_contrato",
    "nit_entidad",
    "nombre_entidad",
    "departamento",
    "modalidad_de_contratacion",
    "tipo_de_contrato",
    "objeto_del_contrato",
    "documento_proveedor",
    "proveedor_adjudicado",
    "valor_del_contrato",
    "fecha_de_firma",
    "estado_contrato",
    "ultima_actualizacion",
]


# ---------------------------------------------------------------------------
# 1. Descarga (Extract)
# ---------------------------------------------------------------------------


def construir_parametros(limite: int, offset: int, where: str | None = None) -> dict[str, str]:
    """Arma los parámetros SoQL de una petición.

    `$order=:id` ordena por el id interno de Socrata. Sin un orden fijo, la
    paginación con `$offset` podría repetir u omitir filas entre páginas.
    """
    params = {"$limit": str(limite), "$offset": str(offset), "$order": ":id"}
    if where:
        params["$where"] = where
    return params


def descargar_contratos(
    limite_total: int,
    where: str | None = None,
    tam_pagina: int = TAM_PAGINA_MAX,
    cliente: httpx.Client | None = None,
) -> list[dict]:
    """Descarga hasta `limite_total` contratos, página por página.

    El `cliente` se puede inyectar desde afuera. En los tests le pasamos un
    cliente falso para no depender de internet (inyección de dependencias).
    """
    url = f"{BASE_URL}/{DATASET_ID}.json"
    headers = {}
    if token := os.getenv("SECOP_APP_TOKEN"):
        headers["X-App-Token"] = token

    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=30.0)
    registros: list[dict] = []
    try:
        while len(registros) < limite_total:
            tam = min(tam_pagina, limite_total - len(registros))
            params = construir_parametros(tam, len(registros), where)
            respuesta = cliente.get(url, params=params, headers=headers)
            respuesta.raise_for_status()  # lanza error si la API responde 4xx/5xx
            pagina = respuesta.json()
            registros.extend(pagina)
            print(f"  página descargada: {len(pagina)} registros (total {len(registros)})")
            if len(pagina) < tam:
                break  # la API ya no tiene más datos
    finally:
        if propio:
            cliente.close()
    return registros


def cargar_desde_archivo(ruta: Path) -> list[dict]:
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar_en_archivo(registros: list[dict], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# 2. Análisis exploratorio
# ---------------------------------------------------------------------------

VALORES_VACIOS = {"", "No Definido", "No definido", "NO DEFINIDO"}


def a_dataframe(registros: list[dict]) -> pd.DataFrame:
    """Convierte la lista de diccionarios en tabla y trata 'No Definido' como vacío."""
    df = pd.DataFrame(registros)
    return df.replace(list(VALORES_VACIOS), pd.NA)


def perfilar(df: pd.DataFrame) -> pd.DataFrame:
    """Genera una ficha por columna: % de nulos, valores únicos y un ejemplo."""
    filas = []
    for columna in df.columns:
        serie = df[columna]
        no_nulos = serie.dropna()
        filas.append(
            {
                "columna": columna,
                "nulos_%": round(serie.isna().mean() * 100, 1),
                "unicos": no_nulos.astype(str).nunique(),
                "ejemplo": str(no_nulos.iloc[0])[:50] if not no_nulos.empty else None,
            }
        )
    return pd.DataFrame(filas).sort_values("nulos_%", ascending=False, ignore_index=True)


def limpiar_valor(serie: pd.Series) -> pd.Series:
    """La API entrega los montos como TEXTO ("38000000"). Los pasamos a número.

    Un valor de 0 en un contrato no tiene sentido de negocio: lo tratamos como dato faltante.
    """
    numeros = pd.to_numeric(serie, errors="coerce")
    return numeros.mask(numeros <= 0)


def resumen_negocio(df: pd.DataFrame) -> dict[str, object]:
    """Preguntas de negocio rápidas que guiarán las banderas rojas de la Fase 4."""
    valores = limpiar_valor(df["valor_del_contrato"])
    fechas = pd.to_datetime(df["fecha_de_firma"], errors="coerce")
    return {
        "total_contratos": len(df),
        "valor_total": float(valores.sum()),
        "valor_mediana": float(valores.median()),
        "valor_maximo": float(valores.max()),
        "contratos_por_modalidad": df["modalidad_de_contratacion"].value_counts().to_dict(),
        "pct_contratacion_directa": round(
            (df["modalidad_de_contratacion"] == "Contratación directa").mean() * 100, 1
        ),
        "firmados_en_fin_de_semana": int((fechas.dt.dayofweek >= 5).sum()),
        "top_proveedores_por_valor": (
            valores.groupby(df["proveedor_adjudicado"]).sum().nlargest(3).to_dict()
        ),
    }


# ---------------------------------------------------------------------------
# 3. Programa principal
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Explora contratos de SECOP II")
    parser.add_argument("--limite", type=int, default=1000, help="máximo de contratos a descargar")
    parser.add_argument("--where", help="filtro SoQL, ej: \"departamento = 'Antioquia'\"")
    parser.add_argument("--guardar", type=Path, help="ruta .json donde guardar lo descargado")
    parser.add_argument("--desde-archivo", type=Path, help="leer un .json local en vez de la API")
    args = parser.parse_args(argv)

    if args.desde_archivo:
        print(f"Leyendo {args.desde_archivo} ...")
        registros = cargar_desde_archivo(args.desde_archivo)
    else:
        print(f"Descargando de {BASE_URL}/{DATASET_ID} ...")
        registros = descargar_contratos(args.limite, where=args.where)
        if args.guardar:
            guardar_en_archivo(registros, args.guardar)
            print(f"Guardado en {args.guardar}")

    df = a_dataframe(registros)
    pd.set_option("display.width", 140)

    print(f"\n=== Forma: {df.shape[0]} filas x {df.shape[1]} columnas ===")
    faltantes = [c for c in COLUMNAS_CLAVE if c not in df.columns]
    if faltantes:
        print(f"OJO: faltan columnas clave: {faltantes}")

    print("\n=== Perfil de columnas ===")
    print(perfilar(df).to_string(index=False))

    print("\n=== Resumen de negocio ===")
    for clave, valor in resumen_negocio(df).items():
        print(f"- {clave}: {valor}")


if __name__ == "__main__":
    main()
