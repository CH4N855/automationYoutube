import os
import threading
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox
import customtkinter as ctk
from src.ui.theme import COLORS
from src.ui.components import add_page_header

from src.storage import load_queue, remove_from_queue
from src.scheduler import scheduler
from src.youtube_auth import is_authenticated
import config

class QueueView(ctk.CTkFrame):
    def __init__(self, master, on_queue_change=None):
        super().__init__(master, fg_color="transparent")
        self.on_queue_change = on_queue_change
        self.batch_video_paths = []

        self._build_ui()

    def _build_ui(self):
        add_page_header(self, "Batch & Queue Manager",
                        "Monitor scheduled uploads and bulk-schedule videos with automated release intervals.", bottom_padding=10)

        # Tabview for Queue vs Batch Auto-Scheduler
        self.tabview = ctk.CTkTabview(self, fg_color=COLORS["surface"])
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)

        self.tab_queue = self.tabview.add("Active Queue")
        self.tab_batch = self.tabview.add("Bulk Auto-Scheduler")

        self._build_queue_tab()
        self._build_batch_tab()

    def _build_queue_tab(self):
        top_bar = ctk.CTkFrame(self.tab_queue, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(5, 10))

        self.queue_count_lbl = ctk.CTkLabel(
            top_bar,
            text="Queued Videos: 0",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.queue_count_lbl.pack(side="left")

        self.upload_all_btn = ctk.CTkButton(
            top_bar,
            text="⚡ Upload All in Queue",
            width=160,
            command=self._upload_all_now,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.upload_all_btn.pack(side="right", padx=(5, 0))

        refresh_btn = ctk.CTkButton(
            top_bar,
            text="Refresh",
            width=80,
            command=self.refresh_queue,
            fg_color=COLORS["raised"],
            hover_color=COLORS["secondary_hover"]
        )
        refresh_btn.pack(side="right", padx=(5, 5))

        # Scrollable list for cards
        self.queue_scroll = ctk.CTkScrollableFrame(self.tab_queue, fg_color=COLORS["bg"])
        self.queue_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self.refresh_queue()

    def refresh_queue(self):
        # Clear existing card widgets
        for widget in self.queue_scroll.winfo_children():
            widget.destroy()

        queue = load_queue()
        self.queue_count_lbl.configure(text=f"Queued Videos: {len(queue)}")

        if not queue:
            no_lbl = ctk.CTkLabel(
                self.queue_scroll,
                text="The queue is currently empty.\nAdd videos from 'New Upload' or 'Bulk Auto-Scheduler'.",
                text_color=COLORS["muted"],
                font=ctk.CTkFont(size=13)
            )
            no_lbl.pack(pady=40)
            return

        for item in queue:
            card = ctk.CTkFrame(self.queue_scroll, fg_color=COLORS["surface"], corner_radius=8)
            card.pack(fill="x", padx=5, pady=5)
            card.grid_columnconfigure(0, weight=1)
            card.grid_columnconfigure(1, weight=0)

            # Left Info
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=16)

            title_text = item.get("title", "Untitled")
            status = item.get("status", "queued").upper()
            status_color = {
                "QUEUED": COLORS["warning"], "SCHEDULED": COLORS["warning"],
                "UPLOADING": COLORS["muted"], "UPLOADED": COLORS["success"],
            }.get(status, COLORS["danger"])

            ctk.CTkLabel(info_frame, text=status, text_color=status_color,
                         font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")

            title_label = ctk.CTkLabel(
                info_frame,
                text=title_text,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w", justify="left", wraplength=420
            )
            title_label.pack(anchor="w")

            filename = os.path.basename(item.get("video_path", ""))
            sched_time = item.get("scheduled_time") or "Immediate"
            meta_str = f"{filename}  |  Scheduled: {sched_time}  |  Privacy: {item.get('privacy_status')}"
            meta_label = ctk.CTkLabel(
                info_frame,
                text=meta_str,
                text_color=COLORS["muted"],
                font=ctk.CTkFont(size=12),
                anchor="w", justify="left", wraplength=420
            )
            meta_label.pack(anchor="w", pady=(4, 0))
            labels = [title_label, meta_label]
            if item.get("error_message"):
                error_label = ctk.CTkLabel(
                    info_frame, text=f"Last attempt: {item['error_message']}",
                    text_color=COLORS["danger"], justify="left", wraplength=420,
                    font=ctk.CTkFont(size=12))
                error_label.pack(anchor="w", pady=(8, 0))
                labels.append(error_label)
            info_frame.bind("<Configure>", lambda event, targets=labels: [
                label.configure(wraplength=max(160, event.width - 8)) for label in targets])

            # Right actions
            action_frame = ctk.CTkFrame(card, fg_color="transparent")
            action_frame.grid(row=0, column=1, sticky="e", padx=12, pady=10)

            up_btn = ctk.CTkButton(
                action_frame,
                text="Retry upload" if status == "FAILED" else "Upload now",
                width=100,
                height=40,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                command=lambda i=item["id"]: self._upload_single_now(i)
            )
            up_btn.pack(side="left", padx=5)
            if status == "UPLOADING":
                up_btn.configure(state="disabled", text="Uploading...")

            del_btn = ctk.CTkButton(
                action_frame,
                text="Remove",
                width=80,
                height=40,
                fg_color=COLORS["danger_bg"],
                hover_color=COLORS["danger_bg"],
                command=lambda i=item["id"]: self._remove_item(i)
            )
            del_btn.pack(side="left", padx=5)
            if status == "UPLOADING":
                del_btn.configure(state="disabled")

    def _upload_all_now(self):
        queue = load_queue()
        pending = [it for it in queue if it.get("status") in ["queued", "failed"]]
        if not pending:
            messagebox.showinfo("Queue Empty", "No pending or failed videos in queue to upload.")
            return

        if not is_authenticated():
            messagebox.showerror("Error", "YouTube account is not connected. Go to 'Settings & Channel' to connect.")
            return

        self.upload_all_btn.configure(state="disabled", text="Uploading Queue...")

        def worker():
            for item in pending:
                scheduler.process_item(item["id"])
                self.after(0, self.refresh_queue)

            def done():
                self.upload_all_btn.configure(state="normal", text="⚡ Upload All in Queue")
                self.refresh_queue()
                if self.on_queue_change:
                    self.on_queue_change()
                messagebox.showinfo("Success", "All videos in queue have been processed!")

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _upload_single_now(self, item_id: str):
        def complete(res):
            if res.get("success"):
                messagebox.showinfo("Success", "Video uploaded successfully!")
            else:
                messagebox.showerror("Error", f"Upload failed: {res.get('error')}")
            self.refresh_queue()
            if self.on_queue_change:
                self.on_queue_change()

        def worker():
            res = scheduler.process_item(item_id)
            self.after(0, lambda: complete(res))

        threading.Thread(target=worker, daemon=True).start()

    def _remove_item(self, item_id: str):
        remove_from_queue(item_id)
        self.refresh_queue()
        if self.on_queue_change:
            self.on_queue_change()

    def _build_batch_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_batch, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # File picker
        pick_btn = ctk.CTkButton(
            container,
            text="Select Multiple Video Files...",
            command=self._choose_batch_files,
            height=40,
            fg_color=COLORS["raised"],
            hover_color=COLORS["secondary_hover"]
        )
        pick_btn.pack(fill="x", pady=5)

        self.batch_files_lbl = ctk.CTkLabel(
            container,
            text="No files selected",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12)
        )
        self.batch_files_lbl.pack(anchor="w", pady=(0, 10))

        # Metadata options
        ctk.CTkLabel(container, text="Base Video Title", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(5, 2))
        self.batch_title_entry = ctk.CTkEntry(container, placeholder_text="Daily Automation Video", height=40)
        self.batch_title_entry.insert(0, "Daily Automation Series")
        self.batch_title_entry.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(container, text="Description", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(5, 2))
        self.batch_desc_entry = ctk.CTkTextbox(container, height=80)
        self.batch_desc_entry.insert("1.0", "New episode automated with YouTube Studio Automator.\nSubscribe for more!")
        self.batch_desc_entry.pack(fill="x", pady=(0, 8))

        # Timing
        row_time = ctk.CTkFrame(container, fg_color="transparent")
        row_time.pack(fill="x", pady=5)
        row_time.grid_columnconfigure(0, weight=1)
        row_time.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row_time, text="Start Release Date/Time (UTC)", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        self.batch_start_entry = ctk.CTkEntry(row_time, height=40)
        suggest_start = datetime.now() + timedelta(hours=2)
        self.batch_start_entry.insert(0, suggest_start.strftime("%Y-%m-%d %H:%M"))
        self.batch_start_entry.grid(row=1, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkLabel(row_time, text="Interval Between Uploads (Hours)", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=1, sticky="w")
        self.batch_interval_entry = ctk.CTkEntry(row_time, height=40)
        self.batch_interval_entry.insert(0, "24")
        self.batch_interval_entry.grid(row=1, column=1, sticky="ew", padx=(5, 0))

        # Action Button
        schedule_all_btn = ctk.CTkButton(
            container,
            text="Auto-Schedule All to Queue",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=40,
            command=self._schedule_batch
        )
        schedule_all_btn.pack(fill="x", pady=(20, 10))

    def _choose_batch_files(self):
        files = filedialog.askopenfilenames(
            title="Select Multiple Videos",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All Files", "*.*")]
        )
        if files:
            self.batch_video_paths = list(files)
            self.batch_files_lbl.configure(
                text=f"Selected {len(files)} video(s)",
                text_color=COLORS["success"]
            )

    def _schedule_batch(self):
        if not self.batch_video_paths:
            messagebox.showerror("Error", "Please select at least one video file.")
            return

        base_title = self.batch_title_entry.get().strip()
        desc = self.batch_desc_entry.get("1.0", "end-1c").strip()
        start_str = self.batch_start_entry.get().strip()
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        except Exception:
            messagebox.showerror("Error", "Invalid start date format. Use YYYY-MM-DD HH:MM.")
            return

        try:
            interval = int(self.batch_interval_entry.get().strip())
        except Exception:
            interval = 24

        scheduler.batch_auto_schedule(
            video_paths=self.batch_video_paths,
            base_title=base_title,
            description=desc,
            tags=["automation", "series"],
            category_id="22",
            privacy_status="public",
            start_datetime=start_dt,
            interval_hours=interval
        )

        messagebox.showinfo("Success", f"Successfully auto-scheduled {len(self.batch_video_paths)} videos into the queue!")
        self.batch_video_paths = []
        self.batch_files_lbl.configure(text="No files selected", text_color=COLORS["muted"])
        self.tabview.set("Active Queue")
        self.refresh_queue()
        if self.on_queue_change:
            self.on_queue_change()
