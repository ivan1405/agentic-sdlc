"""The `Adapter` record — one per agent tool.

Everything the standard needs to know about how a tool wants its files is a
field here, so `registry.py` can hold all per-tool differences in one table
and the renderers stay tool-blind. Adding a new tool is a new `Adapter(...)`
in the registry, not a new branch in three files.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class Adapter:
    name: str

    # Slash-command / prompt files. commands_dir is None for a tool with no
    # native command format (it falls back to single_file instead).
    #   command_style "frontmatter" -> command_frontmatter(desc, hint) header + body
    #   command_style "toml"        -> a native TOML doc (e.g. Gemini CLI)
    commands_dir: Optional[str] = None
    command_filename: str = "{name}.md"
    command_style: str = "frontmatter"
    command_frontmatter: Optional[Callable[[str, str], str]] = None  # (desc, hint) -> header
    # The token the tool substitutes for user input. None => no verified
    # argument mechanism; the renderer emits a neutral placeholder instead.
    arg_token: Optional[str] = "$ARGUMENTS"

    # Custom-subagent files. agents_dir is None for a tool with no native
    # agent format. agent_style selects how the frontmatter/body is rendered:
    #   "claude" -> tools + model + color   "cursor" -> model (+ readonly)
    #   "plain"  -> name + description only  "toml" -> native TOML (Codex)
    agents_dir: Optional[str] = None
    agent_filename: str = "{name}.md"
    agent_style: Optional[str] = None

    # SKILL.md packs. None for a tool that doesn't read the SKILL.md standard.
    skills_dir: Optional[str] = None

    # A single concatenated doc, for tools with no native command/agent files
    # (the paste-into-anything fallback). Mutually exclusive with the dirs above.
    single_file: Optional[str] = None
