import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
import unicodedata 
import io
import zipfile
import requests

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
SUPABASE_URL = "https://sinepuhjujazcaelrqms.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNpbmVwdWhqdWphemNhZWxycW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAzOTgwMDIsImV4cCI6MjA5NTk3NDAwMn0.RoTKaHzfbFViuiNOgMirfws0Pd13nCivAhxDoq_ipJM"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "documentos_operacion_smx10"

# --- LÓGICA DE LOGIN CON SUPABASE ---
def check_password():
    def password_entered():
        input_user = st.session_state["username"].strip()
        input_pass = st.session_state["password"].strip()
        
        try:
            res = supabase.table("usuarios_acceso").select("*").eq("nombre_usuario", input_user).eq("contrasena", input_pass).execute()
            
            if len(res.data) > 0:
                st.session_state["password_correct"] = True
                st.session_state["usuario_actual"] = res.data[0] 
                del st.session_state["password"]  
            else:
                st.session_state["password_correct"] = False
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password", on_change=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Usuario", key="username")
        st.text_input("Contraseña", type="password", key="password", on_change=password_entered)
        st.error("❌ Usuario o contraseña incorrectos")
        return False
    else:
        return True

# Bloque de seguridad: Si no hay login, se detiene la app
if not check_password():
    st.stop()

# --- FUNCIONES DE APOYO ---
def limpiar_texto(texto):
    nfkd_form = unicodedata.normalize('NFKD', texto)
    solo_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return solo_ascii.replace(" ", "_").replace("ñ", "n").replace("Ñ", "N")

def procesar_archivo(archivo, carpeta, identificador):
    if archivo is not None:
        try:
            nombre_limpio = limpiar_texto(archivo.name)
            carpeta_limpia = limpiar_texto(carpeta)
            ruta = f"{carpeta_limpia}/{identificador}_{nombre_limpio}"
            supabase.storage.from_(BUCKET_NAME).upload(
                path=ruta, 
                file=archivo.getvalue(), 
                file_options={"content-type": archivo.type, "upsert": "true"}
            )
            return supabase.storage.from_(BUCKET_NAME).get_public_url(ruta)
        except Exception as e:
            st.error(f"Error en {archivo.name}: {e}")
            return None
    return None

# --- IDENTIFICADOR DEL USUARIO ACTIVO ---
usuario_id_activo = st.session_state["usuario_actual"]["user_id"]
nombre_usuario_activo = st.session_state["usuario_actual"]["nombre_usuario"]

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Plataforma BoulderBrwn", page_icon="🚀", layout="wide")

# --- OCULTAR ELEMENTOS DE LA INTERFAZ DE STREAMLIT ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stDeployButton {display: none;}
            .viewerBadge_container {display: none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Mensaje lateral de bienvenida
st.sidebar.success(f"👤 Conectado como: **{nombre_usuario_activo}**")

st.title("📊 Sistema Centralizado de Proveedores")

# Reordenamiento de Tabs de acuerdo a la declaración oficial
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏢 Registro de Empresa", "🚗 Alta Conductor", "🚛 Control de Unidades", 
    "🔍 Consulta Integral", "🔄 Actualización de Expedientes", 
    "📋 Registro de Operaciones", "📊 Verificación de Captura"
])

