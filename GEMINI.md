# Gemini & Antigravity Agent Workspace Guidelines

## Mandatory Git Synchronization Rule
- **Auto-Push On Every Change**: Whenever any code file is created, modified, or fixed, stage the changes, commit with a clear description, and push to `origin main`.
- **Security Check**: Verify that `data/credentials/*`, `token.json`, and `client_secret.json` are strictly excluded from every commit.
- **Local Background Auto-Pusher**: Available in `src/git_autopush.py` / `run_autopush.bat`.
