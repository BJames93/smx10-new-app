import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import pandas as pd
import unicodedata 
import io
import zipfile
import requests

# Importación segura de FPDF para evitar fallos críticos en servidor
try:
    from fpdf import FPDF
except ModuleNotFoundError:
    FPDF = None

# --- 1. CONFIGURACIÓN E INICIALIZACIÓN ---
SUPABASE_URL = "https://sinepuhjujazcaelrqms.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNpbmVwdWhqdWphemNhZWxycW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAzOTgwMDIsImV4cCI6MjA5NTk3NDAwMn0.RoTKaHzfbFViuiNOgMirfws0Pd13nCivAhxDoq_ipJM"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "documentos_operacion_smx10"

# --- CONFIGURACIÓN DE USUARIOS ADMINISTRADORES ---
USUARIOS_MAESTROS = ["boulder_admin", "boulder_admin_02"]
USUARIO_FINANZAS_MASTER = "boulder_admin"  # Exclusivo para pagos y conciliación secreta

# --- LÓGICA DE LOGIN CON SUPABASE ---
def check_password():
    def password_entered():
        input_user = st.session_state["username"].strip()
        input_pass = st.session_state["password"].strip()
        
        try:
            res = supabase.table("usuarios_acceso").select("*").eq("nombre_usuario", input_user).eq("contrasena", input_pass).execute()
            
            if len(res.data) > 0:
                usuario = res.data[0]
                status_usuario = str(usuario.get("status", "Activo")).strip().capitalize()
                if status_usuario == "Inactivo":
                    st.session_state["password_correct"] = False
                    st.error("❌ Tu usuario se encuentra Inactivo. Contacta al administrador.")
                    return
                
                st.session_state["password_correct"] = True
                st.session_state["usuario_actual"] = usuario 
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

# --- FILTRADO CENTRALIZADO DE USUARIOS ACTIVOS ---
mapa_usuarios_master = {}
lista_nombres_usuarios = []
usuarios_activos_ids = []

try:
    res_usuarios_activos = supabase.table("usuarios_acceso").select("user_id, nombre_usuario, status").execute().data
    if res_usuarios_activos:
        for u in res_usuarios_activos:
            st_val = str(u.get("status", "Activo")).strip().capitalize()
            if st_val != "Inactivo":
                mapa_usuarios_master[u["nombre_usuario"]] = u["user_id"]
                usuarios_activos_ids.append(u["user_id"])
        lista_nombres_usuarios = list(mapa_usuarios_master.keys())
except Exception as e:
    st.error(f"Error crítico al inicializar la lista de usuarios activos: {e}")

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Plataforma BoulderBrwn", page_icon="🚀", layout="wide")

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

st.sidebar.success(f"👤 Conectado como: **{nombre_usuario_activo}**")
st.title("📊 Sistema Centralizado de Proveedores - BoulderBrwn")

# --- CONSTRUCCIÓN DE PESTAÑAS DINÁMICAS (Pestaña secreta solo para Admin Máster Finanzas) ---
titulos_tabs = [
    "🏢 Registro de Empresa", "🚗 Alta Conductor", "🚛 Control de Unidades", 
    "🔍 Consulta Integral", "🔄 Actualización de Expedientes", 
    "📋 Registro de Operaciones", "📊 Verificación de Captura"
]

es_admin_finanzas = (nombre_usuario_activo == USUARIO_FINANZAS_MASTER)

if es_admin_finanzas:
    titulos_tabs.append("💰 Conciliación y Pagos")

tabs = st.tabs(titulos_tabs)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4], tabs[5], tabs[6]
tab_reporte = tabs[7] if es_admin_finanzas else None

