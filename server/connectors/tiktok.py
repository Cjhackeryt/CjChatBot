"""Anonymous TikTok live chat connector.

TikTok live chat is readable without login, but the webcast endpoints demand
signed request parameters. The TikTokLive library handles the protobuf
protocol and routes room-entry signing through Euler Stream (a third-party
signing service with a free rate-limited tier) — the TikTok equivalent of
Kick's Cloudflare hurdle. One client (and task) per channel; if the channel
is not live we recheck every 60s, like the YouTube connector.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import ssl
import time

import httpx
from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    CommentEvent,
    ConnectEvent,
    GiftEvent,
    LiveEndEvent,
)

try:
    from TikTokLive.events import SubNotifyEvent as SubscribeEvent
except ImportError:  # TikTokLive < 7 used the old name
    from TikTokLive.events import SubscribeEvent

try:
    from TikTokLive.client.errors import UserNotFoundError, UserOfflineError
except Exception:  # library layout changed — fall back to generic handling
    class UserOfflineError(Exception):  # type: ignore[no-redef]
        pass

    class UserNotFoundError(Exception):  # type: ignore[no-redef]
        pass

from ..models import Message
from ..tls import create_ssl_context

# TikTok's edge 403s non-US requests carrying the library's default
# datacenter cookie; drop it and let TikTok route by IP.
try:
    from TikTokLive.client.web.web_settings import WebDefaults
    WebDefaults.web_client_cookies.pop("tt-target-idc", None)
except Exception:
    pass

logger = logging.getLogger(__name__)

OFFLINE_RECHECK_SECONDS = 60
TIKTOK_SSL_CONTEXT = create_ssl_context()


def _describe_error(exc: Exception) -> str:
    root = exc
    seen = {id(root)}
    while root.__cause__ or root.__context__:
        cause = root.__cause__ or root.__context__
        if id(cause) in seen:
            break
        seen.add(id(cause))
        root = cause
    detail = str(root).strip()
    if root is exc or not detail:
        return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__
    return f"{type(exc).__name__} ({type(root).__name__}: {detail})"


def _is_connection_error(exc: Exception) -> bool:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        if isinstance(current, (httpx.ConnectError, httpx.ProxyError)):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


def _is_certificate_error(exc: Exception) -> bool:
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        if isinstance(current, ssl.SSLCertVerificationError):
            return True
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return False


def _msg_id(event) -> str | None:
    """Webcast message id — on event.common since TikTokLive 7."""
    msg_id = getattr(getattr(event, "common", None), "msg_id", None)
    return str(msg_id) if msg_id else None


class TikTokChat:
    platform = "tiktok"

    def __init__(self, hub):
        self.hub = hub
        self.tasks: dict[str, asyncio.Task] = {}

    async def join(self, name: str) -> None:
        await self.hub.publish_status(
            self.platform, name, "warn", "connecting", f"Looking up @{name.lstrip('@')}…"
        )
        self.tasks[name] = asyncio.create_task(self._run(name))

    async def part(self, name: str) -> None:
        task = self.tasks.pop(name, None)
        if task is not None:
            task.cancel()

    async def _run(self, name: str) -> None:
        backoff = 5.0
        while True:
            client: TikTokLiveClient | None = None
            try:
                proxy_url = (
                    os.getenv("TIKTOK_PROXY")
                    or os.getenv("HTTPS_PROXY")
                    or os.getenv("https_proxy")
                    or os.getenv("HTTP_PROXY")
                    or os.getenv("http_proxy")
                    or ""
                ).strip()
                proxy = httpx.Proxy(proxy_url) if proxy_url else None
                client = TikTokLiveClient(
                    unique_id=f"@{name.lstrip('@')}",
                    web_proxy=proxy,
                    ws_proxy=proxy,
                    web_kwargs={"httpx_kwargs": {"verify": TIKTOK_SSL_CONTEXT}},
                    ws_kwargs={"ssl": TIKTOK_SSL_CONTEXT},
                )
                self._register_handlers(client, name)
                await client.connect()  # runs until the stream/connection ends
                await self._teardown(client)
                await self.hub.publish_status(
                    self.platform, name, "warn", "offline",
                    f"Stream ended — rechecking every {OFFLINE_RECHECK_SECONDS}s",
                )
                backoff = 5.0
                await asyncio.sleep(OFFLINE_RECHECK_SECONDS)
            except asyncio.CancelledError:
                if client is not None:
                    await self._teardown(client)
                raise
            except UserOfflineError:
                if client is not None:
                    await self._teardown(client)
                await self.hub.publish_status(
                    self.platform, name, "warn", "offline",
                    f"Not live right now — rechecking every {OFFLINE_RECHECK_SECONDS}s",
                )
                backoff = 5.0
                await asyncio.sleep(OFFLINE_RECHECK_SECONDS)
            except UserNotFoundError:
                if client is not None:
                    await self._teardown(client)
                await self.hub.publish_status(
                    self.platform, name, "error", "not found",
                    f"No TikTok user named @{name.lstrip('@')}",
                )
                return
            except Exception as exc:
                if client is not None:
                    await self._teardown(client)
                detail = _describe_error(exc)
                if _is_certificate_error(exc):
                    detail += " — trust your network's root CA using CJCHATBOT_CA_BUNDLE"
                elif _is_connection_error(exc):
                    detail += " — check TikTok network access or configure TIKTOK_PROXY"
                logger.warning("tiktok error for %s: %s", name, detail, exc_info=True)
                await self.hub.publish_status(
                    self.platform, name, "error", "error",
                    f"{detail} — retrying in {int(backoff)}s",
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 120.0)

    async def _teardown(self, client: TikTokLiveClient) -> None:
        """connect() only cleans up after cancellation; a leftover live
        client would duplicate every message."""
        try:
            await client.disconnect()
        except Exception:
            pass

    def _register_handlers(self, client: TikTokLiveClient, name: str) -> None:
        @client.on(ConnectEvent)
        async def _on_connect(event: ConnectEvent) -> None:
            await self.hub.publish_status(
                self.platform, name, "ok", "connected",
                f"Connected to @{name.lstrip('@')}",
            )

        @client.on(CommentEvent)
        async def _on_comment(event: CommentEvent) -> None:
            user = event.user
            author = (getattr(user, "nickname", "") or getattr(user, "unique_id", "") or "Unknown")
            await self._publish(
                name, author, user, str(event.comment or ""),
                kind="chat", message_id=_msg_id(event),
            )

        @client.on(GiftEvent)
        async def _on_gift(event: GiftEvent) -> None:
            gift = event.gift
            # Streakable gifts fire once per tap; only report the final total.
            if getattr(gift, "streakable", False) and getattr(event, "streaking", False):
                return
            user = event.user
            author = (getattr(user, "nickname", "") or getattr(user, "unique_id", "") or "Someone")
            count = getattr(event, "repeat_count", 1) or 1
            gift_name = getattr(gift, "name", "") or "a gift"
            text = f"{author} sent {count}x {gift_name}!" if count > 1 else f"{author} sent {gift_name}!"
            await self._publish(name, author, user, text, kind="system", message_id=_msg_id(event))

        @client.on(SubscribeEvent)
        async def _on_subscribe(event: SubscribeEvent) -> None:
            user = event.user
            author = (getattr(user, "nickname", "") or getattr(user, "unique_id", "") or "Someone")
            await self._publish(
                name, author, user, f"{author} subscribed!",
                kind="system", message_id=_msg_id(event),
            )

        @client.on(LiveEndEvent)
        async def _on_live_end(event: LiveEndEvent) -> None:
            await self.hub.publish_status(
                self.platform, name, "warn", "offline", "Stream ended",
            )

    async def _publish(
        self, name: str, author: str, user, text: str, *,
        kind: str, message_id: str | None = None,
    ) -> None:
        if not text.strip():
            return
        message_id = message_id or getattr(getattr(user, "common", None), "msg_id", None)
        await self.hub.publish_message(Message(
            platform=self.platform,
            id=str(message_id or f"{time.time()}-{random.random()}"),
            channel=name,
            author=author,
            color="",  # TikTok has no per-user chat colors
            badges=[],
            text=text,
            emotes=[],
            timestamp=int(time.time() * 1000),
            author_login=str(getattr(user, "unique_id", "") or author).lower(),
            kind=kind,
        ))
