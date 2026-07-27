"""Write a tool's adapter files into a repo — the file I/O around the renderers.

Lifted out of cli.py: cli now calls `adapters.render_adapter(...)` and stays out
of the tool-specific business entirely. What gets written is driven by which
fields the tool's `Adapter` sets (commands_dir / agents_dir / skills_dir /
single_file), so there is no per-tool branching here.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from asdlc.adapters import agents, commands
from asdlc.adapters.registry import ADAPTERS


def render_adapter(root: Path, tool: str, assets: Path, changes_dir: str, specs_dir: str,
                    context_file: str, force: bool = False) -> int:
    if tool not in ADAPTERS:
        raise SystemExit(f"unknown tool '{tool}'. known: {', '.join(sorted(ADAPTERS))}")
    adapter = ADAPTERS[tool]
    shared_cmds = assets / "commands"
    shared_agents = assets / "agents"
    count = 0

    # Tools with no native command/agent files get one concatenated doc instead.
    if adapter.single_file:
        dst = root / adapter.single_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        doc = (commands.render_generic(shared_cmds, changes_dir, specs_dir, context_file)
               + "\n\n" + agents.render_generic(shared_agents))
        dst.write_text(doc)
        return 1

    if adapter.commands_dir:
        dst = root / adapter.commands_dir
        dst.mkdir(parents=True, exist_ok=True)
        for name, content in sorted(
            commands.render_tool_files(tool, shared_cmds, changes_dir, specs_dir, context_file).items()
        ):
            target = dst / name
            if target.exists() and not force:
                continue
            target.write_text(content)
            count += 1

    if adapter.skills_dir:
        dst = root / adapter.skills_dir
        dst.mkdir(parents=True, exist_ok=True)
        for skill in (assets / "skills").glob("*/"):
            target = dst / skill.name
            if target.exists():
                if not force:
                    continue
                shutil.rmtree(target)
            shutil.copytree(skill, target)
            count += 1

    if adapter.agents_dir:
        dst = root / adapter.agents_dir
        dst.mkdir(parents=True, exist_ok=True)
        for name, content in sorted(agents.render_tool_files(tool, shared_agents).items()):
            target = dst / name
            if target.exists() and not force:
                continue
            target.write_text(content)
            count += 1

    return count
