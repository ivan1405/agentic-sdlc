---
name: drift-reconciliation
description: Detect and repair divergence between the living specs in openspec/specs/ and what the code actually does, deciding case by case whether the spec is stale or the code is wrong. Use this skill whenever `asdlc verify` fails the spec-drift gate, when the user mentions drift, stale specs, "the docs are out of date", "the spec doesn't match the code", spec sync, or archiving a completed change, and during any onboarding or audit of a repo where specs have not been maintained.
---

# Drift reconciliation

This is the skill that decides whether the standard survives contact with reality.
Six months in, the specs are either the source of truth or they are lies that
agents read and act on. There is no stable middle.

## The one rule

**Never sync automatically.** Drift is a fork in the road, and each divergence is
one of exactly three things:

1. **The code is right, the spec is stale.** → Update the spec. Cheap.
2. **The spec is right, the code is wrong.** → You just found a bug. File it.
   Do not "fix" it by editing the spec to match — that is how a spec becomes
   documentation of the bug.
3. **Both are wrong.** → The requirement changed and nobody wrote it down. Stop
   and get a human decision.

An agent that resolves all drift as case (1) has quietly deleted your entire
quality signal. Present the fork; do not take it silently.

## Procedure

1. Run `asdlc verify --only spec-drift` to get the drifting capabilities.
2. For each capability, read `openspec/specs/<cap>/spec.md`, then read the code
   it claims to describe. Requirement by requirement.
3. For every requirement, classify: **holds / stale / violated / unverifiable**.
   - *unverifiable* means the requirement was never testable. That is its own
     finding — rewrite it with the spec-authoring skill.
4. For each `violated`, check whether a test exists. A violated requirement with
   a green test means the test is lying too. Report both.
5. Produce a reconciliation table before changing anything:

   | REQ | Status | Evidence (file:line) | Proposed action | Needs human? |
   |---|---|---|---|---|

6. Apply only the `stale` updates. Everything else goes to a human with the table.

## Archiving a completed change

When a change is done and merged, fold its delta into the living spec:

- `ADDED` requirements → append to `openspec/specs/<cap>/spec.md`, keeping IDs.
- `MODIFIED` → replace the old text in place, keeping the ID.
- `REMOVED` → delete the requirement and note the removal in the ADR if the
  removal was a decision rather than a cleanup.
- Move the change folder to `openspec/changes/archive/<date>-<change-id>/`.
- ADRs stay in `docs/adr/` — they outlive the change. The reasoning is the part
  the next agent needs and the part the archive would otherwise bury.

## Brownfield: the first pass

On a legacy repo there is no spec, so everything is drift. Do not attempt to
back-fill a spec for the whole system — you will produce a beautiful fiction.

Instead: set `spec-drift.mode: warn` in the policy, and back-fill specs only for
capabilities as you touch them. The spec grows along the paths the team actually
works. After a quarter, ratchet to `fail`. This is the only rollout that has ever
worked; big-bang spec back-fill dies in week three, every time.