# ==========================================
# PESTAÑA 1: REGISTRO DE EMPRESA
# ==========================================
with tab1:
    st.header("🏢 Alta y Registro de Empresa")
    creador_id_tab1 = usuario_id_activo
    if nombre_usuario_activo in USUARIOS_MAESTROS and lista_nombres_usuarios:
        user_sel_tab1 = st.selectbox("👑 Asignar esta Empresa al Usuario:", options=lista_nombres_usuarios, index=lista_nombres_usuarios.index(nombre_usuario_activo) if nombre_usuario_activo in lista_nombres_usuarios else 0, key="user_sel_tab1")
        creador_id_tab1 = mapa_usuarios_master[user_sel_tab1]
        st.caption(f"Capturando empresa vinculada a la cuenta de: **{user_sel_tab1}**")
        st.write("---")

    with st.form("form_empresa", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre_empresa = st.text_input("Nombre de la empresa (Se guardará en MAYÚSCULAS) *")
            rfc_empresa = st.text_input("RFC de la Empresa *", max_chars=13)
        with col2:
            nombre_rl = st.text_input("Nombre del Representante Legal (RL) (Se guardará en MAYÚSCULAS) *")

        st.subheader("🏦 Datos Bancarios")
        c_bank1, c_bank2 = st.columns(2)
        with c_bank1:
            banco_empresa = st.text_input("Banco (Se guardará en MAYÚSCULAS) *")
        with c_bank2:
            clabe_empresa = st.text_input("Cuenta CLABE *", max_chars=18)

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
                st.error("Por favor completa los campos obligatorios.")
            elif len(rfc_empresa) < 13:
                st.error("El RFC debe tener 13 caracteres.")
            elif len(clabe_empresa) < 18 or not clabe_empresa.isdigit():
                st.error("La CLABE debe tener 18 dígitos numéricos.")
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
                    "creado_por": creador_id_tab1,
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
    st.header("🚗 Alta de Conductor")
    creador_id_tab2 = usuario_id_activo
    if nombre_usuario_activo in USUARIOS_MAESTROS and lista_nombres_usuarios:
        user_sel_tab2 = st.selectbox("👑 Asignar este Conductor al Usuario:", options=lista_nombres_usuarios, index=lista_nombres_usuarios.index(nombre_usuario_activo) if nombre_usuario_activo in lista_nombres_usuarios else 0, key="user_sel_tab2")
        creador_id_tab2 = mapa_usuarios_master[user_sel_tab2]
        st.caption(f"Capturando conductor vinculado a la cuenta de: **{user_sel_tab2}**")
        st.write("---")

    with st.form("form_conductor", clear_on_submit=True):
        st.subheader("📝 Datos Generales")
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo *")
            rfc = st.text_input("RFC *", max_chars=13)
            correo = st.text_input("Correo")
        with col2:
            celular = st.text_input("Celular")
            banco = st.text_input("Nombre Banco")
            clabe = st.text_input("Clabe Interbancaria", max_chars=18)
            nss_num = st.text_input("Número de Seguro Social (NSS)", max_chars=11)
        
        st.divider() 
        st.subheader("📁 Expediente Digital")
        c1, c2, c3 = st.columns(3)
        with c1:
            f_foto = st.file_uploader("Foto")
            f_ine = st.file_uploader("INE")
            f_curp = st.file_uploader("CURP")
            f_acta = st.file_uploader("Acta de Nacimiento")
        with c2:
            f_lic = st.file_uploader("Licencia")
            f_tox = st.file_uploader("Toxicológico")
            f_ref = st.file_uploader("Carta de Referencia")
        with c3:
            f_fis = st.file_uploader("Constancia Fiscal")
            f_dom = st.file_uploader("Comprobante Domicilio")
            f_ban = st.file_uploader("Carátula Bancaria") 
            f_nss = st.file_uploader("Documento NSS")
        
        st.divider()
        enviar = st.form_submit_button("Guardar Conductor")
        
        if enviar:
            if not nombre or not rfc:
                st.error("Por favor completa los campos obligatorios.")
            else:
                rfc_up = rfc.upper()
                datos = {
                    "nombre_driver": nombre, "rfc": rfc_up, "correo": correo, "celular": celular,
                    "nombre_banco": banco, "clabe_interbancaria": clabe, "creado_por": creador_id_tab2,
                    "url_fotografia": procesar_archivo(f_foto, "conductores/fotos", rfc_up),
                    "url_curp": procesar_archivo(f_curp, "conductores/curps", rfc_up),
                    "url_ine": procesar_archivo(f_ine, "conductores/ines", rfc_up),
                    "url_constancia_fiscal": procesar_archivo(f_fis, "conductores/fiscal", rfc_up),
                    "url_licencia": procesar_archivo(f_lic, "conductores/licencias", rfc_up),
                    "url_comprobante_domicilio": procesar_archivo(f_dom, "conductores/domicilios", rfc_up),
                    "url_caratula_bancaria": procesar_archivo(f_ban, "conductores/bancos", rfc_up),
                    "url_toxicologico": procesar_archivo(f_tox, "conductores/toxicologicos", rfc_up),
                    "url_carta_referencia": procesar_archivo(f_ref, "conductores/referencias", rfc_up),
                    "url_acta_nacimiento": procesar_archivo(f_acta, "conductores/actas", rfc_up),
                    "url_nss": procesar_archivo(f_nss, "conductores/nss", rfc_up)
                }
                try:
                    supabase.table("alta_conductor").insert(datos).execute()
                    st.success("Conductor registrado exitosamente.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# ==========================================
# PESTAÑA 3: CONTROL DE UNIDADES
# ==========================================
with tab3:
    st.header("🚛 Registro y Control de Unidades")
    creador_id_tab3 = usuario_id_activo
    if nombre_usuario_activo in USUARIOS_MAESTROS and lista_nombres_usuarios:
        user_sel_tab3 = st.selectbox("👑 Asignar esta Unidad al Usuario:", options=lista_nombres_usuarios, index=lista_nombres_usuarios.index(nombre_usuario_activo) if nombre_usuario_activo in lista_nombres_usuarios else 0, key="user_sel_tab3")
        creador_id_tab3 = mapa_usuarios_master[user_sel_tab3]
        st.write("---")

    with st.form("form_unidades", clear_on_submit=True):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            p = st.text_input("Placas *")
            m = st.text_input("Marca")
            sm = st.text_input("Submarca")
        with col_u2:
            tipo = st.selectbox("Tipo de Unidad", ["Sedan", "Small", "Large"])
            mod = st.number_input("Modelo", 1990, 2030, 2026)
        
        st.divider()
        c_doc1, c_doc2 = st.columns(2)
        with c_doc1:
            f_circ = st.file_uploader("Tarjeta Circulación")
            f_seg = st.file_uploader("Seguro")
        with c_doc2:
            f_vin = st.file_uploader("Fotografía VIN")
        
        c_img1, c_img2 = st.columns(2)
        with c_img1:
            f_frontal = st.file_uploader("1. Frontal")
            f_trasera = st.file_uploader("2. Trasera")
        with c_img2:
            f_izquierda = st.file_uploader("3. Izquierda")
            f_derecha = st.file_uploader("4. Derecha")
            
        enviar_u = st.form_submit_button("Registrar Unidad")
        if enviar_u:
            if not p:
                st.error("Las placas son obligatorias.")
            else:
                placas_up = p.upper()
                datos_u = {
                    "placas": placas_up, "modelo": int(mod), "marca": m, "submarca": sm, "tipo_unidad": tipo,
                    "creado_por": creador_id_tab3,
                    "url_tarjeta_circulacion": procesar_archivo(f_circ, "unidades/tarjetas", placas_up),
                    "url_poliza_seguro": procesar_archivo(f_seg, "unidades/polizas", placas_up),
                    "url_vin": procesar_archivo(f_vin, "unidades/vin", placas_up),
                    "url_foto_frontal": procesar_archivo(f_frontal, "unidades/fotos_inspeccion", f"{placas_up}_FRONTAL"),
                    "url_foto_trasera": procesar_archivo(f_trasera, "unidades/fotos_inspeccion", f"{placas_up}_TRASERA"),
                    "url_foto_izquierda": procesar_archivo(f_izquierda, "unidades/fotos_inspeccion", f"{placas_up}_IZQUIERDA"),
                    "url_foto_derecha": procesar_archivo(f_derecha, "unidades/fotos_inspeccion", f"{placas_up}_DERECHA")
                }
                try:
                    supabase.table("unidades").insert(datos_u).execute()
                    st.success(f"¡Unidad {placas_up} registrada exitosamente!")
                except Exception as e:
                    st.error(f"Error al registrar unidad: {e}")

# ==========================================
# PESTAÑA 4: CONSULTA DE EXPEDIENTES
# ==========================================
with tab4:
    st.header("🔍 Consulta Integral de Expedientes")
    if nombre_usuario_activo in USUARIOS_MAESTROS and lista_nombres_usuarios:
        user_sel_tab4 = st.selectbox("👑 Filtrar Consulta General por Proveedor:", options=["MOSTRAR TODOS"] + lista_nombres_usuarios, key="user_sel_tab4")
        st.write("---")

    opciones_consulta = ["Conductores", "Unidades"]
    if nombre_usuario_activo in USUARIOS_MAESTROS:
        opciones_consulta.append("Empresas")
        
    tipo_consulta = st.radio("¿Qué desea consultar?", opciones_consulta, horizontal=True)
    
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

    if tipo_consulta == "Empresas":
        res_emp = supabase.table("registro_empresa").select("*").execute()
        df_emp = pd.DataFrame(res_emp.data)
        if not df_emp.empty:
            sel_empresa = st.selectbox("Seleccione Empresa:", [""] + df_emp['nombre_empresa'].tolist())
            if sel_empresa:
                reg_emp = df_emp[df_emp['nombre_empresa'] == sel_empresa].iloc[0].to_dict()
                st.write(f"**RL:** {reg_emp.get('nombre_rl')} | **RFC:** {reg_emp.get('RFC')} | **CLABE:** {reg_emp.get('clabe_empresa')}")

    elif tipo_consulta == "Conductores":
        res = supabase.table("alta_conductor").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            sel = st.selectbox("Seleccione Conductor:", [""] + df['nombre_driver'].tolist())
            if sel:
                reg = df[df['nombre_driver'] == sel].iloc[0].to_dict()
                st.write(f"**RFC:** {reg.get('rfc')} | **Celular:** {reg.get('celular')} | **CLABE:** {reg.get('clabe_interbancaria')}")

    elif tipo_consulta == "Unidades":
        res = supabase.table("unidades").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            sel = st.selectbox("Seleccione Placas:", [""] + df['placas'].tolist())
            if sel:
                reg = df[df['placas'] == sel].iloc[0].to_dict()
                st.write(f"**Marca:** {reg.get('marca')} | **Modelo:** {reg.get('modelo')} | **Tipo:** {reg.get('tipo_unidad')}")

# ===============================================
# PESTAÑA 5: ACTUALIZACIÓN DE EXPEDIENTES
# ===============================================
with tab5:
    st.header("🔄 Actualización de Expedientes")
    st.info("Utiliza esta sección para subir documentos faltantes o actualizar información.")

# ==========================================
# PESTAÑA 6: REGISTRO DE OPERACIÓN Y DEVOLUCIONES
# ==========================================
with tab6:
    st.header("📋 Captura Dinámica de Despacho Operativo")
    dict_conductores, dict_unidades, dict_conductores_owner = {}, {}, {}
    lista_hubs_svc = [""]
    
    try:
        hubs_db = supabase.table("hubs_svc").select("svc").order("svc", desc=False).execute().data
        if hubs_db:
            lista_hubs_svc = [""] + [h["svc"] for h in hubs_db]

        conductores_db = supabase.table("alta_conductor").select("id_conductor, nombre_driver, creado_por").execute().data
        unidades_db = supabase.table("unidades").select("id_unidad, placas, creado_por").execute().data
        
        dict_conductores = {c["nombre_driver"]: c["id_conductor"] for c in conductores_db}
        dict_unidades = {u["placas"]: u["id_unidad"] for u in unidades_db}
        dict_conductores_owner = {c["id_conductor"]: c.get("creado_por") for c in conductores_db}
    except Exception as e:
        st.error(f"Error al sincronizar catálogos: {e}")

    with st.form("form_operacion", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo_cliente = st.selectbox("Tipo de Cliente *", options=["", "Mercado Libre", "Amazon"])
            sel_conductor = st.selectbox("Seleccione Conductor *", options=[""] + list(dict_conductores.keys()))
            sel_unidad = st.selectbox("Seleccione Vehículo *", options=[""] + list(dict_unidades.keys()))
            status_operacion = st.selectbox("Estatus del Servicio", options=["En ruta", "Cancelacion", "No show"])
            es_ambulancia = st.checkbox("¿Realizó Ambulancia?")
            es_costal = st.checkbox("¿Es Costal?")
            monto_ambulancia = st.number_input("Costo Ambulancia ($)", min_value=0.0, value=0.0, step=100.0)
        
        with col2:
            sel_svc = st.selectbox("HUB (SVC) *", options=lista_hubs_svc)
            paquetes = st.number_input("Paquetes Cargados", min_value=0, step=1, value=0)
            paradas = st.number_input("Paradas Planificadas", min_value=0, step=1, value=0)
            fecha_llegada = st.date_input("Fecha Llegada")
            hora_llegada = st.time_input("Hora Entrada")
            fecha_salida = st.date_input("Fecha Salida")
            hora_salida = st.time_input("Hora Despacho")
            
        enviar_operacion = st.form_submit_button("Cerrar y Despachar Operación")
        if enviar_operacion and tipo_cliente and sel_conductor and sel_unidad and sel_svc:
            iso_llegada = datetime.combine(fecha_llegada, hora_llegada).isoformat()
            iso_salida = datetime.combine(fecha_salida, hora_salida).isoformat()
            cond_id = dict_conductores[sel_conductor]
            
            datos_op = {
                "creado_por": dict_conductores_owner.get(cond_id, usuario_id_activo), 
                "tipo_cliente": tipo_cliente,
                "conductor_id": cond_id,
                "unidad_id": dict_unidades[sel_unidad],
                "status_operacion": status_operacion,
                "hora_llegada_hub": iso_llegada,
                "hora_salida_hub": iso_salida,
                "paquetes_cargados": int(paquetes),
                "paradas": int(paradas),
                "ambulancia": es_ambulancia,
                "costal": es_costal,
                "costo_ambulancia_variable": float(monto_ambulancia),
                "svc": sel_svc  
            }
            try:
                supabase.table("registro_operacion").insert(datos_op).execute()
                st.success("¡Operación registrada con éxito!")
            except Exception as e:
                st.error(f"Error al registrar operación: {e}")

# ===============================================
# PESTAÑA 7: VERIFICACIÓN DE CAPTURA
# ===============================================
with tab7:
    st.header("📊 Verificación de Captura")
    st.write("Consulta y verificación de servicios capturados.")

# ===============================================
# NUEVA PESTAÑA: REPORTE DE CONCILIACIÓN (SECRETA Y EXCLUSIVA ADMIN FINANZAS)
# ===============================================
if es_admin_finanzas and tab_reporte:
    with tab_reporte:
        st.header("📊 Reporte de Conciliación Financiera y Facturación")
        st.info("🔐 Módulo confidencial para cálculo fiscal, dispersión de pagos a proveedores y facturación corporativa.")
        
        # --- OPCIONES DE FACTURACIÓN Y PROVEEDOR ---
        opcion_empresa = st.radio(
            "Seleccione la Entidad Emisora / Régimen Fiscal:", 
            ["Proveedor Tercero (RESICO - Retención 1.25%)", "BoulderBrwn (Persona Moral - Operación Directa / Sin Retención)"],
            horizontal=True
        )
        
        es_resico = "RESICO" in opcion_empresa
        
        proveedor_seleccionado = None
        if es_resico:
            # Filtrar lista de proveedores desde usuarios_acceso (excluyendo cuentas máster)
            proveedores_disponibles = [u for u in lista_nombres_usuarios if u not in USUARIOS_MAESTROS]
            if proveedores_disponibles:
                proveedor_seleccionado = st.selectbox("Seleccione el Proveedor a Conciliar:", proveedores_disponibles)
                nombre_empresa_corte = f"Proveedor: {proveedor_seleccionado} (RESICO)"
            else:
                st.warning("No hay proveedores registrados en el sistema.")
                nombre_empresa_corte = "Proveedor RESICO"
        else:
            nombre_empresa_corte = "BoulderBrwn (Persona Moral)"

        st.divider()

        # Parámetros de selección del periodo de corte
        c1, c2, c3 = st.columns(3)
        with c1:
            fecha_ini = st.date_input("Fecha Inicio de Corte", key="rec_fini")
        with c2:
            fecha_fin = st.date_input("Fecha Fin de Corte", key="rec_ffin")
        with c3:
            semana_corte = st.number_input("Número de Semana (Ej. 34)", min_value=1, step=1, value=34, key="rec_sem")
            
        if st.button("🚀 Generar Conciliación Financiera"):
            try:
                # Consulta directa a las operaciones y cruce dinámico con la tabla de tarifas
                res_operaciones = supabase.table("registro_operacion").select("*").execute()
                res_tarifas = supabase.table("tarifas").select("*").execute()
                
                df_rep = pd.DataFrame(res_operaciones.data)
                df_tar = pd.DataFrame(res_tarifas.data)
                
                if not df_rep.empty:
                    df_rep["fecha_raw"] = pd.to_datetime(df_rep["hora_llegada_hub"]).dt.tz_localize(None).dt.date
                    mascara_fechas = (df_rep["fecha_raw"] >= fecha_ini) & (df_rep["fecha_raw"] <= fecha_fin)
                    
                    # Si es proveedor RESICO, filtramos por sus registros asignados
                    if es_resico and proveedor_seleccionado:
                        uid_prov = mapa_usuarios_master.get(proveedor_seleccionado)
                        mascara_fechas = mascara_fechas & (df_rep["creado_por"] == uid_prov)
                    
                    df_periodo = df_rep.loc[mascara_fechas].copy()
                    
                    if not df_periodo.empty:
                        # Mapear nombres de conductores y vehículos
                        res_cond = supabase.table("alta_conductor").select("id_conductor, nombre_driver, nombre_banco, clabe_interbancaria").execute().data
                        res_unid = supabase.table("unidades").select("id_unidad, placas, marca, tipo_unidad").execute().data
                        
                        map_cond = {c["id_conductor"]: c["nombre_driver"] for c in res_cond}
                        map_banco = {c["id_conductor"]: c.get("nombre_banco", "") for c in res_cond}
                        map_clabe = {c["id_conductor"]: c.get("clabe_interbancaria", "") for c in res_cond}
                        map_unid = {u["id_unidad"]: u["placas"] for u in res_unid}
                        map_marca = {u["id_unidad"]: u.get("marca", "") for u in res_unid}
                        map_tipo = {u["id_unidad"]: u.get("tipo_unidad", "") for u in res_unid}
                        
                        df_periodo["Conductor"] = df_periodo["conductor_id"].map(map_cond)
                        df_periodo["Banco"] = df_periodo["conductor_id"].map(map_banco)
                        df_periodo["Cuenta_clabe"] = df_periodo["conductor_id"].map(map_clabe)
                        df_periodo["Placas"] = df_periodo["unidad_id"].map(map_unid)
                        df_periodo["Marca_del_Vehiculo"] = df_periodo["unidad_id"].map(map_marca)
                        df_periodo["Tipo"] = df_periodo["unidad_id"].map(map_tipo)
                        df_periodo["Hora_Arribo"] = pd.to_datetime(df_periodo["hora_llegada_hub"]).dt.strftime('%Y-%m-%d %H:%M')
                        df_periodo["Dia_Semana"] = pd.to_datetime(df_periodo["hora_llegada_hub"]).dt.strftime('%A')
                        df_periodo["Cliente"] = df_periodo["tipo_cliente"]
                        df_periodo["Condicion"] = df_periodo["status_operacion"]
                        df_periodo["Paquetes"] = df_periodo["paquetes_cargados"]
                        df_periodo["Paradas"] = df_periodo["paradas"]
                        df_periodo["Es_Ambulancia"] = df_periodo["ambulancia"]
                        df_periodo["Es_Costal"] = df_periodo["costal"]
                        
                        # Asignación de tarifas y cálculo de impuestos
                        df_periodo["Monto_por_Unidad"] = df_periodo.apply(lambda r: float(r.get("costo_ambulancia_variable", 0)) if r.get("ambulancia") else 1500.0, axis=1)
                        df_periodo["Monto_Final_Unidad"] = df_periodo["Monto_por_Unidad"]
                        df_periodo["Costo_IMSS"] = 0.0
                        df_periodo["Subtotal"] = df_periodo["Monto_Final_Unidad"]
                        df_periodo["IVA"] = df_periodo["Subtotal"] * 0.16
                        df_periodo["Retencion_ISR"] = df_periodo["Subtotal"] * 0.0125 if es_resico else 0.0
                        df_periodo["Total"] = df_periodo["Subtotal"] + df_periodo["IVA"] - df_periodo["Retencion_ISR"]

                        dia_ini = fecha_ini.strftime('%d')
                        dia_fin = fecha_fin.strftime('%d')
                        meses = ["", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
                        mes_texto = meses[fecha_fin.month]
                        titulo_periodo = f"Corte {dia_ini} al {dia_fin} de {mes_texto} | Semana {semana_corte}"
                        
                        st.divider()
                        
                        # --- SECCIÓN 1: AMAZON ---
                        st.subheader(f"{titulo_periodo} | Amazon")
                        df_amazon = df_periodo[df_periodo["Cliente"] == "Amazon"].copy()
                        if not df_amazon.empty:
                            st.dataframe(df_amazon, use_container_width=True)
                            st.write("**Resumen Financiero - Amazon**")
                            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                            col_a1.metric("Subtotal", f"${df_amazon['Subtotal'].sum():,.2f}")
                            col_a2.metric("IVA (16%)", f"${df_amazon['IVA'].sum():,.2f}")
                            col_a3.metric("Retención ISR", f"${df_amazon['Retencion_ISR'].sum():,.2f}")
                            col_a4.metric("Total Final", f"${df_amazon['Total'].sum():,.2f}")
                        else:
                            st.info("No hay registros de Amazon para este periodo.")
                            
                        st.divider()
                        
                        # --- SECCIÓN 2: MERCADO LIBRE ---
                        st.subheader(f"{titulo_periodo} | Mercado Libre")
                        df_ml = df_periodo[df_periodo["Cliente"] == "Mercado Libre"].copy()
                        if not df_ml.empty:
                            st.dataframe(df_ml, use_container_width=True)
                            st.write("**Resumen Financiero - Mercado Libre**")
                            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                            col_m1.metric("Subtotal", f"${df_ml['Subtotal'].sum():,.2f}")
                            col_m2.metric("IVA (16%)", f"${df_ml['IVA'].sum():,.2f}")
                            col_m3.metric("Retención ISR", f"${df_ml['Retencion_ISR'].sum():,.2f}")
                            col_m4.metric("Total Final", f"${df_ml['Total'].sum():,.2f}")
                        else:
                            st.info("No hay registros de Mercado Libre para este periodo.")
                            
                        st.divider()
                        
                        # --- GRAN TOTAL Y RESUMEN OPERATIVO ---
                        st.subheader(f"Gran Total del Periodo - {nombre_empresa_corte}")
                        t_sub = df_periodo['Subtotal'].sum()
                        t_iva = df_periodo['IVA'].sum()
                        t_ret = df_periodo['Retencion_ISR'].sum()
                        t_tot = df_periodo['Total'].sum()
                        
                        total_servicios = len(df_periodo)
                        total_small = len(df_periodo[df_periodo['Tipo'].astype(str).str.upper() == 'SMALL'])
                        total_large = len(df_periodo[df_periodo['Tipo'].astype(str).str.upper() == 'LARGE'])
                        total_ambulancias = len(df_periodo[df_periodo['Es_Ambulancia'] == True])
                        total_costales = len(df_periodo[df_periodo['Es_Costal'] == True])
                        
                        col_fin, col_ope = st.columns(2)
                        with col_fin:
                            st.markdown("**Desglose Financiero Global:**")
                            st.markdown(f"""
                            * **SUBTOTAL:** ${t_sub:,.2f}
                            * **IVA (16%):** ${t_iva:,.2f}
                            * **RETENCIÓN ISR:** ${t_ret:,.2f}
                            * **TOTAL NETO A DISPERSAR:** **${t_tot:,.2f}**
                            """)
                            
                        with col_ope:
                            st.markdown("**Resumen Operativo de Servicios:**")
                            st.markdown(f"""
                            * **Total de Servicios:** {total_servicios} viajes
                            * **Unidades Small:** {total_small}
                            * **Unidades Large:** {total_large}
                            * **Servicios de Ambulancia:** {total_ambulancias}
                            * **Servicios de Costales:** {total_costales}
                            """)

                        # --- MATRIZ DÍA A DÍA ---
                        st.write("---")
                        st.subheader("📅 Distribución Estructurada de Servicios por Día")
                        
                        def clasificar_servicio(row):
                            if row.get("Es_Ambulancia") == True:
                                return "Ambulancia"
                            elif row.get("Es_Costal") == True:
                                return "Costal"
                            else:
                                tipo = str(row.get("Tipo", "")).upper()
                                if "SMALL" in tipo:
                                    return "Small"
                                elif "LARGE" in tipo:
                                    return "Large"
                            return "Otros"

                        df_periodo["Categoria_Servicio"] = df_periodo.apply(clasificar_servicio, axis=1)
                        dias_ordenados = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                        dias_espanol = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}
                        categorias_filas = ["Small", "Large", "Ambulancia", "Costal", "Otros"]

                        matriz_pivot = pd.crosstab(index=df_periodo["Categoria_Servicio"], columns=df_periodo["Dia_Semana"])
                        matriz_pivot = matriz_pivot.reindex(index=categorias_filas, columns=dias_ordenados, fill_value=0)
                        matriz_pivot = matriz_pivot.rename(columns=dias_espanol)
                        if matriz_pivot.loc["Otros"].sum() == 0:
                            matriz_pivot = matriz_pivot.drop(index="Otros")

                        matriz_pivot["Total General"] = matriz_pivot.sum(axis=1)
                        matriz_pivot.loc["TOTAL SERVICIOS"] = matriz_pivot.sum(axis=0)
                        st.dataframe(matriz_pivot, use_container_width=True)

                        # --- MÓDULO DE EXPORTACIÓN (EXCEL Y PDF) ---
                        st.write("---")
                        st.subheader("📥 Exportar Reportes Finanzas")
                        col_btn1, col_btn2 = st.columns(2)
                        
                        def generar_excel():
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                if not df_amazon.empty:
                                    df_amazon.to_excel(writer, sheet_name='Amazon', index=False)
                                if not df_ml.empty:
                                    df_ml.to_excel(writer, sheet_name='Mercado Libre', index=False)
                                
                                df_resumen = pd.DataFrame([{
                                    "Empresa / Entidad": nombre_empresa_corte,
                                    "Periodo": titulo_periodo,
                                    "Subtotal Total": t_sub,
                                    "IVA Total": t_iva,
                                    "Retencion Total": t_ret,
                                    "Total Final": t_tot,
                                    "Total Servicios": total_servicios
                                }])
                                df_resumen.to_excel(writer, sheet_name='Resumen Financiero', index=False)
                            return output.getvalue()

                        def generar_pdf():
                            if FPDF is None:
                                st.error("❌ La librería 'fpdf2' no está instalada en el servidor. Revisa el archivo requirements.txt.")
                                return None
                            
                            pdf = FPDF(orientation='L', unit='mm', format='A4')
                            pdf.set_auto_page_break(auto=True, margin=15)
                            ANCHO_UTIL = 277

                            pdf.add_page()
                            pdf.set_font("Arial", 'B', 16)
                            pdf.cell(ANCHO_UTIL, 10, txt=f"Reporte de Conciliacion - {nombre_empresa_corte}", ln=True, align='C')
                            pdf.set_font("Arial", size=12)
                            pdf.cell(ANCHO_UTIL, 10, txt=f"Periodo: {titulo_periodo}", ln=True, align='C')
                            pdf.ln(10)

                            pdf.set_font("Arial", 'B', 12)
                            pdf.cell(ANCHO_UTIL, 10, txt="RESUMEN FINANCIERO GLOBAL", ln=True, align='L')
                            pdf.set_font("Arial", size=12)
                            datos_resumen = [("Subtotal", t_sub), ("IVA (16%)", t_iva), ("Retencion ISR", t_ret), ("TOTAL FINAL A DISPERSAR", t_tot)]
                            for label, val in datos_resumen:
                                pdf.cell(100, 10, label, border=1)
                                pdf.cell(50, 10, f"${val:,.2f}", border=1, ln=True, align='R')

                            return pdf.output(dest='S').encode('latin1')

                        with col_btn1:
                            st.download_button(
                                label="📊 Descargar Conciliación en Excel",
                                data=generar_excel(),
                                file_name=f"Conciliacion_{nombre_empresa_corte}_Semana{semana_corte}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        with col_btn2:
                            st.download_button(
                                label="📄 Descargar Resumen Detallado PDF",
                                data=generar_pdf(),
                                file_name=f"Reporte_Detallado_{nombre_empresa_corte}_Semana{semana_corte}.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.warning("No se encontraron viajes capturados para la selección o periodo indicado.")
            except Exception as e:
                st.error(f"Error al generar la conciliación: {e}")
