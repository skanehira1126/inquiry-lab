"""Unambiguous JSON input shared by inspection and state persistence."""

import json
from typing import Any


def _read_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if "." in key:
            raise ValueError(f"JSON keys containing '.' are not supported: {key!r}")
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def parse_json(source: str) -> Any:
    """Reject duplicate/dotted keys and nonstandard numeric constants."""
    return json.loads(source, object_pairs_hook=_read_object, parse_constant=_reject_constant)
