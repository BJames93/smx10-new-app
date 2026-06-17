import reflex as rx
# Cambiamos la ruta para que apunte al nuevo archivo state.py y use GlobalState
from ..state import GlobalState, supabase 

def operaciones() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.heading("Registro de Operaciones", color="#003366"),
            # Actualizamos aquí también el nombre de la variable
            rx.text(f"Capturando datos para: {GlobalState.nombre_usuario}"),
            
            rx.button("Volver al Dashboard", on_click=lambda: rx.redirect("/dashboard")),
            spacing="5",
        ),
        padding="2em",
    )