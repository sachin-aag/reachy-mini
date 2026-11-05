---
title: Reachy Mini Grok Bot
emoji: 🤖
colorFrom: red
colorTo: blue
sdk: static
pinned: false
short_description: Reachy Mini body for a Grok Bot chief of staff
tags:
  - reachy_mini
  - reachy_mini_python_app
---

# Reachy Mini × Grok Bot

Give a [Grok Bot](https://x.ai/bot) chief of staff a Reachy Mini body. Runs **on the robot** with remote mode control from your phone.

## Architecture

```
Phone/Web (remote control)
        ↓  GET /api/reachy/state  (mode: idle|scribe|docs_chat)
Reachy Mini Wireless (this app)
        ↓  mode change → ModeController
        ↓  idle: listening pose, await commands
        ↓  scribe: mic → Gemini STT → Google Doc
        ↓  docs_chat: mic → Gemini Live API → spoken answers grounded in Drive docs
```

The app polls a remote control endpoint to switch between modes. Sachin controls the robot from his phone; the robot runs autonomously.

## Features

- **Remote mode control**: Poll `{REACHY_CONTROL_URL}/api/reachy/state` with ETag caching
- **Gemini-powered AI**: TTS, STT, and conversational AI via Google Gemini API
- **Mode handlers**: idle (rest), scribe (dictation), docs_chat (voice Q&A)
- **MCP tools**: speak, look, show, dance, rest, snap, discover
- **Fallback providers**: xAI and Deepgram as optional TTS/STT alternatives
- **Settings UI**: Configure via web UI at port 8042

## Quick Start (Development on Mac)

```bash
# 1. Clone and install
git clone <this-repo>
cd reachy_mini_grokbot
pip install -e ".[dev]"

# 2. Configure (copy .env.example to .env and fill in)
cp .env.example .env
# Required: GEMINI_API_KEY
# Optional: REACHY_CONTROL_URL, REACHY_CONTROL_TOKEN

# 3. Start the daemon (simulator mode for dev)
reachy-mini-daemon --sim

# 4. Run the app
python -m reachy_mini_grokbot.main
```

Open http://127.0.0.1:8042 for the settings UI.

## Installation on Reachy Mini Wireless

### Option A: Offline install (recommended for conferences/demos)

```bash
# From your dev machine, copy the package to the robot
scp -r /path/to/reachy_mini_grokbot pollen@reachy-mini.local:/tmp/reachy_mini_grokbot

# SSH to the robot and install
ssh pollen@reachy-mini.local
/venvs/apps_venv/bin/pip install /tmp/reachy_mini_grokbot

# Create config file with secrets (chmod 600 for security)
mkdir -p ~/.reachy_grokbot
cat > ~/.reachy_grokbot/config.json << 'EOF'
{
  "GEMINI_API_KEY": "your-gemini-key",
  "REACHY_CONTROL_URL": "https://creators-ecosystem.de",
  "REACHY_CONTROL_TOKEN": "your-control-token",
  "GOOGLE_APPLICATION_CREDENTIALS": "/home/pollen/.reachy_grokbot/service-account.json"
}
EOF
chmod 600 ~/.reachy_grokbot/config.json

# Copy your Google service account JSON if using scribe/docs_chat modes
scp /path/to/service-account.json pollen@reachy-mini.local:~/.reachy_grokbot/

# Start the app via the daemon REST API
curl -X POST http://reachy-mini.local:8000/api/apps/start-app/reachy_mini_grokbot
```

### Option B: Hugging Face Space install

```bash
# Install from a published HF Space (must be public or use HF token)
curl -X POST http://reachy-mini.local:8000/api/apps/install \
  -H "Content-Type: application/json" \
  -d '{"name": "reachy_mini_grokbot", "source_kind": "hf_space", "url": "https://huggingface.co/spaces/<user>/reachy_mini_grokbot"}'
```

**Private HF Space note**: The Reachy Mini dashboard does not prompt for HF tokens. For private spaces, either:
1. Make the space public (not recommended for apps with secrets)
2. Use offline install (Option A) — recommended
3. Set `HF_TOKEN` in the robot's environment before installing

### Updating the app

```bash
# Offline update
scp -r /path/to/reachy_mini_grokbot pollen@reachy-mini.local:/tmp/
ssh pollen@reachy-mini.local "/venvs/apps_venv/bin/pip install --upgrade /tmp/reachy_mini_grokbot"
curl -X POST http://reachy-mini.local:8000/api/apps/stop-current-app
curl -X POST http://reachy-mini.local:8000/api/apps/start-app/reachy_mini_grokbot

# Or via REST API for HF Space apps
curl -X POST http://reachy-mini.local:8000/api/apps/update/reachy_mini_grokbot
```

## Configuration

Configuration loads from environment variables first, then falls back to `~/.reachy_grokbot/config.json`.

### Required

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google AI Studio API key ([get one here](https://aistudio.google.com/apikey)) |

### Remote Control

| Variable | Default | Description |
|----------|---------|-------------|
| `REACHY_CONTROL_URL` | `https://creators-ecosystem.de` | Base URL for mode control API |
| `REACHY_CONTROL_TOKEN` | — | Bearer token for control endpoint |
| `REACHY_CONTROL_POLL_INTERVAL` | `3.0` | Seconds between polls |
| `REACHY_CONTROL_OFFLINE_TIMEOUT` | `30.0` | Return to idle after this many seconds offline |

### Google Drive (for scribe/docs_chat modes)

| Variable | Description |
|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON file |

### Voice Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_PROVIDER` | `gemini` | `gemini`, `xai`, or `deepgram` |
| `STT_PROVIDER` | `gemini` | `gemini` or `deepgram` |
| `TTS_VOICE` | `Kore` | Gemini: Kore/Charon/Fenrir/Aoede/Puck/Leda/Orus/Zephyr; xAI: ara/eve/leo/rex/sal |
| `TTS_LANGUAGE` | `en` | BCP-47 language code |
| `STT_CUSTOM_VOCABULARY` | `Reachy,Reachy Mini,Grok,Grok Bot,Sachin` | Comma-separated names for better STT recognition |

### Model Overrides

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_TTS_MODEL` | `gemini-3.8-flash-tts` | TTS model |
| `GEMINI_STT_MODEL` | `gemini-3.5-transcribe` | Batch STT model |
| `GEMINI_STT_LIVE_MODEL` | `gemini-3.5-transcribe-live` | Live streaming STT |
| `GEMINI_LIVE_MODEL` | `gemini-3.8-live` | Bidirectional audio conversation |
| `GEMINI_CHAT_MODEL` | `gemini-3.8-flash` | Text generation |

### Fallback Providers (optional)

| Variable | Description |
|----------|-------------|
| `XAI_API_KEY` | xAI API key for TTS fallback |
| `DEEPGRAM_API_KEY` | Deepgram API key for TTS/STT fallback |

### Grok Bot Integration (optional)

| Variable | Description |
|----------|-------------|
| `GROK_BOT_WEBHOOK_URL` | Routine webhook URL |
| `GROK_BOT_WEBHOOK_KEY` | Routine webhook key |
| `MCP_TOKEN` | Token for MCP server authentication |
| `MCP_HOST` | MCP bind address (default: 127.0.0.1) |
| `MCP_PORT` | MCP port (default: 8765) |
| `PUBLIC_BASE_URL` | Public URL for MCP tunnel |

## Remote Control API

The app polls `GET {REACHY_CONTROL_URL}/api/reachy/state` with:
- Header: `Authorization: Bearer {REACHY_CONTROL_TOKEN}`
- Supports `ETag` / `If-None-Match` → 304 Not Modified

Response:
```json
{
  "mode": "idle" | "scribe" | "docs_chat",
  "targetDocId": "google-doc-id",
  "docIds": ["doc1", "doc2"],
  "sourceFolderId": "folder-id",
  "version": 1,
  "updatedAt": "2024-01-01T00:00:00Z"
}
```

## Modes

### Idle
Robot at rest, listening pose. Responds to MCP/REST tool calls.

### Scribe (stub)
Continuous transcription to a Google Doc. Uses Gemini Live API (`gemini-3.5-transcribe-live`) with custom vocabulary for better name recognition.

### Docs Chat (stub)
Voice Q&A grounded in Google Drive documents. Uses Gemini Live API (`gemini-3.8-live`) for bidirectional audio conversation with doc context.

## TTS Provider Notes

### Gemini (default)
- Model: `gemini-3.8-flash-tts`
- Output: WAV 24kHz mono PCM
- Voices: Kore, Charon, Fenrir, Aoede, Puck, Leda, Orus, Zephyr
- Style goes in `speech_metadata`, not the text (it speaks text literally)

### xAI (fallback)
- Endpoint: `POST https://api.x.ai/v1/tts`
- **Requires a funded API key** (not OAuth subscription tokens)
- 403 error means the key lacks TTS permission
- Voices: ara, eve, leo, rex, sal

### Deepgram (fallback)
- Model: aura-2-saturn-en

## Tools

| Tool | Purpose |
|------|---------|
| `speak` | TTS with `[move:curious]` markers |
| `look` | Named direction or roll/pitch/yaw |
| `show` | Built-in emotions or recorded clips |
| `dance` | Recorded dances |
| `rest` | neutral / sleep / wake |
| `snap` | Camera JPEG |
| `discover` | List emotions or dances |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests (skip MCP test which needs reachy_mini SDK)
python -m pytest tests/test_config.py tests/test_control_client.py tests/test_mode_controller.py -v

# Check app structure
reachy-mini-app-assistant check .
```

## Credits

Apache 2.0. Motion maps follow [ClawBody](https://github.com/tomrikert/clawbody) and [reachy-mini-mcp](https://github.com/jackccrawford/reachy-mini-mcp), on top of the Pollen Reachy Mini SDK.
