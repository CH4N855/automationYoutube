# Application structure

- `main.py` creates the window and connects the screens and background services.
- `src/ui/` contains desktop screens. Put shared screen elements in `src/ui/components.py` and colors in `src/ui/theme.py`.
- `src/video_generator.py` creates narration and renders videos; `src/video_templates.py` owns the reusable script templates and niche selection.
- `src/media_downloader.py`, `src/subtitle_generator.py`, and `src/thumbnail_generator.py` handle individual media tasks.
- `src/folder_watcher.py`, `src/scheduler.py`, and `src/autopilot.py` coordinate automatic workflows.
- `src/storage.py` owns local queue, history, and settings data. `src/youtube_auth.py` and `src/youtube_uploader.py` handle YouTube access.

Keep UI code in views and reusable processing in the corresponding service module. Local data, credentials, generated media, and tests must not be committed under the project's Git rules.
