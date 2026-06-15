import reflex as rx
from ..state import AuthState, supabase

def operaciones() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Registro de Operaciones", color="#003366"),
            rx.text(f"Capturando datos para: {AuthState.usuario}"),
            
            # Aquí irá nuestro formulario que conectaremos a Supabase
            rx.button("Volver al Dashboard", on_click=lambda: rx.redirect("/dashboard")),
            spacing="5",
        ),
        padding="2em",
    )