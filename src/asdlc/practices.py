"""Engineering-practice packs — the standard's opinionated, tool-agnostic
"how we write code here" layer.

Each pack is a self-contained Markdown doc under assets/practices/, starting
with `# <Title>` and a `<!-- summary: … -->` line. At `asdlc init` the selected
packs are copied into the client repo's docs/practices/ and referenced from a
lean `## Practices` section in the agent context file (AGENTS.md/CLAUDE.md), so
every agent reads them without bloating the hub. Selection is per-engagement.
These are guidance, not gated by `asdlc verify` — the point is that agents read
them, not that a check blocks on them.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
SUMMARY_RE = re.compile(r"^<!--\s*summary:\s*(.+?)\s*-->\s*$", re.M)


def _parse(path: Path) -> tuple[str, str]:
    text = path.read_text()
    title_m = TITLE_RE.search(text)
    summary_m = SUMMARY_RE.search(text)
    return (title_m.group(1) if title_m else path.stem,
            summary_m.group(1) if summary_m else "")


def available(assets: Path) -> list[tuple[str, str, str]]:
    """(name, title, summary) for every shipped pack, sorted by name."""
    return [(p.stem, *_parse(p)) for p in sorted((assets / "practices").glob("*.md"))]


def names(assets: Path) -> list[str]:
    return [n for n, _, _ in available(assets)]


def _section(entries: list[tuple[str, str, str]], inline_for_claude: bool) -> str:
    """The `## Practices` section for the context file — a lean pointer list,
    not the practice text itself (the hub stays small; the files carry detail)."""
    lines = [
        "## Practices",
        "",
        "How code is written in this repo. Read the relevant one before you act — "
        "these are standards, not suggestions.",
        "",
    ]
    for name, title, summary in entries:
        rel = f"docs/practices/{name}.md"
        lines.append(f"- [{title}]({rel})" + (f" — {summary}" if summary else ""))
    if inline_for_claude:
        # Claude Code follows @-imports; AGENTS.md-native tools read the links
        # above instead, so this block is additive, never the only reference.
        lines += ["", "<!-- Claude Code auto-loads these: -->"]
        lines += [f"@docs/practices/{name}.md" for name, _, _ in entries]
    return "\n".join(lines) + "\n"


def install(root: Path, assets: Path, selected: list[str], *,
            inline_for_claude: bool = False, force: bool = False) -> str:
    """Copy the selected packs into root/docs/practices/ and return the
    `## Practices` section text to inject into the context file. An empty
    selection copies nothing and returns "" so the section collapses cleanly."""
    catalog = {n: (n, t, s) for n, t, s in available(assets)}
    chosen = [catalog[n] for n in selected if n in catalog]
    if not chosen:
        return ""
    dst = root / "docs" / "practices"
    dst.mkdir(parents=True, exist_ok=True)
    for name, _, _ in chosen:
        target = dst / f"{name}.md"
        if target.exists() and not force:
            continue
        shutil.copy(assets / "practices" / f"{name}.md", target)
    return _section(chosen, inline_for_claude)
