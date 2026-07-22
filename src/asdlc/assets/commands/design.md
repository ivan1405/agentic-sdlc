%%DESC: Produce the technical design for an approved spec, then stop for human review%%
%%HINT: <change-id>%%
Design the approved change: %%ARG%%

1. Read `openspec/changes/<change-id>/proposal.md` and `spec.md`, plus `AGENTS.md`.
2. Explore the actual codebase before proposing anything. Name the files you read.
3. Fill in `design.md`:
   - Approach, and at least one real alternative with why it lost.
   - Affected surfaces: files, contracts, data model, feature flag.
   - **Security notes** — use the **security-review** skill for the threat model
     delta (four questions). "No threat model delta" is a valid answer.
   - **Regression surface** — use the **regression-triage** skill. Run the
     `git grep` / `git log` blast-radius commands; do not guess at callers.
   - Test strategy — use the **test-strategy** skill.
   - Rollout, rollback, observability.
4. Write an ADR in `docs/adr/` if you made an architectural decision.
5. Stop. A human reviews and signs `Approved-by:` in design.md. **This is a hard
   gate — do not begin implementation, not even scaffolding.**
