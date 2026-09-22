from reachy_mini_grokbot.expressions import BUILTIN_EMOTIONS, EXPRESSIONS, LOOK_DIRECTIONS, list_builtin_emotions


def test_builtin_emotions_cover_clawbody_set() -> None:
    required = {"neutral", "curious", "joy", "thinking", "listening", "surprised", "focused"}
    assert required.issubset(set(BUILTIN_EMOTIONS))


def test_each_expression_has_head_and_antennas() -> None:
    for name, expr in EXPRESSIONS.items():
        assert len(expr["antennas"]) == 2, name
        assert expr["duration"] > 0, name
        head = expr["head"]
        assert {"z", "roll", "pitch", "yaw"} <= set(head), name


def test_look_directions() -> None:
    assert LOOK_DIRECTIONS["front"] == (0.0, 0.0, 0.0)
    assert LOOK_DIRECTIONS["left"][2] > 0
    assert list_builtin_emotions() == sorted(EXPRESSIONS)
