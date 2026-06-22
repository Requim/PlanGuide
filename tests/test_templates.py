import json
from pathlib import Path


def test_system_templates_have_no_replacement_question_marks():
    root = Path(__file__).resolve().parents[1] / "planguide" / "templates"
    bad = []
    for path in root.glob("*.json"):
        _collect_bad_strings(json.loads(path.read_text(encoding="utf-8")), str(path), bad)
    assert bad == []


def _collect_bad_strings(value, loc: str, bad: list):
    if isinstance(value, dict):
        for key, item in value.items():
            _collect_bad_strings(item, f"{loc}.{key}", bad)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _collect_bad_strings(item, f"{loc}[{index}]", bad)
        return
    if isinstance(value, str) and "?" in value:
        bad.append((loc, value))
