import reflex as rx
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from .state import AuthState # Agrega esto arriba con los otros import
from .pages.operaciones import operaciones

load_dotenv()

# --- 🔌 CONEXIÓN A SUPABASE ---
url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(url, key)


# --- 🚘 LA CARROCERÍA (Interfaz Visual) ---
def index() -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("Sistema Centralizado para Proveedores", size="6", color="#003366", text_align="center"),
                rx.text("Acceso al Sistema de Operaciones", color="gray", margin_bottom="1em"),
                rx.input(placeholder="Usuario", on_change=AuthState.set_usuario, bg="black", width="100%"),
                rx.input(placeholder="Contraseña", type="password", on_change=AuthState.set_contrasena, bg="black", width="100%"),
                rx.button("Ingresar", on_click=AuthState.procesar_login, bg="#008000", color="white", width="100%", margin_top="1em"),
                rx.cond(AuthState.mensaje_error != "", rx.text(AuthState.mensaje_error, color="red", margin_top="1em", text_align="center")),
                align_items="center",
            ),
            bg="white", padding="2em", width="400px", box_shadow="lg",
        ),
        bg="#f8f9fa", height="100vh",
    )

def dashboard() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Servicio Centralizado de Proveedores", color="#003366"),
            rx.text("Bienvenido al panel de operaciones, ", rx.text(AuthState.usuario, font_weight="bold", color="black"), color="black"),
            rx.button("Cerrar Sesión", on_click=AuthState.cerrar_sesion, bg="red", color="white", margin_top="2em"),
            align_items="center",
        ),
        bg="#f8f9fa", height="100vh",
    )

# --- 🚀 ARRANQUE DE LA APP ---
app = rx.App()
app.add_page(index, route="/", title="Login")
app.add_page(dashboard, route="/dashboard", title="Panel")
app.add_page(operaciones, route="/operaciones", title="Registro de Operaciones") # Esta es la nueva línea