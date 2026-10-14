from __future__ import annotations

import os
import platform
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

LOCAL_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def get_data_dir() -> Path:
    if sys.platform == "win32":
        base_dir = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        base_dir = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base_dir / "CjChatBot"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def choose_port() -> int:
    for port in range(DEFAULT_PORT, DEFAULT_PORT + 20):
        with socket.socket() as probe:
            try:
                probe.bind((LOCAL_HOST, port))
            except OSError:
                continue
            return port
    with socket.socket() as probe:
        probe.bind((LOCAL_HOST, 0))
        return int(probe.getsockname()[1])


def open_browser_when_ready(url: str) -> None:
    deadline = time.monotonic() + 60
    health_url = f"{url}/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    print(f"CjChatBot did not become ready. Open {url} manually after checking the errors above.")


def main() -> None:
    data_dir = get_data_dir()
    os.environ.setdefault("STATS_FILE", str(data_dir / "stats.json"))

    from server.main import app

    port = choose_port()
    url = f"http://{LOCAL_HOST}:{port}"
    print("Starting CjChatBot. Your browser will open when it is ready.")
    print("Keep this window open while you use CjChatBot. Press Ctrl+C to stop.")
    threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()
    uvicorn.run(app, host=LOCAL_HOST, port=port, log_level="warning")


def report_startup_error(exc: Exception) -> None:
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    log_path = None
    try:
        log_path = get_data_dir() / "startup-error.log"
        log_path.write_text(
            f"Platform: {platform.platform()}\n\n{details}",
            encoding="utf-8",
        )
    except OSError:
        log_path = None

    print("\nCjChatBot could not start.")
    print(details)
    if log_path:
        print(f"Startup details were saved to: {log_path}")
    try:
        input("\nPress Enter to close this window...")
    except EOFError:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        report_startup_error(exc)
        sys.exit(1)
