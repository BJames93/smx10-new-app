import reflex as rx
from datetime import datetime
from ..state import GlobalState, supabase

# Opciones fijas para la operación
opciones_cliente = ["Mercado Libre", "Amazon"]
opciones_estatus = ["En ruta", "Cancelacion", "No show"]

class OperacionesState(rx.State):
    # --- LISTAS DINÁMICAS DESDE LA BD ---
    lista_conductores: list[str] = []
    lista_unidades: list[str] = []

    # --- CAMPOS: CAPTURA DINÁMICA DE DESPACHO ---
    tipo_cliente: str = ""
    conductor_asignado: str = ""
    placas_vehiculo: str = ""
    estatus_servicio: str = "En ruta"
    realizo_ambulancia: bool = False
    es_costal: bool = False
    costo_ambulancia: str = "0.00"
    cantidad_paquetes: str = "0"
    paradas_planificadas: str = "0"

    # --- CAMPOS: TIEMPOS DE ESTANCIA EN HUB ---
    fecha_llegada_hub: str = datetime.now().strftime("%Y-%m-%d")
    fecha_salida_hub: str = datetime.now().strftime("%Y-%m-%d")
    hora_entrada_hub: str = "13:32"
    hora_despacho_hub: str = "13:32"

    # --- CAMPOS: REGISTRO DE DEVOLUCIONES ---
    dev_tipo_cliente: str = ""
    dev_conductor: str = ""
    dev_placas: str = ""
    dev_fecha: str = datetime.now().strftime("%Y-%m-%d")
    dev_paquetes_devueltos: str = "1"

    # --- SETTERS ---
    def set_tipo_cliente(self, val: str): self.tipo_cliente = val
    def set_conductor(self, val: str): self.conductor_asignado = val
    def set_placas(self, val: str): self.placas_vehiculo = val
    def set_estatus(self, val: str): self.estatus_servicio = val
    def set_realizo_ambulancia(self, val: bool): self.realizo_ambulancia = val
    def set_es_costal(self, val: bool): self.es_costal = val
    def set_costo_ambulancia(self, val: str): self.costo_ambulancia = val
    def set_cantidad_paquetes(self, val: str): self.cantidad_paquetes = val
    def set_paradas(self, val: str): self.paradas_planificadas = val
    
    def set_fecha_llegada(self, val: str): self.fecha_llegada_hub = val
    def set_fecha_salida(self, val: str): self.fecha_salida_hub = val
    def set_hora_entrada(self, val: str): self.hora_entrada_hub = val
    def set_hora_despacho(self, val: str): self.hora_despacho_hub = val

    def set_dev_cliente(self, val: str): self.dev_tipo_cliente = val
    def set_dev_conductor(self, val: str): self.dev_conductor = val
    def set_dev_placas(self, val: str): self.dev_placas = val
    def set_dev_fecha(self, val: str): self.dev_fecha = val
    def set_dev_paquetes(self, val: str): self.dev_paquetes_devueltos = val

    # --- CARGA INICIAL DE DATOS ---
    def cargar_listas_relacionales(self):
        """Carga los conductores y unidades exclusivos del usuario actual"""
        usuario_actual = GlobalState.usuario_id
        
        if not usuario_actual:
            return # Evita cargar datos si no hay sesión activa

        try:
            res_cond = supabase.table("alta_conductor").select("nombre_driver").eq("user_id", usuario_actual).execute()
            self.lista_conductores = [c["nombre_driver"] for c in res_cond.data] if res_cond.data else []

            res_uni = supabase.table("alta_unidades").select("placas").eq("user_id", usuario_actual).execute()
            self.lista_unidades = [u["placas"] for u in res_uni.data] if res_uni.data else []
        except Exception as e:
            print(f"Error al sincronizar catálogos relacionales: {e}")

    # --- ACCIONES DE BOTONES ---
    def registrar_despacho(self):
        if not self.tipo_cliente or not self.conductor_asignado or not self.placas_vehiculo:
            return rx.window_alert("⚠️ Por favor completa los campos obligatorios del Despacho (*).")
        
        datos = {
            # --- DATOS DEL DESPACHO ---
            "tipo_cliente": self.tipo_cliente,
            "conductor": self.conductor_asignado,
            "placas": self.placas_vehiculo,
            "estatus": self.estatus_servicio,
            "ambulancia": self.realizo_ambulancia,
            "es_costal": self.es_costal,
            "costo_ambulancia": float(self.costo_ambulancia) if self.costo_ambulancia else 0.0,
            "paquetes_cargados": int(self.cantidad_paquetes) if self.cantidad_paquetes else 0,
            "paradas_planificadas": int(self.paradas_planificadas) if self.paradas_planificadas else 0,
            
            # --- DATOS DE TIEMPOS EN HUB ---
            "fecha_llegada": self.fecha_llegada_hub,
            "fecha_salida": self.fecha_salida_hub,
            "hora_entrada": self.hora_entrada_hub,
            "hora_despacho": self.hora_despacho_hub,
            
            # --- SEGURIDAD MULTI-TENANT ---
            "user_id": GlobalState.usuario_id
        }
        
        try:
            # Asegúrate de que la tabla en Supabase se llame 'despacho_operativo' y tenga todas estas columnas
            supabase.table("despacho_operativo").insert(datos).execute() 
            return rx.window_alert("🚀 ¡Operación y Tiempos de Hub registrados exitosamente!")
        except Exception as e:
            return rx.window_alert(f"Error al guardar operación: {str(e)}")

    def registrar_devolucion(self):
        if not self.dev_tipo_cliente or not self.dev_conductor or not self.dev_placas:
            return rx.window_alert("⚠️ Por favor completa los campos obligatorios de la Devolución (*).")
        
        datos = {
            "tipo_cliente_dev": self.dev_tipo_cliente,
            "conductor_dev": self.dev_conductor,
            "placas_dev": self.dev_placas,
            "fecha_dev": self.dev_fecha,
            "paquetes_devueltos": int(self.dev_paquetes_devueltos) if self.dev_paquetes_devueltos else 0,
            "user_id": GlobalState.usuario_id
        }
        try:
            supabase.table("registro_devoluciones").insert(datos).execute()
            return rx.window_alert("📦 ¡Devolución registrada e integrada al inventario!")
        except Exception as e:
            return rx.window_alert(f"Error al registrar devolución: {str(e)}")

    def limpiar_tiempos_hub(self):
        self.hora_entrada_hub = "13:32"
        self.hora_despacho_hub = "13:32"


