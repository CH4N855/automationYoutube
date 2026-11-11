"""Shared desktop design tokens and theme setup."""
from pathlib import Path
import customtkinter as ctk

COLORS = {'bg': '#0F172A', 'sidebar': '#111B2E', 'surface': '#1B2336', 'raised': '#273449', 'border': '#475569', 'text': '#F8FAFC', 'muted': '#A8B6CA', 'accent': '#E5484D', 'accent_hover': '#BD343C', 'success': '#6EE7B7', 'warning': '#FCD34D', 'danger': '#FDA4AF', 'danger_bg': '#452637', 'secondary': '#334155', 'secondary_hover': '#435570'}

def configure_theme():
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme(str(Path(__file__).with_name("studio-theme.json")))
