"""Adapter safety net.

The renderers in commands.py/agents.py are the one place a vendor's file format
leaks into this otherwise tool-blind repo. Two failure modes this guards:

  1. Invalidity — a rendered file the target tool can't parse. Codex agent files
     are TOML (a hand-written serializer with escaping); the other three carry a
     YAML frontmatter block. Both are checked structurally here so a bad escape
     or a stray key fails a test instead of a client's agent tool.

  2. Silent drift — a refactor (e.g. the planned adapters/ consolidation) that
     changes rendered output without anyone noticing. Golden snapshots pin the
     exact bytes per tool; regenerate deliberately with ASDLC_UPDATE_GOLDEN=1
     and review the diff.

    PYTHONPATH=src python3 -m pytest tests/test_adapters.py
    ASDLC_UPDATE_GOLDEN=1 PYTHONPATH=src python3 -m pytest tests/test_adapters.py  # regen goldens
"""
from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import asdlc  # noqa: E402
from asdlc.adapters import ADAPTERS, agents, commands  # noqa: E402

try:
    import yaml  # type: ignore
except ImportError:  # the repo deliberately doesn't depend on PyYAML
    yaml = None

ASSETS = Path(asdlc.__file__).resolve().parent / "assets"
COMMANDS_DIR = ASSETS / "commands"
AGENTS_DIR = ASSETS / "agents"
GOLDEN = Path(__file__).resolve().parent / "golden"

# Derived from the registry so this test tracks new tools automatically.
# generic is excluded (no per-file schema; snapshotted separately).
COMMAND_TOOLS = [n for n, a in ADAPTERS.items() if a.commands_dir]   # claude,codex,copilot,cursor,gemini,windsurf
AGENT_TOOLS = [n for n, a in ADAPTERS.items() if a.agents_dir]       # claude,codex,copilot,cursor
# Command files that carry a YAML frontmatter block — not Codex's HTML-comment
# header nor Gemini's native TOML, both validated separately below.
YAML_COMMAND_TOOLS = ["claude-code", "copilot", "cursor", "windsurf"]
# Agent files that carry a YAML frontmatter block (Codex agents are TOML).
YAML_AGENT_TOOLS = ["claude-code", "copilot", "cursor"]

# Canonical substitution values so snapshots are deterministic. These are just
# what a fresh `asdlc init` (no SDD front-end) would use.
CHANGES_DIR, SPECS_DIR, CONTEXT_FILE = "openspec/changes", "openspec/specs", "AGENTS.md"

EXPECTED_COMMANDS = {"onboard", "jira-import", "propose", "design", "implement", "verify", "archive"}
EXPECTED_ROLES = {"technical-leader", "solutions-architect", "frontend-dev",
                  "backend-dev", "qa-engineer", "security-engineer"}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _render_commands(tool: str) -> dict[str, str]:
    return commands.render_tool_files(tool, COMMANDS_DIR, CHANGES_DIR, SPECS_DIR, CONTEXT_FILE)


def _render_agents(tool: str) -> dict[str, str]:
    return agents.render_tool_files(tool, AGENTS_DIR)


def _frontmatter_block(content: str) -> dict:
    """Extract and parse the leading `---`…`---` YAML block. Uses PyYAML when
    present; otherwise a structural key:value check that still catches a
    missing delimiter or a non-map body."""
    lines = content.splitlines()
    assert lines and lines[0] == "---", f"no opening frontmatter delimiter: {lines[:1]!r}"
    assert "---" in lines[1:], "no closing frontmatter delimiter"
    block_lines = lines[1:lines.index("---", 1)]
    block = "\n".join(block_lines)
    if yaml is not None:
        data = yaml.safe_load(block)
        assert isinstance(data, dict), f"frontmatter is not a YAML map: {data!r}"
        return data
    # Fallback: every non-blank line must look like `key: value`.
    data = {}
    for ln in block_lines:
        if not ln.strip():
            continue
        assert ": " in ln, f"frontmatter line is not key: value: {ln!r}"
        k, _, v = ln.partition(": ")
        data[k.strip()] = v.strip()
    return data


def _manifest(files: dict[str, str]) -> str:
    """Deterministic, human-diffable concatenation of a rendered file set."""
    parts = []
    for name in sorted(files):
        parts.append(f"===== {name} =====\n{files[name]}")
    return "\n".join(parts) + "\n"


def _check_golden(rel: str, actual: str) -> None:
    path = GOLDEN / rel
    if os.environ.get("ASDLC_UPDATE_GOLDEN"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual)
        pytest.skip(f"regenerated golden {rel}")
    assert path.exists(), (
        f"missing golden {rel} — regenerate with "
        f"ASDLC_UPDATE_GOLDEN=1 PYTHONPATH=src python3 -m pytest tests/test_adapters.py"
    )
    assert actual == path.read_text(), (
        f"rendered output drifted from golden {rel}. If intentional, regenerate "
        f"with ASDLC_UPDATE_GOLDEN=1 and review the diff."
    )


