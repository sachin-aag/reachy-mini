from reachy_mini_grokbot.choreography import estimate_speech_seconds, parse_choreographed_text


def test_parse_plain_text() -> None:
    assert parse_choreographed_text("hello") == [{"type": "text", "content": "hello"}]


def test_parse_move_markers() -> None:
    segments = parse_choreographed_text("Hi [move:curious] there [move:joy]")
    assert segments == [
        {"type": "text", "content": "Hi "},
        {"type": "move", "name": "curious"},
        {"type": "text", "content": " there "},
        {"type": "move", "name": "joy"},
    ]


def test_estimate_speech_seconds_has_a_floor() -> None:
    assert estimate_speech_seconds("ok") == 1.0
    assert estimate_speech_seconds("x" * 45) == 3.0
