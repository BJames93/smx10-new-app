import reflex as rx
import unicodedata
from ..state import GlobalState, supabase

def limpiar_texto(texto: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', texto)
    solo_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return solo_ascii.replace(" ", "_").replace("ñ", "n").replace("Ñ", "N")

class ConductorState(rx.State):
    # Variables de texto
    nombre_driver: str = ""
    rfc: str = ""
    correo: str = ""
    celular: str = ""
    nombre_banco: str = ""
    clabe_interbancaria: str = ""
    
    # Variables de URLs de documentos
    url_foto: str = ""
    url_ine: str = ""
    url_curp: str = ""
    url_lic: str = ""
    url_tox: str = ""
    url_fis: str = ""
    url_dom: str = ""
    url_ban: str = ""

    # Setters de texto
    def set_nombre_driver(self, t: str): self.nombre_driver = t
    def set_rfc(self, t: str): self.rfc = t
    def set_correo(self, t: str): self.correo = t
    def set_celular(self, t: str): self.celular = t
    def set_nombre_banco(self, t: str): self.nombre_banco = t
    def set_clabe_interbancaria(self, t: str): self.clabe_interbancaria = t

    # --- LÓGICA DE SUBIDA DE ARCHIVOS ---
    async def procesar_archivo(self, files: list[rx.UploadFile], carpeta: str) -> str:
        if not self.rfc:
            return "ERROR_RFC"
        
        for file in files:
            data = await file.read()
            nombre_limpio = limpiar_texto(file.filename)
            rfc_upper = self.rfc.upper()
            ruta = f"conductores/{carpeta}/{rfc_upper}_{nombre_limpio}"
            try:
                supabase.storage.from_("documentos_operacion").upload(
                    path=ruta, file=data, file_options={"content-type": file.content_type, "upsert": "true"}
                )
                return supabase.storage.from_("documentos_operacion").get_public_url(ruta)
            except Exception as e:
                print(f"Error subiendo {carpeta}: {e}")
                return ""
        return ""

    # Handlers específicos para cada botón de subida
    async def upload_foto(self, files: list[rx.UploadFile]):
        url = await self.procesar_archivo(files, "fotos")
        if url == "ERROR_RFC": return rx.window_alert("⚠️ Ingresa el RFC del conductor antes de subir archivos.")
        self.url_foto = url

    async def upload_ine(self, files: list[rx.UploadFile]):
        url = await self.procesar_archivo(files, "ines")
        if url == "ERROR_RFC": return rx.window_alert("⚠️ Ingresa el RFC del conductor antes de subir archivos.")
        self.url_ine = url

    async def upload_curp(self, files: list[rx.UploadFile]):
        url = await self.procesar_archivo(files, "curps")
        if url == "ERROR_RFC": return rx.window_alert("⚠️ Ingresa el RFC del conductor antes de subir archivos.")
        self.url_curp = url

    async def upload_lic(self, files: list[rx.UploadFile]):
        url = await self.procesar_archivo(files, "licencias")
        if url == "ERROR_RFC": return rx.window_alert("⚠️ Ingresa el RFC del conductor antes de subir archivos.")
        self.url_lic = url

    async def upload_tox(self, files: list[rx.UploadFile]):
        url = await self.procesar_archivo(files, "toxicologicos")
        if url == "ERROR_RFC": return rx.window_alert("⚠️ Ingresa el RFC del conductor antes de subir archivos.")
        self.url_tox = url

    async def upload_fis(self, files: list[rx.UploadFile]):
        url = await self.procesar_archivo(files, "fiscal")
        if url == "ERROR_RFC": return rx.window_alert("⚠️ Ingresa el RFC del conductor antes de subir archivos.")
        self.url_fis = url

    async def upload_dom(self, files: list[rx.UploadFile]):
        url = await self.procesar_archivo(files, "domicilios")
        if url == "ERROR_RFC": return rx.window_alert("⚠️ Ingresa el RFC del conductor antes de subir archivos.")
        self.url_dom = url

    async def upload_ban(self, files: list[rx.UploadFile]):
        url = await self.procesar_archivo(files, "bancos")
        if url == "ERROR_RFC": return rx.window_alert("⚠️ Ingresa el RFC del conductor antes de subir archivos.")
        self.url_ban = url

    def registrar_conductor(self):
        if not self.nombre_driver or not self.rfc:
            return rx.window_alert("Por favor completa los campos obligatorios (Nombre y RFC).")
        
        if len(self.rfc) < 13:
            return rx.window_alert(f"El RFC está incompleto. Ingresaste {len(self.rfc)} caracteres de los 13 requeridos.")
            
        if self.clabe_interbancaria and (len(self.clabe_interbancaria) != 18 or not self.clabe_interbancaria.isdigit()):
            return rx.window_alert("La CLABE Interbancaria debe tener exactamente 18 dígitos numéricos.")

        rfc_up = self.rfc.upper()
        banco_up = self.nombre_banco.upper() if self.nombre_banco else ""
        
        datos = {
            "nombre_driver": self.nombre_driver, 
            "rfc": rfc_up, 
            "correo": self.correo, 
            "celular": self.celular,
            "nombre_banco": banco_up,             
            "clabe_interbancaria": self.clabe_interbancaria,
            "creado_por": GlobalState.usuario_id if GlobalState.usuario_id else "Sistema",
            "url_fotografia": self.url_foto if self.url_foto else None,
            "url_curp": self.url_curp if self.url_curp else None,
            "url_ine": self.url_ine if self.url_ine else None,
            "url_constancia_fiscal": self.url_fis if self.url_fis else None,
            "url_licencia": self.url_lic if self.url_lic else None,
            "url_comprobante_domicilio": self.url_dom if self.url_dom else None,
            "url_caratula_bancaria": self.url_ban if self.url_ban else None,
            "url_toxicologico": self.url_tox if self.url_tox else None
        }
        
        try:
            supabase.table("alta_conductor").insert(datos).execute()
            
            # Limpiar formulario
            self.nombre_driver = self.rfc = self.correo = self.celular = ""
            self.nombre_banco = self.clabe_interbancaria = ""
            self.url_foto = self.url_ine = self.url_curp = self.url_lic = ""
            self.url_tox = self.url_fis = self.url_dom = self.url_ban = ""
            
            return rx.window_alert("¡Conductor registrado exitosamente con su expediente!")
        except Exception as e:
            return rx.window_alert(f"Error al guardar: {str(e)}")


def crear_bloque_carga_cond(label: str, upload_id: str, handler_subida, url_estado) -> rx.Component:
    return rx.vstack(
        rx.text(label, font_weight="bold", color="black", size="2"),
        rx.upload(
            rx.vstack(
                rx.button("Seleccionar", size="1", variant="outline", color_scheme="blue"),
                align_items="center", justify="center"
            ),
            id=upload_id, border="1px dashed #ccc", padding="0.5em", border_radius="md", width="100%", bg="#fafafa"
        ),
        rx.hstack(
            rx.button("Cargar", on_click=handler_subida(rx.upload_files(upload_id=upload_id)), size="1", bg="#003366", color="white"),
            rx.cond(url_estado, rx.text("✅ Listo", color="green", font_weight="bold", size="1"), rx.text("❌ Vacío", color="red", size="1")),
            spacing="3", align_items="center"
        ),
        width="100%", spacing="2"
    )

def conductor() -> rx.Component:
    estilo_input = {"& input::placeholder": {"color": "#666666", "opacity": "1"}}
    
    return rx.center(
        rx.vstack(
            rx.heading("🚗 Alta de Conductor", size="7", color="#003366"),
            rx.text("Captura los datos y el expediente digital del operador.", color="black"),
            
            rx.card(
                rx.vstack(
                    rx.text("📝 Datos Generales", size="4", font_weight="bold", color="#003366"),
                    
                    rx.grid(
                        rx.vstack(
                            rx.text("Nombre Completo *", font_weight="bold", color="black", size="2"),
                            rx.input(placeholder="Nombre del conductor", value=ConductorState.nombre_driver, on_change=ConductorState.set_nombre_driver, width="100%", bg="white", color="black", border="1px solid #ccc", style=estilo_input),
                        ),
                        rx.vstack(
                            rx.text("RFC *", font_weight="bold", color="black", size="2"),
                            rx.input(placeholder="13 caracteres", value=ConductorState.rfc, on_change=ConductorState.set_rfc, max_length=13, width="100%", bg="white", color="black", border="1px solid #ccc", style=estilo_input),
                        ),
                        rx.vstack(
                            rx.text("Correo", font_weight="bold", color="black", size="2"),
                            rx.input(placeholder="correo@ejemplo.com", value=ConductorState.correo, on_change=ConductorState.set_correo, width="100%", bg="white", color="black", border="1px solid #ccc", style=estilo_input),
                        ),
                        rx.vstack(
                            rx.text("Celular", font_weight="bold", color="black", size="2"),
                            rx.input(placeholder="10 dígitos", value=ConductorState.celular, on_change=ConductorState.set_celular, width="100%", bg="white", color="black", border="1px solid #ccc", style=estilo_input),
                        ),
                        rx.vstack(
                            rx.text("Banco", font_weight="bold", color="black", size="2"),
                            rx.input(placeholder="MAYÚSCULAS", value=ConductorState.nombre_banco, on_change=ConductorState.set_nombre_banco, width="100%", bg="white", color="black", border="1px solid #ccc", style=estilo_input),
                        ),
                        rx.vstack(
                            rx.text("CLABE Interbancaria", font_weight="bold", color="black", size="2"),
                            rx.input(placeholder="18 dígitos numéricos", value=ConductorState.clabe_interbancaria, on_change=ConductorState.set_clabe_interbancaria, max_length=18, width="100%", bg="white", color="black", border="1px solid #ccc", style=estilo_input),
                        ),
                        columns="2", spacing="4", width="100%"
                    ),
                    
                    rx.divider(margin_y="1em"),
                    rx.text("📁 Expediente Digital", size="4", font_weight="bold", color="#003366"),
                    
                    rx.grid(
                        crear_bloque_carga_cond("Foto de Perfil", "upload_foto", ConductorState.upload_foto, ConductorState.url_foto),
                        crear_bloque_carga_cond("INE", "upload_ine", ConductorState.upload_ine, ConductorState.url_ine),
                        crear_bloque_carga_cond("CURP", "upload_curp", ConductorState.upload_curp, ConductorState.url_curp),
                        crear_bloque_carga_cond("Licencia", "upload_lic", ConductorState.upload_lic, ConductorState.url_lic),
                        crear_bloque_carga_cond("Toxicológico", "upload_tox", ConductorState.upload_tox, ConductorState.url_tox),
                        crear_bloque_carga_cond("Constancia Fiscal", "upload_fis", ConductorState.upload_fis, ConductorState.url_fis),
                        crear_bloque_carga_cond("Comprobante Domicilio", "upload_dom", ConductorState.upload_dom, ConductorState.url_dom),
                        crear_bloque_carga_cond("Carátula Bancaria", "upload_ban", ConductorState.upload_ban, ConductorState.url_ban),
                        columns="4", spacing="4", width="100%"
                    ),
                    
                    rx.button(
                        "Guardar Conductor", on_click=ConductorState.registrar_conductor,
                        bg="#008000", color="white", width="100%", margin_top="2em", size="3"
                    ),
                    align_items="start", spacing="3",
                ),
                width="900px", # Más ancho para que quepan 4 columnas de archivos
                padding="2.5em", bg="white", box_shadow="lg" 
            ),
            
            rx.link(rx.button("Volver al Panel Principal", variant="outline", margin_top="1em", cursor="pointer"), href="/dashboard"),
            align_items="center", spacing="4",
        ),
        bg="#f8f9fa", min_height="100vh", padding="2em",
    )