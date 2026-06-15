import reflex as rx
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(url, key)

# --- 🧠 EL CEREBRO (Lógica y Estado) ---
class AuthState(rx.State):
    usuario: str = ""
    contrasena: str = ""
    mensaje_error: str = "" 

    def set_usuario(self, texto: str):
        self.usuario = texto

    def set_contrasena(self, texto: str):
        self.contrasena = texto

    def procesar_login(self):
        self.mensaje_error = ""
        try:
            respuesta = supabase.table("usuarios_acceso").select("*").eq("nombre_usuario", self.usuario).eq("contrasena", self.contrasena).execute()
            if len(respuesta.data) > 0:
                return rx.redirect("/dashboard")
            else:
                self.mensaje_error = "Usuario o contraseña incorrectos"
        except Exception as e:
            self.mensaje_error = "Error al conectar con la base de datos."
            print(f"Error detallado: {e}")

    def cerrar_sesion(self):
        self.usuario = ""
        self.contrasena = ""
        return rx.redirect("/")