# --------------------------------------------------------------------------- #
# completeness — every workflow step / role renders, for every tool
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tool", COMMAND_TOOLS)
def test_every_command_renders(tool):
    cmds = _render_commands(tool)
    assert {n.split(".")[0] for n in cmds} == EXPECTED_COMMANDS
    assert all(v.strip() for v in cmds.values()), "a command rendered empty"


@pytest.mark.parametrize("tool", AGENT_TOOLS)
def test_every_role_renders(tool):
    ags = _render_agents(tool)
    assert {n.split(".")[0] for n in ags} == EXPECTED_ROLES
    assert all(v.strip() for v in ags.values()), "an agent rendered empty"


def test_command_only_tools_render_no_agents():
    """gemini/windsurf have commands but no native agent format — they must
    render nothing rather than a bogus agent file."""
    for name, a in ADAPTERS.items():
        if a.commands_dir and not a.agents_dir:
            assert _render_agents(name) == {}, f"{name} unexpectedly rendered agents"


# --------------------------------------------------------------------------- #
# validity — the rendered files parse in their target format
# --------------------------------------------------------------------------- #
def test_codex_agents_are_valid_toml():
    for name, content in _render_agents("codex").items():
        assert name.endswith(".toml")
        data = tomllib.loads(content)  # raises on malformed TOML / bad escape
        assert data.get("name"), f"{name}: missing name"
        assert data.get("description"), f"{name}: missing description"
        assert data.get("developer_instructions", "").strip(), f"{name}: empty instructions"


def test_codex_commands_have_header_and_body():
    for name, content in _render_commands("codex").items():
        assert content.startswith("<!--"), f"{name}: missing Codex comment header"
        body = content.split("-->", 1)[1].strip()
        assert body, f"{name}: no body after header"
        assert "$ARGUMENTS" in content, f"{name}: argument token not substituted"


def test_gemini_commands_are_valid_toml():
    for name, content in _render_commands("gemini").items():
        assert name.endswith(".toml")
        data = tomllib.loads(content)  # raises on malformed TOML / bad escape
        assert data.get("prompt", "").strip(), f"{name}: missing prompt"
        assert "%%ARG%%" not in content, f"{name}: raw arg placeholder left unrendered"
        assert "{{args}}" in data["prompt"], f"{name}: Gemini args token not substituted"


@pytest.mark.parametrize("tool", YAML_COMMAND_TOOLS)
def test_command_frontmatter_is_valid(tool):
    for name, content in _render_commands(tool).items():
        fm = _frontmatter_block(content)
        assert fm.get("description"), f"{tool}/{name}: frontmatter missing description"
        body = content.split("---", 2)[2].strip()
        assert body, f"{tool}/{name}: no body after frontmatter"


@pytest.mark.parametrize("tool", YAML_AGENT_TOOLS)
def test_agent_frontmatter_is_valid(tool):
    for name, content in _render_agents(tool).items():
        fm = _frontmatter_block(content)
        assert fm.get("name"), f"{tool}/{name}: frontmatter missing name"
        assert fm.get("description"), f"{tool}/{name}: frontmatter missing description"


def test_claude_agents_declare_verified_fields():
    """Claude Code's schema (tools/model/color) was verified against a real
    agent file — pin that it's actually emitted so a renderer change can't
    quietly drop it."""
    for name, content in _render_agents("claude-code").items():
        fm = _frontmatter_block(content)
        assert fm.get("model") == "inherit", f"{name}: expected model: inherit"
        assert fm.get("tools"), f"{name}: expected a tools allow-list"
        assert fm.get("color"), f"{name}: expected a color"


# --------------------------------------------------------------------------- #
# golden snapshots — exact rendered bytes, per tool (drift guard for refactors)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tool", COMMAND_TOOLS)
def test_commands_snapshot(tool):
    _check_golden(f"{tool}.commands.txt", _manifest(_render_commands(tool)))


@pytest.mark.parametrize("tool", AGENT_TOOLS)
def test_agents_snapshot(tool):
    _check_golden(f"{tool}.agents.txt", _manifest(_render_agents(tool)))


# One golden per test: _check_golden skips in regen mode, so two calls in one
# test would abort before writing the second.
def test_generic_commands_snapshot():
    _check_golden("generic.commands.txt",
                  commands.render_generic(COMMANDS_DIR, CHANGES_DIR, SPECS_DIR, CONTEXT_FILE))


def test_generic_agents_snapshot():
    _check_golden("generic.agents.txt", agents.render_generic(AGENTS_DIR))
