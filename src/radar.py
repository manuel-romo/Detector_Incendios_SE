import customtkinter as ctk
import tkinter as tk
import math
import requests
import os
from dotenv import load_dotenv
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from db_conexion import obtener_conexion

# Cargar variables de entorno
load_dotenv()

ESP32_IP = os.getenv("ESP32_IP")
INTERVALO_MS = 600
SERVO_INVERTIDO = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class InterfazTorreta(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Detección de Incendios - Torreta")
        self.geometry("1200x840")
        self.resizable(True, True)

        self._activo = True
        self._tarea_pendiente: str | None = None
        self._alarma_activa = False
        self._ultimo_estado_fuego = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._crear_sidebar()
        self._crear_main_frame()

        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

        self.actualizar_datos()

    def _crear_sidebar(self):
        """Panel lateral de configuración"""
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

        ctk.CTkLabel(
            self.sidebar, text="CONFIGURACIÓN", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(20, 30))

        # Umbral Temperatura
        ctk.CTkLabel(
            self.sidebar, text="Umbral Temperatura (°C):", font=ctk.CTkFont(size=14)
        ).pack(anchor="w", padx=20, pady=(10, 5))
        self.entry_temp = ctk.CTkEntry(
            self.sidebar, placeholder_text="Ej: 38", width=200
        )
        self.entry_temp.pack(pady=5, padx=20)

        # Umbral Humo
        ctk.CTkLabel(
            self.sidebar, text="Umbral Humo (MQ2):", font=ctk.CTkFont(size=14)
        ).pack(anchor="w", padx=20, pady=(15, 5))
        self.entry_humo = ctk.CTkEntry(
            self.sidebar, placeholder_text="Ej: 550", width=200
        )
        self.entry_humo.pack(pady=5, padx=20)

        ctk.CTkButton(
            self.sidebar,
            text="ENVIAR CONFIGURACIÓN AL ESP32",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.enviar_configuracion,
        ).pack(pady=30, padx=20)

        ctk.CTkLabel(
            self.sidebar,
            text="Sistema Activo",
            text_color="green",
            font=ctk.CTkFont(size=13),
        ).pack(side="bottom", pady=20)

    def _crear_main_frame(self):
        """Frame principal con radar y gráfica"""
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Zona Superior: Radar + Estado
        self.top_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        # Estado general
        self.lbl_estado = ctk.CTkLabel(
            self.top_frame,
            text="ESPERANDO DATOS...",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="gray",
        )
        self.lbl_estado.pack(pady=15)

        # Sensores
        self.lbl_sensores = ctk.CTkLabel(
            self.top_frame,
            text="Humo: -- | Temp: --°C | Presión: -- hPa",
            font=ctk.CTkFont(size=18),
            text_color="#cccccc",
        )
        self.lbl_sensores.pack(pady=8)

        # Radar
        self._crear_radar()

        self.bottom_frame = ctk.CTkFrame(self.main_frame)
        self.bottom_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        self.fig, self.ax = plt.subplots(
            figsize=(10, 4.2), dpi=110, facecolor="#2b2b2b"
        )
        self.ax.set_facecolor("#1f1f1f")

        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.bottom_frame)
        self.canvas_plot.get_tk_widget().pack(
            fill="both", expand=True, padx=10, pady=10
        )

        self.periodo_grafica_var = ctk.StringVar(value="Últimos 20 (En vivo)")
        self.dropdown_periodo = ctk.CTkOptionMenu(
            self.bottom_frame,
            values=[
                "Últimos 20 (En vivo)",
                "Última hora",
                "Últimas 24 horas",
                "Últimos 7 días",
            ],
            variable=self.periodo_grafica_var,
            width=200,
        )
        self.dropdown_periodo.place(relx=0.97, y=25, anchor="ne")
        self.dropdown_periodo.lift()

        self.metrica_grafica_var = ctk.StringVar(value="Temperatura")
        self.dropdown_metrica = ctk.CTkOptionMenu(
            self.bottom_frame,
            values=["Temperatura", "Presión", "Humo"],
            variable=self.metrica_grafica_var,
            width=150,
        )
        self.dropdown_metrica.place(relx=0.97, x=-210, y=25, anchor="ne")
        self.dropdown_metrica.lift()

    def _crear_radar(self):
        """Crea el radar con más margen y mejor visibilidad en 0° y 180°"""
        self.canvas_width = 540
        self.canvas_height = 370

        self.canvas = tk.Canvas(
            self.top_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="#0f0f0f",
            highlightthickness=0,
        )
        self.canvas.pack(pady=15)

        self.centro_x = self.canvas_width // 2
        self.centro_y = 260
        self.radio_radar = 195
        self.radio_aguja = self.radio_radar - 20

        self.canvas.create_oval(
            self.centro_x - self.radio_radar - 15,
            self.centro_y - self.radio_radar - 15,
            self.centro_x + self.radio_radar + 15,
            self.centro_y + self.radio_radar + 15,
            fill="#001a00",
            outline="#00cc00",
            width=4,
            tags="fondo",
        )

        for r in [65, 130, self.radio_radar]:
            self.canvas.create_oval(
                self.centro_x - r,
                self.centro_y - r,
                self.centro_x + r,
                self.centro_y + r,
                outline="#003300",
                width=2,
            )

        self.canvas.create_line(
            self.centro_x,
            self.centro_y - self.radio_radar - 25,
            self.centro_x,
            self.centro_y + self.radio_radar + 25,
            fill="#004411",
            width=2,
            dash=(4, 4),
        )

        for ang in range(0, 360, 30):
            rad = math.radians(ang)
            cx = math.cos(rad)
            cy = -math.sin(rad)

            # Líneas guía radiales desde el centro
            if ang not in (0, 90, 180, 270):
                self.canvas.create_line(
                    self.centro_x,
                    self.centro_y,
                    self.centro_x + (self.radio_radar - 5) * cx,
                    self.centro_y + (self.radio_radar - 5) * cy,
                    fill="#002b00",
                    width=1,
                )

            # Marca en el borde del arco
            x1 = self.centro_x + (self.radio_radar - 22) * cx
            y1 = self.centro_y + (self.radio_radar - 22) * cy
            x2 = self.centro_x + (self.radio_radar + 12) * cx
            y2 = self.centro_y + (self.radio_radar + 12) * cy

            color_marca = "#00ff66" if ang in (0, 90, 180, 270) else "#00aa00"
            grosor = 4 if ang in (0, 180) else 2

            self.canvas.create_line(x1, y1, x2, y2, fill=color_marca, width=grosor)

            # Etiqueta más afuera
            lx = self.centro_x + (self.radio_radar + 32) * cx
            ly = self.centro_y + (self.radio_radar + 32) * cy
            color_lbl = "#00ff88" if ang in (0, 180) else "#00cc44"

            self.canvas.create_text(
                lx,
                ly,
                text=f"{ang}°",
                fill=color_lbl,
                font=("Courier", 10, "bold"),
            )

        # Punto central del radar
        self.canvas.create_oval(
            self.centro_x - 10,
            self.centro_y - 10,
            self.centro_x + 10,
            self.centro_y + 10,
            fill="#00ff88",
            outline="#003300",
            width=3,
        )

    def actualizar_datos(self):
        """Actualiza todos los datos de la interfaz"""
        if not self._activo:
            return

        if self._tarea_pendiente:
            self.after_cancel(self._tarea_pendiente)
            self._tarea_pendiente = None

        conexion = None
        cursor = None
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("SELECT * FROM registro_sensores ORDER BY id DESC LIMIT 1")
            ultimo = cursor.fetchone()

            if ultimo:
                self._actualizar_indicadores(ultimo)
                self.dibujar_radar(ultimo["estado_servo"], ultimo["fuego_detectado"])
                self._actualizar_grafica(cursor)

        except Exception as e:
            self.lbl_estado.configure(text="⚠️ ERROR DE CONEXIÓN", text_color="orange")
            print(f"[UI] Error: {e}")
        finally:
            if cursor:
                cursor.close()
            if conexion and conexion.is_connected():
                conexion.close()

        if self._activo:
            self._tarea_pendiente = self.after(INTERVALO_MS, self.actualizar_datos)

    def _actualizar_indicadores(self, data):
        """Actualiza labels de sensores y estado"""
        self.lbl_sensores.configure(
            text=f"Humo: {data['humo_mq2']} | Temp: {data['temperatura']}°C | Presión: {data['presion']} hPa"
        )

        if data["fuego_detectado"]:
            self.lbl_estado.configure(
                text="🔥 ¡ALARMA DE INCENDIO ACTIVADA! 🔥", text_color="#ff3333"
            )
            self._activar_alarma_visual()
        else:
            self.lbl_estado.configure(
                text="● SISTEMA VIGILANDO NORMALMENTE", text_color="#00ff88"
            )
            self._desactivar_alarma_visual()

    def _activar_alarma_visual(self):
        if not self._alarma_activa:
            self._alarma_activa = True
            self._parpadear_alarma()

    def _desactivar_alarma_visual(self):
        self._alarma_activa = False

    def _parpadear_alarma(self):
        """Efecto de parpadeo en la alarma"""
        if not self._alarma_activa or not self._activo:
            return
        current_color = self.lbl_estado.cget("text_color")
        new_color = "#ffff00" if current_color == "#ff3333" else "#ff3333"
        self.lbl_estado.configure(text_color=new_color)
        self.after(600, self._parpadear_alarma)

    def dibujar_radar(self, angulo: float, hay_fuego: bool):
        """Dibuja la aguja del radar en el ángulo indicado."""
        self.canvas.delete("aguja")
        self.canvas.delete("alerta")

        ang_canvas = (180 - angulo) if SERVO_INVERTIDO else angulo
        rad = math.radians(ang_canvas)

        fin_x = self.centro_x + self.radio_aguja * math.cos(rad)
        fin_y = self.centro_y - self.radio_aguja * math.sin(rad)

        if hay_fuego:
            # Arco de alerta más visible
            self.canvas.create_arc(
                self.centro_x - self.radio_radar - 18,
                self.centro_y - self.radio_radar - 18,
                self.centro_x + self.radio_radar + 18,
                self.centro_y + self.radio_radar + 18,
                start=angulo - 20,
                extent=40,
                outline="#ff0000",
                width=16,
                tags="alerta",
            )
        else:
            # Aguja normal
            self.canvas.create_line(
                self.centro_x,
                self.centro_y,
                fin_x,
                fin_y,
                fill="#00ff55",
                width=6,
                tags="aguja",
            )

            # Punta de flecha
            arrow_length = 26
            arrow_width = 16

            dx = fin_x - self.centro_x
            dy = fin_y - self.centro_y
            length = math.hypot(dx, dy)

            if length > 1:
                ux = dx / length
                uy = dy / length

                base_x = fin_x - ux * arrow_length
                base_y = fin_y - uy * arrow_length

                px = -uy * (arrow_width / 2)
                py = ux * (arrow_width / 2)

                p1x = fin_x
                p1y = fin_y
                p2x = base_x + px
                p2y = base_y + py
                p3x = base_x - px
                p3y = base_y - py

                self.canvas.create_polygon(
                    p1x,
                    p1y,
                    p2x,
                    p2y,
                    p3x,
                    p3y,
                    fill="#00ff55",
                    outline="#00cc44",
                    width=2,
                    tags="aguja",
                )

            # Centro brillante
            self.canvas.create_oval(
                self.centro_x - 9,
                self.centro_y - 9,
                self.centro_x + 9,
                self.centro_y + 9,
                fill="#00ff88",
                outline="#003300",
                width=3,
                tags="aguja",
            )

    def _actualizar_grafica(self, cursor):
        """Actualiza la gráfica según el período y la métrica seleccionados"""
        seleccion = getattr(self, "periodo_grafica_var", None)
        filtro = seleccion.get() if seleccion else "Últimos 20 (En vivo)"

        seleccion_metrica = getattr(self, "metrica_grafica_var", None)
        metrica = seleccion_metrica.get() if seleccion_metrica else "Temperatura"

        # Mapear la selección de la interfaz a la columna de la BD
        columna = "temperatura"
        if metrica == "Presión":
            columna = "presion"
        elif metrica == "Humo":
            columna = "humo_mq2"

        if filtro == "Última hora":
            cursor.execute(
                f"SELECT {columna} as valor, fecha_hora FROM registro_sensores "
                "WHERE fecha_hora BETWEEN NOW() - INTERVAL 1 HOUR AND NOW() "
                "ORDER BY fecha_hora ASC LIMIT 500"
            )
            historico = cursor.fetchall()
        elif filtro == "Últimas 24 horas":
            cursor.execute(
                f"SELECT {columna} as valor, fecha_hora FROM registro_sensores "
                "WHERE fecha_hora BETWEEN NOW() - INTERVAL 1 DAY AND NOW() "
                "ORDER BY fecha_hora ASC LIMIT 500"
            )
            historico = cursor.fetchall()
        elif filtro == "Últimos 7 días":
            cursor.execute(
                f"SELECT {columna} as valor, fecha_hora FROM registro_sensores "
                "WHERE fecha_hora BETWEEN NOW() - INTERVAL 7 DAY AND NOW() "
                "ORDER BY fecha_hora ASC LIMIT 500"
            )
            historico = cursor.fetchall()
        else:
            cursor.execute(
                f"SELECT {columna} as valor, fecha_hora FROM registro_sensores "
                "ORDER BY id DESC LIMIT 20"
            )
            historico = cursor.fetchall()
            historico.reverse()

        if not historico:
            return

        indices = list(range(len(historico)))

        if filtro in ["Últimas 24 horas", "Últimos 7 días"]:
            etiquetas = [t["fecha_hora"].strftime("%d/%m %H:%M") for t in historico]
        else:
            etiquetas = [t["fecha_hora"].strftime("%H:%M:%S") for t in historico]

        valores = [t["valor"] for t in historico]

        self.ax.clear()

        # Cambio de color dinámico
        color_linea = "#ff4444"
        if metrica == "Presión":
            color_linea = "#4444ff"
        elif metrica == "Humo":
            color_linea = "#aaaaaa"

        self.ax.plot(
            indices, valores, marker="o", linewidth=2.5, color=color_linea, markersize=6
        )

        unidades = {"Temperatura": "°C", "Presión": "hPa", "Humo": "MQ2"}
        unidad = unidades.get(metrica, "")

        self.ax.set_title(
            f"Histórico de {metrica} ({unidad})",
            color="white",
            fontsize=14,
            pad=15,
            loc="left",
        )

        paso = max(1, len(indices) // 8)
        ticks_visibles = indices[::paso]
        labels_visibles = etiquetas[::paso]
        self.ax.set_xticks(ticks_visibles)
        self.ax.set_xticklabels(labels_visibles)

        self.ax.set_ylabel(f"{metrica} ({unidad})", color="#cccccc")
        self.ax.set_xlabel("Hora", color="#cccccc")

        self.ax.grid(True, alpha=0.3, color="#555555")
        self.ax.tick_params(colors="#cccccc", labelsize=9)
        self.ax.tick_params(axis="x", rotation=35)

        if valores:
            margen = (
                max(0.5, (max(valores) - min(valores)) * 0.15)
                if max(valores) != min(valores)
                else 0.5
            )
            self.ax.set_ylim(min(valores) - margen, max(valores) + margen)

        self.fig.tight_layout()
        self.canvas_plot.draw()

    def enviar_configuracion(self):
        """Envía configuración al ESP32"""
        try:
            datos = {
                "umbral_temp": float(self.entry_temp.get() or 35),
                "umbral_humo": float(self.entry_humo.get() or 550),
            }
            res = requests.post(f"{ESP32_IP}/api/config", json=datos, timeout=3)

            if res.status_code == 200:
                print("Configuración enviada correctamente al ESP32")
            else:
                print(f"Error al enviar configuración: {res.status_code}")
        except Exception as e:
            print(f"Error de conexión con ESP32: {e}")

    def _al_cerrar(self):
        """Cierre seguro"""
        self._activo = False
        if self._tarea_pendiente:
            self.after_cancel(self._tarea_pendiente)
        plt.close(self.fig)
        self.destroy()


if __name__ == "__main__":
    app = InterfazTorreta()
    app.mainloop()
