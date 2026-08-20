"""Render per-tool command/prompt files from assets/commands/*.md.

The workflow is written once, in `assets/commands/`. Everything here is a
formatting difference between vendors — a frontmatter header and an argument
token — and those differences live as fields on the tool's `Adapter` in
registry.py. This module is tool-blind: it reads the adapter and applies it.
"""
from __future__ import annotations

import re
from pathlib import Path

from asdlc.adapters.registry import ADAPTERS

ORDER = ["onboard", "jira-import", "azure-devops-import", "propose", "design",
         "implement", "verify", "archive"]

DESC_RE = re.compile(r"^%%DESC:\s*(.+?)%%\s*$", re.M)
HINT_RE = re.compile(r"^%%HINT:\s*(.+?)%%\s*$", re.M)


def parse(path: Path) -> tuple[str, str, str]:
    text = path.read_text()
    desc = DESC_RE.search(text).group(1)
    hint = HINT_RE.search(text).group(1)
    body = HINT_RE.sub("", DESC_RE.sub("", text)).lstrip("\n")
    return desc, hint, body


def _fill_dirs(text: str, changes_dir: str, specs_dir: str, context_file: str) -> str:
    return (text.replace("%%CHANGES_DIR%%", changes_dir)
                .replace("%%SPECS_DIR%%", specs_dir)
                .replace("%%CONTEXT_FILE%%", context_file))


def _render_toml_command(desc: str, body: str) -> str:
    """A native TOML command doc (Gemini CLI): `description` + a `prompt`
    multi-line basic string. Escape backslashes first, then the triple-quote
    delimiter, so the body can't break out of `prompt` — same rule the Codex
    agent serializer uses."""
    esc_desc = desc.replace("\\", "\\\\").replace('"', '\\"')
    esc_body = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'description = "{esc_desc}"\nprompt = """\n{esc_body}"""\n'


def render_tool_files(tool: str, shared_dir: Path, changes_dir: str, specs_dir: str,
                       context_file: str) -> dict[str, str]:
    """Render {filename: content} for every workflow step, for one tool."""
    adapter = ADAPTERS[tool]
    files: dict[str, str] = {}
    # No verified argument token => a neutral placeholder rather than a guess.
    token = adapter.arg_token or "<your input here>"
    for name in ORDER:
        desc, hint, body = parse(shared_dir / f"{name}.md")
        body = body.replace("%%ARG%%", token)
        if adapter.command_style == "toml":
            content = _render_toml_command(desc, body)
        else:
            content = adapter.command_frontmatter(desc, hint).replace("{name}", name) + body
        files[adapter.command_filename.format(name=name)] = _fill_dirs(
            content, changes_dir, specs_dir, context_file
        )
    return files


def render_generic(shared_dir: Path, changes_dir: str, specs_dir: str, context_file: str) -> str:
    """Render the single concatenated file for tools with no slash commands."""
    parts = [
        "# Agent workflow (tool-agnostic)\n",
        "Your client's agent has no slash commands? Paste the relevant section.\n",
        "The workflow is the standard; the slash commands are sugar.\n",
    ]
    for name in ORDER:
        desc, hint, body = parse(shared_dir / f"{name}.md")
        parts.append(
            f"\n---\n\n## {name} — {desc}\n\nUsage: `{name} {hint}`\n\n"
            + body.replace("%%ARG%%", "<your input here>")
        )
    return _fill_dirs("\n".join(parts), changes_dir, specs_dir, context_file)
