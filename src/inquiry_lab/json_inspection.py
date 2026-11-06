"""Read-only, shallow inspection of JSON documents."""

import json
from itertools import islice
from pathlib import Path
from typing import Any

from inquiry_lab.json_parsing import parse_json


class JsonArgumentError(ValueError):
    """Invalid JSON selection or display options (CLI exit code 2)."""


def _display(value: Any) -> str:
    if isinstance(value, dict):
        return f"<object: {len(value)} keys>"
    if isinstance(value, list):
        return f"<array: {len(value)} items>"
    text = json.dumps(value, ensure_ascii=False, allow_nan=False)
    return text if len(text) <= 160 else text[:160] + "… [truncated]"


def inspect_json(path: Path, *, keys: list[str] | None = None, head: int = 20) -> str:
    """Show one level; repeated keys and dotted paths select successive children.

    Read the whole UTF-8 document before selecting. Dotted or duplicate object
    keys anywhere in the document are rejected to keep references unambiguous.
    Display limits do not limit file reading or parsing memory.
    """
    if head < 0:
        raise JsonArgumentError("--head must be non-negative")
    segments = [segment for key in keys or [] for segment in key.split(".")]
    if any(not segment for segment in segments):
        raise JsonArgumentError("--key must contain non-empty dot-separated segments")

    value = parse_json(path.read_text(encoding="utf-8-sig"))

    for segment in segments:
        if isinstance(value, dict):
            if segment not in value:
                raise JsonArgumentError(f"JSON key not found: {segment!r}")
            value = value[segment]
        elif isinstance(value, list):
            if not segment.isascii() or not segment.isdecimal():
                raise JsonArgumentError(f"expected a non-negative array index: {segment!r}")
            index = int(segment)
            if index >= len(value):
                raise JsonArgumentError(f"array index out of range: {segment}")
            value = value[index]
        else:
            raise JsonArgumentError(f"cannot select {segment!r} from a scalar JSON value")

    if isinstance(value, dict):
        lines = [f"TYPE object; keys: {len(value)}"]
        lines.extend(
            f"{_display(key)}: {_display(item)}" for key, item in islice(value.items(), head)
        )
    elif isinstance(value, list):
        lines = [f"TYPE array; items: {len(value)}"]
        lines.extend(
            f"[{index}]: {_display(item)}" for index, item in islice(enumerate(value), head)
        )
    else:
        return _display(value) + "\n"
    omitted = max(0, len(value) - head)
    if omitted:
        lines.append(f"OMITTED {omitted} entries; use --head to show more")
    return "\n".join(lines) + "\n"
