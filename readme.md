# Detector de Incendios SE

Proyecto de Sistemas Empotrados para la recolección, monitoreo y visualización de datos de sensores (temperatura, humo y presencia de fuego) mediante un ESP32 y una interfaz gráfica en Python.

## Requisitos del Sistema

Antes de comenzar, asegúrate de tener instalado lo siguiente:

- **Python 3.8 o superior**
- **Servidor de MySQL** (en ejecución local o remoto)
- **Git**

## Instrucciones de Instalación y Uso

### 1. Clonar el repositorio

```bash
git clone https://github.com/manuel-romo/Detector_Incendios_SE
cd Detector_Incendios_SE
```

### 2. Configurar la Base de Datos

Ejecuta el script SQL `database/crear_db.sql` incluido en el proyecto dentro de tu gestor de base de datos MySQL para crear la base de datos y la tabla necesarias.

### 3. Configurar las Variables de Entorno

El proyecto utiliza un archivo oculto para proteger las contraseñas.
Copia el archivo de ejemplo para crear el tuyo propio:

```bash
cp .env.example .env
```

_(En Windows puedes simplemente copiar y pegar el archivo `.env.example` y renombrarlo a `.env`)._
Luego abre el archivo `.env` en tu editor y asegúrate de actualizar tus credenciales de MySQL y la IP de tu ESP32.

### 4. Crear y activar el entorno virtual

Es sumamente recomendable utilizar un entorno virtual para aislar las dependencias:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 5. Instalar las dependencias

Con el entorno activado, instala las librerías requeridas ejecutando:

```bash
pip install -r requirements.txt
```

### 6. Ejecutar el sistema

El proyecto cuenta con un servidor de recolección de datos y una interfaz gráfica de monitoreo.

Primero, inicia el script encargado de escuchar y guardar los datos que manda el ESP32:

```bash
python .\src\recolector_detector_incendios.py
```

En una nueva terminal (recordando activar nuevamente el entorno virtual), ejecuta la interfaz gráfica para el monitoreo:

```bash
python .\src\radar.py
```
