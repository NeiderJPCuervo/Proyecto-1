"""Pruebas de la API. Ejecutar desde esta carpeta con:  python -m unittest -v"""

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import app


class PruebasValidacion(unittest.TestCase):
    def test_lectura_valida(self):
        lectura, error = app.validar({"dispositivo": "esp32", "temperatura": "24.5", "humedad": 60})
        self.assertIsNone(error)
        self.assertEqual(lectura, {"dispositivo": "esp32", "temperatura": 24.5, "humedad": 60.0})

    def test_humedad_es_opcional(self):
        lectura, error = app.validar({"dispositivo": "pico", "temperatura": 20})
        self.assertIsNone(error)
        self.assertIsNone(lectura["humedad"])

    def test_errores(self):
        casos = [
            [],
            {"temperatura": 20},
            {"dispositivo": "x"},
            {"dispositivo": "x", "temperatura": "caliente"},
            {"dispositivo": "x", "temperatura": 999},
            {"dispositivo": "x", "temperatura": 20, "humedad": 150},
        ]
        for datos in casos:
            with self.subTest(datos=datos):
                lectura, error = app.validar(datos)
                self.assertIsNone(lectura)
                self.assertTrue(error)


class PruebasHTTP(unittest.TestCase):
    def setUp(self):
        carpeta = tempfile.mkdtemp()
        app.Manejador.ruta_db = os.path.join(carpeta, "prueba.db")
        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), app.Manejador)
        self.url = f"http://127.0.0.1:{self.servidor.server_port}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def pedir(self, ruta, datos=None):
        cuerpo = json.dumps(datos).encode() if datos is not None else None
        peticion = urllib.request.Request(
            self.url + ruta, data=cuerpo, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(peticion) as respuesta:
                return respuesta.status, json.loads(respuesta.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_enviar_y_listar(self):
        codigo, creado = self.pedir("/api/datos", {"dispositivo": "esp32", "temperatura": 22})
        self.assertEqual(codigo, 201)
        self.assertEqual(creado["id"], 1)

        self.pedir("/api/datos", {"dispositivo": "esp32", "temperatura": 23, "humedad": 55})
        codigo, lecturas = self.pedir("/api/datos?limite=10")
        self.assertEqual(codigo, 200)
        self.assertEqual([l["temperatura"] for l in lecturas], [23, 22])  # más reciente primero

    def test_rechaza_datos_invalidos(self):
        codigo, respuesta = self.pedir("/api/datos", {"dispositivo": "esp32"})
        self.assertEqual(codigo, 400)
        self.assertIn("temperatura", respuesta["error"])

    def test_salud_y_404(self):
        self.assertEqual(self.pedir("/api/salud"), (200, {"estado": "ok"}))
        self.assertEqual(self.pedir("/api/otra")[0], 404)


if __name__ == "__main__":
    unittest.main()
