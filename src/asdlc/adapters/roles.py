"""Role discovery — the single place a role's existence and permissions come
from, so adding one never touches Python.

A role is defined by two files living side by side in assets/agents/:
  {name}.md     the role's prompt (parsed by agents.py)
  roles.yaml    every role's per-tool permissions, keyed by name then by
                ADAPTERS tool name, in render order — see the comments in
                that file for the field contract

`discover_roles` reads both and cross-checks them: a role missing from either
side fails loudly (naming exactly what's missing) rather than silently
guessing permissions or dropping a role.

Only tools with a *verified* permission schema get a block here today
(claude-code, cursor — see docs/adapter-verification.md). That verification
status, not this module, is what limits which tools show up: the per-role
dict is intentionally open-ended so a newly-verified tool (codex's
sandbox_mode, copilot's tools: vocabulary, ...) is a new block in roles.yaml
plus one new branch in agents.py's `_frontmatter`, not a schema migration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from asdlc import yamlish

# Required keys within a role's per-tool block, for tools whose schema is
# confirmed. Only claude-code has hard requirements today — cursor's only
# field (readonly) is optional and defaults to false.
REQUIRED_TOOL_FIELDS = {
    "claude-code": ("tools", "color"),
}


@dataclass(frozen=True)
class Role:
    name: str
    # {tool_name: {field: value}} — e.g. tools["claude-code"]["tools"],
    # tools["cursor"].get("readonly"). A tool absent from this dict has no
    # verified permission schema yet; its renderer must not require one.
    tools: dict[str, dict] = field(default_factory=dict)


def discover_roles(shared_dir: Path) -> list[Role]:
    yaml_path = shared_dir / "roles.yaml"
    config = yamlish.load(yaml_path.read_text())

    md_names = {p.stem for p in shared_dir.glob("*.md")}
    yaml_names = set(config)

    missing_yaml = sorted(md_names - yaml_names)
    if missing_yaml:
        raise ValueError(
            f"{yaml_path} has no entry for {missing_yaml} — every "
            f"assets/agents/{{name}}.md needs a matching entry there"
        )
    missing_md = sorted(yaml_names - md_names)
    if missing_md:
        raise ValueError(
            f"{yaml_path} lists {missing_md} but {shared_dir} has no matching "
            f".md file for them"
        )

    roles = []
    for name, tool_cfgs in config.items():
        for tool, required in REQUIRED_TOOL_FIELDS.items():
            block = tool_cfgs.get(tool, {})
            missing_fields = [f for f in required if f not in block]
            if missing_fields:
                raise ValueError(
                    f"{yaml_path}: role {name!r}'s {tool!r} block is missing {missing_fields}"
                )
        roles.append(Role(name=name, tools=tool_cfgs))
    return roles
