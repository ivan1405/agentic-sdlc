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
2. **Branch before touching any file.** Create (or switch to) a branch named
   after the change-id — `git checkout -b <change-id>` if it doesn't exist yet
   — and push it upstream. Implementation never commits or pushes directly to
   `main`/the default branch; every commit below lands on this branch.
3. Work **one task at a time**, in order. For each: write the test first (name it
   after the REQ- ID it covers), then the code, then run the suite, then tick the
   box in `tasks.md`. One task, one commit, pushed to the branch from step 2.
4. Stay inside `Scope: Out` from the proposal. If you find something else worth
   fixing, note it — do not fix it here.
5. **Stop and ask** if: the spec is ambiguous, you need a new production
   dependency, you would touch auth/payments/PII/migrations beyond the design, or
   the work is growing past what the proposal scoped.
6. Never weaken, skip, or delete a test to get green. Never edit
   `.asdlc/policy.yaml`.
7. When every task is ticked: run `asdlc verify` and fix what it reports.
8. Update `%%SPECS_DIR%%/<capability>/spec.md` so the living spec matches
   reality (**drift-reconciliation** skill).
9. **Now that the work is done and tests pass, open the PR** from the branch
   pushed in step 2: title `<change-id>: <outcome>`, body = the proposal's
   Problem and Outcome, the REQ- IDs covered, and the regression surface you
   re-verified. Check `.mcp.json`'s `mcpServers` first — if it has a `github`
   entry, use the GitHub MCP tools to open the PR instead of assuming a
   `gh`/git CLI is on PATH. No `github` entry: today's manual flow, unchanged.
   This is pre-authorized — open it yourself, don't ask first, and don't open
   it any earlier than this (not until `asdlc verify` is green).
10. Ticket handoff — only if `proposal.md`'s `Ticket:` field names one **and**
    `.mcp.json` has a matching MCP entry for whichever system it's from. Once
    the PR from step 9 is open:
    - **Jira** (`Ticket:` is a Jira key, `.mcp.json` has `atlassian` or
      `atlassian-self-hosted`) — use the Atlassian MCP tools to look at that
      ticket's available transitions and move it to whichever one means
      "ready for review", then comment on the ticket with the PR link, saying
      it's done and ready for review.
    - **Azure DevOps** (`Ticket:` is a work item ID, `.mcp.json` has
      `azure-devops` or `azure-devops-local`) — use the Azure DevOps MCP tools
      to look at that work item's available states and move it to whichever
      one means "ready for review", then comment on the work item with the PR
      link, saying it's done and ready for review.
    In both cases: never guess a status/state name that isn't an actual
    transition on that ticket/work item — ask a human if it's genuinely
    ambiguous. No `Ticket:` value, or no matching MCP entry for the system it
    names: skip this step entirely, nothing to sync.
11. This step never merges, approves, or skips a gate — it only opens the PR
    and touches the ticket, after `asdlc verify` (step 7, including
    `human-approval`'s named `Approved-by:`) is already green. Never merge
    your own PR, same boundary as always — and never commit or push to `main`
    at any point in this flow.

Exact tool names on the GitHub/Atlassian/Azure DevOps MCP servers may differ by
version — treat your actual tool list as ground truth over the wording above.
