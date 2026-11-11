import os
from tkinter import filedialog, messagebox
import customtkinter as ctk
from src.ui.theme import COLORS

from src.folder_watcher import folder_watcher
from src.storage import load_settings, save_settings
import config

class FolderView(ctk.CTkFrame):
    def __init__(self, master, on_queue_change=None):
        super().__init__(master, fg_color="transparent")
        self.on_queue_change = on_queue_change

        self._build_ui()
        folder_watcher.set_callback(self._on_video_detected)

    def _build_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(5, 15))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="Auto-Watch Folder",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Drop video files into a Windows folder to automatically queue them for YouTube posting.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12)
        )
        sub_lbl.pack(anchor="w")

        # Main Card
        card = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        card.pack(fill="x", padx=10, pady=5)

        # Folder location row
        ctk.CTkLabel(card, text="Monitored Directory:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))

        row_f = ctk.CTkFrame(card, fg_color="transparent")
        row_f.pack(fill="x", padx=15, pady=(0, 10))
        row_f.grid_columnconfigure(0, weight=1)
        row_f.grid_columnconfigure(1, weight=0)
        row_f.grid_columnconfigure(2, weight=0)

        self.path_entry = ctk.CTkEntry(row_f, height=40)
        self.path_entry.insert(0, folder_watcher.get_watch_path())
        self.path_entry.configure(state="readonly")
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        change_btn = ctk.CTkButton(
            row_f,
            text="Change...",
            width=80,
            height=40,
            fg_color=COLORS["raised"],
            hover_color=COLORS["secondary_hover"],
            command=self._change_folder
        )
        change_btn.grid(row=0, column=1, padx=(0, 8))

        open_btn = ctk.CTkButton(
            row_f,
            text="Open in Explorer",
            width=120,
            height=40,
            fg_color=COLORS["raised"],
            hover_color=COLORS["secondary_hover"],
            command=self._open_folder
        )
        open_btn.grid(row=0, column=2)

        # Switch Toggle
        self.toggle_var = ctk.BooleanVar(value=folder_watcher.is_active())
        self.toggle_switch = ctk.CTkSwitch(
            card,
            text="Enable Auto-Watch Folder",
            font=ctk.CTkFont(size=14, weight="bold"),
            variable=self.toggle_var,
            command=self._toggle_watcher,
            progress_color=COLORS["accent"]
        )
        self.toggle_switch.pack(anchor="w", padx=15, pady=(10, 8))

        # Instant Auto-Upload switch
        settings = load_settings()
        self.auto_upload_var = ctk.BooleanVar(value=settings.get("watch_folder_auto_upload", True))
        self.auto_upload_switch = ctk.CTkSwitch(
            card,
            text="⚡ Instant Auto-Upload (Publish to YouTube automatically on detection)",
            font=ctk.CTkFont(size=13, weight="bold"),
            variable=self.auto_upload_var,
            command=self._toggle_auto_upload,
            progress_color=COLORS["success"]
        )
        self.auto_upload_switch.pack(anchor="w", padx=15, pady=(0, 15))

        # Explanation box
        info_box = ctk.CTkFrame(card, fg_color=COLORS["bg"], corner_radius=8)
        info_box.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            info_box,
            text="How it works:\n• Whenever you or another script render/export a video into this folder,\n• YouTube Studio Automator waits until the file finishes writing,\n• Automatically extracts the title from the filename and queues it for YouTube!",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            justify="left"
        ).pack(anchor="w", padx=12, pady=10)

        # Activity Log
        log_frame = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(log_frame, text="Activity Log", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))

        self.log_box = ctk.CTkTextbox(log_frame)
        self.log_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.log_box.insert("end", f"[{folder_watcher.get_watch_path()}] Ready to monitor.\n")

    def _change_folder(self):
        folder = filedialog.askdirectory(title="Select Folder to Watch")
        if folder:
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            self.path_entry.configure(state="readonly")
            if folder_watcher.is_active():
                folder_watcher.stop()
                folder_watcher.start(folder)
            self.log_box.insert("end", f"Monitored folder changed to: {folder}\n")

    def _open_folder(self):
        path = self.path_entry.get()
        if os.path.exists(path):
            os.startfile(path)
        else:
            os.makedirs(path, exist_ok=True)
            os.startfile(path)

    def _toggle_auto_upload(self):
        settings = load_settings()
        settings["watch_folder_auto_upload"] = self.auto_upload_var.get()
        save_settings(settings)
        state_str = "Enabled" if self.auto_upload_var.get() else "Disabled"
        self.log_box.insert("end", f" Instant Auto-Upload on video detection is now {state_str}.\n")

    def _toggle_watcher(self):
        if self.toggle_var.get():
            folder_watcher.start(self.path_entry.get())
            self.log_box.insert("end", " Folder Watcher started. Monitoring for incoming videos...\n")
        else:
            folder_watcher.stop()
            self.log_box.insert("end", " Folder Watcher stopped.\n")

    def _on_video_detected(self, video_path: str):
        self.log_box.insert("end", f" Detected new video: {os.path.basename(video_path)} -> Queued for YouTube!\n")
        if self.on_queue_change:
            self.on_queue_change()
