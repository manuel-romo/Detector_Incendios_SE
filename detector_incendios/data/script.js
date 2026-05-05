setInterval(() => {
  fetch("/api/estado")
    .then((response) => response.json())
    .then((data) => {
      // Fecha y hora
      document.getElementById("fecha_hora").innerText = data.fecha_hora;

      // Datos sensados
      document.getElementById("val_temp").innerText = data.sensores.temperatura_C.toFixed(1) + " °C";
      document.getElementById("val_humo").innerText = data.sensores.gas_crudo.toFixed(1);
      document.getElementById("val_ir").innerText = data.sensores.llama_cruda;
      document.getElementById("val_presion").innerText = data.sensores.presion_Pa + " Pa";
      
      document.getElementById("val_servo").innerText = data.estado.servo_angulo_actual + "°";
      document.getElementById("val_barrido").innerText = data.configuracion.barrido_automatico ? "Activo" : "Inactivo";

      // Detección de fuego
      const elementoFuego = document.getElementById("val_fuego_ir");
      if (data.estado.llama_detectada) {
        elementoFuego.innerText = "Positivo";
        elementoFuego.classList.add("alert-text");
      } else {
        elementoFuego.innerText = "Negativo";
        elementoFuego.classList.remove("alert-text");
      }
      
      // Alarma general
      const elementoAlarma = document.getElementById("val_alarma");
      const tituloEstado = document.getElementById("titulo-estado");
      const cardSensores = document.getElementById("card-sensores");
      const cardActuadores = document.getElementById("card-actuadores");
      
      if (data.estado.incendio_confirmado) {
        elementoAlarma.innerText = "Activa";
        elementoAlarma.classList.add("alert-text");

        cardSensores.classList.add("alert");
        cardActuadores.classList.add("alert");
        
        tituloEstado.innerText = "Estado Crítico: Incendio Confirmado";
        tituloEstado.style.color = "var(--accent-red)";
      } else {
        elementoAlarma.innerText = "Inactiva";
        elementoAlarma.classList.remove("alert-text");

        cardSensores.classList.remove("alert");
        cardActuadores.classList.remove("alert");
        
        // Título normal
        tituloEstado.innerText = "Estado Normal del Sistema";
        tituloEstado.style.color = "#ffffff";
      }

      // Parámetros de configuración
      document.getElementById("conf_ang_min").innerText = data.configuracion.angulo_minimo + "°";
      document.getElementById("conf_ang_max").innerText = data.configuracion.angulo_maximo + "°";
      document.getElementById("conf_vel_servo").innerText = data.configuracion.velocidad_servo + " ms";
      document.getElementById("conf_umb_ir").innerText = data.configuracion.limite_distancia_ir;
      document.getElementById("conf_umb_gas").innerText = data.configuracion.limite_gas;
      document.getElementById("conf_umb_temp").innerText = data.configuracion.limite_temperatura.toFixed(1);
      document.getElementById("conf_umb_pres").innerText = data.configuracion.limite_presion;

    })
    .catch(error => console.error("Error obteniendo datos del ESP32:", error));
}, 2000);