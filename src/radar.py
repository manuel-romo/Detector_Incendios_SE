import threading
import customtkinter as ctk
import tkinter as tk
import math
import requests
import os
import time
from dotenv import load_dotenv
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from db_conexion import obtener_conexion

# Cargar variables de entorno
load_dotenv()

ESP32_IP = os.getenv("ESP32_IP", "192.168.1.64")
INTERVALO_LECTURA_BD = 600
SERVO_INVERTIDO = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_COLOR = "#1e1e1e"
CARD_BG = "#2b2b2b"
TEXT_MUTED = "#8a8a8a"
COLOR_ALERTA = "#e74c3c"

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.tw = None

    def enter(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#2b2b2b", foreground="#e0e0e0", relief='solid', borderwidth=1, highlightbackground="#3d3d3d",
                         font=("Arial", 10, "normal"), wraplength=220)
        label.pack(ipadx=8, ipady=8)

    def close(self, event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

class InterfazDetector(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Detección de Incendios Forestales")
        self.geometry("1280x880")
        self.resizable(True, True)
        self.configure(fg_color=BG_COLOR)

        self._activo = True
        self._tarea_pendiente = None
        self._alarma_activa = False
        
        self._estado_cargando = False
        self._cargando_puntos = "."
        
        # Variables de control de conexión
        self.ultimo_id_bd = -1
        self.tiempo_ultima_actualizacion = time.time()
        self.detector_online = False
        self._forzar_grafica = True
        
        # Variables de la animación simulada
        self.angulo_visual_aguja = 90.0     
        self.direccion_barrido = 1        
        self.velocidad_animacion = 1.6    
        self.rango_min = 0   
        self.rango_max = 180 
        
        self.angulo_real_bd = 90.0        
        self.estado_fuego = False          

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._crear_sidebar()
        self._crear_main_frame()

        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

        self.leer_configuracion()
        self.actualizar_datos()           
        self._animar_radar_suave()        

    def _crear_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=15, fg_color=CARD_BG, border_width=0, border_color=CARD_BG)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.sidebar.grid_rowconfigure(1, weight=1) 

        ctk.CTkLabel(
            self.sidebar, text="Parámetros de Detector", font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, pady=(20, 15), padx=20, sticky="w")

        self.scroll_panel = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.scroll_panel.grid(row=1, column=0, sticky="nsew", padx=10)

        self.entradas_config = {}
        
        parametros = [
            ("Límite de Escaneo Mín. (0-180°)", "angulo_minimo", "Ej: 0"),
            ("Límite de Escaneo Máx. (0-180°)", "angulo_maximo", "Ej: 180"),
            ("Retardo de Paso (ms) [30-200]", "velocidad_servo", "Ej: 30"),
            ("Umbral de Radiación IR (0-100%)", "limite_distancia_ir", "Ej: 50.0"),
            ("Umbral de Partículas (ppm) [0-10000]", "limite_gas", "Ej: 4880"),
            ("Umbral de Temperatura [0-100]", "limite_temperatura", "Ej: 60.0"),
            ("Umbral de Presión [500-1500 hPa]", "limite_presion", "Ej: 1013.2")
        ]

        for i, (label_text, key, placeholder) in enumerate(parametros):
            ctk.CTkLabel(self.scroll_panel, text=label_text, text_color=TEXT_MUTED, font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=5, pady=(10, 2))
            entry = ctk.CTkEntry(self.scroll_panel, placeholder_text=placeholder, height=35, border_width=1, corner_radius=8)
            entry.pack(fill="x", padx=5, pady=2)
            self.entradas_config[key] = entry

        frame_botones = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_botones.grid(row=2, column=0, pady=20, padx=15, sticky="ew")

        self.btn_leer = ctk.CTkButton(
            frame_botones, text="Sincronizar con Detector", font=ctk.CTkFont(weight="bold"), 
            fg_color="transparent", border_width=2, border_color="#3498db", text_color="#3498db",
            hover_color="#2980b9", height=40, command=self.leer_configuracion
        )
        self.btn_leer.pack(fill="x", pady=6)

        self.btn_enviar = ctk.CTkButton(
            frame_botones, text="Aplicar Cambios", font=ctk.CTkFont(weight="bold"), 
            fg_color="#2ecc71", hover_color="#27ae60", text_color="white", height=40,
            command=self.enviar_configuracion
        )
        self.btn_enviar.pack(fill="x", pady=6)

        self.lbl_estado_api = ctk.CTkLabel(self.sidebar, text="Enlace Activo", text_color="#2ecc71", font=ctk.CTkFont(size=13))
        self.lbl_estado_api.grid(row=3, column=0, pady=(0, 20))

    def _crear_main_frame(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        self.main_frame.grid_rowconfigure(2, weight=0, minsize=340) 
        self.main_frame.grid_rowconfigure(3, weight=1) 

        self.cards_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.cards_frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.lbl_vars = {}
        self.frames_tarjetas = []
        
        metricas_info = [
            ("Densidad de Humo", "humo", "0.0", "Valores más altos indican mayor concentración de humo o gases combustibles. Valores bajos indican aire limpio."),
            ("Radiación IR", "llama", "0.0 %", "Valores más altos (cerca de 100%) confirman la fuerte presencia de una llama. Valores bajos indican que no hay fuego."),
            ("Temperatura", "temp", "0.0 °C", "Valores más altos (> 60°C) indican un calor anormal o fuego cercano. Valores bajos reflejan el clima local."),
            ("Presión Atmosférica", "pres", "0.0 hPa", "Valores más bajos pueden indicar un sistema de tormenta, mientras que corrientes térmicas por fuego pueden causar fluctuaciones.")
        ]

        for i, (titulo, clave, valor_def, info_text) in enumerate(metricas_info):
            # Se añade borde inactivo
            card = ctk.CTkFrame(self.cards_frame, fg_color=CARD_BG, corner_radius=12, border_width=2, border_color=CARD_BG)
            card.grid(row=0, column=i, sticky="nsew", padx=5)
            self.frames_tarjetas.append(card)
            
            # Contenedor para el titulo y el botón de información
            header_frame = ctk.CTkFrame(card, fg_color="transparent")
            header_frame.pack(pady=(15, 0))
            
            ctk.CTkLabel(header_frame, text=titulo, text_color=TEXT_MUTED, font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
            
            btn_info = ctk.CTkLabel(header_frame, text="?", text_color="#3498db", font=ctk.CTkFont(size=13, weight="bold"), cursor="hand2")
            btn_info.pack(side="left", padx=(5, 0))
            ToolTip(btn_info, text=info_text)

            lbl_val = ctk.CTkLabel(card, text=valor_def, font=ctk.CTkFont(size=24, weight="bold"))
            lbl_val.pack(pady=(5, 15))
            self.lbl_vars[clave] = lbl_val

        self.lbl_estado = ctk.CTkLabel(self.main_frame, text="ESTABLECIENDO CONEXIÓN...", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT_MUTED)
        self.lbl_estado.grid(row=1, column=0, pady=5)

        # Se añade borde inactivo
        self.radar_frame = ctk.CTkFrame(self.main_frame, fg_color=CARD_BG, corner_radius=15, border_width=2, border_color=CARD_BG)
        self.radar_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 15))
        self._crear_radar(self.radar_frame)

        # Se añade borde inactivo
        self.bottom_frame = ctk.CTkFrame(self.main_frame, fg_color=CARD_BG, corner_radius=15, border_width=2, border_color=CARD_BG)
        self.bottom_frame.grid(row=3, column=0, sticky="nsew")

        ctrl_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(15, 0))
        
        ctk.CTkLabel(ctrl_frame, text="Histórico de Telemetría", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.periodo_grafica_var = ctk.StringVar(value="Últimos 20 (En vivo)")
        ctk.CTkOptionMenu(
            ctrl_frame, values=["Últimos 20 (En vivo)", "Última hora", "Últimas 24 horas", "Últimos 7 días"],
            variable=self.periodo_grafica_var, width=160, fg_color="#3a3a3a", button_color="#4a4a4a",
            command=self._forzar_redraw
        ).pack(side="right", padx=5)

        self.metrica_grafica_var = ctk.StringVar(value="Temperatura")
        ctk.CTkOptionMenu(
            ctrl_frame, values=["Temperatura", "Presión Atmosférica", "Densidad de Humo", "Radiación IR"],
            variable=self.metrica_grafica_var, width=170, fg_color="#3a3a3a", button_color="#4a4a4a",
            command=self._forzar_redraw
        ).pack(side="right", padx=5)

        self.fig, self.ax = plt.subplots(figsize=(10, 3.5), dpi=100)
        self.fig.patch.set_facecolor(CARD_BG)
        self.ax.set_facecolor(CARD_BG)

        for spine in ["top", "right", "left", "bottom"]:
            self.ax.spines[spine].set_visible(False)

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.bottom_frame)
        self.canvas_plot.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _forzar_redraw(self, _):
        self._forzar_grafica = True
        threading.Thread(target=self._threaded_update_bd, daemon=True).start()

    def _crear_radar(self, parent):
        self.canvas_width = 600
        self.canvas_height = 320 
        self.centro_y = 290      

        self.canvas = tk.Canvas(parent, width=self.canvas_width, height=self.canvas_height, bg=CARD_BG, highlightthickness=0)
        self.canvas.pack(pady=10)

        self.centro_x = self.canvas_width // 2
        self.radio_radar = 230
        self.radio_aguja = self.radio_radar - 20

        self.canvas.create_oval(
            self.centro_x - self.radio_radar - 15, self.centro_y - self.radio_radar - 15,
            self.centro_x + self.radio_radar + 15, self.centro_y + self.radio_radar + 15,
            fill="#121a16", outline="#2ecc71", width=2, tags="fondo"
        )

        self.canvas.create_arc(
            self.centro_x - self.radio_radar, self.centro_y - self.radio_radar,
            self.centro_x + self.radio_radar, self.centro_y + self.radio_radar,
            start=0, extent=180, fill="#1c3b28", outline="", tags="zona_escaneo"
        )

        for r in [80, 155, self.radio_radar]:
            self.canvas.create_oval(self.centro_x - r, self.centro_y - r, self.centro_x + r, self.centro_y + r, outline="#27ae60", width=1, dash=(2, 4))

        self.canvas.create_line(self.centro_x, self.centro_y - self.radio_radar - 25, self.centro_x, self.centro_y, fill="#27ae60", width=1, dash=(4, 4))

        for ang in range(0, 181, 30):
            rad = math.radians(ang)
            cx = math.cos(rad)
            cy = -math.sin(rad)

            x1 = self.centro_x + (self.radio_radar - 15) * cx
            y1 = self.centro_y + (self.radio_radar - 15) * cy
            x2 = self.centro_x + (self.radio_radar + 5) * cx
            y2 = self.centro_y + (self.radio_radar + 5) * cy

            self.canvas.create_line(x1, y1, x2, y2, fill="#2ecc71", width=2)

            lx = self.centro_x + (self.radio_radar + 25) * cx
            ly = self.centro_y + (self.radio_radar + 25) * cy
            self.canvas.create_text(lx, ly, text=f"{ang}°", fill="#a8e6cf", font=("Arial", 10, "bold"))

        self.canvas.create_arc(
            self.centro_x - 35, self.centro_y - 35, 
            self.centro_x + 35, self.centro_y + 35, 
            start=0, extent=180, fill="#2b2b2b", outline="#2ecc71", width=2
        )

    def actualizar_datos(self):
        if not self._activo: return
        threading.Thread(target=self._threaded_update_bd, daemon=True).start()
        self._tarea_pendiente = self.after(INTERVALO_LECTURA_BD, self.actualizar_datos)

    def _threaded_update_bd(self):
        conexion = None
        cursor = None
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("SELECT * FROM registro_sensores ORDER BY id DESC LIMIT 1")
            ultimo = cursor.fetchone()

            if ultimo:
                nuevo_id = ultimo['id']
                historico = None
                
                if nuevo_id != self.ultimo_id_bd or self._forzar_grafica:
                    self._forzar_grafica = False
                    
                    filtro = self.periodo_grafica_var.get()
                    metrica = self.metrica_grafica_var.get()

                    columna = "temperatura"
                    if metrica == "Presión Atmosférica": columna = "presion"
                    elif metrica == "Densidad de Humo": columna = "humo_mq2"
                    elif metrica == "Radiación IR": columna = "fuego_raw"

                    if filtro == "Última hora":
                        cursor.execute(f"SELECT {columna} as valor, fecha_hora FROM registro_sensores WHERE fecha_hora BETWEEN NOW() - INTERVAL 1 HOUR AND NOW() ORDER BY fecha_hora ASC LIMIT 500")
                    elif filtro == "Últimas 24 horas":
                        cursor.execute(f"SELECT {columna} as valor, fecha_hora FROM registro_sensores WHERE fecha_hora BETWEEN NOW() - INTERVAL 1 DAY AND NOW() ORDER BY fecha_hora ASC LIMIT 500")
                    elif filtro == "Últimos 7 días":
                        cursor.execute(f"SELECT {columna} as valor, fecha_hora FROM registro_sensores WHERE fecha_hora BETWEEN NOW() - INTERVAL 7 DAY AND NOW() ORDER BY fecha_hora ASC LIMIT 500")
                    else:
                        cursor.execute(f"SELECT {columna} as valor, fecha_hora FROM registro_sensores ORDER BY id DESC LIMIT 20")
                        
                    historico = cursor.fetchall()
                
                self.after(0, self._apply_updated_data, ultimo, historico)

        except Exception as e:
            pass
        finally:
            if cursor: cursor.close()
            if conexion and conexion.is_connected(): conexion.close()

    def _cambiar_estado_visual(self, en_alerta):
        """Aplica o remueve los bordes rojos en todos los contenedores principales."""
        color_borde = COLOR_ALERTA if en_alerta else CARD_BG
        grosor_sidebar = 2 if en_alerta else 0

        for card in self.frames_tarjetas:
            card.configure(border_color=color_borde)
        
        self.radar_frame.configure(border_color=color_borde)
        self.bottom_frame.configure(border_color=color_borde)
        self.sidebar.configure(border_color=color_borde, border_width=grosor_sidebar)

    def _apply_updated_data(self, data, historico):
        if not self._activo: return
        
        current_id = data['id']
        
        if current_id != self.ultimo_id_bd:
            self.ultimo_id_bd = current_id
            self.tiempo_ultima_actualizacion = time.time()
            self.detector_online = True
            
            # Convertir a porcentajes y unidades amigables
            ir_pct = (1.0 - (float(data['fuego_raw']) / 4095.0)) * 100.0
            pres_hpa = float(data['presion']) / 100.0
            humo_ppm = (float(data['humo_mq2']) / 4095.0) * 10000.0
            
            self.lbl_vars["humo"].configure(text=f"{humo_ppm:.0f} ppm")
            self.lbl_vars["llama"].configure(text=f"{ir_pct:.1f} %")
            self.lbl_vars["temp"].configure(text=f"{float(data['temperatura']):.1f} °C")
            self.lbl_vars["pres"].configure(text=f"{pres_hpa:.1f} hPa")
            
            if historico:
                self._dibujar_grafica(historico, self.periodo_grafica_var.get(), self.metrica_grafica_var.get())
        else:
            if time.time() - self.tiempo_ultima_actualizacion > 8:
                self.detector_online = False

        self.estado_fuego = data.get("incendio_confirmado", False)
        angulo_bruto = data["estado_servo"]
        self.angulo_real_bd = (180 - angulo_bruto) if SERVO_INVERTIDO else angulo_bruto

        # Lógica centralizada de actualización visual
        if not self.detector_online:
            self.lbl_estado.configure(text="⚠️ SIN DATOS NUEVOS", text_color="#f39c12")
            self._cambiar_estado_visual(False)
            self._alarma_activa = False
            
        elif self.estado_fuego:
            self.lbl_estado.configure(text="Estado Crítico: Incendio Confirmado", text_color=COLOR_ALERTA)
            self._cambiar_estado_visual(True)
            if not self._alarma_activa:
                self._alarma_activa = True
                self._parpadear_alarma()
                
        else:
            self.lbl_estado.configure(text="● Patrullaje Normal", text_color="#2ecc71")
            self._cambiar_estado_visual(False)
            self._alarma_activa = False

    def _parpadear_alarma(self):
        if not self._alarma_activa or not self._activo: return
        current_color = self.lbl_estado.cget("text_color")
        new_color = "#f1c40f" if current_color == COLOR_ALERTA else COLOR_ALERTA
        self.lbl_estado.configure(text_color=new_color)
        self.after(600, self._parpadear_alarma)

    def _animar_radar_suave(self):
        if not self._activo: return

        self.canvas.delete("aguja")
        self.canvas.delete("alerta")

        if self.detector_online:
            self.angulo_visual_aguja += self.velocidad_animacion * self.direccion_barrido
            
            if self.angulo_visual_aguja >= self.rango_max:
                self.angulo_visual_aguja = self.rango_max
                self.direccion_barrido = -1
            elif self.angulo_visual_aguja <= self.rango_min:
                self.angulo_visual_aguja = self.rango_min
                self.direccion_barrido = 1

            if self.estado_fuego:
                self.canvas.create_arc(
                    self.centro_x - self.radio_radar - 18, self.centro_y - self.radio_radar - 18,
                    self.centro_x + self.radio_radar + 18, self.centro_y + self.radio_radar + 18,
                    start=self.angulo_real_bd - 20, extent=40, outline=COLOR_ALERTA, width=16, tags="alerta",
                )

        rad = math.radians(self.angulo_visual_aguja)
        fin_x = self.centro_x + self.radio_aguja * math.cos(rad)
        fin_y = self.centro_y - self.radio_aguja * math.sin(rad)

        color_aguja = "#2ecc71" if self.detector_online else "#7f8c8d"

        self.canvas.create_line(self.centro_x, self.centro_y, fin_x, fin_y, fill=color_aguja, width=4, tags="aguja")
        self.canvas.create_oval(fin_x - 4, fin_y - 4, fin_x + 4, fin_y + 4, fill="#fff", outline="", tags="aguja")
        
        self.canvas.create_oval(
            self.centro_x - 14, self.centro_y - 14, 
            self.centro_x + 14, self.centro_y + 14, 
            fill="#1a2520", outline=color_aguja, width=3, tags="aguja"
        )
        self.canvas.create_oval(
            self.centro_x - 4, self.centro_y - 4, 
            self.centro_x + 4, self.centro_y + 4, 
            fill=color_aguja, outline="", tags="aguja"
        )
        
        self.after(30, self._animar_radar_suave)

    def _dibujar_grafica(self, historico, filtro, metrica):
        if filtro == "Últimos 20 (En vivo)": historico.reverse()

        indices = list(range(len(historico)))
        if filtro in ["Últimas 24 horas", "Últimos 7 días"]:
            etiquetas = [t["fecha_hora"].strftime("%d/%m %H:%M") for t in historico]
        else:
            etiquetas = [t["fecha_hora"].strftime("%H:%M:%S") for t in historico]

        valores = [float(t["valor"]) for t in historico]

        self.ax.clear()

        color_linea = COLOR_ALERTA
        if metrica == "Presión Atmosférica": color_linea = "#3498db"
        elif metrica == "Densidad de Humo": color_linea = "#95a5a6"
        elif metrica == "Radiación IR": color_linea = "#f39c12"

        self.ax.plot(indices, valores, marker="o", linewidth=2.5, color=color_linea, markersize=5)
        self.ax.fill_between(indices, valores, color=color_linea, alpha=0.15)

        paso = max(1, len(indices) // 8)
        self.ax.set_xticks(indices[::paso])
        self.ax.set_xticklabels(etiquetas[::paso])
        
        self.ax.grid(True, axis='y', alpha=0.1, color="#ffffff", linestyle="--")
        self.ax.grid(False, axis='x')
        self.ax.tick_params(colors=TEXT_MUTED, labelsize=9, length=0)
        self.ax.tick_params(axis="x", rotation=0)

        if valores:
            min_val, max_val = min(valores), max(valores)
            margen = (max_val - min_val) * 0.2 if max_val != min_val else 1
            self.ax.set_ylim(min_val - margen, max_val + margen)

        self.fig.tight_layout(pad=1.5)
        self.canvas_plot.draw()

    def _animar_cargando(self):
        if not self._estado_cargando or not self._activo: return
        self.lbl_estado_api.configure(text=f"⏳ Sincronizando{self._cargando_puntos}", text_color="#f39c12")
        self._cargando_puntos = "." * ((len(self._cargando_puntos) % 3) + 1)
        self.after(400, self._animar_cargando)

    def leer_configuracion(self):
        if self._estado_cargando: return
        self._estado_cargando = True
        self._cargando_puntos = "."
        self.btn_leer.configure(state="disabled")
        self.btn_enviar.configure(state="disabled")
        self._animar_cargando()
        threading.Thread(target=self._hilo_leer_api, daemon=True).start()

    def _hilo_leer_api(self):
        try:
            ip_base = ESP32_IP if ESP32_IP.startswith("http") else f"http://{ESP32_IP}"
            res = requests.get(f"{ip_base}/api/estado", timeout=5)
            self.after(0, self._resultado_leer, res.status_code, res.json() if res.status_code == 200 else None, None)
        except Exception as e:
            self.after(0, self._resultado_leer, None, None, str(e))

    def _resultado_leer(self, status, json_data, error):
        self._estado_cargando = False
        self.btn_leer.configure(state="normal")
        self.btn_enviar.configure(state="normal")

        if error:
            self.lbl_estado_api.configure(text="⚠️ Detector inaccesible", text_color="#f39c12")
            return

        if status == 200:
            config = json_data.get("configuracion", {})
            
            self.rango_min = int(config.get("angulo_minimo", 0))
            self.rango_max = int(config.get("angulo_maximo", 180))
            
            if self.angulo_visual_aguja < self.rango_min:
                self.angulo_visual_aguja = self.rango_min
            elif self.angulo_visual_aguja > self.rango_max:
                self.angulo_visual_aguja = self.rango_max

            if self.rango_min < self.rango_max:
                self.canvas.itemconfigure("zona_escaneo", start=self.rango_min, extent=(self.rango_max - self.rango_min))

            datos_planos = {
                "limite_temperatura": config.get("limite_temperatura", ""),
                "limite_gas": config.get("limite_gas", ""),
                "limite_distancia_ir": config.get("limite_distancia_ir", ""),
                "limite_presion": config.get("limite_presion", ""),
                "velocidad_servo": config.get("velocidad_servo", ""),
                "angulo_minimo": config.get("angulo_minimo", ""), 
                "angulo_maximo": config.get("angulo_maximo", "")  
            }

            # Convertir formato crudo a unidades amigables para la UI
            if datos_planos["limite_distancia_ir"] != "":
                ir_raw = float(datos_planos["limite_distancia_ir"])
                datos_planos["limite_distancia_ir"] = f"{(1.0 - (ir_raw / 4095.0)) * 100.0:.1f}"
            
            if datos_planos.get("limite_gas") and str(datos_planos["limite_gas"]) != "":
                gas_raw = float(datos_planos["limite_gas"])
                datos_planos["limite_gas"] = f"{(gas_raw / 4095.0) * 10000.0:.0f}"

            if datos_planos["limite_presion"] != "":
                pres_raw = float(datos_planos["limite_presion"])
                datos_planos["limite_presion"] = f"{pres_raw / 100.0:.1f}"

            for key, entry in self.entradas_config.items():
                if key in datos_planos and str(datos_planos[key]) != "":
                    entry.delete(0, tk.END)
                    entry.insert(0, str(datos_planos[key]))
                    
            self.lbl_estado_api.configure(text="✅ Sincronizado", text_color="#2ecc71")
        else:
            self.lbl_estado_api.configure(text=f"❌ Error Enlace {status}", text_color=COLOR_ALERTA)

    def enviar_configuracion(self):
        if self._estado_cargando: return
        self._estado_cargando = True
        self._cargando_puntos = "."
        self.btn_leer.configure(state="disabled")
        self.btn_enviar.configure(state="disabled")
        self._animar_cargando()

        payload = {}
        for key, entry in self.entradas_config.items():
            valor = entry.get()
            if valor != "":
                try:
                    val_float = float(valor)
                    val_ui = val_float
                    
                    if key in ["angulo_minimo", "angulo_maximo"]:
                        val_final = int(max(0, min(180, val_float)))
                        val_ui = val_final
                    elif key == "velocidad_servo":
                        val_final = int(max(30, min(200, val_float)))
                        val_ui = val_final
                    elif key == "limite_distancia_ir":
                        val_ui = float(max(0.0, min(100.0, val_float)))
                        val_final = int((1.0 - (val_ui / 100.0)) * 4095.0)
                    elif key == "limite_gas":
                        val_ui = float(max(0.0, min(10000.0, val_float)))
                        val_final = int((val_ui / 10000.0) * 4095.0)
                    elif key == "limite_temperatura":
                        val_final = float(max(-40.0, min(150.0, val_float)))
                        val_ui = val_final
                    elif key == "limite_presion":
                        val_ui = float(max(500.0, min(1500.0, val_float)))
                        val_final = int(val_ui * 100)
                    else:
                        val_final = val_float
                        val_ui = val_float

                    if str(val_ui) != valor and str(float(val_ui)) != valor:
                        entry.delete(0, tk.END)
                        entry.insert(0, str(val_ui))
                        
                    payload[key] = val_final
                    
                except ValueError:
                    self._estado_cargando = False
                    self.btn_leer.configure(state="normal")
                    self.btn_enviar.configure(state="normal")
                    self.lbl_estado_api.configure(text="⚠️ Error: Formato numérico", text_color=COLOR_ALERTA)
                    return

        threading.Thread(target=self._hilo_enviar_api, args=(payload,), daemon=True).start()

    def _hilo_enviar_api(self, payload):
        try:
            ip_base = ESP32_IP if ESP32_IP.startswith("http") else f"http://{ESP32_IP}"
            res = requests.post(f"{ip_base}/api/configuracion", json=payload, timeout=5)
            self.after(0, self._resultado_enviar, res.status_code, None)
        except Exception as e:
            self.after(0, self._resultado_enviar, None, str(e))

    def _resultado_enviar(self, status, error):
        self._estado_cargando = False
        self.btn_leer.configure(state="normal")
        self.btn_enviar.configure(state="normal")

        if error:
            self.lbl_estado_api.configure(text="Error de conexión", text_color="#f39c12")
        elif status == 200:
            self.lbl_estado_api.configure(text="Parámetros enviados", text_color="#2ecc71")
            self.leer_configuracion()
        else:
            self.lbl_estado_api.configure(text=f"Error Enlace {status}", text_color=COLOR_ALERTA)

    def _al_cerrar(self):
        self._activo = False
        if self._tarea_pendiente:
            self.after_cancel(self._tarea_pendiente)
        plt.close(self.fig)
        self.destroy()

if __name__ == "__main__":
    app = InterfazDetector()
    app.mainloop()