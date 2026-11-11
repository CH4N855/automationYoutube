import os
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from src.ui.theme import COLORS

import config
from src.youtube_auth import (
    is_authenticated, has_client_secret, import_client_secret,
    authenticate_interactive, logout, get_channel_info
)
from src.storage import load_settings, save_settings

class SettingsView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_auth_change=None):
        super().__init__(master, fg_color="transparent")
        self.on_auth_change = on_auth_change

        self._build_ui()

    def _build_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(5, 15))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="YouTube Channel & Settings",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Manage YouTube API credentials, channel authentication, and upload presets.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12)
        )
        sub_lbl.pack(anchor="w")

        # ----------------- SECTION 1: Channel Connection -----------------
        self.auth_card = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        self.auth_card.pack(fill="x", padx=10, pady=5)
        self.refresh_channel_status()

        # ----------------- SECTION 2: Presets & Defaults -----------------
        presets_card = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        presets_card.pack(fill="x", padx=10, pady=15)

        ctk.CTkLabel(
            presets_card,
            text="Upload Defaults & Presets",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        settings = load_settings()

        # Category, Privacy & Default Format
        row_opts = ctk.CTkFrame(presets_card, fg_color="transparent")
        row_opts.pack(fill="x", padx=15, pady=5)
        row_opts.grid_columnconfigure(0, weight=1)
        row_opts.grid_columnconfigure(1, weight=1)
        row_opts.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(row_opts, text="Default Category", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        cat_names = list(config.YOUTUBE_CATEGORIES.values())
        cur_cat = config.YOUTUBE_CATEGORIES.get(settings.get("default_category_id", "22"), "People & Blogs")
        self.def_cat_menu = ctk.CTkOptionMenu(row_opts, values=cat_names, height=40)
        self.def_cat_menu.set(cur_cat)
        self.def_cat_menu.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        ctk.CTkLabel(row_opts, text="Default Privacy", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=1, sticky="w")
        self.def_priv_menu = ctk.CTkOptionMenu(row_opts, values=["public", "unlisted", "private"], height=40)
        self.def_priv_menu.set(settings.get("default_privacy", "public"))
        self.def_priv_menu.grid(row=1, column=1, sticky="ew", padx=(4, 4))

        ctk.CTkLabel(row_opts, text="Default Format", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=2, sticky="w")
        self.def_fmt_menu = ctk.CTkOptionMenu(row_opts, values=["Auto-Detect", "YouTube Shorts (<60s)", "YouTube Long Video"], height=40)
        self.def_fmt_menu.set(settings.get("default_video_format", "Auto-Detect"))
        self.def_fmt_menu.grid(row=1, column=2, sticky="ew", padx=(4, 0))

        # Default Tags
        ctk.CTkLabel(presets_card, text="Default Tags (comma separated)", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(10, 2))
        self.def_tags_entry = ctk.CTkEntry(presets_card, height=40)
        self.def_tags_entry.insert(0, ", ".join(settings.get("default_tags", ["automation", "youtube"])))
        self.def_tags_entry.pack(fill="x", padx=15, pady=(0, 10))

        # Default Description Footer
        ctk.CTkLabel(presets_card, text="Default Description Footer (Social links, disclaimers, etc.)", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(5, 2))
        self.def_footer_box = ctk.CTkTextbox(presets_card, height=90)
        self.def_footer_box.insert("1.0", settings.get("default_description_footer", ""))
        self.def_footer_box.pack(fill="x", padx=15, pady=(0, 10))

        # Made for Kids
        self.def_kids_var = ctk.BooleanVar(value=settings.get("default_made_for_kids", False))
        ctk.CTkCheckBox(
            presets_card,
            text="Default to Made for Kids (COPPA)",
            variable=self.def_kids_var
        ).pack(anchor="w", padx=15, pady=(5, 15))

        # Save Presets Button
        save_btn = ctk.CTkButton(
            presets_card,
            text="Save Presets",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=40,
            command=self._save_presets
        )
        save_btn.pack(fill="x", padx=15, pady=(0, 15))

    def refresh_channel_status(self):
        for widget in self.auth_card.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.auth_card,
            text="Channel Connection & OAuth",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        if is_authenticated():
            channel = get_channel_info()
            if channel and not channel.get("error"):
                ctk.CTkLabel(
                    self.auth_card,
                    text=f"Connected as: {channel.get('title')}",
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color=COLORS["success"]
                ).pack(anchor="w", padx=15, pady=2)

                stats_str = f" Subscribers: {channel.get('subscriber_count')}  |   Videos: {channel.get('video_count')}  |   Views: {channel.get('view_count')}"
                ctk.CTkLabel(
                    self.auth_card,
                    text=stats_str,
                    text_color=COLORS["muted"],
                    font=ctk.CTkFont(size=12)
                ).pack(anchor="w", padx=15, pady=(0, 12))

                logout_btn = ctk.CTkButton(
                    self.auth_card,
                    text="Disconnect Channel",
                    width=150,
                    height=40,
                    fg_color=COLORS["danger_bg"],
                    hover_color=COLORS["danger_bg"],
                    command=self._logout
                )
                logout_btn.pack(anchor="w", padx=15, pady=(0, 15))
            else:
                ctk.CTkLabel(self.auth_card, text="Connected, but channel details could not be retrieved.").pack(anchor="w", padx=15)
        else:
            ctk.CTkLabel(
                self.auth_card,
                text="Channel Not Connected",
                text_color=COLORS["danger"],
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w", padx=15, pady=2)

            ctk.CTkLabel(
                self.auth_card,
                text="Step 1: Import client_secret.json (from Google Cloud Console)\nStep 2: Authorize with your Google Account.",
                text_color=COLORS["muted"],
                justify="left"
            ).pack(anchor="w", padx=15, pady=5)

            btn_row = ctk.CTkFrame(self.auth_card, fg_color="transparent")
            btn_row.pack(fill="x", padx=15, pady=(5, 15))

            import_btn = ctk.CTkButton(
                btn_row,
                text="Import client_secret.json...",
                command=self._import_secret,
                height=40,
                fg_color=COLORS["raised"],
                hover_color=COLORS["secondary_hover"]
            )
            import_btn.pack(side="left", padx=(0, 10))

            auth_btn = ctk.CTkButton(
                btn_row,
                text="Authorize YouTube Account",
                command=self._start_auth,
                height=40,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"]
            )
            auth_btn.pack(side="left")

    def _import_secret(self):
        path = filedialog.askopenfilename(
            title="Select client_secret.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if path:
            if import_client_secret(path):
                messagebox.showinfo("Success", "client_secret.json successfully imported! Now click 'Authorize YouTube Account'.")
            else:
                messagebox.showerror("Error", "Invalid client secret JSON format. Ensure it's a valid OAuth 2.0 Client credentials file.")

    def _start_auth(self):
        if not has_client_secret():
            messagebox.showerror("Error", "Please import client_secret.json first.")
            return

        def worker():
            success, msg = authenticate_interactive()
            if success:
                messagebox.showinfo("Success", msg)
                self.refresh_channel_status()
                if self.on_auth_change:
                    self.on_auth_change()
            else:
                messagebox.showerror("Auth Error", msg)

        threading.Thread(target=worker, daemon=True).start()

    def _logout(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to disconnect your YouTube channel?"):
            logout()
            self.refresh_channel_status()
            if self.on_auth_change:
                self.on_auth_change()

    def _save_presets(self):
        cat_id = config.CATEGORY_NAME_TO_ID.get(self.def_cat_menu.get(), "22")
        priv = self.def_priv_menu.get()
        tags = [t.strip() for t in self.def_tags_entry.get().split(",") if t.strip()]
        footer = self.def_footer_box.get("1.0", "end-1c")
        kids = self.def_kids_var.get()

        settings = load_settings()
        settings.update({
            "default_category_id": cat_id,
            "default_privacy": priv,
            "default_video_format": self.def_fmt_menu.get(),
            "default_tags": tags,
            "default_description_footer": footer,
            "default_made_for_kids": kids
        })
        save_settings(settings)
        messagebox.showinfo("Saved", "Default upload presets saved successfully!")
