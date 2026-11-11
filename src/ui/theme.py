"""Shared desktop design tokens and theme setup."""
from pathlib import Path
import customtkinter as ctk

COLORS = {'bg': '#101114',
 'sidebar': '#17181D',
 'surface': '#1D1F25',
 'raised': '#2B2E37',
 'border': '#454954',
 'text': '#F8FAFC',
 'muted': '#A8B6CA',
 'accent': '#E94E58',
 'accent_hover': '#C83C48',
 'success': '#6EE7B7',
 'warning': '#FCD34D',
 'danger': '#FDA4AF',
 'danger_bg': '#452637',
 'secondary': '#334155',
 'secondary_hover': '#435570'}

def configure_theme():
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme(str(Path(__file__).with_name("studio-theme.json")))


def enable_button_keyboard_navigation(root):
    """Make canvas-based buttons reachable by Tab with a visible focus border."""
    for widget in root.winfo_children():
        if isinstance(widget, ctk.CTkButton) and not getattr(widget, "_studio_keyboard_ready", False):
            widget._studio_keyboard_ready = True
            original_width = widget.cget("border_width")
            original_color = widget.cget("border_color")
            widget._canvas.configure(takefocus=1)
            widget._canvas.bind("<FocusIn>", lambda event, button=widget: button.configure(
                border_width=2, border_color=COLORS["text"]), add="+")
            widget._canvas.bind("<FocusOut>", lambda event, button=widget, width=original_width, color=original_color: button.configure(
                border_width=width, border_color=color), add="+")
            for key in ("<Return>", "<space>"):
                widget._canvas.bind(key, lambda event, button=widget: button.invoke(), add="+")
        enable_button_keyboard_navigation(widget)
