# Programa principal de la placa (ESP32, ESP8266 o Raspberry Pi Pico W con MicroPython).
# Se conecta al WiFi y envía una lectura al servidor cada INTERVALO_SEGUNDOS.

import time

import machine
import network

import config

try:
    import urequests as requests  # nombre clásico en MicroPython
except ImportError:
    import requests  # firmwares recientes


def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando a", config.WIFI_SSID, "...")
        wlan.connect(config.WIFI_SSID, config.WIFI_CLAVE)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(1)
    if not wlan.isconnected():
        raise RuntimeError("No se pudo conectar al WiFi")
    print("WiFi conectado. IP de la placa:", wlan.ifconfig()[0])
    return wlan


def crear_lector():
    """Devuelve una función que retorna (temperatura, humedad)."""
    if config.PIN_DHT is not None:
        import dht

        clase = dht.DHT22 if config.TIPO_DHT == "DHT22" else dht.DHT11
        sensor = clase(machine.Pin(config.PIN_DHT))

        def leer_dht():
            sensor.measure()
            return sensor.temperature(), sensor.humidity()

        return leer_dht

    # Sin sensor externo: temperatura interna del chip (sirve para probar).
    try:
        import esp32  # ESP32: devuelve grados Fahrenheit

        return lambda: (round((esp32.raw_temperature() - 32) / 1.8, 1), None)
    except (ImportError, AttributeError):
        pass

    adc = machine.ADC(4)  # Raspberry Pi Pico / Pico W: sensor interno en el canal 4

    def leer_pico():
        voltaje = adc.read_u16() * 3.3 / 65535
        return round(27 - (voltaje - 0.706) / 0.001721, 1), None

    return leer_pico


def enviar(temperatura, humedad):
    datos = {"dispositivo": config.NOMBRE_DISPOSITIVO, "temperatura": temperatura}
    if humedad is not None:
        datos["humedad"] = humedad
    encabezados = {"Content-Type": "application/json"}
    if config.API_KEY:
        encabezados["X-API-Key"] = config.API_KEY

    respuesta = requests.post(config.URL_SERVIDOR, json=datos, headers=encabezados)
    try:
        print("Enviado", datos, "->", respuesta.status_code)
    finally:
        respuesta.close()  # importante: libera memoria en la placa


def main():
    wlan = conectar_wifi()
    leer = crear_lector()
    led = None
    try:
        led = machine.Pin("LED", machine.Pin.OUT)  # Pico W
    except (TypeError, ValueError):
        try:
            led = machine.Pin(2, machine.Pin.OUT)  # LED azul de muchas ESP32
        except ValueError:
            pass

    while True:
        try:
            if not wlan.isconnected():
                wlan = conectar_wifi()
            temperatura, humedad = leer()
            enviar(temperatura, humedad)
            if led:
                led.on()
                time.sleep(0.2)
                led.off()
        except Exception as error:  # que un fallo puntual no detenga la placa
            print("Error:", error)
        time.sleep(config.INTERVALO_SEGUNDOS)


main()
