from rich.console import Console
from rich.theme import Theme

# Define your custom theme
custom_theme = Theme(
    {
        "success": "bold green",
        "error": "bold red",
        "info": "cyan",
        "warning": "bold yellow",
        "highlight": "bold magenta",
        "health.good": "bold green",
        "health.bad": "bold red",
        "url": "blue underline",
        "env.prod": "bold red",
        "env.dev": "yellow",
        "env.local": "green",
        "env.custom": "cyan",
        "bnl.teal": "#105c78",
        "bnl.cerulean": "#00addc",
        "bnl.lime": "#b2d33b",
        "bnl.orange": "#f68b1f",
        "bnl.fuchsia": "#b72467",
        "bnl.goldenrod": "#ffcd34",
        "bnl.crimson": "#db3526",
        "bnl.violet": "#51499e",
        "bnl.cornflower": "#4881c3",
        "bnl.jade": "#25b574",
    }
)

# Instantiate the console with the theme
console = Console(theme=custom_theme)


# Utility functions for printing
def success(message: str):
    console.print(message, style="success")


def error(message: str):
    console.print(message, style="error")


def info(message: str):
    console.print(message, style="info")


def warning(message: str):
    console.print(message, style="warning")


def highlight(message: str):
    console.print(message, style="highlight")
