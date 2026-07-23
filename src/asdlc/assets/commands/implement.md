%%DESC: Implement an approved change, task by task, against the spec%%
%%HINT: <change-id>%%
Implement: %%ARG%%

Best suited to **frontend-dev** or **backend-dev**, whichever matches the
task, if your tool supports subagent delegation. A change that touches both
surfaces splits by task, not by agent doing both — delegate each task to
whichever one actually owns that surface.

Preconditions — verify these yourself and refuse if unmet:
- `design.md` exists and carries an `Approved-by:` line.
- `asdlc verify --stage spec` passes.

Then:
1. Read `%%CONTEXT_FILE%%`, `proposal.md`, `spec.md`, `design.md`, `tasks.md`. All of them.
2. Work **one task at a time**, in order. For each: write the test first (name it
   after the REQ- ID it covers), then the code, then run the suite, then tick the
   box in `tasks.md`. One task, one commit.
3. Stay inside `Scope: Out` from the proposal. If you find something else worth
   fixing, note it — do not fix it here.
4. **Stop and ask** if: the spec is ambiguous, you need a new production
   dependency, you would touch auth/payments/PII/migrations beyond the design, or
   the work is growing past what the proposal scoped.
5. Never weaken, skip, or delete a test to get green. Never edit
   `.asdlc/policy.yaml`.
6. When every task is ticked: run `asdlc verify` and fix what it reports.
7. Update `%%SPECS_DIR%%/<capability>/spec.md` so the living spec matches
   reality (**drift-reconciliation** skill).
8. Open a PR: title `<change-id>: <outcome>`, body = the proposal's Problem and
   Outcome, the REQ- IDs covered, and the regression surface you re-verified.
