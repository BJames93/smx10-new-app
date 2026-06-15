import reflex as rx

config = rx.Config(
    app_name="smx10_new_app",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)