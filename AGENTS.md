# AGENTS.md — agentic-sdlc-2

<!--
This is the context contract. It is read natively by Codex, Cursor, Copilot,
Gemini CLI, Aider, Zed, Windsurf and others; Claude Code reads it when CLAUDE.md
is absent, and our CLAUDE.md is a pointer to this file. One source of truth.

Rules for maintaining it:
  - Commands and constraints first. Agents re-read those constantly.
  - Skip the architecture essay. It costs tokens and changes agent behaviour
    less than a precise "do not touch" list.
  - Pin versions. Unpinned, the agent writes whatever its training data favours.
  - If an agent gets something wrong twice, that is an AGENTS.md bug, not a
    model bug. Fix it here, not in your prompt.
-->

## What this is
agentic-sdlc-2 — <!-- one paragraph, what it does and for whom -->

## Stack (pinned)
TODO: languages, frameworks, versions

## Commands
```bash
# install
# run (dev)
# test                     <- agents must run this before claiming done
# lint / format
# typecheck
asdlc verify               # the gates. If this fails, the work is not done.
```

## The workflow you must follow
This repo uses a spec-first, gated workflow. Do not improvise around it.

1. **No code without a change folder.** Every change lives in
   `openspec/changes/<change-id>/` with proposal.md, spec.md, design.md, tasks.md.
   Create one with `asdlc new <change-id>` if it does not exist.
2. **Stop after design.md.** A human reviews and approves the design before you
   write implementation code. Do not skip ahead because the task seems obvious.
3. **Implement task by task**, ticking `tasks.md` as you go. One task, one
   logical commit. If a task turns out to need a decision that is not in the
   spec, stop and ask — do not infer.
4. **Tests reference requirement IDs.** Every test that covers REQ-00X must name
   `REQ-00X` in its name or docstring. The traceability gate enforces this.
5. **Run `asdlc verify` before opening a PR.** Red gates are not "mostly done".
6. **Update the living spec** in `openspec/specs/<capability>/` when behaviour
   changes. Stale specs are worse than no specs — you will read them next time.

## Conventions
- <!-- naming, error handling, logging, dependency injection, etc. -->
- <!-- be specific: "use X, never Y" beats "prefer X" -->

## Do not touch
- `<!-- generated code, vendored dirs, legacy modules under freeze -->`
- Anything under `infra/` or `**/migrations/` without an approved design.md.
- Secrets, `.env`, credentials. Never inline a credential, even in a test.

## Stop and ask a human when
- The spec is ambiguous or contradicts the code.
- The change would touch auth, payments, PII, a public API contract, or a data
  migration.
- You would need to add a new production dependency.
- The scope is growing beyond what `proposal.md` said was in scope.

## Boundaries
- Never force-push, never rewrite shared history, never merge your own PR.
- Never disable, skip, or weaken a test to make it pass. Fix the code or say
  the requirement is wrong.
- Never edit `.asdlc/policy.yaml` to make a gate pass.
