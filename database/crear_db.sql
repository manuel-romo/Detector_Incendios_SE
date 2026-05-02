-- 1. Crear la base de datos
CREATE DATABASE IF NOT EXISTS detector_incendios_db;

-- 2. Seleccionar la base de datos
USE detector_incendios_db;

-- 3. Crear la tabla
CREATE TABLE IF NOT EXISTS registro_sensores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha_hora DATETIME NOT NULL,
    humo_mq2 FLOAT NOT NULL,
    fuego_detectado BOOLEAN NOT NULL,
    temperatura FLOAT NOT NULL,
    presion FLOAT NOT NULL,
    estado_servo INT NOT NULL,
    estado_led BOOLEAN NOT NULL
);