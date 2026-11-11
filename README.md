# ▶️ YouTube Studio Automator (Native Windows Desktop App)

A modern, standalone Windows desktop application built with **Python & CustomTkinter** for **100% automated video creation, SEO optimization, and scheduled publishing** to YouTube via the official **YouTube Data API v3**.

---

## 🤖 100% Full Auto-Pilot Capabilities

### 1. ⚡ 1-Click AI Video Creation & Auto-Posting
- Enter your narration script and an optional video title.
- Select an ultra-realistic neural voice (*Ryan, Christopher, Jenny, Sonia* via `edge-tts`).
- Click **"🚀 Generate & Post AI Short to YouTube Now"**:
  1. Uses your supplied narration script (required).
  2. Synthesizes human-like neural voiceover audio.
  3. Renders a vertical 1080x1920 YouTube Short with dynamic visual backgrounds.
  4. Derives titles, descriptions, and tags from your supplied content.
  5. Uploads and publishes straight to your connected YouTube channel!

### 2. 📅 24/7 Daily Recurring Auto-Pilot
- Toggle **"Enable Daily Auto-Pilot"** and choose a posting hour (e.g., `18:00`).
- The app can be minimized to the **Windows System Tray**, where it runs silently 24/7 in the background without needing a browser open.
- Every day at the set time, it automatically creates a fresh Short and publishes it.

### 3. 📂 Hands-Free Folder Auto-Poster
- Point to any folder on your PC (`watch_folder/`).
- Drop any raw video (`.mp4`, `.mov`, `.mkv`) into the folder.
- As soon as the file finishes copying, the app automatically generates SEO metadata and queues/uploads it according to your presets.

### 4. ✨ AI SEO & Metadata Helper
- Generate 5 clickable high-converting viral title ideas with one click.
- Derives metadata from transcripts or filenames without fabricated chapters or promotional claims.

### 5. 🔄 Autonomous Git Auto-Push Agent
- Background agent (`src/git_autopush.py` or double-click `run_autopush.bat`) automatically watches the workspace.
- Whenever any code file is edited or saved, it automatically stages, commits, and pushes to GitHub within seconds while strictly protecting sensitive secrets.

---

## 🚀 How to Run

### Option A: Double-Click Launcher
Double-click **`run.bat`** in this folder.
The launcher creates a local `.venv`, installs dependencies on first launch
(or when `requirements.txt` changes), and opens the desktop UI together with
the background scheduler and enabled folder watcher. Python 3.10+ must be
installed; the first setup requires internet access. No separate backend
command is needed. Daily publishing is enabled from the Auto-Pilot UI.
Closing the window keeps services running in the system tray; use the tray's
**Exit Application** command to stop everything.

### Option B: Terminal / PowerShell
```powershell
python main.py
```

---

## 🔑 How to Connect Your YouTube Channel

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `YouTube-Automator`).
3. Under **APIs & Services > Library**, enable **YouTube Data API v3**.
4. Under **APIs & Services > OAuth consent screen**:
   - Choose **External**.
   - Enter an App name and your email address.
   - Under **Test Users**, add your personal Google/YouTube email address.
5. Under **APIs & Services > Credentials**:
   - Click **+ CREATE CREDENTIALS** > **OAuth client ID**.
   - Application type: **Desktop app**.
   - Name: `YouTube Desktop App`.
   - Click **Create**, then click **Download JSON**.
6. In **YouTube Studio Automator**:
   - Open **⚙️ Settings & Channel**.
   - Click **📂 Import client_secret.json...** and pick your downloaded file.
   - Click **🔑 Authorize YouTube Account** to log in via your browser.
