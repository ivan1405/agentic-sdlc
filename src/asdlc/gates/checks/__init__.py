"""Gate framework.

Design rules:
  1. Zero hard dependencies. These run in whatever CI the client already has.
  2. Every check is tool-blind. It inspects git + files, never an agent.
  3. A crashing check fails the build. Gates that fail open are theatre.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

Status = Literal["pass", "fail", "warn", "skip"]


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str = ""
    details: list[str] = field(default_factory=list)


@dataclass
class Context:
    root: Path
    policy: dict[str, Any]
    changed_files: list[str]
    base: str
    stage: str
    changes_dir: str
    specs_dir: str

    def cfg(self, check: str, key: str, default: Any = None) -> Any:
        return self.policy.get("checks", {}).get(check, {}).get(key, default)

    def matches(self, patterns: list[str], files: list[str] | None = None) -> list[str]:
        import fnmatch

        files = self.changed_files if files is None else files
        out = []
        for f in files:
            if any(fnmatch.fnmatch(f, p) for p in patterns):
                out.append(f)
        return out

    @property
    def touched_changes(self) -> list[Path]:
        """Change folders referenced by this diff."""
        ids = set()
        for f in self.changed_files:
            m = re.match(rf"{re.escape(self.changes_dir)}/([^/]+)/", f)
            if m:
                ids.add(m.group(1))
        return [self.root / self.changes_dir / i for i in sorted(ids)]

    @property
    def production_files(self) -> list[str]:
        return self.matches(self.policy.get("source_globs", ["src/**"]))


@dataclass
class Check:
    name: str
    stage: Literal["spec", "code", "any"]
    run: Callable[[Context], CheckResult]


# --------------------------------------------------------------------------- #
# policy loading
# --------------------------------------------------------------------------- #
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

    Only used when PyYAML is unavailable. Supports exactly what policy.yaml uses.
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


def load_policy(root: Path, pkg: Path) -> dict:
    path = root / ".asdlc" / "policy.yaml"
    if not path.exists():
        path = pkg / "gates" / "policy.yaml"
    text = path.read_text()
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        return _mini_yaml(text)


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #
from asdlc.gates.checks import (  # noqa: E402
    coverage,
    drift,
    human_approval,
    security,
    spec_lint,
    spec_present,
    traceability,
)

ALL_CHECKS: list[Check] = [
    Check("spec-present", "code", spec_present.run),
    Check("spec-lint", "spec", spec_lint.run),
    Check("traceability", "code", traceability.run),
    Check("spec-drift", "code", drift.run),
    Check("coverage-delta", "code", coverage.run),
    Check("security-scan", "code", security.run),
    Check("human-approval", "code", human_approval.run),
]
