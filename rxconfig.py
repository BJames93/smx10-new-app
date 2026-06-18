import reflex as rx

config = rx.Config(
    app_name="smx10_new_app",
    
    web_port=3000,
    requirements=[
        "supabase",
        "python-dotenv",
    ],
)