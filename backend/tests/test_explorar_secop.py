"""Tests de la Fase 1. Se ejecutan con `pytest` desde la carpeta `backend/`.

Ningún test usa internet: simulamos la API con `httpx.MockTransport`.
"""

from pathlib import Path

import httpx
import pandas as pd

from scripts.explorar_secop import (
    a_dataframe,
    cargar_desde_archivo,
    construir_parametros,
    descargar_contratos,
    limpiar_valor,
    perfilar,
    resumen_negocio,
)

FIXTURE = Path(__file__).parent / "fixtures" / "secop_contratos_muestra.json"


def test_construir_parametros_incluye_orden_estable_y_filtro():
    params = construir_parametros(limite=50, offset=100, where="departamento = 'Antioquia'")

    assert params == {
        "$limit": "50",
        "$offset": "100",
        "$order": ":id",
        "$where": "departamento = 'Antioquia'",
    }


def test_descargar_contratos_pagina_hasta_que_no_hay_mas_datos():
    # Una "API" falsa con 5 registros en total.
    datos = [{"id_contrato": str(i)} for i in range(5)]
    peticiones = []

    def api_falsa(request: httpx.Request) -> httpx.Response:
        peticiones.append(dict(request.url.params))
        offset = int(request.url.params["$offset"])
        limite = int(request.url.params["$limit"])
        return httpx.Response(200, json=datos[offset : offset + limite])

    cliente = httpx.Client(transport=httpx.MockTransport(api_falsa))
    registros = descargar_contratos(limite_total=100, tam_pagina=2, cliente=cliente)

    assert [r["id_contrato"] for r in registros] == ["0", "1", "2", "3", "4"]
    # 3 páginas: [0,1], [2,3], [4] -> la última llega incompleta y se detiene.
    assert [p["$offset"] for p in peticiones] == ["0", "2", "4"]


def test_descargar_contratos_respeta_el_limite_total():
    def api_falsa(request: httpx.Request) -> httpx.Response:
        limite = int(request.url.params["$limit"])
        return httpx.Response(200, json=[{"id_contrato": "x"}] * limite)

    cliente = httpx.Client(transport=httpx.MockTransport(api_falsa))
    registros = descargar_contratos(limite_total=5, tam_pagina=2, cliente=cliente)

    assert len(registros) == 5


def test_a_dataframe_convierte_no_definido_en_nulo():
    df = a_dataframe([{"proveedor_adjudicado": "No Definido"}, {"proveedor_adjudicado": "ACME"}])

    assert df["proveedor_adjudicado"].isna().tolist() == [True, False]


def test_limpiar_valor_convierte_texto_a_numero_y_descarta_ceros():
    resultado = limpiar_valor(pd.Series(["38000000", "0", "abc", None]))

    assert resultado.iloc[0] == 38_000_000
    assert resultado.iloc[1:].isna().all()


def test_perfilar_reporta_porcentaje_de_nulos():
    df = pd.DataFrame({"a": [1, None, None, 4], "b": ["x", "y", "z", "w"]})

    perfil = perfilar(df).set_index("columna")

    assert perfil.loc["a", "nulos_%"] == 50.0
    assert perfil.loc["b", "nulos_%"] == 0.0
    assert perfil.loc["b", "unicos"] == 4


def test_resumen_negocio_sobre_datos_de_ejemplo():
    df = a_dataframe(cargar_desde_archivo(FIXTURE))

    resumen = resumen_negocio(df)

    assert resumen["total_contratos"] == 12
    assert resumen["firmados_en_fin_de_semana"] == 1  # el contrato firmado el domingo 16/06/2024
    assert resumen["pct_contratacion_directa"] == 58.3  # 7 de 12
    assert "SUMINISTROS EJEMPLO SAS" in df["proveedor_adjudicado"].values
