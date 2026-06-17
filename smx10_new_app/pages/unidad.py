import reflex as rx
from ..state import GlobalState, supabase
from .conductor import limpiar_texto, crear_bloque_carga_cond

# Opciones para el select de tipo de unidad
opciones_tipo = ["Sedan", "Small", "Large"]

class UnidadState(rx.State):
    # Datos de la Unidad
    numero_economico: str = ""
    placas: str = ""
    modelo: str = "2026"
    tipo_unidad: str = "" 
    
    # URLs de Documentos
    url_factura: str = ""
    url_tarjeta_circulacion: str = ""
    url_seguro: str = ""
    url_verificacion: str = ""

    # Setters
    def set_num_eco(self, t: str): self.numero_economico = t
    def set_placas(self, t: str): self.placas = t
    def set_modelo(self, t: str): self.modelo = t
    def set_tipo(self, t: str): self.tipo_unidad = t

    # Lógica de carga específica para Unidades
    async def procesar_archivo_unidad(self, files: list[rx.UploadFile], carpeta: str) -> str:
        if not self.numero_economico: return "ERROR_ID"
        for file in files:
            data = await file.read()
            nombre_limpio = limpiar_texto(file.filename)
            ruta = f"unidades/{self.numero_economico}/{carpeta}/{nombre_limpio}"
            try:
                supabase.storage.from_("documentos_operacion").upload(path=ruta, file=data, file_options={"upsert": "true"})
                return supabase.storage.from_("documentos_operacion").get_public_url(ruta)
            except Exception as e:
                print(f"Error subiendo {carpeta}: {e}")
                return ""
        return ""

    async def up_factura(self, files: list[rx.UploadFile]): self.url_factura = await self.procesar_archivo_unidad(files, "facturas")
    async def up_tarjeta(self, files: list[rx.UploadFile]): self.url_tarjeta_circulacion = await self.procesar_archivo_unidad(files, "tarjetas")
    async def up_seguro(self, files: list[rx.UploadFile]): self.url_seguro = await self.procesar_archivo_unidad(files, "seguros")
    async def up_verif(self, files: list[rx.UploadFile]): self.url_verificacion = await self.procesar_archivo_unidad(files, "verificaciones")

    def registrar_unidad(self):
        if not self.numero_economico or not self.placas:
            return rx.window_alert("El número económico y las placas son obligatorios.")
        
        datos = {
            "num_economico": self.numero_economico.upper(),
            "placas": self.placas.upper(),
            "modelo": self.modelo,
            "tipo_unidad": self.tipo_unidad,
            "url_factura": self.url_factura,
            "url_tarjeta": self.url_tarjeta_circulacion,
            "url_seguro": self.url_seguro,
            "url_verificacion": self.url_verificacion
        }
        try:
            supabase.table("alta_unidades").insert(datos).execute()
            return rx.window_alert("¡Unidad registrada correctamente!")
        except Exception as e:
            return rx.window_alert(f"Error al guardar: {str(e)}")

def unidad() -> rx.Component:
    estilo_input = {"& input::placeholder": {"color": "#666666", "opacity": "1"}}
    
    return rx.center(
        rx.vstack(
            rx.heading("🚛 Control de Unidades", size="7", color="#003366"),
            rx.card(
                rx.vstack(
                    rx.text("Detalles del Vehículo", font_weight="bold", color="black"),
                    rx.input(placeholder="No. Económico", on_change=UnidadState.set_num_eco, bg="white", color="black", border="1px solid #ccc", style=estilo_input),
                    rx.input(placeholder="Placas", on_change=UnidadState.set_placas, bg="white", color="black", border="1px solid #ccc", style=estilo_input),
                    rx.text("Modelo (Año) *", font_weight="bold", color="black", size="2"),
                    rx.input(
                        placeholder="2026",
                        min=2000,
                        max=2030,
                        value=UnidadState.modelo,
                        on_change=UnidadState.set_modelo,
                        width="100%",
                        bg="white",
                        color="black",
                        border="1px solid #ccc"
                    ),
                    
                    rx.text("Tipo de Unidad *", font_weight="bold", color="black", size="2"),
                    rx.select(
                        opciones_tipo,
                        placeholder="Selecciona una opción",
                        value=UnidadState.tipo_unidad,
                        on_change=UnidadState.set_tipo,
                        width="100%",
                        bg="white",
                        color="black",
                    ),
                    
                    rx.divider(),
                    rx.text("Documentación de Seguridad", font_weight="bold", color="black"),
                    rx.grid(
                        crear_bloque_carga_cond("Factura", "u1", UnidadState.up_factura, UnidadState.url_factura),
                        crear_bloque_carga_cond("Tarjeta Circulación", "u2", UnidadState.up_tarjeta, UnidadState.url_tarjeta_circulacion),
                        crear_bloque_carga_cond("Seguro", "u3", UnidadState.up_seguro, UnidadState.url_seguro),
                        crear_bloque_carga_cond("Verificación", "u4", UnidadState.up_verif, UnidadState.url_verificacion),
                        columns="2", spacing="4"
                    ),
                    rx.button("Registrar Unidad", on_click=UnidadState.registrar_unidad, bg="#0066cc", color="white", width="100%", margin_top="1em")
                ),
                width="600px", padding="2em", bg="white", box_shadow="lg"
            ),
            rx.link(rx.button("Volver al Panel", variant="outline", margin_top="1em", cursor="pointer"), href="/dashboard")
        ),
        padding="2em", bg="#f8f9fa", min_height="100vh"
    )