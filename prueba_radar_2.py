import customtkinter as ctk
import tkinter as tk
import math
import requests
import mysql.connector
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# Configuración
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'torreta_db'
}

# IP de ESP32
ESP32_IP = "http://192.168.1.100"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class InterfazTorreta(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Empotrado - Monitor de Torreta")
        self.geometry("1100x700")

        # Configuración de grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Controles y parámetros
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.lbl_titulo = ctk.CTkLabel(self.sidebar, text="CONFIGURACIÓN", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_titulo.pack(pady=20)

        # Temperatura
        ctk.CTkLabel(self.sidebar, text="Umbral Alarma Temp (°C):").pack(pady=(10, 0))
        self.entry_temp = ctk.CTkEntry(self.sidebar, placeholder_text="Ej. 35")
        self.entry_temp.pack(pady=5)

        # Humo
        ctk.CTkLabel(self.sidebar, text="Umbral Alarma Humo (MQ2):").pack(pady=(10, 0))
        self.entry_humo = ctk.CTkEntry(self.sidebar, placeholder_text="Ej. 600")
        self.entry_humo.pack(pady=5)

        self.btn_enviar = ctk.CTkButton(self.sidebar, text="Enviar al ESP32", command=self.enviar_configuracion)
        self.btn_enviar.pack(pady=20)

        # Visualización
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1) # Fila Radar
        self.main_frame.grid_rowconfigure(1, weight=1) # Fila Gráfica

        # Radar y Estado
        self.top_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="nsew")

        # Datos de texto
        self.lbl_estado = ctk.CTkLabel(self.top_frame, text="ESPERANDO DATOS...", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_estado.pack(pady=10)
        
        self.lbl_sensores = ctk.CTkLabel(self.top_frame, text="Humo: -- | Temp: --°C | Presión: -- hPa", font=ctk.CTkFont(size=16))
        self.lbl_sensores.pack(pady=5)

        # Canvas del Radar
        self.canvas_width = 400
        self.canvas_height = 220
        self.canvas = tk.Canvas(self.top_frame, width=self.canvas_width, height=self.canvas_height, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(pady=10)
        self.centro_x = self.canvas_width / 2
        self.centro_y = self.canvas_height - 20
        self.radio_radar = 180

        # Base del radar
        self.canvas.create_arc(
            self.centro_x - self.radio_radar, self.centro_y - self.radio_radar,
            self.centro_x + self.radio_radar, self.centro_y + self.radio_radar,
            start=0, extent=180, fill="#002200", outline="#00ff00", tags="fondo"
        )

        # Gráfica de Matplotlib
        self.bottom_frame = ctk.CTkFrame(self.main_frame)
        self.bottom_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.fig, self.ax = plt.subplots(figsize=(6, 3), dpi=100)
        self.ax.set_facecolor('#f0f0f0')
        self.fig.patch.set_facecolor('#2b2b2b') # Fondo oscuro para combinar
        self.ax.tick_params(colors='white')
        
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.bottom_frame)
        self.canvas_plot.get_tk_widget().pack(fill="both", expand=True)

        # Iniciar hilo de monitoreo
        self.actualizar_datos()

    # Funciones
    def enviar_configuracion(self):
        """Envía los parámetros por POST al ESP32"""
        datos = {
            "umbral_temp": float(self.entry_temp.get() or 0),
            "umbral_humo": float(self.entry_humo.get() or 0)
        }
        try:
            res = requests.post(f"{ESP32_IP}/api/config", json=datos, timeout=2)
            if res.status_code == 200:
                print("Configuración enviada correctamente.")
        except Exception as e:
            print(f"Error conectando con ESP32: {e}")

    def actualizar_datos(self):
        """Consulta la BD y actualiza UI (Radar, Textos y Gráfica)"""
        try:
            conexion = mysql.connector.connect(**DB_CONFIG)
            cursor = conexion.cursor(dictionary=True)
            
            # Se obtiene el registro más reciente para el radar y textos
            cursor.execute("SELECT * FROM registro_sensores ORDER BY id DESC LIMIT 1")
            ultimo = cursor.fetchone()
            
            if ultimo:
                # Actualización de texto
                self.lbl_sensores.configure(text=f"Humo: {ultimo['humo_mq2']} | Temp: {ultimo['temperatura']}°C | Presión: {ultimo['presion']} hPa")
                
                # Lógica de colores y estados
                hay_fuego = ultimo['fuego_detectado']
                if hay_fuego:
                    self.lbl_estado.configure(text="🔥 ALARMA DE INCENDIO 🔥", text_color="red")
                else:
                    self.lbl_estado.configure(text="SISTEMA VIGILANDO", text_color="green")
                
                # Actualización de Radar
                self.dibujar_radar(ultimo['estado_servo'], hay_fuego)

            # Actualización de Gráfica (Últimos 15 registros de temperatura)
            cursor.execute("SELECT temperatura, fecha_hora FROM registro_sensores ORDER BY id DESC LIMIT 15")
            historico = cursor.fetchall()
            if historico:
                historico.reverse()
                tiempos = [t['fecha_hora'].strftime('%H:%M:%S') for t in historico]
                temps = [t['temperatura'] for t in historico]
                
                self.ax.clear()
                self.ax.plot(tiempos, temps, marker='o', color='red')
                self.ax.set_title("Histórico de Temperatura", color='white')
                self.ax.tick_params(axis='x', rotation=45, labelsize=8)
                self.fig.tight_layout()
                self.canvas_plot.draw()

            cursor.close()
            conexion.close()
        except Exception as e:
            # Se reintenta
            pass 

        # Se repite cada 1.5 segundos
        self.after(1500, self.actualizar_datos)

    def dibujar_radar(self, angulo, hay_fuego):
        """Actualiza la aguja y la alerta del radar en base al ángulo real del servo"""
        self.canvas.delete("aguja")
        self.canvas.delete("alerta")
        
        angulo_rad = math.radians(180 - angulo)
        fin_x = self.centro_x + (self.radio_radar * math.cos(angulo_rad))
        fin_y = self.centro_y - (self.radio_radar * math.sin(angulo_rad))
        
        if hay_fuego:
            # Sector rojo en la dirección del fuego
            self.canvas.create_arc(
                self.centro_x - self.radio_radar, self.centro_y - self.radio_radar,
                self.centro_x + self.radio_radar, self.centro_y + self.radio_radar,
                start=(180 - angulo) - 10, extent=20, fill="#ff0000", tags="alerta"
            )
        else:
            # Aguja de escaneo
            self.canvas.create_line(self.centro_x, self.centro_y, fin_x, fin_y, fill="#00ff00", width=3, tags="aguja")

if __name__ == "__main__":
    app = InterfazTorreta()
    app.mainloop()