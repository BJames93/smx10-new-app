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
        # El .strip() elimina espacios invisibles al inicio o al final del texto
        input_user = st.session_state["username"].strip()
        input_pass = st.session_state["password"].strip()
        
        try:
            res = supabase.table("usuarios_acceso").select("*").eq("nombre_usuario", input_user).eq("contrasena", input_pass).execute()
            
            if len(res.data) > 0:
                st.session_state["password_correct"] = True
                # AQUÍ GUARDAMOS TODOS LOS DATOS DEL USUARIO EN MEMORIA
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
# Variable global para todo el código
usuario_id_activo = st.session_state["usuario_actual"]["user_id"]
nombre_usuario_activo = st.session_state["usuario_actual"]["nombre_usuario"]

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Plataforma SMX10", page_icon="🚀", layout="wide")

# --- OCULTAR ELEMENTOS DE LA INTERFAZ DE STREAMLIT ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* Ocultar el botón flotante de Deploy/Manage */
            .stDeployButton {display: none;}
            .viewerBadge_container {display: none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Mensaje lateral de bienvenida
st.sidebar.success(f"👤 Conectado como: **{nombre_usuario_activo}**")

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
            if not nombre_empresa or not nombre_rl or not rfc_empresa:
                st.error("Por favor completa los campos obligatorios (Nombre, RFC y Representante Legal).")
            elif len(rfc_empresa) < 18:
                st.error(f"El RFC está incompleto. Ingresaste {len(rfc_empresa)} caracteres de los 18 requeridos.")
            else:
                empresa_upper = nombre_empresa.upper()
                rfc_upper = rfc_empresa.upper()
                
                datos_empresa = {
                    "nombre_empresa": empresa_upper,
                    "rfc_empresa": rfc_upper,  
                    "nombre_rl": nombre_rl,
                    "creado_por": usuario_id_activo,
                    "url_ine_rl": procesar_archivo(f_ine_rl, "empresas/ines", empresa_upper),
                    "
