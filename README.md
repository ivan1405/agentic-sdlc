# Agentic SDLC Standard

A tool-agnostic standard for AI-assisted software delivery. A developer writes a
spec; agents plan, implement, test, and open a PR; **gates decide whether it
merges**. Works whether the client bought Claude Code, Codex, Copilot, Cursor,
Gemini CLI, Windsurf, Aider, or nothing.

```bash
pipx install .                       # or: PYTHONPATH=src python3 -m asdlc ...
asdlc init --tools claude-code codex --ci github
asdlc new reject-empty-cart          # scaffold a change
asdlc verify                         # the gates — same command locally and in CI
```

## The thesis

Most "AI SDLC frameworks" standardize the wrong layer. They pick a vendor's
workflow, and when the next client has a different toolchain — or the tool churns,
which it does roughly quarterly — the work is thrown away.

So this standardizes one level up:

| Layer | Lifespan | Owned by |
|---|---|---|
| Model / agent CLI | months | the client |
| SDD front-end (OpenSpec, Spec Kit, BMAD) | ~a year | rented, swappable |
| **Artifact contract + gates + skills + practices** | **years** | **this repo** |
| Git, PR, CI | decades | the industry |

The generation step was never the bottleneck. **Verification and review are.** A
pool of agents that produces PRs faster than humans can trust them just moves the
queue. So we do not orchestrate agents — we constrain them, and let the client
run whatever swarm they like against gates that do not care who wrote the code.

## What's in the box

```
src/asdlc/cli.py            asdlc: init | new | verify | doctor | report | mcp
src/asdlc/tui.py            the interactive `asdlc init` wizard's terminal/menu machinery
src/asdlc/adapters/         the ONLY tool-specific code — one registry + renderers:
  base.py                     the Adapter record: all a tool's per-vendor differences, as data
  registry.py                 single source of truth: one Adapter entry per tool (add a tool here)
  commands.py                 renders the one workflow definition into each tool's command format
  agents.py                   renders the 6 role definitions into each tool's native agent format
  render.py                   writes a tool's files into a repo (driven by the Adapter's fields)
src/asdlc/sdd.py            shells out to OpenSpec/Spec Kit/BMAD's own installer, or writes Kiro's templates
src/asdlc/practices.py      installs the selected practice packs and links them from the context file
src/asdlc/report.py         asdlc report: adoption metrics from git + archived verify results (no API)
src/asdlc/gates/            the standard: 7 checks, zero dependencies, one policy file per client
src/asdlc/assets/           the payload asdlc init reads/renders into a client repo:
  templates/                  artifact contract — proposal, spec, design, tasks, ADR, AGENTS.md
  templates/kiro/             Kiro's steering docs — the one SDD methodology with no CLI to shell out to
  skills/                     5 portable SKILL.md packs, copied into each SKILL.md-reading tool's skills dir
  practices/                  15 vendor-neutral practice docs (8 core + 7 domain), installed into docs/practices/
  commands/                   the workflow, written once — onboard/jira-import/propose/design/implement/verify/archive
  agents/                     6 role definitions — technical-leader, solutions-architect, frontend-dev,
                               backend-dev, qa-engineer, security-engineer — written once, rendered per tool
                               (Codex's is TOML, not Markdown)
  ci/                         GitHub Actions + GitLab CI pipelines
standard/                   the docs your boss reads
tests/                      proof that each gate blocks what it claims to, and that
                            the wheel actually contains what the CLI reads (test_sdd.sh is opt-in,
                            needs npx/uv + network — not part of the mandatory suite)
```

Everything under `assets/` ships **inside** the package. If a file the CLI reads
at runtime is not listed in `pyproject.toml`'s `package-data`, it does not exist
once installed — `tests/test_packaging.sh` is what enforces that.

## The gates

`asdlc verify` — the only thing that is actually the standard. Everything else is
scaffolding to help agents pass it.

| Gate | Blocks | Why it exists |
|---|---|---|
| `spec-present` | production code with no change folder | Load-bearing. If code can land without a spec, nobody writes specs by sprint three. |
| `spec-lint` | requirements without SHALL + Given/When/Then | Stops "the system should be fast" from reaching an agent. |
| `traceability` | a requirement with no task or no test | Makes QA mechanical instead of vibes. |
| `spec-drift` | code moving while its spec doesn't | The month-six killer. Frameworks leave this manual; we make it a merge blocker. |
| `coverage-delta` | changed files below threshold | Changed-file scope, so it's enforceable on brownfield from day one. |
| `security-scan` | secrets + whatever scanner the client owns | We don't ship a scanner. We ship the contract that one runs. |
| `human-approval` | sensitive diffs without a named signature | Architecture, migrations, authz, money, public APIs. Sellable to a risk function. |

