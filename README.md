# Agentic SDLC Standard

A tool-agnostic standard for AI-assisted software delivery. A developer writes a
spec; agents plan, implement, test, and open a PR; **gates decide whether it
merges**. Works whether the client bought Claude Code, Codex, Copilot, Cursor,
or nothing.

```bash
pipx install .                       # or: PYTHONPATH=src python -m asdlc ...
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
| **Artifact contract + gates + skills** | **years** | **this repo** |
| Git, PR, CI | decades | the industry |

The generation step was never the bottleneck. **Verification and review are.** A
pool of agents that produces PRs faster than humans can trust them just moves the
queue. So we do not orchestrate agents — we constrain them, and let the client
run whatever swarm they like against gates that do not care who wrote the code.

## What's in the box

```
src/asdlc/cli.py            asdlc: init | new | verify | doctor
src/asdlc/commands.py       renders the one workflow definition into each tool's command format
src/asdlc/gates/            the standard: 7 checks, zero dependencies, one policy file per client
src/asdlc/assets/           the payload asdlc init reads/renders into a client repo:
  templates/                  artifact contract — proposal, spec, design, tasks, ADR, AGENTS.md
  skills/                     5 portable SKILL.md packs (specs, tests, security, drift, regression)
  commands/                   the workflow, written once — propose/design/implement/verify/archive
  ci/                         GitHub Actions + GitLab CI pipelines
standard/                   the docs your boss reads
tests/                      proof that each gate blocks what it claims to, and that
                            the wheel actually contains what the CLI reads
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
python -m pytest tests/test_policy_parser.py   # zero-dep YAML fallback == PyYAML on shipped files
```

A gate you have never seen fail is not a gate. Same for a claim you have never
tested: the zero-dependency fallback parser is exercised by the packaging test
precisely because every dev box has PyYAML and would otherwise hide it.

## Portability

The only tool-specific code in this repo is `commands.py`, and the files it
renders are **generated at `asdlc init` time**, not committed:

```
assets/commands/*.md    ->  asdlc init  ->  .claude/commands/     (Claude Code)
                                            .codex/prompts/       (Codex CLI)
                                            .github/prompts/      (Copilot)
                                            .cursor/commands/     (Cursor)
                                            docs/agent-workflow.md (anything else)
```

The workflow is written once. Per-vendor differences are frontmatter keys and an
argument token, rendered by `commands.py`. A new agent CLI next quarter costs ~8
lines in `commands.py`'s `TOOLS` dict, not a
new methodology.

Context uses the standards, not our inventions: **AGENTS.md** (Linux Foundation's
Agentic AI Foundation, read by 20+ tools, 60k+ repos) and **SKILL.md** (open
standard, read by Claude Code, Codex, Cursor, VS Code and others). `CLAUDE.md`, if
the client wants one, is a one-line pointer to AGENTS.md.

## Which SDD front-end?

Don't standardize one globally. Pick per engagement from a menu the standard defines.
The artifact layout here is OpenSpec-compatible on purpose, so you can adopt its
CLI and slash commands for free — or drop it and keep the gates.

| Client situation | Front-end |
|---|---|
| Brownfield, mixed tooling (the common case) | **OpenSpec** — lightweight, tool-agnostic, no lock-in |
| GitHub/Copilot shop that wants ceremony | **Spec Kit** — `/speckit.*` are first-class Copilot commands |
| Greenfield, regulated, wants agent roles | **BMAD** — accept the token bill |
| AWS-committed, tolerant of IDE lock-in | **Kiro** |
| Nothing / hostile procurement | this repo alone — `asdlc` + AGENTS.md is enough |

`asdlc verify` is identical in every row. That is the product.

## Rollout

Don't big-bang it. See [standard/04-adoption-playbook.md](standard/04-adoption-playbook.md).
Short version: two pilots, six weeks, `spec-drift: warn` on legacy repos, ratchet
to `fail` after a quarter. Measure PR lead time, review rework rate, escaped
defects, and % of PRs with a current spec — or you have a slide deck, not a standard.

## Docs

- [01 — Artifact contract](standard/01-artifact-contract.md) — what each file is for, and the rules
- [02 — Gates](standard/02-gates.md) — every check, its failure mode, and how to tune it
- [03 — Definition of done](standard/03-definition-of-done.md) — the one-pager for the team
- [04 — Adoption playbook](standard/04-adoption-playbook.md) — pilots, metrics, and the anti-patterns
