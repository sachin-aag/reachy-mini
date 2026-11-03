import asyncio

from reachy_mini_grokbot.config import load_settings
from reachy_mini_grokbot.mcp_server import RequireToken, allowed_hosts, start_mcp_thread


def _call(app, headers=(), query=b""):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "headers": list(headers), "query_string": query}
    asyncio.run(app(scope, receive, send))
    return sent[0]["status"]


async def _ok(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})


def test_token_required() -> None:
    app = RequireToken(_ok, "s3cret")
    assert _call(app) == 401
    assert _call(app, headers=[(b"authorization", b"Bearer wrong")]) == 401
    assert _call(app, headers=[(b"authorization", b"Bearer s3cret")]) == 200
    assert _call(app, query=b"token=s3cret") == 200


def test_mcp_refuses_to_start_without_token(monkeypatch) -> None:
    monkeypatch.setenv("MCP_TOKEN", "")
    assert start_mcp_thread(load_settings()) is None


def test_allowed_hosts_include_tunnel(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://reachy.example.com")
    hosts = allowed_hosts(load_settings())
    assert "reachy.example.com" in hosts
    assert "127.0.0.1:*" in hosts
