---
name: regression-triage
description: Work out what an in-flight change could break and prove it does not — blast-radius analysis, regression test selection, and triage of a failing suite into real breaks vs flaky vs correctly-updated expectations. Use this skill whenever the user mentions regression, "did this break anything", blast radius, a red build, flaky tests, a rollback, or an incident, and always before merging a change that touches shared modules, data schemas, public contracts, or anything with more than one caller.
---

# Regression triage

The agent tests what it built. Nobody tests what it broke. That gap is where
agentic delivery actually fails, and it is invisible until production.

## Blast radius (before implementation, in design.md)

Mechanical, not intuitive. Actually run these:

```bash
git grep -n "<symbol>"                    # every caller, not the ones you remember
git log --oneline -20 -- <path>           # who else has been in here lately
git log --format='%an' -- <path> | sort | uniq -c | sort -rn   # who to ask
```

Then answer:
- **Callers** — what invokes what I changed, including tests, jobs, and scripts?
- **Data** — what else reads or writes this table/column/key? Is the migration
  reversible? Does old code have to survive the new schema for one deploy?
- **Contracts** — did a response shape, event payload, or error code change? Who
  consumes it? Are they deployed independently? (If yes: expand/contract, two
  deploys, never one.)
- **Config & flags** — does this behave differently per environment?
- **Timing** — anything that assumed order, latency, or a clock?

Write the list into `design.md` under "Regression surface". If it is empty, say
why it is empty.

## Selecting the regression tests

For each item in the blast radius, one of:
- an existing test already covers it → name it in `tasks.md` and run it,
- no test covers it → **write it before you change the code**, so you can see it
  pass on the old behaviour first. This is the only way to know it tests anything.

## Triaging a red suite

For each failure, classify — never bulk-update snapshots:

| Class | Signal | Action |
|---|---|---|
| **Real break** | Test asserts behaviour the spec still requires | Fix the code |
| **Correct update** | Spec deliberately changed this behaviour (cite the REQ) | Update the test, reference the REQ in the commit |
| **Wrong test** | Test asserted implementation detail, not a requirement | Rewrite the test, note it in the PR |
| **Flaky** | Fails intermittently, unrelated to the diff | Do NOT retry-until-green. Quarantine with a ticket. |
| **Environmental** | Fails everywhere, including on main | Stop, fix the environment, tell the team |

Any "correct update" without a REQ- reference is a real break wearing a disguise.
That is the single highest-value thing to catch in review.

## Never

- Never re-run CI hoping for green. If you do not know why it failed, you do not
  know whether it is fixed.
- Never update a snapshot or golden file in bulk. Read every diff line.
- Never mark a test skipped to unblock a merge without a ticket and an owner.
- Never conclude "unrelated failure" from a first look. Prove it: does it fail on
  main at the same commit?
