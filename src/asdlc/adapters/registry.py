"""The adapter registry — the single source of truth for per-tool differences.

This replaces the three hand-synced tables that used to live in cli.py
(`ADAPTER_TARGETS`), commands.py (`TOOLS`), and agents.py (`TOOLS`). A new agent
CLI is now one `Adapter(...)` entry here; the renderers and `render_adapter`
read these fields and know nothing tool-specific.

Rule (see agents.py / docs/adapter-verification.md): only set a tool/model/
permission-shaped field where the exact schema was verified against a real
example. Guess nothing — an omitted field is safe; a wrong one ships a broken
adapter to a client.
"""
from __future__ import annotations

from asdlc.adapters.base import Adapter

ADAPTER_LIST = [
    # Claude Code: YAML frontmatter, $ARGUMENTS. Agent frontmatter (tools/
    # model/color) verified against a real Claude Code agent file.
    Adapter(
        name="claude-code",
        commands_dir=".claude/commands",
        command_filename="{name}.md",
        command_frontmatter=lambda d, h: f"---\ndescription: {d}\nargument-hint: {h}\n---\n\n",
        arg_token="$ARGUMENTS",
        agents_dir=".claude/agents",
        agent_filename="{name}.md",
        agent_style="claude",
        skills_dir=".claude/skills",
    ),
    # Codex CLI: no command frontmatter schema (HTML-comment header); agent
    # file is native TOML, not Markdown — hence its own serializer.
    Adapter(
        name="codex",
        commands_dir=".codex/prompts",
        command_filename="{name}.md",
        command_frontmatter=lambda d, h: f"<!-- {d} | usage: /{{name}} {h} -->\n\n",
        arg_token="$ARGUMENTS",
        agents_dir=".codex/agents",
        agent_filename="{name}.toml",
        agent_style="toml",
        skills_dir=".codex/skills",
    ),
    # Copilot: mode+description frontmatter, ${input:...}. Its `tools:`
    # vocabulary is unverified, so no extra agent fields are emitted.
    Adapter(
        name="copilot",
        commands_dir=".github/prompts",
        command_filename="{name}.prompt.md",
        command_frontmatter=lambda d, h: f"---\nmode: agent\ndescription: {d}\n---\n\n",
        arg_token="${input:args}",
        agents_dir=".github/agents",
        agent_filename="{name}.agent.md",
        agent_style="plain",
        skills_dir=".github/skills",
    ),
    # Cursor: description frontmatter; agents get model: inherit and readonly
    # on the two review-only roles (verified fields; no per-tool allow-list).
    Adapter(
        name="cursor",
        commands_dir=".cursor/commands",
        command_filename="{name}.md",
        command_frontmatter=lambda d, h: f"---\ndescription: {d}\n---\n\n",
        arg_token="$ARGUMENTS",
        agents_dir=".cursor/agents",
        agent_filename="{name}.md",
        agent_style="cursor",
        skills_dir=".cursor/skills",
    ),
    # Gemini CLI: custom commands are native TOML in .gemini/commands/ with a
    # `prompt` (+ `description`) key and {{args}} for input. No native agent/
    # subagent file format, and SKILL.md support is unconfirmed — so neither is
    # emitted. Context travels via GEMINI.md (out of the adapter's scope).
    # Verified: https://geminicli.com/docs/cli/custom-commands/ (2026-07-27).
    Adapter(
        name="gemini",
        commands_dir=".gemini/commands",
        command_filename="{name}.toml",
        command_style="toml",
        arg_token="{{args}}",
    ),
    # Windsurf: "workflows" are Markdown-with-frontmatter in .windsurf/workflows/,
    # invoked as /name in Cascade. No native agent file; no verified argument
    # token (arg_token=None => neutral placeholder); SKILL.md support unconfirmed.
    # Verified: https://docs.windsurf.com/windsurf/cascade/workflows (2026-07-27).
    Adapter(
        name="windsurf",
        commands_dir=".windsurf/workflows",
        command_filename="{name}.md",
        command_frontmatter=lambda d, h: f"---\ndescription: {d}\n---\n\n",
        arg_token=None,
    ),
    # Generic: no native command/agent files — one concatenated doc to paste
    # into whatever mechanism a long-tail tool has. AGENTS.md carries the rest.
    # Aider maps here too: it has no command/agent format, only AGENTS.md.
    Adapter(
        name="generic",
        single_file="docs/agent-workflow.md",
    ),
]

ADAPTERS: dict[str, Adapter] = {a.name: a for a in ADAPTER_LIST}
TOOL_NAMES: list[str] = [a.name for a in ADAPTER_LIST]
