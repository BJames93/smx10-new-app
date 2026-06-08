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
            if not nombre_empresa or not nombre_rl:
                st.error("Por favor completa los campos obligatorios (Nombre de la empresa y Representante Legal).")
            else:
                # Forzamos mayúsculas
                empresa_upper = nombre_empresa.upper()
                
                datos_empresa = {
                    "nombre_empresa": empresa_upper,
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
                sel = st.selectbox("Seleccione Conductor:", [""] + df['nombre_driver'].tolist())
                
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
                            docs = {
                                "CURP": "url_curp",
                                "INE": "url_ine",
                                "Constancia Fiscal": "url_constancia_fiscal", "Licencia de Conducir": "url_licencia",
                                "Comprobante Domicilio": "url_comprobante_domicilio", "Carátula Bancaria": "url_caratula_bancaria",
                                "Examen Toxicológico": "url_toxicologico"
                            }
                            
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
        except Exception as e:
            st.error(f"Error cargando conductores: {e}")

    else:
        try:
            res = supabase.table("unidades").select("*").execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                df['placas'] = df['placas'].fillna("").astype(str)
                sel = st.selectbox("Seleccione Placas de la Unidad:", [""] + df['placas'].tolist())
                
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
        res = supabase.table("alta_conductor").select("*").eq("rfc", rfc_busqueda.upper()).execute()
        
        if res.data:
            reg = res.data[0]
            st.write(f"Conductor encontrado: **{reg['nombre_driver']}**")
            st.write(f"Celular actual: **{reg.get('celular', 'No registrado')}**")
            banco_actual = reg.get('nombre_banco') or 'No registrado'
            clabe_actual = reg.get('clabe_interbancaria') or 'No registrado'
            st.write(f"Banco actual: **{banco_actual}** | CLABE actual: **{clabe_actual}**")
            
            st.write("---")
            st.write("Estado de documentos actuales:")
            docs_map = {
                "CURP": "url_curp",
                "INE": "url_ine",
                "Constancia Fiscal": "url_constancia_fiscal", "Licencia de Conducir": "url_licencia",
                "Comprobante Domicilio": "url_comprobante_domicilio", "Carátula Bancaria": "url_caratula_bancaria",
                "Examen Toxicológico": "url_toxicologico"
            }
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
                    st.success("¡Celular actualizado correctamente! Recarga la página para ver el cambio.")
            
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
                        st.success("¡Datos bancarios actualizados correctamente! Recarga la página para ver el cambio.")
            
            elif opcion in docs_map:
                archivo_nuevo = st.file_uploader(f"Cargar nuevo archivo de {opcion}")
                if st.button("Guardar actualización"):
                    if archivo_nuevo:
                        columna_db = docs_map[opcion]
                        nombre_carpeta = opcion.lower().replace(" ", "_")
                        ruta_storage = f"conductores/{nombre_carpeta}s"
                        
                        nueva_url = procesar_archivo(archivo_nuevo, ruta_storage, rfc_busqueda.upper())
                        
                        supabase.table("alta_conductor").update({columna_db: nueva_url}).eq("rfc", rfc_busqueda.upper()).execute()
                        st.success(f"¡{opcion} actualizado correctamente! Recarga la página para ver el cambio.")
                    else:
                        st.warning("Por favor selecciona un archivo.")
        else:
            st.error("No se encontró ningún conductor con ese RFC.")

# ==========================================
# PESTAÑA 6: REGISTRO DE OPERACIÓN
# ==========================================
with tab6:
    st.header("Captura Dinámica de Despacho Operativo")
    st.write("Módulo relacional. Permite enlazar los conductores y unidades activos en sistema.")
    
    dict_conductores = {}
    dict_unidades = {}
    
    try:
        conductores_db = supabase.table("alta_conductor").select("id_conductor, nombre_driver").execute().data
        unidades_db = supabase.table("unidades").select("id_unidad, placas").execute().data
        
        dict_conductores = {c["nombre_driver"]: c["id_conductor"] for c in conductores_db}
        dict_unidades = {u["placas"]: u["id_unidad"] for u in unidades_db}
    except Exception as e:
        st.error(f"Error de sincronización con Supabase: {e}")

    if not dict_conductores or not dict_unidades:
        st.warning("⚠️ Atención: Debes tener conductores y unidades registrados para operar.")
    else:
        with st.form("form_operacion", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                tipo_cliente = st.selectbox("Tipo de Cliente *", options=["", "Mercado Libre", "Amazon"])
                sel_conductor = st.selectbox("Seleccione el Conductor asignado *", options=[""] + list(dict_conductores.keys()))
                sel_unidad = st.selectbox("Seleccione las Placas del Vehículo *", options=[""] + list(dict_unidades.keys()))
                status_operacion = st.selectbox("Estatus del Servicio", options=["En ruta", "Cancelacion", "No show"])
            
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
                        "tipo_cliente": tipo_cliente, 
                        "conductor_id": dict_conductores[sel_conductor],
                        "unidad_id": dict_unidades[sel_unidad],
                        "status_operacion": status_operacion,
                        "hora_llegada_hub": iso_llegada,
                        "hora_salida_hub": iso_salida,
                        "paquetes_cargados": int(paquetes),
                        "paradas": int(paradas)
                    }
                    
                    try:
                        supabase.table("registro_operacion").insert(datos_operacion).execute()
                        st.success(f"¡Viaje de {tipo_cliente} despachado correctamente!")
                    except Exception as e:
                        st.error(f"Error al registrar la operación en base de datos: {e}")

# ===============================================
# PESTAÑA 7: VERIFICACION DE CAPTURA
# ===============================================
with tab7:
    st.header("📊 Verificación de Captura")
    st.write("Consulta y verifica los despachos operativos registrados en el sistema.")
    
    c_ini, c_fin = st.columns(2)
    with c_ini:
        fecha_inicio = st.date_input("Fecha de Inicio")
    with c_fin:
        fecha_fin = st.date_input("Fecha de Término")
        
    if st.button("Buscar Capturas"):
        try:
            res_op = supabase.table("registro_operacion").select("*").execute()
            df_op = pd.DataFrame(res_op.data)
            
            if not df_op.empty:
                cond_db = supabase.table("alta_conductor").select("id_conductor, nombre_driver").execute().data
                unid_db = supabase.table("unidades").select("id_unidad, placas, tipo_unidad").execute().data
                
                map_cond = {c["id_conductor"]: c["nombre_driver"] for c in cond_db}
                map_unid = {u["id_unidad"]: u["placas"] for u in unid_db}
                map_tipo_unid = {u["id_unidad"]: u.get("tipo_unidad", "N/A") for u in unid_db}
                
                df_op["Conductor"] = df_op["conductor_id"].map(map_cond)
                df_op["Placas"] = df_op["unidad_id"].map(map_unid)
                df_op["Tipo Unidad"] = df_op["unidad_id"].map(map_tipo_unid) 
                
                df_op["hora_llegada_hub"] = pd.to_datetime(df_op["hora_llegada_hub"]).dt.tz_localize(None)
                
                mascara = (df_op["hora_llegada_hub"].dt.date >= fecha_inicio) & (df_op["hora_llegada_hub"].dt.date <= fecha_fin)
                df_filtrado = df_op.loc[mascara].copy()
                
                if not df_filtrado.empty:
                    df_filtrado["hora_llegada_hub"] = df_filtrado["hora_llegada_hub"].dt.strftime('%Y-%m-%d %H:%M')
                    
                    st.write("---")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total de Viajes", len(df_filtrado))
                    m2.metric("Paquetes Procesados", int(df_filtrado["paquetes_cargados"].sum()))
                    m3.metric("Paradas Planificadas", int(df_filtrado["paradas"].sum()))
                    st.write("---")
                    
                    df_mostrar = df_filtrado[[
                        "hora_llegada_hub", 
                        "Conductor", 
                        "Placas", 
                        "Tipo Unidad",       
                        "tipo_cliente",      
                        "status_operacion", 
                        "paquetes_cargados", 
                        "paradas"
                    ]].rename(columns={
                        "hora_llegada_hub": "Hora de Arribo",
                        "tipo_cliente": "Cliente",
                        "status_operacion": "Condición",
                        "paquetes_cargados": "Paquetes",
                        "paradas": "Paradas"
                    })
                    
                    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                    
                else:
                    st.warning(f"No se encontraron capturas registradas entre {fecha_inicio} y {fecha_fin}.")
            else:
                st.info("Aún no hay registros de operaciones en la base de datos.")
                
        except Exception as e:
            st.error(f"Error al generar la consulta: {e}")
