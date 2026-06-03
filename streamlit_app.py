import streamlit as st
from supabase import create_client, Client

# 1. Configuración de la página
st.set_page_config(page_title="Mi Nueva App", page_icon="🚀", layout="wide")

# 2. Función para conectar a Supabase (usamos caché para no saturar la conexión)
@st.cache_resource
def init_connection() -> Client:
    # Lee las claves desde los secretos de Streamlit
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# 3. Inicializar la conexión
try:
    supabase = init_connection()
    st.success("¡Conexión exitosa a Supabase! 🟢")
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")

# Aquí abajo ya puedes empezar a construir tus st.tabs y formularios...
st.write("¡Bienvenido a la nueva aplicación!")