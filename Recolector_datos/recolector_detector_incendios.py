import socket
import json
import mysql.connector

# Configuración de base de datos:
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'mroMSQL1147-',
    'database': 'detector_incendios_db'
}

# Configuración de servidor TCP:
# Escucha en todas las interfaces de red locales.
HOST = '0.0.0.0'
# Puerto por el que envía los datos el ESP32.
PORT = 5000      

# Función para insertar registro en base de datos.
def guardar_datos(datos):
    
    try:
        conexion = mysql.connector.connect(**db_config)
        cursor = conexion.cursor()
        
        consultaInsercion = """
            INSERT INTO registro_sensores 
            (fecha_hora, humo_mq2, fuego_detectado, temperatura, presion, estado_servo, estado_led) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        # Se extraen los valores del archivo JSON
        valores = (
            datos.get('fecha_hora'),
            datos.get('humo'),
            datos.get('fuego'),
            datos.get('temperatura'),
            datos.get('presion'),
            datos.get('servo'),
            datos.get('led')
        )
        
        cursor.execute(consultaInsercion, valores)
        conexion.commit()
        print("Registro guardado en BD exitosamente.")
        
    except mysql.connector.Error as err:
        print(f"Error de base de datos: {err}")
    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()

# Función que incializa el socket del servidor TCP para escuchar la llegada de nuevos datos.
def iniciar_servidor_tcp():
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Permite el reuso el puerto si el script se reinicia rápidamente.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor TCP de recolección iniciado. Escuchando en puerto: {PORT}...")
        
        # Ciclo infinito para escucha.
        while True:
            # Se acepta la conexión con el dispositivo ESP32.
            conexion_cliente, direccion = s.accept()
            with conexion_cliente:
                print(f"\nConexión entrante desde el ESP32 en la IP: {direccion[0]}")
                
                # Se obtiene el archivo JSON.
                datos_recibidos = conexion_cliente.recv(1024).decode('utf-8')
                
                # Si se reciben datos:
                if datos_recibidos:
                    try:
                        # El archivo JSON se traduce a una cadena de texto.
                        datos_json = json.loads(datos_recibidos)
                        print(f"Datos convertidos: {datos_json}")
                        
                        # Los datos convertidos se guardan en la base de datos.
                        guardar_datos(datos_json)
                        
                    except json.JSONDecodeError:
                        print("Error: Los datos recibidos no tiene un formato válido.")
                        print(f"Datos recibidos: {datos_recibidos}")

if __name__ == "__main__":
    iniciar_servidor_tcp()