

#include <Arduino.h>
#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h> 
#include <Servo.h>
#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <LittleFS.h>
#include <NoDelay.h>
#include <time.h>

/*
Manuel Romo López
Juan Pablo Olivarría Covarrubias
*/
// Configuración de red WiFi y tiempo.
const char* nombreRed = "INFINITUMA519";
const char* contrasenaRed = "Us1Uq7Ec2b";

const char* ipServidorTCP = "192.168.1.64";
const int puertoServidorTCP = 5050;

const char* servidorTiempo = "pool.ntp.org";
const long compensacionZonaHoraria_seg = -25200;
const int compensacionHorarioVerano_seg = 0;

// Pines
const int PIN_SERVO = 18;
const int PIN_LLAMA = 35;
const int PIN_MQ2 = 34;
const int PIN_LED_ALARMA = 5;
const int PIN_I2C_SDA = 21;
const int PIN_I2C_SCL = 22;

// Objetos globales y temporizadores
AsyncWebServer servidorWeb(80);
Servo servoMotor;
Adafruit_BMP085 sensorBmp;
WiFiClient clienteTCP; 

noDelay temporizadorSensores(1000);   

// Estructura de datos y cola (FreeRTOS)
struct PaqueteDatosTCP {
  char fecha_hora[50];
  int gas;
  int llama_cruda;
  bool incendio;
  float temperatura;
  int32_t presion;
  int angulo_servo;
};

QueueHandle_t colaDatosTCP;

// Variables de estado y configuración
String fechaActual = "Sincronizando...";
float temperaturaActual = 0.0;
int32_t presionActual = 0;
int gasActual = 0;
int llamaCrudaActual = 0;
bool llamaDetectada = false;
bool incendioConfirmado = false;
bool sensorBmpConectado = false;

int anguloServo = 0;
int pasoServo = 2; 

float limiteTemperatura = 60.0;     
int limiteGas = 2000;
int limiteLlama = 2000;      
int32_t limitePresion = 100000; 
int velocidadServo = 30;            
bool barridoAutomatico = true;      
int anguloMinimo = 0;
int anguloMaximo = 180;    

// Tarea de núcleo 0. Envío exclusivo por TCP
void tareaEnvioTCP(void * parameter) {
  PaqueteDatosTCP datosRecibidos;
  
  for(;;) {
    if (xQueueReceive(colaDatosTCP, &datosRecibidos, portMAX_DELAY) == pdPASS) {
      if (clienteTCP.connect(ipServidorTCP, puertoServidorTCP, 200)) {
        JsonDocument docTCP; 
        
        docTCP["fecha_hora"]  = datosRecibidos.fecha_hora;
        docTCP["humo"]        = datosRecibidos.gas;
        docTCP["fuego_raw"]   = datosRecibidos.llama_cruda;
        docTCP["fuego_bool"]  = datosRecibidos.incendio;
        docTCP["temperatura"] = datosRecibidos.temperatura;
        docTCP["presion"]     = datosRecibidos.presion;
        docTCP["servo"]       = datosRecibidos.angulo_servo;
        docTCP["led"]         = datosRecibidos.incendio;

        String jsonOutput;
        serializeJson(docTCP, jsonOutput);
        
        clienteTCP.print(jsonOutput);
        clienteTCP.stop();
        
        Serial.println("[TCP] Datos enviados correctamente desde el Núcleo 0.");
      } else {
        Serial.println("[TCP] No se pudo conectar al servidor.");
      }
    }
  }
}

// Funciones de núcleo 1. Sensores y Actuadores

