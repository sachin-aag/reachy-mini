from pathlib import Path

import toml
import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_reachy_mini_python_app_tag() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    _, rest = text.split("---", 1)
    meta_block, _ = rest.split("---", 1)
    meta = yaml.safe_load(meta_block)
    assert meta["title"]
    assert "reachy_mini" in meta["tags"]
    assert "reachy_mini_python_app" in meta["tags"]


def test_pyproject_entrypoint_matches_assistant_contract() -> None:
    pyproject = toml.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    name = pyproject["project"]["name"]
    entry = pyproject["project"]["entry-points"]["reachy_mini_apps"][name]
    assert entry == "reachy_mini_grokbot.main:ReachyMiniGrokbot"
    main = (ROOT / "reachy_mini_grokbot" / "main.py").read_text(encoding="utf-8")
    assert "class ReachyMiniGrokbot(ReachyMiniApp)" in main
    assert (ROOT / "index.html").exists()
    assert (ROOT / "style.css").exists()
