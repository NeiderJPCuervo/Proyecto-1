"""API que recibe y entrega las lecturas enviadas por la placa con MicroPython.

Solo usa la biblioteca estándar de Python (no hay que instalar nada).
Nginx sirve la página web y reenvía a este programa todo lo que empieza por /api/.

Rutas:
    GET  /api/salud            -> comprueba que el servidor está vivo
    GET  /api/datos?limite=50  -> últimas lecturas (la más reciente primero)
    POST /api/datos            -> guarda una lectura nueva (JSON)

Ejecutar:
    python app.py              # escucha en 0.0.0.0:5000
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("API_HOST", "0.0.0.0")
PUERTO = int(os.environ.get("API_PUERTO", "5000"))
RUTA_DB = os.environ.get("API_DB", os.path.join(os.path.dirname(__file__), "lecturas.db"))
# Si se define, la placa debe enviar el encabezado "X-API-Key" con este valor.
API_KEY = os.environ.get("API_KEY", "")

TAMANO_MAXIMO = 2048  # bytes; una lectura nunca debería ocupar más


def conectar(ruta=None):
    conexion = sqlite3.connect(ruta or RUTA_DB)
    conexion.row_factory = sqlite3.Row
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS lecturas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            dispositivo TEXT    NOT NULL,
            temperatura REAL    NOT NULL,
            humedad     REAL,
            recibido    TEXT    NOT NULL
        )
        """
    )
    return conexion


def validar(datos):
    """Devuelve (lectura_limpia, None) o (None, mensaje_de_error)."""
    if not isinstance(datos, dict):
        return None, "El cuerpo debe ser un objeto JSON"

    dispositivo = str(datos.get("dispositivo", "")).strip()
    if not dispositivo or len(dispositivo) > 50:
        return None, "'dispositivo' es obligatorio (máximo 50 caracteres)"

    try:
        temperatura = float(datos["temperatura"])
    except (KeyError, TypeError, ValueError):
        return None, "'temperatura' es obligatoria y debe ser un número"
    if not -50 <= temperatura <= 150:
        return None, "'temperatura' fuera de rango (-50 a 150 °C)"

    humedad = datos.get("humedad")
    if humedad is not None:
        try:
            humedad = float(humedad)
        except (TypeError, ValueError):
            return None, "'humedad' debe ser un número"
        if not 0 <= humedad <= 100:
            return None, "'humedad' fuera de rango (0 a 100 %)"

    return {"dispositivo": dispositivo, "temperatura": temperatura, "humedad": humedad}, None


def guardar(conexion, lectura):
    recibido = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cursor = conexion.execute(
        "INSERT INTO lecturas (dispositivo, temperatura, humedad, recibido) VALUES (?, ?, ?, ?)",
        (lectura["dispositivo"], lectura["temperatura"], lectura["humedad"], recibido),
    )
    conexion.commit()
    return {"id": cursor.lastrowid, **lectura, "recibido": recibido}


def listar(conexion, limite=50):
    filas = conexion.execute(
        "SELECT * FROM lecturas ORDER BY id DESC LIMIT ?", (limite,)
    ).fetchall()
    return [dict(fila) for fila in filas]


class Manejador(BaseHTTPRequestHandler):
    ruta_db = None  # las pruebas lo cambian para usar una base temporal

    def _responder(self, codigo, cuerpo):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/salud":
            return self._responder(200, {"estado": "ok"})
        if url.path == "/api/datos":
            try:
                limite = int(parse_qs(url.query).get("limite", ["50"])[0])
            except ValueError:
                limite = 50
            limite = max(1, min(limite, 500))
            with conectar(self.ruta_db) as conexion:
                return self._responder(200, listar(conexion, limite))
        self._responder(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/datos":
            return self._responder(404, {"error": "Ruta no encontrada"})
        if API_KEY and self.headers.get("X-API-Key") != API_KEY:
            return self._responder(401, {"error": "API key inválida"})

        longitud = int(self.headers.get("Content-Length") or 0)
        if longitud <= 0 or longitud > TAMANO_MAXIMO:
            return self._responder(400, {"error": "Cuerpo vacío o demasiado grande"})
        try:
            datos = json.loads(self.rfile.read(longitud))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._responder(400, {"error": "JSON inválido"})

        lectura, error = validar(datos)
        if error:
            return self._responder(400, {"error": error})
        with conectar(self.ruta_db) as conexion:
            self._responder(201, guardar(conexion, lectura))

    def log_message(self, formato, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} {formato % args}")


def main():
    conectar().close()  # crea la tabla si no existe
    servidor = ThreadingHTTPServer((HOST, PUERTO), Manejador)
    print(f"API escuchando en http://{HOST}:{PUERTO}  (base de datos: {RUTA_DB})")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido")


if __name__ == "__main__":
    main()
