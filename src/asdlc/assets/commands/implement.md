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
   Check `.mcp.json`'s `mcpServers` first — if it has a `github` entry, use
   the GitHub MCP tools to open the PR instead of assuming a `gh`/git CLI is
   on PATH. No `github` entry: today's manual flow, unchanged.
9. Jira handoff — only if `proposal.md`'s `Ticket:` field names one **and**
   `.mcp.json` has an `atlassian` or `atlassian-self-hosted` entry. Once the
   PR from step 8 is open, use the Atlassian MCP tools to: look at that
   ticket's available transitions and move it to whichever one means "ready
   for review" (never guess a status name that isn't an actual transition on
   that ticket — ask a human if it's genuinely ambiguous), then comment on
   the ticket with the PR link, saying it's done and ready for review. No
   `Ticket:` value, or no atlassian* entry: skip this step entirely, nothing
   to sync.
10. This step never merges, approves, or skips a gate — it only opens the PR
    and touches the ticket, after `asdlc verify` (step 6, including
    `human-approval`'s named `Approved-by:`) is already green. Never merge
    your own PR, same boundary as always.

Exact tool names on the GitHub/Atlassian MCP servers may differ by version —
treat your actual tool list as ground truth over the wording above.
