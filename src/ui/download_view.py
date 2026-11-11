"""Desktop controls for downloading a single media URL."""
import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import config
from src.media_downloader import download_video
from src.ui.theme import COLORS


class DownloadView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.events = queue.Queue()
        self.folder = str(config.WATCH_DIR)
        ctk.CTkLabel(self, text="Download media", font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w", padx=12, pady=(8, 4))
        ctk.CTkLabel(self, text="Download and crop the center, enhance color, and speed up to 1.2×.", text_color=COLORS["muted"]).pack(anchor="w", padx=12, pady=(0, 20))
        card = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=12)
        card.pack(fill="x", padx=12)
        ctk.CTkLabel(card, text="Video link", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=24, pady=(24, 6))
        self.url = ctk.CTkEntry(card, placeholder_text="https://...", height=44)
        self.url.pack(fill="x", padx=24)
        ctk.CTkLabel(card, text="Save to", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=24, pady=(18, 6))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=24)
        self.folder_entry = ctk.CTkEntry(row, height=44)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.folder_entry.insert(0, self.folder)
        ctk.CTkButton(row, text="Browse", width=100, height=44, fg_color=COLORS["raised"], command=self._browse).pack(side="left")
        self.button = ctk.CTkButton(card, text="Download video", height=46, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self._start)
        self.button.pack(fill="x", padx=24, pady=(22, 12))
        self.progress = ctk.CTkProgressBar(card, progress_color=COLORS["accent"])
        self.progress.pack(fill="x", padx=24, pady=(0, 8))
        self.progress.set(0)
        self.status = ctk.CTkLabel(card, text="Ready to download one video.", text_color=COLORS["muted"], wraplength=600, justify="left")
        self.status.pack(anchor="w", padx=24, pady=(0, 24))
        self.after(100, self._poll)

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.folder_entry.get() or str(Path.home()))
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)

    def _start(self):
        url, folder = self.url.get().strip(), self.folder_entry.get().strip()
        if not url or not os.path.isdir(folder):
            messagebox.showerror("Download", "Enter a video link and choose an existing folder.")
            return
        self.button.configure(state="disabled")
        self.progress.set(0)
        self.status.configure(text="Preparing download...")

        def worker():
            try:
                title = download_video(url, folder, lambda value, text: self.events.put(("progress", value, text)))
                self.events.put(("done", title, folder))
            except Exception as exc:
                self.events.put(("error", str(exc), None))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind, value, detail = self.events.get_nowait()
                if kind == "progress":
                    if value is not None:
                        self.progress.set(value)
                    self.status.configure(text=detail)
                elif kind == "done":
                    self.progress.set(1)
                    self.status.configure(text=f"Saved {value} to {detail}")
                    self.button.configure(state="normal")
                else:
                    self.status.configure(text=f"Download failed: {value}")
                    self.button.configure(state="normal")
        except queue.Empty:
            pass
        self.after(100, self._poll)
