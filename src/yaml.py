"""Minimal YAML subset parser for offline test environments."""

from __future__ import annotations

from typing import Any


def safe_load(text: str) -> Any:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.strip()))
    if not lines:
        return None
    value, idx = _parse_block(lines, 0, lines[0][0])
    if idx != len(lines):
        raise ValueError("Failed to parse YAML content")
    return value


def _parse_block(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[Any, int]:
    if idx < len(lines) and lines[idx][1].startswith("- "):
        return _parse_list(lines, idx, indent)
    return _parse_dict(lines, idx, indent)


def _parse_list(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[list[Any], int]:
    out: list[Any] = []
    while idx < len(lines):
        cur_indent, content = lines[idx]
        if cur_indent < indent:
            break
        if cur_indent != indent or not content.startswith("- "):
            break
        item = content[2:].strip()
        if item == "":
            child, idx = _parse_block(lines, idx + 1, indent + 2)
            out.append(child)
            continue
        out.append(_parse_scalar(item))
        idx += 1
    return out, idx


def _parse_dict(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    while idx < len(lines):
        cur_indent, content = lines[idx]
        if cur_indent < indent:
            break
        if cur_indent != indent:
            raise ValueError(f"Invalid indentation: {content}")
        if ":" not in content:
            raise ValueError(f"Invalid mapping line: {content}")
        key, raw_value = content.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value == "":
            idx += 1
            if idx < len(lines) and lines[idx][0] > indent:
                child, idx = _parse_block(lines, idx, lines[idx][0])
                out[key] = child
            else:
                out[key] = {}
        else:
            out[key] = _parse_scalar(value)
            idx += 1
    return out, idx


def _parse_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "None"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.replace("_", "").isdigit() or (
        value.startswith("-") and value[1:].replace("_", "").isdigit()
    ):
        return int(value.replace("_", ""))
    try:
        if "." in value:
            return float(value)
    except ValueError:
        pass
    return value
