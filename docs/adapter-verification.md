# Adapter schema verification

The renderers in `commands.py` and `agents.py` are the only tool-specific code
in this repo. Each target tool has its own file location, filename, and — where
it has one — frontmatter schema. This is the record of **what has actually been
verified against a real example, and when**, versus what is deliberately left
minimal because the schema was unconfirmed.

The rule (see the header comment in `agents.py`): add a tool/model/permission
field **only** where the exact schema was confirmed against a real file. Guess
nothing — an omitted field is safe; a wrong one ships a broken adapter to a
client. `tests/test_adapters.py` enforces validity (TOML parses, frontmatter is
YAML) and pins the exact rendered bytes with golden snapshots.

_Last verified: 2026-07-27._

## Matrix

| Tool | Command file | Agent file | Frontmatter / format | Extra fields emitted | Verified against a real example? |
|---|---|---|---|---|---|
| **claude-code** | `.claude/commands/{name}.md` | `.claude/agents/{name}.md` | YAML frontmatter | agents: `tools`, `model: inherit`, `color` | ✅ agent frontmatter confirmed against a real Claude Code agent file |
| **codex** | `.codex/prompts/{name}.md` | `.codex/agents/{name}.toml` | commands: HTML-comment header; agents: **TOML** (`name`, `description`, `developer_instructions`) | none (no per-tool allow-list exists; only the broader `sandbox_mode`) | ✅ agent file is native TOML, not Markdown — dedicated serializer |
| **copilot** | `.github/prompts/{name}.prompt.md` | `.github/agents/{name}.agent.md` | YAML frontmatter (commands add `mode: agent`) | none | ⚠️ `tools:` uses a different vocabulary (`code_search`/`readfile`/…) that is **unverified** — left out on purpose |
| **cursor** | `.cursor/commands/{name}.md` | `.cursor/agents/{name}.md` | YAML frontmatter | agents: `model: inherit`, plus `readonly: true` on the two review-only roles | ✅ `model`/`readonly` confirmed; no per-tool allow-list exists in Cursor |
| **generic** | `docs/agent-workflow.md` (single concatenated doc) | — (same file) | plain Markdown, no schema | n/a | n/a — paste-into-anything fallback for the long tail |

Argument tokens per tool: `$ARGUMENTS` (claude-code, codex, cursor),
`${input:args}` (copilot).

## When to re-verify

Agent-tool vendors change these formats without notice (the SDD front-end
installer flags already drifted across doc versions — see `sdd.py`). Re-check
and bump the date above when:

- Adding a new tool adapter (never add a field you haven't seen in a real file).
- A client reports a rendered command/agent file their tool won't load.
- You bump the pinned version a client installs.

Regenerate the golden snapshots deliberately after any intended change:

```bash
ASDLC_UPDATE_GOLDEN=1 PYTHONPATH=src python3 -m pytest tests/test_adapters.py
```

Review the diff before committing — an unexpected change there is the whole
point of the snapshot.
