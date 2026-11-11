"""Set up the local environment and launch the desktop UI and its services."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main():
    os.chdir(ROOT)
    environment = ROOT / ".venv"
    python = environment / "Scripts" / "python.exe"
    if not python.exists():
        print("First launch: creating the Python environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)

    requirements = ROOT / "requirements.txt"
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = environment / ".requirements-hash"
    if not marker.exists() or marker.read_text() != fingerprint:
        print("Installing application dependencies (internet required)...", flush=True)
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(requirements)],
            check=True,
        )
        marker.write_text(fingerprint)

    print("Opening UI with scheduler and enabled folder watcher...", flush=True)
    return subprocess.call([str(python), str(ROOT / "main.py")], cwd=ROOT)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"Startup failed: {error}", file=sys.stderr)
        sys.exit(1)
