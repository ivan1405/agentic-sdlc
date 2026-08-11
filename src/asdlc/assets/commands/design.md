%%DESC: Produce the technical design for an approved spec, then stop for human review%%
%%HINT: <change-id>%%
Design the approved change: %%ARG%%

Best suited to the **solutions-architect** agent, if your tool supports
subagent delegation — it drafts, it does not approve its own work.
**technical-leader** does the sign-off in step 5, never the same agent that
wrote the design.

1. Read `%%CHANGES_DIR%%/<change-id>/proposal.md` and `spec.md`, plus `%%CONTEXT_FILE%%`.
2. Explore the actual codebase before proposing anything. Name the files you read.
   If `graphify-out/graph.json` exists (see `%%CONTEXT_FILE%%`) and `graphify`
   is on PATH, query it for module boundaries and dependents before
   hand-exploring — re-run `graphify . --update` first if it predates recent
   changes to the affected area; a stale graph is worse than no graph. If
   `graphify` isn't on PATH, don't install it (`/onboard` is the only place
   that does) — fall back to hand-exploring.
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
