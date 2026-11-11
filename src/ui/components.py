"""Reusable building blocks shared by desktop views."""
import customtkinter as ctk

from src.ui.theme import COLORS


def add_page_header(parent, title, subtitle, bottom_padding=15):
    """Add the standard title and description to a view."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=10, pady=(5, bottom_padding))
    ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(frame, text=subtitle, text_color=COLORS["muted"],
                 font=ctk.CTkFont(size=12)).pack(anchor="w")
    return frame
