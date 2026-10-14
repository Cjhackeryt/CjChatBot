from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
from collections.abc import AsyncGenerator, Mapping
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, RedirectResponse

from .connectors.kick import KickChat
from .connectors.tiktok import TikTokChat
from .connectors.twitch import TwitchChat
from .connectors.youtube import YouTubeChat
from .hub import Hub, Viewer
from .stats import Stats

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
SUPPORTED_PLATFORMS = ("twitch", "kick", "youtube", "tiktok")

# Names go straight into IRC commands and URLs, so reject anything outside
# each platform's own username charset.
CHANNEL_PATTERNS = {
    "twitch": re.compile(r"^[a-z0-9_]{1,25}$"),
    "kick": re.compile(r"^[a-z0-9_-]{1,50}$"),
    "youtube": re.compile(r"^@?[a-z0-9._-]{1,50}$"),
    "tiktok": re.compile(r"^@?[a-z0-9._]{1,50}$"),
}

# Site-wide announcement banner; in-memory on purpose — a restart clears it.
ANNOUNCE_TOKEN = os.getenv("ANNOUNCE_TOKEN", "")
ANNOUNCE_MAX_CHARS = 300
announcement = {"text": ""}
viewers: set[Viewer] = set()

stats = Stats()
hub = Hub()
hub.register_connector("twitch", TwitchChat(hub))
hub.register_connector("kick", KickChat(hub))
hub.register_connector("youtube", YouTubeChat(hub))
hub.register_connector("tiktok", TikTokChat(hub))


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    autosave_task = asyncio.create_task(stats.autosave())
    try:
        yield
    finally:
        autosave_task.cancel()
        with suppress(asyncio.CancelledError):
            await autosave_task
        stats.save()


app = FastAPI(title="CjChatBot", lifespan=lifespan)


@app.websocket("/ws")
async def viewer_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    viewer = Viewer(websocket)
    stats.connection_opened()
    viewers.add(viewer)
    try:
        if announcement["text"]:
            await viewer.send({"type": "announce", "text": announcement["text"]})
        while True:
            try:
                payload = await websocket.receive_json()
            except json.JSONDecodeError:
                logger.warning("closing WebSocket after receiving invalid JSON")
                await websocket.close(code=1003, reason="Invalid JSON")
                break
            if not isinstance(payload, dict) or payload.get("type") != "subscribe":
                continue
            channels = payload.get("channels", {})
            if not isinstance(channels, dict):
                logger.warning("ignoring WebSocket subscription with invalid channels")
                continue
            await handle_subscribe(viewer, channels)
    except WebSocketDisconnect:
        pass
    finally:
        viewers.discard(viewer)
        stats.connection_closed()
        await hub.drop_viewer(viewer)


async def handle_subscribe(viewer: Viewer, channels: Mapping[str, object]) -> None:
    desired = set()
    for platform in SUPPORTED_PLATFORMS:
        channel = channels.get(platform)
        if not isinstance(channel, str):
            continue
        channel = channel.strip().lstrip("#").lower()
        if channel and CHANNEL_PATTERNS[platform].match(channel):
            desired.add((platform, channel))

    for key in viewer.keys - desired:
        await hub.unsubscribe(viewer, key)
    for platform, channel in desired - viewer.keys:
        await hub.subscribe(viewer, platform, channel)

    await viewer.send(hub.bootstrap_payload(viewer))


@app.get("/announcement")
async def get_announcement() -> dict:
    return {"text": announcement["text"]}


@app.post("/announce")
async def announce(request: Request) -> dict:
    if not ANNOUNCE_TOKEN:
        raise HTTPException(status_code=404)
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400) from None
    if not isinstance(data, dict):
        raise HTTPException(status_code=400)
    token = data.get("token")
    text = data.get("text", "")
    if not isinstance(token, str) or not isinstance(text, str):
        raise HTTPException(status_code=400)
    if not secrets.compare_digest(token, ANNOUNCE_TOKEN):
        raise HTTPException(status_code=403)
    text = text.strip()[:ANNOUNCE_MAX_CHARS]
    announcement["text"] = text
    await asyncio.gather(
        *(viewer.send({"type": "announce", "text": text}) for viewer in list(viewers))
    )
    return {"ok": True, "viewers": len(viewers)}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/stats")
async def stats_endpoint() -> dict:
    return stats.snapshot(len(hub.channels))


@app.get("/popout")
@app.get("/overlay")
async def popout_page() -> FileResponse:
    return FileResponse(WEB_DIR / "popout.html")


@app.get("/popout.html")
async def popout_legacy(request: Request) -> RedirectResponse:
    query = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(f"/popout{query}", status_code=301)


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")