def operaciones() -> rx.Component:
    estilo_select = {"bg": "#222222", "color": "white", "border": "1px solid #444", "width": "100%"}
    estilo_input = {"bg": "#222222", "color": "white", "border": "1px solid #444", "width": "100%"}
    
    return rx.center(
        rx.vstack(
            # ==========================================
            # SECCIÓN 1: CAPTURA DINÁMICA DE DESPACHO
            # ==========================================
            rx.heading("📝 Captura Dinámica de Despacho Operativo", size="6", color="white", margin_top="1em"),
            rx.text("Módulo relacional. Permite enlazar los conductores y unidades activos en sistema.", color="#aaa", size="2"),
            
            rx.card(
                rx.grid(
                    # Columna Izquierda (Selectores y Checkboxes)
                    rx.vstack(
                        rx.text("Tipo de Cliente *", font_weight="bold", size="2"),
                        rx.select(opciones_cliente, placeholder="Seleccionar", value=OperacionesState.tipo_cliente, on_change=OperacionesState.set_tipo_cliente, **estilo_select),
                        
                        rx.text("Seleccione el Conductor asignado *", font_weight="bold", size="2"),
                        rx.select(OperacionesState.lista_conductores, placeholder="Seleccionar", value=OperacionesState.conductor_asignado, on_change=OperacionesState.set_conductor, **estilo_select),
                        
                        rx.text("Seleccione las Placas del Vehículo *", font_weight="bold", size="2"),
                        rx.select(OperacionesState.lista_unidades, placeholder="Seleccionar", value=OperacionesState.placas_vehiculo, on_change=OperacionesState.set_placas, **estilo_select),
                        
                        rx.text("Estatus del Servicio", font_weight="bold", size="2"),
                        rx.select(opciones_estatus, value=OperacionesState.estatus_servicio, on_change=OperacionesState.set_estatus, **estilo_select),
                        
                        rx.hstack(
                            rx.checkbox(checked=OperacionesState.realizo_ambulancia, on_change=OperacionesState.set_realizo_ambulancia),
                            rx.text("¿Realizó Ambulancia?", size="2"),
                            spacing="2", padding_y="0.3em"
                        ),
                        rx.hstack(
                            rx.checkbox(checked=OperacionesState.es_costal, on_change=OperacionesState.set_es_costal),
                            rx.text("¿Es Costal?", size="2"),
                            spacing="2", padding_y="0.3em"
                        ),
                        
                        rx.text("Costo Ambulancia ($)", font_weight="bold", size="2"),
                        rx.input(type="number", value=OperacionesState.costo_ambulancia, on_change=OperacionesState.set_costo_ambulancia, **estilo_input),
                        
                        align_items="start", spacing="2", width="100%"
                    ),
                    # Columna Derecha (Métricas numéricas fijas)
                    rx.vstack(
                        rx.text("Cantidad de Paquetes Cargados", font_weight="bold", size="2"),
                        rx.input(type="number", value=OperacionesState.cantidad_paquetes, on_change=OperacionesState.set_cantidad_paquetes, **estilo_input),
                        
                        rx.text("Número de Paradas Planificadas (Ruta)", font_weight="bold", size="2"),
                        rx.input(type="number", value=OperacionesState.paradas_planificadas, on_change=OperacionesState.set_paradas, **estilo_input),
                        
                        # EL BOTÓN DE GUARDAR DESPACHO SE ELIMINÓ DE AQUÍ PARA UNIFICARLO ABAJO
                        align_items="start", spacing="2", width="100%"
                    ),
                    columns="2", spacing="6", width="100%"
                ),
                bg="#111111", border="1px solid #222", padding="2em", width="100%"
            ),
            
            # ==========================================
            # SECCIÓN 2: TIEMPOS DE ESTANCIA EN HUB
            # ==========================================
            rx.heading("⏰ Tiempos de Estancia en Hub", size="6", color="white", margin_top="1.5em"),
            rx.card(
                rx.grid(
                    rx.vstack(
                        rx.text("Fecha de Llegada al Hub", font_weight="bold", size="2"),
                        rx.input(type="date", value=OperacionesState.fecha_llegada_hub, on_change=OperacionesState.set_fecha_llegada, **estilo_input),
                        
                        rx.text("Hora de Entrada (Hub)", font_weight="bold", size="2"),
                        rx.input(type="time", value=OperacionesState.hora_entrada_hub, on_change=OperacionesState.set_hora_entrada, **estilo_input),
                        align_items="start", spacing="2", width="100%"
                    ),
                    rx.vstack(
                        rx.text("Fecha de Salida del Hub", font_weight="bold", size="2"),
                        rx.input(type="date", value=OperacionesState.fecha_salida_hub, on_change=OperacionesState.set_fecha_salida, **estilo_input),
                        
                        rx.text("Hora de Despacho (Hub)", font_weight="bold", size="2"),
                        rx.input(type="time", value=OperacionesState.hora_despacho_hub, on_change=OperacionesState.set_hora_despacho, **estilo_input),
                        align_items="start", spacing="2", width="100%"
                    ),
                    columns="2", spacing="6", width="100%"
                ),
                rx.hstack(
                    rx.button("Limpiar Tiempos", on_click=OperacionesState.limpiar_tiempos_hub, variant="outline", size="2"),
                    # BOTÓN UNIFICADO QUE GUARDA TODO (DESPACHO Y HUB)
                    rx.button("🔒 Cerrar y Despachar Operación", on_click=OperacionesState.registrar_despacho, bg="#003366", color="white", size="2"),
                    margin_top="1.5em", spacing="3", justify="end", width="100%"
                ),
                bg="#111111", border="1px solid #222", padding="2em", width="100%"
            ),

            # ==========================================
            # SECCIÓN 3: REGISTRO DE DEVOLUCIONES
            # ==========================================
            rx.heading("📦 Registro de Devoluciones", size="6", color="white", margin_top="1.5em"),
            rx.text("Captura de paquetes retornados asociando la operación a un conductor y unidad.", color="#aaa", size="2"),
            
            rx.card(
                rx.grid(
                    rx.vstack(
                        rx.text("Tipo de Cliente (Devolución) *", font_weight="bold", size="2"),
                        rx.select(opciones_cliente, placeholder="Seleccionar", value=OperacionesState.dev_tipo_cliente, on_change=OperacionesState.set_dev_cliente, **estilo_select),
                        
                        rx.text("Conductor asignado *", font_weight="bold", size="2"),
                        rx.select(OperacionesState.lista_conductores, placeholder="Seleccionar", value=OperacionesState.dev_conductor, on_change=OperacionesState.set_dev_conductor, **estilo_select),
                        
                        rx.text("Placas del Vehículo *", font_weight="bold", size="2"),
                        rx.select(OperacionesState.lista_unidades, placeholder="Seleccionar", value=OperacionesState.dev_placas, on_change=OperacionesState.set_dev_placas, **estilo_select),
                        align_items="start", spacing="2", width="100%"
                    ),
                    rx.vstack(
                        rx.text("Fecha de Devolución *", font_weight="bold", size="2"),
                        rx.input(type="date", value=OperacionesState.dev_fecha, on_change=OperacionesState.set_dev_fecha, **estilo_input),
                        
                        rx.text("Cantidad de Paquetes Devueltos *", font_weight="bold", size="2"),
                        rx.input(type="number", value=OperacionesState.dev_paquetes_devueltos, on_change=OperacionesState.set_dev_paquetes, **estilo_input),
                        
                        rx.button("📥 Registrar Devolución", on_click=OperacionesState.registrar_devolucion, bg="#cc0000", color="white", width="100%", margin_top="4em"),
                        align_items="start", spacing="2", width="100%"
                    ),
                    columns="2", spacing="6", width="100%"
                ),
                bg="#111111", border="1px solid #222", padding="2em", width="100%"
            ),
            
            # Botón de Salida
            rx.link(
                rx.button("Volver al Panel Principal", variant="outline", margin_top="2em", margin_bottom="3em", cursor="pointer"), 
                href="/dashboard"
            ),
            width="1000px", spacing="3", align_items="start"
        ),
        bg="#0f0f0f", min_height="100vh", padding_x="2em", on_mount=OperacionesState.cargar_listas_relacionales
    )