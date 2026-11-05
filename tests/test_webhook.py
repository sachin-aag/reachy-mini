import httpx

from reachy_mini_grokbot.webhook import SOURCE, build_payload, notify_chief_of_staff


def test_build_payload_strips_text() -> None:
    payload = build_payload("  inbox please  ", session_id="desk")
    assert payload == {"utterance": "inbox please", "source": SOURCE, "session_id": "desk"}


def test_build_payload_rejects_empty() -> None:
    try:
        build_payload("   ")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_notify_treats_200_as_accepted(monkeypatch) -> None:
    calls = {}

    class FakeResponse:
        status_code = 200
        text = "ok"

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            calls["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def post(self, url, json, headers):
            calls["url"] = url
            calls["json"] = json
            calls["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    result = notify_chief_of_staff("https://example.test/hook", "secret", "hello")
    assert result["accepted"] is True
    assert result["status_code"] == 200
    assert calls["headers"]["Authorization"] == "Bearer secret"
    assert calls["json"]["utterance"] == "hello"


def test_notify_requires_secrets() -> None:
    try:
        notify_chief_of_staff("", "", "hello")
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError")
