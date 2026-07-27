"""Tool adapters — the only tool-specific code in the standard.

Public surface:
  ADAPTERS / TOOL_NAMES  the registry (single source of truth, see registry.py)
  Adapter                the per-tool record (base.py)
  render_adapter(...)     write one tool's files into a repo (render.py)
  commands / agents       the renderers (used directly by tests)

Import order matters: bind the submodules the renderers/registry need before
importing render (which imports commands + agents), so there's no half-init cycle.
"""
from asdlc.adapters.base import Adapter
from asdlc.adapters.registry import ADAPTERS, ADAPTER_LIST, TOOL_NAMES
from asdlc.adapters import agents, commands
from asdlc.adapters.render import render_adapter

__all__ = [
    "Adapter",
    "ADAPTERS",
    "ADAPTER_LIST",
    "TOOL_NAMES",
    "render_adapter",
    "commands",
    "agents",
]
