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
src/asdlc/sdd.py            shells out to OpenSpec/Spec Kit/BMAD's own installer, or writes Kiro's templates
src/asdlc/gates/            the standard: 7 checks, zero dependencies, one policy file per client
src/asdlc/assets/           the payload asdlc init reads/renders into a client repo:
  templates/                  artifact contract — proposal, spec, design, tasks, ADR, AGENTS.md
  templates/kiro/             Kiro's steering docs — the one SDD methodology with no CLI to shell out to
  skills/                     5 portable SKILL.md packs, copied into every selected tool's own skills dir
  commands/                   the workflow, written once — onboard/propose/design/implement/verify/archive
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
python -m pytest tests/test_policy_parser.py   # zero-dep YAML fallback == PyYAML on shipped files
```

A gate you have never seen fail is not a gate. Same for a claim you have never
tested: the zero-dependency fallback parser is exercised by the packaging test
precisely because every dev box has PyYAML and would otherwise hide it.

## Portability

The only tool-specific code in this repo is `commands.py`, and the files it
renders are **generated at `asdlc init` time**, not committed:

```
assets/commands/*.md     ->  asdlc init  ->  .claude/commands/     (Claude Code)
                                             .codex/prompts/       (Codex CLI)
                                             .github/prompts/      (Copilot)
                                             .cursor/commands/     (Cursor)
                                             docs/agent-workflow.md (anything else)

assets/skills/*/SKILL.md ->  asdlc init  ->  .claude/skills/       (Claude Code)
                                             .codex/skills/        (Codex CLI)
                                             .github/skills/       (Copilot)
                                             .cursor/skills/       (Cursor)
```

The workflow is written once. Per-vendor differences are frontmatter keys and an
argument token, rendered by `commands.py`. A new agent CLI next quarter costs ~8
lines in `commands.py`'s `TOOLS` dict, not a new methodology. Skills are copied,
not shared — pick two tools and the 5 packs land twice, once per tool's own dir,
so each tool's native discovery works without an indirection to chase.

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
