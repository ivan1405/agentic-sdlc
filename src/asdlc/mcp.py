"""Curated catalog of MCP servers + .mcp.json merge helpers.

Same spirit as sdd.py's SDD_TOOLS: an entry here is a pointer to a vendor's
own server and docs, not a copy of it — asdlc doesn't run or manage these
servers itself. Most entries are remote, OAuth-authenticated endpoints, so
their `config` never carries a credential. A `"kind": "local"` entry (e.g.
atlassian-self-hosted, or a future database entry) instead references
environment variables (`"${VAR}"`, expanded by the agent tool at launch —
Claude Code supports this in command/args/env/url) for anything secret or
client-specific, since .mcp.json is meant to be committed and must never
carry a literal secret or a client's own hostname.

Catalog URLs are exactly the kind of vendor detail that drifts (see sdd.py's
own note about installer flags disagreeing across doc versions) — re-verify
against the vendor's docs (linked per entry) before trusting an old checkout.
"""
from __future__ import annotations

import json
from pathlib import Path

CATALOG_FILE = "mcp_catalog.json"


def load_catalog(assets: Path) -> dict:
    return json.loads((assets / CATALOG_FILE).read_text())


def read_mcp_json(root: Path) -> dict:
    path = root / ".mcp.json"
    if not path.exists():
        return {"mcpServers": {}}
    return json.loads(path.read_text())


def write_mcp_json(root: Path, data: dict) -> None:
    (root / ".mcp.json").write_text(json.dumps(data, indent=2) + "\n")


def add(root: Path, assets: Path, name: str) -> dict:
    """Merge catalog entry `name` into .mcp.json's mcpServers. Returns the
    catalog entry. `name` is assumed already validated against the catalog
    (the CLI's argparse `choices` is the boundary check for this)."""
    entry = load_catalog(assets)[name]
    data = read_mcp_json(root)
    data.setdefault("mcpServers", {})[name] = entry["config"]
    write_mcp_json(root, data)
    return entry


def remove(root: Path, name: str) -> bool:
    """Removes `name` from .mcp.json's mcpServers, if present. Unlike add(),
    not restricted to the catalog — someone may have hand-added a server.
    Returns whether anything was actually removed."""
    data = read_mcp_json(root)
    removed = data.get("mcpServers", {}).pop(name, None) is not None
    if removed:
        write_mcp_json(root, data)
    return removed
