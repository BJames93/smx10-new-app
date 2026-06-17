import reflex as rx

# --- IMPORTACIONES MODULARES ---
from .state import GlobalState 
from .pages.operaciones import operaciones 
from .pages.empresa import empresa
from .pages.conductor import conductor
from .pages.unidad import unidad


# --- 🚘 LA CARROCERÍA (Interfaz Visual) ---
def index() -> rx.Component:
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("Sistema Centralizado para Proveedores", size="6", color="#003366", text_align="center"),
                rx.text("Acceso al Sistema de Operaciones", color="gray", margin_bottom="1em"),
                
                # Inputs conectados a GlobalState
                rx.input(placeholder="Usuario", on_change=GlobalState.set_usuario, bg="black", width="100%"),
                rx.input(placeholder="Contraseña", type="password", on_change=GlobalState.set_contrasena, bg="black", width="100%"),
                
                # Botón conectado a la nueva función login()
                rx.button("Ingresar", on_click=GlobalState.login, bg="#008000", color="white", width="100%", margin_top="1em"),
                
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
            
            # Ahora usamos nombre_usuario que viene directamente de la base de datos
            rx.text("Bienvenido al panel de operaciones, ", rx.text(GlobalState.nombre_usuario, font_weight="bold", color="black"), color="black"),
            
            # Botones de navegación
            rx.hstack(
                rx.button("Cerrar Sesión", on_click=GlobalState.cerrar_sesion, bg="red", color="white"),
                rx.button("Registro de Empresa", on_click=lambda: rx.redirect("/empresa"), bg="#E07512D5", color="white"),
                rx.button("Registra Conductores", on_click=lambda: rx.redirect("/conductor"), bg="#E07512D5", color="white"),
                rx.button("Registra Unidades", on_click=lambda: rx.redirect("/unidad"), bg="#E07512D5", color="white"),
                rx.button("Ir a Operaciones", on_click=lambda: rx.redirect("/operaciones"), bg="#E07512D5", color="white"),
                margin_top="2em",
                spacing="4"
            ),
            align_items="center",
        ),
        bg="#f8f9fa", height="100vh",
    )

# --- 🚀 ARRANQUE DE LA APP ---
app = rx.App(
    theme=rx.theme(
        appearance="light",
        has_background=True,
        radius="large",
        accent_color="blue"
    )
)

app.add_page(index, route="/", title="Login - BoulderBrwn")
app.add_page(dashboard, route="/dashboard", title="Panel Principal")
app.add_page(operaciones, route="/operaciones", title="Registro de Operaciones")
app.add_page(empresa, route="/empresa", title="Registro de Empresa")
app.add_page(unidad, route="/unidad",title ="Registro Unidad")
app.add_page(conductor, route="/conductor", title="Alta de Conductor")
