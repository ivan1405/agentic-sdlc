# 03 — Definition of done

Print this. It's the contract between the team, the agents, and the client.

A change is **done** when:

- [ ] `openspec/changes/<id>/` has proposal, spec, design, tasks — all filled, no placeholders
- [ ] Every requirement has a stable `REQ-` ID, a SHALL statement, and at least one
      Given/When/Then scenario **including a failure path**
- [ ] A **named human** approved `design.md` **before** implementation started
- [ ] Every task is ticked and tagged with the requirement it serves
- [ ] Every requirement is named by at least one test
- [ ] The regression surface named in `design.md` was re-verified
- [ ] `asdlc verify` is green — with no gate disabled, no threshold lowered, no
      exempt glob added to make it so
- [ ] The living spec in `openspec/specs/<capability>/` matches reality
- [ ] An ADR exists if an architectural decision was made
- [ ] The PR says: the problem, the outcome, the REQ- IDs covered, and what could break

A change is **not** done because:

- the tests pass — the agent wrote the tests
- coverage went up — coverage without assertions is fraud
- the agent said it was done — it says that every time
- it works on the happy path — the bugs are all in the other branch
- CI went green on the third re-run — you don't know why it failed, so you don't
  know whether it's fixed

## The four things an agent may never do

1. Weaken, skip, or delete a test to get green.
2. Edit `.asdlc/policy.yaml`, add an exempt glob, or lower a threshold.
3. Write its own `Approved-by:` line.
4. Resolve an ambiguity in the spec by choosing. It stops and asks.

If you catch any of these in review, the fix is in `AGENTS.md`, not in a scolding
prompt. An agent that got it wrong twice is an AGENTS.md bug.
