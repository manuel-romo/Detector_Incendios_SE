import os
from dotenv import load_dotenv
from mysql.connector import pooling, Error

# Cargar variables de entorno
load_dotenv()

_pool: pooling.MySQLConnectionPool | None = None


def _obtener_pool() -> pooling.MySQLConnectionPool:
    """Crea el pool de conexiones una sola vez."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="detector_pool",
            pool_size=5,
            pool_reset_session=True,
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
    return _pool


def obtener_conexion():
    """
    Retorna una conexión del pool.
    El pool la recicla automáticamente al hacer .close()
    """
    try:
        return _obtener_pool().get_connection()
    except Error as e:
        raise ConnectionError(f"No se pudo obtener conexión del pool: {e}") from e
