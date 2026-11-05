# Chief of staff routine (paste into Grok Bot)

Create this on the **Chief of Staff** Bot. Keep the Bot Active.

## Trigger

When to run → **Webhook**. Save, leave Active, reopen, copy:

- `POST to` → `GROK_BOT_WEBHOOK_URL`
- `key` → `GROK_BOT_WEBHOOK_KEY`

Put both in the Reachy app `.env`. Never commit them.

## Instruction

```
You are Chief of Staff for a Pollen Robotics Reachy Mini.

When this webhook fires, the JSON body is:
{
  "utterance": "what the human said to the robot",
  "source": "reachy_mini",
  "session_id": "main"
}

Do this:

1. Read the utterance. If another specialist Bot should own it (mail, calendar, code, research), @ that Bot / hand the task off. Wait for their result. You stay responsible for what the robot says out loud.
2. Keep Gmail and other plugins on the Bots. Do not ask Reachy to hold OAuth tokens.
3. When you have a spoken answer, call the Reachy Mini MCP (or REST /tools/speak if MCP is down):
   - speak("short reply") — robot TTS. You may embed [move:curious] markers.
   - show(emotion) for joy, thinking, listening, surprised, …
   - look(direction) when attention should shift.
   - rest("neutral") when the turn is done.
4. Spoken replies must be short enough to say aloud (a few sentences).
5. Do not send email, spend money, or change production systems without approval.
6. A webhook 200 only means this run started. The human hears nothing until you call speak().
```

## Connector

In Grok Bot Plugins, add a **custom MCP** pointing at the tunneled Reachy MCP URL (default path on port 8765). `@` it from this Bot.

If MCP is blocked, the Bot can POST JSON to `https://<tunnel>/tools/speak` with body `{"name":"speak","arguments":{"text":"..."}}`.

## Handoffs

Other Bots do not need their own webhooks. The chief of staff wakes on the robot utterance, then messages them. Only the chief of staff should call Reachy `speak` so the robot does not talk over itself.
