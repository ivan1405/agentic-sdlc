"""Render per-tool agent definitions from assets/agents/*.md.

Each role is written once, in assets/agents/. Per-vendor differences are
formatting — EXCEPT Codex, whose native agent file is TOML, not
Markdown-with-frontmatter, so it gets its own serializer. Which style a tool
uses is `Adapter.agent_style` in registry.py; this module renders each style.

Tool/model/permission fields are emitted ONLY where the schema was confirmed
against a real example (see docs/adapter-verification.md):
  - "claude": `tools:` (built-in names), `model: inherit`, `color:`.
  - "cursor": `model: inherit`, plus `readonly: true` on review-only roles.
  - "plain" (Copilot): name + description only — its `tools:` vocabulary is
    unverified, so nothing extra is guessed.
  - "toml" (Codex): native TOML, no per-tool allow-list exists.
"""
from __future__ import annotations

import re
from pathlib import Path

from asdlc.adapters.registry import ADAPTERS

ROLES = ["technical-leader", "solutions-architect", "frontend-dev", "backend-dev",
         "qa-engineer", "security-engineer"]

DESC_RE = re.compile(r"^%%DESC:\s*(.+?)%%\s*$", re.M)

# Claude Code — confirmed built-in tool names. Review-only roles get no
# Edit/Write/Bash; implementer roles get what they actually need to do the job.
CLAUDE_TOOLS = {
    "technical-leader": "Read, Grep, Glob",
    "solutions-architect": "Read, Grep, Glob, Edit, Write, Bash",
    "frontend-dev": "Read, Grep, Glob, Edit, Write, Bash",
    "backend-dev": "Read, Grep, Glob, Edit, Write, Bash",
    "qa-engineer": "Read, Grep, Glob, Edit, Bash",
    "security-engineer": "Read, Grep, Glob, Bash",
}
CLAUDE_COLOR = {
    "technical-leader": "blue",
    "solutions-architect": "magenta",
    "frontend-dev": "cyan",
    "backend-dev": "green",
    "qa-engineer": "yellow",
    "security-engineer": "red",
}
CURSOR_READONLY = {"technical-leader", "security-engineer"}


def parse(path: Path) -> tuple[str, str]:
    text = path.read_text()
    desc = DESC_RE.search(text).group(1)
    body = DESC_RE.sub("", text).lstrip("\n")
    return desc, body


def _frontmatter(style: str, role: str, desc: str) -> str:
    lines = ["---", f"name: {role}", f"description: {desc}"]
    if style == "claude":
        lines += [f"tools: {CLAUDE_TOOLS[role]}", "model: inherit", f"color: {CLAUDE_COLOR[role]}"]
    elif style == "cursor":
        lines.append("model: inherit")
        if role in CURSOR_READONLY:
            lines.append("readonly: true")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def _toml_basic_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _render_codex(name: str, desc: str, body: str) -> str:
    # TOML multi-line basic string: escape backslashes first, then the
    # triple-quote delimiter, so the body can't break out of
    # developer_instructions. description is a single-line basic string —
    # same backslash rule, plus any lone `"` needs escaping too.
    escaped_body = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    escaped_desc = _toml_basic_string(desc)
    return (f'name = "{name}"\ndescription = "{escaped_desc}"\n'
            f'developer_instructions = """\n{escaped_body}"""\n')


def render_tool_files(tool: str, shared_dir: Path) -> dict[str, str]:
    """Render {filename: content} for every role, for one tool.

    A tool with no native agent format (agent_style is None) renders nothing —
    its role guidance travels via AGENTS.md instead."""
    adapter = ADAPTERS[tool]
    if adapter.agent_style is None:
        return {}
    files: dict[str, str] = {}
    for role in ROLES:
        desc, body = parse(shared_dir / f"{role}.md")
        if adapter.agent_style == "toml":
            content = _render_codex(role, desc, body)
        else:
            content = _frontmatter(adapter.agent_style, role, desc) + body
        files[adapter.agent_filename.format(name=role)] = content
    return files


def render_generic(shared_dir: Path) -> str:
    """Render the single concatenated file for tools with no native agent support."""
    parts = [
        "# Agent roles (tool-agnostic)\n",
        "Your client's agent has no custom-subagent support? These are role\n"
        "definitions to paste into whatever persona/system-prompt mechanism it has.\n",
    ]
    for role in ROLES:
        desc, body = parse(shared_dir / f"{role}.md")
        parts.append(f"\n---\n\n## {role}\n\n{desc}\n\n{body}")
    return "\n".join(parts)
