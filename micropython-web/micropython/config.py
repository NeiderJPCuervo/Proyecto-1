# Configuración de la placa. Cambia estos valores antes de copiar los archivos a la placa.

# --- Red WiFi (la placa y el servidor deben poder verse en la red) ---
WIFI_SSID = "NOMBRE_DE_TU_WIFI"
WIFI_CLAVE = "CLAVE_DE_TU_WIFI"

# --- Servidor ---
# IP del computador donde corre Nginx (en Windows: ipconfig, en Linux/Mac: ip a / ifconfig).
# No uses "localhost": para la placa, localhost es ella misma.
URL_SERVIDOR = "http://192.168.1.100/api/datos"
API_KEY = ""  # déjalo vacío si no configuraste API_KEY en el servidor

# --- Lecturas ---
NOMBRE_DISPOSITIVO = "esp32-01"
INTERVALO_SEGUNDOS = 10

# Sensor DHT11/DHT22 conectado a este pin. Pon None para usar el sensor de
# temperatura interno de la placa (no hace falta cablear nada).
PIN_DHT = None
TIPO_DHT = "DHT11"  # o "DHT22"