```bash
bash tests/test_gates.sh        # 9 realistic agent mistakes, each blocked by the right gate
bash tests/test_packaging.sh    # builds a wheel, installs it clean, drives the CLI from outside the tree
python3 -m pytest tests/        # unit suites: adapters, practices, report, wizard, policy parser
```

CI runs the mandatory suite (all of the above) on Linux **and** macOS — the shell
tests shell out to `git`/`sed`, and GNU vs BSD userlands diverge.

A gate you have never seen fail is not a gate. Same for a claim you have never
tested: the zero-dependency fallback parser is exercised by the packaging test
precisely because every dev box has PyYAML and would otherwise hide it.

## Portability

The only tool-specific code in this repo is the `src/asdlc/adapters/` package,
and the files it renders are **generated at `asdlc init` time**, not committed:

```
assets/commands/*.md     ->  asdlc init  ->  .claude/commands/     (Claude Code)
                                             .codex/prompts/       (Codex CLI)
                                             .github/prompts/      (Copilot)
                                             .cursor/commands/     (Cursor)
                                             .gemini/commands/     (Gemini CLI, .toml)
                                             .windsurf/workflows/  (Windsurf, .md)
                                             docs/agent-workflow.md (generic / Aider / anything else)

assets/skills/*/SKILL.md ->  asdlc init  ->  .claude/skills/       (Claude Code)
                                             .codex/skills/        (Codex CLI)
                                             .github/skills/       (Copilot)
                                             .cursor/skills/       (Cursor)

assets/agents/*.md       ->  asdlc init  ->  .claude/agents/       (Claude Code, .md)
                                             .codex/agents/        (Codex CLI, .toml — not Markdown)
                                             .github/agents/       (Copilot, .agent.md)
                                             .cursor/agents/       (Cursor, .md)
                                             (Gemini/Windsurf have no native agent file — roles ride in AGENTS.md)
```

