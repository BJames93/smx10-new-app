import reflex as rx
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL") or "https://ejemplo.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or "llave_falsa"

# Conexión
supabase: Client = create_client(os.environ.get("SUPABASE_URL") or "", os.environ.get("SUPABASE_KEY") or "")

class GlobalState(rx.State):
    usuario: str = "" 
    contrasena: str = "" 
    usuario_id: str = ""
    nombre_usuario: str = ""
    is_authenticated: bool = False

    def on_load(self):
        """
        Esta función se ejecuta al cargar la app.
        Por ahora está vacía para evitar bloqueos en el arranque del servidor.
        """
        pass

    def set_usuario(self, texto: str):
        self.usuario = texto

    def set_contrasena(self, texto: str):
        self.contrasena = texto

    def login(self): 
        # Aseguramos que la conexión esté lista antes de la consulta
        try:
            res = supabase.table("usuarios_acceso").select("*").eq("nombre_usuario", self.usuario).eq("contrasena", self.contrasena).execute()
            if len(res.data) > 0:
                self.usuario_id = res.data[0]["user_id"]
                self.nombre_usuario = res.data[0]["nombre_usuario"]
                self.is_authenticated = True
                return rx.redirect("/dashboard")
            else:
                return rx.window_alert("Usuario o contraseña incorrectos")
        except Exception as e:
            return rx.window_alert(f"Error de conexión: {str(e)}")

    def cerrar_sesion(self):
        self.usuario = ""
        self.contrasena = ""
        self.is_authenticated = False
        return rx.redirect("/")