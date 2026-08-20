"""Role discovery: adding a role is a {name}.md + a roles.yaml entry, nothing
else. These tests pin the auto-discovery and the fail-loud validation that
makes the two-file contract safe to get wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pytest  # noqa: E402

from asdlc.adapters.roles import Role, discover_roles  # noqa: E402

REAL_AGENTS_DIR = Path(__file__).resolve().parents[1] / "src/asdlc/assets/agents"


def _write_role(tmp_path: Path, name: str, yaml_entry: str = "") -> None:
    (tmp_path / f"{name}.md").write_text(f"%%DESC: {name}%%\nbody\n")
    with open(tmp_path / "roles.yaml", "a") as f:
        f.write(yaml_entry)


def test_discovers_every_shipped_role_in_yaml_order():
    roles = discover_roles(REAL_AGENTS_DIR)
    assert [r.name for r in roles] == [
        "technical-leader", "solutions-architect", "frontend-dev",
        "backend-dev", "qa-engineer", "security-engineer",
    ]
    assert roles[0].tools["claude-code"] == {"tools": "Read, Grep, Glob", "color": "blue"}
    assert roles[0].tools["cursor"] == {"readonly": True}
    assert "cursor" not in roles[1].tools  # solutions-architect: no cursor block


def test_new_role_picked_up_with_no_code_change(tmp_path):
    (tmp_path / "roles.yaml").write_text("")
    _write_role(tmp_path, "devops-engineer",
                "devops-engineer:\n"
                "  claude-code:\n"
                "    tools: \"Read, Grep, Glob, Edit, Write, Bash\"\n"
                "    color: orange\n")
    roles = discover_roles(tmp_path)
    assert roles == [Role(name="devops-engineer", tools={
        "claude-code": {"tools": "Read, Grep, Glob, Edit, Write, Bash", "color": "orange"},
    })]


def test_md_without_yaml_entry_fails_loud_naming_the_role(tmp_path):
    (tmp_path / "roles.yaml").write_text("")
    (tmp_path / "orphan-role.md").write_text("%%DESC: x%%\nbody\n")
    with pytest.raises(ValueError, match="orphan-role"):
        discover_roles(tmp_path)


def test_yaml_entry_without_md_fails_loud_naming_the_role(tmp_path):
    (tmp_path / "roles.yaml").write_text(
        "ghost-role:\n  claude-code:\n    tools: \"Read\"\n    color: blue\n"
    )
    with pytest.raises(ValueError, match="ghost-role"):
        discover_roles(tmp_path)


def test_missing_required_field_fails_loud(tmp_path):
    _write_role(tmp_path, "half-configured",
                "half-configured:\n  claude-code:\n    color: blue\n")
    with pytest.raises(ValueError, match="tools"):
        discover_roles(tmp_path)


def test_missing_claude_code_block_entirely_fails_loud(tmp_path):
    _write_role(tmp_path, "cursor-only", "cursor-only:\n  cursor:\n    readonly: true\n")
    with pytest.raises(ValueError, match="claude-code"):
        discover_roles(tmp_path)


def test_cursor_block_is_optional(tmp_path):
    _write_role(tmp_path, "plain-role",
                "plain-role:\n  claude-code:\n    tools: \"Read\"\n    color: blue\n")
    roles = discover_roles(tmp_path)
    assert "cursor" not in roles[0].tools