Agents are the one place formatting differences become a real format
difference, not just frontmatter: Codex's native agent file is TOML
(`developer_instructions` carries the role's system prompt), so `agents.py`
gives it its own serializer instead of the Markdown-with-frontmatter template
the other three share. Tool/model restrictions are added only where the exact
schema was confirmed against real examples: Claude Code gets `tools:`
(built-in names), `model: inherit`, and `color:`; Cursor gets `model: inherit`
and `readonly: true` on the two review-only roles (no per-tool allow-list
exists there). Copilot's `tools:` uses a different, unverified vocabulary,
and Codex has no per-tool list at all — both are left without extra fields
rather than guess.

The workflow is written once. Per-vendor differences are data — dirs, filenames,
a frontmatter/TOML style, an argument token — held in one place, `adapters/
registry.py`. A new agent CLI next quarter costs **one `Adapter(...)` entry**
there (that's how Gemini CLI and Windsurf were added), not a new methodology.
`docs/adapter-verification.md` records which tool schemas were verified against a
real example, and when. Skills are copied,
not shared — pick two SKILL.md-reading tools and the 5 packs land twice, once per
tool's own dir, so each tool's native discovery works without an indirection to
chase. (Gemini CLI and Windsurf have no SKILL.md support, so they get none.)

Context uses the standards, not our inventions: **AGENTS.md** (Linux Foundation's
Agentic AI Foundation, read by 20+ tools, 60k+ repos) and **SKILL.md** (open
standard, read by Claude Code, Codex, Cursor, VS Code and others). Claude Code
never reads AGENTS.md directly — only `CLAUDE.md`. If some other selected
`--tools` choice reads AGENTS.md natively (Codex/Cursor/Copilot), that stays
the shared hub and `CLAUDE.md` becomes a one-line `@AGENTS.md` import — one
source of truth, no drift between two copies. If `claude-code` is the only
tool that needs this content, there's no AGENTS.md at all — the real content
goes straight into `CLAUDE.md` instead of a hub nothing else reads.

## Which SDD front-end?

Don't standardize one globally. Pick per engagement from a menu the standard defines.

| Client situation | Front-end | `asdlc init --sdd ...` |
|---|---|---|
| Brownfield, mixed tooling (the common case) | **OpenSpec** — lightweight, tool-agnostic, no lock-in | `openspec` |
| GitHub/Copilot shop that wants ceremony | **Spec Kit** — `/speckit.*` are first-class Copilot commands | `speckit` |
| Greenfield, regulated, wants agent roles | **BMAD** — accept the token bill | `bmad` |
| AWS-committed, tolerant of IDE lock-in | **Kiro** | `kiro` |
| Nothing / hostile procurement | this repo alone — `asdlc` + AGENTS.md is enough | `none` (default) |

`--sdd` shells out to each tool's own installer (`npx` for OpenSpec/BMAD, `uv`
for Spec Kit) instead of vendoring a copy — asdlc doesn't own these, it just
launches them, mapping `--tools` (claude-code/codex/copilot/cursor) to
whatever vocabulary that installer expects. `kiro` is the exception: no CLI
exists, so `asdlc` writes its `.kiro/steering/{product,tech,structure}.md`
templates directly. `npx`/`uv` are the client's dependency for that choice,
not `asdlc`'s — pick `none` (the default) and nothing changes.

**Verified, not assumed:** none of these front-ends' own commands produce
what asdlc's spec gates check for — not even OpenSpec's. Its own `openspec
new change` writes `specs/**/*.md` under the change folder, never a literal
`spec.md`; `spec-present`/`spec-lint` require that exact filename. So
`asdlc init --sdd <anything but none>` **disables `spec-present`,
`spec-lint`, `traceability`, and `spec-drift`** in the generated
`.asdlc/policy.yaml` — they can't verify a front-end's native shape, so they
don't pretend to. `coverage-delta`, `security-scan`, and `human-approval`
stay on always; they're the part of the contract that's genuinely
front-end-agnostic. Still want asdlc's own spec gates *and* a front-end
installed side by side? Use asdlc's own `/propose → /design → /implement`
(not the front-end's commands) to actually produce the gated artifacts, then
flip the four checks back to `enabled: true` by hand in `policy.yaml`.

Directory naming follows the same split, recorded in `.asdlc/policy.yaml`'s
`artifact_dirs`: `openspec/changes` + `openspec/specs` for `--sdd openspec`
or `none` (that pairing was never confusing — no other tool is present to
contradict it); `.asdlc/changes` + `.asdlc/specs` for `speckit`/`bmad`/`kiro`,
so this repo's own workflow never claims to be "openspec" when a different
front-end is actually installed. Each front-end's own artifacts (Spec Kit's
`specs/`, BMAD's `_bmad/`, Kiro's `.kiro/`) live wherever *that tool* puts
them — asdlc never reads those paths, gates disabled or not.

```bash
asdlc init --tools claude-code --sdd openspec --ci github
```

## MCP servers

`asdlc init` scaffolds an empty `.mcp.json` (`{"mcpServers": {}}`) — asdlc
doesn't opine on which MCP servers a client needs, only ships a curated
catalog of the common ones and a command to wire them up:

```bash
asdlc mcp list              # catalog + what's already configured here
asdlc mcp add atlassian slack github
asdlc mcp remove slack
```

| Catalog entry | Covers | Kind |
|---|---|---|
| `atlassian` | Jira, Confluence, Jira Service Management, Bitbucket, Compass (Cloud) | remote, OAuth |
| `atlassian-self-hosted` | Jira & Confluence, self-hosted Data Center | local (`uvx`), env vars |
| `github` | Repos, PRs, issues, code search | remote, OAuth |
| `slack` | Channels, threads, posting messages | remote, OAuth |

Most entries are vendor-hosted **remote** servers reached over OAuth —
`asdlc mcp add` writes a `{"type": "http", "url": "..."}` pointer into
`.mcp.json`, with no token or secret in that file, which is exactly why it's
safe to commit.

Data Center / self-hosted clients can't use OAuth against a vendor-hosted
endpoint, so `atlassian-self-hosted` is a **local** entry instead: it runs
[`mcp-atlassian`](https://github.com/sooperset/mcp-atlassian) via `uvx`
(needs [uv](https://astral.sh/uv) on the client's PATH — asdlc's own
dependency for that choice, not asdlc's), and every value that's either
secret or specific to that client's install — `JIRA_URL`,
`JIRA_PERSONAL_TOKEN`, `CONFLUENCE_URL`, `CONFLUENCE_PERSONAL_TOKEN` — is
written as an `"${VAR}"` reference, never a literal. `asdlc mcp add` prints
exactly which env vars to set; you (or the client) put the real values in
your shell or a local `.env`, never in `.mcp.json`. Any future local entry
(a database, an internal API) follows the same rule: `command`/`args` plus
`${VAR}` references, never a literal credential or hostname.

Catalog URLs are exactly the kind of vendor detail that drifts (see the SDD
front-ends' installer flags above) — `asdlc mcp list` prints each entry's
docs link; check it before rolling a change out to a client.

### Authenticating a catalog entry

Adding an entry to `.mcp.json` only registers the server — it doesn't
authenticate anyone. For a **local** entry like `atlassian-self-hosted`, "auth" just
means the env vars `asdlc mcp add` told you about are set wherever the agent
tool runs; no browser flow. For a **remote** (OAuth) entry, that handshake
happens **per person, inside your agent tool**, not through this file:

1. Start (or restart) your agent tool in this repo — it reads `.mcp.json` at
   startup.
2. In Claude Code, run `/mcp`. It lists each configured server and, for an
   unauthenticated one, gives you a link to open.
3. That opens the vendor's OAuth consent screen in your browser. **Slack
   specifically requires a workspace admin to approve the connection once**
   — if you're not an admin, whoever is will get an approval request.
4. Once approved, your agent tool stores the resulting token itself, locally,
   outside the repo. `/mcp` then shows the server as connected.

Two things worth knowing: the token never lands in `.mcp.json` (there's
nothing secret to leak by committing it), but **every teammate has to run
their own OAuth step once** — it doesn't propagate through git. And if the
consent link errors out instead of connecting, it's usually a pending
admin-approval step or an org policy blocking third-party app installs —
check with whoever administers that workspace/org before assuming asdlc's
config is wrong.

## Practices

The gates enforce *that* work is specified, traced, and reviewed. The **practice
packs** say *how* the code inside should be written — the vendor-neutral
engineering standards a consultancy actually bills for. They come in **tiers**,
because a Go service, a React app, and an ML pipeline don't need the same advice:

- **`core`** (universal, installed by default) — `immutability` · `small-units` ·
  `boundary-validation` · `test-first` · `evidence-based-completion` ·
  `secure-by-default` · `surgical-changes` · `clarify-before-coding`
- **`domain`** (opt-in by the nature of the project) — `observability` ·
  `api-design` · `data-privacy` · `cicd-release` · `infrastructure-as-code` ·
  `performance` · `accessibility`
- **`stack`** (React / Go / Python-ML overlays) — *planned; the tier axis is in place.*

`asdlc init` copies the selected packs into the client repo's `docs/practices/`
and folds a lean, grouped `## Practices` section into the context file
(AGENTS.md/CLAUDE.md) that links them — so every agent reads the standards
without bloating the hub. Claude-only repos also get `@docs/practices/*.md`
imports so Claude auto-loads them.

```bash
asdlc init --tools claude-code                                  # core only (default)
asdlc init --tools codex --practices core observability api-design   # core + two domains
asdlc init --tools cursor --practices all                       # everything
asdlc init --tools cursor --practices                           # none
```

`--practices` takes pack names and/or the group tokens `core` / `domain` / `all`.
Both the setup wizard and the rendered `## Practices` section organize the packs
into category boxes — **Foundations · Testing & QA · Security & Data · DevOps &
Platform · Product & Interface** — so a 15-item list stays scannable.

The selection persists in `.asdlc/policy.yaml` (`practices:`), so a re-run
remembers it, and `asdlc doctor` reports what's installed. Practices are
**guidance, not a gate** — the point is that agents read them, not that
`asdlc verify` blocks on them. A client tunes the set per engagement, or edits
the docs in place. Content is distilled tool-agnostic — no vendor, no
slash-commands, no assumptions about which agent runs it.

## Rollout

Don't big-bang it. See [standard/04-adoption-playbook.md](standard/04-adoption-playbook.md).
Short version: two pilots, six weeks, `spec-drift: warn` on legacy repos, ratchet
to `fail` after a quarter. Measure PR lead time, review rework rate, escaped
defects, and % of PRs with a current spec — or you have a slide deck, not a standard.

`asdlc report` computes the git-derivable half of those numbers — merge
throughput, PR lead time, and % of merged PRs that carried a spec — with no API
call or dependency, plus a gate pass-rate if you point `--results-dir` at
archived `asdlc verify --json` runs. Review rework rate and escaped defects need
the PR/issue API, so it names them as such rather than guessing.

```bash
asdlc report --since "90 days ago"                  # git metrics
asdlc report --results-dir ci-artifacts/ --json report.json
```

## Docs

- [01 — Artifact contract](standard/01-artifact-contract.md) — what each file is for, and the rules
- [02 — Gates](standard/02-gates.md) — every check, its failure mode, and how to tune it
- [03 — Definition of done](standard/03-definition-of-done.md) — the one-pager for the team
- [04 — Adoption playbook](standard/04-adoption-playbook.md) — pilots, metrics, and the anti-patterns
- [Adapter schema verification](docs/adapter-verification.md) — which tool formats were verified, and when

## License & contributing

Apache-2.0 — see [LICENSE](LICENSE). How to develop, run the suites, add a tool,
and the SemVer policy (clients pin a tag): [CONTRIBUTING.md](CONTRIBUTING.md).
Release history: [CHANGELOG.md](CHANGELOG.md).
