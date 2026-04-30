import socket
import json

# JSON con la estructura que envía el ESP32.
datos_falsos = {
    "fecha_hora": "2026-04-22 19:30:00",
    "humo": 450.5,
    "fuego": 0,
    "temperatura": 32.4,
    "presion": 1012.3,
    "servo": 90,
    "led": 0
}

# Se conecta al servidor y envía el JSON.
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(('127.0.0.1', 5000))
    s.sendall(json.dumps(datos_falsos).encode('utf-8'))
    print("Datos de prueba enviados.")