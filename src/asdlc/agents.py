"""Render per-tool agent definitions from assets/agents/*.md.

Same idea as commands.py: each role is written once, in assets/agents/, and
per-vendor differences are just formatting — EXCEPT Codex, which is a real
format difference, not a formatting one: its native agent file is TOML, not
Markdown-with-frontmatter, so it gets its own serializer below instead of a
frontmatter-string template like the other three.

Tool/model/color restrictions are added ONLY where the exact schema has been
confirmed against real examples, not guessed:
  - Claude Code: `tools:` (comma list of built-in names: Read/Grep/Glob/Edit/
    Write/Bash), `model: inherit`, `color:` — confirmed against a real
    Claude Code agent file.
  - Cursor: `model: inherit` (same semantics, confirmed) and `readonly: true`
    for the two review-only roles — Cursor has no per-tool allow-list, but
    `readonly` is a confirmed field that maps cleanly onto "reviews, doesn't
    implement".
  - Copilot's `tools:` uses a DIFFERENT vocabulary (code_search/readfile/...,
    not Read/Grep/...) that hasn't been verified, and Codex has no per-tool
    list at all (only the broader `sandbox_mode`) — both are left without
    extra fields rather than guess.
"""
from __future__ import annotations

import re
from pathlib import Path

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


def _frontmatter(tool: str, role: str, desc: str) -> str:
    lines = ["---", f"name: {role}", f"description: {desc}"]
    if tool == "claude-code":
        lines += [f"tools: {CLAUDE_TOOLS[role]}", "model: inherit", f"color: {CLAUDE_COLOR[role]}"]
    elif tool == "cursor":
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


# name -> (dest dir, filename fmt, render function)
TOOLS = {
    "claude-code": (".claude/agents", "{name}.md"),
    "cursor": (".cursor/agents", "{name}.md"),
    "copilot": (".github/agents", "{name}.agent.md"),
    "codex": (".codex/agents", "{name}.toml"),
}


def render_tool_files(tool: str, shared_dir: Path) -> dict[str, str]:
    """Render {filename: content} for every role, for one tool."""
    _, fname_fmt = TOOLS[tool]
    files: dict[str, str] = {}
    for role in ROLES:
        desc, body = parse(shared_dir / f"{role}.md")
        if tool == "codex":
            content = _render_codex(role, desc, body)
        else:
            content = _frontmatter(tool, role, desc) + body
        files[fname_fmt.format(name=role)] = content
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
