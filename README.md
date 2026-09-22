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

1. Install the [Reachy Mini SDK](https://github.com/pollen-robotics/reachy_mini) and start the daemon (`reachy-mini-daemon` or `--sim`).
2. Copy `.env.example` to `.env`.
3. On the chief of staff Bot: Routines → When to run → Webhook. Save, keep **Active**, copy URL and key into `.env` as `GROK_BOT_WEBHOOK_URL` and `GROK_BOT_WEBHOOK_KEY`.
4. Tunnel MCP port `8765` (and optionally `8042`) to a public HTTPS URL. Put that base in `PUBLIC_BASE_URL`. Add it as a Grok Bot **custom MCP** connector and `@` it from the Bot.
5. Run:

```bash
pip install -e .
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
