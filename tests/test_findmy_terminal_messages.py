"""Consumed Apple setup attempts must show a message, never a raw reason key."""
import json
from pathlib import Path

from custom_components.homecircle.findmy_flow import _TERMINAL_SIGNIN_ERRORS


def test_terminal_findmy_errors_have_config_and_options_abort_messages():
    root = Path(__file__).resolve().parents[1] / "custom_components/homecircle"
    for path in (root / "strings.json", root / "translations/en.json"):
        data = json.loads(path.read_text())
        for scope in ("config", "options"):
            for reason in _TERMINAL_SIGNIN_ERRORS:
                message = data[scope]["abort"].get(reason)
                assert isinstance(message, str) and len(message) > 20, (path.name, scope, reason)
                assert message != reason
