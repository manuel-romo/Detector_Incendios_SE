import tkinter as tk
import math

class RadarUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Radar de Torreta")
        
        # Canvas
        self.width = 400
        self.height = 250
        self.canvas = tk.Canvas(self, width=self.width, height=self.height, bg="black")
        self.canvas.pack(padx=20, pady=20)
        
        # Variables del Radar
        self.centro_x = self.width / 2
        self.centro_y = self.height - 20 # Abajo en el centro
        self.radio = 180
        
        # Base del radar
        self.canvas.create_arc(
            self.centro_x - self.radio, self.centro_y - self.radio,
            self.centro_x + self.radio, self.centro_y + self.radio,
            start=0, extent=180, fill="#003300", outline="green", tags="fondo_radar"
        )
        
        # Simulación
        self.angulo_actual = 0
        # 1 para la derecha, -1 para la izquierda
        self.direccion = 1 
        self.animar_radar()

    def animar_radar(self):
        """Esta función simula los datos que llegarían de tu Base de Datos"""
        # Simulación de movimiento del servo
        self.angulo_actual += (5 * self.direccion)
        if self.angulo_actual >= 180:
            self.direccion = -1
        elif self.angulo_actual <= 0:
            self.direccion = 1
            
        # Simulación de detección de fuego
        fuego_detectado = True if 70 <= self.angulo_actual <= 90 else False

        # Actaulización de la UI con nuevos datos
        self.dibujar_escaneo(self.angulo_actual, fuego_detectado)
        
        self.after(50, self.animar_radar)

    def dibujar_escaneo(self, angulo_grados, hay_fuego):
        """Dibuja la aguja y la alerta en el Canvas basado en el ángulo"""
        
        # Limpieza de dibujos anteriores
        self.canvas.delete("aguja")
        self.canvas.delete("alerta")
        
        # Conversión de grados a radianes
        # En Tkinter el ángulo 0 es derecha, y los ángulos crecen en sentido horario.
        angulo_rad = math.radians(180 - angulo_grados)
        
        # Coordenada X e Y de la punta de la aguja
        fin_x = self.centro_x + (self.radio * math.cos(angulo_rad))
        fin_y = self.centro_y - (self.radio * math.sin(angulo_rad))
        
        if hay_fuego:
            # Ancho de 10 grados al sector rojo
            self.canvas.create_arc(
                self.centro_x - self.radio, self.centro_y - self.radio,
                self.centro_x + self.radio, self.centro_y + self.radio,
                start=(180 - angulo_grados) - 5, extent=10, 
                fill="red", outline="yellow", tags="alerta"
            )
        else:
            self.canvas.create_line(
                self.centro_x, self.centro_y, fin_x, fin_y, 
                fill="lime", width=3, tags="aguja"
            )

if __name__ == "__main__":
    app = RadarUI()
    app.mainloop()