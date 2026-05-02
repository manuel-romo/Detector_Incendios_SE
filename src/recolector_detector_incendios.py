import socket
import json
import mysql.connector
import os
from dotenv import load_dotenv
from db_conexion import obtener_conexion

# Cargar variables de entorno
load_dotenv()

# Configuración del servidor TCP
HOST = os.getenv("TCP_HOST")
PORT = int(os.getenv("TCP_PORT"))

# Tamaño de cada bloque de lectura
BUFFER_SIZE = 4096


def guardar_datos(datos: dict) -> None:
    """Valida e inserta un registro de sensores en la base de datos."""
    campos_esperados = [
        "fecha_hora",
        "humo",
        "fuego",
        "temperatura",
        "presion",
        "servo",
        "led",
    ]

    if not all(campo in datos for campo in campos_esperados):
        print(f"[BD] Error: JSON incompleto. Datos recibidos: {datos}")
        return

    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        consulta = """
            INSERT INTO registro_sensores
            (fecha_hora, humo_mq2, fuego_detectado, temperatura, presion, estado_servo, estado_led)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            datos["fecha_hora"],
            datos["humo"],
            datos["fuego"],
            datos["temperatura"],
            datos["presion"],
            datos["servo"],
            datos["led"],
        )

        cursor.execute(consulta, valores)
        conexion.commit()
        print("[BD] Registro guardado exitosamente.")

    except mysql.connector.Error as err:
        print(f"[BD] Error de base de datos: {err}")
    finally:
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()


def recibir_completo(conn: socket.socket) -> str:
    """
    Lee datos del socket en bloques hasta que no llegue nada más.
    """
    fragmentos = []
    while True:
        bloque = conn.recv(BUFFER_SIZE)
        if not bloque:
            break
        fragmentos.append(bloque)
        if len(bloque) < BUFFER_SIZE:
            break
    return b"".join(fragmentos).decode("utf-8")


def manejar_cliente(conexion_cliente: socket.socket, direccion: tuple) -> None:
    """Procesa la conexión del ESP32."""
    print(f"[TCP] Conexión entrante desde ESP32 en IP: {direccion[0]}")
    try:
        with conexion_cliente:
            datos_recibidos = recibir_completo(conexion_cliente)

            if not datos_recibidos:
                print(f"[TCP] Conexión de {direccion[0]} cerrada sin datos.")
                return

            try:
                datos_json = json.loads(datos_recibidos)
                print(f"[TCP] Datos recibidos: {datos_json}")
                guardar_datos(datos_json)
            except json.JSONDecodeError:
                print(f"[TCP] Error: JSON inválido recibido de {direccion[0]}")
                print(f"[TCP] Raw: {datos_recibidos}")

    except OSError as e:
        print(f"[TCP] Error de socket con {direccion[0]}: {e}")


def iniciar_servidor_tcp() -> None:
    """
    Inicia el servidor TCP.
    Atiende las conexiones.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[TCP] Servidor iniciado. Escuchando en {HOST}:{PORT}...")

        while True:
            try:
                conexion_cliente, direccion = s.accept()
                manejar_cliente(conexion_cliente, direccion)

            except KeyboardInterrupt:
                print("\n[TCP] Servidor detenido por el usuario.")
                break


if __name__ == "__main__":
    iniciar_servidor_tcp()