void actualizarSensores() {
  struct tm infoTiempo;
  if (getLocalTime(&infoTiempo)) {
    char textoTiempo[50];
    strftime(textoTiempo, sizeof(textoTiempo), "%Y-%m-%d %H:%M:%S", &infoTiempo);
    fechaActual = String(textoTiempo);
  } else {
    fechaActual = "2026-01-01 00:00:00"; 
  }

  if (sensorBmpConectado) {
    temperaturaActual = sensorBmp.readTemperature();
    presionActual = sensorBmp.readPressure();
  }

  gasActual = analogRead(PIN_MQ2);
  llamaCrudaActual = analogRead(PIN_LLAMA);

  llamaDetectada = (llamaCrudaActual < limiteLlama);

  // Detección de incendio
  if (llamaDetectada && (temperaturaActual > limiteTemperatura) && (gasActual > limiteGas)) {
    incendioConfirmado = true;
    digitalWrite(PIN_LED_ALARMA, HIGH);
  } else {
    incendioConfirmado = false; 
    digitalWrite(PIN_LED_ALARMA, LOW);
  }

  PaqueteDatosTCP datosAEnviar;
  strlcpy(datosAEnviar.fecha_hora, fechaActual.c_str(), sizeof(datosAEnviar.fecha_hora));
  datosAEnviar.gas = gasActual;
  datosAEnviar.llama_cruda = llamaCrudaActual;
  datosAEnviar.incendio = incendioConfirmado;
  datosAEnviar.temperatura = temperaturaActual;
  datosAEnviar.presion = presionActual;
  datosAEnviar.angulo_servo = anguloServo;

  xQueueSend(colaDatosTCP, &datosAEnviar, 0);
}

void moverServo() {
  if (!barridoAutomatico) return; 
  
  anguloServo += pasoServo;
  if (anguloServo >= 180 || anguloServo <= 0) {
    pasoServo = -pasoServo; 
  }
  servoMotor.write(anguloServo);
}

// Rutas de API REST

void manejarEstadoGet(AsyncWebServerRequest *peticion) {
  JsonDocument documento; 
  documento["fecha_hora"] = fechaActual;
  documento["sensores"]["temperatura_C"] = temperaturaActual;
  documento["sensores"]["presion_Pa"] = presionActual;
  documento["sensores"]["gas_crudo"] = gasActual;
  documento["sensores"]["llama_cruda"] = llamaCrudaActual;
  documento["estado"]["llama_detectada"] = llamaDetectada;
  documento["estado"]["incendio_confirmado"] = incendioConfirmado;
  documento["estado"]["servo_angulo_actual"] = anguloServo;
  documento["configuracion"]["limite_temperatura"] = limiteTemperatura;
  documento["configuracion"]["limite_gas"] = limiteGas;
  documento["configuracion"]["limite_distancia_ir"] = limiteLlama;
  documento["configuracion"]["limite_presion"] = limitePresion;
  documento["configuracion"]["velocidad_servo"] = velocidadServo;
  documento["configuracion"]["barrido_automatico"] = barridoAutomatico;
  documento["configuracion"]["angulo_minimo"] = anguloMinimo;
  documento["configuracion"]["angulo_maximo"] = anguloMaximo;
  
  String respuestaJson;
  serializeJson(documento, respuestaJson);
  AsyncWebServerResponse *respuesta = peticion->beginResponse(200, "application/json", respuestaJson);
  respuesta->addHeader("Access-Control-Allow-Origin", "*");
  peticion->send(respuesta);
}

