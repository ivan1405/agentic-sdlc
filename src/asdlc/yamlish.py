"""Zero-dependency YAML loading, shared by every config file the standard reads
(gates/policy.yaml, assets/agents/roles.yaml, ...).

Uses PyYAML when the environment happens to have it (a client's own project
often does); otherwise falls back to a hand-rolled parser covering exactly the
subset of YAML this repo's own config files use — nested maps, scalar lists,
flow collections (`{a: 1}` / `[a, b]`), quoted/bool/null/number scalars.
`dependencies = []` in pyproject.toml is deliberate: these gates run in
whatever CI the client already has, so PyYAML is opportunistic, never required.
"""
from __future__ import annotations

import re
from typing import Any


def load(text: str) -> dict:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        return _mini_yaml(text)


def _split_flow(s: str) -> list[str]:
    """Split a flow collection body on commas that are not nested or quoted."""
    parts, buf, depth, quote = [], "", 0, ""
    for ch in s:
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(buf); buf = ""
            continue
        buf += ch
    parts.append(buf)
    return parts


def _mini_yaml(text: str) -> dict:
    """Minimal YAML subset parser: nested maps, scalar lists, scalars.

    Only used when PyYAML is unavailable. Supports exactly what this repo's
    own YAML config files use.
    """
    root: dict = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    def coerce(v: str) -> Any:
        v = v.strip()
        if v.startswith("{") and v.endswith("}"):
            out: dict = {}
            for part in _split_flow(v[1:-1]):
                if not part.strip():
                    continue
                k, _, val = part.partition(":")
                out[k.strip()] = coerce(val)
            return out
        if v.startswith("[") and v.endswith("]"):
            return [coerce(x) for x in _split_flow(v[1:-1]) if x.strip()]
        if v.startswith(("'", '"')) and v.endswith(("'", '"')) and len(v) > 1:
            return v[1:-1]
        low = v.lower()
        if low in ("true", "yes"):
            return True
        if low in ("false", "no"):
            return False
        if low in ("null", "~", ""):
            return None
        if re.fullmatch(r"-?\d+", v):
            return int(v)
        if re.fullmatch(r"-?\d+\.\d+", v):
            return float(v)
        return v

    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = raw.split(" #")[0].rstrip()
        indent = len(line) - len(line.lstrip())
        body = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if body.startswith("- "):
            if not isinstance(parent, (_Lazy, list)):
                raise ValueError(f"list item under a non-list key: {body!r}")
            parent.append(coerce(body[2:]))
            continue
        key, _, val = body.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "":
            # peek: could be a map or a list; decide lazily via a proxy dict
            container: Any = _Lazy()
            parent[key] = container
            stack.append((indent, container))
        else:
            parent[key] = coerce(val)
    return _resolve(root)


class _Lazy(dict):
    """Dict that turns into a list on first `- ` item."""

    _items: list

    def __init__(self):
        super().__init__()
        self._items = []

    def append(self, v):
        self._items.append(v)


def _resolve(node):
    if isinstance(node, _Lazy):
        if node._items and not dict.keys(node):
            return [_resolve(i) for i in node._items]
        if not node._items and not dict.keys(node):
            return None          # `key:` with nothing under it — PyYAML says None
        return {k: _resolve(v) for k, v in node.items()}
    if isinstance(node, dict):
        return {k: _resolve(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve(i) for i in node]
    return node
