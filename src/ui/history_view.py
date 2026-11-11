import webbrowser
from tkinter import messagebox
import customtkinter as ctk
from src.ui.theme import COLORS
from src.ui.components import add_page_header

from src.storage import load_history, clear_history

class HistoryView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self._build_ui()

    def _build_ui(self):
        add_page_header(self, "Upload History",
                        "Log of previously published videos and direct YouTube URLs.", bottom_padding=10)

        # Top Bar
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=5)

        self.count_lbl = ctk.CTkLabel(top_bar, text="Total Uploads: 0", font=ctk.CTkFont(size=13, weight="bold"))
        self.count_lbl.pack(side="left")

        clear_btn = ctk.CTkButton(
            top_bar,
            text="Clear History",
            width=110,
            height=40,
            fg_color=COLORS["danger_bg"],
            hover_color=COLORS["danger_bg"],
            command=self._clear_history
        )
        clear_btn.pack(side="right")

        # Scrollable list
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"])
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.refresh_history()

    def refresh_history(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        history = load_history()
        self.count_lbl.configure(text=f"Total Uploads: {len(history)}")

        if not history:
            no_lbl = ctk.CTkLabel(
                self.scroll_frame,
                text="No upload history yet.\nVideos uploaded will appear here with direct YouTube links.",
                text_color=COLORS["muted"],
                font=ctk.CTkFont(size=13)
            )
            no_lbl.pack(pady=40)
            return

        for item in history:
            card = ctk.CTkFrame(self.scroll_frame, fg_color=COLORS["surface"], corner_radius=8)
            card.pack(fill="x", padx=5, pady=5)
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)

            # Info
            info_f = ctk.CTkFrame(card, fg_color="transparent")
            info_f.grid(row=0, column=0, sticky="w", padx=15, pady=10)

            ctk.CTkLabel(
                info_f,
                text=item.get("title", "Untitled"),
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(anchor="w")

            meta = f"ID: {item.get('video_id')}  |  Privacy: {item.get('privacy_status')}  |  Published: {item.get('published_at', '')[:19]}"
            ctk.CTkLabel(
                info_f,
                text=meta,
                text_color=COLORS["muted"],
                font=ctk.CTkFont(size=12)
            ).pack(anchor="w", pady=(2, 0))

            # Action
            action_f = ctk.CTkFrame(card, fg_color="transparent")
            action_f.grid(row=0, column=1, sticky="e", padx=15, pady=10)

            url = item.get("url")
            if url:
                watch_btn = ctk.CTkButton(
                    action_f,
                    text="▶ Watch on YouTube",
                    width=140,
                    height=40,
                    fg_color=COLORS["accent"],
                    hover_color=COLORS["accent_hover"],
                    command=lambda u=url: webbrowser.open(u)
                )
                watch_btn.pack(side="right")

    def _clear_history(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear upload history?"):
            clear_history()
            self.refresh_history()
