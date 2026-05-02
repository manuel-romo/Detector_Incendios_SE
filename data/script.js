setInterval(() => {
  fetch("/api/estado")
    .then((response) => response.json())
    .then((data) => {
      document.getElementById("temp").innerText = data.temperatura + " °C";
      document.getElementById("humo").innerText = data.humo_mq2;
      document.getElementById("presion").innerText = data.presion + " hPa";
      document.getElementById("servo").innerText = data.estado_servo + "°";
      
      const ledElement = document.getElementById("led");
      const cardSensores = document.getElementById("card-sensores");
      const cardActuadores = document.getElementById("card-actuadores");
      const tituloEstado = document.getElementById("titulo-estado");

      if (data.estado_led) {
        ledElement.innerText = "ACTIVADA";
        ledElement.classList.add("alert-text");
        cardSensores.classList.add("alert");
        cardActuadores.classList.add("alert");
        tituloEstado.innerText = "¡ALARMA ACTIVADA!";
        tituloEstado.style.color = "var(--accent-red)";
      } else {
        ledElement.innerText = "Vigilando";
        ledElement.classList.remove("alert-text");
        cardSensores.classList.remove("alert");
        cardActuadores.classList.remove("alert");
        tituloEstado.innerText = "Estado del Sistema";
        tituloEstado.style.color = "#ffffff";
      }

      document.getElementById("umb_temp").innerText = data.umbral_temp + " °C";
      document.getElementById("umb_humo").innerText = data.umbral_humo;
    });
}, 2000);