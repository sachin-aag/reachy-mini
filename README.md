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

Give a [Grok Bot](https://x.ai/bot) chief of staff a Reachy Mini body.

There is **no Grok Bot chat API**. This app uses the supported pieces:

1. A **routine webhook** to wake the chief of staff with what a human said to the robot.
2. **MCP tools** (and matching REST) so that Bot — or a specialist it hands off to — can `speak`, `look`, `show`, `dance`, and `rest`.
3. Motion from [ClawBody](https://github.com/tomrikert/clawbody) and [reachy-mini-mcp](https://github.com/jackccrawford/reachy-mini-mcp): built-in expressions, Pollen recorded emotions/dances, `[move:name]` speech markers.

Gmail stays on Grok Bot plugins. The robot never holds your mailbox tokens.

## How it fits together

```
You type (or later, speak) on Reachy
        → POST webhook → Chief of Staff Grok Bot
        → optional @handoff to other Bots
        → MCP speak/show/look → Reachy Mini
```

A webhook HTTP 200 means the run **started**. Nothing is spoken until the Bot calls `speak`.

Paste the routine text from [`routines/chief-of-staff.md`](routines/chief-of-staff.md) into the chief of staff Bot.

## Setup

### Python environment (macOS / Linux)

The repo does not ship a `.venv` folder (it is gitignored). Create it once, then activate it in every new terminal:

```bash
cd reachy-mini
./scripts/setup.sh          # creates .venv, pip install -e ., copies .env if missing
source .venv/bin/activate   # required in each new shell before running the app
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
cp .env.example .env
```

Install the [Reachy Mini SDK](https://github.com/pollen-robotics/reachy_mini) in the same venv if `reachy-mini` is not already installed (`reachy-mini-daemon` must be on your PATH).

### Grok Bot + run

1. Start the daemon (`reachy-mini-daemon` on Lite, or `--sim` without hardware).
2. Edit `.env`: `GROK_BOT_WEBHOOK_URL`, `GROK_BOT_WEBHOOK_KEY`, and `PUBLIC_BASE_URL` (tunnel to MCP port `8765`).
3. On the chief of staff Bot: Routines → When to run → Webhook. Save, keep **Active**. Paste [`routines/chief-of-staff.md`](routines/chief-of-staff.md). Add a **custom MCP** connector (tunneled URL) and `@` it from the Bot.
4. With the venv activated:

```bash
python -m reachy_mini_grokbot.main
```

Open the control UI at http://127.0.0.1:8042/

Optional: `XAI_API_KEY` (Grok Voice) or `DEEPGRAM_API_KEY` so `speak` plays audio. Without them, the robot still gestures.

## Tools

| Tool | Purpose |
|------|---------|
| `speak` | TTS + `[move:curious]` markers |
| `look` | `left` / `right` / `up` / `down` / `front`, or roll/pitch/yaw |
| `show` | Built-in emotions, or `move=` for Pollen recorded clips |
| `dance` | Recorded dances |
| `rest` | `neutral` / `sleep` / `wake` |
| `snap` | Camera JPEG |
| `discover` | List recorded `emotions` or `dances` |

REST fallback (if MCP is blocked): `POST /tools/speak` with `{"name":"speak","arguments":{"text":"Hello"}}`.

## Credits

Apache 2.0. Motion maps and choreography markers follow ClawBody (Tom Rikert) and reachy-mini-mcp (Jack Crawford), on top of the Pollen Reachy Mini SDK.
