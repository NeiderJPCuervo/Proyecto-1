"""Simula la placa desde tu computador: envía lecturas falsas a la API.

Sirve para probar la página sin tener la ESP32/Pico a mano.

    python simulador.py                          # envía a http://localhost/api/datos
    python simulador.py --url http://192.168.1.100/api/datos --cada 2
"""

import argparse
import json
import math
import random
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost/api/datos")
    parser.add_argument("--cada", type=float, default=3, help="segundos entre envíos")
    parser.add_argument("--dispositivo", default="simulador")
    parser.add_argument("--api-key", default="")
    args = parser.parse_args()

    encabezados = {"Content-Type": "application/json"}
    if args.api_key:
        encabezados["X-API-Key"] = args.api_key

    paso = 0
    print(f"Enviando a {args.url} cada {args.cada}s (Ctrl+C para parar)")
    while True:
        datos = {
            "dispositivo": args.dispositivo,
            "temperatura": round(24 + 3 * math.sin(paso / 5) + random.uniform(-0.3, 0.3), 1),
            "humedad": round(60 + 10 * math.cos(paso / 7) + random.uniform(-1, 1), 1),
        }
        peticion = urllib.request.Request(
            args.url, data=json.dumps(datos).encode(), headers=encabezados
        )
        try:
            with urllib.request.urlopen(peticion, timeout=5) as respuesta:
                print(respuesta.status, datos)
        except urllib.error.HTTPError as error:
            print("Error", error.code, error.read().decode())
        except urllib.error.URLError as error:
            print("Sin conexión:", error.reason)
        paso += 1
        time.sleep(args.cada)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSimulador detenido")
