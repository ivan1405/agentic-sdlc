---
name: spec-authoring
description: Turn a vague request, ticket, or conversation into a spec that passes `asdlc verify --stage spec` — requirements with stable REQ- IDs, normative SHALL statements, and Given/When/Then acceptance scenarios. Use this skill whenever the user mentions a spec, requirements, a change folder, a proposal, a ticket to implement, or asks to "add a feature" / "build X" / "implement Y" — even if they do not say the word "spec". Also use it when refining or reviewing an existing spec.md, and before writing any implementation code in a repo that has an openspec/ directory.
---

# Spec authoring

Your job is to produce a spec a machine can verify and a human can approve, not
a description of a feature.

## Before writing anything

Read, in order: `AGENTS.md`, `.asdlc/policy.yaml` (for the capability map), and
the existing living spec at `openspec/specs/<capability>/spec.md` if the
capability already exists. You are writing a **delta**, not a document.

## The interview

Do not start drafting until you can answer these. Ask the human; do not guess.

1. What is observably wrong today? (evidence: metric, ticket, quote)
2. Who is affected, and how many of them?
3. What is explicitly **out** of scope?
4. What is the acceptance test the requester would run to accept this?
5. What existing behaviour must NOT change?
6. Does this touch auth, money, PII, a public contract, or a migration?

If the answer to (4) is fuzzy, the spec is not ready. Say so.

## Writing requirements

One requirement = one testable claim. Rules:

- **Stable IDs.** `REQ-001`, `REQ-002`. Never renumber; IDs are referenced by
  tasks, tests, and commits. Append, don't reshuffle.
- **SHALL / SHALL NOT.** Normative language only. "should", "may", "ideally"
  are not requirements — they are hopes, and an agent will optimise them away.
- **No conjunctions.** If it has an "and", it is two requirements. This matters:
  a compound requirement cannot be traced to a single failing test.
- **Observable from outside.** "The repository layer SHALL cache" is design.
  "A repeat read within 60s SHALL not hit the database" is a requirement.

Every requirement gets at least one `#### Scenario:` with Given/When/Then, and
at least one scenario for the failure path. The happy path is the part the agent
was going to get right anyway.

### Good vs bad

| Bad | Why | Good |
|---|---|---|
| The API should be fast. | Not testable, no threshold. | The search endpoint SHALL return p95 < 300ms at 50 rps. |
| Users can reset passwords and change emails. | Two requirements. | Split into REQ-004 and REQ-005. |
| Handle errors gracefully. | Undefined. | On upstream 5xx the system SHALL return 503 with Retry-After and SHALL NOT retry more than 3 times. |
| Refactor the auth module. | Not a behaviour. | This is a task, not a requirement. Requirements describe unchanged behaviour under refactor. |

## Non-functional requirements

Only state the ones this change actually moves. A copy-pasted NFR table is noise
that dilutes the ones that matter. Each NFR names how it is verified.

## The capability line

`**Capability:** <name>` must match a key in `.asdlc/policy.yaml`. The drift gate
uses it to prove code and spec moved together. If the capability does not exist
yet, propose adding it to the policy in this same change.

## Self-check before handing over

Run `asdlc verify --stage spec`. Then ask yourself the question the gate cannot:
**could a competent developer who has never met me implement exactly this, and
would I accept what they built?** If no, the gap is in the spec.

## Never

- Never write implementation code in this phase, even a sketch. The design is
  reviewed separately and by a human, on purpose.
- Never invent a requirement to fill the template. An empty section is honest;
  a plausible-sounding invented requirement will be built.
- Never resolve an open question by choosing. Leave it in `Open questions` and
  block.