# ==========================================
# PESTAÑA 1: REGISTRO DE EMPRESA
# ==========================================
with tab1:
    st.header("🏢 Alta y Registro de Empresa")
    with st.form("form_empresa", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre_empresa = st.text_input("Nombre de la empresa (Se guardará en MAYÚSCULAS) *")
            rfc_empresa = st.text_input("RFC de la Empresa *", max_chars=13, help="El RFC debe tener exactamente 13 caracteres.")
        with col2:
            nombre_rl = st.text_input("Nombre del Representante Legal (RL) (Se guardará en MAYÚSCULAS) *")

        st.subheader("🏦 Datos Bancarios")
        c_bank1, c_bank2 = st.columns(2)
        with c_bank1:
            banco_empresa = st.text_input("Banco (Se guardará en MAYÚSCULAS) *")
        with c_bank2:
            clabe_empresa = st.text_input("Cuenta CLABE *", max_chars=18, help="La CLABE debe tener exactamente 18 caracteres numéricos.")

        st.subheader("📁 Expediente de la Empresa")
        c1, c2 = st.columns(2)
        with c1:
            f_ine_rl = st.file_uploader("Cargar INE del RL")
            f_csf = st.file_uploader("Cargar Constancia de Situación Fiscal")
        with c2:
            f_cb = st.file_uploader("Cargar Carátula Bancaria")
            f_dom_empresa = st.file_uploader("Cargar Comprobante de Domicilio")
            
        enviar_empresa = st.form_submit_button("Registrar Empresa")
        
        if enviar_empresa:
            if not nombre_empresa or not nombre_rl or not rfc_empresa or not banco_empresa or not clabe_empresa:
                st.error("Por favor completa los campos obligatorios (Nombre, RFC, Representante Legal, Banco y CLABE).")
            elif len(rfc_empresa) < 13:
                st.error(f"El RFC está incompleto. Ingresaste {len(rfc_empresa)} caracteres de los 13 requeridos.")
            elif len(clabe_empresa) < 18:
                st.error(f"La CLABE está incompleta. Ingresaste {len(clabe_empresa)} caracteres de los 18 requeridos.")
            elif not clabe_empresa.isdigit():
                st.error("La CLABE solo debe contener números, sin letras ni espacios.")
            else:
                empresa_upper = nombre_empresa.upper()
                rfc_upper = rfc_empresa.upper()
                rl_upper = nombre_rl.upper()
                banco_upper = banco_empresa.upper()
                
                url_ine = procesar_archivo(f_ine_rl, "empresas/ines", empresa_upper)
                url_csf = procesar_archivo(f_csf, "empresas/fiscal", empresa_upper)
                url_cb = procesar_archivo(f_cb, "empresas/bancos", empresa_upper)
                url_dom = procesar_archivo(f_dom_empresa, "empresas/domicilios", empresa_upper)
                
                datos_empresa = {
                    "nombre_empresa": empresa_upper,
                    "RFC": rfc_upper,  
                    "nombre_rl": rl_upper,
                    "banco_empresa": banco_upper,
                    "clabe_empresa": clabe_empresa,
                    "creado_por": usuario_id_activo,
                    "url_ine_rl": url_ine,
                    "url_constancia_fiscal": url_csf,
                    "url_caratula_bancaria": url_cb,
                    "url_comprobante_domicilio": url_dom
                }
                
                try:
                    supabase.table("registro_empresa").insert(datos_empresa).execute()
                    st.success(f"¡Empresa {empresa_upper} registrada exitosamente!")
                except Exception as e:
                    st.error(f"Error al registrar la empresa: {e}")
# ==========================================
# PESTAÑA 2: ALTA DE CONDUCTOR
# ==========================================
with tab2:
    with st.form("form_conductor", clear_on_submit=True):
        st.subheader("📝 Datos Generales")
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo *")
            rfc = st.text_input("RFC *", max_chars=13, help="El RFC para personas físicas debe tener exactamente 13 caracteres.")
            correo = st.text_input("Correo")
        with col2:
            celular = st.text_input("Celular")
            banco = st.text_input("Nombre Banco")
            clabe = st.text_input("Clabe Interbancaria", max_chars=18, help="La CLABE debe tener exactamente 18 dígitos numéricos.")
        
        st.divider() 
        st.subheader("📁 Expediente Digital")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("**Identidad**")
            f_foto = st.file_uploader("Foto (Mercado Libre)")
            f_ine = st.file_uploader("INE (Mercado Libre)")
            f_curp = st.file_uploader("CURP (Mercado Libre)")
            
        with c2:
            st.markdown("**Operación y Control**")
            f_lic = st.file_uploader("Licencia (Mercado Libre)")
            f_tox = st.file_uploader("Toxicológico")
            f_ref = st.file_uploader("Carta de Referencia")
            
        with c3:
            st.markdown("**Fiscal y Bancario**")
            f_fis = st.file_uploader("Constancia Fiscal")
            f_dom = st.file_uploader("Comprobante de Domicilio (Mercado Libre)")
            f_ban = st.file_uploader("Banco (Archivo)") 
        
        st.divider()
        enviar = st.form_submit_button("Guardar Conductor")
        
        if enviar:
            if not nombre or not rfc:
                st.error("Por favor completa los campos obligatorios (Nombre y RFC)")
            elif len(rfc) < 13:
                st.error(f"El RFC está incompleto. Ingresaste {len(rfc)} caracteres de los 13 requeridos.")
            elif clabe and len(clabe) < 18:
                st.error(f"La CLABE Interbancaria está incompleta. Ingresaste {len(clabe)} dígitos de los 18 requeridos.")
            elif clabe and not clabe.isdigit():
                st.error("La CLABE Interbancaria solo debe contener caracteres numéricos (números del 0 al 9).")
            else:
                rfc_up = rfc.upper()
                u_foto = procesar_archivo(f_foto, "conductores/fotos", rfc_up)
                u_curp = procesar_archivo(f_curp, "conductores/curps", rfc_up)
                u_ine = procesar_archivo(f_ine, "conductores/ines", rfc_up)
                u_fis = procesar_archivo(f_fis, "conductores/fiscal", rfc_up)
                u_lic = procesar_archivo(f_lic, "conductores/licencias", rfc_up)
                u_dom = procesar_archivo(f_dom, "conductores/domicilios", rfc_up)
                u_ban = procesar_archivo(f_ban, "conductores/bancos", rfc_up)
                u_tox = procesar_archivo(f_tox, "conductores/toxicologicos", rfc_up)
                
                datos = {
                    "nombre_driver": nombre, 
                    "rfc": rfc_up, 
                    "correo": correo, 
                    "celular": celular,
                    "nombre_banco": banco,             
                    "clabe_interbancaria": clabe,
                    "creado_por": usuario_id_activo,
                    "url_fotografia": u_foto,
                    "url_curp": u_curp,
                    "url_ine": u_ine,
                    "url_constancia_fiscal": u_fis,
                    "url_licencia": u_lic,
                    "url_comprobante_domicilio": u_dom,
                    "url_caratula_bancaria": u_ban,
                    "url_toxicologico": u_tox
                }
                try:
                    supabase.table("alta_conductor").insert(datos).execute()
                    st.success("Conductor registrado exitosamente")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# ==========================================
# PESTAÑA 3: UNIDADES
# ==========================================
with tab3:
    with st.form("form_unidades", clear_on_submit=True):
        p = st.text_input("Placas")
        m = st.text_input("Marca")
        sm = st.text_input("Submarca")
        
        tipo = st.selectbox("Tipo de Unidad", ["Sedan", "Small", "Large"])
        mod = st.number_input("Modelo", 1990, 2030, 2026)
        
        f_circ = st.file_uploader("Tarjeta Circulación (Mercado Libre)")
        f_seg = st.file_uploader("Seguro (Mercado Libre)")
        f_vin = st.file_uploader("Fotografía VIN")
        f_plac = st.file_uploader("Fotografía Placas")
        
        enviar_u = st.form_submit_button("Registrar Unidad")
        if enviar_u:
            if not p:
                st.error("Las placas son obligatorias.")
            else:
                placas_up = p.upper()
                u_circ = procesar_archivo(f_circ, "unidades/tarjetas", placas_up)
                u_seg = procesar_archivo(f_seg, "unidades/polizas", placas_up)
                u_vin = procesar_archivo(f_vin, "unidades/vin", placas_up)
                u_plac = procesar_archivo(f_plac, "unidades/placas", placas_up)
                
                datos_u = {
                    "placas": placas_up, 
                    "modelo": int(mod), 
                    "marca": m, 
                    "submarca": sm,
                    "tipo_unidad": tipo,
                    "creado_por": usuario_id_activo,
                    "url_tarjeta_circulacion": u_circ,
                    "url_poliza_seguro": u_seg,
                    "url_vin": u_vin,
                    "url_placa": u_plac
                }
                try:
                    supabase.table("unidades").insert(datos_u).execute()
                    st.success("Unidad registrada exitosamente")
                except Exception as e:
                    st.error(f"Error al registrar la unidad: {e}")

# ==========================================
# PESTAÑA 4: CONSULTA DE EXPEDIENTES
# ==========================================
with tab4:
    st.header("🔍 Consulta Integral de Expedientes")
    tipo_consulta = st.radio("¿Qué desea consultar?", ["Conductores", "Unidades"], horizontal=True)
    
    def generar_zip(diccionario_documentos):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for nombre, url in diccionario_documentos.items():
                try:
                    respuesta = requests.get(url)
                    if respuesta.status_code == 200:
                        ext = url.split('.')[-1]
                        if len(ext) > 4 or not ext.isalnum():
                            ext = "pdf"
                        zip_file.writestr(f"{nombre}.{ext}", respuesta.content)
                except Exception:
                    pass
        return zip_buffer.getvalue()

    if tipo_consulta == "Conductores":
        try:
            res = supabase.table("alta_conductor").select("*").eq("creado_por", usuario_id_activo).execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                df['nombre_driver'] = df['nombre_driver'].fillna("").astype(str)
                lista_conductores = [""] + df['nombre_driver'].tolist()
                sel = st.selectbox("Seleccione Conductor:", options=lista_conductores)
                
                if sel:
                    fila = df[df['nombre_driver'] == sel]
                    if not fila.empty:
                        reg = fila.iloc[0].to_dict()
                        st.subheader(f"Expediente de: {sel}")
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.write(f"**RFC:** {reg.get('rfc', 'N/A')}")
                            st.write(f"**Correo:** {reg.get('correo', 'N/A')}")
                            st.write(f"**Celular:** {reg.get('celular', 'N/A')}")
                            st.write(f"**Banco:** {reg.get('nombre_banco', 'N/A') or 'N/A'}")
                            st.write(f"**CLABE:** {reg.get('clabe_interbancaria', 'N/A') or 'N/A'}")
                            
                            foto = reg.get('url_fotografia')
                            if foto and isinstance(foto, str):
                                st.image(foto, width=200, caption="Foto de Perfil")
                        with c2:
                            st.write("### Documentación Digital")
                            
                            docs = {}
                            docs["CURP"] = "url_curp"
                            docs["INE"] = "url_ine"
                            docs["Constancia Fiscal"] = "url_constancia_fiscal"
                            docs["Licencia de Conducir"] = "url_licencia"
                            docs["Comprobante Domicilio"] = "url_comprobante_domicilio"
                            docs["Caratula Bancaria"] = "url_caratula_bancaria"
                            docs["Examen Toxicologico"] = "url_toxicologico"
                            
                            documentos_validos = {}
                            for nombre, key in docs.items():
                                url = reg.get(key)
                                if url and isinstance(url, str) and url.startswith("http"):
                                    st.link_button(f"📄 Ver {nombre}", url)
                                    documentos_validos[nombre] = url
                                else:
                                    st.caption(f"❌ {nombre}: No cargado")
                            
                            if documentos_validos:
                                st.write("---")
                                st.download_button(
                                    label="📦 Descargar Expediente en ZIP",
                                    data=generar_zip(documentos_validos),
                                    file_name=f"Expediente_{sel.replace(' ', '_')}.zip",
                                    mime="application/zip"
                                )
            else:
                st.info("No tienes conductores registrados en tu cuenta.")
        except Exception as e:
            st.error(f"Error cargando conductores: {e}")

    else:
        try:
            res = supabase.table("unidades").select("*").eq("creado_por", usuario_id_activo).execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                df['placas'] = df['placas'].fillna("").astype(str)
                lista_placas = [""] + df['placas'].tolist()
                sel = st.selectbox("Seleccione Placas de la Unidad:", options=lista_placas)
                
                if sel:
                    fila = df[df['placas'] == sel]
                    if not fila.empty:
                        reg = fila.iloc[0].to_dict()
                        st.subheader(f"Unidad Placas: {sel}")
                        st.write(f"**Marca:** {reg.get('marca', 'N/A')} | **Submarca:** {reg.get('submarca', 'N/A')} | **Modelo:** {reg.get('modelo', 'N/A')}")
                        st.write(f"**Tipo de Unidad:** {reg.get('tipo_unidad', 'N/A')}")
                        
                        st.write("### Documentación de Unidad")
                        docs_u = {
                            "Tarjeta de Circulación": "url_tarjeta_circulacion",
                            "Póliza de Seguro": "url_poliza_seguro",
                            "Fotografía VIN": "url_vin",
                            "Fotografía Placas": "url_placa"
                        }
                        
                        documentos_u_validos = {}
                        for nombre, key in docs_u.items():
                            url = reg.get(key)
                            if url and isinstance(url, str) and url.startswith("http"):
                                st.link_button(f"📄 Ver {nombre}", url)
                                documentos_u_validos[nombre] = url
                            else:
                                st.caption(f"❌ {nombre}: No cargado")
                                
                        if documentos_u_validos:
                            st.write("---")
                            st.download_button(
                                label="📦 Descargar Documentos en ZIP",
                                data=generar_zip(documentos_u_validos),
                                file_name=f"Unidad_{sel.replace(' ', '_')}.zip",
                                mime="application/zip"
                            )
            else:
                st.info("No tienes unidades registradas en tu cuenta.")
        except Exception as e:
            st.error(f"Error cargando unidades: {e}")

# ===============================================
# PESTAÑA 5: ACTUALIZACION DE EXPEDIENTES
# ===============================================
with tab5:
    st.header("🔄 Actualización de Expedientes")
    st.info("Utiliza esta sección para subir documentos faltantes, renovaciones o actualizar datos de contacto y bancarios.")
    
    rfc_busqueda = st.text_input("Ingresa el RFC del conductor para actualizar:")
    
    if rfc_busqueda:
        res = supabase.table("alta_conductor").select("*").eq("rfc", rfc_busqueda.upper()).eq("creado_por", usuario_id_activo).execute()
        
        if res.data:
            reg = res.data[0]
            st.write(f"Conductor encontrado: **{reg['nombre_driver']}**")
            st.write(f"Celular actual: **{reg.get('celular', 'No registrado')}**")
            banco_actual = reg.get('nombre_banco') or 'No registrado'
            clabe_actual = reg.get('clabe_interbancaria') or 'No registrado'
            st.write(f"Banco actual: **{banco_actual}** | CLABE actual: **{clabe_actual}**")
            
            st.write("---")
            st.write("Estado de documentos actuales:")
            
            docs_map = {}
            docs_map["CURP"] = "url_curp"
            docs_map["INE"] = "url_ine"
            docs_map["Constancia Fiscal"] = "url_constancia_fiscal"
            docs_map["Licencia de Conducir"] = "url_licencia"
            docs_map["Comprobante Domicilio"] = "url_comprobante_domicilio"
            docs_map["Caratula Bancaria"] = "url_caratula_bancaria"
            docs_map["Examen Toxicologico"] = "url_toxicologico"
            
            cols = st.columns(3)
            for i, (nombre, key) in enumerate(docs_map.items()):
                status = "✅" if reg.get(key) else "❌"
                cols[i % 3].write(f"{status} {nombre}")
            st.write("---")
            
            opcion = st.selectbox("¿Qué deseas actualizar?", [""] + list(docs_map.keys()) + ["Actualizar Número de Celular", "Actualizar Datos Bancarios"])
            
            if opcion == "Actualizar Número de Celular":
                nuevo_celular = st.text_input("Nuevo número de celular:", value=reg.get('celular') or "")
                if st.button("Guardar nuevo celular"):
                    supabase.table("alta_conductor").update({"celular": nuevo_celular}).eq("rfc", rfc_busqueda.upper()).execute()
                    st.success("¡Celular actualizado correctamente!")
            
            elif opcion == "Actualizar Datos Bancarios":
                nuevo_banco = st.text_input("Nuevo Nombre del Banco:", value=reg.get('nombre_banco') or "")
                nueva_clabe = st.text_input("Nueva CLABE Interbancaria:", max_chars=18, value=reg.get('clabe_interbancaria') or "")
                
                if st.button("Guardar datos bancarios"):
                    if nueva_clabe and len(nueva_clabe) < 18:
                        st.error(f"La CLABE está incompleta. Ingresaste {len(nueva_clabe)} dígitos de los 18 requeridos.")
                    elif nueva_clabe and not nueva_clabe.isdigit():
                        st.error("La CLABE solo debe contener números.")
                    else:
                        supabase.table("alta_conductor").update({
                            "nombre_banco": nuevo_banco,
                            "clabe_interbancaria": nueva_clabe
                        }).eq("rfc", rfc_busqueda.upper()).execute()
                        st.success("¡Datos bancarios updated correctamente!")
            
            elif opcion in docs_map:
                archivo_nuevo = st.file_uploader(f"Cargar nuevo archivo de {opcion}")
                if st.button("Guardar actualización"):
                    if archivo_nuevo:
                        columna_db = docs_map[opcion]
                        nombre_carpeta = opcion.lower().replace(" ", "_")
                        ruta_storage = f"conductores/{nombre_carpeta}s"
                        
                        nueva_url = procesar_archivo(archivo_nuevo, ruta_storage, rfc_busqueda.upper())
                        supabase.table("alta_conductor").update({columna_db: nueva_url}).eq("rfc", rfc_busqueda.upper()).execute()
                        st.success(f"¡{opcion} actualizado correctamente!")
                    else:
                        st.warning("Por favor selecciona un archivo.")
        else:
            st.error("No se encontró ningún conductor con ese RFC en tu cuenta de usuario.")

# ==========================================
# PESTAÑA 6: REGISTRO DE OPERACIÓN Y DEVOLUCIONES
# ==========================================
with tab6:
    st.header("Captura Dinámica de Despacho Operativo")
    st.write("Módulo relacional. Permite enlazar los conductores y unidades activos en sistema.")
    
    # 1. Definimos variables vacías por defecto para prevenir NameError
    dict_conductores = {}
    dict_unidades = {}
    
    # 2. Intentamos cargar datos desde la base de datos (Filtrados por usuario activo)
    try:
        conductores_db = supabase.table("alta_conductor").select("id_conductor, nombre_driver").eq("creado_por", usuario_id_activo).execute().data
        unidades_db = supabase.table("unidades").select("id_unidad, placas").eq("creado_por", usuario_id_activo).execute().data
        
        # Mapeo seguro
        dict_conductores = {c["nombre_driver"]: c["id_conductor"] for c in conductores_db}
        dict_unidades = {u["placas"]: u["id_unidad"] for u in unidades_db}
    except Exception as e:
        st.error(f"Error de sincronización con Supabase: {e}")

    # 3. Verificamos que existan datos antes de mostrar el formulario
    if not dict_conductores or not dict_unidades:
        st.warning("⚠️ Atención: Debes tener conductores y unidades registrados para operar.")
    else:
        # =======================================================
        # MÓDULO 1: REGISTRO DE OPERACIÓN (DESPACHO)
        # =======================================================
        with st.form("form_operacion", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                # --- CAMPO: Tipo de Cliente ---
                tipo_cliente = st.selectbox("Tipo de Cliente *", options=["", "Mercado Libre", "Amazon"])
                
                sel_conductor = st.selectbox("Seleccione el Conductor asignado *", options=[""] + list(dict_conductores.keys()))
                sel_unidad = st.selectbox("Seleccione las Placas del Vehículo *", options=[""] + list(dict_unidades.keys()))
                status_operacion = st.selectbox("Estatus del Servicio", options=["En ruta", "Cancelacion", "No show"])
                
                # --- CAMPOS BOOLEANOS Y COSTO ---
                es_ambulancia = st.checkbox("¿Realizó Ambulancia?")
                es_costal = st.checkbox("¿Es Costal?")
                monto_ambulancia = st.number_input("Costo Ambulancia ($)", min_value=0.0, value=0.0, step=100.0)
            
            with col2:
                paquetes = st.number_input("Cantidad de Paquetes Cargados", min_value=0, step=1, value=0)
                paradas = st.number_input("Número de Paradas Planificadas (Ruta)", min_value=0, step=1, value=0)
                
            st.subheader("⏱️ Tiempos de Estancia en Hub")
            t1, t2 = st.columns(2)
            with t1:
                fecha_llegada = st.date_input("Fecha de Llegada al Hub")
                hora_llegada = st.time_input("Hora de Entrada (Hub)")
            with t2:
                fecha_salida = st.date_input("Fecha de Salida del Hub")
                hora_salida = st.time_input("Hora de Despacho (Hub)")
            
            c_btn1, c_btn2 = st.columns([1, 4])
            with c_btn1:
                limpiar = st.form_submit_button("Limpiar")
            with c_btn2:
                enviar_operacion = st.form_submit_button("Cerrar y Despachar Operación")
            
            if limpiar:
                st.info("🧹 Formulario reiniciado a sus valores por defecto.")
            
            if enviar_operacion:
                if not tipo_cliente or not sel_conductor or not sel_unidad:
                    st.error("Por favor selecciona el Tipo de Cliente, el Conductor y el Vehículo válidos para despachar.")
                else:
                    iso_llegada = datetime.combine(fecha_llegada, hora_llegada).isoformat()
                    iso_salida = datetime.combine(fecha_salida, hora_salida).isoformat()
                    
                    datos_operacion = {
                        "creado_por": usuario_id_activo,  # <--- LLAVE MAESTRA AÑADIDA PARA DESPACHOS
                        "tipo_cliente": tipo_cliente,
                        "conductor_id": dict_conductores[sel_conductor],
                        "unidad_id": dict_unidades[sel_unidad],
                        "status_operacion": status_operacion,
                        "hora_llegada_hub": iso_llegada,
                        "hora_salida_hub": iso_salida,
                        "paquetes_cargados": int(paquetes),
                        "paradas": int(paradas),
                        "ambulancia": es_ambulancia,
                        "costal": es_costal,
                        "costo_ambulancia_variable": float(monto_ambulancia)
                    }
                    
                    try:
                        supabase.table("registro_operacion").insert(datos_operacion).execute()
                        st.success(f"¡Viaje despachado! (Ambulancia: {'Sí' if es_ambulancia else 'No'} | Costo: ${monto_ambulancia:,.2f})")
                    except Exception as e:
                        st.error(f"Error al registrar la operación en base de datos: {e}")

        # =======================================================
        # MÓDULO 2: REGISTRO DE DEVOLUCIONES (SMX10-operaciones)
        # =======================================================
        st.write("---")
        st.subheader("📦 Registro de Devoluciones")
        st.write("Captura de paquetes retornados asociando la operación a un conductor y unidad.")

        with st.form("form_devoluciones", clear_on_submit=True):
            col_dev1, col_dev2 = st.columns(2)
            
            with col_dev1:
                dev_cliente = st.selectbox("Tipo de Cliente (Devolución) *", options=["", "Mercado Libre", "Amazon"])
                dev_conductor = st.selectbox("Conductor asignado *", options=[""] + list(dict_conductores.keys()), key="dev_cond")
                dev_unidad = st.selectbox("Placas del Vehículo *", options=[""] + list(dict_unidades.keys()), key="dev_unid")
            
            with col_dev2:
                # Permite seleccionar una fecha pasada para devoluciones desfasadas
                dev_fecha = st.date_input("Fecha de Devolución *")
                dev_paquetes = st.number_input("Cantidad de Paquetes Devueltos *", min_value=1, step=1, value=1)
            
            enviar_devolucion = st.form_submit_button("Registrar Devolución")
            
            if enviar_devolucion:
                if not dev_cliente or not dev_conductor or not dev_unidad:
                    st.error("⚠️ Por favor selecciona el Cliente, Conductor y Placas para registrar la devolución.")
                else:
                    datos_devolucion = {
                        "user_id": usuario_id_activo,  # <--- LLAVE MAESTRA AÑADIDA PARA DEVOLUCIONES
                        "fecha_devolucion": dev_fecha.isoformat(),
                        "tipo_cliente": dev_cliente,
                        "conductor_id": dict_conductores[dev_conductor],
                        "unidad_id": dict_unidades[dev_unidad],
                        "paquetes_devueltos": int(dev_paquetes)
                    }
                    
                    try:
                        supabase.table("devoluciones").insert(datos_devolucion).execute()
                        st.success(f"✅ ¡Devolución de {dev_paquetes} paquete(s) de {dev_cliente} registrada correctamente!")
                    except Exception as e:
                        st.error(f"Error al registrar la devolución en la base de datos: {e}")


# ===============================================
# PESTAÑA 7: VERIFICACION DE CAPTURA Y EDICIÓN
# ===============================================
with tab7:
    st.header("📊 Verificación de Captura y Edición")
    st.write("Consulta, verifica, modifica o elimina los despachos operativos registrados en el sistema.")
    
    # --- FILTROS DE FECHA ---
    c_ini, c_fin = st.columns(2)
    with c_ini:
        fecha_inicio = st.date_input("Fecha de Inicio")
    with c_fin:
        fecha_fin = st.date_input("Fecha de Término")
        
    if st.button("Buscar Capturas"):
        try:
            # Filtro aplicado para traer solo los viajes registrados por el usuario activo
            res_op = supabase.table("registro_operacion").select("*").eq("creado_por", usuario_id_activo).execute()
            df_op = pd.DataFrame(res_op.data)
            
            if not df_op.empty:
                # Filtros añadidos para que los diccionarios de edición también sean exclusivos del usuario
                cond_db = supabase.table("alta_conductor").select("id_conductor, nombre_driver").eq("creado_por", usuario_id_activo).execute().data
                unid_db = supabase.table("unidades").select("id_unidad, placas, tipo_unidad").eq("creado_por", usuario_id_activo).execute().data
                
                map_cond = {c["id_conductor"]: c["nombre_driver"] for c in cond_db}
                map_unid = {u["id_unidad"]: u["placas"] for u in unid_db}
                map_tipo_unid = {u["id_unidad"]: u.get("tipo_unidad", "N/A") for u in unid_db}
                
                df_op["Conductor"] = df_op["conductor_id"].map(map_cond)
                df_op["Placas"] = df_op["unidad_id"].map(map_unid)
                df_op["Tipo Unidad"] = df_op["unidad_id"].map(map_tipo_unid) 
                
                df_op["hora_llegada_hub_raw"] = pd.to_datetime(df_op["hora_llegada_hub"]).dt.tz_localize(None)
                
                mascara = (df_op["hora_llegada_hub_raw"].dt.date >= fecha_inicio) & (df_op["hora_llegada_hub_raw"].dt.date <= fecha_fin)
                df_filtrado = df_op.loc[mascara].copy()
                
                if not df_filtrado.empty:
                    df_filtrado["hora_llegada_hub_str"] = df_filtrado["hora_llegada_hub_raw"].dt.strftime('%Y-%m-%d %H:%M')
                    
                    st.write("---")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total de Viajes", len(df_filtrado))
                    m2.metric("Paquetes Procesados", int(df_filtrado["paquetes_cargados"].sum()))
                    m3.metric("Paradas Planificadas", int(df_filtrado["paradas"].sum()))
                    st.write("---")
                    
                    df_mostrar = df_filtrado[[
                        "id", "hora_llegada_hub_str", "Conductor", "Placas", 
                        "Tipo Unidad", "tipo_cliente", "status_operacion", 
                        "ambulancia", "paquetes_cargados", "paradas"
                    ]].rename(columns={
                        "hora_llegada_hub_str": "Hora de Arribo",
                        "tipo_cliente": "Cliente",
                        "status_operacion": "Condición",
                        "paquetes_cargados": "Paquetes",
                        "paradas": "Paradas"
                    })
                    
                    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                    
                    st.divider()
                    st.subheader("🛠️ Gestión de Registros (Modificar o Eliminar)")
                    
                    if "id" in df_filtrado.columns:
                        opciones_editar = df_filtrado.apply(
                            lambda x: f"ID: {x['id']} | {x['hora_llegada_hub_str']} | {x['Conductor']} | {x['Placas']}",
                            axis=1
                        ).tolist()
                        
                        registro_seleccionado = st.selectbox("Selecciona un viaje de la lista para gestionar:", [""] + opciones_editar)
                        
                        if registro_seleccionado:
                            id_registro = int(registro_seleccionado.split(" | ")[0].replace("ID: ", ""))
                            row_data = df_filtrado[df_filtrado["id"] == id_registro].iloc[0]
                            
                            dict_cond_inv = {v: k for k, v in map_cond.items()}
                            dict_unid_inv = {v: k for k, v in map_unid.items()}
                            
                            with st.form("form_edicion"):
                                st.write("**📝 Formulario de Actualización**")
                                c_ed1, c_ed2 = st.columns(2)
                                with c_ed1:
                                    cli_actual = row_data.get("tipo_cliente", "")
                                    idx_cli = ["Mercado Libre", "Amazon", ""].index(cli_actual) if cli_actual in ["Mercado Libre", "Amazon", ""] else 0
                                    nuevo_cliente = st.selectbox("Cliente", ["Mercado Libre", "Amazon", ""], index=idx_cli)
                                    
                                    cond_actual = row_data["Conductor"]
                                    idx_cond = list(dict_cond_inv.keys()).index(cond_actual) if cond_actual in dict_cond_inv else 0
                                    nuevo_cond = st.selectbox("Conductor", list(dict_cond_inv.keys()), index=idx_cond)
                                    
                                    unid_actual = row_data["Placas"]
                                    idx_unid = list(dict_unid_inv.keys()).index(unid_actual) if unid_actual in dict_unid_inv else 0
                                    nueva_unidad = st.selectbox("Vehículo (Placas)", list(dict_unid_inv.keys()), index=idx_unid)
                                
                                with c_ed2:
                                    stat_actual = row_data.get("status_operacion", "En ruta")
                                    idx_stat = ["En ruta", "Cancelacion", "No show"].index(stat_actual) if stat_actual in ["En ruta", "Cancelacion", "No show"] else 0
                                    nuevo_status = st.selectbox("Condición", ["En ruta", "Cancelacion", "No show"], index=idx_stat)
                                    
                                    nuevos_paquetes = st.number_input("Paquetes", min_value=0, step=1, value=int(row_data.get("paquetes_cargados", 0)))
                                    nuevas_paradas = st.number_input("Paradas", min_value=0, step=1, value=int(row_data.get("paradas", 0)))
                                
                                es_amb = True if row_data.get("ambulancia") == True else False
                                nueva_ambulancia = st.checkbox("El servicio es Ambulancia", value=es_amb)
                                
                                st.write("⏱️ Ajuste de Horario de Arribo")
                                raw_dt = row_data["hora_llegada_hub_raw"]
                                t1, t2 = st.columns(2)
                                with t1:
                                    nueva_fecha = st.date_input("Nueva Fecha", value=raw_dt.date())
                                with t2:
                                    nueva_hora = st.time_input("Nueva Hora", value=raw_dt.time())
                                
                                st.divider()
                                btn_col1, btn_col2 = st.columns(2)
                                with btn_col1:
                                    btn_actualizar = st.form_submit_button("💾 Guardar Cambios")
                                with btn_col2:
                                    btn_eliminar = st.form_submit_button("❌ Eliminar Registro Completo")
                                    
                            if btn_actualizar:
                                iso_llegada_nueva = datetime.combine(nueva_fecha, nueva_hora).isoformat()
                                datos_actualizados = {
                                    "tipo_cliente": nuevo_cliente,
                                    "conductor_id": dict_cond_inv[nuevo_cond],
                                    "unidad_id": dict_unid_inv[nueva_unidad],
                                    "status_operacion": nuevo_status,
                                    "ambulancia": nueva_ambulancia,
                                    "paquetes_cargados": nuevos_paquetes,
                                    "paradas": nuevas_paradas,
                                    "hora_llegada_hub": iso_llegada_nueva
                                }
                                try:
                                    supabase.table("registro_operacion").update(datos_actualizados).eq("id", id_registro).execute()
                                    st.success("✅ ¡Registro actualizado! Presiona 'Buscar Capturas' para refrescar.")
                                except Exception as e:
                                    st.error(f"Error al actualizar: {e}")
                                    
                            if btn_eliminar:
                                try:
                                    supabase.table("registro_operacion").delete().eq("id", id_registro).execute()
                                    st.warning("🗑️ ¡Registro eliminado! Presiona 'Buscar Capturas' para refrescar.")
                                except Exception as e:
                                    st.error(f"Error al eliminar: {e}")
                    else:
                        st.error("Falta la columna 'id' Primary Key en la tabla de Supabase.")
                else:
                    st.warning(f"No se encontraron capturas entre {fecha_inicio} y {fecha_fin}.")
            else:
                st.info("Aún no hay registros de operaciones.")
        except Exception as e:
            st.error(f"Error al generar la consulta: {e}")