void manejarConfiguracionPost(AsyncWebServerRequest *peticion, uint8_t *datos, size_t longitud, size_t indice, size_t total) {
  if (longitud == 0) return peticion->send(400, "application/json", "{\"error\":\"Cuerpo vacio\"}");
  JsonDocument documento;
  if (deserializeJson(documento, (const char*)datos, longitud)) return peticion->send(400, "application/json", "{\"error\":\"JSON invalido\"}");

  if (documento["limite_temperatura"].is<float>()) 
      limiteTemperatura = constrain(documento["limite_temperatura"].as<float>(), -40.0, 150.0);
      
  if (documento["limite_gas"].is<int>()) 
      limiteGas = constrain(documento["limite_gas"].as<int>(), 0, 4095);
      
  if (documento["limite_distancia_ir"].is<int>()) 
      limiteLlama = constrain(documento["limite_distancia_ir"].as<int>(), 0, 4095);
      
  if (documento["limite_presion"].is<int32_t>()) 
      limitePresion = constrain(documento["limite_presion"].as<int32_t>(), 50000, 150000);
      
  if (documento["barrido_automatico"].is<bool>()) 
      barridoAutomatico = documento["barrido_automatico"];
  
  if (documento["velocidad_servo"].is<int>()) 
      velocidadServo = constrain(documento["velocidad_servo"].as<int>(), 30, 200);

  if (documento["angulo_minimo"].is<int>()) 
      anguloMinimo = constrain(documento["angulo_minimo"].as<int>(), 0, 180);
      
  if (documento["angulo_maximo"].is<int>()) 
      anguloMaximo = constrain(documento["angulo_maximo"].as<int>(), 0, 180);

  if (anguloMinimo > anguloMaximo) {
    int temporal = anguloMinimo;
    anguloMinimo = anguloMaximo;
    anguloMaximo = temporal;
  }

  if (anguloMinimo == anguloMaximo) {
    barridoAutomatico = false; 
    anguloServo = anguloMinimo;
    servoMotor.write(anguloServo);
  } else {
    barridoAutomatico = true;
    if (anguloServo < anguloMinimo) anguloServo = anguloMinimo;
    if (anguloServo > anguloMaximo) anguloServo = anguloMaximo;
  }

  AsyncWebServerResponse *respuesta = peticion->beginResponse(200, "application/json", "{\"estado\":\"Ok\"}");
  respuesta->addHeader("Access-Control-Allow-Origin", "*");
  peticion->send(respuesta);
}

// Control de servomotor con prioridad alta
void tareaMovimientoServo(void * parameter) {
  for(;;) {
    if (barridoAutomatico) {
      anguloServo += pasoServo;
      
      if (anguloServo >= anguloMaximo) {
        anguloServo = anguloMaximo;
        // Se fuerza ir abajo
        pasoServo = -abs(pasoServo);
      } else if (anguloServo <= anguloMinimo) {
        anguloServo = anguloMinimo;
        // Se fuerza ir arriba
        pasoServo = abs(pasoServo);
      }
      servoMotor.write(anguloServo);
    }
    vTaskDelay(velocidadServo / portTICK_PERIOD_MS);
  }
}

// Configuración inicial
void setup() {
  Serial.begin(115200);

  pinMode(PIN_LLAMA, INPUT);
  pinMode(PIN_MQ2, INPUT);
  pinMode(PIN_LED_ALARMA, OUTPUT);
  digitalWrite(PIN_LED_ALARMA, LOW);

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  sensorBmpConectado = sensorBmp.begin();

  servoMotor.attach(PIN_SERVO); 

  WiFi.mode(WIFI_STA);
  WiFi.begin(nombreRed, contrasenaRed);
  Serial.print("Conectando WiFi ");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nIP: " + WiFi.localIP().toString());

  configTime(compensacionZonaHoraria_seg, compensacionHorarioVerano_seg, servidorTiempo);

  LittleFS.begin(true);

  colaDatosTCP = xQueueCreate(5, sizeof(PaqueteDatosTCP));

  // Parámetros: Función, Nombre, Memoria, Parámetros, Prioridad, Handle y Pin al núcleo 0
  xTaskCreatePinnedToCore(
    tareaEnvioTCP,
    "TareaTCP",
    10000,
    NULL,
    1,
    NULL,
    0);

  // Parámetros: Función, Nombre, Memoria, Parámetros, Prioridad, Handle y Pin al núcleo 1
  xTaskCreatePinnedToCore(
    tareaMovimientoServo,
    "TareaServo",
    2048,
    NULL,
    5,
    NULL,
    1);

  servidorWeb.serveStatic("/", LittleFS, "/").setDefaultFile("index.html");
  servidorWeb.on("/api/estado", HTTP_GET, manejarEstadoGet);
  servidorWeb.on("/api/configuracion", HTTP_POST, [](AsyncWebServerRequest *peticion){}, NULL, manejarConfiguracionPost);
  servidorWeb.begin();
  
  Serial.println("Servidor Iniciado");
}

// Bucle principal
void loop() {
    if (temporizadorSensores.update()) {
      actualizarSensores();       
    }
}