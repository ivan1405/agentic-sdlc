"""Render per-tool adapter file content from assets/commands/*.md.

The workflow is written once, in `assets/commands/`. Everything here is a
formatting difference between vendors — frontmatter keys and an argument
placeholder. If a new agent CLI shows up next quarter, add ~8 lines to TOOLS
below, not a new methodology. Generation happens at `asdlc init` time (see
cli.py::render_adapter), not as a separate dev-time build step, so
`assets/commands/*.md` is the only file anyone ever hand-edits.
"""
from __future__ import annotations

import re
from pathlib import Path

ORDER = ["onboard", "propose", "design", "implement", "verify", "archive"]

# name -> (filename fmt, frontmatter builder, argument token)
TOOLS = {
    # Claude Code: .claude/commands/<name>.md, $ARGUMENTS, YAML frontmatter.
    "claude-code": (
        "{name}.md",
        lambda d, h: f"---\ndescription: {d}\nargument-hint: {h}\n---\n\n",
        "$ARGUMENTS",
    ),
    # Codex CLI: .codex/prompts/<name>.md, $ARGUMENTS, no frontmatter schema.
    "codex": (
        "{name}.md",
        lambda d, h: f"<!-- {d} | usage: /{{name}} {h} -->\n\n",
        "$ARGUMENTS",
    ),
    # Copilot: .github/prompts/<name>.prompt.md, ${input:...}, mode frontmatter.
    "copilot": (
        "{name}.prompt.md",
        lambda d, h: f"---\nmode: agent\ndescription: {d}\n---\n\n",
        "${input:args}",
    ),
    # Cursor: .cursor/commands/<name>.md, plain markdown.
    "cursor": (
        "{name}.md",
        lambda d, h: f"---\ndescription: {d}\n---\n\n",
        "$ARGUMENTS",
    ),
}

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


def render_tool_files(tool: str, shared_dir: Path, changes_dir: str, specs_dir: str,
                       context_file: str) -> dict[str, str]:
    """Render {filename: content} for every workflow step, for one tool."""
    fname_fmt, fm, argtok = TOOLS[tool]
    files: dict[str, str] = {}
    for name in ORDER:
        desc, hint, body = parse(shared_dir / f"{name}.md")
        content = fm(desc, hint).replace("{name}", name) + body.replace("%%ARG%%", argtok)
        files[fname_fmt.format(name=name)] = _fill_dirs(content, changes_dir, specs_dir, context_file)
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
