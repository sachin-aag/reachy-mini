# Plan: Reachy Mini talking to Grok Bot

## Direct answer

**Not through an official Grok Bot API.** A Reachy Mini app cannot currently open a supported chat/voice session to a named Bot the way the Grok Bot desktop or phone app can.

That is a different product from **Grok** (the model / Voice API at `api.x.ai`). You asked for [Grok Bot](https://x.ai/bot): persistent named teammates with their own cloud computer, memory, plugins, and routines. Official docs: [Grok Bot overview](https://docs.x.ai/grok-bot/overview).

xAI documents how *you* message a Bot (text, dictate, desktop voice chat) and how a Bot uses **plugins / custom MCP servers**. It does not document a public REST/WebSocket API for a third-party robot to send utterances into a Bot conversation and get replies back.

So:

| What you want | Possible today? |
|---|---|
| Reachy Mini speaks with **Grok the model** (OpenAI-compatible / Voice API) | Yes. That is the official conversation-app path. **You said this is not what you want.** |
| Reachy Mini is the body for **Grok Bot** (Bot uses the robot via tools) | **Yes, this is the supported direction.** Custom MCP connector + Reachy daemon. |
| Reachy Mini is a phone-like client that chats with your named Bot | **No official API.** Unofficial host-gateway hacks exist; they are unsupported and fragile. |

## What Grok Bot actually is

From the official overview:

- A Bot is one persistent, named teammate (not a stateless `chat.completions` call).
- Bots share one cloud computer (browser, filesystem, terminal).
- You work with them in the Grok Bot app (desktop + mobile). Voice chat is in that app, not a robot SDK.
- Bots use Marketplace plugins and **custom MCP servers** that must be reachable on the public internet.
- Cursor account integrations can start a **routine** from Slack / GitHub events. That is event automation, not a conversational robot client.

## Recommended architecture (official)

**Invert the conversation: Grok Bot talks *to* Reachy Mini.**

```
You (Grok Bot app, text or voice)
        ↓
Named Grok Bot (cloud computer + memory)
        ↓  custom MCP plugin
Reachy Mini MCP (speak / listen / look / show / rest)
        ↓  daemon REST
Physical Reachy Mini
```

This matches Grok Bot's extension model ([custom MCP connectors](https://docs.x.ai/grok/connectors)) and Reachy's hardware API.

Concrete pieces:

1. Python Reachy Mini app (discoverable on Hugging Face) that starts/wraps an MCP server next to the robot daemon.
2. Tools at minimum: `speak`, `listen`, `look`, `show` (emotion), `rest`, `snap` (camera). Community reference: [jackccrawford/reachy-mini-mcp](https://github.com/jackccrawford/reachy-mini-mcp).
3. Public URL for the MCP server (tunnel if the daemon is on a laptop / Wireless robot). Grok Bot requires a reachable MCP endpoint.
4. In Grok Bot: Marketplace → add custom MCP connector → `@` that connector from the Bot you want embodied.

Result: you talk to your Bot in the Grok Bot app; the Bot moves Reachy's head, plays emotions, and can speak through the robot's speaker via the `speak` tool.

This is **not** "Reachy's mic streams into Grok Bot voice chat." Desktop voice stays in the Grok Bot client unless we later add a listen/speak loop on the robot and have the Bot consume `listen` transcripts.

## Other options (weaker)

### A. Robot as the conversation surface (you talk to Reachy, Reachy talks to the Bot)

Blocked officially. There is no documented "send this user utterance to Bot Ada and return the reply" API.

An unofficial TypeScript client ([adam91holt/grokbot-sdk](https://github.com/adam91holt/grokbot-sdk)) talks to a **running Grok Bot host gateway** (`POST /api/<command>`, token from `gateway.json`). That is not an xAI product API. It needs a reachable host, a gateway token, and it can break on host updates. I will not build this unless you explicitly accept that risk.

### B. Slack / GitHub as a message bus

Grok Bot routines can fire on Slack or GitHub events. Reachy could post a transcript to Slack and wait. Latency and turn-taking would be poor compared with a live conversation.

### C. Grok *model* conversation app

Pollen's conversation template (`reachy-mini-app-assistant create --template conversation`) and xAI Voice API would make Reachy a Grok-voiced chatbot. Easy, well documented, **not Grok Bot** (no named teammate, no shared computer, no Bot memory/plugins).

## Flavour choice

Default in the Reachy Mini agent guide is a **JS web app**. This use case needs **Python** (or Python + `static/` UI):

- MCP server and daemon control run next to the robot.
- Speech, camera, and motion are on-robot / daemon-side.
- Hugging Face discovery still wants a Python app tag today.

A JS Space can still be the *phone UI* (watch the camera, leave the session) while the Bot drives the robot through MCP.

## What I will not do until you answer

Reachy Mini `AGENTS.md` says: write `plan.md`, ask, then wait. I am stopping here instead of scaffolding the wrong app (a Grok-model conversation demo).

## Questions

Fill these in (or reply in chat). Defaults are in parentheses.

1. **Direction**
   - [ ] **Bot drives Reachy** via MCP (recommended)
   - [ ] Robot is the chat client talking *into* a named Bot (unofficial / likely blocked)
   - [ ] Something else: ________

2. **Hardware**
   - [ ] Lite (USB to a laptop)
   - [ ] Wireless (onboard CM4)
   - [ ] Simulator only for now
   - [ ] No robot yet

3. **Where should the human speak?**
   - [ ] Grok Bot app (phone/desktop); robot is the body
   - [ ] Reachy's mic and speaker; Bot is the brain
   - [ ] Both

4. **Do you already have a named Grok Bot** you want embodied (name: ________), or should the app work with whichever Bot has the Reachy plugin enabled?

5. **MCP hosting**
   - [ ] I can expose a public HTTPS MCP URL (or use a tunnel)
   - [ ] Daemon stays on LAN only
   - [ ] Not sure

6. **App flavour**
   - [ ] Python MCP app (recommended)
   - [ ] Python app + simple web UI in `static/`
   - [ ] JS Space only (would still need a backend for MCP/secrets)

## After you confirm

If you pick **Bot drives Reachy**:

1. Scaffold with `reachy-mini-app-assistant create --template conversation` *or* a minimal Python app plus MCP (I'll choose the smaller surface unless you want the full conversation UI).
2. Wrap Reachy daemon commands as MCP tools.
3. Document Grok Bot plugin setup (custom connector URL, `@` the server, tunnel).
4. Keep secrets out of git. No Grok Bot gateway tokens.

If you pick **robot chats into a Bot**, I need you to accept the unofficial host-gateway path in writing before any code.
