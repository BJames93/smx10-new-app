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
BUCKET_NAME = "documentos_operacion"

# --- LÓGICA DE LOGIN CON SUPABASE ---
def check_password():
    def password_entered():
        input_user = st.session_state["username"]
        input_pass = st.session_state["password"]
        
        try:
            # Consultamos la tabla de usuarios en Supabase
            res = supabase.table("usuarios_acceso").select("*").eq("nombre_usuario", input_user).eq("contrasena", input_pass).execute()
            
            if len(res.data) > 0:
                st.session_state["password_correct"] = True
                del st.session_state["password"]  # Por seguridad
            else:
                st.session_state["password_correct"] = False
        except Exception as e:
            st.error(f"Error de conexión con la base de datos: {e}")
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

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Plataforma SMX10", page_icon="🚀", layout="wide")
st.title("📊 Sistema Centralizado SVC: SMX10")

# Reordenamiento de Tabs
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
            # --- NUEVO CAMPO RFC ---
            rfc_empresa = st.text_input("RFC de la Empresa *", max_chars=18, help="El RFC debe tener exactamente 18 caracteres.")
        with col2:
            nombre_rl = st.text_input("Nombre del Representante Legal (RL) *")
        
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
            # Validación de campos obligatorios
            if not nombre_empresa or not nombre_rl or not rfc_empresa:
                st.error("Por favor completa los campos obligatorios (Nombre, RFC y Representante Legal).")
            # Validación estricta de longitud del RFC
            elif len(rfc_empresa) < 18:
                st.error(f"El RFC está incompleto. Ingresaste {len(rfc_empresa)} caracteres de los 18 requeridos.")
            else:
                empresa_upper = nombre_empresa.upper()
                rfc_upper = rfc_empresa.upper()
                
                datos_empresa = {
                    "nombre_empresa": empresa_upper,
                    "rfc_empresa": rfc_upper,  # <-- Se guarda en la BD
                    "nombre_rl": nombre_rl,
                    "url_ine_rl": procesar_archivo(f_ine_rl, "empresas/ines", empresa_upper),
                    "url_constancia_fiscal": procesar_archivo(f_csf, "empresas/fiscal", empresa_upper),
                    "url_caratula_bancaria": procesar_archivo(f_cb, "empresas/bancos", empresa_upper),
                    "url_comprobante_domicilio": procesar_archivo(f_dom_empresa, "empresas/domicilios", empresa_upper)
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
            f_foto = st.file_uploader("Foto")
            f_ine = st.file_uploader("INE")
            f_curp = st.file_uploader("CURP")
            
        with c2:
            st.markdown("**Operación y Control**")
            f_lic = st.file_uploader("Licencia")
            f_tox = st.file_uploader("Toxicológico")
            f_ref = st.file_uploader("Carta de Referencia")
            
        with c3:
            st.markdown("**Fiscal y Bancario**")
            f_fis = st.file_uploader("Constancia Fiscal")
            f_dom = st.file_uploader("Domicilio")
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
                datos = {
                    "nombre_driver": nombre, 
                    "rfc": rfc.upper(), 
                    "correo": correo, 
                    "celular": celular,
                    "nombre_banco": banco,             
                    "clabe_interbancaria": clabe,    
                    "url_fotografia": procesar_archivo(f_foto, "conductores/fotos", rfc),
                    "url_curp": procesar_archivo(f_curp, "conductores/curps", rfc),
                    "url_ine": procesar_archivo(f_ine, "conductores/ines", rfc),
                    "url_constancia_fiscal": procesar_archivo(f_fis, "conductores/fiscal", rfc),
                    "url_licencia": procesar_archivo(f_lic, "conductores/licencias", rfc),
                    "url_comprobante_domicilio": procesar_archivo(f_dom, "conductores/domicilios", rfc),
                    "url_caratula_bancaria": procesar_archivo(f_ban, "conductores/bancos", rfc),
                    "url_toxicologico": procesar_archivo(f_tox, "conductores/toxicologicos", rfc),
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
        
        f_circ = st.file_uploader("Tarjeta Circulación")
        f_seg = st.file_uploader("Seguro")
        f_vin = st.file_uploader("Fotografía VIN")
        f_plac = st.file_uploader("Fotografía Placas")
        
        enviar_u = st.form_submit_button("Registrar Unidad")
        if enviar_u:
            if not p:
                st.error("Las placas son obligatorias.")
            else:
                datos_u = {
                    "placas": p.upper(), 
                    "modelo": int(mod), 
                    "marca": m, 
                    "submarca": sm,
                    "tipo_unidad": tipo,
                    "url_tarjeta_circulacion": procesar_archivo(f_circ, "unidades/tarjetas", p),
                    "url_poliza_seguro": procesar_archivo(f_seg, "unidades/polizas", p),
                    "url_vin": procesar_archivo(f_vin, "unidades/vin", p),
                    "url_placa": procesar_archivo(f_plac, "unidades/placas", p)
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
            res = supabase.table("alta_conductor").select("*").execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                df['nombre_driver'] = df['nombre_driver'].fillna("").astype(str)
                sel = st.selectbox("Seleccione Conductor:",
