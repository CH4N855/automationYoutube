import os
import threading
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox
import customtkinter as ctk
from src.ui.theme import COLORS
from PIL import Image

import config
from src.youtube_uploader import get_video_info, upload_video
from src.storage import add_to_queue, load_settings
from src.youtube_auth import is_authenticated
from src.metadata_generator import clean_topic_from_filename, generate_seo_metadata

class UploadView(ctk.CTkScrollableFrame):
    def __init__(self, master, on_upload_success=None):
        super().__init__(master, fg_color="transparent")
        self.on_upload_success = on_upload_success

        self.selected_video_path = None
        self.selected_thumb_path = None
        self.thumb_image = None

        self._build_ui()

    def _build_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(5, 15))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="New Video Upload",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            header_frame,
            text="Upload videos directly or schedule them for future automated release.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12)
        )
        sub_lbl.pack(anchor="w")

        # Two-column container
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)

        # ----------------- LEFT COLUMN: Media -----------------
        left_col = ctk.CTkFrame(content_frame, fg_color=COLORS["surface"], corner_radius=10)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        ctk.CTkLabel(
            left_col,
            text="Video File",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        # Video picker button
        self.video_btn = ctk.CTkButton(
            left_col,
            text="Choose video file...",
            command=self._choose_video,
            fg_color=COLORS["raised"],
            hover_color=COLORS["secondary_hover"],
            height=40
        )
        self.video_btn.pack(fill="x", padx=15, pady=5)

        # Video info card
        self.video_info_frame = ctk.CTkFrame(left_col, fg_color=COLORS["bg"], corner_radius=8)
        self.video_info_frame.pack(fill="x", padx=15, pady=10)

        self.video_name_lbl = ctk.CTkLabel(
            self.video_info_frame,
            text="No video selected",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12, slant="italic")
        )
        self.video_name_lbl.pack(anchor="w", padx=10, pady=(8, 2))

        self.video_details_lbl = ctk.CTkLabel(
            self.video_info_frame,
            text="Select an MP4, MOV, or MKV file to inspect details.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12)
        )
        self.video_details_lbl.pack(anchor="w", padx=10, pady=(0, 8))

        # Shorts Badge
        self.shorts_badge = ctk.CTkLabel(
            self.video_info_frame,
            text="YouTube Short (<60s & Vertical)",
            fg_color=COLORS["danger_bg"],
            text_color=COLORS["danger"],
            corner_radius=6,
            font=ctk.CTkFont(size=12, weight="bold"),
            padx=10,
            pady=3
        )
        # Hidden by default

        # Target Post Format Selector (Short vs Long Video)
        format_frame = ctk.CTkFrame(self.video_info_frame, fg_color="transparent")
        format_frame.pack(fill="x", padx=10, pady=(4, 6))
        ctk.CTkLabel(format_frame, text="Format:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.upload_format_menu = ctk.CTkOptionMenu(
            format_frame,
            values=["Auto-Detect", "YouTube Short (<60s)", "YouTube Long Video"],
            height=30,
            command=self._on_upload_format_selected
        )
        def_fmt = load_settings().get("default_video_format", "Auto-Detect")
        self.upload_format_menu.set(def_fmt)
        self.upload_format_menu.pack(side="right", fill="x", expand=True, padx=(8, 0))

        # Auto-Detect Title, Description & Hashtags Button
        self.auto_meta_btn = ctk.CTkButton(
            self.video_info_frame,
            text="✨ Auto-Detect Title, Desc & Tags",
            command=self._auto_detect_metadata,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=32,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.auto_meta_btn.pack(fill="x", padx=10, pady=(4, 8))

        # Thumbnail Section
        ctk.CTkLabel(
            left_col,
            text="Custom Thumbnail (Optional)",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        thumb_btn_row = ctk.CTkFrame(left_col, fg_color="transparent")
        thumb_btn_row.pack(fill="x", padx=15, pady=5)
        thumb_btn_row.grid_columnconfigure(0, weight=1)
        thumb_btn_row.grid_columnconfigure(1, weight=1)

        self.thumb_btn = ctk.CTkButton(
            thumb_btn_row,
            text="Choose Image...",
            command=self._choose_thumbnail,
            fg_color=COLORS["raised"],
            hover_color=COLORS["secondary_hover"],
            height=36
        )
        self.thumb_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.gen_thumb_btn = ctk.CTkButton(
            thumb_btn_row,
            text="🎨 AI Generate",
            command=self._auto_generate_thumbnail,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=36
        )
        self.gen_thumb_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Thumbnail preview label
        self.thumb_preview = ctk.CTkLabel(
            left_col,
            text="No thumbnail selected\n(YouTube will auto-generate one)",
            text_color=COLORS["muted"],
            fg_color=COLORS["bg"],
            height=130,
            corner_radius=8
        )
        self.thumb_preview.pack(fill="x", padx=15, pady=(5, 15))

        # ----------------- RIGHT COLUMN: Metadata -----------------
        right_col = ctk.CTkFrame(content_frame, fg_color=COLORS["surface"], corner_radius=10)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)

        layout_state = {"compact": None}

        def adapt_columns(event):
            compact = event.width < 840
            if compact == layout_state["compact"]:
                return
            layout_state["compact"] = compact
            if compact:
                content_frame.grid_columnconfigure(1, weight=0)
                left_col.grid_configure(row=0, column=0, padx=0, pady=(0, 16))
                right_col.grid_configure(row=1, column=0, padx=0)
            else:
                content_frame.grid_columnconfigure(1, weight=1)
                left_col.grid_configure(row=0, column=0, padx=(0, 8), pady=0)
                right_col.grid_configure(row=0, column=1, padx=(8, 0))

        content_frame.bind("<Configure>", adapt_columns)

        ctk.CTkLabel(
            right_col,
            text="Video Metadata",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 8))

        # Title with AI SEO Helper Button
        title_row = ctk.CTkFrame(right_col, fg_color="transparent")
        title_row.pack(fill="x", padx=15, pady=(5, 2))
        title_row.grid_columnconfigure(0, weight=1)
        title_row.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(title_row, text="Title *", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        seo_btn = ctk.CTkButton(
            title_row,
            text="AI SEO Helper",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            height=40,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._open_seo_dialog
        )
        seo_btn.grid(row=0, column=1, sticky="e")

        self.title_entry = ctk.CTkEntry(
            right_col,
            placeholder_text="Enter engaging video title (Max 100 chars)...",
            height=40
        )
        self.title_entry.pack(fill="x", padx=15, pady=(0, 10))

        # Description
        ctk.CTkLabel(right_col, text="Description", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(5, 2))
        self.desc_textbox = ctk.CTkTextbox(right_col, height=120)
        self.desc_textbox.pack(fill="x", padx=15, pady=(0, 10))

        # Load default footer from settings
        settings = load_settings()
        self.desc_textbox.insert("1.0", f"Video description here.{settings.get('default_description_footer', '')}")

        # Tags
        ctk.CTkLabel(right_col, text="Tags (comma separated)", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(5, 2))
        self.tags_entry = ctk.CTkEntry(
            right_col,
            placeholder_text="e.g. tutorial, automation, tech",
            height=40
        )
        self.tags_entry.pack(fill="x", padx=15, pady=(0, 10))
        self.tags_entry.insert(0, ", ".join(settings.get("default_tags", ["automation", "youtube"])))

        # Category & Privacy
        row_opts = ctk.CTkFrame(right_col, fg_color="transparent")
        row_opts.pack(fill="x", padx=15, pady=(0, 10))
        row_opts.grid_columnconfigure(0, weight=1)
        row_opts.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row_opts, text="Category", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 2))
        categories = list(config.YOUTUBE_CATEGORIES.values())
        default_cat = config.YOUTUBE_CATEGORIES.get(settings.get("default_category_id", "22"), "People & Blogs")
        self.cat_menu = ctk.CTkOptionMenu(row_opts, values=categories, height=40)
        self.cat_menu.set(default_cat)
        self.cat_menu.grid(row=1, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkLabel(row_opts, text="Privacy", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=1, sticky="w", pady=(0, 2))
        self.privacy_menu = ctk.CTkOptionMenu(row_opts, values=["public", "unlisted", "private"], height=40)
        self.privacy_menu.set(settings.get("default_privacy", "public"))
        self.privacy_menu.grid(row=1, column=1, sticky="ew", padx=(5, 0))

        # Scheduling
        self.sched_var = ctk.BooleanVar(value=False)
        self.sched_check = ctk.CTkCheckBox(
            right_col,
            text="Schedule Release for a future date/time",
            variable=self.sched_var,
            command=self._toggle_schedule
        )
        self.sched_check.pack(anchor="w", padx=15, pady=(5, 5))

        self.sched_frame = ctk.CTkFrame(right_col, fg_color=COLORS["bg"], corner_radius=6)
        sched_time_suggest = datetime.now() + timedelta(hours=2)

        ctk.CTkLabel(self.sched_frame, text="Release (YYYY-MM-DD HH:MM UTC):", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=(5, 2))
        self.sched_entry = ctk.CTkEntry(
            self.sched_frame,
            placeholder_text="2026-11-12 18:00",
            height=40
        )
        self.sched_entry.insert(0, sched_time_suggest.strftime("%Y-%m-%d %H:%M"))
        self.sched_entry.pack(fill="x", padx=10, pady=(0, 8))
        # Hidden initially
        if not self.sched_var.get():
            self.sched_frame.pack_forget()

        # COPPA
        self.kids_var = ctk.BooleanVar(value=settings.get("default_made_for_kids", False))
        self.kids_check = ctk.CTkCheckBox(
            right_col,
            text="Yes, this video is Made for Kids (COPPA)",
            variable=self.kids_var
        )
        self.kids_check.pack(anchor="w", padx=15, pady=(5, 15))

        # ----------------- ACTION & PROGRESS BAR -----------------
        action_frame = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=10)
        action_frame.pack(fill="x", padx=5, pady=(15, 10))

        self.status_lbl = ctk.CTkLabel(
            action_frame,
            text="Ready to upload.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12)
        )
        self.status_lbl.pack(anchor="w", padx=15, pady=(12, 2))

        self.prog_bar = ctk.CTkProgressBar(action_frame, height=12, fg_color=COLORS["raised"], progress_color=COLORS["accent"])
        self.prog_bar.set(0)
        self.prog_bar.pack(fill="x", padx=15, pady=(2, 12))

        # 1-Click Master Button
        self.one_click_btn = ctk.CTkButton(
            action_frame,
            text="⚡ 1-Click Auto Upload (Pick Video & Let Bot Do Everything)",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#00C853",
            hover_color="#00B248",
            height=46,
            command=self._one_click_auto_publish
        )
        self.one_click_btn.pack(fill="x", padx=15, pady=(0, 10))

        btn_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 15))
        btn_row.grid_columnconfigure(0, weight=2)
        btn_row.grid_columnconfigure(1, weight=1)

        self.upload_btn = ctk.CTkButton(
            btn_row,
            text="Upload to YouTube Now",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=40,
            command=self._start_upload_now
        )
        self.upload_btn.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.queue_btn = ctk.CTkButton(
            btn_row,
            text="Add to Queue",
            font=ctk.CTkFont(size=14),
            fg_color=COLORS["raised"],
            hover_color=COLORS["secondary_hover"],
            height=40,
            command=self._add_to_queue
        )
        self.queue_btn.grid(row=0, column=1, sticky="ew", padx=(10, 0))

    def _load_selected_video(self, file_path: str):
        self.selected_video_path = file_path
        info = get_video_info(file_path)

        self.video_name_lbl.configure(text=f"{info['filename']}", text_color=COLORS["text"])
        details = f"Size: {info['size_mb']} MB"
        if info['duration_sec']:
            details += f"  |  Duration: {info['duration_sec']}s"
        if info['width'] and info['height']:
            details += f"  |  Res: {info['width']}x{info['height']}"
        self.video_details_lbl.configure(text=details)

        # Auto-populate title if empty
        if not self.title_entry.get().strip():
            clean_title = os.path.splitext(info['filename'])[0].replace("_", " ").title()
            self.title_entry.insert(0, clean_title[:100])

        # Show / hide Shorts badge based on format menu or video info
        fmt_choice = self.upload_format_menu.get().lower()
        if "short" in fmt_choice:
            self.shorts_badge.configure(text="YouTube Short (<60s & Vertical)", fg_color=COLORS["danger_bg"], text_color=COLORS["danger"])
            self.shorts_badge.pack(anchor="w", padx=10, pady=(0, 6))
        elif "long" in fmt_choice:
            self.shorts_badge.configure(text="YouTube Long Video (16:9)", fg_color=COLORS["raised"], text_color=COLORS["text"])
            self.shorts_badge.pack(anchor="w", padx=10, pady=(0, 6))
        elif info['is_short']:
            self.shorts_badge.configure(text="YouTube Short (<60s & Vertical)", fg_color=COLORS["danger_bg"], text_color=COLORS["danger"])
            self.shorts_badge.pack(anchor="w", padx=10, pady=(0, 6))
        else:
            self.shorts_badge.pack_forget()

    def _on_upload_format_selected(self, choice: str):
        import re
        if "short" in choice.lower():
            self.shorts_badge.configure(text="YouTube Short (<60s & Vertical)", fg_color=COLORS["danger_bg"], text_color=COLORS["danger"])
            self.shorts_badge.pack(anchor="w", padx=10, pady=(0, 6))
            cur_title = self.title_entry.get().strip()
            if cur_title and "#Shorts" not in cur_title:
                self.title_entry.delete(0, "end")
                self.title_entry.insert(0, f"{cur_title} #Shorts")
            self._auto_generate_thumbnail()
        elif "long" in choice.lower():
            self.shorts_badge.configure(text="YouTube Long Video (16:9)", fg_color=COLORS["raised"], text_color=COLORS["text"])
            self.shorts_badge.pack(anchor="w", padx=10, pady=(0, 6))
            cur_title = self.title_entry.get().strip()
            if "#Shorts" in cur_title or "#shorts" in cur_title:
                clean_title = re.sub(r'#shorts?\b', '', cur_title, flags=re.IGNORECASE).strip()
                self.title_entry.delete(0, "end")
                self.title_entry.insert(0, clean_title)
            self._auto_generate_thumbnail()
        else:
            if self.selected_video_path and os.path.exists(self.selected_video_path):
                info = get_video_info(self.selected_video_path)
                if info.get("is_short"):
                    self.shorts_badge.configure(text="YouTube Short (<60s & Vertical)", fg_color=COLORS["danger_bg"], text_color=COLORS["danger"])
                    self.shorts_badge.pack(anchor="w", padx=10, pady=(0, 6))
                else:
                    self.shorts_badge.pack_forget()
            else:
                self.shorts_badge.pack_forget()

    def _choose_video(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All Files", "*.*")]
        )
        if file_path:
            self._load_selected_video(file_path)
            # Automatically analyze video speech and populate Title, Description & Hashtags
            self.after(100, self._auto_detect_metadata)

    def _auto_detect_metadata(self):
        """Read and transcribe video file automatically to detect Title, Description and Hashtags."""
        if not self.selected_video_path or not os.path.exists(self.selected_video_path):
            messagebox.showinfo("Notice", "Please select a video file first.")
            return

        self.auto_meta_btn.configure(state="disabled", text="✨ Analyzing Speech...")
        self.status_lbl.configure(
            text="Reading video & analyzing audio for Title, Description & Hashtags...",
            text_color=COLORS["warning"]
        )

        def worker():
            try:
                force_fmt = None
                fmt_choice = self.upload_format_menu.get().lower()
                if "short" in fmt_choice:
                    force_fmt = "short"
                elif "long" in fmt_choice:
                    force_fmt = "long"

                from src.metadata_generator import auto_generate_video_metadata
                meta = auto_generate_video_metadata(self.selected_video_path, force_format=force_fmt)

                def update_ui():
                    if meta.get("title"):
                        self.title_entry.delete(0, "end")
                        self.title_entry.insert(0, meta["title"])

                    if meta.get("description"):
                        self.desc_textbox.delete("1.0", "end")
                        self.desc_textbox.insert("1.0", meta["description"])

                    if meta.get("tags_csv"):
                        self.tags_entry.delete(0, "end")
                        self.tags_entry.insert(0, meta["tags_csv"])

                    if meta.get("category_id"):
                        cat_name = config.YOUTUBE_CATEGORIES.get(meta["category_id"])
                        if cat_name:
                            self.cat_menu.set(cat_name)

                    source_name = meta.get("source", "video").replace("_", " ").capitalize()
                    self.status_lbl.configure(
                        text=f"✨ Title, Description & Hashtags auto-generated from {source_name}!",
                        text_color=COLORS["success"]
                    )
                    self.auto_meta_btn.configure(state="normal", text="✨ Auto-Detect Title, Desc & Tags")

                    # Also auto-generate thumbnail if none chosen
                    if not self.selected_thumb_path:
                        self._auto_generate_thumbnail()

                self.after(0, update_ui)
            except Exception as e:
                def on_err():
                    self.status_lbl.configure(text=f"Auto-metadata notice: {e}", text_color=COLORS["muted"])
                    self.auto_meta_btn.configure(state="normal", text="✨ Auto-Detect Title, Desc & Tags")
                self.after(0, on_err)

        threading.Thread(target=worker, daemon=True).start()

    def _one_click_auto_publish(self):
        """1-Click: Pick video (if not chosen) -> Transcribe & Generate Metadata -> Generate Thumbnail -> Upload to YouTube!"""
        if not self.selected_video_path or not os.path.exists(self.selected_video_path):
            file_path = filedialog.askopenfilename(
                title="Select Video to Auto-Publish",
                filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi *.webm"), ("All Files", "*.*")]
            )
            if not file_path:
                return
            self._load_selected_video(file_path)

        if not is_authenticated():
            messagebox.showerror("Error", "YouTube account is not connected. Go to 'Settings & Channel' to connect.")
            return

        self.one_click_btn.configure(state="disabled", text="⚡ Processing 1-Click Auto Upload...")
        self.upload_btn.configure(state="disabled")
        self.queue_btn.configure(state="disabled")

        def worker():
            try:
                # Step 1: Detect / Auto-generate metadata
                self.after(0, lambda: self.status_lbl.configure(text="Step 1/3: Analyzing speech & generating viral metadata...", text_color=COLORS["warning"]))
                self.after(0, lambda: self.prog_bar.set(0.15))

                force_fmt = None
                fmt_choice = self.upload_format_menu.get().lower()
                if "short" in fmt_choice:
                    force_fmt = "short"
                elif "long" in fmt_choice:
                    force_fmt = "long"

                from src.metadata_generator import auto_generate_video_metadata
                meta = auto_generate_video_metadata(self.selected_video_path, force_format=force_fmt)

                title = meta.get("title") or self.title_entry.get().strip()
                if not title:
                    title = os.path.splitext(os.path.basename(self.selected_video_path))[0].replace("_", " ").title()

                settings = load_settings()
                footer = settings.get("default_description_footer", "").strip()
                base_desc = meta.get("description") or self.desc_textbox.get("1.0", "end-1c").strip()
                desc = f"{base_desc}\n\n{footer}".strip() if footer else base_desc
                tags = meta.get("tags") or [t.strip() for t in self.tags_entry.get().split(",") if t.strip()]
                cat_id = meta.get("category_id") or config.CATEGORY_NAME_TO_ID.get(self.cat_menu.get(), "22")
                privacy = self.privacy_menu.get()
                kids = self.kids_var.get()

                def sync_ui():
                    self.title_entry.delete(0, "end")
                    self.title_entry.insert(0, title)
                    self.desc_textbox.delete("1.0", "end")
                    self.desc_textbox.insert("1.0", desc)
                    self.tags_entry.delete(0, "end")
                    self.tags_entry.insert(0, ", ".join(tags))
                    cat_name = config.YOUTUBE_CATEGORIES.get(cat_id)
                    if cat_name:
                        self.cat_menu.set(cat_name)
                self.after(0, sync_ui)

                # Step 2: Auto-generate high-CTR thumbnail if needed
                thumb_path = self.selected_thumb_path
                if not thumb_path or not os.path.exists(thumb_path):
                    self.after(0, lambda: self.status_lbl.configure(text="Step 2/3: Generating high-CTR custom thumbnail...", text_color=COLORS["warning"]))
                    self.after(0, lambda: self.prog_bar.set(0.30))
                    from src.thumbnail_generator import generate_youtube_thumbnail
                    is_short = meta.get("is_short", False)
                    aspect = "9:16" if is_short else "16:9"
                    thumb_path = generate_youtube_thumbnail(
                        title=title,
                        subtitle="SHORTS" if is_short else "MUST WATCH",
                        aspect_ratio=aspect
                    )
                    self.selected_thumb_path = thumb_path
                    try:
                        img = Image.open(thumb_path)
                        size = (110, 195) if is_short else (220, 124)
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                        self.after(0, lambda: self.thumb_preview.configure(image=ctk_img, text=""))
                    except Exception:
                        pass

                # Step 3: Direct upload to YouTube
                self.after(0, lambda: self.status_lbl.configure(text="Step 3/3: Uploading video directly to YouTube...", text_color=COLORS["warning"]))

                def progress_cb(percent, msg):
                    self.prog_bar.set(percent)
                    self.status_lbl.configure(text=msg)

                result = upload_video(
                    video_path=self.selected_video_path,
                    title=title,
                    description=desc,
                    tags=tags,
                    category_id=cat_id,
                    privacy_status=privacy,
                    thumbnail_path=thumb_path,
                    scheduled_time=None,
                    made_for_kids=kids,
                    progress_callback=progress_cb
                )

                def on_done():
                    self.prog_bar.set(1.0)
                    self.status_lbl.configure(
                        text=f"✅ Video Uploaded! Direct Link: {result['url']}",
                        text_color=COLORS["success"]
                    )
                    self.one_click_btn.configure(state="normal", text="⚡ 1-Click Auto Upload (Pick Video & Let Bot Do Everything)")
                    self.upload_btn.configure(state="normal")
                    self.queue_btn.configure(state="normal")
                    messagebox.showinfo("Published Successfully!", f"Video uploaded to YouTube!\n\nTitle: {result['title']}\nVideo ID: {result['video_id']}\nURL: {result['url']}")
                    if self.on_upload_success:
                        self.on_upload_success()

                self.after(0, on_done)

            except Exception as e:
                def on_fail(err=str(e)):
                    self.prog_bar.set(0)
                    self.status_lbl.configure(text=f"Upload Failed: {err}", text_color=COLORS["danger"])
                    self.one_click_btn.configure(state="normal", text="⚡ 1-Click Auto Upload (Pick Video & Let Bot Do Everything)")
                    self.upload_btn.configure(state="normal")
                    self.queue_btn.configure(state="normal")
                    messagebox.showerror("Upload Error", f"Upload failed: {err}")
                self.after(0, on_fail)

        threading.Thread(target=worker, daemon=True).start()

    def _choose_thumbnail(self):
        file_path = filedialog.askopenfilename(
            title="Select Thumbnail Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp"), ("All Files", "*.*")]
        )
        if file_path:
            self.selected_thumb_path = file_path
            try:
                img = Image.open(file_path)
                # Resize keeping 16:9 aspect ratio
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(220, 124))
                self.thumb_preview.configure(image=ctk_img, text="")
            except Exception as e:
                self.thumb_preview.configure(text=f"Error previewing: {e}")

    def _auto_generate_thumbnail(self):
        title = self.title_entry.get().strip()
        if not title and self.selected_video_path:
            title = clean_topic_from_filename(self.selected_video_path)
        if not title:
            title = "Awesome Video"

        fmt_choice = self.upload_format_menu.get().lower()
        if "short" in fmt_choice:
            is_short = True
        elif "long" in fmt_choice:
            is_short = False
        else:
            is_short = self.shorts_badge.winfo_ismapped()
        aspect = "9:16" if is_short else "16:9"

        from src.thumbnail_generator import generate_youtube_thumbnail
        thumb_path = generate_youtube_thumbnail(
            title=title,
            subtitle="SHORTS" if is_short else "MUST WATCH",
            aspect_ratio=aspect
        )
        self.selected_thumb_path = thumb_path
        try:
            img = Image.open(thumb_path)
            size = (110, 195) if is_short else (220, 124)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            self.thumb_preview.configure(image=ctk_img, text="")
            self.status_lbl.configure(text="Custom AI Thumbnail generated and applied!", text_color=COLORS["success"])
        except Exception as e:
            self.thumb_preview.configure(text=f"Error: {e}")

    def _toggle_schedule(self):
        if self.sched_var.get():
            self.sched_frame.pack(fill="x", padx=15, pady=(0, 10))
        else:
            self.sched_frame.pack_forget()

    def _start_upload_now(self):
        if not self.selected_video_path or not os.path.exists(self.selected_video_path):
            messagebox.showerror("Error", "Please select a valid video file first.")
            return

        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("Error", "Please enter a video title.")
            return

        if not is_authenticated():
            messagebox.showerror("Error", "YouTube account is not connected. Go to 'Settings & Channel' to connect.")
            return

        # Disable buttons during upload
        self.upload_btn.configure(state="disabled")
        self.queue_btn.configure(state="disabled")

        thread = threading.Thread(target=self._upload_worker, daemon=True)
        thread.start()

    def _upload_worker(self):
        title = self.title_entry.get().strip()
        desc = self.desc_textbox.get("1.0", "end-1c").strip()
        tags = [t.strip() for t in self.tags_entry.get().split(",") if t.strip()]
        cat_id = config.CATEGORY_NAME_TO_ID.get(self.cat_menu.get(), "22")
        privacy = self.privacy_menu.get()
        kids = self.kids_var.get()

        scheduled_time = None
        if self.sched_var.get():
            sched_str = self.sched_entry.get().strip()
            try:
                dt = datetime.strptime(sched_str, "%Y-%m-%d %H:%M")
                scheduled_time = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        def progress_cb(percent, msg):
            self.prog_bar.set(percent)
            self.status_lbl.configure(text=msg)

        try:
            result = upload_video(
                video_path=self.selected_video_path,
                title=title,
                description=desc,
                tags=tags,
                category_id=cat_id,
                privacy_status=privacy,
                thumbnail_path=self.selected_thumb_path,
                scheduled_time=scheduled_time,
                made_for_kids=kids,
                progress_callback=progress_cb
            )

            self.status_lbl.configure(
                text=f"Video Uploaded! Direct Link: {result['url']}",
                text_color=COLORS["success"]
            )
            messagebox.showinfo("Success", f"Video uploaded successfully!\n\nVideo ID: {result['video_id']}\nURL: {result['url']}")
            if self.on_upload_success:
                self.on_upload_success()

        except Exception as e:
            self.status_lbl.configure(text=f"Upload Failed: {str(e)}", text_color=COLORS["danger"])
            messagebox.showerror("Upload Failed", str(e))
        finally:
            self.upload_btn.configure(state="normal")
            self.queue_btn.configure(state="normal")

    def _add_to_queue(self):
        if not self.selected_video_path or not os.path.exists(self.selected_video_path):
            messagebox.showerror("Error", "Please select a valid video file.")
            return

        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("Error", "Please enter a video title.")
            return

        desc = self.desc_textbox.get("1.0", "end-1c").strip()
        tags = [t.strip() for t in self.tags_entry.get().split(",") if t.strip()]
        cat_id = config.CATEGORY_NAME_TO_ID.get(self.cat_menu.get(), "22")
        privacy = self.privacy_menu.get()
        kids = self.kids_var.get()

        scheduled_time = None
        if self.sched_var.get():
            sched_str = self.sched_entry.get().strip()
            try:
                dt = datetime.strptime(sched_str, "%Y-%m-%d %H:%M")
                scheduled_time = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        item = add_to_queue(
            video_path=self.selected_video_path,
            title=title,
            description=desc,
            tags=tags,
            category_id=cat_id,
            privacy_status=privacy,
            thumbnail_path=self.selected_thumb_path,
            scheduled_time=scheduled_time,
            made_for_kids=kids
        )

        messagebox.showinfo("Queue", f"Added '{title}' to queue successfully!")
        self.status_lbl.configure(text=f"Added to Queue (ID: {item['id']})", text_color=COLORS["warning"])
        if self.on_upload_success:
            self.on_upload_success()

    def _open_seo_dialog(self):
        """Open popup modal for AI SEO title and metadata generation."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(" AI SEO & Metadata Generator")
        dialog.geometry("620x540")
        dialog.resizable(False, False)
        dialog.grab_set()  # Make modal

        ctk.CTkLabel(
            dialog,
            text="YouTube SEO Title & Metadata Generator",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 2))

        ctk.CTkLabel(
            dialog,
            text="Generate high-converting titles, timestamps, descriptions, and ranking tags.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # Topic Input
        ctk.CTkLabel(dialog, text="Video Topic / Concept:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(5, 2))
        initial_topic = self.title_entry.get().strip()
        if not initial_topic and self.selected_video_path:
            initial_topic = clean_topic_from_filename(self.selected_video_path)

        topic_entry = ctk.CTkEntry(dialog, placeholder_text="e.g. Python automation, Gym Workout, Tech Review", height=40)
        topic_entry.insert(0, initial_topic)
        topic_entry.pack(fill="x", padx=20, pady=(0, 10))

        # Format selector
        type_row = ctk.CTkFrame(dialog, fg_color="transparent")
        type_row.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(type_row, text="Video Format:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 10))
        format_menu = ctk.CTkOptionMenu(type_row, values=["Standard Video", "YouTube Short"], width=160, height=40)
        format_menu.set("YouTube Short" if self.shorts_badge.winfo_ismapped() else "Standard Video")
        format_menu.pack(side="left")

        # Result Frame
        results_frame = ctk.CTkScrollableFrame(dialog, height=240, fg_color=COLORS["bg"])
        results_frame.pack(fill="both", expand=True, padx=20, pady=(5, 10))

        current_gen = {}

        def populate_results():
            for w in results_frame.winfo_children():
                w.destroy()

            topic = topic_entry.get().strip() or "My Video"
            vtype = "Short" if "Short" in format_menu.get() else "Standard"
            data = generate_seo_metadata(topic, video_type=vtype)
            current_gen.clear()
            current_gen.update(data)

            ctk.CTkLabel(
                results_frame,
                text="Click any title below to select it:",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["muted"]
            ).pack(anchor="w", padx=5, pady=(5, 5))

            selected_title_var = ctk.StringVar(value=data["recommended_title"])

            for t in data["titles"]:
                btn = ctk.CTkRadioButton(
                    results_frame,
                    text=t,
                    variable=selected_title_var,
                    value=t,
                    font=ctk.CTkFont(size=12)
                )
                btn.pack(anchor="w", padx=10, pady=4)

            current_gen["selected_title_var"] = selected_title_var

        gen_btn = ctk.CTkButton(
            dialog,
            text="Generate SEO Metadata",
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=40,
            command=populate_results
        )
        gen_btn.pack(fill="x", padx=20, pady=(0, 10))

        # Run initial generation
        populate_results()

        # Checkboxes for Description & Tags
        apply_desc_var = ctk.BooleanVar(value=True)
        apply_tags_var = ctk.BooleanVar(value=True)

        opts_row = ctk.CTkFrame(dialog, fg_color="transparent")
        opts_row.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkCheckBox(opts_row, text="Include Description with Timestamps", variable=apply_desc_var, font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 15))
        ctk.CTkCheckBox(opts_row, text="Include Ranking Tags", variable=apply_tags_var, font=ctk.CTkFont(size=12)).pack(side="left")

        # Apply Button
        def apply_metadata():
            if not current_gen:
                return

            chosen_title = current_gen.get("selected_title_var").get() if "selected_title_var" in current_gen else current_gen.get("recommended_title")
            if chosen_title:
                self.title_entry.delete(0, "end")
                self.title_entry.insert(0, chosen_title[:100])

            if apply_desc_var.get() and current_gen.get("description"):
                self.desc_textbox.delete("1.0", "end")
                settings = load_settings()
                full_desc = current_gen["description"] + settings.get("default_description_footer", "")
                self.desc_textbox.insert("1.0", full_desc)

            if apply_tags_var.get() and current_gen.get("tags_csv"):
                self.tags_entry.delete(0, "end")
                self.tags_entry.insert(0, current_gen["tags_csv"])

            dialog.destroy()
            messagebox.showinfo("Applied", "SEO Title, Description, and Tags applied to upload form!")

        apply_btn = ctk.CTkButton(
            dialog,
            text="Apply to Video Form",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=38,
            command=apply_metadata
        )
        apply_btn.pack(fill="x", padx=20, pady=(0, 15))
