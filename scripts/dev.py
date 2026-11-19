"""Start the whole app for development with one command: the API and the web app.

    uv run python scripts/dev.py          # your own database (DATABASE_URL or openfittrack.db)
    uv run python scripts/dev.py --demo   # a separate demo.db with dummy data

It checks the login settings (and offers to create them), installs the web packages when
they are missing, starts both servers, waits until the API answers and stops both on Ctrl+C.
Open http://localhost:5173 when it says so.

For the production-like Docker setup use `docker compose up -d --build` instead.
"""

import argparse
import getpass
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Allow running as a plain script from the repo root.
sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values  # noqa: E402

from api.auth import MIN_PASSWORD_LENGTH, create_credentials  # noqa: E402

WEB = ROOT / "web"
API_PORT = 8000
WEB_PORT = 5173
DEMO_DATABASE_URL = "sqlite:///demo.db"
CREDENTIAL_KEYS = ("OFT_PASSWORD_HASH", "OFT_SESSION_SECRET")


def upsert_env(text: str, values: dict[str, str]) -> str:
    """Set KEY='value' lines in .env text, replacing existing (also empty) lines of the keys."""
    kept = [line for line in text.splitlines() if line.split("=", 1)[0].strip() not in values]
    kept += [f"{key}='{value}'" for key, value in values.items()]  # quotes keep the $ signs
    return "\n".join(kept) + "\n"


def settings() -> dict[str, str | None]:
    """The .env file with real environment variables on top."""
    return {**dotenv_values(ROOT / ".env"), **os.environ}


def ensure_credentials() -> None:
    if all(settings().get(key) for key in CREDENTIAL_KEYS):
        return
    print("There is no login yet (OFT_PASSWORD_HASH / OFT_SESSION_SECRET in .env).")
    if not sys.stdin.isatty():
        sys.exit("Run `uv run python scripts/create_credentials.py` and put the lines in .env.")
    password = getpass.getpass(f"Choose a password (at least {MIN_PASSWORD_LENGTH} characters): ")
    if password != getpass.getpass("Repeat the password: "):
        sys.exit("The passwords do not match.")
    try:
        password_hash, secret = create_credentials(password)
    except ValueError as error:
        sys.exit(str(error))
    env_path = ROOT / ".env"
    old = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    new = upsert_env(old, {"OFT_PASSWORD_HASH": password_hash, "OFT_SESSION_SECRET": secret})
    env_path.write_text(new, encoding="utf-8")
    print("Saved to .env (only the hash of your password is stored).\n")


def ensure_web_packages(npm: str) -> None:
    if not (WEB / "node_modules").is_dir():
        print("Installing the web packages (npm install)...")
        subprocess.run([npm, "install"], cwd=WEB, check=True)


def port_in_use(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def api_is_up() -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/api/health", timeout=1)
    except OSError:
        return False
    return True


def start(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    # Own process group on Linux/macOS, so stop() can end the whole tree (npm starts node).
    return subprocess.Popen(command, cwd=cwd, env=env, start_new_session=os.name != "nt")


def stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":  # terminate() would leave the child processes of npm running
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False
        )
    else:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the API and the web app for development.")
    parser.add_argument(
        "--demo", action="store_true", help="use demo.db and fill it with dummy data"
    )
    args = parser.parse_args()

    npm = shutil.which("npm")
    if npm is None:
        sys.exit("npm was not found. Install Node.js 22.12 or newer first.")
    for port in (API_PORT, WEB_PORT):
        if port_in_use(port):
            sys.exit(f"Port {port} is already in use. Stop whatever runs there first.")

    ensure_credentials()
    ensure_web_packages(npm)

    env = {**os.environ}
    if args.demo:
        env["DATABASE_URL"] = DEMO_DATABASE_URL
        print("Demo mode: using demo.db with dummy data.")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "seed_demo_data.py")],
            cwd=ROOT,
            env=env,
            check=True,
        )

    api = start(
        [sys.executable, "-m", "uvicorn", "api.server:app", "--reload", "--port", str(API_PORT)],
        ROOT,
        env,
    )
    web = start([npm, "run", "dev", "--", "--port", str(WEB_PORT), "--strictPort"], WEB, env)
    processes = [api, web]

    try:
        for _ in range(60):
            if api.poll() is not None:
                sys.exit("The API stopped while starting; see the messages above.")
            if api_is_up():
                break
            time.sleep(0.5)
        else:
            sys.exit("The API did not start within 30 seconds.")
        print(
            f"\nReady: open http://localhost:{WEB_PORT}  (API docs: http://127.0.0.1:{API_PORT}/docs)"
        )
        print("Press Ctrl+C to stop both.\n")
        while all(process.poll() is None for process in processes):
            time.sleep(1)
        print("One of the servers stopped; stopping the other.")
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        for process in processes:
            stop(process)


if __name__ == "__main__":
    main()
