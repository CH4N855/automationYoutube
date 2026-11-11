"""
Git Auto-Push Background Agent
Automatically detects code edits and pushes them cleanly to GitHub.
Ensures zero sensitive credentials or temporary media files are ever pushed.
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Workspace root
REPO_DIR = Path(__file__).resolve().parent.parent

# Strictly ignored patterns / directories to protect sensitive data
IGNORED_PATTERNS = [
    ".git",
    "data/credentials",
    "token.json",
    "client_secret",
    "tests",
    "data/uploads",
    "data/generated",
    "data/thumbnails",
    "watch_folder",
    "__pycache__",
    ".playwright-mcp",
    ".gemini"
]

def is_safe_path(filepath: str) -> bool:
    """Ensure no credential, token, or media paths are staged or committed."""
    f_lower = filepath.replace("\\", "/").lower()
    for pattern in IGNORED_PATTERNS:
        if pattern.lower() in f_lower:
            return False
    return True

def run_git(args, cwd=REPO_DIR):
    """Run a git command in the repository."""
    cmd = ["git"] + args
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return result

class GitAutoPushAgent:
    def __init__(self, check_interval: int = 5, debounce_seconds: int = 4):
        self.interval = check_interval
        self.debounce = debounce_seconds
        self.running = False

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [GitAutoPush] {message}", flush=True)

    def get_status_entries(self):
        """Get list of changed files from git status."""
        res = run_git(["status", "--porcelain"])
        if res.returncode != 0:
            return []
        
        lines = res.stdout.splitlines()
        entries = []
        for line in lines:
            if len(line) >= 4:
                status_code = line[:2]
                file_rel = line[3:].strip().strip('"')
                if file_rel:
                    entries.append((status_code, file_rel))
        return entries

    def push_pending_changes(self):
        """Safely stage, commit, and push pending code changes."""
        entries = self.get_status_entries()
        if not entries:
            return False

        safe_files_to_add = []
        for status_code, file_rel in entries:
            if is_safe_path(file_rel):
                safe_files_to_add.append(file_rel)
            else:
                self.log(f"⚠️ Skipped sensitive/ignored file: {file_rel}")

        if not safe_files_to_add:
            return False

        self.log(f"Detected {len(safe_files_to_add)} updated file(s). Staging...")
        for f in safe_files_to_add:
            run_git(["add", f])

        # Extra safety check on staged files
        diff_staged = run_git(["diff", "--cached", "--name-only"]).stdout.splitlines()
        for staged in diff_staged:
            staged = staged.strip()
            if not is_safe_path(staged):
                self.log(f"🚨 Unstaging sensitive file: {staged}")
                run_git(["reset", "HEAD", staged])

        # Verify there are still staged files to commit
        diff_final = [f.strip() for f in run_git(["diff", "--cached", "--name-only"]).stdout.splitlines() if f.strip()]
        if not diff_final:
            return False

        # Build clean commit message
        file_basenames = [os.path.basename(f.strip()) for f in diff_final if f.strip()][:4]
        summary = ", ".join(file_basenames)
        if len(diff_final) > 4:
            summary += f" +{len(diff_final) - 4} more"

        commit_msg = f"Auto-update: {summary}"
        self.log(f"Committing: '{commit_msg}'...")
        commit_res = run_git(["commit", "-m", commit_msg])
        if commit_res.returncode != 0:
            self.log(f"Commit notice: {commit_res.stderr.strip()}")
            return False

        self.log("Pushing updates to GitHub (main)...")
        push_res = run_git(["push", "origin", "main"])
        if push_res.returncode == 0:
            self.log(f"✅ Successfully pushed to GitHub! ({summary})")
            return True
        else:
            self.log(f"❌ Push error: {push_res.stderr.strip()}")
            return False

    def start(self):
        """Start the auto-push monitoring loop."""
        self.running = True
        self.log("🟢 Git Auto-Push Agent started. Monitoring workspace for updates...")
        self.log(f"📁 Watching: {REPO_DIR}")

        last_had_changes = False

        while self.running:
            try:
                entries = self.get_status_entries()
                has_changes = any(is_safe_path(f) for _, f in entries)

                if has_changes:
                    if not last_had_changes:
                        self.log("Changes detected. Waiting for file save to complete...")
                        time.sleep(self.debounce)
                        self.push_pending_changes()
                        last_had_changes = False
                else:
                    last_had_changes = False

            except Exception as e:
                self.log(f"Notice: {e}")

            time.sleep(self.interval)

    def stop(self):
        self.running = False
        self.log("🔴 Git Auto-Push Agent stopped.")

if __name__ == "__main__":
    agent = GitAutoPushAgent(check_interval=5, debounce_seconds=3)
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()
