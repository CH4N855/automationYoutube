import threading
from tkinter import messagebox
import customtkinter as ctk
from src.ui.theme import COLORS

from src.autopilot import autopilot
from src.youtube_auth import is_authenticated

class AutoPilotView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_upload_success=None):
        super().__init__(master, fg_color="transparent")
        self.on_upload_success = on_upload_success

        self._build_ui()
        autopilot.set_callback(self._append_log)

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(8, 24))
        ctk.CTkLabel(header, text="YOUR CREATIVE WORKSPACE", text_color=COLORS["muted"],
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text="Auto-Pilot Studio", font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w", pady=(4, 4))
        ctk.CTkLabel(header, text="Turn an idea into your next Short. Keep your channel moving.",
                     text_color=COLORS["muted"], font=ctk.CTkFont(size=14)).pack(anchor="w")

        gen_card = self._card("01 / CREATE", "Make your next Short",
                              "Choose a topic and voice. We will create a script, narration, and vertical video.")
        row = ctk.CTkFrame(gen_card, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(8, 16))
        row.grid_columnconfigure((0, 1), weight=1, uniform="fields")
        for col, label in enumerate(("Content niche", "Narration voice")):
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=col, sticky="w", pady=(0, 8))
        self.niche_menu = ctk.CTkOptionMenu(row, height=44, values=["Space & Science", "Psychology & Motivation", "Unbelievable History", "Productivity & Life Hacks", "Random Viral Facts"])
        self.niche_menu.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        self.voice_menu = ctk.CTkOptionMenu(row, height=44, values=["Ryan (Energetic Male)", "Christopher (Authoritative)", "Jenny (Natural Female)", "Sonia (British Female)"])
        self.voice_menu.grid(row=1, column=1, sticky="ew", padx=(12, 0))
        self.instant_btn = ctk.CTkButton(gen_card, text="⚡ 1-Click Generate & Publish Short (AI Script, Voice, Video & Upload)", height=48,
                                         fg_color="#00C853", hover_color="#00B248",
                                         font=ctk.CTkFont(size=14, weight="bold"), command=self._trigger_instant_generation)
        self.instant_btn.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkLabel(gen_card, text="Publishes publicly when connected. Otherwise, saves to your queue.",
                     text_color=COLORS["muted"], font=ctk.CTkFont(size=12), wraplength=680).pack(anchor="w", padx=24, pady=(0, 20))

        daily = self._card("02 / AUTOMATE", "Build a daily rhythm",
                           "Create and publish one Short each day while this app is running, including in the tray.")
        row = ctk.CTkFrame(daily, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(8, 24))
        row.grid_columnconfigure((0, 1), weight=1, uniform="fields")
        ctk.CTkLabel(row, text="Posting time (this computer's local time)", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.hour_menu = ctk.CTkOptionMenu(row, values=[f"{h:02d}:00 (Hour {h})" for h in range(24)], height=44)
        self.hour_menu.set("18:00 (Hour 18)")
        self.hour_menu.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        self.daily_switch_var = ctk.BooleanVar(value=autopilot.is_active())
        self.daily_switch = ctk.CTkSwitch(row, text="Enable daily publishing", variable=self.daily_switch_var,
                                          command=self._toggle_daily_autopilot, progress_color=COLORS["secondary_hover"],
                                          height=44, font=ctk.CTkFont(size=13))
        self.daily_switch.grid(row=1, column=1, sticky="w", padx=(24, 0))

        log = self._card("03 / ACTIVITY", "Automation activity", "Generation progress and publishing results appear here.")
        self.log_textbox = ctk.CTkTextbox(log, height=140, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_textbox.pack(fill="both", expand=True, padx=24, pady=(8, 24))
        self.log_textbox.insert("end", "Ready when you are. Choose a topic to get started.\n")
        self.log_textbox.configure(state="disabled")

    def _card(self, eyebrow, title, description):
        card = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=12,
                             border_width=1, border_color=COLORS["raised"])
        card.pack(fill="x", padx=12, pady=(0, 16))
        ctk.CTkLabel(card, text=eyebrow, text_color=COLORS["muted"],
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=24)
        ctk.CTkLabel(card, text=description, text_color=COLORS["muted"], justify="left",
                     wraplength=680, font=ctk.CTkFont(size=13)).pack(anchor="w", padx=24, pady=(4, 12))
        return card

    def _trigger_instant_generation(self):
        niche, voice = self.niche_menu.get(), self.voice_menu.get()
        self.instant_btn.configure(state="disabled", text="Creating your Short...")
        self.niche_menu.configure(state="disabled")
        self.voice_menu.configure(state="disabled")

        def complete(res):
            self.instant_btn.configure(state="normal", text="Generate & publish Short")
            self.niche_menu.configure(state="normal")
            self.voice_menu.configure(state="normal")
            if res.get("success"):
                if res.get("url"):
                    messagebox.showinfo("Published", f"Video published to YouTube!\n\nTitle: {res.get('title')}\nURL: {res.get('url')}")
                else:
                    messagebox.showinfo("Queued", f"Video created and added to queue!\nTitle: {res.get('title')}")
                if self.on_upload_success:
                    self.on_upload_success()
            else:
                messagebox.showerror("Generation failed", str(res.get("error")))

        def worker():
            try:
                res = autopilot.generate_and_post_short_now(niche=niche, voice=voice)
            except Exception as exc:
                res = {"success": False, "error": str(exc)}
            self.after(0, lambda: complete(res))

        threading.Thread(target=worker, daemon=True).start()

    def _toggle_daily_autopilot(self):
        if self.daily_switch_var.get():
            hour_str = self.hour_menu.get().split(":")[0]
            try:
                hour = int(hour_str)
            except Exception:
                hour = 18
            niche = self.niche_menu.get()
            voice = self.voice_menu.get()
            autopilot.start_daily_automation(post_hour=hour, niche=niche, voice=voice)
        else:
            autopilot.stop_daily_automation()

    def _append_log(self, text: str):
        def append():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{text}\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, append)
