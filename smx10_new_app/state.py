import reflex as rx
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Conexión
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

class GlobalState(rx.State):
    usuario: str = "" 
    contrasena: str = "" 
    usuario_id: str = ""
    nombre_usuario: str = ""
    is_authenticated: bool = False

    # --- AGREGAMOS LAS FUNCIONES FALTANTES AQUÍ ---
    def set_usuario(self, texto: str):
        self.usuario = texto

    def set_contrasena(self, texto: str):
        self.contrasena = texto
    # ----------------------------------------------

    def login(self): 
        res = supabase.table("usuarios_acceso").select("*").eq("nombre_usuario", self.usuario).eq("contrasena", self.contrasena).execute()
        if len(res.data) > 0:
            self.usuario_id = res.data[0]["user_id"]
            self.nombre_usuario = res.data[0]["nombre_usuario"]
            self.is_authenticated = True
            return rx.redirect("/dashboard")
        else:
            return rx.window_alert("Usuario o contraseña incorrectos")

    def cerrar_sesion(self):
        self.usuario = ""
        self.contrasena = ""
        self.is_authenticated = False
        return rx.redirect("/")