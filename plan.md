# Plan: Reachy Mini body for a Grok Bot chief of staff

## Decision (confirmed)

The brain is a **Grok Bot chief of staff**, not the Grok model API and not OpenClaw. Reachy Mini is the body.

Inbound: a **routine webhook** (Tom Coustols / Cursor). There is no Grok Bot chat API.

Outbound: **MCP tools** (and the same tools as REST) so the chief of staff — or a Bot it hands off to — can `speak`, `look`, `show`, `dance`, and `rest` on the robot.

Motion: take the useful bits from [ClawBody](https://github.com/tomrikert/clawbody) and [reachy-mini-mcp](https://github.com/jackccrawford/reachy-mini-mcp) (queued gestures, recorded emotion/dance libraries, `[move:name]` speech markers). Do not take OpenClaw as the brain or OpenAI Realtime as the conversation loop.

## Architecture

```
You (typed in the app UI, later STT)
        ↓  POST webhook  { utterance, source, session_id }
Chief of Staff Grok Bot  (routine, Active)
        ↓  @handoff to specialist Bots when needed
        ↓  MCP or REST  speak / show / look / rest
Reachy Mini (daemon + this app)
```

A webhook 200 means the run **started**. The spoken reply is not in that HTTP response. The Bot must call Reachy tools to talk and move.

## App flavour

Python Reachy Mini app (`reachy_mini_python_app`) so it is discoverable and can sit next to the daemon. Settings UI on port 8042. MCP on port 8765 (streamable HTTP) for a Grok Bot custom connector. Tunnel that port if the Bot computer is in the cloud.

## Out of scope for this revision

- Sub-second duplex voice (that is ClawBody + OpenAI Realtime, a different product)
- Unofficial Grok Bot host-gateway SDK
- Putting Gmail OAuth on the robot (Grok Bot Gmail plugin stays on the Bot)
- Hugging Face Space publish (`reachy-mini-app-assistant --publish`) until you are logged in to HF
