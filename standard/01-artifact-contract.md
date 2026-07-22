# 01 — The artifact contract

Four files per change, in `openspec/changes/<change-id>/`. They exist because
each answers a question that, left unanswered, an agent will answer for you —
confidently, and out of sight.

| File | Question | Reviewed by | Gate |
|---|---|---|---|
| `proposal.md` | Why, and what's out of scope? | requester + owner | `spec-present` |
| `spec.md` | What must be true when this is done? | owner | `spec-lint`, `traceability`, `spec-drift` |
| `design.md` | How, and what could it break? | **a human, before code** | `human-approval` |
| `tasks.md` | In what order, tied to which requirement? | agent self-service | `traceability` |

Plus two that outlive the change:
- `openspec/specs/<capability>/spec.md` — the **living spec**. What the system does
  today. Deltas fold into it on archive.
- `docs/adr/NNN-*.md` — **architectural decisions**. These outlive the change folder
  deliberately: the reasoning is what the next agent needs, and the archive would
  otherwise bury it.

## Rules that matter

**Requirement IDs are permanent.** `REQ-001` is referenced by tasks, tests, commits,
and PRs. Append; never renumber. Renumbering silently breaks every trace.

**Deltas, not documents.** A change's `spec.md` describes what changes
(ADDED/MODIFIED/REMOVED), not the whole system. This is what makes the standard
survive brownfield: you never have to write the spec you don't have.

**One requirement, one testable claim.** If it has an "and", it's two. A compound
requirement can't be traced to a single failing test, which is the entire point.

**SHALL / SHALL NOT only.** "Should", "ideally", "where possible" are hopes. An
agent optimises hopes away and is technically correct to.

**Every requirement has a failure scenario.** The happy path is the part the model
was going to get right anyway.

**The `Capability:` line is load-bearing.** It's how `spec-drift` proves code and
spec moved together. It must match a key in `.asdlc/policy.yaml`.

**`Approved-by:` is typed by a human.** It is the one line in the system an agent
must never write. Everything else in this standard is a convention; that one is
the accountability boundary.

## Why the design review is a hard stop

The single highest-leverage moment in the whole lifecycle is a human reading
`design.md` before any code exists. Catching the wrong library there costs ten
minutes. Catching it after the agent has written 500 confident, well-tested,
consistent lines costs a day — and reviewers who have already read 500 lines
approve them, because sunk cost applies to reviewers too.

This is why `/design` and `/implement` are separate commands and why the workflow
tells agents to stop. It is not ceremony. It is the only cheap review in the process.

## Naming

Change IDs: `verb-noun`, kebab-case, imperative. `reject-empty-cart`, not
`cart-fixes` or `SHOP-1423`. The ID appears in the branch, the PR title, the
commits, and the archive path. Ticket IDs go in the proposal body, where they
belong — they're a link to another system, not a description of the work.
