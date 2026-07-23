%%DESC: Run the gates and fix what they report — honestly%%
%%HINT: [--stage spec|code]%%
Run `asdlc verify %%ARG%%` and work through the failures.

For each failing gate, fix the underlying cause. Delegate to the matching
agent below if your tool supports subagent delegation:
- **spec-present / spec-lint** — the artifact is missing or untestable. Fix the
  spec (**spec-authoring** skill), not the gate.
- **traceability** — a requirement has no task or no test. Write it.
  Best suited to **qa-engineer**.
- **spec-drift** — code moved and the spec did not. Use the
  **drift-reconciliation** skill: classify each divergence, do not blanket-sync.
  Best suited to **solutions-architect** — this is a spec-accuracy question.
- **coverage-delta** — add tests that assert behaviour. Not lines executed.
  Coverage that does not fail when you break the code is fraud.
  Best suited to **qa-engineer**.
- **security-scan** — triage with the **security-review** skill. A false positive
  gets an `asdlc:allow-secret` comment and a one-line justification, never a
  silent policy edit. Best suited to **security-engineer**.
- **human-approval** — this one is not yours to fix, agent or not. Ask an
  actual human — this gate exists specifically because some decisions are
  not an agent's to make alone.

Absolutely forbidden: editing `.asdlc/policy.yaml`, adding exempt globs,
deleting tests, or lowering thresholds to make this pass. If you believe a gate
is genuinely wrong, say so and stop.
