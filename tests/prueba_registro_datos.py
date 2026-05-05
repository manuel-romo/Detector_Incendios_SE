import socket
import json
import datetime
import time
import random

angulo = 0
direccion = 15  # Incremento del ángulo en grados

base_humo = 400.0
base_temp = 25.0
base_presion = 1012.0

print("Iniciando simulación del ESP32... Presiona Ctrl+C para detener.")

try:
    while True:
        # Simular variación de los sensores
        base_humo += random.uniform(-10.0, 10.0)
        base_temp += random.uniform(-0.5, 0.5)
        base_presion += random.uniform(-1.0, 1.0)

        # Simular el movimiento del servo
        angulo += direccion
        if angulo >= 180:
            angulo = 180
            direccion = -15
        elif angulo <= 0:
            angulo = 0
            direccion = 15

        datos_falsos = {
            "fecha_hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "humo": round(base_humo, 2),
            "fuego_raw": 4095,
            "fuego_bool": False,
            "temperatura": round(base_temp, 2),
            "presion": round(base_presion, 2),
            "servo": angulo,
            "led": 0,
        }

        # Se conecta al servidor y envía el JSON
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("127.0.0.1", 5000))
            s.sendall(json.dumps(datos_falsos).encode("utf-8"))
            print(
                f"Datos enviados -> Ángulo: {angulo}°, Temp: {round(base_temp, 1)}°C, Humo: {round(base_humo, 1)}"
            )

        time.sleep(1.2)
except KeyboardInterrupt:
    print("\nSimulación detenida.")
