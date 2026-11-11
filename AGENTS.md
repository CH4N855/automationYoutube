# Git Auto-Push & Coding Agent Instructions

## 🚀 Core Mandate: Automatic GitHub Push
Whenever any code edit, feature implementation, refactoring, or bug fix is completed:
1. **Always Push Automatically**: The agent MUST stage the modified files, commit with a clean descriptive message, and push directly to GitHub (`origin main`). Do not leave unpushed commits sitting locally unless explicitly asked.
2. **Absolute Secret & Privacy Protection**:
   - **NEVER** stage or commit:
     - `data/credentials/*`
     - `client_secret*.json`
     - `token*.json`
     - `data/*.json` (local database / queues)
     - `tests/` directory
     - Raw audio/video files (`*.mp4`, `*.mov`, `*.mp3`, `*.wav`)
3. **Standard Push Protocol**:
   ```powershell
   git status
   git add <safe modified files>
   git commit -m "Descriptive update message"
   git push origin main
   ```
4. **Git Auto-Push Background Agent**:
   - The file `src/git_autopush.py` and `run_autopush.bat` provide an autonomous background watcher that automatically detects file saves and pushes to GitHub within seconds.
