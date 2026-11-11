import sys
import os
import threading
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src.youtube_auth import is_authenticated, get_channel_info
from src.storage import load_queue
from src.scheduler import scheduler
from src.folder_watcher import folder_watcher

from src.ui.theme import COLORS, configure_theme, enable_button_keyboard_navigation

from src.ui.upload_view import UploadView
from src.ui.queue_view import QueueView
from src.ui.folder_view import FolderView
from src.ui.history_view import HistoryView
from src.ui.settings_view import SettingsView
from src.ui.autopilot_view import AutoPilotView
from src.autopilot import autopilot

def create_tray_image(size=(64, 64)):
    """Generate a clean YouTube Red play icon for the Windows system tray."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Red rounded background
    draw.rounded_rectangle([2, 2, size[0] - 2, size[1] - 2], radius=16, fill="#FF0000")
    # White play triangle
    draw.polygon([(24, 18), (24, 46), (46, 32)], fill="#FFFFFF")
    return img

class YouTubeAutomatorApp(ctk.CTk):
    def __init__(self):
        configure_theme()
        super().__init__()

        # Window Setup
        self.title("YouTube Studio Automator - Desktop")
        self.geometry("1240x860")
        self.minsize(1060, 700)

        # Set Dark Appearance
        ctk.set_appearance_mode("Dark")

        # Layout Configuration
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.active_tab = "upload"
        self.views = {}
        self.tray_icon = None

        self._build_sidebar()
        self._build_content_area()

        # Start Background Scheduler Daemon (checks queue every 30s)
        scheduler.start(poll_seconds=30)
        scheduler.set_change_callback(self._on_queue_data_changed)

        # Setup Windows System Tray
        self._setup_system_tray()

        # Window close handler: minimize to tray instead of quitting
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=224, corner_radius=0, fg_color=COLORS["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.pack_propagate(False)
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=24, pady=(32, 24))
        ctk.CTkLabel(brand, text="STUDIO / AUTOMATOR", text_color=COLORS["muted"],
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(brand, text="Create. Publish.",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(brand, text="Your content workspace", text_color=COLORS["muted"]).pack(anchor="w")

        ctk.CTkLabel(self.sidebar, text="WORKSPACE", text_color=COLORS["muted"],
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=24, pady=(8, 8))
        self.nav_btns = {}
        nav_items = [("autopilot", "Auto-Pilot Studio"), ("upload", "New Upload"),
                     ("queue", "Batch & Queue"), ("folder", "Folder Watcher"),
                     ("history", "Upload History"), ("settings", "Settings & Channel")]
        for index, (key, label) in enumerate(nav_items, 1):
            btn = ctk.CTkButton(self.sidebar, text=label, anchor="w", height=44,
                                border_spacing=14, font=ctk.CTkFont(size=14),
                                fg_color="transparent", text_color=COLORS["muted"],
                                hover_color=COLORS["raised"], command=lambda k=key: self.switch_view(k))
            btn.pack(fill="x", padx=12, pady=4)
            self.nav_btns[key] = btn
            self.bind(f"<Control-Key-{index}>", lambda event, k=key: self.switch_view(k))

        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=20)
        self.channel_badge = ctk.CTkFrame(bottom, fg_color=COLORS["surface"], corner_radius=10)
        self.channel_badge.pack(fill="x", pady=(0, 16))
        self.channel_status_lbl = ctk.CTkLabel(self.channel_badge, text="Checking connection...",
                                               font=ctk.CTkFont(size=13, weight="bold"), wraplength=160)
        self.channel_status_lbl.pack(anchor="w", padx=14, pady=(12, 0))
        self.channel_sub_lbl = ctk.CTkLabel(self.channel_badge, text="", text_color=COLORS["muted"],
                                            font=ctk.CTkFont(size=12), wraplength=160)
        self.channel_sub_lbl.pack(anchor="w", padx=14, pady=(0, 12))
        self.sched_status_lbl = ctk.CTkLabel(bottom, text="Scheduler ready", text_color=COLORS["success"],
                                            font=ctk.CTkFont(size=12, weight="bold"))
        self.sched_status_lbl.pack(anchor="w", padx=8)
        ctk.CTkLabel(bottom, text="Ctrl+1-6 to switch pages", text_color=COLORS["muted"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=8)
        ctk.CTkButton(bottom, text="Minimize to tray", height=40, fg_color=COLORS["raised"],
                       command=self.minimize_to_tray).pack(fill="x", pady=(12, 0))
        self.update_channel_badge()

    def _build_content_area(self):
        self.content_container = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=24, pady=24)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # Initialize Views
        self.views["autopilot"] = AutoPilotView(self.content_container, on_upload_success=self._on_upload_event)
        self.views["upload"] = UploadView(self.content_container, on_upload_success=self._on_upload_event)
        self.views["queue"] = QueueView(self.content_container, on_queue_change=self._on_queue_data_changed)
        self.views["folder"] = FolderView(self.content_container, on_queue_change=self._on_queue_data_changed)
        self.views["history"] = HistoryView(self.content_container)
        self.views["settings"] = SettingsView(self.content_container, on_auth_change=self.update_channel_badge)

        self.switch_view("autopilot")

    def switch_view(self, view_key: str):
        self.active_tab = view_key

        for key, btn in self.nav_btns.items():
            if key == view_key:
                btn.configure(fg_color=COLORS["raised"], text_color=COLORS["text"], hover_color=COLORS["secondary_hover"])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["muted"], hover_color=COLORS["raised"])

        for key, view in self.views.items():
            if key == view_key:
                view.grid(row=0, column=0, sticky="nsew")
                if hasattr(view, "refresh_queue"):
                    view.refresh_queue()
                elif hasattr(view, "refresh_history"):
                    view.refresh_history()
            else:
                view.grid_forget()

        enable_button_keyboard_navigation(self)

    def update_channel_badge(self):
        if is_authenticated():
            info = get_channel_info()
            if info and not info.get("error"):
                self.channel_status_lbl.configure(text=f"{info.get('title', 'Connected')}", text_color=COLORS["success"])
                self.channel_sub_lbl.configure(text=f"{info.get('subscriber_count')} subscribers")
            else:
                self.channel_status_lbl.configure(text="Connected", text_color=COLORS["success"])
                self.channel_sub_lbl.configure(text="Channel ready")
        else:
            self.channel_status_lbl.configure(text="Not Connected", text_color=COLORS["danger"])
            self.channel_sub_lbl.configure(text="Click Settings to sign in")

        q_count = len(load_queue())
        self.nav_btns["queue"].configure(text=f"Batch & Queue ({q_count})" if q_count > 0 else "Batch & Queue")

    def _on_queue_data_changed(self):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, self._on_queue_data_changed)
            return
        self.update_channel_badge()
        if "queue" in self.views and hasattr(self.views["queue"], "refresh_queue"):
            self.views["queue"].refresh_queue()

    def _on_upload_event(self):
        self.update_channel_badge()
        if "history" in self.views and hasattr(self.views["history"], "refresh_history"):
            self.views["history"].refresh_history()

    # ----------------- SYSTEM TRAY INTEGRATION -----------------
    def _setup_system_tray(self):
        def tray_worker():
            icon_img = create_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem("▶ Open YouTube Automator", lambda: self.after(0, self.restore_from_tray), default=True),
                pystray.MenuItem(" Scheduler: Active (30s)", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(" Exit Application", lambda: self.after(0, self.exit_app))
            )
            self.tray_icon = pystray.Icon("YouTubeAutomator", icon_img, "YouTube Studio Automator", menu)
            self.tray_icon.run()

        threading.Thread(target=tray_worker, daemon=True).start()

    def minimize_to_tray(self):
        self.withdraw()  # Hide main window
        if self.tray_icon and hasattr(self.tray_icon, "notify"):
            try:
                self.tray_icon.notify("YouTube Automator is running in background.", "Automated Scheduling Active")
            except Exception:
                pass

    def restore_from_tray(self):
        self.deiconify()  # Show main window
        self.lift()
        self.focus_force()

    def exit_app(self):
        scheduler.stop()
        folder_watcher.stop()
        autopilot.stop_daily_automation()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

if __name__ == "__main__":
    app = YouTubeAutomatorApp()
    app.mainloop()
