<p align="center">
  <img width="112" src="web/assets/cjchatbot-mark.svg" alt="CjChatBot logo">
</p>

<h1 align="center">CjChatBot</h1>

<p align="center">
  <strong>All your live chats, together.</strong><br>
  A local-first multistream chat viewer for Twitch, YouTube, Kick and TikTok.
</p>

This is a local-first fork of
[kimsec/unified-chat-lite](https://github.com/Kimsec/unified-chat-lite), itself
based on [kimsec/unified-chat](https://github.com/kimsec/unified-chat). The
upstream MIT license and copyright notice are retained in [LICENSE](LICENSE).
Current fork maintenance and branding are by **Cjhackeryt**.

## Run locally

On Windows, double-click [`run-cjchatbot.bat`](run-cjchatbot.bat). The first
run creates a local Python environment and installs the required packages;
then it starts the server and opens CjChatBot in your browser. Keep the
terminal window open while using the app and press **Ctrl+C** there to stop it.
Python 3.12 or newer must be installed.

### Build a Windows app for sharing

On your development PC, run [`packaging/build-windows.ps1`](packaging/build-windows.ps1)
in PowerShell after setting up the project once and installing Inno Setup. It
builds `dist/CjChatBot-Setup.exe`, a Windows installer that includes the app
and its bundled runtime. Your client can run the installer without installing
Python, then start CjChatBot from its shortcut. The app opens in their browser
and stores its connection statistics under their local AppData folder. If
startup fails, the console remains open and details are saved to
`%LOCALAPPDATA%\CjChatBot\startup-error.log`.

The package includes the project license. Packaging is not code encryption:
bundled Python bytecode and browser assets can still be inspected.

### Build a macOS app for sharing

After this project is pushed to its GitHub repository, GitHub Actions builds
the release packages on native Windows and macOS runners. Run the
**Build release packages** workflow from the repository's Actions tab to get
temporary artifacts, or push a version tag beginning with `v` to publish
downloadable files on the GitHub Releases page. The Windows download is
`CjChatBot-Setup.exe`. The macOS ZIP files are
`CjChatBot-macOS-arm64.zip` for Apple Silicon Macs (M1 and later) and
`CjChatBot-macOS-x86_64.zip` for Intel Macs.

On the client's Mac, extract the matching ZIP, then double-click
`Start-CjChatBot.command` inside the extracted `CjChatBot` folder. Keep the
Terminal window open while using the app. App data and startup diagnostics are
stored under `~/Library/Application Support/CjChatBot`.

These builds are not signed or notarized with an Apple Developer identity, so
macOS may block the first launch. If Gatekeeper warns, Control-click
`Start-CjChatBot.command`, choose **Open**, and confirm. If the Mac is managed
by an organization, its security policy may require a signed and notarized
build instead. Packaging does not encrypt the Python bytecode or browser
assets.

Alternatively, use Docker Engine and Docker Compose:

```bash
docker compose up --build -d
```

Open `http://localhost:8100`, enter channel names, and select **Connect**.
To stop the app, run `docker compose down`. Channel selections and preferences
are saved in your browser; no account or hosted service is required.

You can also run the server directly with Python 3.12 or newer:

```bash
pip install -r server/requirements.txt
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

## Connection troubleshooting

Kick's Pusher credentials are negotiated automatically. TikTok connections
require the host machine to reach TikTok's live endpoints and its signing
service; TLS or network failures are shown in the platform status detail and
retried automatically. If TikTok is blocked on your network, connect through
a VPN that allows TikTok, or set `TIKTOK_PROXY` to an HTTP or SOCKS5 proxy
that supports both HTTPS requests and WebSockets before starting CjChatBot.
For example, in PowerShell:

```powershell
$env:TIKTOK_PROXY = "http://127.0.0.1:8080"
.\run-cjchatbot.bat
```

For Docker Compose, set the same variable before starting the container. If
the proxy runs on the Windows host, use `host.docker.internal` instead of
`127.0.0.1`:

```powershell
$env:TIKTOK_PROXY = "http://host.docker.internal:8080"
docker compose up --build -d
```

Twitch IRC uses the host's trusted certificates plus the `certifi` CA bundle,
including in the packaged macOS app. If a managed network or HTTPS-inspecting
proxy still causes a Twitch certificate error, its root CA must be trusted by
macOS; do not disable certificate verification.

## Features

- **Unified feed** — up to four chats in one view, with per-platform filters,
  timestamps and clickable links/emotes. Messages that @-mention a connected
  channel are highlighted.
- **7TV / BTTV / FFZ emotes** — third-party Twitch emotes render automatically,
  no browser extension needed.
- **Twitch badges** — broadcaster, mod, VIP, sub and more, using Twitch's own
  badge art.
- **Expand** — one click fills the window with the chat; ✕ or Esc brings the
  page back. The state lives in the URL (`?expand=1`), so a bookmark or shared
  link opens straight into it.
- **Stream player** — press ▶ in the expanded chat to watch Twitch, Kick or
  YouTube (once live) above the chat. Starts muted; platform icons switch source.
- **Alert sounds** — paste your StreamElements/Streamlabs alert overlay URLs
  under Settings → Alert sounds and they play in the expanded chat. Stored
  only in your browser, never on the server.
- **OBS Browser Source** — connect the channels and click **Copy OBS link**
  above the feed, then paste the copied `/overlay?...` URL directly into the
  Browser Source URL field. The link is transparent and supports auto-fading
  messages (see parameters below).
- **Event notices** — subs, resubs, gift subs, raids and cheers with animated
  cheermotes (Twitch), subs/gift subs/hosts/Kicks gifts (Kick), Super
  Chats/Stickers and memberships (YouTube) render with a highlight border.
- **Hype Train** — a live progress bar (level + %) appears when a Twitch hype
  train is rolling, and fades out when it ends.
- **Shared chat** — in Twitch dual streams, messages from the partner's chat
  show that streamer's avatar.
- **Installable (PWA)** — install as an app from the browser's address bar;
  it opens with your last used channels.
- **Efficient** — the server keeps one upstream connection per unique channel
  (not per viewer) and fans out through an internal WebSocket hub.
- **Resilient Kick connection** — current Pusher credentials are resolved
  automatically and refreshed if Kick rotates them.

## Settings

All toggles live in the sidebar and are stored locally in the browser:

| Setting | Default | Does |
|---|---|---|
| Platform | on | platform icon in front of each message |
| User badges | on | Twitch badges (mod, sub, VIP...) |
| 7TV/BTTV/FFZ emotes | on | third-party emotes in Twitch chats |
| Highlight mentions | on | highlight messages @-mentioning a connected channel |
| 24-hour clock | on | 24h vs 12h timestamps |
| Text size | 16 px | chat text size |
| Alert sounds | – | alert overlay URLs whose sounds play in the expanded chat |

## OBS overlay parameters

Append to the overlay link, e.g.
`/overlay?twitch=channelname&fade=90&size=18&max=8`:

| Parameter | Default | Does |
|---|---|---|
| `fade=<s>` | 60 | seconds before a message fades out; `0` = never fade |
| `size=<px>` | – | text size |
| `align=right` | left | right-align messages |
| `max=<n>` | 200 | max messages on screen |
| `icons=0` | on | hide platform icons |

## Privacy

This service stores **no data** — it is a pure pass-through proxy:

- Chat messages live only in memory: a rolling buffer of the last ~100
  messages per channel (so new viewers get instant history) plus what each
  browser holds on screen. Nothing is written to disk, no database, and a
  restart wipes everything.
- With the recommended flags (`--no-access-log --log-level warning`) the
  server logs no requests, no IP addresses and no watched channels.
- The browser's localStorage keeps only the visitor's own settings (channel
  names, toggles) — locally, on their machine, never sent anywhere.


## Optional announcement banner

The local server can show an in-app announcement without restarting. This is
disabled by default. To enable it, add the following to the service in
`docker-compose.yml`:

```yaml
    environment:
      - ANNOUNCE_TOKEN=${ANNOUNCE_TOKEN:-}
```

Set `ANNOUNCE_TOKEN` in a `.env` file next to the compose file, then restart
with `docker compose up -d`.

Send an announcement from the machine running Docker:

```bash
curl -X POST http://localhost:8100/announce \
  -H "content-type: application/json" \
  -d '{"token":"<your token>","text":"Maintenance at 18:00 UTC — a few seconds, refresh after."}'
```

- Clear: same call with `"text":""` (a restart also clears it)
- Without a token configured the endpoint answers 404



## License and attribution

The project is distributed under the [MIT License](LICENSE). The upstream
copyright notice is preserved as required by that license. CjChatBot branding
and fork maintenance are by Cjhackeryt.
