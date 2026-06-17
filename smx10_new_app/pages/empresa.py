import reflex as rx
import unicodedata
from ..state import GlobalState, supabase

# --- FUNCION AUXILIAR PARA LIMPIAR NOMBRES DE ARCHIVOS ---
def limpiar_texto(texto: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', texto)
    solo_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return solo_ascii.replace(" ", "_").replace("ñ", "n").replace("Ñ", "N")

class EmpresaState(rx.State):
    # Variables de texto
    nombre_empresa: str = ""
    rfc_empresa: str = ""
    nombre_rl: str = ""
    banco_empresa: str = "" # 
    clabe_empresa: str = ""


    # Variables para almacenar las URLs públicas de los documentos
    url_ine: str = ""
    url_csf: str = ""
    url_cb: str = ""
    url_dom: str = ""

    # Setters explícitos obligatorios
    def set_nombre_empresa(self, texto: str):
        self.nombre_empresa = texto

    def set_rfc_empresa(self, texto: str):
        self.rfc_empresa = texto

    def set_nombre_rl(self, texto: str):
        self.nombre_rl = texto

    def set_banco_empresa(self, texto: str): # <-- NUEVA
        self.banco_empresa = texto

    def set_clabe_empresa(self, texto: str): # <-- NUEVA
        self.clabe_empresa = texto

    # --- LÓGICA DE SUBIDA DE ARCHIVOS A SUPABASE STORAGE ---
    async def upload_ine(self, files: list[rx.UploadFile]):
        if not self.nombre_empresa:
            return rx.window_alert("⚠️ Por favor ingresa primero el Nombre de la Empresa.")
        for file in files:
            data = await file.read()
            nombre_limpio = limpiar_texto(file.filename)
            empresa_upper = self.nombre_empresa.upper()
            ruta = f"empresas/ines/{empresa_upper}_{nombre_limpio}"
            try:
                supabase.storage.from_("documentos_operacion").upload(
                    path=ruta, file=data, file_options={"content-type": file.content_type, "upsert": "true"}
                )
                self.url_ine = supabase.storage.from_("documentos_operacion").get_public_url(ruta)
            except Exception as e:
                return rx.window_alert(f"Error al subir INE: {str(e)}")

    async def upload_csf(self, files: list[rx.UploadFile]):
        if not self.nombre_empresa:
            return rx.window_alert("⚠️ Por favor ingresa primero el Nombre de la Empresa.")
        for file in files:
            data = await file.read()
            nombre_limpio = limpiar_texto(file.filename)
            empresa_upper = self.nombre_empresa.upper()
            ruta = f"empresas/fiscal/{empresa_upper}_{nombre_limpio}"
            try:
                supabase.storage.from_("documentos_operacion").upload(
                    path=ruta, file=data, file_options={"content-type": file.content_type, "upsert": "true"}
                )
                self.url_csf = supabase.storage.from_("documentos_operacion").get_public_url(ruta)
            except Exception as e:
                return rx.window_alert(f"Error al subir Constancia Fiscal: {str(e)}")

    async def upload_cb(self, files: list[rx.UploadFile]):
        if not self.nombre_empresa:
            return rx.window_alert("⚠️ Por favor ingresa primero el Nombre de la Empresa.")
        for file in files:
            data = await file.read()
            nombre_limpio = limpiar_texto(file.filename)
            empresa_upper = self.nombre_empresa.upper()
            ruta = f"empresas/bancos/{empresa_upper}_{nombre_limpio}"
            try:
                supabase.storage.from_("documentos_operacion").upload(
                    path=ruta, file=data, file_options={"content-type": file.content_type, "upsert": "true"}
                )
                self.url_cb = supabase.storage.from_("documentos_operacion").get_public_url(ruta)
            except Exception as e:
                return rx.window_alert(f"Error al subir Carátula Bancaria: {str(e)}")

    async def upload_dom(self, files: list[rx.UploadFile]):
        if not self.nombre_empresa:
            return rx.window_alert("⚠️ Por favor ingresa primero el Nombre de la Empresa.")
        for file in files:
            data = await file.read()
            nombre_limpio = limpiar_texto(file.filename)
            empresa_upper = self.nombre_empresa.upper()
            ruta = f"empresas/domicilios/{empresa_upper}_{nombre_limpio}"
            try:
                supabase.storage.from_("documentos_operacion").upload(
                    path=ruta, file=data, file_options={"content-type": file.content_type, "upsert": "true"}
                )
                self.url_dom = supabase.storage.from_("documentos_operacion").get_public_url(ruta)
            except Exception as e:
                return rx.window_alert(f"Error al subir Comprobante de Domicilio: {str(e)}")

    def registrar_empresa(self):
        # Validaciones
        if not self.nombre_empresa or not self.rfc_empresa or not self.nombre_rl or not self.banco_empresa or not self.clabe_empresa:
            return rx.window_alert("Por favor completa todos los campos de texto.")
        
        if len(self.rfc_empresa) < 12:
            return rx.window_alert(f"El RFC está incompleto. Ingresaste {len(self.rfc_empresa)} caracteres.")

        if len(self.clabe_empresa) != 18 or not self.clabe_empresa.isdigit():
            return rx.window_alert("La CLABE debe tener exactamente 18 dígitos numéricos.")
        
        # Preparación de datos (forzando MAYÚSCULAS)
        empresa_upper = self.nombre_empresa.upper()
        rfc_upper = self.rfc_empresa.upper()
        banco_upper = self.banco_empresa.upper() # <-- Banco en mayúsculas
        

        datos_empresa = {
            "nombre_empresa": empresa_upper,
            "rfc_empresa": rfc_upper,  
            "nombre_rl": self.nombre_rl,
            "banco_empresa": banco_upper,       # <-- Enviamos el banco
            "clabe_empresa": self.clabe_empresa, # <-- Enviamos la CLABE
            "user_id": GlobalState.usuario_id,
            "creado_por": GlobalState.usuario_id if GlobalState.usuario_id else "Sistema",
            "url_ine_rl": self.url_ine if self.url_ine else None,
            "url_constancia_fiscal": self.url_csf if self.url_csf else None,
            "url_caratula_bancaria": self.url_cb if self.url_cb else None,
            "url_comprobante_domicilio": self.url_dom if self.url_dom else None
        }
        
        try:
            supabase.table("registro_empresa").insert(datos_empresa).execute()
            
            # Limpiamos todo tras el éxito
            self.nombre_empresa = ""
            self.rfc_empresa = ""
            self.nombre_rl = ""
            self.banco_empresa = "" # <-- Limpiamos
            self.clabe_empresa = "" # <-- Limpiamos
            self.url_ine = ""
            self.url_csf = ""
            self.url_cb = ""
            self.url_dom = ""
            
            return rx.window_alert(f"¡Empresa {empresa_upper} registrada exitosamente junto con su expediente!")
        except Exception as e:
            return rx.window_alert(f"Error al guardar en Base de Datos: {str(e)}")

def crear_bloque_carga(label: str, upload_id: str, handler_subida, url_estado) -> rx.Component:
    """Función auxiliar para generar cajas de subida limpias y uniformes"""
    return rx.vstack(
        rx.text(label, font_weight="bold", color="black", size="2"),
        rx.upload(
            rx.vstack(
                rx.button("Seleccionar", size="1", variant="outline", color_scheme="blue"),
                rx.text("o arrastra el archivo aquí", size="1", color="gray"),
                align_items="center",
                spacing="1"
            ),
            id=upload_id,
            border="1px dashed #ccc",
            padding="0.8em",
            border_radius="md",
            width="100%",
            bg="#fafafa"
        ),
        rx.hstack(
            rx.button("Cargar", on_click=handler_subida(rx.upload_files(upload_id=upload_id)), size="1", bg="#003366", color="white"),
            rx.cond(
                url_estado,
                rx.text("✅ Cargado", color="green", font_weight="bold", size="2"),
                rx.text("❌ Sin archivo", color="red", size="1")
            ),
            spacing="3",
            align_items="center"
        ),
        width="100%",
        spacing="2"
    )


def empresa() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("🏢 Alta y Registro de Empresa", size="7", color="#003366"),
            rx.text("Introduce los datos correspondientes y su expediente digital para el alta en el sistema.", color="black"),
            
            rx.card(
                rx.vstack(
                    rx.text("📝 Datos Generales", size="4", font_weight="bold", color="#003366", margin_bottom="0.5em"),
                    
                    rx.text("Nombre de la empresa *", font_weight="bold", color="black", size="2"),
                    rx.input(
                        placeholder="Se guardará en MAYÚSCULAS", 
                        value=EmpresaState.nombre_empresa,
                        on_change=EmpresaState.set_nombre_empresa, 
                        width="100%", bg="white", color="black", border="1px solid #ccc", 
                        style={"& input::placeholder": {"color": "#666666", "opacity": "1"}} # <-- Ataque directo al input
                    ),
                    
                    rx.text("RFC de la Empresa *", font_weight="bold", color="black", size="2"),
                    rx.input(
                        placeholder="Máximo 18 caracteres", 
                        value=EmpresaState.rfc_empresa,
                        on_change=EmpresaState.set_rfc_empresa, 
                        max_length=18, width="100%", bg="white", color="black", border="1px solid #ccc", 
                        style={"& input::placeholder": {"color": "#666666", "opacity": "1"}}
                    ),
                    
                    rx.text("Nombre del Representante Legal (RL) *", font_weight="bold", color="black", size="2"),
                    rx.input(
                        placeholder="Nombre Completo", 
                        value=EmpresaState.nombre_rl,
                        on_change=EmpresaState.set_nombre_rl, 
                        width="100%", bg="white", color="black", border="1px solid #ccc", 
                        style={"& input::placeholder": {"color": "#666666", "opacity": "1"}}
                    ),

                    rx.text("Banco de la Empresa *", font_weight="bold", color="black", size="2"),
                    rx.input(
                        placeholder="Se guardará en MAYÚSCULAS", 
                        value=EmpresaState.banco_empresa,
                        on_change=EmpresaState.set_banco_empresa, 
                        width="100%", bg="white", color="black", border="1px solid #ccc", 
                        style={"& input::placeholder": {"color": "#666666", "opacity": "1"}}
                    ),
                    
                    rx.text("Cuenta CLABE *", font_weight="bold", color="black", size="2"),
                    rx.input(
                        placeholder="18 dígitos numéricos", 
                        value=EmpresaState.clabe_empresa,
                        on_change=EmpresaState.set_clabe_empresa, 
                        max_length=18, width="100%", bg="white", color="black", border="1px solid #ccc", 
                        style={"& input::placeholder": {"color": "#666666", "opacity": "1"}}
                    ),

                    rx.divider(margin_y="1em"),
                    rx.text("📁 Expediente de la Empresa", size="4", font_weight="bold", color="#003366", margin_bottom="0.5em"),
                    
                    # Cuadrícula distribuidora de los 4 archivos (2 columnas)
                    rx.grid(
                        crear_bloque_carga("INE del Representante Legal", "upload_ine", EmpresaState.upload_ine, EmpresaState.url_ine),
                        crear_bloque_carga("Constancia de Situación Fiscal", "upload_csf", EmpresaState.upload_csf, EmpresaState.url_csf),
                        crear_bloque_carga("Carátula Bancaria", "upload_cb", EmpresaState.upload_cb, EmpresaState.url_cb),
                        crear_bloque_carga("Comprobante de Domicilio", "upload_dom", EmpresaState.upload_dom, EmpresaState.url_dom),
                        columns="2",
                        spacing="4",
                        width="100%"
                    ),
                    
                    rx.button(
                        "Registrar Empresa Completa", on_click=EmpresaState.registrar_empresa,
                        bg="#008000", color="white", width="100%", margin_top="2em", size="3"
                    ),
                    align_items="start",
                    spacing="3",
                ),
                width="650px", # Lo hacemos un poco más ancho para acomodar la cuadrícula de archivos
                padding="2.5em",
                bg="white", 
                box_shadow="lg" 
            ),
            
            rx.link(
                rx.button("Volver al Panel Principal", variant="outline", margin_top="1em", cursor="pointer"),
                href="/dashboard"
            ),
        ),
        bg="#f8f9fa",
        min_height="100vh",
        padding="2em",
    )