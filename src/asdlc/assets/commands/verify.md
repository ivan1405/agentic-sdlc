%%DESC: Run the gates and fix what they report — honestly%%
%%HINT: [--stage spec|code]%%
Run `asdlc verify %%ARG%%` and work through the failures.

For each failing gate, fix the underlying cause:
- **spec-present / spec-lint** — the artifact is missing or untestable. Fix the
  spec (**spec-authoring** skill), not the gate.
- **traceability** — a requirement has no task or no test. Write it.
- **spec-drift** — code moved and the spec did not. Use the
  **drift-reconciliation** skill: classify each divergence, do not blanket-sync.
- **coverage-delta** — add tests that assert behaviour. Not lines executed.
  Coverage that does not fail when you break the code is fraud.
- **security-scan** — triage with the **security-review** skill. A false positive
  gets an `asdlc:allow-secret` comment and a one-line justification, never a
  silent policy edit.
- **human-approval** — this one is not yours to fix. Ask a human.

Absolutely forbidden: editing `.asdlc/policy.yaml`, adding exempt globs,
deleting tests, or lowering thresholds to make this pass. If you believe a gate
is genuinely wrong, say so and stop.
