# Transcript Puller

A small web app that pulls the transcript of a YouTube or TikTok video. Paste a link and
you get the captions as text you can search, copy, or download as `.txt`, `.srt`, `.vtt`,
or `.json`, or tap **Send to Claude** to hand the transcript straight to Claude. It also runs
as an [MCP server](#use-it-from-claude-mcp-server), so Claude can fetch a transcript itself
when you paste a link in a chat. Everything runs on your own computer; no third-party
transcript service is involved.

- **YouTube**: `youtube.com/watch`, `youtu.be`, Shorts, live and embed links (also
  `m.` and `music.` hosts, or a bare 11-character video ID).
- **TikTok**: `tiktok.com/@user/video/…`, `vm.tiktok.com/…`, `vt.tiktok.com/…` and
  `tiktok.com/t/…` short links.
- Videos with **no captions** can optionally be transcribed from their audio with local
  speech-to-text (Whisper). This is off unless you install it and tick the box.

The result always says where the text came from: creator captions, auto-generated
captions, or speech-to-text. A video with no captions returns a clear "no captions"
error, never a blank or made-up transcript.

## Quick start

Needs Python 3.10+.

```bash
cd video-transcript-app
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>.

**Run it on your own computer.** YouTube and TikTok often bot-check or block requests
from cloud/datacenter IP addresses. From a home connection it generally just works. If
you have to host it on a server, see `TRANSCRIPT_PROXY` and `YTDLP_COOKIES_FILE` below.
To use it from your phone, see [Install it on your Android phone](#install-it-on-your-android-phone).

### Optional: speech-to-text for videos without captions

```bash
pip install -r requirements-whisper.txt
```

This adds [faster-whisper](https://github.com/SYSTRAN/faster-whisper). It runs on the CPU
and needs no system ffmpeg. The first transcription downloads the Whisper model (about
150 MB for the default `base` model) from Hugging Face. Once it's installed, a checkbox
appears in the UI. Speech-to-text runs only when a video has no usable captions, one video
at a time, for videos up to 20 minutes (configurable).

## Install it on your Android phone

The app can be installed on Android as a home-screen app. It opens full-screen with its own
icon, and it shows up in the **Share** menu of the YouTube and TikTok apps. The phone is the
screen; the app itself keeps running on your computer.

Android only installs apps served over HTTPS. The easiest way to get HTTPS, and to reach your
computer from anywhere, is [Tailscale](https://tailscale.com) (free for personal use):

1. Install Tailscale on your computer and on your phone, and sign in to the same account on both.
2. In the Tailscale admin console, open **DNS** and make sure **MagicDNS** and **HTTPS
   Certificates** are enabled.
3. On your computer, start the app (as in Quick start), then in a second terminal run:
   ```bash
   tailscale serve --bg 8000
   ```
   It prints your app's address, something like `https://my-laptop.tail1234.ts.net`. Run
   `tailscale serve status` to see it again, or `tailscale serve reset` to turn it off. If your
   Tailscale version uses different options, see Tailscale's
   [`serve` documentation](https://tailscale.com/kb/1312/serve).
4. On your phone, open that address in **Chrome**, tap **⋮ → Install app** (or **Add to Home
   screen**), and confirm.

Then, in the YouTube or TikTok app, tap **Share** on a video and choose **Transcripts**. The
transcript opens straight away. You can also tap **Paste** in the app after copying a link.

To ask Claude about the video, tap **Send to Claude** and pick the Claude app in the share
sheet. The transcript arrives in a new message, labelled with the video's title and link, ready
for your question. On a computer, the button copies the same text and links to Claude so you can
paste it into a new chat.

Only devices signed in to your Tailscale account can reach the app. If the computer is off or
the app isn't running, the phone app still opens, and it tells you it can't reach the server.

## Use it from Claude (MCP server)

`mcp_server.py` runs the same transcript pipeline as an
[MCP](https://modelcontextprotocol.io) server. Once it's added, paste a video link into a
Claude chat and ask about it ("get the transcript of https://youtu.be/… and summarize it").
Claude calls the server, which fetches the captions on your computer, and answers from the
full transcript.

You need two full paths from the Quick start install:

- **Python**: `/full/path/to/video-transcript-app/.venv/bin/python`
  (Windows: `C:\full\path\to\video-transcript-app\.venv\Scripts\python.exe`)
- **Server**: `/full/path/to/video-transcript-app/mcp_server.py`

Your MCP client starts the server itself; you don't run it in a terminal.

**Claude desktop app.** Open **Settings → Developer → Edit Config**, which opens
`claude_desktop_config.json`, and add:

```json
{
  "mcpServers": {
    "transcripts": {
      "command": "/full/path/to/video-transcript-app/.venv/bin/python",
      "args": ["/full/path/to/video-transcript-app/mcp_server.py"]
    }
  }
}
```

On Windows, write each `\` in the paths as `\\`. Restart Claude and the server shows up under
**Settings → Developer**. Keep the name `transcripts`: the Transcript Puller artifact looks for
a server with that name.

**Claude Code.**

```bash
claude mcp add --scope user transcripts -- /full/path/to/video-transcript-app/.venv/bin/python /full/path/to/video-transcript-app/mcp_server.py
```

**Other MCP clients** (your own agent setup, for example) can run the same command over stdio.
For a client that wants a URL instead, start it with `python mcp_server.py --http` and point
the client at `http://127.0.0.1:8765/mcp` (`--port` changes the port). It only listens on this
computer.

The server has one tool, `get_transcript`:

| Argument | Meaning |
|---|---|
| `url` | The YouTube or TikTok link (required). |
| `language` | A track `code` from an earlier result, e.g. `en` (creator captions) or `a.en` (auto-captions). |
| `speech_to_text` | Transcribe the audio when there are no captions (needs the Whisper install; slow). |
| `timestamps` | Start each paragraph with its `[m:ss]` time (default on). |

It answers with a short header (title, channel, link, caption source, length) followed by the
transcript in paragraphs, plus the timed lines as structured content for programs. Failures
come back as tool errors ending in the error `code` from the [API](#api) table, such as
`[no_transcript]` or `[upstream_blocked]`.

Claude on the web and in the phone app reach connectors from Anthropic's servers, so they
can't see a server on your computer. On your phone, use the
[home-screen app](#install-it-on-your-android-phone) and **Send to Claude** instead.

## How it works

```
YouTube:  youtube-transcript-api  ->  yt-dlp captions  ->  [speech-to-text]
TikTok:                               yt-dlp captions  ->  [speech-to-text]
```

1. The link is validated against an exact allowlist of YouTube/TikTok hosts and rebuilt
   into a canonical URL. The raw input is never handed to the downloaders.
2. **YouTube** first tries [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
   (a couple of small requests, no media download). If YouTube blocks that, it falls back
   to [yt-dlp](https://github.com/yt-dlp/yt-dlp).
3. **TikTok** goes through yt-dlp, which reads TikTok's own captions.
4. The caption track is chosen in this order:
   1. creator captions in your preferred language
   2. auto-captions in your preferred language
   3. creator captions in the spoken language
   4. auto-captions in the spoken language

   Machine-translated tracks are never offered. Every available track appears in the
   **Captions** dropdown.
5. The captions (json3, WebVTT or SRT) are parsed into timed lines and grouped into
   paragraphs. YouTube's "rolling" auto-captions, which repeat every line twice, are
   de-duplicated.
6. If there are no captions and you asked for speech-to-text, the audio is downloaded to a
   temporary folder, transcribed, and deleted.

Successful results are cached in memory for 30 minutes.

## Configuration

All settings are optional environment variables.

| Variable | Default | Meaning |
|---|---|---|
| `TRANSCRIPT_LANGUAGES` | `en` | Preferred caption languages, comma-separated (e.g. `es,en`). |
| `TRANSCRIPT_PROXY` | – | Proxy URL (`http://user:pass@host:port`) for YouTube/TikTok requests. |
| `YTDLP_COOKIES_FILE` | – | Netscape-format cookies file for yt-dlp (helps with "confirm you're not a bot"). |
| `TRANSCRIPT_TIMEOUT` | `20` | Per-request network timeout, seconds. |
| `TRANSCRIPT_CACHE_TTL` | `1800` | Cache lifetime in seconds (`0` disables the cache). |
| `TRANSCRIPT_CACHE_SIZE` | `128` | Max cached transcripts. |
| `WHISPER_ENABLED` | `true` | Set `false` to hide speech-to-text even if installed. |
| `WHISPER_MODEL` | `base` | Whisper model: `tiny`, `base`, `small`, `medium`, `large-v3`, … |
| `WHISPER_DEVICE` / `WHISPER_COMPUTE_TYPE` | `cpu` / `int8` | Use `cuda` / `float16` on an NVIDIA GPU. |
| `WHISPER_MAX_DURATION` | `1200` | Longest video (seconds) sent to speech-to-text. |
| `WHISPER_MAX_DOWNLOAD_MB` | `200` | Largest audio download for speech-to-text. |

## API

`POST /api/transcript`

```json
{ "url": "https://youtu.be/dQw4w9WgXcQ", "language": "a.en", "speech_to_text": false }
```

`language` is optional. Pass a `code` from the `tracks` list of an earlier response to
pick a specific track. Codes are `en` for creator captions and `a.en` for auto-captions.

Response (abridged):

```json
{
  "platform": "youtube", "video_id": "dQw4w9WgXcQ", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "…", "author": "…", "duration": 212.0, "thumbnail": "…",
  "track_code": "en", "language": "en", "language_name": "English",
  "kind": "manual", "provider": "youtube-transcript-api",
  "tracks": [{ "code": "en", "language": "en", "name": "English", "kind": "manual", "is_original": false }],
  "segments": [{ "start": 0.16, "end": 2.15, "text": "…" }],
  "paragraphs": [{ "start": 0.16, "text": "…" }],
  "text": "…", "word_count": 1234, "notes": []
}
```

`kind` is `manual` (creator captions), `auto` (platform auto-captions) or
`speech-to-text`. `notes` lists any fallbacks that were taken.

Errors always have the shape `{"error": {"code", "message", "details": []}}`:

| HTTP | `code` | When |
|---|---|---|
| 400 | `invalid_url`, `invalid_request` | Not a YouTube/TikTok video link, or a malformed request. |
| 404 | `no_transcript` | The video has no captions (and speech-to-text wasn't used). |
| 404 | `video_unavailable` | Removed, private, or region-locked. |
| 422 | `speech_to_text_unavailable` | Speech-to-text not installed, or the video is too long. |
| 429 | `speech_to_text_busy` | Another speech-to-text job is running. |
| 502 | `upstream_error` | YouTube/TikTok returned something unexpected. |
| 503 | `upstream_blocked` | YouTube/TikTok is blocking this server (bot check, IP block, rate limit). |

`GET /api/health` reports whether speech-to-text is available.

## Troubleshooting

- **"…is blocking requests from this server's IP address"**: run the app locally, or set
  `TRANSCRIPT_PROXY` (a residential proxy) and/or `YTDLP_COOKIES_FILE`.
- **Extraction suddenly fails for every video**: YouTube and TikTok change often. Update
  the extractors with `pip install -U yt-dlp youtube-transcript-api`.
- **yt-dlp warns about a missing JavaScript runtime**: recent yt-dlp versions want an
  external JS runtime (such as [Deno](https://deno.com/)) for full YouTube support.
  Without one, YouTube audio downloads for speech-to-text can fail. See yt-dlp's
  installation docs.

## Tests

```bash
pip install -r requirements-dev.txt
pytest                                 # backend
node --test tests/formats.test.mjs     # frontend export/format helpers
```

The tests run fully offline:

- The YouTube path drives the real `youtube-transcript-api` library through a fake HTTP
  adapter. The adapter replays recorded YouTube responses (see `tests/fixtures/README.md`).
- The yt-dlp caption and audio downloads run the real `yt-dlp` library against a local
  HTTP server.

## Limitations

- Captions come from the platform. Auto-generated captions and speech-to-text contain
  mistakes, especially with names and jargon.
- TikTok doesn't say which caption track is the original language, so with no
  preferred-language match the first track TikTok lists is used.
- TikTok timestamps aren't links: TikTok has no "open at this time" URL.
- Respect YouTube's and TikTok's terms of service and the creators' copyright when using
  transcripts.

## Layout

```
app/
  main.py         FastAPI app: routes, error mapping, security headers, static files
  mcp_server.py   MCP server exposing the get_transcript tool
  service.py      the fallback pipeline + in-memory cache
  urls.py         link validation and canonicalisation (host allowlist)
  youtube_api.py  YouTube via youtube-transcript-api (+ oEmbed for title/author)
  ytdlp_source.py YouTube/TikTok via yt-dlp: track listing, caption + audio download
  speech.py       optional faster-whisper speech-to-text
  captions.py     WebVTT / SRT / json3 parsers, paragraphing
  tracks.py       caption-track selection policy
  models.py       shared data shapes and error types
  config.py       environment-variable settings
mcp_server.py     launcher MCP clients run by path (works from any directory)
static/           the frontend (plain HTML/CSS/JS, no build step), plus the
                  installable-app files: manifest.json, sw.js, icons/
tests/            pytest suite + node formatter tests + fixtures
```
